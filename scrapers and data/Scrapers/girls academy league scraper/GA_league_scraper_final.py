#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GIRLS ACADEMY SCRAPER v16 - SMART DEDUPLICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGE GROUP CONVENTION (IMPORTANT - Updated Dec 2024):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All age groups use BIRTH YEAR format, NOT age format:
  - G13 = Girls born in 2013 (NOT girls age 13)
  - B14 = Boys born in 2014 (NOT boys age 14)
  - 14G, G14, Girls 2014, 2014G = all equivalent (birth year 2014)

This means G13 and 13G are the SAME as "2013" - they all refer to birth year.
The ranker and display logic depend on this convention for team name cleanup.

U-AGE FORMAT (U15, U16, etc.):
Some leagues and tournaments use "Under XX" format (U15, U16, etc.). This format
is TRICKY because the U-age changes after January 1 each year:
  - A player born in 2012 is U13 in 2024, but U14 in 2025
  - Cannot reliably convert U-age to birth year without knowing the date context

When encountering U-age format:
  1. Save it as a potentially useful datapoint
  2. ALWAYS try to find the birth year (2014, G14, 14G, etc.) in:
     - Team name (most reliable)
     - Bracket/division name
     - League name
     - Tournament name
  3. Only fall back to U-age conversion if no birth year is found

DUPLICATE DETECTION TIP:
Teams with slightly different names may be duplicates. To verify, check if they
played the same opponent on the same day with the same score - if so, they are
definitely the same team and should be merged.

NOTE: Most leagues are transitioning to SCHOOL YEAR format starting Summer 2025.
Until then, continue using birth year format as described above. When the
transition occurs, this scraper will need to be updated accordingly.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V16b CHANGES (Current):
  ✅ NEW: AMBIGUOUS_TEAMS dictionary for teams that exist in multiple states
  ✅ NEW: disambiguate_team_name() adds state identifiers based on conference context
  ✅ FIX: Teams like "Beach FC" now get "(CA)" or "(VA)" suffix based on conference
  ✅ WHY: Prevents duplicate entries for teams with same name in different states

V16 CHANGES:
  ✅ SMART DEDUPLICATION - Fuzzy team name matching prevents duplicates
  ✅ normalize_team_for_id() - Aggressive team name normalization
  ✅ WAL MODE - Better database concurrency with busy_timeout
  ✅ 3-STEP MATCHING - exact game_id → fuzzy match → insert/update/skip
  ✅ ALL V15 FEATURES PRESERVED

V15 CHANGES:
  ✅ TEAM DATA COLLECTION - Saves team info to teams table
  ✅ STATE INFERENCE - Attempts to infer state from conference names

V13 CHANGES:
  ✅ ADMIN UI COMPATIBLE - Accepts --gender, --ages, --days, --players, --verbose
  ✅ NO-CONFIRM MODE - Runs without prompts when called from admin UI
  ✅ INCLUDES ALL V12 FEATURES - Improved score parsing, canonical IDs, score merging
  ✅ DATABASE-CENTRIC - Uses discovered_urls table + games table
  ✅ TIMESTAMPED CSV EXPORT - Outputs GA_games_YYYYMMDD_HHMMSS.csv

ADMIN UI ARGUMENTS:
  --gender girls|boys|both    Filter by gender (GA is girls only)
  --ages 13,12,11             Comma-separated age groups
  --days 90                   Only games from last N days
  --players                   Include player scraping
  --verbose                   Show detailed output
  --no-confirm                Skip "Press Enter" prompts (for admin UI)

DATABASE STRUCTURE:
  Reads from: discovered_urls (league='GA'), games table
  Writes to: games table

USAGE:
  # From Admin UI (no prompts):
  python GA_scraper_v13.py --gender girls --ages 13,12,11 --days 90 --no-confirm
  
  # Interactive mode:
  python GA_scraper_v13.py
  
  # Original commands still work:
  python GA_scraper_v13.py --fix-scores
  python GA_scraper_v13.py --debug --max 5

OUTPUT:
  - Games saved to: seedlinedata.db
  - CSV exported to: GA_games_YYYYMMDD_HHMMSS.csv

CRITICAL IMPLEMENTATION NOTES - DO NOT REMOVE OR MODIFY:
═══════════════════════════════════════════════════════════════════════════════

  1. SMART DEDUPLICATION (save_games_to_db method):
     - Uses 3-step matching: exact game_id → fuzzy match → insert/update/skip
     - Fuzzy matching checks ALL existing games (not just those without scores)
     - Matches games regardless of home/away ordering
     - PRESERVE: The normalize_team_for_id() function and fuzzy matching logic
     - WHY: Prevents duplicates when team names vary between sources

  2. CANONICAL GAME IDs (make_canonical_game_id function):
     - Uses normalized team names, sorted alphabetically
     - Same game always gets same ID regardless of home/away perspective
     - PRESERVE: This function and its use in parse_game_row()
     - WHY: Allows matching games scraped from both teams' perspectives

  3. TEAM NAME NORMALIZATION (normalize_team_for_id function):
     - Removes: FC, SC, Academy, Club, United, Soccer, age patterns
     - Removes all non-alphanumeric characters, truncates to 30 chars
     - PRESERVE: All remove_patterns and remove_words lists
     - WHY: Team names vary across sources but need to match for deduplication

  4. STATE INFERENCE (infer_state_from_team function):
     - IMPORTANT: Does NOT include 'GA ' as a Georgia indicator
     - ' GA' in team names usually means "Girls Academy" league suffix
     - Only full word 'GEORGIA' maps to Georgia state
     - PRESERVE: This behavior to avoid mis-mapping California teams to Georgia
     - WHY: Teams like "TopHat 12G GA" are from various states, not Georgia

  5. SCORE EXTRACTION (extract_scores_from_row method):
     - Multiple fallback patterns for different score formats
     - Handles W/L/T indicators, View Box Score proximity, separate cells
     - PRESERVE: All 5 extraction methods in this function
     - WHY: GotSport score formatting varies; removing patterns breaks extraction

  6. DATABASE RESILIENCE:
     - WAL mode enabled for better concurrency
     - 30-second busy_timeout prevents "database locked" errors
     - PRESERVE: PRAGMA statements in save_games_to_db()
     - WHY: Multiple scrapers may access the database simultaneously

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# === AUTO-INSTALL REQUIRED PACKAGES ==========================================
import subprocess
import sys

