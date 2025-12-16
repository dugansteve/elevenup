#!/usr/bin/env python3
"""
US Club Soccer NPL League Scraper v20.0
=======================================
Comprehensive scraper for US Club Soccer NPL and Sub-NPL leagues.

Changes in v20.0:
- NEW: Resume capability - can restart where it left off if interrupted
- NEW: --scrape flag (scrape pending leagues only - default)
- NEW: --scrape-all flag (re-scrape all leagues)
- NEW: --reset-status flag (reset all leagues to pending, then scrape)
- NEW: npl_scrape_status table tracks which leagues have been scraped
- All v19 features preserved

Changes in v19.0:
- FIXED: Age group conversion - now correctly converts birth year to U-age format
  (e.g., 2013 -> G12 for Girls, B12 for Boys) instead of graduation year
- NEW: Added location scraping from team profile pages (city, state, zip, address)
- All v18 features preserved

Changes in v18.0:
- Added --players arg (accepted for admin UI, NPL doesn't scrape players)
- Added --verbose arg (enables debug output)
- All v15 features preserved

Changes in v15.0:
- Added --ages and --no-confirm args for admin UI compatibility
- Added --gender both option to scrape all genders
- Games saved to seedlinedata.db games table
- All v14 features preserved

Changes in v13.0:
- NEW: Teams saved to seedlinedata.db teams table
- NEW: State inference from team name, region, and league name
- NEW: Database path auto-detection
- All v12 features preserved

Changes in v12.0:
- NEW: Output filenames now include version number for tracking
- NEW: "Bye" games excluded from output (not real games)
- IMPROVED: All v9/v10/v11 fixes verified and preserved
- VERIFIED: Gender detection working (v11 fix)
- VERIFIED: Age group conversion working (v9/v10 fixes)
- VERIFIED: Time parsing working (v7 fix)

Changes in v11.0:
- FIXED: Gender detection from team names (B15, G14, etc.)

Changes in v10.0:
- FIXED: Handle 2013B/2013G format (birth year + gender suffix)

Changes in v9.0:
- FIXED: Age groups converted to birth year format (U14B -> 2011)
- FIXED: Games without scores marked "unknown" not "completed"
- FIXED: Doubled team name patterns cleaned

Changes in v7/v8:
- FIXED: Time parsing for year-concatenated strings
- FIXED: Club name extraction for abbreviation patterns

Features:
- 🕵️ Human-like behavior (delays, coffee breaks, rotating user agents)
- 📋 Interactive menu system (or command-line mode)
- 📊 CSV export with proper schema for seedlinedata.db import
- 📍 Location data extraction from team profiles
- 🔄 Resume capability (can pick up where it left off)

Supported Platforms:
- GotSport (system.gotsport.com) - 26 leagues
- TotalGlobalSports (public.totalglobalsports.com) - 3 leagues  
- SincSports (soccer.sincsports.com) - 1 league

Author: Claude (with Steve)
Version: 20.0
"""

# Version constant for filename tracking
SCRAPER_VERSION = "v20"

import os
import re
import csv
import sys
import json
import time
import random
import asyncio
import argparse
import traceback
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path

# Third-party imports
try:
    from playwright.async_api import async_playwright, Page, Browser
    from bs4 import BeautifulSoup
    import requests
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip install playwright beautifulsoup4 requests --break-system-packages")
    print("Then run: playwright install chromium")
    sys.exit(1)


# =============================================================================
# STEALTH CONFIGURATION - Human-like behavior
# =============================================================================

# Rotating user agents to look like different browsers/devices
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]

# Delay ranges (in seconds) - mimics human browsing patterns
MIN_DELAY = 2.0
MAX_DELAY = 5.0
MIN_COFFEE_BREAK = 30.0
MAX_COFFEE_BREAK = 60.0
COFFEE_BREAK_INTERVAL = (15, 20)  # Take a break every 15-20 requests
READING_PAUSE_CHANCE = 0.2  # 20% chance of longer pause (simulating reading)

# Screenshot settings (v4 - non-blocking)
SCREENSHOT_TIMEOUT = 60000  # 60 seconds (was 30s default)
TAKE_SCREENSHOTS = True  # Can be disabled with --no-screenshots


# =============================================================================
# LEAGUE CONFIGURATION
# =============================================================================

@dataclass
class LeagueConfig:
    """Configuration for a single league"""
    name: str
    organization: str  # "US Club Soccer"
    platform: str      # "gotsport", "totalglobalsports", "sincsports"
    url: str
    event_id: str
    gender: str        # "Both", "Boys", "Girls"
    age_groups: str    # "U13-U19", "U9-U19", etc.
    region: str
    tier: str          # "NPL", "Sub-NPL"
    active: bool = True


# All verified US Club Soccer NPL leagues
LEAGUE_CONFIGS = [
    # === NPL TIER LEAGUES (GotSport) ===
    LeagueConfig("Central States NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/46428", "46428",
                 "Both", "U13-U19", "Midwest", "NPL"),
    LeagueConfig("CPSL NPL (Chesapeake)", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/43268", "43268",
                 "Both", "U13-U19", "Mid-Atlantic", "NPL"),
    LeagueConfig("FCL NPL (Florida)", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44970", "44970",
                 "Both", "U13-U19", "Southeast", "NPL"),
    LeagueConfig("Frontier Premier League", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44015", "44015",
                 "Both", "U13-U19", "Mountain", "NPL"),
    LeagueConfig("Great Lakes Alliance NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/43157", "43157",
                 "Both", "U13-U19", "Midwest", "NPL"),
    LeagueConfig("Mid-Atlantic Premier League", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45036", "45036",
                 "Both", "U13-U19", "Mid-Atlantic", "NPL"),
    LeagueConfig("MDL NPL (Midwest Developmental)", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/43156", "43156",
                 "Both", "U11-U14", "Midwest", "NPL"),
    LeagueConfig("Minnesota NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/47013", "47013",
                 "Both", "U13-U19", "Midwest", "NPL"),
    LeagueConfig("Mountain West NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44839", "44839",
                 "Both", "U13-U19", "Mountain", "NPL"),
    LeagueConfig("NISL NPL (Northern Illinois)", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44630", "44630",
                 "Both", "U13-U19", "Midwest", "NPL"),
    LeagueConfig("NorCal NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44145", "44145",
                 "Both", "U13-U19", "West", "NPL"),
    LeagueConfig("Red River NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45381", "45381",
                 "Both", "U13-U19", "Central", "NPL"),
    LeagueConfig("SOCAL NPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/43086", "43086",
                 "Both", "U13-U19", "Southwest", "NPL"),
    LeagueConfig("South Atlantic Premier League", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45713", "45713",
                 "Both", "U13-U19", "Southeast", "NPL"),
    LeagueConfig("VPSL NPL (Virginia)", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/42891", "42891",
                 "Both", "U13-U19", "Mid-Atlantic", "NPL"),
    LeagueConfig("WPL NPL U11-U14 Fall", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44846", "44846",
                 "Both", "U11-U14", "Northwest", "NPL"),
    LeagueConfig("WPL NPL Boys Fall HS", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/44844", "44844",
                 "Boys", "U15-U19", "Northwest", "NPL"),
    LeagueConfig("WPL NPL Girls HS", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/38594", "38594",
                 "Girls", "U15-U19", "Northwest", "NPL"),
    
    # === NPL TIER LEAGUES (TotalGlobalSports) ===
    LeagueConfig("STXCL NPL Girls", "US Club Soccer", "totalglobalsports",
                 "https://public.totalglobalsports.com/public/event/3979/schedules-standings", "3979",
                 "Girls", "U13-U19", "Southwest", "NPL"),
    LeagueConfig("STXCL NPL Boys", "US Club Soccer", "totalglobalsports",
                 "https://public.totalglobalsports.com/public/event/3973/schedules-standings", "3973",
                 "Boys", "U13-U19", "Southwest", "NPL"),
    LeagueConfig("TCSL NPL (Texas)", "US Club Soccer", "totalglobalsports",
                 "https://public.totalglobalsports.com/public/event/3989/schedules-standings", "3989",
                 "Both", "U13-U19", "Southwest", "NPL"),
    
    # === SUB-NPL TIER LEAGUES (GotSport) ===
    LeagueConfig("Chesapeake PSL YPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/43658", "43658",
                 "Both", "U9-U12", "Mid-Atlantic", "Sub-NPL"),
    LeagueConfig("Idaho Premier League", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45021", "45021",
                 "Both", "U9-U19", "Northwest", "Sub-NPL"),
    LeagueConfig("Florida CFPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45046", "45046",
                 "Both", "U9-U19", "Southeast", "Sub-NPL"),
    LeagueConfig("Florida NFPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45064", "45064",
                 "Both", "U9-U19", "Southeast", "Sub-NPL"),
    LeagueConfig("Florida SEFPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45052", "45052",
                 "Both", "U9-U19", "Southeast", "Sub-NPL"),
    LeagueConfig("Florida WFPL", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45008", "45008",
                 "Both", "U9-U19", "Southeast", "Sub-NPL"),
    LeagueConfig("Southeastern CCL Fall", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/45507", "45507",
                 "Both", "U13-U19", "Southeast", "Sub-NPL"),
    LeagueConfig("Southeastern CCL U11/U12", "US Club Soccer", "gotsport",
                 "https://system.gotsport.com/org_event/events/49040", "49040",
                 "Both", "U11-U12", "Southeast", "Sub-NPL"),
    
    # === SUB-NPL TIER LEAGUES (SincSports) ===
    LeagueConfig("Carolina Champions League", "US Club Soccer", "sincsports",
                 "https://soccer.sincsports.com/TTContent.aspx?tid=CARCHLEA", "CARCHLEA",
                 "Both", "U9-U19", "Southeast", "Sub-NPL"),
]


# =============================================================================
# CSV OUTPUT SCHEMA - Matches seedlinedata.db structure
# =============================================================================

GAMES_CSV_COLUMNS = [
    'game_id', 'external_game_id', 'league', 'organization', 'platform',
    'tier', 'region', 'gender', 'age_group', 'division',
    'home_team', 'home_team_normalized', 'home_team_id', 'home_team_url',
    'away_team', 'away_team_normalized', 'away_team_id', 'away_team_url',
    'home_score', 'away_score', 'game_date', 'game_time', 'game_status',
    'location', 'field', 'source_url', 'scraped_at',
]

TEAMS_CSV_COLUMNS = [
    'team_id', 'team_name', 'team_name_normalized', 'club_name',
    'league', 'age_group', 'gender', 'region', 'platform',
    'schedule_url', 'profile_url', 'state', 'city', 'street_address', 
    'zip_code', 'official_website', 'discovered_at',
]


# =============================================================================
# DATABASE FUNCTIONS (v13)
# =============================================================================

def find_database_path():
    """Find the seedlinedata.db database file"""
    script_dir = Path(__file__).parent.resolve()
    search_paths = [
        # v16: Added parent.parent for actual folder structure:
        # Script: scrapers and data/Scrapers/NPL league scraper/scraper.py
        # DB:     scrapers and data/seedlinedata.db
        script_dir.parent.parent / "seedlinedata.db",
        script_dir.parent / "seedlinedata.db",
        script_dir / "seedlinedata.db",
        Path.cwd() / "seedlinedata.db",
        script_dir.parent / "scrapers and data" / "seedlinedata.db",
    ]
    for path in search_paths:
        if path.exists():
            return str(path.resolve())
    return None


# Region to state mapping for NPL leagues
NPL_REGION_STATE_MAP = {
    'Midwest': None,  # Multiple states
    'Mid-Atlantic': None,  # Multiple states
    'Southeast': None,  # Multiple states
    'Mountain': None,  # Multiple states
    'West': 'California',
    'Southwest': None,  # Multiple states
    'Central': None,  # Multiple states
    'Northwest': None,  # Multiple states
}


