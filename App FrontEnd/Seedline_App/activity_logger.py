"""
Seedline Activity Logger
Tracks user sessions, page views, API calls, and suspicious behavior.
"""

import sqlite3
import os
import json
import hashlib
import uuid
import urllib.request
import ssl
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
from pathlib import Path

# Cache for IP info lookups to avoid repeated API calls
_ip_info_cache = {}
_ip_cache_lock = Lock()

# Database path
ACTIVITY_DB_PATH = Path(__file__).parent / "seedline_activity.db"
SCHEMA_PATH = Path(__file__).parent / "seedline_activity.db.sql"

# Thread lock for database writes
db_lock = Lock()

# In-memory rate limiting cache
rate_limit_cache = defaultdict(list)  # ip -> [timestamps]
rate_limit_lock = Lock()

# Suspicious behavior thresholds
SUSPICIOUS_RULES = {
    "team_pages_per_day": {
        "threshold": 100,
        "severity": "medium",
        "description": "Viewed more than 100 team pages in one day"
    },
    "sequential_browsing": {
        "threshold": 20,
        "severity": "high",
        "description": "Sequential browsing pattern detected (possible scraping)"
    },
    "api_rate_per_minute": {
        "threshold": 60,
        "severity": "high",
        "description": "API rate limit exceeded (60 requests/minute)"
    },
    "rapid_navigation": {
        "threshold": 5,  # pages per second average over 30 seconds
        "severity": "medium",
        "description": "Unusually rapid page navigation"
    },
    "high_volume_ip": {
        "threshold": 500,
        "severity": "high",
        "description": "IP address generated excessive traffic"
    }
}

# Rate limits by account type
RATE_LIMITS = {
    "guest": 30,      # requests per minute
    "free": 60,
    "paid": 120,
    "coach": 120,
    "admin": 300
}