def install_packages():
    """Install required packages if not present"""
    required = ['requests', 'beautifulsoup4']
    
    for package in required:
        try:
            if package == 'beautifulsoup4':
                __import__('bs4')
            else:
                __import__(package)
        except ImportError:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
            print(f"✅ {package} installed")

install_packages()
# =============================================================================

import os
import json
import csv
import re
import time
import random
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# === CONFIGURATION =========================================================

SCRIPT_DIR = Path(__file__).parent.resolve()

def find_database_path():
    search_paths = [
        # v15.1: Added parent.parent for actual folder structure:
        # Script: scrapers and data/Scrapers/girls academy league scraper/scraper.py
        # DB:     scrapers and data/seedlinedata.db
        SCRIPT_DIR.parent.parent / "seedlinedata.db",
        SCRIPT_DIR.parent / "seedlinedata.db",
        SCRIPT_DIR / "seedlinedata.db",
        Path.cwd() / "seedlinedata.db",
        SCRIPT_DIR.parent / "scrapers and data" / "seedlinedata.db",
    ]
    for path in search_paths:
        if path.exists():
            return str(path.resolve())
    return str(SCRIPT_DIR.parent / "seedlinedata.db")

DATABASE_PATH = find_database_path()
OUTPUT_DIR = SCRIPT_DIR

GOTSPORT_SCHEDULE_URL = "https://system.gotsport.com/org_event/events/{event_id}/schedules?team={team_id}"
DEFAULT_EVENT_ID = "42137"  # Girls Academy 2024-25 season

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

MIN_DELAY = 2.0
MAX_DELAY = 5.0

# Age group mappings
U_TO_G_MAPPING = {'U13': 'G13', 'U14': 'G12', 'U15': 'G11', 'U16': 'G10', 'U17': 'G09', 'U18': 'G08', 'U19': 'G07'}
AGE_CODE_MAPPING = {
    '13': 'G13', '12': 'G12', '11': 'G11', '10': 'G10', '09': 'G09', '08': 'G08', '07': 'G07',
    'U13': 'G13', 'U14': 'G12', 'U15': 'G11', 'U16': 'G10', 'U17': 'G09', 'U18': 'G08', 'U19': 'G07',
}

# ===========================================================================

def parse_age_filter(ages_str: str) -> List[str]:
    """Parse comma-separated ages into list of standard age codes"""
    if not ages_str:
        return []
    
    ages = []
    for age in ages_str.split(','):
        age = age.strip().upper()
        if age in AGE_CODE_MAPPING:
            ages.append(AGE_CODE_MAPPING[age])
        elif re.match(r'^G\d{2}$', age):
            ages.append(age)
        elif re.match(r'^\d{2}$', age):
            ages.append(f"G{age}")
        elif age.startswith('U') and age[1:].isdigit():
            ages.append(U_TO_G_MAPPING.get(age, age))
    return ages

def normalize_team_for_id(team: str) -> str:
    """Normalize team name for matching - aggressive normalization for deduplication.

    Used for matching games across different sources where team names may vary.
    Original team names are preserved in the database.
    """
    if not team:
        return "unknown"
    normalized = team.lower().strip()

    # Remove common suffixes/words that vary between sources
    remove_patterns = [
        r'\s*-\s*$',                    # trailing dash
        r'\s+(sc|fc)\s*$',              # SC/FC at end
        r'\s+soccer\s*club\s*$',        # Soccer Club
        r'\s+futbol\s*club\s*$',        # Futbol Club
        r'\s+academy\s*$',              # Academy
        r'\s+united\s*$',               # United
        r'\s+club\s*$',                 # Club alone
    ]
    for pattern in remove_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.I)

    # Remove words that appear anywhere
    remove_words = ['soccer', 'futbol', 'fc', 'sc', 'academy', 'club', 'united']
    for word in remove_words:
        normalized = re.sub(r'\b' + word + r'\b', '', normalized, flags=re.I)

    # Remove age group patterns
    normalized = re.sub(r'\s*G\d{2}\s*', '', normalized)
    normalized = re.sub(r'\s*U\d{2}\s*', '', normalized, flags=re.I)

    # Remove all non-alphanumeric
    normalized = re.sub(r'[^a-z0-9]', '', normalized)

    return normalized[:30] if normalized else "unknown"


def make_canonical_game_id(date: str, team1: str, team2: str) -> str:
    """
    Create a canonical game ID that's the same regardless of home/away order.
    Uses normalized team names for consistent matching.
    """
    t1_clean = normalize_team_for_id(team1)
    t2_clean = normalize_team_for_id(team2)
    teams_sorted = sorted([t1_clean, t2_clean])
    return f"ga_{date}_{teams_sorted[0]}_{teams_sorted[1]}"

def export_csv(games: List[Dict], output_dir: Path, prefix: str) -> str:
    if not games:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = output_dir / f"{prefix}_games_{ts}.csv"
    fields = ['game_id','game_date','game_time','home_team','away_team','home_score','away_score',
              'age_group','conference','location','game_status','source_url','league']
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(games)
    return str(fp)


# Conference to state mapping for GA leagues
GA_CONFERENCE_STATE_MAP = {
    'Atlantic': None,  # Multiple states
    'Central': None,  # Multiple states  
    'Frontier': 'Texas',
    'Gulf': None,  # Multiple states
    'Heartland': None,  # Multiple states
    'Mid-Atlantic': None,  # Multiple states
    'Midwest': None,  # Multiple states
    'Northeast': None,  # Multiple states
    'Northwest': None,  # Multiple states
    'Ohio Valley': 'Ohio',
    'Southeast': None,  # Multiple states
    'Southwest': None,  # Multiple states
    'SoCal': 'California',
    'NorCal': 'California',
    'Texas': 'Texas',
    'Florida': 'Florida',
}