def infer_state_from_npl_team(team_name: str, region: str, league: str) -> Optional[str]:
    """Try to infer state from team name, region, or league"""
    # Check for state indicators in team name
    team_upper = team_name.upper() if team_name else ''
    
    state_indicators = {
        'TEXAS': 'Texas', 'TX ': 'Texas', ' TX': 'Texas',
        'CALIFORNIA': 'California', 'CA ': 'California', ' CA': 'California', 'SOCAL': 'California', 'NORCAL': 'California',
        'FLORIDA': 'Florida', 'FL ': 'Florida', ' FL': 'Florida',
        'VIRGINIA': 'Virginia', 'VA ': 'Virginia', ' VA': 'Virginia',
        'GEORGIA': 'Georgia',
        'NEW YORK': 'New York', 'NY ': 'New York', ' NY': 'New York',
        'PENNSYLVANIA': 'Pennsylvania', 'PA ': 'Pennsylvania', ' PA': 'Pennsylvania',
        'OHIO': 'Ohio', 'OH ': 'Ohio', ' OH': 'Ohio',
        'ILLINOIS': 'Illinois', 'IL ': 'Illinois', ' IL': 'Illinois', 'CHICAGO': 'Illinois',
        'MICHIGAN': 'Michigan', 'MI ': 'Michigan', ' MI': 'Michigan',
        'ARIZONA': 'Arizona', 'AZ ': 'Arizona', ' AZ': 'Arizona',
        'COLORADO': 'Colorado', 'CO ': 'Colorado', ' CO': 'Colorado', 'DENVER': 'Colorado',
        'WASHINGTON': 'Washington', 'WA ': 'Washington', ' WA': 'Washington', 'SEATTLE': 'Washington',
        'MARYLAND': 'Maryland', 'MD ': 'Maryland', ' MD': 'Maryland',
        'NEW JERSEY': 'New Jersey', 'NJ ': 'New Jersey', ' NJ': 'New Jersey',
        'MASSACHUSETTS': 'Massachusetts', 'MA ': 'Massachusetts', ' MA': 'Massachusetts', 'BOSTON': 'Massachusetts',
        'NORTH CAROLINA': 'North Carolina', 'NC ': 'North Carolina', ' NC': 'North Carolina', 'CHARLOTTE': 'North Carolina',
        'SOUTH CAROLINA': 'South Carolina',
        'TENNESSEE': 'Tennessee', 'TN ': 'Tennessee', ' TN': 'Tennessee', 'NASHVILLE': 'Tennessee',
        'MISSOURI': 'Missouri', 'MO ': 'Missouri', ' MO': 'Missouri', 'ST LOUIS': 'Missouri', 'KANSAS CITY': 'Missouri',
        'MINNESOTA': 'Minnesota', 'MN ': 'Minnesota', ' MN': 'Minnesota', 'MINNEAPOLIS': 'Minnesota',
        'WISCONSIN': 'Wisconsin', 'WI ': 'Wisconsin', ' WI': 'Wisconsin',
        'INDIANA': 'Indiana', 'IN ': 'Indiana', 'INDIANAPOLIS': 'Indiana',
        'UTAH': 'Utah', 'UT ': 'Utah', ' UT': 'Utah', 'SALT LAKE': 'Utah',
        'NEVADA': 'Nevada', 'NV ': 'Nevada', ' NV': 'Nevada', 'LAS VEGAS': 'Nevada',
        'OREGON': 'Oregon', 'OR ': 'Oregon', 'PORTLAND': 'Oregon',
        'ALABAMA': 'Alabama', 'AL ': 'Alabama', ' AL': 'Alabama',
        'LOUISIANA': 'Louisiana', 'LA ': 'Louisiana', 'NEW ORLEANS': 'Louisiana',
        'KENTUCKY': 'Kentucky', 'KY ': 'Kentucky', ' KY': 'Kentucky',
        'CONNECTICUT': 'Connecticut', 'CT ': 'Connecticut', ' CT': 'Connecticut',
        'OKLAHOMA': 'Oklahoma', 'OK ': 'Oklahoma', ' OK': 'Oklahoma',
        'KANSAS': 'Kansas', 'KS ': 'Kansas', ' KS': 'Kansas',
        'IOWA': 'Iowa', 'IA ': 'Iowa', ' IA': 'Iowa',
        'NEBRASKA': 'Nebraska', 'NE ': 'Nebraska', 'OMAHA': 'Nebraska',
        'IDAHO': 'Idaho', 'ID ': 'Idaho', ' ID': 'Idaho',
        'NEW MEXICO': 'New Mexico', 'NM ': 'New Mexico', ' NM': 'New Mexico',
    }
    
    for indicator, state in state_indicators.items():
        if indicator in team_upper:
            return state
    
    # Check league name for state hints
    if league:
        league_upper = league.upper()
        if 'TEXAS' in league_upper or 'STXCL' in league_upper:
            return 'Texas'
        if 'FLORIDA' in league_upper or 'FCL' in league_upper:
            return 'Florida'
        if 'VIRGINIA' in league_upper or 'VPSL' in league_upper:
            return 'Virginia'
        if 'MINNESOTA' in league_upper:
            return 'Minnesota'
        if 'NORCAL' in league_upper:
            return 'California'
        if 'SOCAL' in league_upper:
            return 'California'
        if 'CHESAPEAKE' in league_upper or 'CPSL' in league_upper:
            return 'Maryland'
        if 'ILLINOIS' in league_upper or 'NISL' in league_upper:
            return 'Illinois'
    
    return None


# =============================================================================
# NPL SCRAPE STATUS TRACKING (v20)
# =============================================================================

def ensure_npl_scrape_status_table(db_path: str) -> bool:
    """Create npl_scrape_status table if it doesn't exist"""
    if not db_path:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS npl_scrape_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_name TEXT UNIQUE NOT NULL,
                league_url TEXT,
                scrape_status TEXT DEFAULT 'pending',
                last_scraped TIMESTAMP,
                games_found INTEGER DEFAULT 0,
                teams_found INTEGER DEFAULT 0,
                errors TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  ⚠️ Could not create npl_scrape_status table: {e}")
        return False


def get_league_scrape_status(db_path: str, league_name: str) -> Optional[str]:
    """Get the scrape status for a league"""
    if not db_path:
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT scrape_status FROM npl_scrape_status WHERE league_name = ?", (league_name,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return None


def update_league_scrape_status(db_path: str, league_name: str, status: str, 
                                 league_url: str = None, games_found: int = 0, 
                                 teams_found: int = 0, errors: str = None) -> bool:
    """Update or insert the scrape status for a league"""
    if not db_path:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if exists
        cur.execute("SELECT id FROM npl_scrape_status WHERE league_name = ?", (league_name,))
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""UPDATE npl_scrape_status SET 
                          scrape_status = ?, 
                          last_scraped = datetime('now'),
                          games_found = ?,
                          teams_found = ?,
                          errors = ?
                          WHERE league_name = ?""",
                       (status, games_found, teams_found, errors, league_name))
        else:
            cur.execute("""INSERT INTO npl_scrape_status 
                          (league_name, league_url, scrape_status, last_scraped, games_found, teams_found, errors)
                          VALUES (?, ?, ?, datetime('now'), ?, ?, ?)""",
                       (league_name, league_url, status, games_found, teams_found, errors))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  ⚠️ Could not update scrape status: {e}")
        return False


def reset_all_npl_scrape_status(db_path: str) -> int:
    """Reset all NPL league scrape statuses to 'pending'"""
    if not db_path:
        return 0
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("UPDATE npl_scrape_status SET scrape_status = 'pending'")
        count = cur.rowcount
        conn.commit()
        conn.close()
        return count
    except Exception as e:
        print(f"  ⚠️ Could not reset scrape status: {e}")
        return 0


def get_pending_leagues_count(db_path: str) -> Tuple[int, int]:
    """Get count of pending and completed leagues"""
    if not db_path:
        return (0, 0)
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM npl_scrape_status WHERE scrape_status = 'pending' OR scrape_status IS NULL")
        pending = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM npl_scrape_status WHERE scrape_status = 'completed'")
        completed = cur.fetchone()[0]
        conn.close()
        return (pending, completed)
    except:
        return (0, 0)


def save_npl_team_to_db(db_path: str, team: Dict) -> bool:
    """Save NPL team to teams table in database"""
    if not db_path:
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Build a unique URL for the team
    team_url = team.get('schedule_url') or team.get('profile_url') or f"npl_team_{team.get('team_id', '')}"
    
    cur.execute("SELECT rowid FROM teams WHERE team_url = ?", (team_url,))
    existing = cur.fetchone()
    
    if existing:
        # Update existing team with any new data
        cur.execute("""UPDATE teams SET 
                      state = COALESCE(?, state),
                      conference = COALESCE(?, conference),
                      last_updated = datetime('now')
                      WHERE team_url = ?""",
                   (team.get('state'), team.get('region'), team_url))
        conn.commit()
        conn.close()
        return False
    
    # Infer state from team name/region/league
    state = infer_state_from_npl_team(team.get('team_name'), team.get('region'), team.get('league'))
    
    # v19 FIX: Convert age_group to U-age format (birth year to G12/B12 format)
    # Previous versions incorrectly converted to graduation year (G31)
    age_group = team.get('age_group', '')
    gender = team.get('gender', 'Girls')
    if age_group and age_group.isdigit() and len(age_group) == 4:
        birth_year = int(age_group)
        current_year = datetime.now().year
        age = current_year - birth_year  # 2025 - 2013 = 12
        gender_prefix = 'B' if gender.lower().startswith('b') else 'G'
        age_group = f"{gender_prefix}{age:02d}"  # "G12" or "B12"
    
    # v19: Get location fields
    city = team.get('city', '')
    street_address = team.get('street_address', '')
    zip_code = team.get('zip_code', '')
    official_website = team.get('official_website', '')
    
    # Use provided state or inferred state
    if team.get('state'):
        state = team.get('state')
    
    cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference, 
                  state, city, street_address, zip_code, official_website, team_id, scraped_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
               (team_url, team.get('club_name'), team.get('team_name'), age_group,
                gender, team.get('league'), team.get('region'),
                state, city, street_address, zip_code, official_website, team.get('team_id')))
    conn.commit()
    conn.close()
    return True


def save_npl_game_to_db(db_path: str, game: Dict) -> bool:
    """Save NPL game to games table in database (v14)"""
    if not db_path:
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    game_id = game.get('game_id', '')
    if not game_id:
        conn.close()
        return False
    
    # Check if game already exists
    cur.execute("SELECT rowid, home_score, away_score FROM games WHERE game_id = ?", (game_id,))
    existing = cur.fetchone()
    
    if existing:
        # Update if we have score data and existing doesn't
        existing_home_score = existing[1]
        existing_away_score = existing[2]
        new_home_score = game.get('home_score')
        new_away_score = game.get('away_score')
        
        # Only update if we have new score data
        if (new_home_score is not None and existing_home_score is None) or \
           (new_away_score is not None and existing_away_score is None):
            cur.execute("""UPDATE games SET 
                          home_score = COALESCE(?, home_score),
                          away_score = COALESCE(?, away_score),
                          game_status = COALESCE(?, game_status),
                          last_updated = datetime('now')
                          WHERE game_id = ?""",
                       (new_home_score, new_away_score, game.get('game_status'), game_id))
            conn.commit()
        conn.close()
        return False
    
    # v19 FIX: Convert age_group to U-age format (birth year to G12/B12 format)
    # Previous versions incorrectly converted to graduation year (G31)
    age_group = game.get('age_group', '')
    gender = game.get('gender', 'Girls')
    if age_group and age_group.isdigit() and len(age_group) == 4:
        birth_year = int(age_group)
        current_year = datetime.now().year
        age = current_year - birth_year  # 2025 - 2013 = 12
        gender_prefix = 'B' if gender.lower().startswith('b') else 'G'
        age_group = f"{gender_prefix}{age:02d}"  # "G12" or "B12"
    
    # Map NPL fields to games table columns
    # NPL uses 'region' which maps to 'conference' in the games table
    league = game.get('league', 'NPL')
    conference = game.get('region', '') or game.get('division', '')
    
    # Get game_date_iso from game_date if not provided
    game_date = game.get('game_date', '')
    game_date_iso = game.get('game_date_iso', '')
    if game_date and not game_date_iso:
        # Try to parse the date
        try:
            from dateutil import parser
            parsed = parser.parse(game_date)
            game_date_iso = parsed.strftime('%Y-%m-%d')
        except:
            game_date_iso = game_date
    
    cur.execute("""INSERT INTO games (game_id, game_date, game_date_iso, game_time, home_team, away_team, 
                  home_score, away_score, league, age_group, conference, location, game_status, source_url, scraped_at, gender)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
               (game_id, game_date, game_date_iso, game.get('game_time'),
                game.get('home_team') or game.get('home_team_normalized'),
                game.get('away_team') or game.get('away_team_normalized'),
                game.get('home_score'), game.get('away_score'),
                league, age_group, conference,
                game.get('location', ''), game.get('game_status', ''),
                game.get('source_url', ''), game.get('gender', 'Girls')))
    conn.commit()
    conn.close()
    return True


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_random_user_agent() -> str:
    """Get a random user agent from the pool."""
    return random.choice(USER_AGENTS)


# =============================================================================
# BIRTH YEAR RESOLUTION - CONTEXT CLUE METHOD (v4)
# =============================================================================
# 
# We do NOT convert U-age to birth year using arithmetic.
# Instead, we look for context clues in the same division:
#   - If "FC Dallas 2013G" and "Solar SC U13G" are in same division,
#     we know U13 = 2013 birth year for this division
#   - We use that context to normalize "Solar SC U13G" -> "solar sc 13g"
#
# If no context clues found, we keep the original format.
# =============================================================================

class BirthYearResolver:
    """
    Resolves U-age to birth year using context clues from the same division.
    Does NOT use arithmetic conversion.
    """
    
    def __init__(self):
        self.division_mappings: Dict[str, Dict[int, int]] = {}
    
    def extract_birth_year_from_name(self, name: str) -> Optional[int]:
        """
        Extract explicit birth year from team name.
        Returns the 2-digit birth year (e.g., 13 for 2013) or None.
        
        Matches: 2013G, 2012B, 13G, G13, 14B, B15
        Does NOT match: U13, BU14, GU15 (these are age-based)
        """
        if not name:
            return None
        
        # Full birth year: 2013G, 2012B, 2013, 2012
        full_year = re.search(r'\b(20[01]\d)([gbGB])?\b', name)
        if full_year:
            year = int(full_year.group(1))
            return year % 100  # 2013 -> 13
        
        # Birth year shorthand: 13G, 14B (NOT preceded by U)
        num_gender = re.search(r'(?<![Uu])(\d{2})([gbGB])\b', name)
        if num_gender:
            num = int(num_gender.group(1))
            if 7 <= num <= 18:
                return num
        
        # Gender first: G13, B14 (NOT followed by U)
        gender_num = re.search(r'\b([gbGB])(\d{2})(?![Uu])', name)
        if gender_num:
            num = int(gender_num.group(2))
            if 7 <= num <= 18:
                return num
        
        return None
    
    def extract_u_age_from_name(self, name: str) -> Optional[int]:
        """
        Extract U-age from team name.
        Matches: U13, U14G, BU12, GU15
        """
        if not name:
            return None
        
        u_age = re.search(r'\b[Uu][\s-]*(\d{1,2})([gbGB])?\b', name)
        if u_age:
            return int(u_age.group(1))
        
        bu_gu = re.search(r'\b[BbGg][Uu](\d{1,2})\b', name)
        if bu_gu:
            return int(bu_gu.group(1))
        
        return None
    
    def learn_from_division(self, team_names: List[str], division: str = None) -> Dict[int, int]:
        """
        Learn U-age to birth-year mapping from team names in same division.
        
        If we see "FC Dallas 2013G" and "Solar SC U13G" in the same division,
        we learn that U13 = 2013 (birth year 13).
        """
        mapping = {}
        
        birth_years_found: Set[int] = set()
        u_ages_found: Set[int] = set()
        
        for name in team_names:
            by = self.extract_birth_year_from_name(name)
            if by:
                birth_years_found.add(by)
            
            ua = self.extract_u_age_from_name(name)
            if ua:
                u_ages_found.add(ua)
        
        # Also check division name
        if division:
            div_by = self.extract_birth_year_from_name(division)
            if div_by:
                birth_years_found.add(div_by)
            div_ua = self.extract_u_age_from_name(division)
            if div_ua:
                u_ages_found.add(div_ua)
        
        # Match U-ages to birth years found in same division
        for ua in u_ages_found:
            for by in birth_years_found:
                full_by = 2000 + by
                # Approximate: in 2025, U13 = ~2012-2013 birth year
                expected_by_low = 2025 - ua
                expected_by_high = 2025 - ua + 2
                
                if expected_by_low <= full_by <= expected_by_high:
                    mapping[ua] = by
                    break
        
        return mapping
    
    def extract_gender_from_context(self, name: str, division: str = None) -> Optional[str]:
        """Extract gender from name or division."""
        combined = f"{name} {division or ''}".lower()
        
        if re.search(r'\b(girls?|women|female)\b', combined):
            return 'g'
        if re.search(r'\b(boys?|men|male)\b', combined):
            return 'b'
        
        if re.search(r'[gG](?=\d)|(?<=\d)[gG]', name):
            return 'g'
        if re.search(r'[bB](?=\d)|(?<=\d)[bB]', name):
            return 'b'
        
        return None
    
    def normalize_with_context(self, name: str, division_teams: List[str] = None,
                               division: str = None) -> str:
        """
        Normalize team name using context clues for birth year resolution.
        
        1. If name has explicit birth year (2013G, 13G, G13), use it directly
        2. If name has U-age (U13, BU12), look for context clues to resolve
        3. If no context clues, keep original format
        """
        if not name:
            return ""
        
        normalized = name.lower().strip()
        
        # Remove league suffixes
        league_patterns = [
            r'\s+npl\s*$', r'\s+ecnl\s*$', r'\s+ecnl[\s-]*rl\s*$',
            r'\s+ga\s*$', r'\s+girls\s*academy\s*$', r'\s+aspire\s*$',
            r'\s+premier\s*$', r'\s+elite\s*$', r'\s+academy\s*$', r'\s+select\s*$',
        ]
        for pattern in league_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.I)
        
        # Check if already has birth year format - just clean up
        explicit_by = self.extract_birth_year_from_name(name)
        if explicit_by:
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        
        # Check for U-age that needs resolution
        u_age = self.extract_u_age_from_name(name)
        if u_age and division_teams:
            mapping = self.learn_from_division(division_teams, division)
            
            if u_age in mapping:
                birth_year = mapping[u_age]
                gender = self.extract_gender_from_context(name, division)
                
                if gender:
                    replacement = f"{birth_year}{gender}"
                else:
                    replacement = str(birth_year)
                
                # Replace U-age patterns with birth year
                normalized = re.sub(r'\b[Uu][\s-]*\d{1,2}([gbGB])\b', 
                                   lambda m: f"{birth_year}{m.group(1).lower()}", 
                                   normalized, flags=re.I)
                normalized = re.sub(r'\b[Uu][\s-]*\d{1,2}\b', 
                                   replacement, normalized, flags=re.I)
                normalized = re.sub(r'\b([BbGg])[Uu](\d{1,2})\b',
                                   lambda m: f"{birth_year}{m.group(1).lower()}",
                                   normalized, flags=re.I)
        
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized


