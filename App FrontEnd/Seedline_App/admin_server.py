#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEEDLINE ADMIN SERVER v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Backend server for the Seedline Admin Dashboard.
Provides API endpoints for database stats, scraper management, and user management.

USAGE:
    python admin_server.py                    # Start server on port 5050
    python admin_server.py --port 8080        # Custom port

Then open admin_dashboard.html in your browser.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import sqlite3
import subprocess
import threading
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import time

# Import activity logging and auth middleware
try:
    from activity_logger import (
        init_database as init_activity_db,
        create_session, update_session_user, log_page_view, update_page_time,
        log_api_call, check_rate_limit, get_session_stats, get_suspicious_activity,
        get_daily_stats, add_to_blocklist, ACTIVITY_DB_PATH
    )
    from auth_middleware import (
        get_auth_from_request, verify_firebase_token, get_account_type_from_user,
        check_user_rate_limit
    )
    ACTIVITY_TRACKING_ENABLED = True
    print("[INFO] Activity tracking and auth middleware loaded")
except ImportError as e:
    ACTIVITY_TRACKING_ENABLED = False
    print(f"[WARN] Activity tracking not available: {e}")
import webbrowser

# ============================================================================
# CONFIGURATION - ADJUST THESE PATHS FOR YOUR SETUP
# ============================================================================

# Auto-detect paths based on script location
SCRIPT_DIR = Path(__file__).parent.absolute()

# Try to find the scrapers and data folder
def find_scrapers_folder():
    """Find the 'scrapers and data' folder"""
    # Expected structure:
    # Seedline/
    #   scrapers and data/     <- we want to find this
    #   App_FrontEnd/
    #     Seedline_App/        <- SCRIPT_DIR is here
    #
    # So from Seedline_App, we go: parent (App_FrontEnd) -> parent (Seedline) -> scrapers and data
    
    candidates = [
        # Standard structure: Seedline_App is in App_FrontEnd which is sibling to "scrapers and data"
        SCRIPT_DIR.parent.parent / "scrapers and data",
        # Alternative: scrapers and data is direct sibling of Seedline_App
        SCRIPT_DIR.parent / "scrapers and data",
        # Alternative: scrapers and data is inside Seedline_App's parent's parent's parent
        SCRIPT_DIR.parent.parent.parent / "scrapers and data",
        # Direct sibling
        SCRIPT_DIR / "scrapers and data",
        # Hardcoded fallback
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data"),
    ]
    
    print(f"[SEARCH] Looking for 'scrapers and data' folder...")
    print(f"   Script location: {SCRIPT_DIR}")

    for path in candidates:
        print(f"   Checking: {path}")
        if path.exists():
            print(f"   [OK] Found: {path}")
            return path

    print(f"   [WARN] Not found - using script directory")
    return SCRIPT_DIR

SCRAPERS_FOLDER = find_scrapers_folder()
DATABASE_PATH = SCRAPERS_FOLDER / "seedlinedata.db"

def find_latest_scraper(folder_path: Path, pattern: str) -> Path:
    """Find the latest version of a scraper matching the pattern"""
    import re
    
    if not folder_path.exists():
        return folder_path / pattern.replace("*", "1")
    
    # Find all matching files
    files = list(folder_path.glob(pattern))
    if not files:
        # Try case-insensitive search on Windows
        all_files = list(folder_path.glob("*.py"))
        pattern_base = pattern.lower().replace("*", "").replace(".py", "")
        files = [f for f in all_files if pattern_base in f.name.lower()]
    
    if not files:
        return folder_path / pattern.replace("*", "1")
    
    # Sort by version number (extract number from filename)
    def get_version(f):
        match = re.search(r'v(\d+)', f.name)
        return int(match.group(1)) if match else 0
    
    files.sort(key=get_version, reverse=True)
    return files[0]

# Scraper locations - will be updated dynamically
def get_scraper_paths():
    """Get scraper paths, preferring latest versions from correct folders"""
    # Updated folder paths to match actual folder structure (v2)
    # Structure: scrapers and data / Scrapers / [scraper folders]
    scrapers_subfolder = SCRAPERS_FOLDER / "Scrapers"
    
    ecnl_folder = scrapers_subfolder / "ECNL and ECNL RL Scraper"
    ga_league_folder = scrapers_subfolder / "girls academy league scraper"
    ga_events_folder = scrapers_subfolder / "Girls Academy Event Scraper"
    aspire_folder = scrapers_subfolder / "aspire scraper"
    npl_folder = scrapers_subfolder / "NPL league scraper"
    
    # Also check in scrapers subfolder of Seedline_App (bundled with app)
    app_scrapers = SCRIPT_DIR / "scrapers"
    
    print(f"\n[CONFIG] Configuring scraper paths...")
    print(f"   SCRAPERS_FOLDER: {SCRAPERS_FOLDER}")
    print(f"   Scrapers subfolder: {scrapers_subfolder} (exists: {scrapers_subfolder.exists()})")
    print(f"   App scrapers folder: {app_scrapers} (exists: {app_scrapers.exists()})")
    
    scrapers = {
        "ecnl": {
            "name": "ECNL + ECNL-RL Scraper",
            "path": ecnl_folder / "ecnl_scraper_final.py",
            "description": "Scrapes ECNL and ECNL Regional League games and players"
        },
        "ga": {
            "name": "Girls Academy Scraper",
            "path": ga_league_folder / "GA_league_scraper_final.py",
            "description": "Scrapes Girls Academy league games"
        },
        "ga_events": {
            "name": "GA Events Scraper",
            "path": ga_events_folder / "GA_events_scraper_final.py",
            "description": "Scrapes GA showcases, playoffs, regionals, and Champions Cup"
        },
        "aspire": {
            "name": "ASPIRE Scraper",
            "path": aspire_folder / "ASPIRE_league_scraper_final.py",
            "description": "Scrapes ASPIRE league games"
        },
        "npl": {
            "name": "NPL League Scraper",
            "path": npl_folder / "us_club_npl_league_scraper_final.py",
            "description": "Scrapes US Club Soccer NPL and Sub-NPL league games"
        }
    }
    
    # Override with app-bundled scrapers if they exist AND if Dropbox versions weren't found
    # The find_latest_scraper function already picks the highest version, so we only use
    # bundled scrapers as fallback
    if app_scrapers.exists():
        bundled_scrapers = {
            "ecnl": "ecnl_scraper_final.py",
            "ga": "GA_league_scraper_final.py",
            "ga_events": "GA_events_scraper_final.py",
            "aspire": "ASPIRE_league_scraper_final.py"
        }
        
        for scraper_id, pattern in bundled_scrapers.items():
            current_path = scrapers[scraper_id]["path"]
            # Only use bundled if current doesn't exist
            if not current_path.exists():
                bundled_path = find_latest_scraper(app_scrapers, pattern)
                if bundled_path.exists():
                    print(f"   {scraper_id}: Using bundled {bundled_path.name}")
                    scrapers[scraper_id]["path"] = bundled_path
            else:
                print(f"   {scraper_id}: Using {current_path.name} from {current_path.parent.name}")
    
    # Final status
    print(f"\n[INFO] Scraper configuration:")
    for sid, s in scrapers.items():
        exists = s["path"].exists()
        print(f"   {sid}: {s['path']} ({'OK' if exists else 'MISSING'})")
    
    return scrapers

SCRAPERS = get_scraper_paths()

# Team ranker location - use final version
def find_team_ranker():
    """Find the team ranker (now using 'final' naming convention)"""
    ranker_folder = SCRAPERS_FOLDER / "Run Rankings"
    ranker_path = ranker_folder / "team_ranker_final.py"

    if ranker_path.exists():
        print(f"   Found team ranker: {ranker_path.name}")
        return ranker_path

    # Fallback to old versioned naming if final doesn't exist
    if ranker_folder.exists():
        import re
        ranker_files = list(ranker_folder.glob("team_ranker_v*.py"))
        if ranker_files:
            def get_version(f):
                match = re.search(r'v(\d+)([a-z])?', f.name)
                if match:
                    num = int(match.group(1))
                    letter = match.group(2) or ''
                    return (num, letter)
                return (0, '')
            ranker_files.sort(key=get_version, reverse=True)
            print(f"   Found team ranker (fallback): {ranker_files[0].name}")
            return ranker_files[0]

    return ranker_folder / "team_ranker_final.py"

RANKER_PATH = find_team_ranker()
RANKINGS_OUTPUT = SCRAPERS_FOLDER / "Run Rankings" / "rankings_for_react.json"

# React app location
REACT_APP_PATH = SCRIPT_DIR

# ============================================================================
# DATA FOLDER MANAGEMENT
# ============================================================================
# Data files are stored in a sibling "Seedline_Data" folder to persist across app updates
# Structure:
#   App_FrontEnd/
#     Seedline_Data/    <- persistent data (users, config, badges)
#     Seedline_App/     <- app code (replaceable on updates)

DATA_FOLDER = SCRIPT_DIR.parent / "Seedline_Data"

def ensure_data_folder():
    """Create Seedline_Data folder if it doesn't exist"""
    if not DATA_FOLDER.exists():
        DATA_FOLDER.mkdir(parents=True, exist_ok=True)
        print(f"Created data folder: {DATA_FOLDER}")

def get_data_file_path(filename):
    """Get path to a data file, preferring Seedline_Data folder"""
    # First check Seedline_Data folder (preferred)
    data_path = DATA_FOLDER / filename
    if data_path.exists():
        return data_path
    
    # Then check current app folder (legacy location)
    legacy_path = SCRIPT_DIR / filename
    if legacy_path.exists():
        # Migrate to data folder
        ensure_data_folder()
        try:
            import shutil
            shutil.copy2(legacy_path, data_path)
            print(f"Migrated {filename} to {DATA_FOLDER}")
            return data_path
        except Exception as e:
            print(f"Could not migrate {filename}: {e}")
            return legacy_path
    
    # Return data folder path for new files
    ensure_data_folder()
    return data_path

# Config file for storing settings (badges, saved players, etc.)
CONFIG_FILE = get_data_file_path("admin_config.json")

# Separate users file for persistence across app updates
USERS_FILE = get_data_file_path("seedline_users.json")

# GA Events config file
GA_EVENTS_CONFIG = get_data_file_path("ga_events_config.json")

# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def load_users():
    """Load users from separate persistent file"""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                return data.get("users", [])
        except:
            pass
    return []

def save_users(users):
    """Save users to separate persistent file"""
    with open(USERS_FILE, 'w') as f:
        json.dump({"users": users, "last_updated": datetime.now().isoformat()}, f, indent=2)

def load_config():
    """Load configuration from file"""
    default_config = {
        "users": [],  # Legacy - will migrate to USERS_FILE
        "scraper_history": [],
        "settings": {
            "auto_export": True,
            "theme": "dark"
        }
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                
                # Migrate users to separate file if they exist in config but not in users file
                if config.get("users") and not USERS_FILE.exists():
                    save_users(config["users"])
                    print(f"Migrated {len(config['users'])} users to {USERS_FILE}")
                
                return config
        except:
            pass
    return default_config

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, default=str)

