#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASPIRE SCRAPER v8 - SMART DEDUPLICATION
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

V8b CHANGES (Current):
  ✅ NEW: AMBIGUOUS_TEAMS dictionary for teams that exist in multiple states
  ✅ NEW: disambiguate_team_name() adds state identifiers based on conference context
  ✅ FIX: Teams like "Beach FC" now get "(CA)" or "(VA)" suffix based on conference
  ✅ WHY: Prevents duplicate entries for teams with same name in different states

V8 CHANGES:
  ✅ SMART DEDUPLICATION - Fuzzy team name matching prevents duplicates
  ✅ normalize_team_for_id() - Aggressive team name normalization
  ✅ WAL MODE - Better database concurrency with busy_timeout
  ✅ 3-STEP MATCHING - exact game_id → fuzzy match → insert/update/skip
  ✅ ALL V7 FEATURES PRESERVED

V7 CHANGES:
  ✅ TEAM DATA COLLECTION - Saves team info to teams table
  ✅ STATE INFERENCE - Attempts to infer state from conference and team names

V5 CHANGES:
  ✅ ADMIN UI COMPATIBLE - Accepts --gender, --ages, --days, --players, --verbose
  ✅ NO-CONFIRM MODE - Runs without prompts when called from admin UI
  ✅ INCLUDES ALL V4 FEATURES - Database-centric, CSV export, status tracking
  ✅ BOTH GENDERS - Supports Girls and Boys (though ASPIRE is primarily girls)

ADMIN UI ARGUMENTS:
  --gender girls|boys|both    Filter by gender
  --ages 13G,12G,11G          Comma-separated age groups (ASPIRE format)
  --days 90                   Only games from last N days
  --players                   Include player scraping (if available)
  --verbose                   Show detailed output
  --no-confirm                Skip "Press Enter" prompts (for admin UI)

DATABASE STRUCTURE:
  Reads from: discovered_urls (league='ASPIRE')
  Writes to: games table

USAGE:
  # From Admin UI (no prompts):
  python ASPIRE_scraper_v5.py --gender girls --ages 13G,12G,11G --days 90 --no-confirm
  
  # Interactive mode:
  python ASPIRE_scraper_v5.py
  
  # Original commands still work:
  python ASPIRE_scraper_v5.py --all --limit 10
  python ASPIRE_scraper_v5.py --stats

OUTPUT:
  - Games saved to: seedlinedata.db
  - CSV exported to: ASPIRE_games_YYYYMMDD_HHMMSS.csv

CRITICAL IMPLEMENTATION NOTES - DO NOT REMOVE OR MODIFY:
═══════════════════════════════════════════════════════════════════════════════

  1. SMART DEDUPLICATION (save_games function):
     - Uses 3-step matching: exact game_id → fuzzy match → insert/update/skip
     - Fuzzy matching checks ALL existing games (not just those without scores)
     - Matches games regardless of home/away ordering
     - PRESERVE: The normalize_team_for_id() function and fuzzy matching logic
     - WHY: Prevents duplicates when team names vary between sources

  2. TEAM NAME NORMALIZATION (normalize_team_for_id function):
     - Removes: FC, SC, Academy, Club, United, Soccer, ASPIRE, age patterns
     - Removes all non-alphanumeric characters, truncates to 30 chars
     - PRESERVE: All remove_patterns and remove_words lists
     - WHY: Team names vary across sources but need to match for deduplication

  3. STATE INFERENCE (infer_state_from_team function):
     - IMPORTANT: Does NOT include 'GA ' as a Georgia indicator
     - ' GA' in team names may mean "Girls Academy" league suffix
     - Only full word 'GEORGIA' maps to Georgia state
     - PRESERVE: This behavior to avoid mis-mapping teams to Georgia
     - WHY: ASPIRE teams with ' GA' suffix are not necessarily from Georgia

  4. AGE GROUP CONVERSION (ASPIRE_AGE_MAPPING):
     - ASPIRE uses 13G, 12G format (not U13, G13)
     - Maps to standard G13, G12 format
     - PRESERVE: The ASPIRE_AGE_MAPPING and extract_age_from_team_name()
     - WHY: Ensures consistent age format across all scraped data

  5. DATABASE RESILIENCE:
     - WAL mode enabled for better concurrency
     - 30-second busy_timeout prevents "database locked" errors
     - PRESERVE: PRAGMA statements in save_games()
     - WHY: Multiple scrapers may access the database simultaneously

  6. SCRAPE STATUS TRACKING:
     - update_status() tracks which teams have been scraped
     - Allows --all flag to re-scrape vs only pending teams
     - PRESERVE: Status tracking for resume capability
     - WHY: Long scrapes can be interrupted; resume prevents re-scraping

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import subprocess
import sys