def init_database():
    """Initialize the activity database with schema."""
    with db_lock:
        conn = sqlite3.connect(ACTIVITY_DB_PATH)
        try:
            with open(SCHEMA_PATH, 'r') as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()
            print(f"Activity database initialized at {ACTIVITY_DB_PATH}")
        finally:
            conn.close()


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(ACTIVITY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_session_id():
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def check_ip_info(ip_address):
    """
    Check IP address for VPN/proxy/hosting detection using ip-api.com.

    Returns dict with:
    - is_vpn: bool
    - is_proxy: bool
    - is_hosting: bool (datacenter IP)
    - is_mobile: bool
    - country: str
    - region: str
    - city: str
    - isp: str
    - org: str
    - as_name: str (ASN name)
    """
    if not ip_address or ip_address in ('127.0.0.1', 'localhost', 'unknown', '::1'):
        return {
            'is_vpn': False,
            'is_proxy': False,
            'is_hosting': False,
            'is_mobile': False,
            'country': 'Local',
            'region': '',
            'city': '',
            'isp': 'Localhost',
            'org': '',
            'as_name': ''
        }

    # Check cache first
    with _ip_cache_lock:
        if ip_address in _ip_info_cache:
            cached = _ip_info_cache[ip_address]
            # Cache for 24 hours
            if cached.get('_cached_at', 0) > datetime.now().timestamp() - 86400:
                return cached

    try:
        # Use ip-api.com with extended fields for VPN/proxy detection
        # Note: Free tier limited to 45 requests/minute
        url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,regionName,city,isp,org,as,mobile,proxy,hosting"

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={"User-Agent": "Seedline/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

            if data.get('status') == 'success':
                result = {
                    'is_vpn': False,  # ip-api doesn't directly detect VPN in free tier
                    'is_proxy': data.get('proxy', False),
                    'is_hosting': data.get('hosting', False),  # Datacenter/hosting provider
                    'is_mobile': data.get('mobile', False),
                    'country': data.get('country', ''),
                    'region': data.get('regionName', ''),
                    'city': data.get('city', ''),
                    'isp': data.get('isp', ''),
                    'org': data.get('org', ''),
                    'as_name': data.get('as', ''),
                    '_cached_at': datetime.now().timestamp()
                }

                # Heuristic VPN detection based on hosting + known VPN ISP patterns
                vpn_isps = [
                    'nordvpn', 'expressvpn', 'surfshark', 'cyberghost', 'private internet access',
                    'mullvad', 'protonvpn', 'ipvanish', 'vyprvpn', 'tunnelbear', 'hotspot shield',
                    'windscribe', 'hide.me', 'purevpn', 'torguard', 'astrill', 'zenmate',
                    'digitalocean', 'amazon', 'google cloud', 'microsoft azure', 'linode',
                    'vultr', 'ovh', 'hetzner', 'scaleway', 'choopa', 'm247'
                ]
                isp_lower = result['isp'].lower()
                org_lower = result['org'].lower()
                as_lower = result['as_name'].lower()

                for vpn_pattern in vpn_isps:
                    if vpn_pattern in isp_lower or vpn_pattern in org_lower or vpn_pattern in as_lower:
                        result['is_vpn'] = True
                        break

                # If hosting provider is detected, likely a VPN/proxy
                if result['is_hosting']:
                    result['is_vpn'] = True

                # Cache the result
                with _ip_cache_lock:
                    _ip_info_cache[ip_address] = result
                    # Limit cache size
                    if len(_ip_info_cache) > 10000:
                        # Remove oldest entries
                        sorted_keys = sorted(_ip_info_cache.keys(),
                                           key=lambda k: _ip_info_cache[k].get('_cached_at', 0))
                        for k in sorted_keys[:1000]:
                            del _ip_info_cache[k]

                return result
            else:
                print(f"[IP] API error for {ip_address}: {data.get('message')}")

    except Exception as e:
        print(f"[IP] Failed to check IP {ip_address}: {e}")

    # Return unknown on failure
    return {
        'is_vpn': None,  # Unknown
        'is_proxy': None,
        'is_hosting': None,
        'is_mobile': None,
        'country': '',
        'region': '',
        'city': '',
        'isp': '',
        'org': '',
        'as_name': ''
    }


def hash_fingerprint(fingerprint_data):
    """Generate SHA-256 hash of fingerprint data."""
    if isinstance(fingerprint_data, dict):
        fingerprint_data = json.dumps(fingerprint_data, sort_keys=True)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def create_session(device_info, ip_address=None, user_id=None, firebase_uid=None, account_type='guest'):
    """
    Create a new session and return the session_id.

    Args:
        device_info: dict with user_agent, screen_width, etc.
        ip_address: Client IP address
        user_id: Internal user ID (if logged in)
        firebase_uid: Firebase UID (if authenticated)
        account_type: guest, free, paid, coach, admin

    Returns:
        session_id: str
    """
    session_id = generate_session_id()

    # Generate fingerprint hash
    fingerprint_data = {
        "user_agent": device_info.get("userAgent", ""),
        "screen": f"{device_info.get('screenWidth', 0)}x{device_info.get('screenHeight', 0)}",
        "timezone": device_info.get("timezone", ""),
        "language": device_info.get("language", ""),
        "platform": device_info.get("platform", "")
    }
    fingerprint_hash = hash_fingerprint(fingerprint_data)

    # Check IP for VPN/proxy detection (async-friendly, with caching)
    ip_info = check_ip_info(ip_address)

    with db_lock:
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO sessions (
                    session_id, user_id, firebase_uid, account_type,
                    ip_address, user_agent, screen_width, screen_height,
                    color_depth, pixel_ratio, timezone, timezone_offset,
                    language, languages, platform, vendor,
                    hardware_concurrency, max_touch_points, cookies_enabled,
                    do_not_track, fingerprint_hash, referrer, landing_page,
                    utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                    ip_country, ip_region, ip_city, ip_isp, ip_org, ip_asn,
                    is_vpn, is_proxy, is_hosting, is_mobile
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, firebase_uid, account_type,
                ip_address,
                device_info.get("userAgent"),
                device_info.get("screenWidth"),
                device_info.get("screenHeight"),
                device_info.get("colorDepth"),
                device_info.get("pixelRatio"),
                device_info.get("timezone"),
                device_info.get("timezoneOffset"),
                device_info.get("language"),
                json.dumps(device_info.get("languages", [])),
                device_info.get("platform"),
                device_info.get("vendor"),
                device_info.get("hardwareConcurrency"),
                device_info.get("maxTouchPoints"),
                1 if device_info.get("cookiesEnabled") else 0,
                device_info.get("doNotTrack"),
                fingerprint_hash,
                device_info.get("referrer"),
                device_info.get("landingPage"),
                device_info.get("utm_source"),
                device_info.get("utm_medium"),
                device_info.get("utm_campaign"),
                device_info.get("utm_term"),
                device_info.get("utm_content"),
                # IP geolocation and VPN detection
                ip_info.get('country'),
                ip_info.get('region'),
                ip_info.get('city'),
                ip_info.get('isp'),
                ip_info.get('org'),
                ip_info.get('as_name'),
                1 if ip_info.get('is_vpn') else (0 if ip_info.get('is_vpn') is False else None),
                1 if ip_info.get('is_proxy') else (0 if ip_info.get('is_proxy') is False else None),
                1 if ip_info.get('is_hosting') else (0 if ip_info.get('is_hosting') is False else None),
                1 if ip_info.get('is_mobile') else (0 if ip_info.get('is_mobile') is False else None)
            ))
            conn.commit()

            # Check if IP or fingerprint is blocked
            is_blocked = check_blocklist(conn, ip_address, fingerprint_hash)
            if is_blocked:
                conn.execute("""
                    UPDATE sessions SET is_blocked = 1, blocked_reason = ?
                    WHERE session_id = ?
                """, (is_blocked, session_id))
                conn.commit()

        finally:
            conn.close()

    return session_id


def update_session_user(session_id, user_id, firebase_uid, account_type):
    """Update session with authenticated user info."""
    with db_lock:
        conn = get_db_connection()
        try:
            conn.execute("""
                UPDATE sessions
                SET user_id = ?, firebase_uid = ?, account_type = ?, last_activity = datetime('now')
                WHERE session_id = ?
            """, (user_id, firebase_uid, account_type, session_id))
            conn.commit()
        finally:
            conn.close()


def log_page_view(session_id, page_type, page_path, entity_type=None, entity_id=None,
                  entity_name=None, previous_page=None, previous_entity_id=None,
                  navigation_method=None, page_params=None, user_id=None):
    """
    Log a page view event.

    Returns:
        page_view_id: int
    """
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO page_views (
                    session_id, user_id, page_type, page_path, page_params,
                    entity_type, entity_id, entity_name,
                    previous_page, previous_entity_id, navigation_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, page_type, page_path,
                json.dumps(page_params) if page_params else None,
                entity_type, entity_id, entity_name,
                previous_page, previous_entity_id, navigation_method
            ))
            page_view_id = cursor.lastrowid

            # Update session stats
            conn.execute("""
                UPDATE sessions
                SET page_view_count = page_view_count + 1, last_activity = datetime('now')
                WHERE session_id = ?
            """, (session_id,))

            conn.commit()

            # Check for suspicious patterns (async-safe)
            check_suspicious_patterns(conn, session_id, entity_type, entity_id, previous_entity_id)

        finally:
            conn.close()

    return page_view_id