def update_paths(new_paths):
    """Update configuration paths"""
    global DATABASE_PATH, SCRAPERS_FOLDER, REACT_APP_PATH, RANKER_PATH
    
    config = load_config()
    if "paths" not in config:
        config["paths"] = {}
    
    for key, value in new_paths.items():
        if value:
            config["paths"][key] = value
            if key == "database":
                DATABASE_PATH = Path(value)
            elif key == "scrapers_folder":
                SCRAPERS_FOLDER = Path(value)
            elif key == "react_app":
                REACT_APP_PATH = Path(value)
            elif key == "ranker":
                RANKER_PATH = Path(value)
    
    save_config(config)
    return {"success": True, "paths": config["paths"]}

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def get_database_stats():
    """Get comprehensive database statistics"""
    stats = {
        "connected": False,
        "path": str(DATABASE_PATH),
        "exists": DATABASE_PATH.exists(),
        "size_mb": 0,
        "last_modified": None,
        "total_games": 0,
        "total_teams": 0,
        "total_players": 0,
        "completed_games": 0,
        "games_by_league": {},
        "games_by_age": {},
        "games_by_status": {},
        "players_by_league": {},
        "recent_games": [],
        "tables": []
    }
    
    if not DATABASE_PATH.exists():
        return stats
    
    try:
        stats["size_mb"] = round(DATABASE_PATH.stat().st_size / (1024 * 1024), 2)
        stats["last_modified"] = datetime.fromtimestamp(DATABASE_PATH.stat().st_mtime).isoformat()
        
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        stats["connected"] = True
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        stats["tables"] = [row[0] for row in cursor.fetchall()]
        
        # Total games
        if 'games' in stats["tables"]:
            cursor.execute("SELECT COUNT(*) FROM games")
            stats["total_games"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM games WHERE game_status = 'completed'")
            stats["completed_games"] = cursor.fetchone()[0]
            
            # Games by league
            cursor.execute("""
                SELECT league, COUNT(*) FROM games 
                WHERE league IS NOT NULL 
                GROUP BY league ORDER BY COUNT(*) DESC
            """)
            stats["games_by_league"] = dict(cursor.fetchall())
            
            # Games by age group - sort Girls first (G), then Boys (B), oldest to youngest
            cursor.execute("""
                SELECT age_group, COUNT(*) FROM games 
                WHERE age_group IS NOT NULL 
                GROUP BY age_group
            """)
            age_data = cursor.fetchall()
            
            def age_sort_key(item):
                ag = str(item[0]) if item[0] else ""
                # Girls (G) sort before Boys (B)
                gender = 0 if ag.upper().startswith('G') else 1
                # Extract number, sort descending (older kids first)
                try:
                    num = int(re.sub(r'[^0-9]', '', ag))
                except:
                    num = 0
                return (gender, -num)
            
            stats["games_by_age"] = dict(sorted(age_data, key=age_sort_key))
            
            # Games by status
            cursor.execute("""
                SELECT COALESCE(game_status, 'unknown'), COUNT(*) FROM games 
                GROUP BY game_status
            """)
            stats["games_by_status"] = dict(cursor.fetchall())
            
            # Recent games - use game_date_iso column for proper sorting
            # First check if game_date_iso column exists and has data
            cursor.execute("PRAGMA table_info(games)")
            columns = [row[1] for row in cursor.fetchall()]
            has_iso_column = 'game_date_iso' in columns
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            if has_iso_column:
                # Use the ISO date column for efficient sorting
                cursor.execute("""
                    SELECT game_date_iso, home_team, away_team, home_score, away_score, league, age_group
                    FROM games 
                    WHERE game_status = 'completed' 
                    AND home_score IS NOT NULL
                    AND game_date_iso IS NOT NULL 
                    AND game_date_iso != ''
                    AND game_date_iso <= ?
                    ORDER BY game_date_iso DESC
                    LIMIT 20
                """, (today,))
                recent = cursor.fetchall()
                
                stats["recent_games"] = [
                    {
                        "date": row[0],
                        "home_team": row[1],
                        "away_team": row[2],
                        "home_score": row[3],
                        "away_score": row[4],
                        "league": row[5],
                        "age_group": row[6]
                    }
                    for row in recent
                ]
            else:
                # Fallback: Parse dates manually (slower)
                cursor.execute("""
                    SELECT game_date, home_team, away_team, home_score, away_score, league, age_group
                    FROM games 
                    WHERE game_status = 'completed' AND home_score IS NOT NULL
                """)
                all_games = cursor.fetchall()
                
                # Parse and sort dates properly
                def parse_date_for_sort(date_str):
                    if not date_str:
                        return "0000-00-00"
                    date_str = str(date_str).strip()
                    
                    # Already YYYY-MM-DD format
                    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
                        return date_str[:10]
                    
                    # Try standard datetime formats
                    for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%m-%d-%Y"]:
                        try:
                            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                        except:
                            continue
                    
                    # Try to extract date from string like "Dec 7, 2025"
                    try:
                        parts = date_str.replace(',', '').split()
                        if len(parts) >= 3:
                            month_map = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                                        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
                            month_str = parts[0][:3].lower()
                            if month_str in month_map:
                                month = month_map[month_str]
                                day = ''.join(c for c in parts[1] if c.isdigit()).zfill(2)
                                year = parts[2][:4] if len(parts[2]) >= 4 else '2025'
                                return f"{year}-{month}-{day}"
                    except:
                        pass
                    
                    return "0000-00-00"
                
                # Filter and sort
                games_with_dates = []
                for game in all_games:
                    parsed = parse_date_for_sort(game[0])
                    if parsed != "0000-00-00" and parsed <= today:
                        games_with_dates.append((parsed, game))
                
                games_with_dates.sort(key=lambda x: x[0], reverse=True)
                
                stats["recent_games"] = [
                    {
                        "date": parsed_date,
                        "home_team": game[1],
                        "away_team": game[2],
                        "home_score": game[3],
                        "away_score": game[4],
                        "league": game[5],
                        "age_group": game[6]
                    }
                    for parsed_date, game in games_with_dates[:20]
                ]
        
        # Total teams
        if 'teams' in stats["tables"]:
            cursor.execute("SELECT COUNT(*) FROM teams")
            stats["total_teams"] = cursor.fetchone()[0]
        
        # Total players
        if 'players' in stats["tables"]:
            cursor.execute("SELECT COUNT(*) FROM players")
            stats["total_players"] = cursor.fetchone()[0]
            
            # Players by league
            cursor.execute("""
                SELECT COALESCE(league, 'Unknown'), COUNT(*) FROM players 
                GROUP BY league ORDER BY COUNT(*) DESC
            """)
            stats["players_by_league"] = dict(cursor.fetchall())
        
        conn.close()
    except Exception as e:
        stats["error"] = str(e)
    
    return stats

def get_filter_options():
    """Get available filter options from database"""
    options = {
        "leagues": [],
        "age_groups": [],
        "player_age_groups": [],
        "positions": [],
        "genders": ["Boys", "Girls"]
    }
    
    if not DATABASE_PATH.exists():
        return options
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        # Get unique leagues from BOTH teams AND games tables
        leagues = set()
        cursor.execute("SELECT DISTINCT league FROM teams WHERE league IS NOT NULL AND league != ''")
        leagues.update(row[0] for row in cursor.fetchall())
        cursor.execute("SELECT DISTINCT league FROM games WHERE league IS NOT NULL AND league != ''")
        leagues.update(row[0] for row in cursor.fetchall())
        options["leagues"] = sorted(list(leagues))
        
        # Get unique age groups from teams, games, AND players
        age_groups = set()
        cursor.execute("SELECT DISTINCT age_group FROM teams WHERE age_group IS NOT NULL AND age_group != ''")
        age_groups.update(row[0] for row in cursor.fetchall())
        cursor.execute("SELECT DISTINCT age_group FROM games WHERE age_group IS NOT NULL AND age_group != ''")
        age_groups.update(row[0] for row in cursor.fetchall())
        options["age_groups"] = sorted(list(age_groups))
        
        # Get age groups specifically from players table (for player filtering)
        cursor.execute("SELECT DISTINCT age_group FROM players WHERE age_group IS NOT NULL AND age_group != '' ORDER BY age_group")
        options["player_age_groups"] = [row[0] for row in cursor.fetchall()]
        
        # Get unique positions from players
        cursor.execute("SELECT DISTINCT position FROM players WHERE position IS NOT NULL AND position != '' ORDER BY position")
        options["positions"] = [row[0] for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        options["error"] = str(e)
    
    return options

def normalize_age_group_for_sql(age_group):
    """
    Convert age group to multiple possible formats for flexible matching.
    Handles: G13 <-> 13G, G08/07 <-> 08/07G, etc.
    Returns list of possible formats.
    """
    if not age_group:
        return []
    
    formats = [age_group]  # Always include original
    
    # Pattern: G13, B13, G08/07, etc.
    import re
    
    # Format 1: GXX or BXX (e.g., G13, B08, G08/07)
    match1 = re.match(r'^([GB])(\d{2}(?:/\d{2})?)$', age_group)
    if match1:
        gender, num = match1.groups()
        # Add reversed format: XXG or XXB
        formats.append(f"{num}{gender}")
    
    # Format 2: XXG or XXB (e.g., 13G, 08B, 08/07G)
    match2 = re.match(r'^(\d{2}(?:/\d{2})?)([GB])$', age_group)
    if match2:
        num, gender = match2.groups()
        # Add reversed format: GXX or BXX
        formats.append(f"{gender}{num}")
    
    return formats

def get_all_teams(limit=100, offset=0, league=None, age_group=None, search=None, gender=None):
    """Get teams from database with filtering"""
    if not DATABASE_PATH.exists():
        return {"teams": [], "total": 0}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        # Check if teams table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teams'")
        if not cursor.fetchone():
            conn.close()
            return {"teams": [], "total": 0}
        
        # Build query
        where_clauses = []
        params = []
        
        if league:
            # Use LIKE for partial matching (e.g., "GA" matches "Girls Academy")
            where_clauses.append("league LIKE ?")
            params.append(f"%{league}%")
        if age_group:
            # Handle both G13 and 13G formats
            age_formats = normalize_age_group_for_sql(age_group)
            if len(age_formats) == 1:
                where_clauses.append("age_group = ?")
                params.append(age_group)
            else:
                placeholders = " OR ".join(["age_group = ?" for _ in age_formats])
                where_clauses.append(f"({placeholders})")
                params.extend(age_formats)
        if gender:
            # Filter by first letter of age_group (G for Girls, B for Boys)
            if gender.lower() in ['girls', 'g']:
                where_clauses.append("age_group LIKE 'G%'")
            elif gender.lower() in ['boys', 'b']:
                where_clauses.append("age_group LIKE 'B%'")
        if search:
            where_clauses.append("(team_name LIKE ? OR club LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM teams{where_sql}", params)
        total = cursor.fetchone()[0]
        
        # Get teams with rowid for editing
        cursor.execute(f"""
            SELECT rowid, * FROM teams{where_sql}
            ORDER BY team_name
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        columns = ['rowid'] + [desc[0] for desc in cursor.description][1:]
        teams = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return {"teams": teams, "total": total}
    except Exception as e:
        return {"teams": [], "total": 0, "error": str(e)}

def get_all_players(limit=100, offset=0, league=None, age_group=None, search=None, position=None, gender=None):
    """Get players from database with filtering"""
    if not DATABASE_PATH.exists():
        return {"players": [], "total": 0}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        # Check if players table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
        if not cursor.fetchone():
            conn.close()
            return {"players": [], "total": 0}
        
        # Build query
        where_clauses = []
        params = []
        
        if league:
            where_clauses.append("league LIKE ?")
            params.append(f"%{league}%")
        if age_group:
            # Handle both G13 and 13G formats
            age_formats = normalize_age_group_for_sql(age_group)
            if len(age_formats) == 1:
                where_clauses.append("age_group = ?")
                params.append(age_group)
            else:
                placeholders = " OR ".join(["age_group = ?" for _ in age_formats])
                where_clauses.append(f"({placeholders})")
                params.extend(age_formats)
        if position:
            # Use LIKE for partial matching (e.g., "D" matches "Defender")
            where_clauses.append("position LIKE ?")
            params.append(f"{position}%")
        if gender:
            if gender.lower() in ['girls', 'g']:
                where_clauses.append("age_group LIKE 'G%'")
            elif gender.lower() in ['boys', 'b']:
                where_clauses.append("age_group LIKE 'B%'")
        if search:
            where_clauses.append("(player_name LIKE ? OR team_name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM players{where_sql}", params)
        total = cursor.fetchone()[0]
        
        # Get players with rowid for editing
        cursor.execute(f"""
            SELECT rowid, * FROM players{where_sql}
            ORDER BY player_name
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        columns = ['rowid'] + [desc[0] for desc in cursor.description][1:]
        players = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return {"players": players, "total": total}
    except Exception as e:
        return {"players": [], "total": 0, "error": str(e)}

# ============================================================================
# DATABASE UPDATE FUNCTIONS
# ============================================================================

def update_team(rowid, updates):
    """Update a team in the database"""
    if not DATABASE_PATH.exists():
        return {"success": False, "error": "Database not found"}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        # Build update query
        set_clauses = []
        params = []
        for key, value in updates.items():
            if key not in ['rowid', 'id']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return {"success": False, "error": "No valid fields to update"}
        
        params.append(rowid)
        cursor.execute(f"UPDATE teams SET {', '.join(set_clauses)} WHERE rowid = ?", params)
        conn.commit()
        updated = cursor.rowcount
        conn.close()
        
        return {"success": updated > 0, "updated": updated}
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_player(rowid, updates):
    """Update a player in the database"""
    if not DATABASE_PATH.exists():
        return {"success": False, "error": "Database not found"}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        # Get actual columns in the players table
        cursor.execute("PRAGMA table_info(players)")
        valid_columns = {row[1] for row in cursor.fetchall()}
        
        set_clauses = []
        params = []
        skipped = []
        for key, value in updates.items():
            if key in ['rowid', 'id']:
                continue
            # Only update columns that exist in the table
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            else:
                skipped.append(key)
        
        if not set_clauses:
            error_msg = "No valid fields to update"
            if skipped:
                error_msg += f". Columns not in table: {', '.join(skipped)}"
            return {"success": False, "error": error_msg}
        
        params.append(rowid)
        cursor.execute(f"UPDATE players SET {', '.join(set_clauses)} WHERE rowid = ?", params)
        conn.commit()
        updated = cursor.rowcount
        conn.close()
        
        result = {"success": updated > 0, "updated": updated}
        if skipped:
            result["warning"] = f"Skipped columns not in table: {', '.join(skipped)}"
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_game(rowid, updates):
    """Update a game in the database"""
    if not DATABASE_PATH.exists():
        return {"success": False, "error": "Database not found"}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        set_clauses = []
        params = []
        for key, value in updates.items():
            if key not in ['rowid', 'id']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return {"success": False, "error": "No valid fields to update"}
        
        params.append(rowid)
        cursor.execute(f"UPDATE games SET {', '.join(set_clauses)} WHERE rowid = ?", params)
        conn.commit()
        updated = cursor.rowcount
        conn.close()
        
        return {"success": updated > 0, "updated": updated}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_game(rowid):
    """Delete a game from the database"""
    if not DATABASE_PATH.exists():
        return {"success": False, "error": "Database not found"}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM games WHERE rowid = ?", [rowid])
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        
        return {"success": deleted > 0, "deleted": deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_all_games(limit=100, offset=0, league=None, age_group=None, search=None, status=None, gender=None, sort='desc'):
    """Get games from database with filtering and sorting"""
    if not DATABASE_PATH.exists():
        return {"games": [], "total": 0}
    
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        
        # Check if games table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        if not cursor.fetchone():
            conn.close()
            return {"games": [], "total": 0}
        
        # Check if game_date_iso column exists
        cursor.execute("PRAGMA table_info(games)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        has_iso_column = 'game_date_iso' in column_names
        
        # Build query
        where_clauses = []
        params = []
        
        if league:
            where_clauses.append("league LIKE ?")
            params.append(f"%{league}%")
        if age_group:
            # Handle both G13 and 13G formats
            age_formats = normalize_age_group_for_sql(age_group)
            if len(age_formats) == 1:
                where_clauses.append("age_group = ?")
                params.append(age_group)
            else:
                placeholders = " OR ".join(["age_group = ?" for _ in age_formats])
                where_clauses.append(f"({placeholders})")
                params.extend(age_formats)
        if status:
            where_clauses.append("game_status = ?")
            params.append(status)
        if gender:
            if gender.lower() in ['girls', 'g']:
                where_clauses.append("age_group LIKE 'G%'")
            elif gender.lower() in ['boys', 'b']:
                where_clauses.append("age_group LIKE 'B%'")
        if search:
            where_clauses.append("(home_team LIKE ? OR away_team LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM games{where_sql}", params)
        total = cursor.fetchone()[0]
        
        # Use game_date_iso for sorting if available
        if has_iso_column:
            sort_order = "ASC" if sort == 'asc' else "DESC"
            cursor.execute(f"""
                SELECT rowid, * FROM games{where_sql}
                ORDER BY COALESCE(game_date_iso, game_date) {sort_order}
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            
            columns = ['rowid'] + [desc[0] for desc in cursor.description][1:]
            games = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            # Fallback: Get all and sort in Python
            cursor.execute(f"SELECT rowid, * FROM games{where_sql}", params)
            columns = ['rowid'] + [desc[0] for desc in cursor.description][1:]
            all_games = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Parse and sort dates properly
            def parse_date_for_sort(game):
                date_str = game.get('game_date', '')
                if not date_str:
                    return "0000-00-00"
                date_str = str(date_str).strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
                    return date_str[:10]
                for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%m-%d-%Y"]:
                    try:
                        return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                    except:
                        continue
                try:
                    parts = date_str.replace(',', '').split()
                    if len(parts) >= 3:
                        month_map = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                                    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
                        month = month_map.get(parts[0][:3].lower(), '01')
                        day = parts[1].zfill(2)
                        year = parts[2] if len(parts[2]) == 4 else '2025'
                        return f"{year}-{month}-{day}"
                except:
                    pass
                return "0000-00-00"
            
            reverse_sort = (sort != 'asc')
            sorted_games = sorted(all_games, key=parse_date_for_sort, reverse=reverse_sort)
            games = sorted_games[offset:offset + limit]
        
        conn.close()
        return {"games": games, "total": total}
    except Exception as e:
        return {"games": [], "total": 0, "error": str(e)}

def get_users():
    """Get all users from persistent file"""
    return load_users()

def authenticate_user(username, password):
    """Authenticate a user by username and password"""
    users = load_users()
    
    for user in users:
        if user["username"].lower() == username.lower():
            if user.get("password") == password:
                # Update last login
                user["last_login"] = datetime.now().isoformat()
                save_users(users)
                # Return user without password
                safe_user = {k: v for k, v in user.items() if k != "password"}
                return {"success": True, "user": safe_user}
            else:
                return {"success": False, "error": "Invalid password"}
    
    return {"success": False, "error": "User not found"}

def get_user_by_email(email):
    """Find a user by email"""
    users = load_users()
    
    for user in users:
        if user.get("email", "").lower() == email.lower():
            return user
    return None

def get_user_data(username):
    """Get user's saved data (players, badges, teams)"""
    config = load_config()
    user_data = config.get("user_data", {})
    return user_data.get(username, {"players": [], "badges": {}, "myTeams": []})

def save_user_data(username, data):
    """Save user's data"""
    config = load_config()
    if "user_data" not in config:
        config["user_data"] = {}
    config["user_data"][username] = data
    save_config(config)
    return {"success": True}

def add_user(username, email="", account_type="free", notes="", password=""):
    """Add a new user"""
    users = load_users()
    
    # Check for duplicate
    if any(u["username"].lower() == username.lower() for u in users):
        return {"success": False, "error": f"User '{username}' already exists"}
    
    # Password required for free and pro accounts
    if account_type in ["free", "pro"] and not password:
        return {"success": False, "error": f"Password required for {account_type} accounts"}
    
    # Generate unique ID
    max_id = max([u.get("id", 0) for u in users], default=0)
    
    user = {
        "id": max_id + 1,
        "username": username,
        "email": email,
        "password": password,
        "account_type": account_type,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "teams_saved": 0,
        "games_submitted": 0
    }
    
    users.append(user)
    save_users(users)
    
    return {"success": True, "user": user}

def update_user(user_id, updates):
    """Update a user"""
    users = load_users()
    
    for user in users:
        if user["id"] == user_id:
            for key, value in updates.items():
                if key != "id":
                    user[key] = value
            save_users(users)
            return {"success": True, "user": user}
    
    return {"success": False, "error": "User not found"}

def delete_user(user_id):
    """Delete a user"""
    users = load_users()
    
    original_count = len(users)
    users = [u for u in users if u["id"] != user_id]
    
    if len(users) == original_count:
        return {"success": False, "error": "User not found"}
    
    save_users(users)
    return {"success": True}

# ============================================================================
# SCHEDULE MANAGEMENT
# ============================================================================

# Schedule settings file
SCHEDULE_SETTINGS_FILE = SCRAPERS_FOLDER / "schedule_settings.json"

# Default schedule settings
DEFAULT_SCHEDULE_SETTINGS = {
    "scrapers": {
        "ECNL": {"enabled": True, "name": "ECNL + ECNL RL", "headless": True},
        "GA": {"enabled": True, "name": "Girls Academy", "headless": True},
        "ASPIRE": {"enabled": True, "name": "ASPIRE", "headless": True},
    },
    "schedule": {
        "saturday_enabled": True,
        "saturday_time": "22:00",
        "sunday_enabled": True,
        "sunday_time": "22:00",
        "monday_followup": True,
        "monday_time": "07:00",
        "tuesday_cleanup": True,
        "tuesday_time": "07:00",
    },
    "options": {
        "run_if_missed": True,
        "retry_count": 3,
        "retry_interval_hours": 1,
    }
}

def load_schedule_settings():
    """Load schedule settings from file"""
    if SCHEDULE_SETTINGS_FILE.exists():
        try:
            with open(SCHEDULE_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Merge with defaults for any missing keys
                for key in DEFAULT_SCHEDULE_SETTINGS:
                    if key not in settings:
                        settings[key] = DEFAULT_SCHEDULE_SETTINGS[key]
                return settings
        except:
            pass
    return DEFAULT_SCHEDULE_SETTINGS.copy()

def save_schedule_settings(settings):
    """Save schedule settings to file"""
    try:
        with open(SCHEDULE_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_scraper_logs(scraper_id=None, lines=100):
    """Get recent scraper log entries"""
    logs = {}
    log_files = {
        "schedule": SCRAPERS_FOLDER / "scraper_schedule.log",
        "ecnl": SCRAPERS_FOLDER / "scraper_ecnl.log",
        "ga": SCRAPERS_FOLDER / "scraper_ga.log",
        "aspire": SCRAPERS_FOLDER / "scraper_aspire.log",
    }

    files_to_read = {scraper_id: log_files[scraper_id]} if scraper_id and scraper_id in log_files else log_files

    for name, log_path in files_to_read.items():
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    logs[name] = {
                        "path": str(log_path),
                        "lines": all_lines[-lines:] if len(all_lines) > lines else all_lines,
                        "total_lines": len(all_lines),
                        "last_modified": datetime.fromtimestamp(log_path.stat().st_mtime).isoformat()
                    }
            except Exception as e:
                logs[name] = {"error": str(e)}
        else:
            logs[name] = {"exists": False, "path": str(log_path)}

    return logs

def get_scrape_reports():
    """Get list of scrape report files"""
    reports = []
    report_pattern = SCRAPERS_FOLDER / "scrape_report_*.txt"

    for report_file in sorted(SCRAPERS_FOLDER.glob("scrape_report_*.txt"), reverse=True)[:10]:
        try:
            with open(report_file, 'r') as f:
                content = f.read()
            reports.append({
                "filename": report_file.name,
                "date": report_file.name.replace("scrape_report_", "").replace(".txt", ""),
                "content": content,
                "size": report_file.stat().st_size,
                "modified": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat()
            })
        except Exception as e:
            reports.append({"filename": report_file.name, "error": str(e)})

    return reports

def get_scheduled_tasks():
    """Get status of Windows scheduled tasks for scraping"""
    import subprocess

    tasks = []
    # Updated task names for smart schedule
    task_names = [
        "Seedline Saturday Scrape",
        "Seedline Sunday Scrape",
        "Seedline Monday Follow-up",
        "Seedline Tuesday Cleanup",
        # Legacy tasks (may still exist)
        "Seedline Daily Scrape - Evening",
        "Seedline Daily Scrape - Morning",
        "Seedline Weekly Deep Scan"
    ]

    for task_name in task_names:
        task_info = {
            "name": task_name,
            "exists": False,
            "state": "Unknown",
            "last_run": None,
            "next_run": None,
            "last_result": None
        }

        try:
            # Get task info using PowerShell
            result = subprocess.run(
                ["powershell", "-Command",
                 f"Get-ScheduledTask -TaskName '{task_name}' -TaskPath '\\Seedline\\' -ErrorAction Stop | "
                 f"Select-Object TaskName, State | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                task_info["exists"] = True
                task_info["state"] = data.get("State", 3)  # 3 = Ready

                # Map state number to string
                state_map = {0: "Unknown", 1: "Disabled", 2: "Queued", 3: "Ready", 4: "Running"}
                task_info["state"] = state_map.get(task_info["state"], str(task_info["state"]))

                # Get additional info
                result2 = subprocess.run(
                    ["powershell", "-Command",
                     f"Get-ScheduledTaskInfo -TaskName '{task_name}' -TaskPath '\\Seedline\\' -ErrorAction Stop | "
                     f"Select-Object LastRunTime, NextRunTime, LastTaskResult | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=10
                )

                if result2.returncode == 0 and result2.stdout.strip():
                    info_data = json.loads(result2.stdout)
                    task_info["last_run"] = info_data.get("LastRunTime")
                    task_info["next_run"] = info_data.get("NextRunTime")
                    task_info["last_result"] = info_data.get("LastTaskResult", 0)

                tasks.append(task_info)

        except Exception as e:
            task_info["error"] = str(e)

    # Filter to only existing tasks
    return [t for t in tasks if t.get("exists", False)]

def run_scheduled_task(task_name):
    """Run a scheduled task immediately"""
    import subprocess

    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"Start-ScheduledTask -TaskName '{task_name}' -TaskPath '\\Seedline\\'"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            return {"success": True, "message": f"Started {task_name}"}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def toggle_scheduled_task(task_name, enable):
    """Enable or disable a scheduled task"""
    import subprocess

    action = "Enable" if enable else "Disable"

    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"{action}-ScheduledTask -TaskName '{task_name}' -TaskPath '\\Seedline\\'"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            return {"success": True, "message": f"{action}d {task_name}"}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_games_needing_scrape():
    """Get count of games that need scraping (missing results from past 7 days)"""
    if not DATABASE_PATH.exists():
        return {"error": "Database not found"}

    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()

        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Games missing results from past week
        cursor.execute("""
            SELECT COUNT(*) FROM games
            WHERE game_date >= ? AND game_date <= ?
            AND (home_score IS NULL OR away_score IS NULL)
        """, (week_ago, today))
        missing_results = cursor.fetchone()[0]

        # Today's games
        cursor.execute("""
            SELECT COUNT(*) FROM games WHERE game_date = ?
        """, (today,))
        today_games = cursor.fetchone()[0]

        # Yesterday's games
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COUNT(*) FROM games WHERE game_date = ?
        """, (yesterday,))
        yesterday_games = cursor.fetchone()[0]

        # By league
        cursor.execute("""
            SELECT league, COUNT(*) FROM games
            WHERE game_date >= ? AND game_date <= ?
            AND (home_score IS NULL OR away_score IS NULL)
            GROUP BY league
        """, (week_ago, today))
        by_league = dict(cursor.fetchall())

        conn.close()

        return {
            "missing_results": missing_results,
            "today_games": today_games,
            "yesterday_games": yesterday_games,
            "by_league": by_league
        }
    except Exception as e:
        return {"error": str(e)}

def run_scrape_now(scrape_type="full"):
    """Run the scheduled scraper immediately"""
    scraper_path = SCRAPERS_FOLDER / "scheduled_scraper.py"

    if not scraper_path.exists():
        return {"success": False, "error": f"Scheduled scraper not found: {scraper_path}"}

    try:
        args = []
        if scrape_type == "missing":
            args.append("--missing-only")
        elif scrape_type == "today":
            args.append("--today-only")
        elif scrape_type == "ecnl":
            args.append("--ecnl-only")
        elif scrape_type == "ga":
            args.append("--ga-only")
        elif scrape_type == "aspire":
            args.append("--aspire-only")

        # Open in a new CMD window
        if sys.platform == 'win32':
            window_title = f"Seedline - Scheduled Scrape ({scrape_type})"
            python_cmd = f'"{sys.executable}" -X utf8 -u "{scraper_path}" {" ".join(args)}'
            full_cmd = f'cd /d "{scraper_path.parent}" && {python_cmd} && echo. && echo Scrape complete. Press any key... && pause'
            start_cmd = f'start "{window_title}" cmd /k "{full_cmd}"'
            os.system(start_cmd)
            return {"success": True, "message": f"Started {scrape_type} scrape in new window"}
        else:
            # Run in background on non-Windows
            subprocess.Popen(
                [sys.executable, str(scraper_path)] + args,
                cwd=str(scraper_path.parent)
            )
            return {"success": True, "message": f"Started {scrape_type} scrape"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# SCRAPER MANAGEMENT
# ============================================================================

scraper_processes = {}
scraper_output = {}

def get_scraper_status():
    """Get status of all scrapers"""
    config = load_config()
    history = config.get("scraper_history", [])
    
    status = []
    for key, scraper in SCRAPERS.items():
        # Find last run from history
        last_runs = [h for h in history if h.get("scraper") == key]
        last_run = last_runs[-1] if last_runs else None
        
        # Check if running - handle both subprocess and CMD window modes
        # For CMD windows, process is set to None so we can't track it
        is_running = False
        if key in scraper_processes:
            proc = scraper_processes[key]
            if proc is not None and hasattr(proc, 'poll'):
                is_running = proc.poll() is None
            # If proc is None (CMD window), we can't track it, so assume not running
        
        status.append({
            "id": key,
            "name": scraper["name"],
            "description": scraper["description"],
            "path": str(scraper["path"]),
            "exists": scraper["path"].exists(),
            "running": is_running,
            "last_run": last_run.get("started_at") if last_run else None,
            "last_status": last_run.get("status") if last_run else None,
            "last_duration": last_run.get("duration") if last_run else None
        })
    
    return status

def run_scraper(scraper_id, settings=None):
    """Run a scraper in a visible CMD window (Windows) or terminal"""
    if scraper_id not in SCRAPERS:
        return {"success": False, "error": f"Unknown scraper: {scraper_id}"}
    
    scraper = SCRAPERS[scraper_id]
    scraper_path = scraper["path"]
    
    # Check if scraper file exists
    if not scraper_path.exists():
        return {"success": False, "error": f"Scraper file not found: {scraper_path}\n\nPlease check the scraper path in Settings."}
    
    if scraper_id in scraper_processes:
        proc = scraper_processes[scraper_id]
        if proc is not None and hasattr(proc, 'poll') and proc.poll() is None:
            return {"success": False, "error": "Scraper is already running"}
    
    # Build args from settings if provided
    args = []
    if settings:
        # Always add --no-confirm when run from admin UI
        args.append('--no-confirm')
        
        # Handle GA Events scraper specially
        if scraper_id == 'ga_events':
            events_mode = settings.get('events_mode', 'scrape')
            if events_mode == 'discover':
                args.append('--discover')
            elif events_mode == 'scrape-all':
                args.append('--scrape-all')
            else:  # 'scrape' (default - active events)
                args.append('--scrape')
        elif scraper_id == 'ecnl':
            # ECNL-specific settings (v2)
            # Scrape mode
            scrape_mode = settings.get('scrape_mode', 'pending')
            if scrape_mode == 'all':
                args.append('--scrape-all')
            elif scrape_mode == 'reset':
                # Reset status and scrape all
                args.append('--reset-status')
                args.append('--scrape')
            else:
                args.append('--scrape')
            
            # League selection
            ecnl_league = settings.get('ecnl_league', 'both')
            if ecnl_league and ecnl_league != 'both':
                args.extend(['--league', ecnl_league])
            
            # Gender settings
            if settings.get('girls') and settings.get('boys'):
                args.extend(['--gender', 'both'])
            elif settings.get('girls'):
                args.extend(['--gender', 'girls'])
            elif settings.get('boys'):
                args.extend(['--gender', 'boys'])
            
            # Age groups
            age_groups = settings.get('age_groups', [])
            if age_groups:
                args.extend(['--ages', ','.join(age_groups)])
            
            # Include players
            if settings.get('include_players'):
                args.append('--players')
            
            # Verbose
            if settings.get('verbose'):
                args.append('--verbose')
        elif scraper_id == 'npl':
            # NPL-specific settings
            # Scrape mode (pending, all, reset)
            scrape_mode = settings.get('scrape_mode', 'pending')
            if scrape_mode == 'all':
                args.append('--scrape-all')
            elif scrape_mode == 'reset':
                args.append('--reset-status')
                args.append('--scrape')
            else:
                args.append('--scrape')  # pending only (default)
            
            # Tier selection (NPL, Sub-NPL, or all)
            npl_tier = settings.get('npl_tier', 'all')
            if npl_tier and npl_tier != 'all':
                args.extend(['--tier', npl_tier])
            
            # Region selection
            npl_region = settings.get('npl_region', '')
            if npl_region:
                args.extend(['--region', npl_region])
            
            # Specific league name
            npl_league = settings.get('npl_league', '')
            if npl_league:
                args.extend(['--league', npl_league])
            
            # Gender settings
            if settings.get('girls') and settings.get('boys'):
                args.extend(['--gender', 'both'])
            elif settings.get('girls'):
                args.extend(['--gender', 'girls'])
            elif settings.get('boys'):
                args.extend(['--gender', 'boys'])
            
            # Time filter
            time_filter = settings.get('time_filter', 'all')
            if time_filter and time_filter != 'all':
                args.extend(['--time', time_filter])
                # Days for last_days filter
                if time_filter == 'last_days':
                    days = settings.get('days', 90)
                    args.extend(['--days', str(days)])
            
            # Headless mode
            if settings.get('headless'):
                args.append('--headless')
            
            # Screenshots
            if settings.get('no_screenshots'):
                args.append('--no-screenshots')
            
            # Verbose/Debug
            if settings.get('verbose'):
                args.append('--verbose')
        else:
            # Regular scraper settings
            # Gender settings
            if settings.get('girls') and settings.get('boys'):
                args.extend(['--gender', 'both'])
            elif settings.get('girls'):
                args.extend(['--gender', 'girls'])
            elif settings.get('boys'):
                args.extend(['--gender', 'boys'])
            
            # Age groups
            age_groups = settings.get('age_groups', [])
            if age_groups:
                args.extend(['--ages', ','.join(age_groups)])
            
            # Date range
            date_range = settings.get('date_range', '90')
            if date_range != 'all':
                args.extend(['--days', str(date_range)])
            
            # Include players
            if settings.get('include_players'):
                args.append('--players')
            
            # Verbose
            if settings.get('verbose'):
                args.append('--verbose')
    else:
        # Even without settings, add --no-confirm for admin UI
        args.append('--no-confirm')
    
    # Start process
    try:
        # Initialize output for dashboard display
        scraper_output[scraper_id] = [
            f"[{datetime.now().strftime('%H:%M:%S')}] ═══════════════════════════════════════",
            f"[{datetime.now().strftime('%H:%M:%S')}] Starting {scraper['name']}",
            f"[{datetime.now().strftime('%H:%M:%S')}] ═══════════════════════════════════════",
            f"[{datetime.now().strftime('%H:%M:%S')}] Scraper file: {scraper_path}",
            f"[{datetime.now().strftime('%H:%M:%S')}] Working dir: {scraper_path.parent}",
        ]
        
        # Build the Python command
        python_cmd = f'"{sys.executable}" -X utf8 -u "{scraper_path}" {" ".join(args)}'
        
        # On Windows, open a new visible CMD window
        if sys.platform == 'win32':
            # Use 'start' to open a new CMD window
            # /k keeps the window open after command finishes
            # Title the window with the scraper name
            window_title = f"Seedline - {scraper['name']}"
            
            # Build the full command for CMD
            # cd to working directory, then run python script, then pause
            full_cmd = f'cd /d "{scraper_path.parent}" && {python_cmd} && echo. && echo ════════════════════════════════════════ && echo Scraper finished. Press any key to close... && pause'
            
            # Use os.system with 'start' to open new window
            # This runs asynchronously and opens a visible CMD window
            start_cmd = f'start "{window_title}" cmd /k "{full_cmd}"'
            
            scraper_output[scraper_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] Opening CMD window...")
            scraper_output[scraper_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] Command: {python_cmd}")
            scraper_output[scraper_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] ───────────────────────────────────────")
            scraper_output[scraper_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] Output will appear in the CMD window.")
            scraper_output[scraper_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] You can interact with the window directly.")
            
            # Run the start command (this returns immediately)
            os.system(start_cmd)
            
            # We can't easily track the subprocess when using 'start cmd'
            # So we use a dummy process for status tracking
            scraper_processes[scraper_id] = None
            
        else:
            # On Mac/Linux, try to open a terminal window
            # This varies by system, so fall back to background process if needed
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            cmd = [sys.executable, "-X", "utf8", "-u", str(scraper_path)] + args
            
            # Try to open in a new terminal (macOS)
            if sys.platform == 'darwin':
                # macOS - use osascript to open Terminal
                script_cmd = f'cd "{scraper_path.parent}" && {python_cmd}'
                apple_script = f'''tell app "Terminal" to do script "{script_cmd}"'''
                os.system(f"osascript -e '{apple_script}'")
                scraper_processes[scraper_id] = None
            else:
                # Linux - try common terminal emulators
                terminals = ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal']
                opened = False
                for term in terminals:
                    try:
                        if term == 'gnome-terminal':
                            subprocess.Popen([term, '--', 'bash', '-c', f'cd "{scraper_path.parent}" && {python_cmd}; read -p "Press Enter to close..."'])
                        else:
                            subprocess.Popen([term, '-e', f'bash -c "cd \\"{scraper_path.parent}\\" && {python_cmd}; read -p \\"Press Enter to close...\\""'])
                        opened = True
                        scraper_processes[scraper_id] = None
                        break
                    except FileNotFoundError:
                        continue
                
                if not opened:
                    # Fall back to background process
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        bufsize=1,
                        cwd=str(scraper_path.parent),
                        env=env
                    )
                    scraper_processes[scraper_id] = process
                    scraper_output[scraper_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] Running in background (no terminal available)")
        
        # Log start
        config = load_config()
        config.setdefault("scraper_history", []).append({
            "scraper": scraper_id,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "args": args,
            "settings": settings
        })
        save_config(config)
        
        return {"success": True, "message": f"Started {scraper['name']} in CMD window"}
    except Exception as e:
        scraper_output[scraper_id] = scraper_output.get(scraper_id, []) + [f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}"]
        return {"success": False, "error": str(e)}

def get_scraper_output(scraper_id):
    """Get output from a running scraper"""
    return scraper_output.get(scraper_id, [])

def stop_scraper(scraper_id):
    """Stop a running scraper"""
    if scraper_id in scraper_processes:
        process = scraper_processes[scraper_id]
        if process.poll() is None:
            process.terminate()
            return {"success": True, "message": "Scraper stopped"}
    return {"success": False, "error": "Scraper not running"}

# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def run_ranker():
    """Run the team ranker to generate rankings"""
    if not RANKER_PATH.exists():
        return {"success": False, "error": f"Ranker not found: {RANKER_PATH}"}
    
    try:
        # Set UTF-8 encoding to avoid Windows charmap errors
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSSTDIO'] = '0'  # Force UTF-8 on Windows
        
        # Use Popen for better control over encoding on Windows
        # Note: team_ranker_v38.py uses positional [db_path] argument, not --db flag
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", str(RANKER_PATH), str(DATABASE_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(RANKER_PATH.parent),
            env=env
        )
        
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=300)
            # Decode with error handling
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            return {
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr if process.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            process.kill()
            return {"success": False, "error": "Ranker timed out after 5 minutes"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def export_to_react():
    """Export rankings and players to React app"""
    results = {"rankings": None, "players": None}
    
    # Check if rankings file exists
    if RANKINGS_OUTPUT.exists():
        try:
            # Copy to React app public folder
            react_public = REACT_APP_PATH / "public"
            if react_public.exists():
                import shutil
                dest = react_public / "rankings_for_react.json"
                shutil.copy(RANKINGS_OUTPUT, dest)
                results["rankings"] = {"success": True, "path": str(dest)}
            else:
                results["rankings"] = {"success": False, "error": "React public folder not found"}
        except Exception as e:
            results["rankings"] = {"success": False, "error": str(e)}
    else:
        results["rankings"] = {"success": False, "error": "Rankings file not found. Run the ranker first."}
    
    # Export players
    try:
        export_script = REACT_APP_PATH / "export_players.py"
        if export_script.exists():
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.Popen(
                [sys.executable, "-X", "utf8", str(export_script), "--db", str(DATABASE_PATH), "--react", str(REACT_APP_PATH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=120)
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                
                results["players"] = {
                    "success": process.returncode == 0,
                    "output": stdout,
                    "error": stderr if process.returncode != 0 else None
                }
            except subprocess.TimeoutExpired:
                process.kill()
                results["players"] = {"success": False, "error": "Player export timed out"}
        else:
            results["players"] = {"success": False, "error": "export_players.py not found"}
    except Exception as e:
        results["players"] = {"success": False, "error": str(e)}
    
    return results

def launch_react_app():
    """Launch the React app in a new terminal window"""
    try:
        react_path = REACT_APP_PATH
        
        if not react_path.exists():
            return {"success": False, "error": f"React app folder not found: {react_path}"}
        
        # Check if package.json exists
        package_json = react_path / "package.json"
        if not package_json.exists():
            return {"success": False, "error": "package.json not found in React app folder"}
        
        # On Windows, open a new CMD window that navigates to the folder and runs npm commands
        if sys.platform == 'win32':
            # Create a batch command that:
            # 1. Changes to the React app directory
            # 2. Checks if node_modules exists, if not runs npm install
            # 3. Runs npm run dev
            batch_cmd = f'''
@echo off
title Seedline React App
color 0A
cd /d "{react_path}"
echo.
echo  ========================================
echo   SEEDLINE REACT APP
echo  ========================================
echo.
echo  Directory: {react_path}
echo.
if not exist "node_modules" (
    echo  Installing dependencies...
    echo.
    call npm install
    echo.
)
echo  Starting development server...
echo.
call npm run dev
pause
'''
            # Write temporary batch file
            batch_file = react_path / "_launch_react_temp.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_cmd)
            
            # Launch in new CMD window
            subprocess.Popen(
                ['cmd', '/c', 'start', 'cmd', '/k', str(batch_file)],
                cwd=str(react_path),
                shell=True
            )
            
            return {"success": True, "message": "React app launching in new window...", "path": str(react_path)}
        else:
            # On Mac/Linux, try to open a terminal
            subprocess.Popen(
                ['bash', '-c', f'cd "{react_path}" && npm install && npm run dev'],
                cwd=str(react_path)
            )
            return {"success": True, "message": "React app launching...", "path": str(react_path)}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# TEAM RATINGS - Claude Moderation & CRUD Functions
# ============================================================================

import urllib.request
import ssl

# Claude API configuration for content moderation
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = 'claude-sonnet-4-20250514'  # Fast model for moderation

# Rating categories (must match frontend and database columns)
RATING_CATEGORIES = [
    'possession', 'direct_attack', 'passing', 'fast', 'shooting', 'footwork', 'physical',
    'coaching', 'allstar_players', 'player_sportsmanship', 'parent_sportsmanship',
    'strong_defense', 'strong_midfield', 'strong_offense'
]


def init_ratings_table():
    """Initialize the team_ratings table in the activity database."""
    if not ACTIVITY_TRACKING_ENABLED:
        print("[RATINGS] Activity tracking not enabled - skipping ratings table init")
        return

    try:
        conn = sqlite3.connect(str(ACTIVITY_DB_PATH))
        cursor = conn.cursor()

        # Create the team_ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                team_name TEXT NOT NULL,
                team_age_group TEXT,
                team_league TEXT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                relationship TEXT NOT NULL DEFAULT 'neither',
                comment TEXT NOT NULL,
                rating_possession INTEGER CHECK (rating_possession IS NULL OR rating_possession BETWEEN 1 AND 5),
                rating_direct_attack INTEGER CHECK (rating_direct_attack IS NULL OR rating_direct_attack BETWEEN 1 AND 5),
                rating_passing INTEGER CHECK (rating_passing IS NULL OR rating_passing BETWEEN 1 AND 5),
                rating_fast INTEGER CHECK (rating_fast IS NULL OR rating_fast BETWEEN 1 AND 5),
                rating_shooting INTEGER CHECK (rating_shooting IS NULL OR rating_shooting BETWEEN 1 AND 5),
                rating_footwork INTEGER CHECK (rating_footwork IS NULL OR rating_footwork BETWEEN 1 AND 5),
                rating_physical INTEGER CHECK (rating_physical IS NULL OR rating_physical BETWEEN 1 AND 5),
                rating_coaching INTEGER CHECK (rating_coaching IS NULL OR rating_coaching BETWEEN 1 AND 5),
                rating_allstar_players INTEGER CHECK (rating_allstar_players IS NULL OR rating_allstar_players BETWEEN 1 AND 5),
                rating_player_sportsmanship INTEGER CHECK (rating_player_sportsmanship IS NULL OR rating_player_sportsmanship BETWEEN 1 AND 5),
                rating_parent_sportsmanship INTEGER CHECK (rating_parent_sportsmanship IS NULL OR rating_parent_sportsmanship BETWEEN 1 AND 5),
                rating_strong_defense INTEGER CHECK (rating_strong_defense IS NULL OR rating_strong_defense BETWEEN 1 AND 5),
                rating_strong_midfield INTEGER CHECK (rating_strong_midfield IS NULL OR rating_strong_midfield BETWEEN 1 AND 5),
                rating_strong_offense INTEGER CHECK (rating_strong_offense IS NULL OR rating_strong_offense BETWEEN 1 AND 5),
                moderation_status TEXT DEFAULT 'pending',
                moderation_reason TEXT,
                moderated_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_team ON team_ratings(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_user ON team_ratings(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_status ON team_ratings(moderation_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_created ON team_ratings(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_team_approved ON team_ratings(team_id, moderation_status, is_deleted)')

        conn.commit()
        print("[RATINGS] Team ratings table initialized successfully")
    except Exception as e:
        print(f"[RATINGS] Error initializing ratings table: {e}")
    finally:
        conn.close()


def moderate_comment_with_claude(comment: str) -> dict:
    """
    Use Claude API to moderate comment content.

    Returns:
        {
            "approved": bool,
            "reason": str or None  # Reason if rejected
        }
    """
    if not ANTHROPIC_API_KEY:
        # If no API key, approve with warning (for development)
        print("[MODERATION] No ANTHROPIC_API_KEY - auto-approving comment (dev mode)")
        return {"approved": True, "reason": None}

    moderation_prompt = f"""You are a content moderator for a youth soccer team rating platform. Your job is to review comments about soccer teams and determine if they are appropriate for publication.

APPROVE comments that:
- Describe team playing style (e.g., "They play a possession-based game with strong midfield")
- Offer constructive observations about team strengths/weaknesses
- Are neutral or positive in tone
- Discuss coaching style or team culture professionally

REJECT comments that contain:
1. Foul language, profanity, or vulgar content
2. Personal attacks on specific players, coaches, or parents by name
3. Personal identifying information (phone numbers, addresses, emails)
4. Content that could be hurtful to child players (bullying, mocking, humiliation)
5. Defamatory or libelous statements
6. Content promoting violence or hate
7. Extremely negative generalizations about an entire team

The comment to review is:
<comment>
{comment}
</comment>

Respond in JSON format only:
{{"approved": true}}
OR
{{"approved": false, "reason": "Brief explanation of why this was rejected (one sentence)"}}

JSON response:"""

    try:
        request_data = json.dumps({
            "model": CLAUDE_MODEL,
            "max_tokens": 150,
            "messages": [{"role": "user", "content": moderation_prompt}]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            }
        )

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            result = json.loads(response.read().decode())
            content = result.get("content", [{}])[0].get("text", "")

            # Parse JSON response from Claude - handle markdown code blocks
            if "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]

            moderation_result = json.loads(content.strip())
            print(f"[MODERATION] Comment review result: {moderation_result}")
            return moderation_result

    except json.JSONDecodeError as e:
        print(f"[MODERATION] Failed to parse Claude response: {e}")
        return {"approved": False, "reason": "Moderation service returned invalid response - pending manual review"}
    except Exception as e:
        print(f"[MODERATION] Claude API error: {e}")
        # On API failure, mark as pending for manual review
        return {"approved": False, "reason": "Moderation service unavailable - pending manual review"}


def submit_team_rating(user_id: str, data: dict) -> dict:
    """Submit a new team rating with Claude moderation."""

    team_id = data.get('team_id')
    comment = data.get('comment', '').strip()
    relationship = data.get('relationship', 'neither')
    ratings = data.get('ratings', {})
    session_id = data.get('session_id')

    # Validate required fields
    if not team_id:
        return {"success": False, "error": "Team ID required"}

    if not comment or len(comment) < 10:
        return {"success": False, "error": "Comment must be at least 10 characters"}

    if len(comment) > 1000:
        return {"success": False, "error": "Comment must be less than 1000 characters"}

    if relationship not in ['my_team', 'followed', 'neither']:
        return {"success": False, "error": "Invalid relationship value"}

    if not ACTIVITY_TRACKING_ENABLED:
        return {"success": False, "error": "Rating system not available"}

    conn = sqlite3.connect(str(ACTIVITY_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Check for existing rating from this user for this team
        cursor.execute("""
            SELECT id FROM team_ratings
            WHERE user_id = ? AND team_id = ? AND is_deleted = 0
        """, (user_id, team_id))

        existing = cursor.fetchone()
        if existing:
            return {"success": False, "error": "You have already rated this team. Delete your existing rating first."}

        # Rate limit: max 10 new ratings per day
        cursor.execute("""
            SELECT COUNT(*) FROM team_ratings
            WHERE user_id = ? AND date(created_at) = date('now')
        """, (user_id,))

        daily_count = cursor.fetchone()[0]
        if daily_count >= 10:
            return {"success": False, "error": "Daily rating limit reached (10 per day)"}

        # Moderate comment with Claude
        moderation = moderate_comment_with_claude(comment)

        if not moderation.get('approved'):
            return {
                "success": False,
                "error": "Comment not approved",
                "moderation_reason": moderation.get('reason', 'Content policy violation'),
                "code": "MODERATION_REJECTED"
            }

        # Build insert with optional rating columns
        columns = ['team_id', 'team_name', 'team_age_group', 'team_league',
                   'user_id', 'session_id', 'relationship', 'comment',
                   'moderation_status', 'moderated_at']
        values = [team_id, data.get('team_name', ''), data.get('team_age_group'),
                  data.get('team_league'), user_id, session_id, relationship, comment,
                  'approved', datetime.now().isoformat()]

        # Add rating columns (only if provided and valid)
        for category in RATING_CATEGORIES:
            value = ratings.get(category)
            if value is not None:
                try:
                    int_value = int(value)
                    if not (1 <= int_value <= 5):
                        return {"success": False, "error": f"Invalid rating value for {category}: must be 1-5"}
                    columns.append(f'rating_{category}')
                    values.append(int_value)
                except (ValueError, TypeError):
                    return {"success": False, "error": f"Invalid rating value for {category}"}

        placeholders = ','.join(['?' for _ in values])
        column_list = ','.join(columns)

        cursor.execute(f"""
            INSERT INTO team_ratings ({column_list}) VALUES ({placeholders})
        """, values)

        rating_id = cursor.lastrowid
        conn.commit()

        print(f"[RATINGS] New rating {rating_id} submitted for team {team_id} by user {user_id}")
        return {"success": True, "rating_id": rating_id, "moderation_status": "approved"}

    except sqlite3.IntegrityError as e:
        print(f"[RATINGS] Integrity error: {e}")
        return {"success": False, "error": "You have already rated this team"}
    except Exception as e:
        print(f"[RATINGS] Error submitting rating: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_team_ratings(team_id: str, include_pending: bool = False) -> dict:
    """Get all approved ratings for a team with category averages."""

    if not ACTIVITY_TRACKING_ENABLED:
        return {"team_id": team_id, "total_ratings": 0, "averages": {}, "ratings": []}

    conn = sqlite3.connect(str(ACTIVITY_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Base query for approved ratings
        if include_pending:
            status_filter = "IN ('approved', 'pending')"
        else:
            status_filter = "= 'approved'"

        cursor.execute(f"""
            SELECT * FROM team_ratings
            WHERE team_id = ? AND moderation_status {status_filter} AND is_deleted = 0
            ORDER BY created_at DESC
        """, (team_id,))

        rows = cursor.fetchall()

        # Calculate category averages
        averages = {}
        for category in RATING_CATEGORIES:
            col_name = f'rating_{category}'
            values = [row[col_name] for row in rows if row[col_name] is not None]
            if values:
                averages[category] = round(sum(values) / len(values), 1)
            else:
                averages[category] = None

        # Format individual ratings
        ratings_list = []
        for row in rows:
            rating = {
                "id": row['id'],
                "relationship": row['relationship'],
                "comment": row['comment'],
                "created_at": row['created_at'],
                "moderation_status": row['moderation_status'],
                "ratings": {}
            }
            for category in RATING_CATEGORIES:
                col_name = f'rating_{category}'
                if row[col_name] is not None:
                    rating['ratings'][category] = row[col_name]
            ratings_list.append(rating)

        return {
            "team_id": team_id,
            "total_ratings": len(ratings_list),
            "averages": averages,
            "ratings": ratings_list
        }

    except Exception as e:
        print(f"[RATINGS] Error fetching ratings: {e}")
        return {"team_id": team_id, "total_ratings": 0, "averages": {}, "ratings": [], "error": str(e)}
    finally:
        conn.close()


def get_user_ratings(user_id: str) -> dict:
    """Get all ratings submitted by a user."""

    if not ACTIVITY_TRACKING_ENABLED:
        return {"ratings": [], "total": 0}

    conn = sqlite3.connect(str(ACTIVITY_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM team_ratings
            WHERE user_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """, (user_id,))

        rows = cursor.fetchall()

        ratings_list = []
        for row in rows:
            rating = {
                "id": row['id'],
                "team_id": row['team_id'],
                "team_name": row['team_name'],
                "team_age_group": row['team_age_group'],
                "team_league": row['team_league'],
                "relationship": row['relationship'],
                "comment": row['comment'],
                "moderation_status": row['moderation_status'],
                "moderation_reason": row['moderation_reason'],
                "created_at": row['created_at'],
                "ratings": {}
            }
            for category in RATING_CATEGORIES:
                col_name = f'rating_{category}'
                if row[col_name] is not None:
                    rating['ratings'][category] = row[col_name]
            ratings_list.append(rating)

        return {"ratings": ratings_list, "total": len(ratings_list)}

    except Exception as e:
        print(f"[RATINGS] Error fetching user ratings: {e}")
        return {"ratings": [], "total": 0, "error": str(e)}
    finally:
        conn.close()


def delete_team_rating(rating_id: str, user_id: str) -> dict:
    """Soft delete a rating (users can only delete their own)."""

    if not ACTIVITY_TRACKING_ENABLED:
        return {"success": False, "error": "Rating system not available"}

    conn = sqlite3.connect(str(ACTIVITY_DB_PATH))
    try:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT user_id FROM team_ratings WHERE id = ? AND is_deleted = 0
        """, (rating_id,))

        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Rating not found"}

        if row[0] != user_id:
            return {"success": False, "error": "Cannot delete another user's rating"}

        # Soft delete
        cursor.execute("""
            UPDATE team_ratings
            SET is_deleted = 1, deleted_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ?
        """, (rating_id,))

        conn.commit()
        print(f"[RATINGS] Rating {rating_id} deleted by user {user_id}")
        return {"success": True}

    except Exception as e:
        print(f"[RATINGS] Error deleting rating: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# HTTP SERVER
# ============================================================================

class AdminHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the admin API"""
    
    def _set_headers(self, status=200, content_type='application/json', extra_headers=None):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Session-ID')
        self.send_header('Access-Control-Expose-Headers', 'X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset')
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()

    def _get_client_ip(self):
        """Get client IP address, checking X-Forwarded-For for proxied requests."""
        forwarded = self.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        real_ip = self.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        return self.client_address[0] if self.client_address else 'unknown'

    def _get_auth_info(self):
        """Get authentication info from request headers."""
        if not ACTIVITY_TRACKING_ENABLED:
            return None, 'guest'
        headers = {k: v for k, v in self.headers.items()}
        user_info = get_auth_from_request(headers)
        if user_info:
            account_type = get_account_type_from_user(user_info, get_user_by_email)
            return user_info, account_type
        return None, 'guest'

    def _check_rate_limit(self, ip_address, account_type='guest'):
        """Check rate limit and return headers."""
        if not ACTIVITY_TRACKING_ENABLED:
            return True, 999, 60, {}
        allowed, remaining, reset = check_rate_limit(ip_address, account_type)
        headers = {
            'X-RateLimit-Limit': str(check_rate_limit.__code__.co_freevars),  # Will be fixed
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset)
        }
        return allowed, remaining, reset, headers
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # Helper to get single param value
        def get_param(name, default=None):
            values = params.get(name, [default])
            return values[0] if values else default
        
        try:
            # Debug: Print path for troubleshooting
            print(f"[DEBUG] Received path: '{path}'")

            if path == '/api/test-new':
                self._set_headers()
                self.wfile.write(json.dumps({"message": "New code is loaded!"}).encode())

            elif path == '/api/stats':
                self._set_headers()
                self.wfile.write(json.dumps(get_database_stats()).encode())
            
            elif path == '/api/scrapers':
                self._set_headers()
                self.wfile.write(json.dumps(get_scraper_status()).encode())
            
            elif path == '/api/scraper/output':
                scraper_id = get_param('id')
                self._set_headers()
                self.wfile.write(json.dumps(get_scraper_output(scraper_id)).encode())
            
            elif path == '/api/users':
                self._set_headers()
                self.wfile.write(json.dumps(get_users()).encode())

            elif path.startswith('/api/user/lookup'):
                # Look up user account type by email: GET /api/user/lookup?email=xxx
                email = get_param('email')
                if email:
                    user = get_user_by_email(email)
                    if user:
                        self._set_headers()
                        self.wfile.write(json.dumps({
                            "found": True,
                            "account_type": user.get("account_type", "free"),
                            "username": user.get("username", "")
                        }).encode())
                    else:
                        self._set_headers()
                        self.wfile.write(json.dumps({"found": False}).encode())
                else:
                    self._set_headers()
                    self.wfile.write(json.dumps({"error": "Email required"}).encode())

            elif path.startswith('/api/user/') and path.endswith('/data'):
                # Get user data: GET /api/user/<username>/data
                parts = path.split('/')
                username = parts[3]
                self._set_headers()
                self.wfile.write(json.dumps(get_user_data(username)).encode())
            
            elif path == '/api/filter-options':
                self._set_headers()
                self.wfile.write(json.dumps(get_filter_options()).encode())
            
            elif path == '/api/teams':
                limit = int(get_param('limit', 100))
                offset = int(get_param('offset', 0))
                league = get_param('league')
                age_group = get_param('age_group')
                gender = get_param('gender')
                search = get_param('search')
                self._set_headers()
                self.wfile.write(json.dumps(get_all_teams(limit, offset, league, age_group, search, gender)).encode())
            
            elif path == '/api/players':
                limit = int(get_param('limit', 100))
                offset = int(get_param('offset', 0))
                league = get_param('league')
                age_group = get_param('age_group')
                position = get_param('position')
                gender = get_param('gender')
                search = get_param('search')
                self._set_headers()
                self.wfile.write(json.dumps(get_all_players(limit, offset, league, age_group, search, position, gender)).encode())
            
            elif path == '/api/games':
                limit = int(get_param('limit', 100))
                offset = int(get_param('offset', 0))
                league = get_param('league')
                age_group = get_param('age_group')
                status = get_param('status')
                gender = get_param('gender')
                search = get_param('search')
                sort = get_param('sort', 'desc')
                self._set_headers()
                self.wfile.write(json.dumps(get_all_games(limit, offset, league, age_group, search, status, gender, sort)).encode())
            
            elif path == '/api/file-info':
                # Get file info for the Files & Folders page
                file_path = get_param('path')
                self._set_headers()
                
                if not file_path:
                    self.wfile.write(json.dumps({"error": "No path provided"}).encode())
                    return
                
                # Try multiple base paths
                possible_paths = [
                    SCRIPT_DIR / file_path,
                    SCRAPERS_FOLDER / file_path,
                    Path(file_path)
                ]
                
                file_info = {"exists": False, "path": file_path}
                
                for check_path in possible_paths:
                    if check_path.exists():
                        file_info["exists"] = True
                        file_info["full_path"] = str(check_path)
                        
                        stat = check_path.stat()
                        file_info["modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Format size
                        size = stat.st_size
                        if size < 1024:
                            file_info["size"] = f"{size} bytes"
                        elif size < 1024 * 1024:
                            file_info["size"] = f"{size / 1024:.1f} KB"
                        else:
                            file_info["size"] = f"{size / (1024 * 1024):.2f} MB"
                        
                        break
                
                self.wfile.write(json.dumps(file_info).encode())

            elif path == '/api/schedule/tasks':
                self._set_headers()
                self.wfile.write(json.dumps(get_scheduled_tasks()).encode())

            elif path == '/api/schedule/status':
                self._set_headers()
                self.wfile.write(json.dumps(get_games_needing_scrape()).encode())

            elif path == '/api/schedule/settings':
                self._set_headers()
                self.wfile.write(json.dumps(load_schedule_settings()).encode())

            elif path == '/api/schedule/logs':
                self._set_headers()
                # Get optional query params
                params = parse_qs(urlparse(self.path).query)
                scraper_id = params.get('scraper', [None])[0]
                lines = int(params.get('lines', [100])[0])
                self.wfile.write(json.dumps(get_scraper_logs(scraper_id, lines)).encode())

            elif path == '/api/schedule/reports':
                self._set_headers()
                self.wfile.write(json.dumps(get_scrape_reports()).encode())

            elif path == '/api/config':
                self._set_headers()
                config = load_config()
                config["paths"] = {
                    "database": str(DATABASE_PATH),
                    "scrapers_folder": str(SCRAPERS_FOLDER),
                    "react_app": str(REACT_APP_PATH),
                    "ranker": str(RANKER_PATH)
                }
                self.wfile.write(json.dumps(config).encode())

            # ========== API V1 - RANKINGS ENDPOINTS ==========
            elif path == '/api/v1/rankings':
                # Get rankings with optional filters
                start_time = time.time()
                ip_address = self._get_client_ip()
                user_info, account_type = self._get_auth_info()

                # Check rate limit
                allowed, remaining, reset, rate_headers = self._check_rate_limit(ip_address, account_type)
                if not allowed:
                    self._set_headers(429, extra_headers=rate_headers)
                    self.wfile.write(json.dumps({
                        "error": "Rate limit exceeded",
                        "retry_after": reset
                    }).encode())
                    return

                # Get filter parameters
                gender = get_param('gender')
                age_group = get_param('age_group')
                league = get_param('league')
                state = get_param('state')
                limit = min(int(get_param('limit', 100)), 500)  # Cap at 500
                offset = int(get_param('offset', 0))
                search = get_param('search')

                # Load rankings from JSON file (for now)
                rankings_path = SCRIPT_DIR / "public" / "rankings_for_react.json"
                if not rankings_path.exists():
                    rankings_path = RANKINGS_OUTPUT

                if rankings_path.exists():
                    with open(rankings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    all_teams = data.get('teamsData', [])

                    # Extract metadata from FULL dataset before filtering
                    all_age_groups = sorted(set(t.get('ageGroup', '') for t in all_teams if t.get('ageGroup')),
                                           key=lambda x: (x[0] != 'G', -int(x[1:]) if x[1:].isdigit() else 0))
                    all_genders = sorted(set(t.get('gender', '') for t in all_teams if t.get('gender')))
                    all_leagues = sorted(set(t.get('league', '') for t in all_teams if t.get('league')))
                    all_states = sorted(set(t.get('state', '') for t in all_teams if t.get('state')))

                    teams = all_teams

                    # Apply filters
                    if gender:
                        teams = [t for t in teams if t.get('gender', '').lower() == gender.lower()]
                    if age_group:
                        age_groups = [a.strip() for a in age_group.split(',')]
                        teams = [t for t in teams if t.get('age_group') in age_groups]
                    if league:
                        leagues = [l.strip() for l in league.split(',')]
                        teams = [t for t in teams if t.get('league') in leagues]
                    if state:
                        states = [s.strip().upper() for s in state.split(',')]
                        teams = [t for t in teams if t.get('state', '').upper() in states]
                    if search:
                        search_lower = search.lower()
                        teams = [t for t in teams if
                                 search_lower in t.get('name', '').lower() or
                                 search_lower in t.get('club', '').lower()]

                    total = len(teams)
                    teams = teams[offset:offset + limit]

                    response_data = {
                        "teams": teams,
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                        "lastUpdated": data.get('lastUpdated'),
                        # Metadata for dropdowns (from full dataset, not filtered)
                        "ageGroups": all_age_groups,
                        "genders": all_genders,
                        "leagues": all_leagues,
                        "states": all_states
                    }

                    # Log API call
                    if ACTIVITY_TRACKING_ENABLED:
                        session_id = self.headers.get('X-Session-ID')
                        log_api_call(
                            endpoint='/api/v1/rankings',
                            method='GET',
                            session_id=session_id,
                            user_id=user_info.get('uid') if user_info else None,
                            ip_address=ip_address,
                            params={'gender': gender, 'age_group': age_group, 'league': league,
                                    'state': state, 'limit': limit, 'offset': offset},
                            status_code=200,
                            response_time_ms=int((time.time() - start_time) * 1000),
                            response_size_bytes=len(json.dumps(response_data))
                        )

                    self._set_headers(extra_headers=rate_headers)
                    self.wfile.write(json.dumps(response_data).encode())
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"error": "Rankings data not found"}).encode())

            elif path.startswith('/api/v1/rankings/team/'):
                # Get single team profile
                team_id = unquote(path.split('/api/v1/rankings/team/')[1])
                ip_address = self._get_client_ip()
                user_info, account_type = self._get_auth_info()

                # Check rate limit
                allowed, remaining, reset, rate_headers = self._check_rate_limit(ip_address, account_type)
                if not allowed:
                    self._set_headers(429, extra_headers=rate_headers)
                    self.wfile.write(json.dumps({"error": "Rate limit exceeded"}).encode())
                    return

                # Load rankings and find team
                rankings_path = SCRIPT_DIR / "public" / "rankings_for_react.json"
                if not rankings_path.exists():
                    rankings_path = RANKINGS_OUTPUT

                if rankings_path.exists():
                    with open(rankings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    teams = data.get('teamsData', [])
                    team = None

                    # Find by various identifiers
                    for t in teams:
                        if (str(t.get('rank')) == team_id or
                            t.get('name', '').lower() == team_id.lower() or
                            t.get('team_url', '') == team_id):
                            team = t
                            break

                    if team:
                        # Log page view for activity tracking
                        if ACTIVITY_TRACKING_ENABLED:
                            session_id = self.headers.get('X-Session-ID')
                            if session_id:
                                log_page_view(
                                    session_id=session_id,
                                    page_type='team',
                                    page_path=f'/team/{team_id}',
                                    entity_type='team',
                                    entity_id=team_id,
                                    entity_name=team.get('name'),
                                    user_id=user_info.get('uid') if user_info else None
                                )

                        self._set_headers(extra_headers=rate_headers)
                        self.wfile.write(json.dumps({"team": team}).encode())
                    else:
                        self._set_headers(404)
                        self.wfile.write(json.dumps({"error": "Team not found"}).encode())
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"error": "Rankings data not found"}).encode())

            elif path.startswith('/api/v1/rankings/club/'):
                # Get all teams for a club
                club_name = unquote(path.split('/api/v1/rankings/club/')[1])
                ip_address = self._get_client_ip()
                user_info, account_type = self._get_auth_info()

                allowed, remaining, reset, rate_headers = self._check_rate_limit(ip_address, account_type)
                if not allowed:
                    self._set_headers(429, extra_headers=rate_headers)
                    self.wfile.write(json.dumps({"error": "Rate limit exceeded"}).encode())
                    return

                rankings_path = SCRIPT_DIR / "public" / "rankings_for_react.json"
                if not rankings_path.exists():
                    rankings_path = RANKINGS_OUTPUT

                if rankings_path.exists():
                    with open(rankings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    teams = data.get('teamsData', [])
                    club_teams = [t for t in teams if t.get('club', '').lower() == club_name.lower()]

                    if club_teams:
                        self._set_headers(extra_headers=rate_headers)
                        self.wfile.write(json.dumps({
                            "club": club_name,
                            "teams": club_teams,
                            "count": len(club_teams)
                        }).encode())
                    else:
                        self._set_headers(404)
                        self.wfile.write(json.dumps({"error": "Club not found"}).encode())
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"error": "Rankings data not found"}).encode())

            elif path == '/api/v1/rankings/search':
                # Search teams, clubs, players
                q = get_param('q', '')
                search_type = get_param('type', 'all')  # all, team, club, player
                limit = min(int(get_param('limit', 20)), 50)

                if len(q) < 2:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "Query must be at least 2 characters"}).encode())
                    return

                rankings_path = SCRIPT_DIR / "public" / "rankings_for_react.json"
                if not rankings_path.exists():
                    rankings_path = RANKINGS_OUTPUT

                results = {"teams": [], "clubs": [], "players": []}

                if rankings_path.exists():
                    with open(rankings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    q_lower = q.lower()

                    if search_type in ['all', 'team']:
                        teams = data.get('teamsData', [])
                        matching_teams = [t for t in teams if q_lower in t.get('name', '').lower()][:limit]
                        results["teams"] = matching_teams

                    if search_type in ['all', 'club']:
                        teams = data.get('teamsData', [])
                        clubs = {}
                        for t in teams:
                            club = t.get('club', '')
                            if q_lower in club.lower() and club not in clubs:
                                clubs[club] = {"name": club, "team_count": 0}
                            if club in clubs:
                                clubs[club]["team_count"] += 1
                        results["clubs"] = list(clubs.values())[:limit]

                    if search_type in ['all', 'player']:
                        players = data.get('playersData', [])
                        matching_players = [p for p in players if q_lower in p.get('name', '').lower()][:limit]
                        results["players"] = matching_players

                self._set_headers()
                self.wfile.write(json.dumps(results).encode())

            # ========== API V1 - ACTIVITY TRACKING ENDPOINTS ==========
            elif path == '/api/v1/activity/stats':
                # Get activity statistics (admin only)
                user_info, account_type = self._get_auth_info()

                if account_type != 'admin':
                    self._set_headers(403)
                    self.wfile.write(json.dumps({"error": "Admin access required"}).encode())
                    return

                if ACTIVITY_TRACKING_ENABLED:
                    date = get_param('date')
                    stats = get_daily_stats(date)
                    self._set_headers()
                    self.wfile.write(json.dumps(stats).encode())
                else:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())

            elif path == '/api/v1/activity/suspicious':
                # Get suspicious activity (admin only)
                user_info, account_type = self._get_auth_info()

                if account_type != 'admin':
                    self._set_headers(403)
                    self.wfile.write(json.dumps({"error": "Admin access required"}).encode())
                    return

                if ACTIVITY_TRACKING_ENABLED:
                    limit = int(get_param('limit', 100))
                    severity = get_param('severity')
                    activity = get_suspicious_activity(limit=limit, severity=severity)
                    self._set_headers()
                    self.wfile.write(json.dumps({"suspicious_activity": activity}).encode())
                else:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())

            elif path.startswith('/api/v1/activity/session/'):
                # Get session stats
                session_id = path.split('/api/v1/activity/session/')[1]
                user_info, account_type = self._get_auth_info()

                if account_type != 'admin':
                    self._set_headers(403)
                    self.wfile.write(json.dumps({"error": "Admin access required"}).encode())
                    return

                if ACTIVITY_TRACKING_ENABLED:
                    stats = get_session_stats(session_id)
                    if stats:
                        self._set_headers()
                        self.wfile.write(json.dumps(stats).encode())
                    else:
                        self._set_headers(404)
                        self.wfile.write(json.dumps({"error": "Session not found"}).encode())
                else:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())

            # ========== TEAM RATINGS API (GET) ==========
            elif path.startswith('/api/v1/ratings/team/'):
                # Get all ratings for a team
                team_id = path.split('/api/v1/ratings/team/')[1]
                include_pending = get_param('include_pending', 'false') == 'true'

                result = get_team_ratings(team_id, include_pending)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())

            elif path == '/api/v1/ratings/user':
                # Get current user's ratings
                user_info, account_type = self._get_auth_info()

                if not user_info:
                    self._set_headers(401)
                    self.wfile.write(json.dumps({"error": "Authentication required"}).encode())
                    return

                result = get_user_ratings(user_info.get('uid'))
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not found"}).encode())

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Read body
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
        
        try:
            # ========== AUTH ENDPOINTS ==========
            if path == '/api/auth/login':
                username = body.get('username', '')
                password = body.get('password', '')
                result = authenticate_user(username, password)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path == '/api/auth/signup':
                result = add_user(
                    body.get('username', ''),
                    body.get('email', ''),
                    body.get('account_type', 'free'),
                    body.get('notes', ''),
                    body.get('password', '')
                )
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path == '/api/auth/forgot-username':
                email = body.get('email', '')
                user = get_user_by_email(email)
                # Always return success to prevent email enumeration
                # In production, would send actual email
                if user:
                    print(f"[AUTH] Username reminder requested for: {email} -> {user['username']}")
                self._set_headers()
                self.wfile.write(json.dumps({"success": True, "message": "If account exists, username was sent"}).encode())
            
            elif path == '/api/auth/forgot-password':
                email = body.get('email', '')
                user = get_user_by_email(email)
                # Always return success to prevent email enumeration
                # In production, would send actual email with reset link
                if user:
                    print(f"[AUTH] Password reset requested for: {email}")
                self._set_headers()
                self.wfile.write(json.dumps({"success": True, "message": "If account exists, reset link was sent"}).encode())
            
            elif path.startswith('/api/user/') and path.endswith('/data'):
                # Save user data: POST /api/user/<username>/data
                parts = path.split('/')
                username = parts[3]
                result = save_user_data(username, body)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            # ========== SCRAPER ENDPOINTS ==========
            elif path == '/api/scraper/run':
                scraper_id = body.get('id')
                # Pass entire body as settings (includes all options from UI)
                self._set_headers()
                self.wfile.write(json.dumps(run_scraper(scraper_id, body)).encode())
            
            elif path == '/api/scraper/stop':
                scraper_id = body.get('id')
                self._set_headers()
                self.wfile.write(json.dumps(stop_scraper(scraper_id)).encode())
            
            elif path == '/api/users':
                result = add_user(
                    body.get('username', ''),
                    body.get('email', ''),
                    body.get('account_type', 'free'),
                    body.get('notes', ''),
                    body.get('password', '')
                )
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path == '/api/ranker/run':
                self._set_headers()
                self.wfile.write(json.dumps(run_ranker()).encode())
            
            elif path == '/api/export':
                self._set_headers()
                self.wfile.write(json.dumps(export_to_react()).encode())
            
            elif path == '/api/launch-react':
                self._set_headers()
                self.wfile.write(json.dumps(launch_react_app()).encode())

            elif path == '/api/schedule/run':
                task_name = body.get('task_name')
                if task_name:
                    result = run_scheduled_task(task_name)
                else:
                    result = run_scrape_now(body.get('type', 'full'))
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())

            elif path == '/api/schedule/toggle':
                task_name = body.get('task_name')
                enable = body.get('enable', True)
                self._set_headers()
                self.wfile.write(json.dumps(toggle_scheduled_task(task_name, enable)).encode())

            elif path == '/api/schedule/settings':
                # Save schedule settings
                self._set_headers()
                result = save_schedule_settings(body)
                self.wfile.write(json.dumps(result).encode())

            elif path == '/api/schedule/run-scraper':
                # Run a specific scraper immediately
                scraper_id = body.get('scraper_id', 'all')
                visible = body.get('visible', False)
                result = run_scrape_now(scraper_id if scraper_id != 'all' else 'full')
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())

            # ========== API V1 - ACTIVITY TRACKING ENDPOINTS ==========
            elif path == '/api/v1/activity/session':
                # Create a new session
                if not ACTIVITY_TRACKING_ENABLED:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())
                    return

                ip_address = self._get_client_ip()
                user_info, account_type = self._get_auth_info()

                # Extract device info from body
                device_info = {
                    "userAgent": body.get("userAgent"),
                    "screenWidth": body.get("screenWidth"),
                    "screenHeight": body.get("screenHeight"),
                    "colorDepth": body.get("colorDepth"),
                    "pixelRatio": body.get("pixelRatio"),
                    "timezone": body.get("timezone"),
                    "timezoneOffset": body.get("timezoneOffset"),
                    "language": body.get("language"),
                    "languages": body.get("languages"),
                    "platform": body.get("platform"),
                    "vendor": body.get("vendor"),
                    "hardwareConcurrency": body.get("hardwareConcurrency"),
                    "maxTouchPoints": body.get("maxTouchPoints"),
                    "cookiesEnabled": body.get("cookiesEnabled"),
                    "doNotTrack": body.get("doNotTrack"),
                    "referrer": body.get("referrer"),
                    "landingPage": body.get("landingPage"),
                    "utm_source": body.get("utm_source"),
                    "utm_medium": body.get("utm_medium"),
                    "utm_campaign": body.get("utm_campaign"),
                    "utm_term": body.get("utm_term"),
                    "utm_content": body.get("utm_content"),
                }

                session_id = create_session(
                    device_info=device_info,
                    ip_address=ip_address,
                    user_id=user_info.get('uid') if user_info else None,
                    firebase_uid=user_info.get('uid') if user_info else None,
                    account_type=account_type
                )

                self._set_headers()
                self.wfile.write(json.dumps({
                    "session_id": session_id,
                    "account_type": account_type
                }).encode())

            elif path == '/api/v1/activity/pageview':
                # Log a page view
                if not ACTIVITY_TRACKING_ENABLED:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())
                    return

                session_id = body.get('session_id') or self.headers.get('X-Session-ID')
                if not session_id:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "session_id required"}).encode())
                    return

                user_info, _ = self._get_auth_info()

                page_view_id = log_page_view(
                    session_id=session_id,
                    page_type=body.get('page_type', 'unknown'),
                    page_path=body.get('page_path', '/'),
                    entity_type=body.get('entity_type'),
                    entity_id=body.get('entity_id'),
                    entity_name=body.get('entity_name'),
                    previous_page=body.get('previous_page'),
                    previous_entity_id=body.get('previous_entity_id'),
                    navigation_method=body.get('navigation_method'),
                    page_params=body.get('page_params'),
                    user_id=user_info.get('uid') if user_info else None
                )

                self._set_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "page_view_id": page_view_id
                }).encode())

            elif path == '/api/v1/activity/heartbeat':
                # Update time on page
                if not ACTIVITY_TRACKING_ENABLED:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())
                    return

                page_view_id = body.get('page_view_id')
                if not page_view_id:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "page_view_id required"}).encode())
                    return

                update_page_time(
                    page_view_id=page_view_id,
                    time_on_page_ms=body.get('time_on_page_ms', 0),
                    max_scroll_depth=body.get('max_scroll_depth')
                )

                self._set_headers()
                self.wfile.write(json.dumps({"success": True}).encode())

            elif path == '/api/v1/activity/update-user':
                # Update session with authenticated user info
                if not ACTIVITY_TRACKING_ENABLED:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())
                    return

                session_id = body.get('session_id') or self.headers.get('X-Session-ID')
                if not session_id:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "session_id required"}).encode())
                    return

                user_info, account_type = self._get_auth_info()

                if user_info:
                    update_session_user(
                        session_id=session_id,
                        user_id=user_info.get('uid'),
                        firebase_uid=user_info.get('uid'),
                        account_type=account_type
                    )
                    self._set_headers()
                    self.wfile.write(json.dumps({
                        "success": True,
                        "account_type": account_type
                    }).encode())
                else:
                    self._set_headers(401)
                    self.wfile.write(json.dumps({"error": "Not authenticated"}).encode())

            elif path == '/api/v1/activity/block':
                # Block an IP or fingerprint (admin only)
                user_info, account_type = self._get_auth_info()

                if account_type != 'admin':
                    self._set_headers(403)
                    self.wfile.write(json.dumps({"error": "Admin access required"}).encode())
                    return

                if not ACTIVITY_TRACKING_ENABLED:
                    self._set_headers(503)
                    self.wfile.write(json.dumps({"error": "Activity tracking not enabled"}).encode())
                    return

                block_type = body.get('block_type')  # 'ip' or 'fingerprint'
                block_value = body.get('block_value')
                reason = body.get('reason', 'Manual block')
                expires_hours = body.get('expires_hours')  # None = permanent

                if not block_type or not block_value:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "block_type and block_value required"}).encode())
                    return

                add_to_blocklist(
                    block_type=block_type,
                    block_value=block_value,
                    reason=reason,
                    expires_hours=expires_hours,
                    created_by=user_info.get('email') if user_info else 'admin'
                )

                self._set_headers()
                self.wfile.write(json.dumps({"success": True}).encode())

            # ========== TEAM RATINGS API (POST) ==========
            elif path == '/api/v1/ratings/submit':
                # Submit a new team rating
                user_info, account_type = self._get_auth_info()

                if not user_info:
                    self._set_headers(401)
                    self.wfile.write(json.dumps({
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED"
                    }).encode())
                    return

                # Check account type (PAID+ only)
                if account_type not in ['paid', 'pro', 'coach', 'admin']:
                    self._set_headers(403)
                    self.wfile.write(json.dumps({
                        "error": "Pro account required to submit ratings",
                        "code": "PAID_REQUIRED"
                    }).encode())
                    return

                result = submit_team_rating(user_info.get('uid'), body)
                status_code = 200 if result.get('success') else 400
                self._set_headers(status_code)
                self.wfile.write(json.dumps(result).encode())

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not found"}).encode())

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
        
        try:
            if path.startswith('/api/users/'):
                user_id = int(path.split('/')[-1])
                result = update_user(user_id, body)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path.startswith('/api/teams/'):
                rowid = path.split('/')[-1]
                result = update_team(rowid, body)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path.startswith('/api/players/'):
                rowid = path.split('/')[-1]
                result = update_player(rowid, body)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path.startswith('/api/games/'):
                rowid = path.split('/')[-1]
                result = update_game(rowid, body)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path == '/api/config/paths':
                result = update_paths(body)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            if path.startswith('/api/users/'):
                user_id = int(path.split('/')[-1])
                result = delete_user(user_id)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif path.startswith('/api/games/'):
                rowid = path.split('/')[-1]
                result = delete_game(rowid)
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())

            # ========== TEAM RATINGS API (DELETE) ==========
            elif path.startswith('/api/v1/ratings/'):
                # Delete a rating: DELETE /api/v1/ratings/{ratingId}
                rating_id = path.split('/api/v1/ratings/')[1]

                user_info, account_type = self._get_auth_info()

                if not user_info:
                    self._set_headers(401)
                    self.wfile.write(json.dumps({"error": "Authentication required"}).encode())
                    return

                result = delete_team_rating(rating_id, user_info.get('uid'))
                status_code = 200 if result.get('success') else 400
                self._set_headers(status_code)
                self.wfile.write(json.dumps(result).encode())

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not found"}).encode())

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        # Custom logging
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

def run_server(port=5050, open_browser=True):
    """Start the admin server"""
    # Initialize ratings table on startup
    init_ratings_table()

    server = HTTPServer(('localhost', port), AdminHandler)
    
    print("\n" + "=" * 60)
    print("  SEEDLINE ADMIN SERVER")
    print("=" * 60)
    print(f"\n  Server running at: http://localhost:{port}")
    print(f"  Dashboard: Open admin_dashboard.html in your browser")
    print(f"\n  Database: {DATABASE_PATH}")
    print(f"  Exists: {'Yes' if DATABASE_PATH.exists() else 'No'}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    if open_browser:
        dashboard_path = SCRIPT_DIR / "admin_dashboard.html"
        if dashboard_path.exists():
            webbrowser.open(f"file://{dashboard_path}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  Server stopped")
        server.shutdown()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seedline Admin Server')
    parser.add_argument('--port', type=int, default=5050, help='Server port')
    parser.add_argument('--no-browser', action='store_true', help="Don't open browser")
    args = parser.parse_args()
    
    run_server(args.port, not args.no_browser)
