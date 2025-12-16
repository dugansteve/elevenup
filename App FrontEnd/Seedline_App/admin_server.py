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
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
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
    
    print(f"🔍 Looking for 'scrapers and data' folder...")
    print(f"   Script location: {SCRIPT_DIR}")
    
    for path in candidates:
        print(f"   Checking: {path}")
        if path.exists():
            print(f"   ✅ Found: {path}")
            return path
    
    print(f"   ❌ Not found - using script directory")
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
    
    print(f"\n🔧 Configuring scraper paths...")
    print(f"   SCRAPERS_FOLDER: {SCRAPERS_FOLDER}")
    print(f"   Scrapers subfolder: {scrapers_subfolder} (exists: {scrapers_subfolder.exists()})")
    print(f"   App scrapers folder: {app_scrapers} (exists: {app_scrapers.exists()})")
    
    scrapers = {
        "ecnl": {
            "name": "ECNL + ECNL-RL Scraper",
            "path": find_latest_scraper(ecnl_folder, "ecnl_scraper_v*.py"),
            "description": "Scrapes ECNL and ECNL Regional League games and players"
        },
        "ga": {
            "name": "Girls Academy Scraper", 
            "path": find_latest_scraper(ga_league_folder, "GA_scraper_v*.py"),
            "description": "Scrapes Girls Academy league games"
        },
        "ga_events": {
            "name": "GA Events Scraper",
            "path": find_latest_scraper(ga_events_folder, "GA_events_scraper_v*.py"),
            "description": "Scrapes GA showcases, playoffs, regionals, and Champions Cup"
        },
        "aspire": {
            "name": "ASPIRE Scraper",
            "path": find_latest_scraper(aspire_folder, "ASPIRE_scraper_v*.py"),
            "description": "Scrapes ASPIRE league games"
        },
        "npl": {
            "name": "NPL League Scraper",
            "path": find_latest_scraper(npl_folder, "us_club_npl_league_scraper_v*.py"),
            "description": "Scrapes US Club Soccer NPL and Sub-NPL league games"
        }
    }
    
    # Override with app-bundled scrapers if they exist AND if Dropbox versions weren't found
    # The find_latest_scraper function already picks the highest version, so we only use
    # bundled scrapers as fallback
    if app_scrapers.exists():
        bundled_scrapers = {
            "ecnl": "ecnl_scraper_v*.py",
            "ga": "GA_scraper_v*.py", 
            "ga_events": "GA_events_scraper_v*.py",
            "aspire": "ASPIRE_scraper_v*.py"
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
    print(f"\n📋 Scraper configuration:")
    for sid, s in scrapers.items():
        exists = s["path"].exists()
        print(f"   {sid}: {s['path']} ({'✅' if exists else '❌'})")
    
    return scrapers

SCRAPERS = get_scraper_paths()

# Team ranker location - find latest version
def find_team_ranker():
    """Find the latest team ranker version"""
    ranker_folder = SCRAPERS_FOLDER / "Run Rankings"
    if not ranker_folder.exists():
        return ranker_folder / "team_ranker_v38.py"
    
    # Look for team_ranker_v*.py files
    import re
    ranker_files = list(ranker_folder.glob("team_ranker_v*.py"))
    if not ranker_files:
        return ranker_folder / "team_ranker_v38.py"
    
    # Sort by version (handle versions like v39, v39b, v39c)
    def get_version(f):
        match = re.search(r'v(\d+)([a-z])?', f.name)
        if match:
            num = int(match.group(1))
            letter = match.group(2) or ''
            return (num, letter)
        return (0, '')
    
    ranker_files.sort(key=get_version, reverse=True)
    print(f"   Found team ranker: {ranker_files[0].name}")
    return ranker_files[0]

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
# HTTP SERVER
# ============================================================================

class AdminHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the admin API"""
    
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
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
            if path == '/api/stats':
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
    server = HTTPServer(('localhost', port), AdminHandler)
    
    print("\n" + "=" * 60)
    print("  🌱 SEEDLINE ADMIN SERVER")
    print("=" * 60)
    print(f"\n  Server running at: http://localhost:{port}")
    print(f"  Dashboard: Open admin_dashboard.html in your browser")
    print(f"\n  Database: {DATABASE_PATH}")
    print(f"  Exists: {'✅ Yes' if DATABASE_PATH.exists() else '❌ No'}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    if open_browser:
        dashboard_path = SCRIPT_DIR / "admin_dashboard.html"
        if dashboard_path.exists():
            webbrowser.open(f"file://{dashboard_path}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  👋 Server stopped")
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