def install_packages():
    required = ['requests', 'beautifulsoup4']
    for package in required:
        try:
            __import__('bs4' if package == 'beautifulsoup4' else package)
        except ImportError:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])

install_packages()

import os
import csv
import re
import time
import random
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).parent.resolve()

def find_database_path():
    search_paths = [
        # v7.1: Added parent.parent for actual folder structure:
        # Script: scrapers and data/Scrapers/aspire scraper/scraper.py
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
GOTSPORT_URL = "https://system.gotsport.com/org_event/events/{event_id}/schedules?team={team_id}"
DEFAULT_EVENT_ID = "42138"  # ASPIRE 2024-25 season

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

U_TO_G_MAPPING = {'U13': 'G13', 'U14': 'G12', 'U15': 'G11', 'U16': 'G10', 'U17': 'G09', 'U18': 'G08', 'U19': 'G07'}

# ASPIRE uses different age format (13G, 12G, etc.)
ASPIRE_AGE_MAPPING = {
    '13': 'G13', '12': 'G12', '11': 'G11', '10': 'G10', '09': 'G09', '08': 'G08', '07': 'G07',
    '13G': 'G13', '12G': 'G12', '11G': 'G11', '10G': 'G10', '09G': 'G09', '08G': 'G08', '07G': 'G07',
    '08/07G': 'G08', '08/07': 'G08',
}

def extract_age_from_team_name(team_name: str) -> Optional[str]:
    if not team_name:
        return None
    match = re.search(r'(\d{2})G', team_name, re.IGNORECASE)
    if match:
        return f"G{match.group(1)}"
    match = re.search(r'U(\d{2})', team_name, re.IGNORECASE)
    if match:
        return U_TO_G_MAPPING.get(f"U{match.group(1)}", f"U{match.group(1)}")
    return None

def normalize_date_to_iso(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    date_str = str(date_str).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    months = {'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06',
              'jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12'}
    match = re.match(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', date_str)
    if match:
        m = match.group(1)[:3].lower()
        if m in months:
            return f"{match.group(3)}-{months[m]}-{match.group(2).zfill(2)}"
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', date_str)
    if match:
        y = match.group(3) if len(match.group(3)) == 4 else '20' + match.group(3)
        return f"{y}-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}"
    return None

def make_game_id(date: str, team1: str, team2: str, age: str = "") -> str:
    teams = sorted([team1.lower()[:20], team2.lower()[:20]])
    date_clean = re.sub(r'[^0-9]', '', str(date))[:8]
    return f"ASPIRE_{date_clean}_{teams[0][:12]}_{teams[1][:12]}_{age}"

def parse_aspire_ages(ages_str: str) -> List[str]:
    """Parse comma-separated ages into list of standard age codes for ASPIRE"""
    if not ages_str:
        return []
    
    ages = []
    for age in ages_str.split(','):
        age = age.strip().upper()
        if age in ASPIRE_AGE_MAPPING:
            ages.append(ASPIRE_AGE_MAPPING[age])
        elif re.match(r'^G\d{2}$', age):
            ages.append(age)
        elif re.match(r'^\d{2}G$', age):
            ages.append(f"G{age[:2]}")
        elif age.isdigit() and len(age) == 2:
            ages.append(f"G{age}")
    return ages

def get_teams_from_db(db_path: str, league: str, age: str = None, pending_only: bool = True, 
                      limit: int = None, age_list: List[str] = None) -> List[Dict]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    q = "SELECT team_name, url, age_group, team_id, event_id, conference FROM discovered_urls WHERE league = ?"
    p = [league]
    if pending_only:
        q += " AND (scrape_status IS NULL OR scrape_status = 'pending')"
    
    # Single age filter (legacy)
    if age:
        q += " AND age_group = ?"
        p.append(age)
    
    # Multiple age filter (from admin UI)
    if age_list:
        placeholders = ','.join(['?' for _ in age_list])
        q += f" AND age_group IN ({placeholders})"
        p.extend(age_list)
    
    q += " ORDER BY age_group, team_name"
    if limit:
        q += f" LIMIT {limit}"
    cur.execute(q, p)
    rows = cur.fetchall()
    conn.close()
    teams = []
    for r in rows:
        tid = r[3]
        if not tid and r[1]:
            m = re.search(r'team=(\d+)', r[1])
            if m: tid = m.group(1)
        teams.append({'team_name': r[0], 'url': r[1], 'age_group': r[2], 'team_id': tid, 
                     'event_id': r[4] or DEFAULT_EVENT_ID, 'conference': r[5] or ''})
    return teams

def update_status(db_path: str, url: str, status: str):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE discovered_urls SET scrape_status = ?, last_scraped = datetime('now') WHERE url = ?", (status, url))
    conn.commit()
    conn.close()

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
    remove_words = ['soccer', 'futbol', 'fc', 'sc', 'academy', 'club', 'united', 'aspire']
    for word in remove_words:
        normalized = re.sub(r'\b' + word + r'\b', '', normalized, flags=re.I)

    # Remove age group patterns
    normalized = re.sub(r'\s*G\d{2}\s*', '', normalized)
    normalized = re.sub(r'\s*U\d{2}\s*', '', normalized, flags=re.I)

    # Remove all non-alphanumeric
    normalized = re.sub(r'[^a-z0-9]', '', normalized)

    return normalized[:30] if normalized else "unknown"


# =============================================================================
# AMBIGUOUS TEAM NAME DISAMBIGUATION (v8b)
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
            'CA': ['Southwest', 'SoCal', 'NorCal'],
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


def disambiguate_team_name(team_name: str, context_conference: str = None) -> str:
    """
    Add state identifier to ambiguous team names based on conference context.
    V8b: Prevents duplicate team entries by consistently adding state identifiers.
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

    if context_conference:
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


def save_games(db_path: str, games: List[Dict], league: str, days_filter: int = None) -> Tuple[int, int]:
    """Save games to database with smart deduplication.

    Matching logic:
    1. First try exact game_id match
    2. If no match, use fuzzy matching by date + normalized teams + age + league
    3. Check ALL existing games (not just those without scores) to prevent duplicates
    4. Update existing games with new scores if available
    5. Only insert if no matching game exists

    This preserves original team names while using normalized names for matching.
    """
    if not games:
        return 0, 0

    # Filter by days if specified
    if days_filter:
        cutoff_date = (datetime.now() - timedelta(days=days_filter)).strftime('%Y-%m-%d')
        games = [g for g in games if g.get('game_date_iso', '') >= cutoff_date]

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    cur = conn.cursor()
    new_count, updated, skipped = 0, 0, 0

    for g in games:
        home_norm = normalize_team_for_id(g.get('home_team', ''))
        away_norm = normalize_team_for_id(g.get('away_team', ''))
        game_date = g.get('game_date_iso', '')
        age_group = g.get('age_group', '')

        # Step 1: Try exact game_id match
        cur.execute("SELECT rowid, home_score, away_score FROM games WHERE game_id = ?", (g['game_id'],))
        ex = cur.fetchone()

        # Step 2: If no exact match, fuzzy match on ALL games
        if not ex:
            cur.execute("""
                SELECT rowid, home_score, away_score, home_team, away_team FROM games
                WHERE game_date_iso = ? AND age_group = ? AND league = 'ASPIRE'
            """, (game_date, age_group))

            for row in cur.fetchall():
                existing_home = normalize_team_for_id(row[3] or '')
                existing_away = normalize_team_for_id(row[4] or '')
                # Match if teams match in either order
                if (home_norm == existing_home and away_norm == existing_away) or \
                   (home_norm == existing_away and away_norm == existing_home):
                    ex = (row[0], row[1], row[2])
                    break

        # Step 3: Decide action based on what we found
        if ex:
            existing_has_scores = ex[1] is not None and ex[2] is not None
            new_has_scores = g.get('home_score') is not None

            if new_has_scores and not existing_has_scores:
                # Update: existing game missing scores, new data has scores
                cur.execute("""UPDATE games SET
                    home_score = ?, away_score = ?,
                    game_status = 'completed',
                    scraped_at = datetime('now')
                    WHERE rowid = ?""",
                    (g.get('home_score'), g.get('away_score'), ex[0]))
                updated += 1
            else:
                # Skip: game already exists
                skipped += 1
        else:
            # Insert: no matching game found
            cur.execute("""INSERT INTO games (game_id, game_date, game_date_iso, game_time, home_team, away_team,
                          home_score, away_score, league, age_group, conference, location, game_status, source_url, scraped_at, gender)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),'Girls')""",
                       (g['game_id'], g.get('game_date'), g.get('game_date_iso'), g.get('game_time'), g.get('home_team'),
                        g.get('away_team'), g.get('home_score'), g.get('away_score'), league, g.get('age_group'),
                        g.get('conference'), g.get('location'), 'completed' if g.get('home_score') is not None else 'scheduled', g.get('source_url')))
            new_count += 1

    conn.commit()
    conn.close()

    if skipped > 0:
        print(f"   ⚠️ Skipped {skipped} duplicate games (already exist in database)")

    return new_count, updated

def export_csv(games: List[Dict], output_dir: Path, prefix: str) -> str:
    if not games:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = output_dir / f"{prefix}_games_{ts}.csv"
    fields = ['game_id','game_date','game_date_iso','game_time','home_team','away_team','home_score','away_score','age_group','conference','location','game_status','source_url','league']
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(games)
    return str(fp)


def infer_state_from_team(team_name: str, conference: str) -> Optional[str]:
    """Try to infer state from team name or conference.

    NOTE: We intentionally do NOT include 'GA ' as a Georgia indicator because
    team names may contain ' GA' as a Girls Academy league suffix
    (e.g., "TopHat 12G GA"). This was causing teams to be incorrectly mapped
    to Georgia state. Only match full word 'GEORGIA' to identify Georgia teams.
    """
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


def save_aspire_team(db_path: str, team: Dict) -> bool:
    """Save ASPIRE team to teams table"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Build a unique URL for the team
    team_url = team.get('url') or f"https://system.gotsport.com/org_event/events/{team.get('event_id')}/schedules?team={team.get('team_id')}"
    
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
                'Girls', 'ASPIRE', team.get('conference'), team.get('event_id'), state))
    conn.commit()
    conn.close()
    return True