# Global resolver instance
birth_year_resolver = BirthYearResolver()


def normalize_team_name(name: str, division_teams: List[str] = None, division: str = None) -> str:
    """
    Normalize team name for matching across leagues.
    Uses context clues to resolve U-age to birth year when possible.
    """
    if division_teams:
        return birth_year_resolver.normalize_with_context(name, division_teams, division)
    
    # Fallback to basic normalization if no context
    if not name:
        return ""
    
    normalized = name.lower().strip()
    
    # Remove league suffixes
    league_patterns = [
        r'\s+npl\s*$', r'\s+ecnl\s*$', r'\s+ecnl[\s-]*rl\s*$',
        r'\s+ga\s*$', r'\s+girls\s*academy\s*$', r'\s+aspire\s*$',
        r'\s+premier\s*$', r'\s+elite\s*$', r'\s+academy\s*$', r'\s+select\s*$',
    ]
    for pattern in league_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.I)
    
    # Clean up whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def extract_club_name(team_name: str) -> str:
    """
    Extract the club name from a team name.
    
    v9 FIX: Better handle doubled patterns like "Steel City FC Steel City FC"
    v9 FIX: Detect when club name appears twice in team name
    
    v7 FIX: Better handle:
    - Multi-word abbreviations like "KC SURF" after club name
    - State abbreviations like "Mo" in "Missouri Rush Mo Rush"
    - Partial year patterns like "08/07", "/08", "07/"
    - Doubled patterns where abbreviation follows club name
    
    Examples:
    - "Kansas City Surf KC SURF NPL 12G" -> "Kansas City Surf"
    - "Missouri Rush Mo Rush 2012G NPL White" -> "Missouri Rush"  
    - "Gretna Elite Academy GEA NPL G07/08" -> "Gretna Elite Academy"
    - "Steel City FC Steel City FC 2013G Premier" -> "Steel City FC"
    """
    if not team_name:
        return ""
    
    club = team_name.strip()
    original_words = club.split()
    words = original_words.copy()
    
    # v9 FIX: PASS 0 - Detect exact doubled club names
    # "Steel City FC Steel City FC 2013G" -> first 3 words repeat
    if len(words) >= 4:
        for prefix_len in range(2, min(6, len(words) // 2 + 1)):
            prefix = ' '.join(words[:prefix_len]).lower()
            remaining = ' '.join(words[prefix_len:]).lower()
            
            # Check if the prefix appears again at start of remaining
            if remaining.startswith(prefix):
                # Found doubled pattern, return just the first occurrence
                club = ' '.join(words[:prefix_len])
                words = club.split()
                break
    
    # PASS 1: Detect full doubled sequences (e.g., "Gateway Rush" appears twice)
    if len(words) >= 4:
        found_repeat = False
        for prefix_len in range(2, min(5, len(words) // 2 + 1)):
            prefix_words = [w.lower() for w in words[:prefix_len]]
            rest_words = words[prefix_len:]
            
            # Look for where the prefix appears again in rest
            for i in range(len(rest_words) - prefix_len + 1):
                rest_slice = [w.lower() for w in rest_words[i:i+prefix_len]]
                if rest_slice == prefix_words:
                    # Found a repeat! Keep everything before the repeat
                    club = ' '.join(words[:prefix_len + i])
                    words = club.split()
                    found_repeat = True
                    break
            if found_repeat:
                break
    
    # PASS 2: Look for patterns where first word(s) appear again later
    # This handles: "Potomac Soccer Association Potomac Black 13B"
    common_words = {'city', 'club', 'soccer', 'fc', 'sc', 'united', 'elite', 'academy', 'association'}
    
    if len(words) >= 4:
        for word_idx in range(min(2, len(words))):
            first_word = words[word_idx].lower()
            if first_word in common_words or len(first_word) < 3:
                continue
            
            for check_idx in range(word_idx + 2, len(words)):
                check_word = words[check_idx].lower()
                if check_word == first_word:
                    club = ' '.join(words[:check_idx])
                    words = club.split()
                    break
            else:
                continue
            break
    
    # v7 FIX: Detect abbreviation patterns like "Kansas City Surf KC SURF"
    # Look for 2-3 consecutive CAPS/abbreviated words after meaningful words
    if len(words) >= 4:
        for i in range(2, len(words) - 1):
            # Check if words[i] and words[i+1] look like abbreviations (all caps, short)
            w1, w2 = words[i], words[i+1] if i+1 < len(words) else ''
            if w1.isupper() and len(w1) <= 4 and w2 and (w2.isupper() or w2[0].isupper()):
                # Check if this might be "KC SURF" type pattern
                # Truncate to before the abbreviation
                club = ' '.join(words[:i])
                words = club.split()
                break
    
    # Remove age patterns including partial years
    club = re.sub(r'\bU[\s-]*\d{1,2}[GB]?\b', '', club, flags=re.I)
    club = re.sub(r'\b[GB]\d{1,2}\b', '', club, flags=re.I)
    club = re.sub(r'\b\d{1,2}[GB]\b', '', club, flags=re.I)
    club = re.sub(r'\b20\d{2}[GB]?\b', '', club, flags=re.I)
    
    # v7 FIX: Remove partial year patterns like "08/07", "/08", "07/", "08/"
    club = re.sub(r'\s+\d{2}/\d{2}\b', '', club)
    club = re.sub(r'\s+\d{2}/\s*$', '', club)
    club = re.sub(r'\s+/\d{2}\s*$', '', club)
    club = re.sub(r'\s+/\d{2}\b', '', club)
    
    # Remove league suffixes
    club = re.sub(r'\s+\b(NPL|ECNL|ECNL-RL|GA|Girls Academy|Aspire|Premier|Select)\b\s*', ' ', club, flags=re.I)
    
    # v7 FIX: Only remove trailing Elite/Academy if NOT part of "Elite Academy" pattern
    # "Gretna Elite Academy" should stay, but "Some Club Academy" can lose "Academy"
    words_after_clean = club.split()
    if len(words_after_clean) > 2:
        # Don't remove "Academy" if preceded by "Elite" (as in "Elite Academy")
        if not (words_after_clean[-1].lower() == 'academy' and 
                len(words_after_clean) >= 2 and words_after_clean[-2].lower() == 'elite'):
            club = re.sub(r'\s+Academy\s*$', '', club, flags=re.I)
        # Don't remove "Elite" if followed by "Academy" - but Academy would be at end
        # So only remove "Elite" if it's truly standalone at end
        if words_after_clean[-1].lower() == 'elite':
            club = re.sub(r'\s+Elite\s*$', '', club, flags=re.I)
    
    club = re.sub(r'\s+(Girls|Boys|Girl|Boy)\s*$', '', club, flags=re.I)
    club = re.sub(r'\s+(Girls|Boys)\s+(United|Elite|Premier|Blue|Red|White|Black|Gold|Green|Navy|Gray|Grey)\s*$', '', club, flags=re.I)
    
    # Remove trailing color/team identifiers
    club = re.sub(r'\s+(Blue|Red|White|Black|Gold|Green|Navy|Gray|Grey|United|Premier)\s*$', '', club, flags=re.I)
    
    # Remove trailing West/East etc
    club = re.sub(r'\s+[A-Z]{2,5}\s+(West|East|North|South)\s*$', '', club, flags=re.I)
    
    # v7 FIX: Final cleanup - remove trailing abbreviations more aggressively
    # Protected words that are meaningful parts of club names
    protected_words = {'club', 'fc', 'sc', 'soccer', 'city', 'united', 'elite', 'rush', 'surf', 
                       'fire', 'heat', 'wave', 'academy', 'association'}
    
    # State abbreviations to always remove
    state_abbrevs = {'mo', 'kc', 'dc', 'la', 'ny', 'nj', 'pa', 'va', 'md', 'tx', 'ca', 'fl', 'ga', 'nc'}
    
    words_list = club.split()
    for _ in range(3):  # Multiple passes for stacked abbreviations
        if len(words_list) >= 2:
            last_word = words_list[-1]
            last_lower = last_word.lower()
            
            # Always remove state abbreviations at end
            if last_lower in state_abbrevs:
                words_list = words_list[:-1]
                club = ' '.join(words_list)
                continue
            
            # Special case: "CiTY" style abbreviations
            if last_lower == 'city' and last_word != 'City' and last_word != 'city':
                words_list = words_list[:-1]
                club = ' '.join(words_list)
                continue
            
            # Remove short all-caps words that aren't protected
            if last_lower not in protected_words and 2 <= len(last_word) <= 5:
                is_abbrev = last_word.isupper() or (last_word[0].isupper() and any(c.isupper() for c in last_word[1:]))
                if is_abbrev:
                    words_list = words_list[:-1]
                    club = ' '.join(words_list)
    
    return re.sub(r'\s+', ' ', club).strip()


def extract_age_group(text: str, team_names: List[str] = None) -> str:
    """
    Extract age group from text, ALWAYS converting to birth year format.
    
    v9 FIX: Convert U-format ages to birth years (U14 -> 2011 for 2025)
    v9 FIX: Extract from team names when division has no age info
    v9 FIX: Handle B2014, G2017, '14, '15 patterns in team names
    
    Args:
        text: Division or section text
        team_names: Optional list of team names to search for age clues
    
    Returns:
        Birth year string (e.g., "2011") or empty string
    """
    if not text:
        text = ""
    
    # Skip pure division markers that aren't age groups
    if re.match(r'^NPL\s*\d+$', text.strip(), re.I):
        text = ""  # Clear it so we try team names
    if text.strip().lower() in ['schedule', 'results', 'standings']:
        text = ""
    
    current_year = 2025  # Base year for U-age conversion
    
    def u_age_to_birth_year(u_age: int) -> str:
        """Convert U-age to birth year (U14 in 2025 = born 2011)"""
        return str(current_year - u_age)
    
    # Try to extract from the main text first
    result = _extract_age_from_text(text, u_age_to_birth_year)
    if result:
        return result
    
    # v9 FIX: If no age found in division, try team names
    if team_names:
        for team_name in team_names:
            if team_name:
                result = _extract_age_from_text(team_name, u_age_to_birth_year)
                if result:
                    return result
    
    return ""


def _extract_age_from_text(text: str, u_age_converter) -> str:
    """
    Extract age from a single text string.
    
    v9 FIX: Helper function to extract birth year from any text source.
    v10 FIX: Handle 2013B, 2013G formats (year followed by gender suffix)
    """
    if not text:
        return ""
    
    # Birth year with gender word: "Girls 2013", "Boys 2012"
    birth_year_with_word = re.search(r'\b(Girls?|Boys?)\s*(20\d{2})\b', text, re.I)
    if birth_year_with_word:
        return birth_year_with_word.group(2)
    
    # B2014 / G2017 format (common in team names)
    bg_year = re.search(r'\b[BG](20\d{2})\b', text, re.I)
    if bg_year:
        return bg_year.group(1)
    
    # v10 FIX: 2013B / 2013G format (birth year followed by gender suffix)
    year_with_suffix = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))[BG]\b', text, re.I)
    if year_with_suffix:
        return year_with_suffix.group(1)
    
    # Birth year format: 2013, 2012, etc. (standalone 4-digit year 2005-2025)
    birth_year = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))\b', text)
    if birth_year:
        return birth_year.group(1)
    
    # Apostrophe year: '14, '15 (convert to birth year)
    apostrophe_year = re.search(r"'(\d{2})\b", text)
    if apostrophe_year:
        year_2digit = int(apostrophe_year.group(1))
        if 5 <= year_2digit <= 25:  # Valid birth years '05 to '25
            return f"20{year_2digit:02d}"
    
    # U-age format: U13, U-13, U13G, U13B - CONVERT TO BIRTH YEAR
    u_age = re.search(r'\bU[\s-]*(\d{1,2})([GB])?\b', text, re.I)
    if u_age:
        age = int(u_age.group(1))
        if 6 <= age <= 19:  # Valid U-ages
            return u_age_converter(age)
    
    # BU/GU format: BU13, GU14 - CONVERT TO BIRTH YEAR
    bu_gu = re.search(r'\b([BG])U(\d{1,2})\b', text, re.I)
    if bu_gu:
        age = int(bu_gu.group(2))
        if 6 <= age <= 19:
            return u_age_converter(age)
    
    # G13/B13 format - CONVERT TO BIRTH YEAR
    gb_first = re.search(r'\b([GB])(\d{2})\b', text, re.I)
    if gb_first:
        age = int(gb_first.group(2))
        if 6 <= age <= 19:
            return u_age_converter(age)
    
    # 13G/14B format - CONVERT TO BIRTH YEAR
    gb_last = re.search(r'\b(\d{2})([GB])\b', text, re.I)
    if gb_last:
        age = int(gb_last.group(1))
        if 6 <= age <= 19:
            return u_age_converter(age)
    
    # Under XX format: "Under 14 Boys"
    under_age = re.search(r'\bUnder\s*(\d{1,2})\b', text, re.I)
    if under_age:
        age = int(under_age.group(1))
        if 6 <= age <= 19:
            return u_age_converter(age)
    
    return ""