def update_page_time(page_view_id, time_on_page_ms, max_scroll_depth=None):
    """Update time spent on a page (called when user leaves page)."""
    with db_lock:
        conn = get_db_connection()
        try:
            conn.execute("""
                UPDATE page_views
                SET time_on_page_ms = ?, max_scroll_depth = ?
                WHERE id = ?
            """, (time_on_page_ms, max_scroll_depth, page_view_id))
            conn.commit()
        finally:
            conn.close()


def log_api_call(endpoint, method, session_id=None, user_id=None, ip_address=None,
                 params=None, status_code=None, response_time_ms=None,
                 response_size_bytes=None, error_message=None, was_rate_limited=False):
    """Log an API call."""
    with db_lock:
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO api_calls (
                    session_id, user_id, ip_address, endpoint, method, params,
                    status_code, response_time_ms, response_size_bytes,
                    error_message, was_rate_limited
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, ip_address, endpoint, method,
                json.dumps(params) if params else None,
                status_code, response_time_ms, response_size_bytes,
                error_message, 1 if was_rate_limited else 0
            ))

            # Update session API call count
            if session_id:
                conn.execute("""
                    UPDATE sessions
                    SET api_call_count = api_call_count + 1, last_activity = datetime('now')
                    WHERE session_id = ?
                """, (session_id,))

            conn.commit()
        finally:
            conn.close()