def infer_state_from_team(team_name: str, conference: str) -> Optional[str]:
    """Try to infer state from team name or conference.

    NOTE: We intentionally do NOT include 'GA ' as a Georgia indicator because
    Girls Academy teams often have ' GA' in their name as a league suffix
    (e.g., "TopHat 12G GA"). This was causing teams from California, Texas, etc.
    to be incorrectly mapped to Georgia state.
    Only match full word 'GEORGIA' to identify Georgia teams.
    """
    # Check conference first
    if conference:
        state = GA_CONFERENCE_STATE_MAP.get(conference)
        if state:
            return state

    # Try to infer from team name
    team_upper = team_name.upper() if team_name else ''

    # NOTE: 'GA ' is NOT included here - see docstring above
    state_indicators = {
        'TEXAS': 'Texas', 'TX ': 'Texas', ' TX': 'Texas',
        'CALIFORNIA': 'California', 'CA ': 'California', ' CA': 'California', 'SOCAL': 'California', 'NORCAL': 'California',
        'FLORIDA': 'Florida', 'FL ': 'Florida', ' FL': 'Florida',
        'VIRGINIA': 'Virginia', 'VA ': 'Virginia', ' VA': 'Virginia',
        'GEORGIA': 'Georgia',  # Only full word - NOT 'GA ' which conflicts with Girls Academy league suffix
        'NEW YORK': 'New York', 'NY ': 'New York', ' NY': 'New York',
        'PENNSYLVANIA': 'Pennsylvania', 'PA ': 'Pennsylvania', ' PA': 'Pennsylvania',
        'OHIO': 'Ohio', 'OH ': 'Ohio', ' OH': 'Ohio',
        'ILLINOIS': 'Illinois', 'IL ': 'Illinois', ' IL': 'Illinois',
        'MICHIGAN': 'Michigan', 'MI ': 'Michigan', ' MI': 'Michigan',
        'ARIZONA': 'Arizona', 'AZ ': 'Arizona', ' AZ': 'Arizona',
        'COLORADO': 'Colorado', 'CO ': 'Colorado', ' CO': 'Colorado',
        'WASHINGTON': 'Washington', 'WA ': 'Washington', ' WA': 'Washington',
        'MARYLAND': 'Maryland', 'MD ': 'Maryland', ' MD': 'Maryland',
        'NEW JERSEY': 'New Jersey', 'NJ ': 'New Jersey', ' NJ': 'New Jersey',
        'MASSACHUSETTS': 'Massachusetts', 'MA ': 'Massachusetts', ' MA': 'Massachusetts',
        'NORTH CAROLINA': 'North Carolina', 'NC ': 'North Carolina', ' NC': 'North Carolina',
        'SOUTH CAROLINA': 'South Carolina', 'SC ': 'South Carolina',
        'TENNESSEE': 'Tennessee', 'TN ': 'Tennessee', ' TN': 'Tennessee',
        'MISSOURI': 'Missouri', 'MO ': 'Missouri', ' MO': 'Missouri',
        'MINNESOTA': 'Minnesota', 'MN ': 'Minnesota', ' MN': 'Minnesota',
        'WISCONSIN': 'Wisconsin', 'WI ': 'Wisconsin', ' WI': 'Wisconsin',
        'INDIANA': 'Indiana', 'IN ': 'Indiana',
        'UTAH': 'Utah', 'UT ': 'Utah', ' UT': 'Utah',
        'NEVADA': 'Nevada', 'NV ': 'Nevada', ' NV': 'Nevada',
        'OREGON': 'Oregon', 'OR ': 'Oregon',
        'ALABAMA': 'Alabama', 'AL ': 'Alabama', ' AL': 'Alabama',
        'LOUISIANA': 'Louisiana', 'LA ': 'Louisiana',
        'KENTUCKY': 'Kentucky', 'KY ': 'Kentucky', ' KY': 'Kentucky',
        'CONNECTICUT': 'Connecticut', 'CT ': 'Connecticut', ' CT': 'Connecticut',
        'OKLAHOMA': 'Oklahoma', 'OK ': 'Oklahoma', ' OK': 'Oklahoma',
        'KANSAS': 'Kansas', 'KS ': 'Kansas', ' KS': 'Kansas',
        'IOWA': 'Iowa', 'IA ': 'Iowa', ' IA': 'Iowa',
        'NEBRASKA': 'Nebraska', 'NE ': 'Nebraska',
        'IDAHO': 'Idaho', 'ID ': 'Idaho', ' ID': 'Idaho',
    }
    
    for indicator, state in state_indicators.items():
        if indicator in team_upper:
            return state

    return None


# =============================================================================
# AMBIGUOUS TEAM NAME DISAMBIGUATION (v16b)
# =============================================================================
AMBIGUOUS_TEAMS = {
    'beach fc': {
        'states': {
            'CA': ['Southwest', 'SoCal', 'Southern California'],
            'VA': ['Mid-Atlantic', 'Southeast', 'Virginia'],
        }
    },
    'fc united': {
        'states': {
            'IL': ['Midwest', 'Northern Illinois', 'Central'],
            'PA': ['Mid-Atlantic', 'Northeast', 'Eastern Pennsylvania'],
        }
    },
    'sporting': {
        'states': {
            'CA': ['Southwest', 'SoCal', 'NorCal', 'Southern California', 'Northern California'],
            'MO': ['Midwest', 'Central', 'Heartland'],
            'KS': ['Midwest', 'Central', 'Heartland'],
        }
    },
    'united fc': {
        'states': {
            'GA': ['Southeast', 'Southern', 'Georgia'],
            'NC': ['Southeast', 'Southern', 'North Carolina'],
        }
    },
}


def disambiguate_team_name(team_name: str, context_conference: str = None,
                           context_state: str = None) -> str:
    """
    Add state identifier to ambiguous team names based on conference/state context.
    V16b: Prevents duplicate team entries by consistently adding state identifiers.
    """
    if not team_name:
        return team_name

    team_lower = team_name.lower().strip()

    matched_base = None
    for base_name in AMBIGUOUS_TEAMS:
        if team_lower.startswith(base_name) or team_lower == base_name:
            matched_base = base_name
            break
        if f' {base_name}' in team_lower or f'{base_name} ' in team_lower:
            matched_base = base_name
            break

    if not matched_base:
        return team_name

    # Already has a state identifier?
    if re.search(r'\s*\([A-Z]{2}\)\s*$', team_name):
        return team_name

    ambig_info = AMBIGUOUS_TEAMS[matched_base]
    states_info = ambig_info['states']
    inferred_state = None

    if context_state:
        state_upper = context_state.upper()
        if state_upper in states_info:
            inferred_state = state_upper

    if not inferred_state and context_conference:
        conf_lower = context_conference.lower()
        for state_code, conferences in states_info.items():
            for conf in conferences:
                if conf.lower() in conf_lower or conf_lower in conf.lower():
                    inferred_state = state_code
                    break
            if inferred_state:
                break

    if inferred_state:
        return f"{team_name.strip()} ({inferred_state})"

    return team_name