class ASPIREScraper:
    def __init__(self, db_path: str, debug: bool = False, days_filter: int = None):
        self.db_path = db_path
        self.debug = debug
        self.days_filter = days_filter
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        self.all_games = []
        self.errors = 0

    def scrape_team(self, team: Dict) -> List[Dict]:
        games = []
        tid = team.get('team_id')
        if not tid:
            m = re.search(r'team=(\d+)', team.get('url', ''))
            tid = m.group(1) if m else None
        if not tid:
            return games
        
        url = GOTSPORT_URL.format(event_id=team.get('event_id', DEFAULT_EVENT_ID), team_id=tid)
        try:
            time.sleep(random.uniform(2.0, 4.0))
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            table = soup.find('table', class_=re.compile(r'schedule|games', re.I))
            if not table:
                for t in soup.find_all('table'):
                    if t.find('a', href=re.compile(r'team=\d+')):
                        table = t
                        break
            if not table:
                return games
            
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                g = self._parse_row(row, team, url)
                if g:
                    games.append(g)
        except Exception as e:
            if self.debug:
                print(f" Error: {e}")
            self.errors += 1
        return games

    def _parse_row(self, row, team: Dict, src_url: str) -> Optional[Dict]:
        try:
            txt = row.get_text(' ', strip=True)
            dm = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4}|\w{3,9}\s+\d{1,2},?\s+\d{4})', txt)
            if not dm:
                return None
            date_str = dm.group(1)
            
            links = row.find_all('a', href=re.compile(r'team=\d+'))
            if len(links) < 2:
                return None
            home = re.sub(r'\s*\([HA]\)\s*$', '', links[0].get_text(strip=True)).strip()
            away = re.sub(r'\s*\([HA]\)\s*$', '', links[1].get_text(strip=True)).strip()
            if not home or not away:
                return None

            # V8b: Disambiguate team names that exist in multiple states
            conference = team.get('conference', '')
            home = disambiguate_team_name(home, context_conference=conference)
            away = disambiguate_team_name(away, context_conference=conference)

            hs, aws = None, None
            sm = re.search(r'(\d+)\s*[-–:]\s*(\d+)', txt)
            if sm:
                hs, aws = int(sm.group(1)), int(sm.group(2))
            
            age = team.get('age_group')
            if not age or age.startswith('U'):
                age = extract_age_from_team_name(home) or extract_age_from_team_name(away) or age
            if age and age.startswith('U'):
                age = U_TO_G_MAPPING.get(age, age)
            
            return {
                'game_id': make_game_id(date_str, home, away, age),
                'game_date': date_str, 'game_date_iso': normalize_date_to_iso(date_str),
                'game_time': None, 'home_team': home, 'away_team': away,
                'home_score': hs, 'away_score': aws, 'age_group': age,
                'conference': team.get('conference', ''), 'location': None,
                'game_status': 'completed' if hs is not None else 'scheduled',
                'source_url': src_url, 'league': 'ASPIRE'
            }
        except:
            return None

    def scrape_all(self, teams: List[Dict]) -> Tuple[int, int]:
        total_new, total_upd = 0, 0
        print(f"\n📥 Scraping {len(teams)} ASPIRE teams...")
        for i, t in enumerate(teams, 1):
            print(f"[{i}/{len(teams)}] {t.get('team_name','')} ({t.get('age_group','')})", end=" ", flush=True)
            
            # Save team to teams table
            save_aspire_team(self.db_path, t)
            
            games = self.scrape_team(t)
            if games:
                n, u = save_games(self.db_path, games, 'ASPIRE', self.days_filter)
                total_new += n
                total_upd += u
                self.all_games.extend(games)
                print(f"✓ {len(games)} games ({n} new)")
                update_status(self.db_path, t.get('url'), 'completed')
            else:
                print("- No games")
                update_status(self.db_path, t.get('url'), 'no_games')

        # Post-scrape validation check
        mismatch_count = self.validate_data_quiet()
        if mismatch_count > 0:
            print(f"\n⚠️  WARNING: {mismatch_count} team name mismatches detected!")
            print("   Run with --validate for details or --fix-mismatches to correct")

        return total_new, total_upd

    def validate_data_quiet(self):
        """Quick mismatch count without printing details"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM discovered_urls d
            JOIN teams t ON d.url = t.team_url
            WHERE d.team_name != t.team_name
            AND d.league = 'ASPIRE'
        """)
        count = cur.fetchone()[0]
        conn.close()
        return count

    def clear_aspire_games(self):
        print("\n🗑️ Clearing ASPIRE games...")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM games WHERE league='ASPIRE'")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM games WHERE league='ASPIRE'")
        cur.execute("UPDATE discovered_urls SET scrape_status='pending' WHERE league='ASPIRE'")
        conn.commit()
        conn.close()
        print(f"✅ Deleted {count} ASPIRE games, reset URL status")

    def show_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        print("\n" + "="*60)
        print("📊 ASPIRE STATISTICS")
        print("="*60)
        cur.execute("SELECT COUNT(*) FROM games WHERE league='ASPIRE'")
        print(f"Total ASPIRE games: {cur.fetchone()[0]:,}")
        cur.execute("SELECT age_group, COUNT(*) FROM games WHERE league='ASPIRE' GROUP BY age_group ORDER BY age_group")
        print("\nBy age:")
        for r in cur.fetchall():
            print(f"  {r[0]}: {r[1]:,}")
        cur.execute("SELECT scrape_status, COUNT(*) FROM discovered_urls WHERE league='ASPIRE' GROUP BY scrape_status")
        print("\nURL status:")
        for r in cur.fetchall():
            print(f"  {r[0] or 'pending'}: {r[1]}")
        conn.close()

    def validate_data(self):
        """Check for mismatches between discovered_urls and teams tables"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        print("\n" + "="*60)
        print("🔍 ASPIRE DATA VALIDATION CHECK")
        print("="*60)

        # Find mismatches where same URL has different team names
        cur.execute("""
            SELECT d.url, d.team_name as discovered_name, t.team_name as teams_name, d.age_group
            FROM discovered_urls d
            JOIN teams t ON d.url = t.team_url
            WHERE d.team_name != t.team_name
            AND d.league = 'ASPIRE'
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
                WHERE d.team_name != t.team_name AND d.league = 'ASPIRE'
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


