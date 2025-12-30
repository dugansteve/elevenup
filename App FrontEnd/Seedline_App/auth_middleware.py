"""
Firebase Authentication Middleware for Seedline API
Verifies Firebase JWT tokens and extracts user information.
"""

import json
import time
import base64
import urllib.request
import ssl
from pathlib import Path
from functools import lru_cache
from typing import Optional, Dict, Any

# Firebase project configuration
# These are public values - safe to include in code
FIREBASE_PROJECT_ID = "seedline-ai"

# Cache for Firebase public keys (they rotate periodically)
_firebase_keys_cache = {
    "keys": None,
    "expires_at": 0
}


def _base64url_decode(data: str) -> bytes:
    """Decode base64url encoded data."""
    # Add padding if needed
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    # Replace URL-safe characters
    data = data.replace('-', '+').replace('_', '/')
    return base64.b64decode(data)


def _decode_jwt_without_verification(token: str) -> Dict[str, Any]:
    """Decode JWT payload without verifying signature (for extracting claims)."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Decode header and payload
        header = json.loads(_base64url_decode(parts[0]))
        payload = json.loads(_base64url_decode(parts[1]))

        return {
            "header": header,
            "payload": payload
        }
    except Exception as e:
        print(f"[AUTH] JWT decode error: {e}")
        return None


def _fetch_firebase_public_keys():
    """Fetch Firebase public keys for token verification."""
    global _firebase_keys_cache

    # Check cache
    if _firebase_keys_cache["keys"] and time.time() < _firebase_keys_cache["expires_at"]:
        return _firebase_keys_cache["keys"]

    try:
        url = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

        # Create SSL context
        ctx = ssl.create_default_context()

        req = urllib.request.Request(url, headers={"User-Agent": "Seedline/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            keys = json.loads(response.read().decode())

            # Get cache-control max-age
            cache_control = response.headers.get('Cache-Control', '')
            max_age = 3600  # Default 1 hour
            if 'max-age=' in cache_control:
                try:
                    max_age = int(cache_control.split('max-age=')[1].split(',')[0])
                except:
                    pass

            _firebase_keys_cache["keys"] = keys
            _firebase_keys_cache["expires_at"] = time.time() + max_age

            return keys

    except Exception as e:
        print(f"[AUTH] Failed to fetch Firebase public keys: {e}")
        return _firebase_keys_cache.get("keys")  # Return stale cache if available


def verify_firebase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token and return user info.

    For production use, this should use the official Firebase Admin SDK.
    This is a simplified version that validates basic claims without
    full cryptographic signature verification.

    Args:
        token: The Firebase ID token from the client

    Returns:
        Dict with user info (uid, email, etc.) or None if invalid
    """
    if not token:
        return None

    try:
        # Decode the JWT
        decoded = _decode_jwt_without_verification(token)
        if not decoded:
            return None

        payload = decoded["payload"]
        header = decoded["header"]

        # Validate required claims
        now = int(time.time())

        # Check expiration
        exp = payload.get("exp", 0)
        if now > exp:
            print(f"[AUTH] Token expired: {exp} < {now}")
            return None

        # Check issued at time (not in future)
        iat = payload.get("iat", 0)
        if iat > now + 60:  # Allow 60 seconds clock skew
            print(f"[AUTH] Token issued in future: {iat}")
            return None

        # Check audience (should be our project ID)
        aud = payload.get("aud", "")
        if aud != FIREBASE_PROJECT_ID:
            print(f"[AUTH] Invalid audience: {aud}")
            return None

        # Check issuer
        iss = payload.get("iss", "")
        expected_issuer = f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
        if iss != expected_issuer:
            print(f"[AUTH] Invalid issuer: {iss}")
            return None

        # Check subject (user ID) exists
        sub = payload.get("sub", "")
        if not sub:
            print("[AUTH] Missing subject (user ID)")
            return None

        # Token is valid - return user info
        return {
            "uid": sub,
            "email": payload.get("email"),
            "email_verified": payload.get("email_verified", False),
            "name": payload.get("name"),
            "picture": payload.get("picture"),
            "auth_time": payload.get("auth_time"),
            "firebase": payload.get("firebase", {})
        }

    except Exception as e:
        print(f"[AUTH] Token verification error: {e}")
        return None


def get_auth_from_request(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Extract and verify authentication from request headers.

    Args:
        headers: Dict of HTTP headers

    Returns:
        User info dict if authenticated, None for guests
    """
    auth_header = headers.get("Authorization", "") or headers.get("authorization", "")

    if not auth_header:
        return None

    if not auth_header.startswith("Bearer "):
        print("[AUTH] Invalid Authorization header format")
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix
    return verify_firebase_token(token)


def require_auth(handler_func):
    """
    Decorator for endpoints that require authentication.

    Usage:
        @require_auth
        def handle_protected_endpoint(self, user_info, ...):
            # user_info contains uid, email, etc.
            pass
    """
    def wrapper(self, *args, **kwargs):
        headers = {k: v for k, v in self.headers.items()}
        user_info = get_auth_from_request(headers)

        if not user_info:
            self._set_headers(401)
            self.wfile.write(json.dumps({
                "error": "Authentication required",
                "code": "AUTH_REQUIRED"
            }).encode())
            return

        return handler_func(self, user_info, *args, **kwargs)

    return wrapper


def get_account_type_from_user(user_info: Dict[str, Any], users_lookup_func) -> str:
    """
    Get account type for a Firebase user.

    Args:
        user_info: Verified Firebase user info
        users_lookup_func: Function to look up user by email in local database

    Returns:
        Account type: 'guest', 'free', 'paid', 'coach', 'admin'
    """
    if not user_info:
        return 'guest'

    email = user_info.get('email')
    if not email:
        return 'free'  # Authenticated but no email

    # Look up in local user database
    local_user = users_lookup_func(email)
    if local_user:
        return local_user.get('account_type', 'free')

    return 'free'  # Authenticated but not in local DB


# Rate limit tracking per user
_user_rate_limits = {}

def check_user_rate_limit(user_id: str, account_type: str = 'guest') -> tuple:
    """
    Check rate limit for a specific user.

    Args:
        user_id: Firebase UID or IP address for guests
        account_type: Account type for determining limit

    Returns:
        (allowed: bool, remaining: int, reset_time: int)
    """
    from activity_logger import RATE_LIMITS

    limit = RATE_LIMITS.get(account_type, RATE_LIMITS['guest'])
    window = 60  # 1 minute window

    now = time.time()
    window_start = now - window

    if user_id not in _user_rate_limits:
        _user_rate_limits[user_id] = []

    # Clean old entries
    _user_rate_limits[user_id] = [
        t for t in _user_rate_limits[user_id]
        if t > window_start
    ]

    current = len(_user_rate_limits[user_id])

    if current >= limit:
        oldest = min(_user_rate_limits[user_id]) if _user_rate_limits[user_id] else now
        reset_time = int(oldest + window - now)
        return False, 0, max(1, reset_time)

    _user_rate_limits[user_id].append(now)
    return True, limit - current - 1, window