def save_ga_team(db_path: str, team: Dict) -> bool:
    """Save GA team to teams table"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Build a unique URL for the team
    team_url = team.get('source_url') or f"https://system.gotsport.com/org_event/events/{team.get('event_id')}/schedules?team={team.get('team_id')}"
    
    # Infer state from team name/conference (do this first for both insert and update)
    inferred_state = infer_state_from_team(team.get('team_name'), team.get('conference'))
    new_state = team.get('state') or inferred_state

    cur.execute("SELECT rowid, state FROM teams WHERE team_url = ?", (team_url,))
    existing = cur.fetchone()

    if existing:
        existing_state = existing[1]
        # Only update state if: existing is NULL/empty AND we have a new non-empty value
        # This ensures we NEVER overwrite existing good data
        final_state = new_state if (not existing_state or existing_state.strip() == '') and new_state else existing_state

        # Update existing team with any new data (including team_name to fix mismatches)
        cur.execute("""UPDATE teams SET
                      team_name = COALESCE(?, team_name),
                      club_name = COALESCE(?, club_name),
                      state = ?,
                      conference = COALESCE(?, conference),
                      last_updated = datetime('now')
                      WHERE team_url = ?""",
                   (team.get('team_name'), team.get('club_name'), final_state, team.get('conference'), team_url))
        conn.commit()
        conn.close()
        return False

    state = new_state
    
    cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference, 
                  event_id, state, scraped_at)
                  VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
               (team_url, team.get('club_name'), team.get('team_name'), team.get('age_group'),
                'Girls', 'GA', team.get('conference'), team.get('event_id'), state))
    conn.commit()
    conn.close()
    return True


class GAScraperV13:
    """GA Scraper v13 with admin UI support and improved score parsing"""
    
    def __init__(self, db_path: str = None, debug: bool = False, days_filter: int = None):
        self.db_path = db_path or DATABASE_PATH
        self.debug = debug
        self.days_filter = days_filter
        self.session = requests.Session()
        self.update_user_agent()
        
        self.games_scraped = 0
        self.teams_processed = 0
        self.scores_merged = 0
        self.errors = []
        self.all_games = []
        
        print(f"📁 Using database: {self.db_path}")
        if self.debug:
            print("🔍 Debug mode enabled - will show HTML parsing details")
    
    def update_user_agent(self):
        """Rotate user agent"""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://system.gotsport.com/",
        })
    
    def rate_limit(self):
        """Rate limiting"""
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
    
    # =========================================================================
    # FIX EXISTING PARTIAL SCORES
    # =========================================================================
    
    def fix_partial_scores_in_db(self):
        """
        Fix partial scores by finding game pairs scraped from both perspectives.
        """
        print("\n" + "="*70)
        print("🔧 FIXING PARTIAL SCORES IN DATABASE")
        print("="*70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE league = 'GA' 
            AND ((home_score IS NOT NULL AND away_score IS NULL)
                 OR (home_score IS NULL AND away_score IS NOT NULL))
        """)
        partial_before = cursor.fetchone()[0]
        print(f"Partial score games before: {partial_before}")
        
        cursor.execute("""
            SELECT game_id, game_date, home_team, away_team, home_score, away_score
            FROM games 
            WHERE league = 'GA'
        """)
        all_games = cursor.fetchall()
        
        game_groups = {}
        for row in all_games:
            game_id, game_date, home_team, away_team, home_score, away_score = row
            canonical_id = make_canonical_game_id(game_date, home_team, away_team)
            
            if canonical_id not in game_groups:
                game_groups[canonical_id] = []
            
            game_groups[canonical_id].append({
                'game_id': game_id,
                'game_date': game_date,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
            })
        
        merged = 0
        deleted = 0
        
        for canonical_id, games in game_groups.items():
            if len(games) < 2:
                continue
            
            best_game = None
            best_score = (None, None)
            
            for game in games:
                hs = game['home_score']
                aws = game['away_score']
                
                if hs is not None and aws is not None:
                    best_game = game
                    best_score = (hs, aws)
                    break
                elif hs is not None and best_score[0] is None:
                    best_score = (hs, best_score[1])
                    best_game = game
                elif aws is not None and best_score[1] is None:
                    best_score = (best_score[0], aws)
                    if best_game is None:
                        best_game = game
            
            if best_score[0] is not None and best_score[1] is not None:
                primary = games[0]
                final_home, final_away = None, None
                
                for game in games:
                    if game['home_score'] is not None and game['away_score'] is None:
                        if game['home_team'] == primary['home_team']:
                            final_home = game['home_score']
                        else:
                            final_away = game['home_score']
                    elif game['away_score'] is not None and game['home_score'] is None:
                        if game['away_team'] == primary['away_team']:
                            final_away = game['away_score']
                        else:
                            final_home = game['away_score']
                    elif game['home_score'] is not None and game['away_score'] is not None:
                        if game['home_team'] == primary['home_team']:
                            final_home = game['home_score']
                            final_away = game['away_score']
                        else:
                            final_home = game['away_score']
                            final_away = game['home_score']
                
                try:
                    cursor.execute("""
                        UPDATE games SET home_score = ?, away_score = ?, game_status = 'completed'
                        WHERE game_id = ?
                    """, (final_home, final_away, primary['game_id']))
                    merged += 1
                except:
                    pass
                
                for game in games[1:]:
                    try:
                        cursor.execute("DELETE FROM games WHERE game_id = ?", (game['game_id'],))
                        deleted += 1
                    except:
                        pass
        
        conn.commit()
        
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE league = 'GA' 
            AND ((home_score IS NOT NULL AND away_score IS NULL)
                 OR (home_score IS NULL AND away_score IS NOT NULL))
        """)
        partial_after = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n✅ Results:")
        print(f"  Games merged: {merged}")
        print(f"  Duplicates deleted: {deleted}")
        print(f"  Partial scores before: {partial_before}")
        print(f"  Partial scores after: {partial_after}")
        print(f"  Fixed: {partial_before - partial_after}")
        
        return merged
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    def get_all_ga_teams(self, age_group: str = "ALL", age_list: List[str] = None) -> List[Dict]:
        """Get all GA teams from database"""
        print("\n📊 Loading GA teams from database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        teams = {}
        
        # First try discovered_urls table
        try:
            q = "SELECT team_name, url, age_group, team_id, event_id, conference FROM discovered_urls WHERE league = 'GA'"
            params = []
            
            if age_list:
                placeholders = ','.join(['?' for _ in age_list])
                q += f" AND age_group IN ({placeholders})"
                params.extend(age_list)
            elif age_group != "ALL":
                q += " AND age_group = ?"
                params.append(age_group)
            
            cursor.execute(q, params)
            for team_name, url, age, team_id, event_id, conference in cursor.fetchall():
                if not team_id and url:
                    m = re.search(r'team=(\d+)', url)
                    if m:
                        team_id = m.group(1)
                if team_id:
                    teams[team_id] = {
                        'team_id': team_id,
                        'team_name': team_name,
                        'age_group': age,
                        'source_url': url or GOTSPORT_SCHEDULE_URL.format(
                            event_id=event_id or DEFAULT_EVENT_ID,
                            team_id=team_id
                        ),
                        'event_id': event_id or DEFAULT_EVENT_ID,
                        'conference': conference or ''
                    }
        except Exception as e:
            if self.debug:
                print(f"  discovered_urls query error: {e}")
        
        # Also check games table for additional teams
        cursor.execute("""
            SELECT DISTINCT source_url, home_team, age_group
            FROM games
            WHERE league = 'GA' AND source_url IS NOT NULL AND source_url != ''
        """)
        for url, team_name, age in cursor.fetchall():
            match = re.search(r'team=(\d+)', url)
            if match:
                team_id = match.group(1)
                if age_list:
                    if age not in age_list:
                        continue
                elif age_group != "ALL" and age != age_group:
                    continue
                    
                if team_id not in teams:
                    teams[team_id] = {
                        'team_id': team_id,
                        'team_name': team_name,
                        'age_group': age,
                        'source_url': url,
                        'event_id': DEFAULT_EVENT_ID
                    }
        
        # Also check ga_teams table if it exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ga_teams'")
        if cursor.fetchone():
            query = "SELECT team_id, team_name, age_group, source_url, event_id FROM ga_teams"
            if age_list:
                placeholders = ','.join(['?' for _ in age_list])
                query += f" WHERE age_group IN ({placeholders})"
                cursor.execute(query, age_list)
            elif age_group != "ALL":
                query += f" WHERE age_group = ?"
                cursor.execute(query, [age_group])
            else:
                cursor.execute(query)
            
            for team_id, team_name, age, url, event_id in cursor.fetchall():
                if team_id not in teams:
                    teams[team_id] = {
                        'team_id': team_id,
                        'team_name': team_name,
                        'age_group': age,
                        'source_url': url or GOTSPORT_SCHEDULE_URL.format(
                            event_id=event_id or DEFAULT_EVENT_ID,
                            team_id=team_id
                        ),
                        'event_id': event_id or DEFAULT_EVENT_ID
                    }
        
        conn.close()
        
        team_list = list(teams.values())
        print(f"✅ Found {len(team_list)} unique GA teams")
        
        return team_list
    
    # =========================================================================
    # IMPROVED GAME PARSING
    # =========================================================================
    
    def extract_scores_from_row(self, cells: List, cell_texts: List) -> Tuple[Optional[int], Optional[int]]:
        """
        Try multiple methods to extract scores from a table row.
        Returns (home_score, away_score) or (None, None)
        """
        home_score = None
        away_score = None
        
        # Method 1: Look for "X-Y" or "X - Y" pattern in any cell
        for text in cell_texts:
            score_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                if self.debug:
                    print(f"      Found score pattern '{text}' -> {home_score}-{away_score}")
                return home_score, away_score
        
        # Method 2: Check cell at position 3 specifically (results column)
        if len(cell_texts) > 3 and cell_texts[3]:
            text = cell_texts[3].strip()
            score_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                return home_score, away_score
        
        # Method 3: Look for separate score cells (two adjacent cells with just numbers)
        for i in range(len(cell_texts) - 1):
            if re.match(r'^\d+$', cell_texts[i].strip()) and re.match(r'^\d+$', cell_texts[i+1].strip()):
                home_score = int(cell_texts[i])
                away_score = int(cell_texts[i+1])
                if self.debug:
                    print(f"      Found separate score cells -> {home_score}-{away_score}")
                return home_score, away_score
        
        # Method 4: Check for score in a specific class or data attribute
        for cell in cells:
            if cell.get('data-home-score'):
                home_score = int(cell.get('data-home-score'))
            if cell.get('data-away-score'):
                away_score = int(cell.get('data-away-score'))
            
            score_span = cell.find('span', class_=re.compile(r'score', re.I))
            if score_span:
                score_text = score_span.get_text(strip=True)
                score_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', score_text)
                if score_match:
                    home_score = int(score_match.group(1))
                    away_score = int(score_match.group(2))
                    return home_score, away_score
        
        # Method 5: Look for W/L/T indicators with scores
        for text in cell_texts:
            wlt_match = re.search(r'[WLT]\s*(\d+)\s*[-–—]\s*(\d+)', text, re.I)
            if wlt_match:
                home_score = int(wlt_match.group(1))
                away_score = int(wlt_match.group(2))
                return home_score, away_score
        
        if self.debug and any(re.search(r'\d', t) for t in cell_texts):
            print(f"      ⚠️ Could not extract scores from: {cell_texts[:6]}")
        
        return home_score, away_score
    
    def parse_game_row(self, row, team_info: Dict) -> Optional[Dict]:
        """Parse a single game row from GotSport table - IMPROVED VERSION"""
        try:
            cells = row.find_all(['td', 'th'])
            
            if not cells or len(cells) < 5:
                return None
            
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            # Skip header rows
            if cell_texts[0] == 'Match #' or 'Match' in cell_texts[0] and '#' in cell_texts[0]:
                return None
            
            if self.debug:
                print(f"    Parsing row: {cell_texts[:6]}")
            
            game_data = {}
            
            # Column 0: Match ID
            game_data['match_id'] = cell_texts[0] if len(cell_texts) > 0 else None
            
            # Column 1: Date and Time
            if len(cell_texts) > 1 and cell_texts[1]:
                date_time_str = cell_texts[1]
                
                date_match = re.search(r'([A-Za-z]+ \d{1,2}, \d{4})', date_time_str)
                if date_match:
                    date_str = date_match.group(1)
                    parsed_date = None
                    
                    for fmt in ["%b %d, %Y", "%B %d, %Y"]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            parsed_date = dt.strftime("%Y-%m-%d")
                            break
                        except:
                            continue
                    
                    if not parsed_date:
                        return None
                    game_data['game_date'] = parsed_date
                else:
                    date_match2 = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_time_str)
                    if date_match2:
                        try:
                            dt = datetime.strptime(date_match2.group(1), "%m/%d/%Y")
                            game_data['game_date'] = dt.strftime("%Y-%m-%d")
                        except:
                            return None
                    else:
                        return None
                
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)', date_time_str, re.I)
                game_data['game_time'] = time_match.group(1).strip() if time_match else ""
            else:
                return None
            
            # Column 2: Home Team
            game_data['home_team'] = cell_texts[2] if len(cell_texts) > 2 else None
            
            # Column 4: Away Team (or 5 depending on layout)
            game_data['away_team'] = cell_texts[4] if len(cell_texts) > 4 else None
            
            if game_data['away_team'] and re.match(r'^[\d\s\-–—]+$', game_data['away_team']):
                game_data['away_team'] = cell_texts[5] if len(cell_texts) > 5 else None
            
            # Extract scores using improved method
            home_score, away_score = self.extract_scores_from_row(cells, cell_texts)
            game_data['home_score'] = home_score
            game_data['away_score'] = away_score
            game_data['game_status'] = 'completed' if home_score is not None and away_score is not None else 'scheduled'
            
            # Location (usually column 5 or 6)
            for i in [5, 6, 7]:
                if len(cell_texts) > i and cell_texts[i] and not re.match(r'^[\d\s\-–—WLT]+$', cell_texts[i]):
                    game_data['location'] = cell_texts[i]
                    break
            else:
                game_data['location'] = ""
            
            # Conference/Division
            for i in [7, 8, 6]:
                if len(cell_texts) > i and cell_texts[i]:
                    if 'division' in cell_texts[i].lower() or 'conference' in cell_texts[i].lower() or len(cell_texts[i]) > 3:
                        game_data['conference'] = cell_texts[i]
                        break
            else:
                game_data['conference'] = ""
            
            # Validate required fields
            if not (game_data.get('game_date') and 
                    game_data.get('home_team') and 
                    game_data.get('away_team')):
                if self.debug:
                    print(f"      ❌ Missing required fields")
                return None
            
            # Clean team names
            game_data['home_team'] = game_data['home_team'].strip()
            game_data['away_team'] = game_data['away_team'].strip()

            # V16b: Disambiguate team names that exist in multiple states
            conference = team_info.get('conference', '')
            game_data['home_team'] = disambiguate_team_name(game_data['home_team'], context_conference=conference)
            game_data['away_team'] = disambiguate_team_name(game_data['away_team'], context_conference=conference)

            # Generate CANONICAL game ID
            game_data['game_id'] = make_canonical_game_id(
                game_data['game_date'],
                game_data['home_team'],
                game_data['away_team']
            )
            
            # Use team's age group
            game_data['age_group'] = team_info.get('age_group')
            
            if self.debug:
                print(f"      ✅ Parsed: {game_data['home_team'][:20]} vs {game_data['away_team'][:20]} = {home_score}-{away_score}")
            
            return game_data
            
        except Exception as e:
            if self.debug:
                print(f"      ❌ Parse error: {e}")
            return None
    
    def scrape_team_schedule(self, team: Dict) -> List[Dict]:
        """Scrape schedule for a single team"""
        
        url = team.get('source_url')
        if not url:
            return []
        
        try:
            self.update_user_agent()
            resp = self.session.get(url, timeout=20)
            
            if resp.status_code != 200:
                self.errors.append(f"HTTP {resp.status_code} for {team.get('team_name', 'Unknown')}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            tables = soup.find_all('table')
            
            if self.debug:
                print(f"  Found {len(tables)} tables")
            
            if not tables:
                return []
            
            games = []
            
            for table in tables:
                header_row = table.find('tr')
                if not header_row:
                    continue
                
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                is_schedule_table = any(h in headers for h in ['Match #', 'Home Team', 'Home', 'Away Team', 'Away', 'Time', 'Date'])
                
                if is_schedule_table or 'Match' in str(headers):
                    if self.debug:
                        print(f"  Processing schedule table with headers: {headers[:6]}")
                    
                    rows = table.find_all('tr')[1:]
                    
                    for row in rows:
                        game = self.parse_game_row(row, team)
                        if game:
                            game['source_url'] = url
                            game['scraped_at'] = datetime.now().isoformat()
                            game['league'] = 'GA'
                            games.append(game)
            
            return games
            
        except requests.Timeout:
            self.errors.append(f"Timeout for {team.get('team_name', 'Unknown')}")
            return []
        except Exception as e:
            self.errors.append(f"Error for {team.get('team_name', 'Unknown')}: {str(e)}")
            return []
    
    def save_games_to_db(self, games: List[Dict]) -> int:
        """
        Save games to database with smart deduplication.

        Matching logic:
        1. First try exact game_id match
        2. If no match, fuzzy match by date + normalized teams + age group
        3. Check ALL existing games (not just those without scores) to prevent duplicates
        4. Update existing games with new scores if available
        5. Only insert if no matching game exists

        This preserves original team names while using normalized names for matching.
        """
        if not games:
            return 0

        # Filter by days if specified
        if self.days_filter:
            cutoff_date = (datetime.now() - timedelta(days=self.days_filter)).strftime('%Y-%m-%d')
            games = [g for g in games if g.get('game_date', '') >= cutoff_date]

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        cursor = conn.cursor()

        saved = 0
        merged = 0
        skipped = 0

        for game in games:
            try:
                home_norm = normalize_team_for_id(game.get('home_team', ''))
                away_norm = normalize_team_for_id(game.get('away_team', ''))

                # Step 1: Try exact game_id match
                cursor.execute("""
                    SELECT rowid, home_score, away_score, home_team, away_team
                    FROM games WHERE game_id = ?
                """, (game['game_id'],))
                existing = cursor.fetchone()

                # Step 2: If no exact match, fuzzy match on ALL games
                if not existing:
                    cursor.execute("""
                        SELECT rowid, home_score, away_score, home_team, away_team
                        FROM games
                        WHERE game_date = ? AND age_group = ? AND league = 'GA'
                    """, (game['game_date'], game['age_group']))

                    for row in cursor.fetchall():
                        existing_home = normalize_team_for_id(row[3] or '')
                        existing_away = normalize_team_for_id(row[4] or '')
                        # Match if teams match in either order
                        if (home_norm == existing_home and away_norm == existing_away) or \
                           (home_norm == existing_away and away_norm == existing_home):
                            existing = row
                            break

                # Step 3: Decide action based on what we found
                if existing:
                    rowid, old_home, old_away, old_home_team, old_away_team = existing
                    existing_has_scores = old_home is not None and old_away is not None
                    new_has_scores = game.get('home_score') is not None

                    if new_has_scores and not existing_has_scores:
                        # Update: existing game missing scores, new data has scores
                        cursor.execute("""
                            UPDATE games SET
                                home_score = ?, away_score = ?,
                                game_status = 'completed',
                                scraped_at = ?
                            WHERE rowid = ?
                        """, (game.get('home_score'), game.get('away_score'),
                              game['scraped_at'], rowid))
                        if cursor.rowcount > 0:
                            merged += 1
                    else:
                        # Skip: game already exists
                        skipped += 1
                else:
                    # Insert: no matching game found
                    cursor.execute("""
                        INSERT INTO games (
                            game_id, age_group, game_date, game_time,
                            home_team, away_team, home_score, away_score,
                            conference, location, scraped_at, source_url,
                            game_status, league, gender
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Girls')
                    """, (
                        game['game_id'], game['age_group'], game['game_date'],
                        game.get('game_time', ''), game['home_team'], game['away_team'],
                        game.get('home_score'), game.get('away_score'),
                        game.get('conference', ''), game.get('location', ''),
                        game['scraped_at'], game['source_url'],
                        game['game_status'], game['league']
                    ))
                    
                    if cursor.rowcount > 0:
                        saved += 1
                        
            except Exception as e:
                if self.debug:
                    print(f"    ⚠️ DB error: {e}")
        
        conn.commit()
        conn.close()
        
        if skipped > 0:
            print(f"    ⚠️ Skipped {skipped} duplicate games (team already has game on that date)")
        
        self.scores_merged += merged
        return saved + merged
    
    def filter_games(self, games: List[Dict], filter_type: str) -> List[Dict]:
        """Filter games by type"""
        if filter_type == "all":
            return games
        
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today - timedelta(days=7)
        
        filtered = []
        for game in games:
            try:
                game_date = datetime.strptime(game['game_date'], "%Y-%m-%d")
                
                if filter_type == "upcoming":
                    if game_date >= today:
                        filtered.append(game)
                elif filter_type == "past":
                    if game_date < today:
                        filtered.append(game)
                elif filter_type == "last_7_days":
                    if seven_days_ago <= game_date <= now:
                        filtered.append(game)
            except:
                if filter_type == "all":
                    filtered.append(game)
        
        return filtered
    
    def show_stats(self):
        """Show database statistics"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        print("\n" + "="*60)
        print("📊 GA STATISTICS")
        print("="*60)
        cur.execute("SELECT COUNT(*) FROM games WHERE league='GA'")
        print(f"Total GA games: {cur.fetchone()[0]:,}")
        cur.execute("SELECT age_group, COUNT(*) FROM games WHERE league='GA' GROUP BY age_group ORDER BY age_group")
        print("\nBy age:")
        for r in cur.fetchall():
            print(f"  {r[0]}: {r[1]:,}")
        
        # Check discovered_urls status
        try:
            cur.execute("SELECT scrape_status, COUNT(*) FROM discovered_urls WHERE league='GA' GROUP BY scrape_status")
            print("\nURL status:")
            for r in cur.fetchall():
                print(f"  {r[0] or 'pending'}: {r[1]}")
        except:
            pass
        conn.close()

    def validate_data(self):
        """Check for mismatches between discovered_urls and teams tables"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        print("\n" + "="*60)
        print("🔍 GA DATA VALIDATION CHECK")
        print("="*60)

        # Find mismatches where same URL has different team names
        cur.execute("""
            SELECT d.url, d.team_name as discovered_name, t.team_name as teams_name, d.age_group
            FROM discovered_urls d
            JOIN teams t ON d.url = t.team_url
            WHERE d.team_name != t.team_name
            AND d.league = 'GA'
        """)
        mismatches = cur.fetchall()

        if mismatches:
            print(f"⚠️  Found {len(mismatches)} team name mismatches:")
            for url, d_name, t_name, age in mismatches:
                print(f"   {age}: discovered='{d_name}' vs teams='{t_name}'")
            print("\nRun with --fix-mismatches to correct the teams table")
        else:
            print("✅ No mismatches found between discovered_urls and teams tables")

        conn.close()
        return len(mismatches)

    def fix_mismatches(self):
        """Fix team name mismatches by syncing teams table with discovered_urls"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Update teams table to match discovered_urls
        cur.execute("""
            UPDATE teams SET team_name = (
                SELECT d.team_name FROM discovered_urls d WHERE d.url = teams.team_url
            )
            WHERE team_url IN (
                SELECT d.url FROM discovered_urls d
                JOIN teams t ON d.url = t.team_url
                WHERE d.team_name != t.team_name AND d.league = 'GA'
            )
        """)
        fixed = cur.rowcount
        conn.commit()
        conn.close()

        if fixed:
            print(f"✅ Fixed {fixed} team name mismatches")
        else:
            print("No mismatches to fix")
        return fixed

    # =========================================================================
    # MAIN RUN METHOD
    # =========================================================================
    
    def run(self, age_group: str = "ALL", filter_type: str = "all", max_teams: int = None,
            age_list: List[str] = None):
        """Main scraping process"""
        print("\n" + "="*70)
        print("🏃 STARTING GA SCRAPER v15 - ADMIN UI COMPATIBLE")
        print("="*70)
        print(f"📁 Database: {self.db_path}")
        print(f"📊 Age Group: {age_group if not age_list else ','.join(age_list)}")
        print(f"📅 Filter: {filter_type}")
        if self.days_filter:
            print(f"📆 Days filter: last {self.days_filter} days")
        print(f"⏱️ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get all GA teams
        teams = self.get_all_ga_teams(age_group, age_list)
        
        if not teams:
            print("\n❌ No teams found in database!")
            return
        
        if max_teams:
            teams = teams[:max_teams]
            print(f"⚠️ Limited to {max_teams} teams for testing")
        
        total_teams = len(teams)
        print(f"\n📋 Processing {total_teams} teams...")
        print("="*70)
        
        teams_with_games = 0
        
        for i, team in enumerate(teams, 1):
            team_display = (team.get('team_name') or 'Unknown')[:40]
            pct = (i / total_teams) * 100
            print(f"\n📍 [{i}/{total_teams}] ({pct:.1f}%) {team_display}")
            
            # Save team to teams table
            save_ga_team(self.db_path, team)
            
            games = self.scrape_team_schedule(team)
            
            if games:
                filtered_games = self.filter_games(games, filter_type)
                
                if filtered_games:
                    complete = sum(1 for g in filtered_games 
                                   if g.get('home_score') is not None and g.get('away_score') is not None)
                    print(f"    ✅ Found {len(filtered_games)} games ({complete} with complete scores)")
                    
                    self.all_games.extend(filtered_games)
                    teams_with_games += 1
                    
                    saved = self.save_games_to_db(filtered_games)
                    if saved:
                        print(f"    💾 Saved/merged {saved} games")
                    
                    self.games_scraped += len(filtered_games)
                else:
                    print(f"    ⏭️ No games match filter")
            else:
                print(f"    ⏭️ No games found")
            
            self.teams_processed += 1
            self.rate_limit()
            
            # Longer break every 20 teams
            if self.teams_processed % 20 == 0:
                print(f"\n☕ Quick break... ({self.teams_processed}/{total_teams} teams processed)")
                time.sleep(random.uniform(30, 45))
        
        # Summary
        print("\n" + "="*70)
        print("📊 SCRAPING COMPLETE")
        print("="*70)
        print(f"✅ Teams processed: {self.teams_processed}")
        print(f"✅ Teams with games: {teams_with_games}")
        print(f"✅ Total games found: {len(self.all_games)}")
        print(f"✅ Scores merged: {self.scores_merged}")
        print(f"⏱️ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Export CSV
        if self.all_games:
            csv_path = export_csv(self.all_games, OUTPUT_DIR, 'GA')
            if csv_path:
                print(f"\n📄 CSV: {csv_path}")
        
        if self.errors:
            print(f"\n⚠️ Errors encountered: {len(self.errors)}")
            for err in self.errors[:10]:
                print(f"   - {err}")

        # Post-scrape validation check
        mismatch_count = self.validate_data_quiet()
        if mismatch_count > 0:
            print(f"\n⚠️  WARNING: {mismatch_count} team name mismatches detected!")
            print("   Run with --validate for details or --fix-mismatches to correct")

    def validate_data_quiet(self):
        """Quick mismatch count without printing details"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM discovered_urls d
            JOIN teams t ON d.url = t.team_url
            WHERE d.team_name != t.team_name
            AND d.league = 'GA'
        """)
        count = cur.fetchone()[0]
        conn.close()
        return count


# =============================================================================
# CLI INTERFACE
# =============================================================================

def prompt_age_group() -> str:
    """Prompt for age group"""
    print("\n" + "="*70)
    print("SELECT AGE GROUP")
    print("="*70)
    print("  1. U13 / G13")
    print("  2. U14 / G12")
    print("  3. U15 / G11")
    print("  4. U16 / G10")
    print("  5. U17 / G09")
    print("  6. U19 / G07")
    print("  7. ALL age groups")
    
    while True:
        try:
            choice = input("\nChoice (1-7): ").strip()
        except EOFError:
            return "ALL"
        mapping = {"1": "U13", "2": "U14", "3": "U15", "4": "U16", "5": "U17", "6": "U19", "7": "ALL"}
        if choice in mapping:
            return mapping[choice]
        print("Invalid choice")


def prompt_game_filter() -> str:
    """Prompt for filter"""
    print("\n" + "="*70)
    print("GAME FILTER")
    print("="*70)
    print("  1. All games")
    print("  2. Upcoming games only")
    print("  3. Past games only")
    print("  4. Last 7 days")
    
    while True:
        try:
            choice = input("\nChoice (1-4): ").strip()
        except EOFError:
            return "all"
        mapping = {"1": "all", "2": "upcoming", "3": "past", "4": "last_7_days"}
        if choice in mapping:
            return mapping[choice]
        print("Invalid choice")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='GA Scraper v13 - Admin UI Compatible')
    
    # Original arguments
    parser.add_argument('--fix-scores', action='store_true', help='Fix existing partial scores in database')
    parser.add_argument('--debug', action='store_true', help='Show HTML parsing details')
    parser.add_argument('--age', type=str, default=None, help='Age group (U13, U14, etc. or ALL)')
    parser.add_argument('--filter', type=str, default=None, help='Filter (all, upcoming, past, last_7_days)')
    parser.add_argument('--max', type=int, default=None, help='Max teams to process')
    parser.add_argument('--stats', action='store_true', help='Show stats only')
    
    # Admin UI arguments
    parser.add_argument('--gender', choices=['girls', 'boys', 'both'], default='girls',
                       help='Filter by gender (GA is girls only)')
    parser.add_argument('--ages', help='Comma-separated age groups (e.g., 13,12,11)')
    parser.add_argument('--days', type=int, help='Only games from last N days')
    parser.add_argument('--players', action='store_true', help='Include player scraping')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--validate', action='store_true', help='Check for data mismatches between tables')
    parser.add_argument('--fix-mismatches', action='store_true', help='Fix team name mismatches')

    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🎯 GA SCRAPER v15 - ADMIN UI COMPATIBLE")
    print("="*70)
    
    db_path = DATABASE_PATH
    if not os.path.exists(db_path):
        print(f"\n❌ Database not found: {db_path}")
        return
    
    debug = args.debug or args.verbose
    scraper = GAScraperV13(db_path, debug=debug, days_filter=args.days)
    
    if args.stats:
        scraper.show_stats()
        return

    if args.validate:
        scraper.validate_data()
        return

    if args.fix_mismatches:
        scraper.fix_mismatches()
        return

    # Fix existing partial scores first if requested
    if args.fix_scores:
        scraper.fix_partial_scores_in_db()
        if not args.no_confirm:
            print("\n" + "="*70)
            try:
                proceed = input("Continue with scraping? [y/N]: ").strip().lower()
            except EOFError:
                return
            if proceed != 'y':
                return
    
    # Parse age filter from admin UI
    age_list = parse_age_filter(args.ages) if args.ages else None
    
    # Determine options
    if args.no_confirm or args.ages:
        # Admin UI mode - skip prompts
        age_group = args.age or "ALL"
        filter_type = args.filter or "all"
        max_teams = args.max
    else:
        # Interactive mode
        age_group = args.age or prompt_age_group()
        filter_type = args.filter or prompt_game_filter()
        
        if args.max:
            max_teams = args.max
        else:
            try:
                test_mode = input("\nRun in test mode (first 5 teams only)? [y/N]: ").strip().lower()
            except EOFError:
                test_mode = 'n'
            max_teams = 5 if test_mode == 'y' else None
    
    # Run
    scraper.run(age_group=age_group, filter_type=filter_type, max_teams=max_teams, age_list=age_list)
    scraper.show_stats()


if __name__ == "__main__":
    main()