def check_rate_limit(ip_address, account_type='guest'):
    """
    Check if request should be rate limited.

    Returns:
        (allowed: bool, remaining: int, reset_seconds: int)
    """
    limit = RATE_LIMITS.get(account_type, RATE_LIMITS['guest'])
    window_seconds = 60
    now = datetime.now()
    window_start = now - timedelta(seconds=window_seconds)

    with rate_limit_lock:
        # Clean old entries
        rate_limit_cache[ip_address] = [
            t for t in rate_limit_cache[ip_address]
            if t > window_start
        ]

        current_count = len(rate_limit_cache[ip_address])

        if current_count >= limit:
            # Calculate reset time
            oldest = min(rate_limit_cache[ip_address]) if rate_limit_cache[ip_address] else now
            reset_seconds = int((oldest + timedelta(seconds=window_seconds) - now).total_seconds())
            return False, 0, max(1, reset_seconds)

        rate_limit_cache[ip_address].append(now)
        remaining = limit - current_count - 1
        return True, remaining, window_seconds


def check_suspicious_patterns(conn, session_id, entity_type, entity_id, previous_entity_id):
    """Check for suspicious browsing patterns."""

    # Check for sequential browsing (team1, team2, team3, etc.)
    if entity_type == 'team' and entity_id and previous_entity_id:
        try:
            current_id = int(entity_id) if entity_id.isdigit() else None
            previous_id = int(previous_entity_id) if previous_entity_id.isdigit() else None

            if current_id and previous_id and abs(current_id - previous_id) == 1:
                # Increment sequential count in daily stats
                today = datetime.now().strftime('%Y-%m-%d')

                # Get or create daily stats
                cursor = conn.execute("""
                    SELECT sequential_team_views FROM daily_session_stats
                    WHERE date = ? AND session_id = ?
                """, (today, session_id))
                row = cursor.fetchone()

                if row:
                    new_count = row[0] + 1
                    conn.execute("""
                        UPDATE daily_session_stats
                        SET sequential_team_views = ?, team_pages = team_pages + 1
                        WHERE date = ? AND session_id = ?
                    """, (new_count, today, session_id))
                else:
                    # Get session info
                    session = conn.execute("""
                        SELECT user_id, ip_address, fingerprint_hash FROM sessions
                        WHERE session_id = ?
                    """, (session_id,)).fetchone()

                    conn.execute("""
                        INSERT INTO daily_session_stats (
                            date, session_id, user_id, ip_address, fingerprint_hash,
                            team_pages, sequential_team_views
                        ) VALUES (?, ?, ?, ?, ?, 1, 1)
                    """, (today, session_id,
                          session['user_id'] if session else None,
                          session['ip_address'] if session else None,
                          session['fingerprint_hash'] if session else None))
                    new_count = 1

                # Check threshold
                if new_count >= SUSPICIOUS_RULES['sequential_browsing']['threshold']:
                    flag_suspicious(conn, session_id, 'sequential_browsing', {
                        'sequential_count': new_count,
                        'last_entity_id': entity_id
                    })

                conn.commit()

        except (ValueError, TypeError):
            pass  # Non-numeric IDs, skip sequential check