def extract_gender(text: str, age_group_text: str = "", team_names: List[str] = None, default: str = "Both") -> str:
    """
    Extract gender from text, age group, or team names.
    
    v9 FIX: Better gender detection from multiple sources
    v9 FIX: Check age_group suffix (U14B -> Boys, U14G -> Girls)
    v9 FIX: Search team names for "Girls" or "Boys" keywords
    
    Args:
        text: Primary text to search (division, section)
        age_group_text: Age group text that may contain gender suffix
        team_names: List of team names to search
        default: Default gender if not detected
    
    Returns:
        "Girls", "Boys", or default
    """
    # Check primary text
    if text:
        text_lower = text.lower()
        if 'girl' in text_lower or 'female' in text_lower:
            return "Girls"
        if 'boy' in text_lower or 'male' in text_lower:
            return "Boys"
        
        # Check for G/B markers in primary text
        if re.search(r'\bG\d{2}\b|\b\d{2}G\b|20\d{2}G\b|\bGU\d+\b', text, re.I):
            return "Girls"
        if re.search(r'\bB\d{2}\b|\b\d{2}B\b|20\d{2}B\b|\bBU\d+\b', text, re.I):
            return "Boys"
    
    # v9 FIX: Check age_group_text for gender suffix
    if age_group_text:
        age_lower = age_group_text.lower()
        # U14B, U14G patterns
        if re.search(r'u\d+b\b', age_lower):
            return "Boys"
        if re.search(r'u\d+g\b', age_lower):
            return "Girls"
        # BU14, GU14 patterns
        if re.search(r'\bbu\d+', age_lower):
            return "Boys"
        if re.search(r'\bgu\d+', age_lower):
            return "Girls"
        # B2014, G2014 patterns
        if re.search(r'\bb20\d{2}\b', age_lower):
            return "Boys"
        if re.search(r'\bg20\d{2}\b', age_lower):
            return "Girls"
    
    # v9 FIX: Check team names for gender keywords
    if team_names:
        for team_name in team_names:
            if team_name:
                team_lower = team_name.lower()
                if ' girls ' in team_lower or ' girls' in team_lower or 'girls ' in team_lower:
                    return "Girls"
                if ' boys ' in team_lower or ' boys' in team_lower or 'boys ' in team_lower:
                    return "Boys"
                # Check G/B patterns in team names
                if re.search(r'\bG20\d{2}\b|\b20\d{2}G\b|\bGU?\d{2}\b', team_name, re.I):
                    return "Girls"
                if re.search(r'\bB20\d{2}\b|\b20\d{2}B\b|\bBU?\d{2}\b', team_name, re.I):
                    return "Boys"
    
    return default


def generate_game_id(league: str, age_group: str, game_date: str,
                     home_team: str, away_team: str) -> str:
    """Generate unique game ID including age to prevent collisions."""
    league_clean = re.sub(r'[^a-zA-Z0-9]', '', league.lower())[:20]
    age_clean = re.sub(r'[^a-zA-Z0-9]', '', age_group.upper()) if age_group else "NOAGE"
    date_clean = game_date if game_date else "NODATE"
    home_clean = re.sub(r'[^a-zA-Z0-9]', '', home_team.lower())[:25]
    away_clean = re.sub(r'[^a-zA-Z0-9]', '', away_team.lower())[:25]
    
    teams_sorted = sorted([home_clean, away_clean])
    return f"{league_clean}_{age_clean}_{date_clean}_{teams_sorted[0]}_{teams_sorted[1]}"


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    formats = [
        "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y",
        "%m/%d/%y", "%d %b %Y", "%d-%b-%Y", "%Y/%m/%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def parse_time(time_str: str) -> Optional[str]:
    """
    Parse various time formats to HH:MM.
    
    Handles formats like:
    - "1:00 PM", "1:00PM", "9:00 AM EDT"
    - "13:00", "09:30"
    
    v5 FIX: Be more strict about time boundaries to avoid matching
    year digits concatenated with time (e.g., "20259:00 AM" should extract "9:00 AM" not "59:00")
    
    v7 FIX: Better handle year-concatenated times like "20255:30PM" -> "5:30PM"
    """
    if not time_str:
        return None
    
    time_str = time_str.strip()
    
    # First, try to find a proper time pattern with AM/PM (most reliable)
    # This pattern requires either start of string, whitespace, or non-digit before the time
    am_pm_match = re.search(r'(?:^|[^\d])(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.I)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minute = am_pm_match.group(2)
        meridiem = am_pm_match.group(3).upper()
        
        if meridiem == 'PM' and hour < 12:
            hour += 12
        elif meridiem == 'AM' and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute}"
    
    # v7 FIX: Handle year-concatenated times like "20255:30PM" or "20259:00 AM"
    # Look for a pattern like 202X followed by a single digit time
    year_concat_match = re.search(r'202\d(\d):(\d{2})\s*(AM|PM)', time_str, re.I)
    if year_concat_match:
        hour = int(year_concat_match.group(1))
        minute = year_concat_match.group(2)
        meridiem = year_concat_match.group(3).upper()
        
        if 1 <= hour <= 12:  # Valid hour for AM/PM format
            if meridiem == 'PM' and hour < 12:
                hour += 12
            elif meridiem == 'AM' and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute}"
    
    # Also handle "202512:30PM" -> 12:30PM
    year_concat_match2 = re.search(r'202\d(1[0-2]):(\d{2})\s*(AM|PM)', time_str, re.I)
    if year_concat_match2:
        hour = int(year_concat_match2.group(1))
        minute = year_concat_match2.group(2)
        meridiem = year_concat_match2.group(3).upper()
        
        if meridiem == 'PM' and hour < 12:
            hour += 12
        elif meridiem == 'AM' and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute}"
    
    # Try AM/PM match from start of string (for extracted times like "9:00 AM")
    am_pm_start = re.match(r'^(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.I)
    if am_pm_start:
        hour = int(am_pm_start.group(1))
        minute = am_pm_start.group(2)
        meridiem = am_pm_start.group(3).upper()
        
        if meridiem == 'PM' and hour < 12:
            hour += 12
        elif meridiem == 'AM' and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute}"
    
    # Try 24-hour format with proper boundaries (not part of a year)
    # Must be preceded by space, start, or non-digit
    time_24_match = re.search(r'(?:^|\s|[^\d])(\d{1,2}):(\d{2})(?:\s|$|[^\d])', time_str)
    if time_24_match:
        hour = int(time_24_match.group(1))
        minute = time_24_match.group(2)
        
        # Validate hour range
        if 0 <= hour <= 23:
            return f"{hour:02d}:{minute}"
    
    # Fallback: simple time pattern at start (for extracted times like "9:00")
    simple_match = re.match(r'^(\d{1,2}):(\d{2})$', time_str.strip())
    if simple_match:
        hour = int(simple_match.group(1))
        minute = simple_match.group(2)
        if 0 <= hour <= 23:
            return f"{hour:02d}:{minute}"
    
    return None