def main():
    parser = argparse.ArgumentParser(description='ASPIRE Scraper v5 - Admin UI Compatible')
    
    # Original arguments
    parser.add_argument('--db', help='Database path')
    parser.add_argument('--all', action='store_true', help='Scrape all teams')
    parser.add_argument('--age', help='Age group filter (single)')
    parser.add_argument('--limit', type=int, help='Limit teams')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--clear', action='store_true', help='Clear ASPIRE games')
    parser.add_argument('--debug', action='store_true')
    
    # Admin UI arguments
    parser.add_argument('--gender', choices=['girls', 'boys', 'both'], default='girls',
                       help='Filter by gender (ASPIRE is primarily girls)')
    parser.add_argument('--ages', help='Comma-separated age groups (e.g., 13G,12G,11G)')
    parser.add_argument('--days', type=int, help='Only games from last N days')
    parser.add_argument('--players', action='store_true', help='Include player scraping')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--validate', action='store_true', help='Check for data mismatches between tables')
    parser.add_argument('--fix-mismatches', action='store_true', help='Fix team name mismatches')

    args = parser.parse_args()
    
    db = args.db or DATABASE_PATH
    print("\n" + "="*60)
    print("🏃 ASPIRE SCRAPER v8 - Smart Deduplication")
    print("="*60)
    print(f"📂 Database: {db}")
    
    if args.gender:
        print(f"👤 Gender: {args.gender}")
    if args.ages:
        print(f"📅 Age groups: {args.ages}")
    if args.days:
        print(f"📆 Days filter: last {args.days} days")
    
    if not os.path.exists(db):
        print(f"❌ Database not found: {db}")
        sys.exit(1)
    
    debug = args.debug or args.verbose
    scraper = ASPIREScraper(db, debug, days_filter=args.days)
    
    if args.stats:
        scraper.show_stats()
        return

    if args.validate:
        scraper.validate_data()
        return

    if args.fix_mismatches:
        scraper.fix_mismatches()
        return

    if args.clear:
        scraper.clear_aspire_games()
        return
    
    # Determine if we should scrape
    should_scrape = args.all or args.no_confirm or args.ages
    
    if should_scrape or not args.stats:
        # Parse age filter
        age_list = parse_aspire_ages(args.ages) if args.ages else None
        
        teams = get_teams_from_db(db, 'ASPIRE', args.age, not args.all, args.limit, age_list)
        if not teams:
            print("\n⚠️ No ASPIRE teams to scrape. Use --all or run db_migrate_v1.py")
            scraper.show_stats()
            return
        
        print(f"\n📋 {len(teams)} teams to scrape")
        
        # Skip prompt if --no-confirm
        if not args.no_confirm:
            try:
                input("Press Enter to start...")
            except EOFError:
                pass
        
        new_cnt, upd_cnt = scraper.scrape_all(teams)
        
        if scraper.all_games:
            csv_path = export_csv(scraper.all_games, OUTPUT_DIR, 'ASPIRE')
            print(f"\n📄 CSV: {csv_path}")
        
        print("\n" + "="*60)
        print("✅ COMPLETE")
        print(f"   Teams: {len(teams)}, New: {new_cnt}, Updated: {upd_cnt}, Errors: {scraper.errors}")
        scraper.show_stats()

if __name__ == "__main__":
    main()