def flag_suspicious(conn, session_id, detection_type, details=None):
    """Flag a session for suspicious activity."""
    rule = SUSPICIOUS_RULES.get(detection_type, {})

    # Get session info
    session = conn.execute("""
        SELECT user_id, ip_address, fingerprint_hash, page_view_count, api_call_count
        FROM sessions WHERE session_id = ?
    """, (session_id,)).fetchone()

    if not session:
        return

    # Check if already flagged for this type today
    today = datetime.now().strftime('%Y-%m-%d')
    existing = conn.execute("""
        SELECT id FROM suspicious_activity
        WHERE session_id = ? AND detection_type = ? AND date(timestamp) = ?
    """, (session_id, detection_type, today)).fetchone()

    if existing:
        return  # Already flagged today

    conn.execute("""
        INSERT INTO suspicious_activity (
            session_id, user_id, ip_address, fingerprint_hash,
            detection_type, detection_rule, severity, details,
            page_views_count, api_calls_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, session['user_id'], session['ip_address'], session['fingerprint_hash'],
        detection_type, rule.get('description', ''), rule.get('severity', 'medium'),
        json.dumps(details) if details else None,
        session['page_view_count'], session['api_call_count']
    ))

    # Update session suspicious flag
    conn.execute("""
        UPDATE sessions SET is_suspicious = 1, suspicious_reason = ?
        WHERE session_id = ?
    """, (detection_type, session_id))

    conn.commit()


def check_blocklist(conn, ip_address, fingerprint_hash):
    """Check if IP or fingerprint is blocked."""
    now = datetime.now().isoformat()

    cursor = conn.execute("""
        SELECT block_type, reason FROM blocklist
        WHERE is_active = 1
        AND (expires_at IS NULL OR expires_at > ?)
        AND ((block_type = 'ip' AND block_value = ?)
             OR (block_type = 'fingerprint' AND block_value = ?))
        LIMIT 1
    """, (now, ip_address, fingerprint_hash))

    row = cursor.fetchone()
    if row:
        return f"Blocked ({row['block_type']}): {row['reason']}"
    return None


def add_to_blocklist(block_type, block_value, reason, expires_hours=None, created_by=None):
    """Add an IP or fingerprint to the blocklist."""
    expires_at = None
    if expires_hours:
        expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()

    with db_lock:
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO blocklist (block_type, block_value, reason, expires_at, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (block_type, block_value, reason, expires_at, created_by))
            conn.commit()
        finally:
            conn.close()


def get_session_stats(session_id):
    """Get statistics for a session."""
    conn = get_db_connection()
    try:
        session = conn.execute("""
            SELECT * FROM sessions WHERE session_id = ?
        """, (session_id,)).fetchone()

        if not session:
            return None

        page_views = conn.execute("""
            SELECT page_type, COUNT(*) as count FROM page_views
            WHERE session_id = ?
            GROUP BY page_type
        """, (session_id,)).fetchall()

        return {
            "session": dict(session),
            "page_views_by_type": {row['page_type']: row['count'] for row in page_views}
        }
    finally:
        conn.close()


def get_suspicious_activity(limit=100, severity=None, unresolved_only=True):
    """Get recent suspicious activity."""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM suspicious_activity WHERE 1=1"
        params = []

        if unresolved_only:
            query += " AND resolved = 0"

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_daily_stats(date=None):
    """Get daily activity statistics."""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    try:
        # Session counts
        sessions = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN account_type = 'guest' THEN 1 ELSE 0 END) as guests,
                   SUM(CASE WHEN account_type != 'guest' THEN 1 ELSE 0 END) as authenticated,
                   SUM(is_suspicious) as suspicious
            FROM sessions
            WHERE date(created_at) = ?
        """, (date,)).fetchone()

        # Page views
        page_views = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN entity_type = 'team' THEN 1 ELSE 0 END) as team_views,
                   SUM(CASE WHEN entity_type = 'club' THEN 1 ELSE 0 END) as club_views,
                   SUM(CASE WHEN entity_type = 'player' THEN 1 ELSE 0 END) as player_views
            FROM page_views
            WHERE date(timestamp) = ?
        """, (date,)).fetchone()

        # API calls
        api_calls = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(was_rate_limited) as rate_limited,
                   AVG(response_time_ms) as avg_response_time
            FROM api_calls
            WHERE date(timestamp) = ?
        """, (date,)).fetchone()

        return {
            "date": date,
            "sessions": dict(sessions),
            "page_views": dict(page_views),
            "api_calls": dict(api_calls)
        }
    finally:
        conn.close()


# Initialize database on import
if not ACTIVITY_DB_PATH.exists():
    init_database()