def parse_score(score_str: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse score string to (home, away) tuple."""
    if not score_str:
        return None, None
    
    match = re.match(r'(\d+)\s*[-:]\s*(\d+)', score_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2))
    
    return None, None


def determine_game_status(game_date: str, home_score: Optional[int],
                          away_score: Optional[int]) -> str:
    """
    Determine if game is completed, scheduled, or unknown.
    
    v9 FIX: Games without scores are NEVER marked "completed"
    v9 FIX: Past games without scores are "unknown" not "completed"
    
    Returns:
        "completed" - has scores
        "scheduled" - future game
        "unknown" - past game without scores
    """
    # v9 FIX: Only mark completed if we have BOTH scores
    if home_score is not None and away_score is not None:
        return "completed"
    
    if game_date:
        try:
            game_dt = datetime.strptime(game_date, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if game_dt < today:
                # v9 FIX: Past game without score = unknown, not completed
                return "unknown"
            else:
                return "scheduled"
        except:
            pass
    
    return "scheduled"


# =============================================================================
# DIAGNOSTIC LOGGER
# =============================================================================

class DiagnosticLogger:
    """Handles all diagnostic output with different verbosity levels."""
    
    def __init__(self, debug: bool = False, quiet: bool = False):
        self.debug = debug
        self.quiet = quiet
        self.start_time = datetime.now()
        self.errors: List[Dict] = []
        self.warnings: List[str] = []
    
    def header(self, text: str):
        """Print a major header."""
        if not self.quiet:
            print("\n" + "=" * 70)
            print(text)
            print("=" * 70)
    
    def subheader(self, text: str):
        """Print a sub-header."""
        if not self.quiet:
            print("\n" + "-" * 50)
            print(f"  {text}")
            print("-" * 50)
    
    def info(self, text: str):
        """Print info message."""
        if not self.quiet:
            print(f"  {text}")
    
    def success(self, text: str):
        """Print success message."""
        if not self.quiet:
            print(f"  ✅ {text}")
    
    def warning(self, text: str):
        """Print warning message."""
        self.warnings.append(text)
        if not self.quiet:
            print(f"  ⚠️  {text}")
    
    def error(self, text: str, exception: Optional[Exception] = None):
        """Print error message and store for summary."""
        error_info = {'message': text, 'time': datetime.now().isoformat()}
        if exception:
            error_info['exception'] = str(exception)
            error_info['traceback'] = traceback.format_exc()
        self.errors.append(error_info)
        
        if not self.quiet:
            print(f"  ❌ {text}")
            if self.debug and exception:
                traceback.print_exc()
    
    def debug_msg(self, text: str):
        """Print debug message (only if debug mode enabled)."""
        if self.debug:
            print(f"  🔍 DEBUG: {text}")
    
    def progress(self, current: int, total: int, item: str):
        """Print progress indicator."""
        if not self.quiet:
            pct = (current / total * 100) if total > 0 else 0
            print(f"\n  [{current}/{total}] ({pct:.0f}%) {item}")
    
    def stats(self, label: str, value: any):
        """Print a stat line."""
        if not self.quiet:
            print(f"     {label}: {value}")
    
    def delay_message(self, seconds: float):
        """Print delay message."""
        if not self.quiet:
            print(f"  ⏳ Waiting {seconds:.1f}s...")
    
    def coffee_break(self, seconds: float):
        """Print coffee break message."""
        if not self.quiet:
            print(f"\n  ☕ Taking a coffee break for {seconds:.1f}s...")
            print(f"     (This looks more human and helps avoid detection)")
    
    def coffee_break_end(self):
        """Print coffee break end message."""
        if not self.quiet:
            print(f"  ☕ Break over! Continuing...\n")
    
    def summary(self, stats: Dict):
        """Print final summary."""
        duration = datetime.now() - self.start_time
        
        print("\n" + "=" * 70)
        print("📊 SCRAPING SUMMARY")
        print("=" * 70)
        print(f"   ⏱️  Duration: {duration}")
        print(f"   🏆 Leagues scraped: {stats.get('leagues_scraped', 0)}")
        print(f"   📋 Schedules processed: {stats.get('schedules_scraped', 0)}")
        print(f"   🎮 Games found: {stats.get('games_found', 0)}")
        print(f"   ✨ New games: {stats.get('games_new', 0)}")
        print(f"   🔄 Duplicates skipped: {stats.get('games_duplicate', 0)}")
        print(f"   👥 Teams found: {stats.get('teams_found', 0)}")
        print(f"   ❌ Errors: {len(self.errors)}")
        print(f"   ⚠️  Warnings: {len(self.warnings)}")
        print("=" * 70)
        
        if stats.get('games_csv'):
            print(f"\n   📁 Games CSV: {stats['games_csv']}")
        if stats.get('teams_csv'):
            print(f"   📁 Teams CSV: {stats['teams_csv']}")
        
        if self.errors and self.debug:
            print("\n   🔴 ERRORS:")
            for err in self.errors[:10]:
                print(f"      - {err['message']}")
        
        print("=" * 70)


# =============================================================================
# HUMAN-LIKE BEHAVIOR
# =============================================================================

class HumanBehavior:
    """Manages human-like delays and breaks."""
    
    def __init__(self, logger: DiagnosticLogger):
        self.logger = logger
        self.request_count = 0
        self.next_break_at = random.randint(COFFEE_BREAK_INTERVAL[0], COFFEE_BREAK_INTERVAL[1])
    
    async def delay(self, min_sec: float = MIN_DELAY, max_sec: float = MAX_DELAY):
        """Human-like delay with occasional reading pauses."""
        # 20% chance of longer pause (simulating reading)
        if random.random() < READING_PAUSE_CHANCE:
            delay = random.uniform(max_sec, max_sec * 1.5)
            self.logger.debug_msg(f"Extended reading pause: {delay:.1f}s")
        else:
            delay = random.uniform(min_sec, max_sec)
        
        self.logger.delay_message(delay)
        await asyncio.sleep(delay)
    
    async def maybe_coffee_break(self):
        """Take a coffee break if it's time."""
        self.request_count += 1
        
        if self.request_count >= self.next_break_at:
            break_time = random.uniform(MIN_COFFEE_BREAK, MAX_COFFEE_BREAK)
            self.logger.coffee_break(break_time)
            await asyncio.sleep(break_time)
            self.logger.coffee_break_end()
            
            # Reset for next break
            self.request_count = 0
            self.next_break_at = random.randint(COFFEE_BREAK_INTERVAL[0], COFFEE_BREAK_INTERVAL[1])
    
    async def random_scroll(self, page: Page):
        """Simulate human-like scrolling behavior."""
        try:
            await page.evaluate("""
                () => {
                    const scrollAmount = Math.random() * 500 + 200;
                    window.scrollBy({
                        top: scrollAmount,
                        behavior: 'smooth'
                    });
                }
            """)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Sometimes scroll back up a bit
            if random.random() < 0.3:
                await page.evaluate("window.scrollTo(0, Math.random() * 200)")
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except:
            pass  # Ignore scroll errors


# =============================================================================
# CSV EXPORTER
# =============================================================================

class CSVExporter:
    """Handles CSV export with deduplication and database saving (v13)."""
    
    def __init__(self, output_dir: str, logger: DiagnosticLogger):
        self.output_dir = output_dir
        self.logger = logger
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # v12: Include version number in output filenames for tracking
        self.games_file = os.path.join(output_dir, f"npl_games_{SCRAPER_VERSION}_{timestamp}.csv")
        self.teams_file = os.path.join(output_dir, f"npl_teams_{SCRAPER_VERSION}_{timestamp}.csv")
        
        self.seen_game_ids: Set[str] = set()
        self.seen_team_keys: Set[str] = set()
        
        self.stats = {
            'games_written': 0,
            'games_skipped_duplicate': 0,
            'games_saved_to_db': 0,
            'teams_written': 0,
            'teams_skipped_duplicate': 0,
            'teams_saved_to_db': 0,
        }
        
        # v14: Find database path for game and team saving
        self.db_path = find_database_path()
        if self.db_path:
            self.logger.info(f"📂 Database found: {self.db_path}")
        else:
            self.logger.warning("⚠️ Database not found - games and teams will only be saved to CSV")
        
        self._init_files()
    
    def _init_files(self):
        """Initialize CSV files with headers."""
        with open(self.games_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=GAMES_CSV_COLUMNS)
            writer.writeheader()
        
        with open(self.teams_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=TEAMS_CSV_COLUMNS)
            writer.writeheader()
        
        self.logger.info(f"📁 Games CSV: {self.games_file}")
        self.logger.info(f"📁 Teams CSV: {self.teams_file}")
    
    def write_game(self, game: Dict) -> bool:
        """Write a game to CSV and database (v14), returns True if written."""
        game_id = game.get('game_id', '')
        
        if game_id in self.seen_game_ids:
            self.stats['games_skipped_duplicate'] += 1
            return False
        
        self.seen_game_ids.add(game_id)
        
        row = {col: game.get(col, '') for col in GAMES_CSV_COLUMNS}
        row['scraped_at'] = datetime.now().isoformat()
        
        with open(self.games_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=GAMES_CSV_COLUMNS)
            writer.writerow(row)
        
        self.stats['games_written'] += 1
        
        # v14: Also save to database
        if self.db_path:
            try:
                if save_npl_game_to_db(self.db_path, game):
                    self.stats['games_saved_to_db'] += 1
            except Exception as e:
                self.logger.debug_msg(f"Database game save error: {e}")
        
        return True
    
    def write_team(self, team: Dict) -> bool:
        """Write a team to CSV and database (v13), returns True if written."""
        team_key = f"{team.get('team_name_normalized', '')}_{team.get('league', '')}_{team.get('age_group', '')}"
        
        if team_key in self.seen_team_keys:
            self.stats['teams_skipped_duplicate'] += 1
            return False
        
        self.seen_team_keys.add(team_key)
        
        row = {col: team.get(col, '') for col in TEAMS_CSV_COLUMNS}
        row['discovered_at'] = datetime.now().isoformat()
        
        with open(self.teams_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=TEAMS_CSV_COLUMNS)
            writer.writerow(row)
        
        self.stats['teams_written'] += 1
        
        # v13: Also save to database
        if self.db_path:
            try:
                if save_npl_team_to_db(self.db_path, team):
                    self.stats['teams_saved_to_db'] += 1
            except Exception as e:
                self.logger.debug_msg(f"Database save error: {e}")
        
        return True


# =============================================================================
# GOTSPORT SCRAPER
# =============================================================================

class GotSportScraper:
    """Scraper for GotSport platform using Playwright."""
    
    def __init__(self, csv_exporter: CSVExporter, logger: DiagnosticLogger,
                 human: HumanBehavior, time_filter: str = 'all', days_back: int = None,
                 take_screenshots: bool = True):
        self.csv = csv_exporter
        self.logger = logger
        self.human = human
        self.time_filter = time_filter
        self.days_back = days_back
        self.take_screenshots = take_screenshots
        
        self.stats = {
            'leagues_scraped': 0,
            'schedules_scraped': 0,
            'games_found': 0,
            'teams_found': 0,
            'errors': 0,
        }
    
    async def safe_screenshot(self, page: Page, path: str) -> bool:
        """
        Take a screenshot safely - don't let it crash the scrape.
        Returns True if screenshot was taken, False otherwise.
        """
        if not self.take_screenshots:
            return False
        
        try:
            await page.screenshot(path=path, full_page=True, timeout=SCREENSHOT_TIMEOUT)
            self.logger.debug_msg(f"Screenshot saved: {path}")
            return True
        except Exception as e:
            self.logger.warning(f"Screenshot skipped (non-fatal): {str(e)[:50]}...")
            return False
    
    async def scrape_team_details(self, page: Page, team_url: str) -> Dict:
        """
        v19: Scrape location details from a team's profile page on GotSport.
        Extracts city, state, zip code, and street address if available.
        Similar to ECNL scraper's approach but adapted for GotSport.
        """
        details = {}
        
        if not team_url or 'gotsport.com' not in team_url:
            return details
        
        try:
            # Navigate to team page
            await page.goto(team_url, wait_until='domcontentloaded', timeout=30000)
            await self.human.delay(1, 2)
            
            # Extract location info using JavaScript
            location_info = await page.evaluate("""
                () => {
                    const info = {};
                    
                    // State name to abbreviation mapping
                    const stateMap = {
                        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
                        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
                        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
                        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
                        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
                        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
                        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
                        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
                        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
                        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
                        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
                        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
                        'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
                    };
                    
                    // Valid 2-letter state codes
                    const stateCodes = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID',
                        'IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE',
                        'NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
                        'TX','UT','VT','VA','WA','WV','WI','WY','DC'];
                    
                    // Get page text
                    const bodyText = document.body.innerText || '';
                    const addressBlock = bodyText.replace(/\\t/g, ' ').replace(/  +/g, ' ');
                    
                    // Find 5-digit ZIP code (most reliable marker)
                    const zipMatches = addressBlock.match(/\\b(\\d{5})\\b/g);
                    if (zipMatches && zipMatches.length > 0) {
                        for (const zip of zipMatches) {
                            const lines = addressBlock.split('\\n').map(l => l.trim()).filter(l => l);
                            
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i];
                                if (line.includes(zip)) {
                                    info.zip = zip;
                                    
                                    // Parse this line for city and state
                                    const beforeZip = line.substring(0, line.indexOf(zip)).trim();
                                    
                                    let foundState = null;
                                    let foundCity = null;
                                    
                                    // Check for 2-letter state code
                                    for (const code of stateCodes) {
                                        const codeRegex = new RegExp('\\\\b' + code + '\\\\b', 'i');
                                        if (codeRegex.test(beforeZip)) {
                                            foundState = code;
                                            const stateIdx = beforeZip.search(codeRegex);
                                            foundCity = beforeZip.substring(0, stateIdx).replace(/,\\s*$/, '').trim();
                                            break;
                                        }
                                    }
                                    
                                    // If no 2-letter code, check for full state names
                                    if (!foundState) {
                                        for (const [stateName, code] of Object.entries(stateMap)) {
                                            const nameRegex = new RegExp('\\\\b' + stateName + '\\\\b', 'i');
                                            if (nameRegex.test(beforeZip)) {
                                                foundState = code;
                                                const stateIdx = beforeZip.search(nameRegex);
                                                foundCity = beforeZip.substring(0, stateIdx).replace(/,\\s*$/, '').trim();
                                                break;
                                            }
                                        }
                                    }
                                    
                                    if (foundState) {
                                        info.state = foundState;
                                        if (foundCity) {
                                            info.city = foundCity.replace(/[,;:]$/, '').trim();
                                        }
                                    }
                                    
                                    // Get address from line above city/state/zip
                                    if (i > 0) {
                                        const addressLine = lines[i - 1];
                                        if (/\\d/.test(addressLine) || /p\\.?o\\.?\\s*box/i.test(addressLine)) {
                                            info.address = addressLine.replace(/[\\n\\r]/g, ' ').trim();
                                        }
                                    }
                                    
                                    if (info.zip && info.state) {
                                        break;
                                    }
                                }
                            }
                            
                            if (info.zip && info.state) {
                                break;
                            }
                        }
                    }
                    
                    // Clean all values
                    for (const key of Object.keys(info)) {
                        if (typeof info[key] === 'string') {
                            info[key] = info[key].replace(/[\\n\\r\\t]/g, ' ').replace(/  +/g, ' ').trim();
                        }
                    }
                    
                    return info;
                }
            """)
            
            if location_info:
                details['city'] = location_info.get('city', '')
                details['state'] = location_info.get('state', '')
                details['zip_code'] = location_info.get('zip', '')
                details['street_address'] = location_info.get('address', '')
                
        except Exception as e:
            self.logger.debug_msg(f"Team details error for {team_url}: {e}")
        
        return details
    
    async def scrape_league(self, page: Page, league: LeagueConfig) -> Tuple[List[Dict], List[Dict]]:
        """Scrape all games and teams from a GotSport league event."""
        games = []
        teams = []
        
        self.logger.header(f"🏆 {league.name}")
        self.logger.info(f"📍 Region: {league.region} | Tier: {league.tier}")
        self.logger.info(f"👥 Gender: {league.gender} | Ages: {league.age_groups}")
        self.logger.info(f"🔗 {league.url}")
        
        try:
            # Navigate to event page
            self.logger.info("🌐 Loading event page...")
            await page.goto(league.url, timeout=60000)
            await self.human.delay(3, 5)
            
            # Take screenshot for debugging (non-blocking in v4)
            screenshot_dir = os.path.join(self.csv.output_dir, "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"{screenshot_dir}/{league.event_id}_{timestamp}.png"
            await self.safe_screenshot(page, screenshot_path)
            
            # Scroll around like a human
            await self.human.random_scroll(page)
            
            # Find schedule sections
            schedule_sections = await self._find_schedule_sections(page)
            self.logger.info(f"📋 Found {len(schedule_sections)} schedule sections")
            
            if not schedule_sections:
                self.logger.warning("No schedule sections found - trying alternate selectors")
                schedule_sections = await self._find_alternate_sections(page)
                self.logger.info(f"📋 Found {len(schedule_sections)} sections (alternate method)")
            
            # Scrape each section
            for i, section in enumerate(schedule_sections, 1):
                section_name = section.get('name', f'Section {i}')
                section_url = section.get('url')
                
                self.logger.progress(i, len(schedule_sections), section_name)
                
                try:
                    section_games, section_teams = await self._scrape_schedule_section(
                        page, league, section_name, section_url
                    )
                    
                    # Apply time filter
                    section_games = self._apply_time_filter(section_games)
                    
                    games.extend(section_games)
                    teams.extend(section_teams)
                    
                    # Write to CSV
                    games_written = sum(1 for g in section_games if self.csv.write_game(g))
                    teams_written = sum(1 for t in section_teams if self.csv.write_team(t))
                    
                    self.logger.stats("Games", f"{len(section_games)} found, {games_written} new")
                    self.logger.stats("Teams", f"{len(section_teams)} found, {teams_written} new")
                    
                    self.stats['schedules_scraped'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Section error: {e}", e)
                    self.stats['errors'] += 1
                
                await self.human.delay(2, 4)
                await self.human.maybe_coffee_break()
            
        except Exception as e:
            self.logger.error(f"League error: {e}", e)
            self.stats['errors'] += 1
        
        self.stats['leagues_scraped'] += 1
        self.stats['games_found'] += len(games)
        self.stats['teams_found'] += len(teams)
        
        return games, teams
    
    async def _find_schedule_sections(self, page: Page) -> List[Dict]:
        """Find all schedule/division links on the event page."""
        sections = []
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        base_url = page.url.split('?')[0]  # Get base URL without query params
        
        self.logger.debug_msg(f"Page HTML length: {len(html)} chars")
        self.logger.debug_msg(f"Base URL: {base_url}")
        
        # Method 1: Look for age/gender schedule links (common GotSport pattern)
        # URL pattern: /schedules?age=17&gender=f or /schedules?age=15&gender=m
        schedule_links = soup.find_all('a', href=re.compile(r'schedules\?.*age=\d+.*gender=[mf]', re.I))
        self.logger.debug_msg(f"Found {len(schedule_links)} age/gender schedule links")
        
        for link in schedule_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if href:
                full_url = href if href.startswith('http') else f"https://system.gotsport.com{href}"
                sections.append({'name': text or f"Schedule ({href})", 'url': full_url})
                self.logger.debug_msg(f"  Age/gender link: {text} -> {full_url[:60]}...")
        
        # Method 2: Look for division/bracket links with schedules
        schedule_links = soup.find_all('a', href=re.compile(r'schedule', re.I))
        self.logger.debug_msg(f"Found {len(schedule_links)} general schedule links")
        
        for link in schedule_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text and href:
                full_url = href if href.startswith('http') else f"https://system.gotsport.com{href}"
                # Avoid duplicates
                if not any(s['url'] == full_url for s in sections):
                    sections.append({'name': text, 'url': full_url})
                    self.logger.debug_msg(f"  Schedule link: {text} -> {full_url[:60]}...")
        
        # Method 3: Look for age group elements (U13, U14, etc.) that might be clickable
        age_gender_patterns = [
            # Female patterns
            (r'U?(\d{1,2})\s*(G|Girls?|Female)', 'f'),
            (r'(G|Girls?)\s*U?(\d{1,2})', 'f'),
            (r'Female\s*U?(\d{1,2})', 'f'),
            (r'20\d{2}\s*(G|Girls?)', 'f'),
            # Male patterns  
            (r'U?(\d{1,2})\s*(B|Boys?|Male)', 'm'),
            (r'(B|Boys?)\s*U?(\d{1,2})', 'm'),
            (r'Male\s*U?(\d{1,2})', 'm'),
            (r'20\d{2}\s*(B|Boys?)', 'm'),
        ]
        
        # Look for clickable elements containing age/gender
        for element in soup.find_all(['a', 'button', 'div'], class_=re.compile(r'age|division|bracket|group|schedule', re.I)):
            text = element.get_text(strip=True)
            href = element.get('href', '')
            
            # Check if text contains age/gender info
            age_match = re.search(r'U?(\d{1,2})', text)
            if age_match and len(text) < 50:  # Avoid long text blocks
                if href:
                    full_url = href if href.startswith('http') else f"https://system.gotsport.com{href}"
                else:
                    # Construct URL from age/gender
                    age = age_match.group(1)
                    gender = 'f' if re.search(r'girl|female|^g\d|g$', text, re.I) else 'm' if re.search(r'boy|male|^b\d|b$', text, re.I) else None
                    if gender:
                        full_url = f"{base_url}/schedules?age={age}&gender={gender}"
                    else:
                        full_url = None
                
                if full_url and not any(s['url'] == full_url for s in sections):
                    sections.append({'name': text, 'url': full_url})
                    self.logger.debug_msg(f"  Age element: {text} -> {full_url[:60] if full_url else 'N/A'}...")
        
        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for s in sections:
            url = s.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(s)
            elif not url:
                unique.append(s)
        
        self.logger.debug_msg(f"Total unique sections found: {len(unique)}")
        return unique
    
    async def _find_alternate_sections(self, page: Page) -> List[Dict]:
        """Try alternate methods to find schedule sections."""
        sections = []
        
        # Try finding clickable elements with age patterns
        age_patterns = ['U9', 'U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16', 'U17', 'U18', 'U19']
        
        for age in age_patterns:
            try:
                locators = await page.locator(f'text="{age}"').all()
                self.logger.debug_msg(f"Found {len(locators)} elements containing '{age}'")
                
                for loc in locators[:3]:  # Limit to avoid too many
                    try:
                        text = await loc.inner_text()
                        sections.append({'name': text.strip(), 'url': None})
                    except:
                        pass
            except:
                pass
        
        return sections
    
    async def _click_view_all_matches(self, page: Page):
        """
        Click "All" date filter or "View All Matches" button to see all games.
        
        GotSport has a date selector with individual dates (Aug 23, Aug 24, etc.)
        and an "All" option. We need to click "All" to see all games at once.
        
        URL patterns:
        - Individual date: /schedules?age=17&gender=f (shows only one date)
        - All matches: /schedules?date=All&group=405220 (shows all dates)
        """
        clicked = False
        
        # Method 1: Try clicking "View All Matches" button/link
        view_all_selectors = [
            'text="View All Matches"',
            'a:has-text("View All Matches")',
            'button:has-text("View All Matches")',
            'text="View all Matches"',
            'text="view all matches"',
        ]
        
        for selector in view_all_selectors:
            try:
                locator = page.locator(selector)
                count = await locator.count()
                if count > 0:
                    self.logger.debug_msg(f"Found 'View All Matches' button, clicking...")
                    await locator.first.click()
                    await self.human.delay(2, 3)
                    clicked = True
                    self.logger.info("📅 Clicked 'View All Matches' - loading all games")
                    break
            except Exception as e:
                self.logger.debug_msg(f"Selector {selector} failed: {e}")
                continue
        
        if clicked:
            return
        
        # Method 2: Try clicking "All" in the date selector tabs
        all_date_selectors = [
            'text="All"',
            'div:has-text("All"):not(:has(div))',  # Direct text match
            'a:has-text("All")',
            'button:has-text("All")',
            '[class*="date"] >> text="All"',
            '[class*="calendar"] >> text="All"',
        ]
        
        for selector in all_date_selectors:
            try:
                locator = page.locator(selector)
                all_elements = await locator.all()
                
                for el in all_elements:
                    try:
                        text = await el.inner_text()
                        # Make sure it's the "All" date selector, not something else
                        if text.strip().lower() == 'all':
                            self.logger.debug_msg(f"Found 'All' date tab, clicking...")
                            await el.click()
                            await self.human.delay(2, 3)
                            clicked = True
                            self.logger.info("📅 Clicked 'All' date filter - loading all games")
                            break
                    except:
                        continue
                
                if clicked:
                    break
            except Exception as e:
                self.logger.debug_msg(f"Selector {selector} failed: {e}")
                continue
        
        if clicked:
            return
        
        # Method 3: Try modifying URL directly to add date=All parameter
        current_url = page.url
        if 'date=All' not in current_url and '/schedules' in current_url:
            # Try to extract group ID from page and construct All URL
            try:
                html = await page.content()
                
                # Look for group ID in page links
                group_match = re.search(r'group=(\d+)', html)
                if group_match:
                    group_id = group_match.group(1)
                    
                    # Construct All URL
                    base_url = current_url.split('?')[0]
                    all_url = f"{base_url}?date=All&group={group_id}"
                    
                    self.logger.debug_msg(f"Navigating to All URL: {all_url}")
                    await page.goto(all_url, timeout=30000)
                    await self.human.delay(2, 3)
                    clicked = True
                    self.logger.info("📅 Navigated to date=All URL - loading all games")
            except Exception as e:
                self.logger.debug_msg(f"URL modification failed: {e}")
        
        if not clicked:
            self.logger.warning("Could not find 'All' or 'View All Matches' - may only see partial games")
    
    async def _scrape_schedule_section(self, page: Page, league: LeagueConfig,
                                        section_name: str, section_url: Optional[str]) -> Tuple[List[Dict], List[Dict]]:
        """Scrape games and teams from a specific schedule section."""
        games = []
        teams = []
        
        # Navigate if URL provided
        if section_url:
            self.logger.debug_msg(f"Navigating to: {section_url}")
            await page.goto(section_url, timeout=30000)
            await self.human.delay(2, 3)
            await self.human.random_scroll(page)
        
        # Parse age and gender from section name
        age_group = extract_age_group(section_name)
        # v11 FIX: Use named parameter for default, gender will be refined later with team names
        gender = extract_gender(section_name, default=league.gender)
        
        self.logger.debug_msg(f"Section age: {age_group}, gender: {gender}")
        
        # === CRITICAL: Click "All" or "View All Matches" to get all games ===
        await self._click_view_all_matches(page)
        
        # Get page content
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        current_url = page.url
        
        self.logger.debug_msg(f"Page content: {len(html)} chars")
        
        # === v4: COLLECT ALL TEAM NAMES FIRST FOR CONTEXT CLUES ===
        division_team_names = []
        
        # Find team names in all links
        for link in soup.find_all('a', href=re.compile(r'team', re.I)):
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) >= 3 and not link_text.isdigit():
                division_team_names.append(link_text)
        
        # Also check division name itself
        division_team_names.append(section_name)
        
        self.logger.debug_msg(f"Collected {len(division_team_names)} team names for context clues")
        
        # Check if we found any birth year clues
        birth_year_clues = [n for n in division_team_names if birth_year_resolver.extract_birth_year_from_name(n)]
        if birth_year_clues:
            self.logger.debug_msg(f"Birth year context found: {birth_year_clues[:3]}...")
        
        # Find all tables
        tables = soup.find_all('table')
        self.logger.debug_msg(f"Found {len(tables)} tables")
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            self.logger.debug_msg(f"Table {table_idx + 1}: {len(rows)} rows")
            
            for row in rows:
                result = self._parse_game_row(row, league, age_group, gender, section_name, current_url, division_team_names)
                if result:
                    game, game_teams = result
                    games.append(game)
                    teams.extend(game_teams)
        
        # Also try div-based layouts
        game_divs = soup.find_all('div', class_=re.compile(r'game|match|fixture|schedule-row', re.I))
        self.logger.debug_msg(f"Found {len(game_divs)} game divs")
        
        for div in game_divs:
            result = self._parse_game_div(div, league, age_group, gender, section_name, current_url, division_team_names)
            if result:
                game, game_teams = result
                games.append(game)
                teams.extend(game_teams)
        
        return games, teams
    
    def _parse_game_row(self, row, league: LeagueConfig, age_group: str,
                        gender: str, division: str, source_url: str,
                        division_team_names: List[str] = None) -> Optional[Tuple[Dict, List[Dict]]]:
        """
        Parse a game from a GotSport table row.
        
        Expected columns (from screenshot):
        - Match # (1, 2, 3...)
        - Time (Aug 23, 2025 1:00PM CDT with "Scheduled" label)
        - Home Team (logo + team name link)
        - Results (1 - 1 score)
        - Away Team (logo + team name link)
        - Location
        - Division
        """
        cells = row.find_all(['td', 'th'])
        if len(cells) < 4:
            return None
        
        # Skip header rows
        if row.find('th'):
            return None
        
        # Extract data from cells
        home_team = None
        home_team_url = None
        home_team_id = None
        away_team = None
        away_team_url = None
        away_team_id = None
        home_score = None
        away_score = None
        game_date = None
        game_time = None
        location = None
        external_game_id = None
        game_division = None
        
        cell_texts = []
        for idx, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            cell_texts.append(text)
            links = cell.find_all('a')
            
            self.logger.debug_msg(f"  Cell {idx}: '{text[:50]}...' ({len(links)} links)") if len(text) > 0 else None
            
            # Column detection based on content patterns
            
            # Match # column (just a number)
            if idx == 0 and text.isdigit():
                external_game_id = text
                continue
            
            # Time column - contains date and time, often with "Scheduled" or status
            # Pattern: "Aug 23, 2025 1:00PM CDT" or "Aug 23, 2025\n1:00PM CDT\nScheduled"
            # v5 FIX: Be more careful about time extraction to avoid matching year digits
            date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}', text, re.I)
            if date_match and not game_date:
                game_date = parse_date(date_match.group(0))
                
                # Extract time - look for time AFTER the date, not within it
                # First try to find time with AM/PM and proper boundary (most reliable)
                time_with_ampm = re.search(r'(?:^|[^\d])(\d{1,2}:\d{2}\s*(?:AM|PM))', text, re.I)
                if time_with_ampm:
                    game_time = parse_time(time_with_ampm.group(1))
                else:
                    # v5 FIX: For concatenated year+time like "20259:00 AM", extract time after the year
                    # Also capture AM/PM if present
                    after_year = re.search(r'\d{4}[^\d]*(\d{1,2}:\d{2})(\s*(?:AM|PM))?', text, re.I)
                    if after_year:
                        time_part = after_year.group(1)
                        ampm_part = after_year.group(2) or ""
                        full_time = time_part + ampm_part
                        
                        # Validate hour is reasonable
                        hour_check = re.match(r'(\d{1,2}):', time_part)
                        if hour_check and int(hour_check.group(1)) <= 23:
                            game_time = parse_time(full_time)
                continue
            
            # Results column - score pattern like "1 - 1" or "2 - 0"
            score_match = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', text.strip())
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                continue
            
            # Division column - often at the end, contains age info
            if re.search(r'(Girls|Boys|U\d{2}|20\d{2})', text, re.I) and idx >= len(cells) - 2:
                game_division = text
                continue
            
            # Team columns - have links to team pages
            # Home team comes before Results, Away team comes after
            if links:
                for link in links:
                    link_text = link.get_text(strip=True)
                    link_href = link.get('href', '')
                    
                    # Skip non-team links (like location links)
                    if not link_text or len(link_text) < 3:
                        continue
                    if 'map' in link_href.lower() or 'location' in link_href.lower():
                        continue
                    
                    # Extract team ID from URL
                    team_id_match = re.search(r'team[=_/](\d+)', link_href, re.I)
                    team_id = team_id_match.group(1) if team_id_match else None
                    
                    full_url = link_href
                    if link_href and not link_href.startswith('http'):
                        full_url = f"https://system.gotsport.com{link_href}"
                    
                    # Assign to home or away based on whether we've seen a score yet
                    if not home_team:
                        home_team = link_text
                        home_team_url = full_url
                        home_team_id = team_id
                    elif not away_team and link_text != home_team:
                        away_team = link_text
                        away_team_url = full_url
                        away_team_id = team_id
            
            # Location - usually contains field/park name
            if 'field' in text.lower() or 'park' in text.lower() or 'complex' in text.lower():
                location = text
        
        # Fallback: try to find teams in cell texts if not found via links
        if not home_team or not away_team:
            for i, text in enumerate(cell_texts):
                # Skip short texts, numbers, dates, scores
                if len(text) < 5 or text.isdigit():
                    continue
                if re.match(r'^\d+\s*[-–]\s*\d+$', text):
                    continue
                if parse_date(text):
                    continue
                
                # Look for team-like names (contain letters, maybe FC, SC, etc.)
                if re.search(r'[A-Z][a-z]+', text) and len(text) < 100:
                    if not home_team:
                        home_team = text
                    elif not away_team and text != home_team:
                        away_team = text
        
        # Validate we have minimum required fields
        if not home_team or not away_team:
            return None
        
        # v12 FIX: Skip "Bye" games - these are placeholders, not real games
        if home_team.strip().lower() == 'bye' or away_team.strip().lower() == 'bye':
            return None
        
        # Use division from page if not found in row
        if not game_division:
            game_division = division
        
        # v6 FIX: Don't use navigation words as division
        if game_division and game_division.lower() in ['schedule', 'results', 'standings', 'bracket', 'npl 1', 'npl 2', 'npl1', 'npl2']:
            # Try to extract a proper division from the row's division cell content
            # or from team names
            game_division = ''
        
        # Extract age from division if not set
        if not age_group:
            age_group = extract_age_group(game_division) or extract_age_group(home_team) or extract_age_group(away_team)
        
        # v11 FIX: Re-detect gender from actual team names if still "Both"
        if gender == "Both" and (home_team or away_team):
            team_names_for_gender = [home_team, away_team]
            detected_gender = extract_gender(game_division or "", age_group_text="", team_names=team_names_for_gender, default="Both")
            if detected_gender != "Both":
                gender = detected_gender
        
        # v6 FIX: If division is empty but we found age_group, use that for division
        if not game_division and age_group:
            game_division = age_group
        
        # Generate game ID
        game_id = generate_game_id(league.name, age_group, game_date, home_team, away_team)
        game_status = determine_game_status(game_date, home_score, away_score)
        
        game = {
            'game_id': game_id,
            'external_game_id': external_game_id or '',
            'league': league.name,
            'organization': league.organization,
            'platform': league.platform,
            'tier': league.tier,
            'region': league.region,
            'gender': gender,
            'age_group': age_group,
            'division': game_division,
            'home_team': home_team,
            'home_team_normalized': normalize_team_name(home_team, division_team_names, division),
            'home_team_id': home_team_id or '',
            'home_team_url': home_team_url or '',
            'away_team': away_team,
            'away_team_normalized': normalize_team_name(away_team, division_team_names, division),
            'away_team_id': away_team_id or '',
            'away_team_url': away_team_url or '',
            'home_score': home_score if home_score is not None else '',
            'away_score': away_score if away_score is not None else '',
            'game_date': game_date or '',
            'game_time': game_time or '',
            'game_status': game_status,
            'location': location or '',
            'field': '',
            'source_url': source_url,
        }
        
        team_list = []
        for team_name, team_id, team_url in [
            (home_team, home_team_id, home_team_url),
            (away_team, away_team_id, away_team_url)
        ]:
            if team_name:
                team_list.append({
                    'team_id': team_id or '',
                    'team_name': team_name,
                    'team_name_normalized': normalize_team_name(team_name, division_team_names, division),
                    'club_name': extract_club_name(team_name),
                    'league': league.name,
                    'age_group': age_group,
                    'gender': gender,
                    'region': league.region,
                    'platform': league.platform,
                    'schedule_url': team_url or '',
                    'profile_url': '',
                    'state': '',  # v19: Location fields for future scraping
                    'city': '',
                    'street_address': '',
                    'zip_code': '',
                    'official_website': '',
                })
        
        return game, team_list
    
    def _parse_game_div(self, div, league: LeagueConfig, age_group: str,
                        gender: str, division: str, source_url: str,
                        division_team_names: List[str] = None) -> Optional[Tuple[Dict, List[Dict]]]:
        """Parse a game from a div element.
        
        v6 FIX: Skip divs that contain (H)/(A) markers - these are summary views,
        not actual game data with complete info.
        """
        text = div.get_text(separator=' ', strip=True)
        
        # v6 FIX: Skip divs that look like summary rows with (H)/(A) markers
        # These are standings/summary views that don't have full game data
        if ' (H)' in text or ' (A)' in text or '(H)' in text.split() or '(A)' in text.split():
            return None
        
        # Find team links
        links = div.find_all('a')
        team_data = []
        
        for link in links:
            link_text = link.get_text(strip=True)
            link_href = link.get('href', '')
            
            # v6 FIX: Skip team names with (H)/(A) markers
            if '(H)' in link_text or '(A)' in link_text:
                continue
            
            if len(link_text) > 3 and not link_text.isdigit():
                team_id_match = re.search(r'team[=_/](\d+)', link_href, re.I)
                full_url = link_href if link_href.startswith('http') else f"https://system.gotsport.com{link_href}" if link_href else ''
                
                team_data.append({
                    'name': link_text,
                    'url': full_url,
                    'id': team_id_match.group(1) if team_id_match else ''
                })
        
        if len(team_data) < 2:
            return None
        
        home = team_data[0]
        away = team_data[1]
        
        # v12 FIX: Skip "Bye" games - these are placeholders, not real games
        if home['name'].strip().lower() == 'bye' or away['name'].strip().lower() == 'bye':
            return None
        
        home_score, away_score = parse_score(text)
        game_date = parse_date(text)
        game_time = parse_time(text)
        
        # v6 FIX: Skip games without dates - these are likely summary rows
        if not game_date:
            return None
        
        # v6 FIX: Don't use navigation words as division
        actual_division = division
        if division.lower() in ['schedule', 'results', 'standings', 'bracket']:
            actual_division = ''
        
        # v6 FIX: Try to extract age_group from team names if not already set
        actual_age_group = age_group
        if not actual_age_group:
            actual_age_group = extract_age_group(home['name']) or extract_age_group(away['name'])
        
        # v11 FIX: Re-detect gender from actual team names if still "Both"
        actual_gender = gender
        if actual_gender == "Both":
            team_names_for_gender = [home['name'], away['name']]
            detected_gender = extract_gender(actual_division or "", age_group_text="", team_names=team_names_for_gender, default="Both")
            if detected_gender != "Both":
                actual_gender = detected_gender
        
        game_id = generate_game_id(league.name, actual_age_group, game_date, home['name'], away['name'])
        game_status = determine_game_status(game_date, home_score, away_score)
        
        game = {
            'game_id': game_id,
            'external_game_id': '',
            'league': league.name,
            'organization': league.organization,
            'platform': league.platform,
            'tier': league.tier,
            'region': league.region,
            'gender': actual_gender,
            'age_group': actual_age_group,
            'division': actual_division,
            'home_team': home['name'],
            'home_team_normalized': normalize_team_name(home['name'], division_team_names, actual_division),
            'home_team_id': home['id'],
            'home_team_url': home['url'],
            'away_team': away['name'],
            'away_team_normalized': normalize_team_name(away['name'], division_team_names, actual_division),
            'away_team_id': away['id'],
            'away_team_url': away['url'],
            'home_score': home_score if home_score is not None else '',
            'away_score': away_score if away_score is not None else '',
            'game_date': game_date or '',
            'game_time': game_time or '',
            'game_status': game_status,
            'location': '',
            'field': '',
            'source_url': source_url,
        }
        
        teams = [
            {
                'team_id': home['id'],
                'team_name': home['name'],
                'team_name_normalized': normalize_team_name(home['name'], division_team_names, actual_division),
                'club_name': extract_club_name(home['name']),
                'league': league.name,
                'age_group': actual_age_group,
                'gender': actual_gender,
                'region': league.region,
                'platform': league.platform,
                'schedule_url': home['url'],
                'profile_url': '',
                'state': '',  # v19: Location fields
                'city': '',
                'street_address': '',
                'zip_code': '',
                'official_website': '',
            },
            {
                'team_id': away['id'],
                'team_name': away['name'],
                'team_name_normalized': normalize_team_name(away['name'], division_team_names, actual_division),
                'club_name': extract_club_name(away['name']),
                'league': league.name,
                'age_group': actual_age_group,
                'gender': actual_gender,
                'region': league.region,
                'platform': league.platform,
                'schedule_url': away['url'],
                'profile_url': '',
                'state': '',  # v19: Location fields
                'city': '',
                'street_address': '',
                'zip_code': '',
                'official_website': '',
            }
        ]
        
        return game, teams
    
    def _apply_time_filter(self, games: List[Dict]) -> List[Dict]:
        """Apply time filter to games list."""
        if self.time_filter == 'all':
            return games
        
        today = datetime.now().date()
        filtered = []
        
        for game in games:
            game_date_str = game.get('game_date', '')
            if not game_date_str:
                # Include games without dates
                filtered.append(game)
                continue
            
            try:
                game_date = datetime.strptime(game_date_str, "%Y-%m-%d").date()
                
                if self.time_filter == 'past':
                    if game_date < today:
                        filtered.append(game)
                elif self.time_filter == 'future':
                    if game_date >= today:
                        filtered.append(game)
                elif self.time_filter == 'last_days' and self.days_back:
                    cutoff = today - timedelta(days=self.days_back)
                    if game_date >= cutoff:
                        filtered.append(game)
            except:
                filtered.append(game)
        
        return filtered


# =============================================================================
# INTERACTIVE MENU
# =============================================================================

def interactive_menu() -> Dict:
    """Display interactive menu and get user selections."""
    
    print("\n" + "=" * 70)
    print(f"🏆 US CLUB SOCCER NPL SCRAPER {SCRAPER_VERSION}")
    print("=" * 70)
    print("  📋 30 leagues (21 NPL + 9 Sub-NPL)")
    print("  🌐 3 platforms (GotSport, TotalGlobalSports, SincSports)")
    print("=" * 70)
    
    # === TIER SELECTION ===
    print("\n📊 TIER SELECTION")
    print("-" * 40)
    print("  1. NPL only (21 leagues)")
    print("  2. Sub-NPL only (9 leagues)")
    print("  3. All leagues (30 leagues)")
    print()
    
    tier_filter = None
    while True:
        choice = input("  Enter choice (1-3): ").strip()
        if choice == '1':
            tier_filter = 'NPL'
            break
        elif choice == '2':
            tier_filter = 'Sub-NPL'
            break
        elif choice == '3':
            tier_filter = None
            break
        else:
            print("  ❌ Invalid choice. Try again.")
    
    # === REGION SELECTION ===
    regions = sorted(set(l.region for l in LEAGUE_CONFIGS))
    print("\n📍 REGION SELECTION")
    print("-" * 40)
    for i, region in enumerate(regions, 1):
        count = len([l for l in LEAGUE_CONFIGS if l.region == region])
        print(f"  {i}. {region} ({count} leagues)")
    print(f"  {len(regions) + 1}. All regions")
    print()
    
    region_filter = None
    while True:
        choice = input(f"  Enter choice (1-{len(regions) + 1}): ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(regions):
                region_filter = regions[idx - 1]
                break
            elif idx == len(regions) + 1:
                region_filter = None
                break
        except ValueError:
            pass
        print("  ❌ Invalid choice. Try again.")
    
    # === GENDER SELECTION ===
    print("\n👥 GENDER SELECTION")
    print("-" * 40)
    print("  1. Boys only")
    print("  2. Girls only")
    print("  3. Both")
    print()
    
    gender_filter = None
    while True:
        choice = input("  Enter choice (1-3): ").strip()
        if choice == '1':
            gender_filter = 'Boys'
            break
        elif choice == '2':
            gender_filter = 'Girls'
            break
        elif choice == '3':
            gender_filter = None
            break
        else:
            print("  ❌ Invalid choice. Try again.")
    
    # === TIME FILTER ===
    print("\n📅 TIME FILTER")
    print("-" * 40)
    print("  1. All games")
    print("  2. Past games only")
    print("  3. Future games only")
    print("  4. Last X days")
    print()
    
    time_filter = 'all'
    days_back = None
    while True:
        choice = input("  Enter choice (1-4): ").strip()
        if choice == '1':
            time_filter = 'all'
            break
        elif choice == '2':
            time_filter = 'past'
            break
        elif choice == '3':
            time_filter = 'future'
            break
        elif choice == '4':
            time_filter = 'last_days'
            while True:
                days_str = input("  Enter number of days: ").strip()
                try:
                    days_back = int(days_str)
                    if days_back > 0:
                        break
                except ValueError:
                    pass
                print("  ❌ Enter a positive number.")
            break
        else:
            print("  ❌ Invalid choice. Try again.")
    
    # === SPECIFIC LEAGUE ===
    print("\n🎯 SPECIFIC LEAGUE (optional)")
    print("-" * 40)
    print("  Enter league name to filter (or press Enter for all):")
    league_name = input("  League name: ").strip()
    if not league_name:
        league_name = None
    
    # === DEBUG MODE ===
    print("\n🔧 DEBUG MODE")
    print("-" * 40)
    debug_choice = input("  Enable debug output? (y/n): ").strip().lower()
    debug = debug_choice == 'y'
    
    # === HEADLESS MODE ===
    print("\n🖥️  BROWSER MODE")
    print("-" * 40)
    print("  1. Visible browser (see what's happening)")
    print("  2. Headless (faster, no window)")
    print()
    
    headless = False
    while True:
        choice = input("  Enter choice (1-2): ").strip()
        if choice == '1':
            headless = False
            break
        elif choice == '2':
            headless = True
            break
        else:
            print("  ❌ Invalid choice. Try again.")
    
    # === CONFIRMATION ===
    print("\n" + "=" * 70)
    print("📝 CONFIGURATION SUMMARY")
    print("=" * 70)
    print(f"   Tier:      {tier_filter or 'All'}")
    print(f"   Region:    {region_filter or 'All'}")
    print(f"   Gender:    {gender_filter or 'Both'}")
    print(f"   Time:      {time_filter}" + (f" ({days_back} days)" if days_back else ""))
    print(f"   League:    {league_name or 'All'}")
    print(f"   Debug:     {'Yes' if debug else 'No'}")
    print(f"   Browser:   {'Headless' if headless else 'Visible'}")
    print("=" * 70)
    
    confirm = input("\n  ✅ Proceed with scraping? (y/n): ").strip().lower()
    if confirm != 'y':
        print("\n  ❌ Cancelled.")
        sys.exit(0)
    
    return {
        'tier': tier_filter,
        'region': region_filter,
        'gender': gender_filter,
        'time_filter': time_filter,
        'days_back': days_back,
        'league': league_name,
        'debug': debug,
        'headless': headless,
    }


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class USClubNPLScraper:
    """Main orchestrator for scraping all US Club Soccer NPL leagues."""
    
    def __init__(self, output_dir: str = ".", debug: bool = False,
                 headless: bool = False, time_filter: str = 'all',
                 days_back: int = None, take_screenshots: bool = True):
        self.output_dir = output_dir
        self.debug = debug
        self.headless = headless
        self.time_filter = time_filter
        self.days_back = days_back
        self.take_screenshots = take_screenshots
        
        self.logger = DiagnosticLogger(debug=debug)
        self.csv = CSVExporter(output_dir, self.logger)
        self.human = HumanBehavior(self.logger)
        
        self.gotsport = GotSportScraper(self.csv, self.logger, self.human,
                                        time_filter, days_back, take_screenshots)
        
        self.total_stats = {
            'leagues_scraped': 0,
            'schedules_scraped': 0,
            'games_found': 0,
            'games_new': 0,
            'games_duplicate': 0,
            'teams_found': 0,
        }
    
    def filter_leagues(self, tier: str = None, region: str = None,
                       gender: str = None, league_name: str = None,
                       platform: str = None) -> List[LeagueConfig]:
        """Filter leagues by criteria."""
        filtered = [l for l in LEAGUE_CONFIGS if l.active]
        
        if tier:
            filtered = [l for l in filtered if l.tier.lower() == tier.lower()]
        
        if region:
            filtered = [l for l in filtered if region.lower() in l.region.lower()]
        
        # v16: Handle 'both' - means scrape all genders, so don't filter
        if gender and gender.lower() != 'both':
            filtered = [l for l in filtered if l.gender in ['Both', gender]]
        
        if league_name:
            filtered = [l for l in filtered if league_name.lower() in l.name.lower()]
        
        if platform:
            filtered = [l for l in filtered if l.platform.lower() == platform.lower()]
        
        return filtered
    
    async def _launch_browser(self, playwright):
        """Launch browser with stealth settings. Returns (browser, context, page)."""
        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        user_agent = get_random_user_agent()
        self.logger.debug_msg(f"User agent: {user_agent[:50]}...")
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=user_agent
        )
        
        # Add stealth script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        page = await context.new_page()
        
        return browser, context, page
    
    async def run(self, tier: str = None, region: str = None,
                  gender: str = None, league_name: str = None,
                  platform: str = None, test_mode: bool = False,
                  scrape_mode: str = 'all'):
        """Main scraping orchestration with browser relaunch support.
        
        Args:
            tier: Filter by league tier (NPL, Sub-NPL)
            region: Filter by region
            gender: Filter by gender (Boys, Girls, both)
            league_name: Filter by specific league name
            platform: Filter by platform (gotsport, totalglobalsports, sincsports)
            test_mode: If True, only scrape first 2 leagues
            scrape_mode: 'all' (scrape everything), 'pending' (only pending), 'reset' (reset then scrape)
        """
        
        self.logger.header(f"🚀 US CLUB SOCCER NPL SCRAPER {SCRAPER_VERSION}")
        self.logger.info("📁 Output: CSV files for seedlinedata.db import")
        
        # v20: Initialize scrape status tracking
        db_path = find_database_path()
        if db_path:
            ensure_npl_scrape_status_table(db_path)
            
            # Handle reset mode
            if scrape_mode == 'reset':
                reset_count = reset_all_npl_scrape_status(db_path)
                self.logger.info(f"🔄 Reset {reset_count} leagues to pending status")
                scrape_mode = 'pending'  # After reset, scrape pending
        
        # Show scrape mode
        mode_names = {
            'all': '🔄 Scrape All (re-scrape everything)',
            'pending': '⚡ Pending Only (resume mode)',
            'reset': '♻️ Reset & Scrape'
        }
        self.logger.info(f"Mode: {mode_names.get(scrape_mode, scrape_mode)}")
        
        # Show stealth settings
        self.logger.subheader("🕵️ STEALTH MODE ENABLED")
        self.logger.info(f"Random delays: {MIN_DELAY:.1f}-{MAX_DELAY:.1f} seconds")
        self.logger.info(f"Coffee breaks: Every {COFFEE_BREAK_INTERVAL[0]}-{COFFEE_BREAK_INTERVAL[1]} requests")
        self.logger.info(f"User agents: {len(USER_AGENTS)} different browsers")
        self.logger.info(f"Reading pauses: {READING_PAUSE_CHANCE * 100:.0f}% chance")
        
        # Filter leagues
        leagues = self.filter_leagues(tier, region, gender, league_name, platform)
        
        if not leagues:
            self.logger.error("No leagues match the specified filters")
            return
        
        # v20: Filter out already-completed leagues if in pending mode
        if scrape_mode == 'pending' and db_path:
            original_count = len(leagues)
            leagues_to_scrape = []
            skipped_count = 0
            
            for league in leagues:
                status = get_league_scrape_status(db_path, league.name)
                if status == 'completed':
                    skipped_count += 1
                else:
                    leagues_to_scrape.append(league)
            
            if skipped_count > 0:
                self.logger.info(f"⏭️ Skipping {skipped_count} already-completed leagues")
            
            leagues = leagues_to_scrape
            
            if not leagues:
                self.logger.success("✅ All leagues already completed! Use --scrape-all to re-scrape.")
                pending, completed = get_pending_leagues_count(db_path)
                self.logger.info(f"Status: {completed} completed, {pending} pending")
                return
        
        self.logger.subheader(f"📋 LEAGUES TO SCRAPE ({len(leagues)} total)")
        for i, league in enumerate(leagues, 1):
            self.logger.info(f"{i}. {league.name} ({league.platform})")
        
        if test_mode:
            self.logger.warning("TEST MODE: Limiting to first 2 leagues")
            leagues = leagues[:2]
        
        # Track progress for resume capability
        current_league_index = 0
        max_retries = 10  # Maximum browser relaunches
        retry_count = 0
        
        self.logger.subheader("🌐 STARTING BROWSER")
        self.logger.info("💡 If browser closes accidentally, it will auto-relaunch and resume")
        
        async with async_playwright() as p:
            browser = None
            context = None
            page = None
            
            while current_league_index < len(leagues) and retry_count < max_retries:
                try:
                    # Launch browser if not running
                    if browser is None or not browser.is_connected():
                        if retry_count > 0:
                            self.logger.warning(f"🔄 Relaunching browser (attempt {retry_count + 1}/{max_retries})...")
                            await asyncio.sleep(2)  # Brief pause before relaunch
                        
                        browser, context, page = await self._launch_browser(p)
                        self.logger.success("Browser launched successfully")
                    
                    # Process leagues starting from current index
                    while current_league_index < len(leagues):
                        league = leagues[current_league_index]
                        i = current_league_index + 1
                        
                        self.logger.progress(i, len(leagues), league.name)
                        
                        # Check if browser is still connected before scraping
                        if not browser.is_connected():
                            raise Exception("Browser disconnected")
                        
                        # v20: Mark league as in-progress
                        if db_path:
                            update_league_scrape_status(db_path, league.name, 'in_progress', league.url)
                        
                        games_count = 0
                        teams_count = 0
                        error_msg = None
                        
                        try:
                            # GotSport scraper (main platform)
                            if league.platform == 'gotsport':
                                games, teams = await self.gotsport.scrape_league(page, league)
                                games_count = len(games)
                                teams_count = len(teams)
                                
                                self.total_stats['games_found'] += games_count
                                self.total_stats['teams_found'] += teams_count
                            
                            # TotalGlobalSports (placeholder - can port ECNL scraper patterns)
                            elif league.platform == 'totalglobalsports':
                                self.logger.warning(f"TGS scraper not yet implemented for {league.name}")
                            
                            # SincSports (placeholder)
                            elif league.platform == 'sincsports':
                                self.logger.warning(f"SincSports scraper not yet implemented for {league.name}")
                            
                            # v20: Mark league as completed
                            if db_path:
                                update_league_scrape_status(db_path, league.name, 'completed', 
                                                          league.url, games_count, teams_count)
                        
                        except Exception as e:
                            error_msg = str(e)
                            self.logger.error(f"Error scraping {league.name}: {e}")
                            if db_path:
                                update_league_scrape_status(db_path, league.name, 'error',
                                                          league.url, games_count, teams_count, error_msg)
                        
                        self.total_stats['leagues_scraped'] += 1
                        current_league_index += 1
                    
                    # Successfully completed all leagues
                    break
                    
                except KeyboardInterrupt:
                    self.logger.warning("Interrupted by user (Ctrl+C)")
                    break
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # Check if this is a browser closed/disconnected error
                    is_browser_closed = any(phrase in error_msg for phrase in [
                        'browser has been closed',
                        'target closed',
                        'browser disconnected',
                        'connection closed',
                        'target page, context or browser has been closed',
                        'session closed',
                        'page closed',
                        'context closed',
                        'browser.newcontext',
                        'browser is not connected',
                    ])
                    
                    if is_browser_closed:
                        retry_count += 1
                        self.logger.warning(f"🔌 Browser was closed! Will relaunch and resume from league {current_league_index + 1}...")
                        
                        # Clean up old browser reference
                        try:
                            if browser:
                                await browser.close()
                        except:
                            pass
                        
                        browser = None
                        context = None
                        page = None
                        
                        # Brief pause before retry
                        await asyncio.sleep(3)
                    else:
                        # Non-browser error - log and continue to next league
                        self.logger.error(f"Error scraping league: {e}", e)
                        current_league_index += 1
                        
                        if current_league_index >= len(leagues):
                            break
            
            # Clean up browser
            if browser and browser.is_connected():
                try:
                    await browser.close()
                except:
                    pass
            
            if retry_count >= max_retries:
                self.logger.error(f"Max browser relaunches ({max_retries}) exceeded. Stopping.")
        
        # Final stats
        self.total_stats['schedules_scraped'] = self.gotsport.stats['schedules_scraped']
        self.total_stats['games_new'] = self.csv.stats['games_written']
        self.total_stats['games_duplicate'] = self.csv.stats['games_skipped_duplicate']
        self.total_stats['games_csv'] = self.csv.games_file
        self.total_stats['teams_csv'] = self.csv.teams_file
        
        self.logger.summary(self.total_stats)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=f'US Club Soccer NPL Scraper {SCRAPER_VERSION}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python us_club_npl_scraper_v5.py              # Interactive menu
  python us_club_npl_scraper_v5.py --list       # List all leagues
  python us_club_npl_scraper_v5.py --league "SOCAL" --debug
  python us_club_npl_scraper_v5.py --tier NPL --region Southwest
  python us_club_npl_scraper_v5.py --time last_days --days 7
  python us_club_npl_scraper_v5.py --no-screenshots  # Skip screenshots (faster)
        """
    )
    
    parser.add_argument('--platform', choices=['gotsport', 'totalglobalsports', 'sincsports'],
                        help='Only scrape leagues on this platform')
    parser.add_argument('--tier', choices=['NPL', 'Sub-NPL'],
                        help='Only scrape leagues of this tier')
    parser.add_argument('--region', type=str,
                        help='Only scrape leagues in this region')
    parser.add_argument('--gender', choices=['Boys', 'Girls', 'both', 'boys', 'girls'],
                        help='Only scrape leagues for this gender')
    parser.add_argument('--league', type=str,
                        help='Only scrape leagues matching this name')
    parser.add_argument('--time', choices=['all', 'past', 'future', 'last_days'],
                        default='all', help='Time filter for games')
    parser.add_argument('--days', type=int,
                        help='Number of days for last_days filter')
    parser.add_argument('--test', action='store_true',
                        help='Test mode - limited scraping')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode')
    parser.add_argument('--no-screenshots', action='store_true',
                        help='Disable screenshots (faster, avoids timeout errors)')
    parser.add_argument('--output', type=str, default='.',
                        help='Output directory for CSV files')
    parser.add_argument('--list', action='store_true',
                        help='List all configured leagues and exit')
    
    # Admin UI compatibility args (v15)
    parser.add_argument('--ages', help='Comma-separated age groups (e.g., U13,U14,U15) - currently informational only')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation prompts (for admin UI integration)')
    parser.add_argument('--players', action='store_true', 
                        help='Include player scraping (accepted for admin UI compatibility, NPL does not scrape players)')
    parser.add_argument('--verbose', action='store_true', 
                        help='Verbose output')
    
    # v20: Resume capability args
    parser.add_argument('--scrape', action='store_true',
                        help='Scrape pending leagues only (resume mode - default)')
    parser.add_argument('--scrape-all', action='store_true',
                        help='Scrape all leagues (ignore status, re-scrape everything)')
    parser.add_argument('--reset-status', action='store_true',
                        help='Reset all league statuses to pending before scraping')
    
    args = parser.parse_args()
    
    # List mode
    if args.list:
        print("\n" + "=" * 80)
        print("📋 US CLUB SOCCER NPL LEAGUES")
        print("=" * 80)
        
        # Group by tier
        for tier in ['NPL', 'Sub-NPL']:
            tier_leagues = [l for l in LEAGUE_CONFIGS if l.tier == tier]
            print(f"\n{tier} ({len(tier_leagues)} leagues):")
            print("-" * 60)
            
            for i, l in enumerate(tier_leagues, 1):
                status = "✅" if l.active else "❌"
                print(f"  {i:2}. {status} {l.name:<35} | {l.platform}")
        
        print("\n" + "=" * 80)
        print(f"Total: {len(LEAGUE_CONFIGS)} leagues")
        return
    
    # Check for command-line args
    has_args = any([args.platform, args.tier, args.region, args.gender,
                    args.league, args.time != 'all', args.days, args.test,
                    args.debug, args.headless, args.no_screenshots,
                    args.ages, args.no_confirm, args.players, args.verbose,
                    args.scrape, args.scrape_all, args.reset_status])
    
    # Determine scrape mode (v20)
    if args.scrape_all:
        scrape_mode = 'all'
    elif args.reset_status:
        scrape_mode = 'reset'
    else:
        scrape_mode = 'pending'  # Default: only pending leagues
    
    if not has_args:
        # Interactive mode
        config = interactive_menu()
        
        scraper = USClubNPLScraper(
            output_dir=args.output,
            debug=config['debug'],
            headless=config['headless'],
            time_filter=config['time_filter'],
            days_back=config['days_back'],
            take_screenshots=True  # Always take screenshots in interactive mode
        )
        
        asyncio.run(scraper.run(
            tier=config['tier'],
            region=config['region'],
            gender=config['gender'],
            league_name=config['league'],
            test_mode=False,
            scrape_mode='all'  # Interactive mode always scrapes all
        ))
    else:
        # Command-line mode
        if args.time == 'last_days' and not args.days:
            parser.error("--days required with --time last_days")
        
        scraper = USClubNPLScraper(
            output_dir=args.output,
            debug=args.debug or args.verbose,  # v16: --verbose also enables debug
            headless=args.headless,
            time_filter=args.time,
            days_back=args.days,
            take_screenshots=not args.no_screenshots
        )
        
        asyncio.run(scraper.run(
            platform=args.platform,
            tier=args.tier,
            region=args.region,
            gender=args.gender.capitalize() if args.gender and args.gender.lower() != 'both' else args.gender,
            league_name=args.league,
            test_mode=args.test,
            scrape_mode=scrape_mode
        ))


if __name__ == '__main__':
    main()
