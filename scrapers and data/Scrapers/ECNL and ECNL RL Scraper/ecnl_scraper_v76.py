#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ECNL COMPREHENSIVE SCRAPER v76 - RETRY LOGIC & ERROR TRACKING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERSION HISTORY & BUG FIXES:
═══════════════════════════════════════════════════════════════════════════════

V76 (Current) - Retry Logic & Error Tracking:
  ✅ NEW: Retry failed teams at end of scraping session
  ✅ NEW: File write retry with exponential backoff (handles Excel locking)
  ✅ NEW: scrape_status column in CSV to track incomplete records
  ✅ NEW: Detailed error logging for debugging
  ✅ FIX: "Permission denied" errors when CSV open in Excel

V75 - Improved Address Extraction:
  ✅ FIX: Address/City/State/ZIP extraction completely rewritten
  ✅ FIX: Now finds text directly below club name (heading element)
  ✅ FIX: Finds 5-digit ZIP first (most reliable marker)
  ✅ FIX: Handles full state names: Georgia -> GA, Colorado -> CO
  ✅ FIX: Handles lowercase state codes: Co -> CO
  ✅ FIX: Strips newlines from all extracted values (was corrupting CSV)
  ✅ FIX: Handles website formatting errors (duplicate state names)
  RESULT: State extraction improved from 4.4% to 97.6%

V74 - Incremental CSV Writing:
  ✅ NEW: CSV files created at START of scraping (not end)
  ✅ NEW: Data appended INCREMENTALLY as each team is scraped
  ✅ NEW: All 3 CSV files: games, teams, players
  ✅ BENEFIT: No data loss if scraper crashes mid-run

V73 - CSV Export Enhancement:
  ✅ NEW: Player count shown when --players flag used
  ✅ NEW: CSV export for TEAMS (ECNL_teams_*.csv)
  ✅ NEW: CSV export for PLAYERS (ECNL_players_*.csv)
  ✅ NEW: Session summary with counts

V72 - Critical JavaScript Regex Fix:
  ✅ CRITICAL FIX: JavaScript regex escaping in Python strings
  ✅ ISSUE: Python string "\\s" corrupted to invalid JS regex
  ✅ SOLUTION: Use "\\\\s" so Python passes "\\s" to JavaScript
  ✅ FIX: Browser now VISIBLE by default (use --headless to hide)
  ✅ FIX: Added scroll_to_load_all() for lazy-loaded content
  SYMPTOM: "SyntaxError: Invalid regular expression: missing /"

V70-V71 - Broken Versions (DO NOT USE):
  ❌ V71: JavaScript regex corrupted by single backslash escaping
  ❌ V70: Switched to HTML table parsing which doesn't work on TGS
  NOTE: TGS uses text-based layout, NOT HTML tables

V68 - Admin UI Compatibility:
  ✅ FIX: Database path for folder structure (parent.parent)
  ✅ NEW: --league option (ECNL, ECNL RL, or both)
  ✅ NEW: --reset-status to reset teams to pending before scraping

V63 - Original Working Version:
  ✅ Baseline working extraction logic
  ✅ Text-based parsing of TGS website
  ✅ All JavaScript regex patterns properly escaped

KNOWN ISSUES & SOLUTIONS:
═══════════════════════════════════════════════════════════════════════════════
  
  Issue: "Permission denied" on CSV files
  Cause: File open in Excel or another application
  Solution: V76 adds retry with delay, close Excel before scraping
  
  Issue: Games showing 0 found when website has data
  Cause: JavaScript regex corruption (V70-V71 bug)
  Solution: Use V72+ with proper double-backslash escaping
  
  Issue: State/City/ZIP missing from most teams
  Cause: Regex expected 2-letter state codes only
  Solution: V75 added full state name mapping + better targeting
  
  Issue: CSV rows corrupted with newlines
  Cause: Extracted text contained \\n characters
  Solution: V75 strips all newlines from extracted values

ADMIN UI ARGUMENTS (all supported):
═══════════════════════════════════════════════════════════════════════════════
  --gender girls|boys|both    Filter by gender
  --ages 13,12,11,10,09,08    Comma-separated age groups
  --days 90                   Only games from last N days
  --players                   Include player/roster scraping
  --verbose                   Show detailed output
  --no-confirm                Skip "Press Enter" prompts (auto for Admin UI)
  --league ECNL|ECNL RL|both  Specific league (default: both)
  --scrape                    Scrape pending teams only
  --scrape-all                Scrape all teams
  --reset-status              Reset teams to pending before scraping
  --headless                  Hide browser window (default: visible)

OUTPUT FILES:
═══════════════════════════════════════════════════════════════════════════════
  - ECNL_games_YYYYMMDD_HHMMSS.csv   - All games scraped
  - ECNL_teams_YYYYMMDD_HHMMSS.csv   - All teams with location data
  - ECNL_players_YYYYMMDD_HHMMSS.csv - All players (when --players used)
  - scrape_status column: 'complete', 'partial', 'error', 'retry_success'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import os
import re
import sys
import csv
import time
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()

def find_database_path():
    search_paths = [
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

ECNL_EVENT_ID = "3925"
ECNL_RL_EVENT_ID = "3932"

def normalize_date_to_iso(date_str: str) -> Optional[str]:
    """Convert various date formats to ISO format (YYYY-MM-DD)"""
    if not date_str:
        return None
    date_str = date_str.strip()
    
    # Try "Month Day, Year" format (e.g., "Sep 6, 2025")
    match = re.match(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', date_str)
    if match:
        month_str, day, year = match.groups()
        months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                  'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        month = months.get(month_str.lower()[:3])
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    
    # Try MM/DD/YYYY format
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', date_str)
    if match:
        month, day, year = match.groups()
        if len(year) == 2:
            year = f"20{year}"
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    return None

def standardize_age_group(age_str: str, gender: str = "Girls") -> str:
    """Standardize age group format to 'G08' or 'B08' format"""
    if not age_str:
        return ""
    
    age_str = str(age_str).strip().upper()
    prefix = "G" if gender.lower().startswith('g') else "B"
    
    # Extract just the number part
    numbers = re.findall(r'\d+', age_str)
    if numbers:
        num = numbers[0]
        # Handle 4-digit year format (2008 -> 08)
        if len(num) == 4:
            num = num[2:]
        # Ensure 2 digits
        num = num.zfill(2)[-2:]
        return f"{prefix}{num}"
    
    return age_str

def normalize_team_for_id(team: str) -> str:
    """Normalize team name for game ID generation"""
    if not team:
        return "unknown"
    normalized = team.lower().strip()
    normalized = re.sub(r'\s+(SC|FC|Academy|Soccer|Club)\s*$', '', normalized, flags=re.I)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    normalized = re.sub(r'\s+\d{2}G\s*$', '', normalized)
    normalized = re.sub(r'\s+G\d{2}\s*$', '', normalized)
    normalized = re.sub(r'\s+U\d{2}\s*$', '', normalized, flags=re.I)
    return normalized[:30]

def make_game_id(date: str, team1: str, team2: str, league: str, age: str = "") -> str:
    """Generate unique game ID"""
    date_iso = normalize_date_to_iso(date) or date
    t1 = normalize_team_for_id(team1)
    t2 = normalize_team_for_id(team2)
    teams_sorted = "_".join(sorted([t1, t2]))
    league_short = league.replace(" ", "").lower()[:6]
    age_clean = re.sub(r'[^a-zA-Z0-9]', '', age).lower()
    return f"{date_iso}_{teams_sorted}_{league_short}_{age_clean}"

def parse_age_filter(ages_str: str) -> List[str]:
    """Parse age filter string into list of age groups"""
    if not ages_str:
        return []
    ages = []
    for part in ages_str.split(','):
        part = part.strip()
        if part:
            if part.isdigit():
                ages.append(f"G{part.zfill(2)}")
                ages.append(f"B{part.zfill(2)}")
            else:
                ages.append(part.upper())
    return ages

def get_teams_from_db(db_path: str, league: str = None, age: str = None, 
                      gender: str = None, status: str = 'pending', limit: int = None) -> List[Dict]:
    """Get teams from discovered_urls table"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = "SELECT * FROM discovered_urls WHERE 1=1"
    params = []
    
    if league and league.lower() != 'both':
        if league.lower() == 'ecnl-rl':
            league = 'ECNL RL'
        elif league.lower() == 'ecnl':
            league = 'ECNL'
        query += " AND league = ?"
        params.append(league)
    elif league and league.lower() == 'both':
        query += " AND league IN ('ECNL', 'ECNL RL')"
    
    if age:
        age_list = parse_age_filter(age)
        if age_list:
            placeholders = ','.join(['?' for _ in age_list])
            query += f" AND age_group IN ({placeholders})"
            params.extend(age_list)
    
    if gender:
        if gender.lower() == 'girls':
            query += " AND (gender = 'Girls' OR age_group LIKE 'G%')"
        elif gender.lower() == 'boys':
            query += " AND (gender = 'Boys' OR age_group LIKE 'B%')"
    
    if status:
        query += " AND (scrape_status = ? OR scrape_status IS NULL)"
        params.append(status)
    
    query += " ORDER BY league, age_group, team_name"
    
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_status(db_path: str, url: str, status: str):
    """Update scrape status for a team"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE discovered_urls SET scrape_status = ?, last_scraped = datetime('now') WHERE url = ?",
               (status, url))
    conn.commit()
    conn.close()

def reset_scrape_status(db_path: str, league: str = None, gender: str = None, age_list: List[str] = None) -> int:
    """Reset scrape_status to 'pending' for teams matching filters"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    query = "UPDATE discovered_urls SET scrape_status = 'pending' WHERE 1=1"
    params = []
    
    if league and league.lower() != 'both':
        if league.lower() == 'ecnl-rl':
            league = 'ECNL RL'
        elif league.lower() == 'ecnl':
            league = 'ECNL'
        query += " AND league = ?"
        params.append(league)
    elif league and league.lower() == 'both':
        query += " AND league IN ('ECNL', 'ECNL RL')"
    
    if gender:
        if gender.lower() == 'girls':
            query += " AND (gender = 'Girls' OR age_group LIKE 'G%')"
        elif gender.lower() == 'boys':
            query += " AND (gender = 'Boys' OR age_group LIKE 'B%')"
    
    if age_list:
        placeholders = ','.join(['?' for _ in age_list])
        query += f" AND age_group IN ({placeholders})"
        params.extend(age_list)
    
    cur.execute(query, params)
    count = cur.rowcount
    conn.commit()
    conn.close()
    
    return count

def save_games(db_path: str, games: List[Dict], days_filter: int = None) -> Tuple[int, int]:
    """Save games to database"""
    if not games:
        return 0, 0
    
    if days_filter:
        cutoff_date = (datetime.now() - timedelta(days=days_filter)).strftime('%Y-%m-%d')
        games = [g for g in games if g.get('game_date_iso', '') >= cutoff_date]
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    new_count, updated = 0, 0
    
    for g in games:
        cur.execute("SELECT rowid, home_score, away_score FROM games WHERE game_id = ?", (g['game_id'],))
        ex = cur.fetchone()
        if ex:
            if (g.get('home_score') is not None) and (ex[1] is None or ex[2] is None):
                cur.execute("UPDATE games SET home_score=COALESCE(?,home_score), away_score=COALESCE(?,away_score) WHERE rowid=?",
                           (g.get('home_score'), g.get('away_score'), ex[0]))
                updated += 1
        else:
            cur.execute("""INSERT INTO games (game_id, game_date, game_date_iso, game_time, home_team, away_team, 
                          home_score, away_score, league, age_group, conference, location, game_status, source_url, scraped_at, gender)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                       (g['game_id'], g.get('game_date'), g.get('game_date_iso'), g.get('game_time'), g.get('home_team'),
                        g.get('away_team'), g.get('home_score'), g.get('away_score'), g.get('league'), g.get('age_group'),
                        g.get('conference'), g.get('location'), 'completed' if g.get('home_score') is not None else 'scheduled',
                        g.get('source_url'), g.get('gender', 'Girls')))
            new_count += 1
    conn.commit()
    conn.close()
    return new_count, updated

def save_team(db_path: str, team: Dict) -> bool:
    """Save team to database"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT rowid FROM teams WHERE team_url = ?", (team.get('team_url'),))
    existing = cur.fetchone()
    
    if existing:
        if team.get('state') or team.get('city'):
            cur.execute("""UPDATE teams SET 
                          state = COALESCE(?, state),
                          city = COALESCE(?, city),
                          street_address = COALESCE(?, street_address),
                          zip_code = COALESCE(?, zip_code),
                          official_website = COALESCE(?, official_website),
                          last_updated = datetime('now')
                          WHERE team_url = ?""",
                       (team.get('state'), team.get('city'), team.get('street_address'),
                        team.get('zip_code'), team.get('official_website'), team.get('team_url')))
            conn.commit()
            conn.close()
            return False
    else:
        cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference,
                      state, city, street_address, zip_code, official_website, event_id, scraped_at, last_updated)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
                   (team.get('team_url'), team.get('club_name'), team.get('team_name'), team.get('age_group'),
                    team.get('gender'), team.get('league'), team.get('conference'), team.get('state'),
                    team.get('city'), team.get('street_address'), team.get('zip_code'),
                    team.get('official_website'), team.get('event_id')))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def save_players(db_path: str, players: List[Dict], team_url: str, team_name: str) -> int:
    """Save players to database"""
    if not players:
        return 0
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    saved = 0
    for p in players:
        try:
            cur.execute("""INSERT OR REPLACE INTO players 
                          (team_url, team_name, player_name, first_name, last_name, jersey_number, position, graduation_year, scraped_at)
                          VALUES (?,?,?,?,?,?,?,?,datetime('now'))""",
                       (team_url, team_name, p.get('name'), p.get('first_name'), p.get('last_name'),
                        p.get('number'), p.get('position'), p.get('grad_year')))
            saved += 1
        except:
            pass
    conn.commit()
    conn.close()
    return saved

# CSV Field definitions - V76: Added scrape_status column
GAMES_CSV_FIELDS = ['game_id','game_date','game_date_iso','game_time','home_team','away_team','home_score','away_score',
                    'age_group','conference','location','game_status','source_url','league','gender','scrape_status']
TEAMS_CSV_FIELDS = ['team_url', 'team_name', 'club_name', 'age_group', 'gender', 'league', 'conference',
                    'state', 'city', 'street_address', 'zip_code', 'official_website', 'event_id', 'scrape_status']
PLAYERS_CSV_FIELDS = ['player_name', 'first_name', 'last_name', 'team_name', 'team_url', 
                      'jersey_number', 'position', 'graduation_year', 'age_group', 'league', 'scrape_status']

def create_csv_with_headers(filepath: Path, fields: List[str]) -> str:
    """V74: Create CSV file with headers only (called at start of scraping)"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
    return str(filepath)

def append_to_csv_with_retry(filepath: Path, data: List[Dict], fields: List[str], max_retries: int = 3) -> Tuple[int, str]:
    """
    V76: Append data rows to existing CSV file with retry logic.
    Returns (rows_written, error_message). error_message is empty on success.
    Handles "Permission denied" errors when file is open in Excel.
    """
    if not data or not filepath.exists():
        return 0, ""
    
    last_error = ""
    for attempt in range(max_retries):
        try:
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
                w.writerows(data)
            return len(data), ""
        except PermissionError as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                # Wait before retry: 1s, 2s, 4s (exponential backoff)
                time.sleep(2 ** attempt)
        except Exception as e:
            last_error = str(e)
            break
    
    return 0, last_error

def append_to_csv(filepath: Path, data: List[Dict], fields: List[str]) -> int:
    """V74: Append data rows to existing CSV file (backwards compatible wrapper)"""
    rows, _ = append_to_csv_with_retry(filepath, data, fields)
    return rows

def export_csv(games: List[Dict], output_dir: Path, prefix: str) -> str:
    """Export games to CSV file (batch mode for backwards compatibility)"""
    if not games:
        return ""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fp = output_dir / f"{prefix}_games_{ts}.csv"
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=GAMES_CSV_FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(games)
    return str(fp)

def export_teams_csv(teams: List[Dict], output_dir: Path, prefix: str) -> str:
    """Export teams to CSV file (batch mode for backwards compatibility)"""
    if not teams:
        return ""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fp = output_dir / f"{prefix}_teams_{ts}.csv"
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=TEAMS_CSV_FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(teams)
    return str(fp)

def export_players_csv(players: List[Dict], output_dir: Path, prefix: str) -> str:
    """Export players to CSV file (batch mode for backwards compatibility)"""
    if not players:
        return ""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fp = output_dir / f"{prefix}_players_{ts}.csv"
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=PLAYERS_CSV_FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(players)
    return str(fp)


class ECNLScraper:
    def __init__(self, db_path: str, headless: bool = False, debug: bool = False, 
                 include_players: bool = False, days_filter: int = None, output_dir: Path = None):
        self.db_path = db_path
        self.headless = headless  # Default to False (visible browser)
        self.debug = debug
        self.include_players = include_players
        self.days_filter = days_filter
        self.output_dir = output_dir or SCRIPT_DIR
        
        # Tracking for counts
        self.all_games = []
        self.all_teams = []
        self.all_players = []
        self.errors = 0
        
        # V74: CSV file paths (set when initialized)
        self.games_csv_path = None
        self.teams_csv_path = None
        self.players_csv_path = None
        self.csv_timestamp = None
    
    def initialize_csv_files(self, prefix: str = "ECNL"):
        """V74: Create CSV files with headers at start of scraping"""
        self.csv_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Games CSV - always created
        self.games_csv_path = self.output_dir / f"{prefix}_games_{self.csv_timestamp}.csv"
        create_csv_with_headers(self.games_csv_path, GAMES_CSV_FIELDS)
        print(f"📄 Created: {self.games_csv_path.name}")
        
        # Teams CSV - always created
        self.teams_csv_path = self.output_dir / f"{prefix}_teams_{self.csv_timestamp}.csv"
        create_csv_with_headers(self.teams_csv_path, TEAMS_CSV_FIELDS)
        print(f"📄 Created: {self.teams_csv_path.name}")
        
        # Players CSV - only if --players flag
        if self.include_players:
            self.players_csv_path = self.output_dir / f"{prefix}_players_{self.csv_timestamp}.csv"
            create_csv_with_headers(self.players_csv_path, PLAYERS_CSV_FIELDS)
            print(f"📄 Created: {self.players_csv_path.name}")
        
        return self.games_csv_path, self.teams_csv_path, self.players_csv_path

    async def scroll_to_load_all(self, page, max_scrolls=30, wait_time=0.8):
        """Scroll page to load all lazy-loaded content (from v63)"""
        try:
            initial_height = await page.evaluate("document.body.scrollHeight")
            stable_count = 0
            
            for _ in range(max_scrolls):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(wait_time)
                
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == initial_height:
                    stable_count += 1
                    if stable_count >= 2:
                        break
                else:
                    stable_count = 0
                initial_height = current_height
            
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ Scroll error: {e}")

    async def scrape_team_details(self, page, team: Dict) -> Dict:
        """
        V75: Improved extraction of team location details.
        Finds text directly below club name heading, extracts ZIP first,
        then parses city/state from same line. Handles full state names.
        """
        details = {}
        
        try:
            # Extract location info using improved JavaScript
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
                    
                    // Strategy 1: Find club name heading and get text below it
                    // The club name is typically in a heading (h1-h6) or bold element
                    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6, .team-name, .club-name');
                    let addressBlock = '';
                    
                    for (const heading of headings) {
                        const text = heading.textContent.trim();
                        // Skip navigation items, look for club-like names
                        if (text.length > 3 && text.length < 80 && !text.includes('Schedules') && !text.includes('Venues')) {
                            // Get the parent container and look for nearby text
                            let container = heading.parentElement;
                            if (container) {
                                const containerText = container.innerText || '';
                                // Look for 5-digit zip in this container
                                const zipMatch = containerText.match(/\\b(\\d{5})\\b/);
                                if (zipMatch) {
                                    addressBlock = containerText;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Strategy 2: Fallback - search entire page for address pattern
                    if (!addressBlock) {
                        addressBlock = document.body.innerText;
                    }
                    
                    // Clean up the text - normalize whitespace
                    addressBlock = addressBlock.replace(/\\t/g, ' ').replace(/  +/g, ' ');
                    
                    // Find the 5-digit ZIP code (most reliable marker)
                    const zipMatches = addressBlock.match(/\\b(\\d{5})\\b/g);
                    if (zipMatches && zipMatches.length > 0) {
                        // Take the first ZIP that appears in a reasonable context
                        for (const zip of zipMatches) {
                            // Get the line containing this ZIP
                            const lines = addressBlock.split('\\n').map(l => l.trim()).filter(l => l);
                            
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i];
                                if (line.includes(zip)) {
                                    info.zip = zip;
                                    
                                    // Parse this line for city and state
                                    // Format could be: "City, State ZIP" or "City State ZIP"
                                    const beforeZip = line.substring(0, line.indexOf(zip)).trim();
                                    
                                    // Try to find state (2-letter code or full name)
                                    let foundState = null;
                                    let foundCity = null;
                                    
                                    // Check for 2-letter state code (case insensitive)
                                    for (const code of stateCodes) {
                                        const codeRegex = new RegExp('\\\\b' + code + '\\\\b', 'i');
                                        if (codeRegex.test(beforeZip)) {
                                            foundState = code;
                                            // City is everything before the state
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
                                        // Clean city - remove any trailing punctuation
                                        if (foundCity) {
                                            info.city = foundCity.replace(/[,;:]$/, '').trim();
                                        }
                                    }
                                    
                                    // Get address from the line ABOVE the city/state/zip line
                                    if (i > 0) {
                                        const addressLine = lines[i - 1];
                                        // Make sure it looks like an address (has numbers or PO Box)
                                        if (/\\d/.test(addressLine) || /p\\.?o\\.?\\s*box/i.test(addressLine)) {
                                            info.address = addressLine.replace(/[\\n\\r]/g, ' ').trim();
                                        }
                                    }
                                    
                                    // If we found a ZIP and state, we're done
                                    if (info.zip && info.state) {
                                        break;
                                    }
                                }
                            }
                            
                            // If we found good data, stop looking
                            if (info.zip && info.state) {
                                break;
                            }
                        }
                    }
                    
                    // Look for official website link
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        const text = link.textContent.toLowerCase();
                        if (text.includes('official website')) {
                            const href = link.href;
                            if (href && !href.includes('totalglobalsports')) {
                                info.website = href;
                                break;
                            }
                        }
                    }
                    
                    // Clean all values - remove any newlines or excess whitespace
                    for (const key of Object.keys(info)) {
                        if (typeof info[key] === 'string') {
                            info[key] = info[key].replace(/[\\n\\r\\t]/g, ' ').replace(/  +/g, ' ').trim();
                        }
                    }
                    
                    return info;
                }
            """)
            
            if location_info:
                details['city'] = location_info.get('city')
                details['state'] = location_info.get('state')
                details['zip_code'] = location_info.get('zip')
                details['street_address'] = location_info.get('address')
                details['official_website'] = location_info.get('website')
                
        except Exception as e:
            if self.debug:
                print(f"    Details error: {e}")
        
        return details

    async def scrape_team_schedule(self, page, team: Dict) -> List[Dict]:
        """
        Scrape games from team page using text extraction.
        V72: Uses EXACT working code from v63 with proper regex escaping.
        """
        games = []
        url = team.get('url')
        if not url:
            return games
        
        team_name = team.get('team_name', 'Unknown')
        team_league = team.get('league', 'ECNL')
        team_age = team.get('age_group', '')
        team_gender = team.get('gender', 'Girls')
        team_conference = team.get('conference', '')
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Scroll to load all content
            await self.scroll_to_load_all(page)
            
            # V72: Use EXACT JavaScript from v63 with proper double-escaped regex
            # Note: In Python strings, \\ becomes \ which JavaScript sees as regex escape
            games_data = await page.evaluate("""
                () => {
                    const games = [];
                    const seen = new Set();
                    
                    // Get page text
                    const bodyText = document.body.innerText;
                    
                    // Find the Team Information / schedule section
                    const teamInfoIdx = bodyText.indexOf('Team Information');
                    const clubPlayersIdx = bodyText.indexOf('Club Players');
                    
                    let scheduleSection = bodyText;
                    if (teamInfoIdx > -1 && clubPlayersIdx > -1) {
                        scheduleSection = bodyText.substring(teamInfoIdx, clubPlayersIdx);
                    } else if (teamInfoIdx > -1) {
                        scheduleSection = bodyText.substring(teamInfoIdx);
                    }
                    
                    // Date pattern: "Sep 6, 2025" or "Sep 20, 2025"
                    const dateRegex = /(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+(\\d{1,2}),?\\s+(\\d{4})/gi;
                    const dateMatches = [...scheduleSection.matchAll(dateRegex)];
                    
                    dateMatches.forEach((match, idx) => {
                        const date = match[1] + ' ' + match[2] + ', ' + match[3];
                        const matchIdx = match.index;
                        
                        // Get context: 150 chars before and up to next date or 300 chars after
                        const startIdx = Math.max(0, matchIdx - 150);
                        
                        let endIdx;
                        if (idx + 1 < dateMatches.length) {
                            endIdx = dateMatches[idx + 1].index;
                        } else {
                            endIdx = Math.min(scheduleSection.length, matchIdx + 300);
                        }
                        
                        const beforeContext = scheduleSection.substring(startIdx, matchIdx);
                        const afterContext = scheduleSection.substring(matchIdx, endIdx);
                        
                        // Skip if this is from Next Game Preview section
                        if (beforeContext.includes('Next Game Preview') || beforeContext.includes('Parking Fee')) {
                            return;
                        }
                        
                        const game = {
                            date: date,
                            home_away: null,
                            opponent: null,
                            score: null,
                            home_score: null,
                            away_score: null,
                            time: null
                        };
                        
                        // Look for H or A indicator before the date
                        const haMatch = beforeContext.match(/\\b([HA])\\s*$/);
                        if (haMatch) {
                            game.home_away = haMatch[1] === 'H' ? 'Home' : 'Away';
                        }
                        
                        // Look for time pattern after date
                        const timeMatch = afterContext.match(/(\\d{1,2}:\\d{2}\\s*(?:AM|PM))/i);
                        if (timeMatch) {
                            game.time = timeMatch[1];
                        }
                        
                        // OPPONENT EXTRACTION (from v63)
                        let opponent = null;
                        
                        // Pattern 1: "Team Name ECNL RL G08/07"
                        let opponentMatch = afterContext.match(/([A-Za-z][A-Za-z0-9\\s()\\-'&.]+?)\\s+ECNL\\s+RL\\s+[GB]\\d{2,4}(?:\\/\\d{2,4})?/i);
                        if (opponentMatch) {
                            opponent = opponentMatch[1].trim();
                        }
                        
                        // Pattern 2: "Team Name ECNL G08" (no RL)
                        if (!opponent) {
                            opponentMatch = afterContext.match(/([A-Za-z][A-Za-z0-9\\s()\\-'&.]+?)\\s+ECNL\\s+[GB]\\d{2,4}(?:\\/\\d{2,4})?/i);
                            if (opponentMatch) {
                                opponent = opponentMatch[1].trim();
                            }
                        }
                        
                        // Pattern 3: After "field X"
                        if (!opponent) {
                            opponentMatch = afterContext.match(/(?:field|Field)\\s*\\d+[\\s\\n]+([A-Za-z][A-Za-z0-9\\s()\\-'&.]+?)\\s+ECNL/i);
                            if (opponentMatch) {
                                opponent = opponentMatch[1].trim();
                            }
                        }
                        
                        // Pattern 4: Fallback
                        if (!opponent) {
                            opponentMatch = afterContext.match(/([A-Za-z][A-Za-z0-9\\s()\\-'&.]{2,40})\\s+ECNL/i);
                            if (opponentMatch) {
                                opponent = opponentMatch[1].trim();
                            }
                        }
                        
                        // Clean up opponent name
                        if (opponent) {
                            opponent = opponent.replace(/\\s+/g, ' ').trim();
                            opponent = opponent.replace(/^\\d{1,2}:\\d{2}\\s*(AM|PM)?\\s*/i, '').trim();
                            opponent = opponent.replace(/^(field|Field)\\s*\\d+\\s*/i, '').trim();
                            opponent = opponent.replace(/^#\\d+\\s*/i, '').trim();
                            
                            if (opponent.length > 2 && opponent.length < 60) {
                                game.opponent = opponent;
                            }
                        }
                        
                        // SCORE EXTRACTION (from v63)
                        let scoreFound = false;
                        let scoreMatch;
                        
                        // Pattern 1: W/L/D followed by score
                        scoreMatch = afterContext.match(/\\b([WLD])\\b[\\s\\n]+(\\d+)\\s*[-\\u2013]\\s*(\\d+)/i);
                        if (scoreMatch) {
                            game.result = scoreMatch[1].toUpperCase();
                            game.home_score = parseInt(scoreMatch[2]);
                            game.away_score = parseInt(scoreMatch[3]);
                            game.score = scoreMatch[2] + '-' + scoreMatch[3];
                            scoreFound = true;
                        }
                        
                        // Pattern 2: Score near "View Box Score"
                        if (!scoreFound) {
                            const vbsIdx = afterContext.indexOf('View Box Score');
                            if (vbsIdx > 0) {
                                const beforeVBS = afterContext.substring(Math.max(0, vbsIdx - 50), vbsIdx);
                                scoreMatch = beforeVBS.match(/(\\d+)\\s*[-\\u2013]\\s*(\\d+)/);
                                if (scoreMatch) {
                                    game.home_score = parseInt(scoreMatch[1]);
                                    game.away_score = parseInt(scoreMatch[2]);
                                    game.score = scoreMatch[1] + '-' + scoreMatch[2];
                                    scoreFound = true;
                                    const wldMatch = beforeVBS.match(/\\b([WLD])\\b/i);
                                    if (wldMatch) {
                                        game.result = wldMatch[1].toUpperCase();
                                    }
                                }
                            }
                        }
                        
                        // Pattern 3: Standalone W/L/D + newline + score
                        if (!scoreFound) {
                            scoreMatch = afterContext.match(/\\n([WLD])\\n(\\d+)\\s*[-\\u2013]\\s*(\\d+)/i);
                            if (scoreMatch) {
                                game.result = scoreMatch[1].toUpperCase();
                                game.home_score = parseInt(scoreMatch[2]);
                                game.away_score = parseInt(scoreMatch[3]);
                                game.score = scoreMatch[2] + '-' + scoreMatch[3];
                                scoreFound = true;
                            }
                        }
                        
                        // Pattern 4: "D 0 - 0" format
                        if (!scoreFound) {
                            scoreMatch = afterContext.match(/([WLD])\\s*(\\d+)\\s*[-\\u2013]\\s*(\\d+)/i);
                            if (scoreMatch) {
                                game.result = scoreMatch[1].toUpperCase();
                                game.home_score = parseInt(scoreMatch[2]);
                                game.away_score = parseInt(scoreMatch[3]);
                                game.score = scoreMatch[2] + '-' + scoreMatch[3];
                                scoreFound = true;
                            }
                        }
                        
                        // Only add if we have meaningful data
                        const key = date + '-' + (game.opponent || '') + '-' + (game.score || '');
                        if (!seen.has(key) && (game.opponent || game.score)) {
                            seen.add(key);
                            games.push(game);
                        }
                    });
                    
                    return games;
                }
            """)
            
            # Convert to expected format
            age_group = standardize_age_group(team_age, team_gender)
            
            for g in games_data:
                opponent = g.get('opponent', '')
                home_away = g.get('home_away', 'Unknown')
                date_str = g.get('date', '')
                
                # Determine home/away teams
                if home_away == 'Home':
                    home_team = team_name
                    away_team = opponent if opponent else 'Unknown'
                elif home_away == 'Away':
                    home_team = opponent if opponent else 'Unknown'
                    away_team = team_name
                else:
                    home_team = team_name
                    away_team = opponent if opponent else 'Unknown'
                
                game = {
                    'game_id': make_game_id(date_str, home_team, away_team, team_league, age_group),
                    'game_date': date_str,
                    'game_date_iso': normalize_date_to_iso(date_str),
                    'game_time': g.get('time'),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': g.get('home_score'),
                    'away_score': g.get('away_score'),
                    'league': team_league,
                    'age_group': age_group,
                    'conference': team_conference,
                    'location': None,
                    'game_status': 'completed' if g.get('home_score') is not None else 'scheduled',
                    'source_url': url,
                    'gender': team_gender
                }
                games.append(game)
            
            # V73: Don't print here - let scrape_teams coordinate with player output
            
        except Exception as e:
            print(f"Page error: {e}")
            self.errors += 1
        
        return games

    async def scrape_team_roster(self, page, team: Dict) -> List[Dict]:
        """Scrape player roster from team page"""
        players = []
        
        try:
            roster_data = await page.evaluate("""
                () => {
                    const players = [];
                    const seen = new Set();
                    const bodyText = document.body.innerText;
                    
                    // Find players section
                    const playersIdx = bodyText.indexOf('Club Players');
                    if (playersIdx === -1) return players;
                    
                    const playerSection = bodyText.substring(playersIdx);
                    const chunks = playerSection.split('View Profile');
                    
                    chunks.forEach(chunk => {
                        const nameMatches = chunk.matchAll(/([A-Z][a-z]+),\\s*([A-Z][a-z]+)/g);
                        
                        for (const nameMatch of nameMatches) {
                            const lastName = nameMatch[1];
                            const firstName = nameMatch[2];
                            const fullName = firstName + ' ' + lastName;
                            
                            if (seen.has(fullName)) continue;
                            seen.add(fullName);
                            
                            const afterName = chunk.substring(chunk.indexOf(nameMatch[0]) + nameMatch[0].length);
                            const numberMatch = afterName.match(/#(\\d{1,2})\\b/);
                            const yearMatch = afterName.match(/\\b(202[5-9]|203[0-2])\\b/);
                            
                            let position = null;
                            const posMatch = afterName.match(/\\b(Goal\\s*Keeper|Goalkeeper|GK|Defender|Midfielder|Forward|Fwd|Mid|Def)\\b/i);
                            if (posMatch) position = posMatch[1];
                            
                            if (fullName && (position || yearMatch)) {
                                players.push({
                                    name: fullName,
                                    first_name: firstName,
                                    last_name: lastName,
                                    number: numberMatch ? numberMatch[1] : null,
                                    position: position,
                                    grad_year: yearMatch ? yearMatch[1] : null
                                });
                            }
                        }
                    });
                    
                    return players;
                }
            """)
            
            players = roster_data
            
        except Exception as e:
            if self.debug:
                print(f"    Roster error: {e}")
        
        return players

    async def scrape_teams(self, teams: List[Dict]) -> Tuple[int, int]:
        """
        V76: Scrape games for a list of teams with retry logic.
        - Tracks failed teams and retries them at the end
        - Uses retry logic for CSV writes (handles file locking)
        - Adds scrape_status to track incomplete records
        """
        total_new, total_upd = 0, 0
        failed_teams = []  # V76: Track failed teams for retry
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            print(f"\n📥 Scraping {len(teams)} teams...")
            print(f"🖥️  Browser: {'Hidden' if self.headless else 'Visible'}")
            
            for i, team in enumerate(teams, 1):
                team_name = team.get('team_name', 'Unknown')
                league = team.get('league', 'ECNL')
                age = team.get('age_group', '')
                
                print(f"[{i}/{len(teams)}] {team_name} ({league} {age}) ", end="", flush=True)
                
                try:
                    games = await self.scrape_team_schedule(page, team)
                    
                    if games:
                        # V76: Add scrape_status to games
                        for g in games:
                            g['scrape_status'] = 'complete'
                        
                        n, u = save_games(self.db_path, games, self.days_filter)
                        total_new += n
                        total_upd += u
                        self.all_games.extend(games)
                        update_status(self.db_path, team.get('url'), 'completed')
                        
                        # V76: Write games to CSV with retry logic
                        if self.games_csv_path:
                            rows, err = append_to_csv_with_retry(self.games_csv_path, games, GAMES_CSV_FIELDS)
                            if err:
                                print(f"⚠️ CSV write failed: {err}")
                                failed_teams.append(('games_csv', team, games))
                        
                        # Print game summary
                        with_opponent = sum(1 for g in games if g.get('away_team') != 'Unknown')
                        with_score = sum(1 for g in games if g.get('home_score') is not None)
                        
                        # Save team details
                        team_details = await self.scrape_team_details(page, team)
                        team_data = {
                            'team_url': team.get('url'),
                            'club_name': team.get('club_name'),
                            'team_name': team_name,
                            'age_group': age,
                            'gender': team.get('gender', 'Girls'),
                            'league': league,
                            'conference': team.get('conference', ''),
                            'event_id': team.get('event_id'),
                            'state': team_details.get('state'),
                            'city': team_details.get('city'),
                            'street_address': team_details.get('street_address'),
                            'zip_code': team_details.get('zip_code'),
                            'official_website': team_details.get('official_website'),
                            'scrape_status': 'complete',  # V76
                        }
                        save_team(self.db_path, team_data)
                        self.all_teams.append(team_data)
                        
                        # V76: Write team to CSV with retry logic
                        if self.teams_csv_path:
                            rows, err = append_to_csv_with_retry(self.teams_csv_path, [team_data], TEAMS_CSV_FIELDS)
                            if err:
                                print(f"⚠️ CSV write failed: {err}")
                                failed_teams.append(('teams_csv', team, [team_data]))
                        
                        # Scrape players if requested
                        player_count = 0
                        player_data_for_csv = []
                        if self.include_players:
                            players = await self.scrape_team_roster(page, team)
                            if players:
                                player_count = save_players(self.db_path, players, team.get('url', ''), team_name)
                                # Track players with team info for CSV export
                                for p in players:
                                    p['player_name'] = p.get('name')
                                    p['team_name'] = team_name
                                    p['team_url'] = team.get('url', '')
                                    p['age_group'] = age
                                    p['league'] = league
                                    p['jersey_number'] = p.get('number')
                                    p['graduation_year'] = p.get('grad_year')
                                    p['scrape_status'] = 'complete'  # V76
                                    player_data_for_csv.append(p)
                                self.all_players.extend(players)
                                
                                # V76: Write players to CSV with retry logic
                                if self.players_csv_path and player_data_for_csv:
                                    rows, err = append_to_csv_with_retry(self.players_csv_path, player_data_for_csv, PLAYERS_CSV_FIELDS)
                                    if err:
                                        print(f"⚠️ CSV write failed: {err}")
                                        failed_teams.append(('players_csv', team, player_data_for_csv))
                        
                        # Print combined output
                        if self.include_players:
                            print(f"✓ {len(games)} games ({with_score} scored) | 👥 {player_count} players")
                        else:
                            print(f"✓ {len(games)} games ({with_opponent} with opponent, {with_score} with scores)")
                    else:
                        print("- No games")
                        update_status(self.db_path, team.get('url'), 'no_games')
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"❌ {e}")
                    self.errors += 1
                    update_status(self.db_path, team.get('url'), 'error')
                    failed_teams.append(('scrape_error', team, str(e)))
            
            await browser.close()
        
        # V76: Retry failed teams
        if failed_teams:
            print(f"\n🔄 Retrying {len(failed_teams)} failed operations...")
            retry_success = 0
            
            for fail_type, team, data in failed_teams:
                team_name = team.get('team_name', 'Unknown')
                
                if fail_type == 'games_csv' and self.games_csv_path:
                    print(f"  Retry games CSV for {team_name}... ", end="")
                    rows, err = append_to_csv_with_retry(self.games_csv_path, data, GAMES_CSV_FIELDS, max_retries=5)
                    if not err:
                        print("✓")
                        retry_success += 1
                        # Update status to retry_success
                        for g in data:
                            g['scrape_status'] = 'retry_success'
                    else:
                        print(f"❌ {err}")
                        
                elif fail_type == 'teams_csv' and self.teams_csv_path:
                    print(f"  Retry teams CSV for {team_name}... ", end="")
                    rows, err = append_to_csv_with_retry(self.teams_csv_path, data, TEAMS_CSV_FIELDS, max_retries=5)
                    if not err:
                        print("✓")
                        retry_success += 1
                    else:
                        print(f"❌ {err}")
                        
                elif fail_type == 'players_csv' and self.players_csv_path:
                    print(f"  Retry players CSV for {team_name}... ", end="")
                    rows, err = append_to_csv_with_retry(self.players_csv_path, data, PLAYERS_CSV_FIELDS, max_retries=5)
                    if not err:
                        print("✓")
                        retry_success += 1
                    else:
                        print(f"❌ {err}")
                        
                elif fail_type == 'scrape_error':
                    # Can't retry scrape errors without browser - mark as failed
                    print(f"  ⚠️ {team_name}: scrape error (requires re-run)")
            
            print(f"  Retry complete: {retry_success}/{len(failed_teams)} successful")
        
        return total_new, total_upd

    def show_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        print("\n" + "="*60)
        print("📊 ECNL DATABASE STATISTICS")
        print("="*60)
        
        cur.execute("SELECT COUNT(*) FROM games WHERE league IN ('ECNL', 'ECNL RL')")
        total_games = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM games WHERE league IN ('ECNL', 'ECNL RL') AND home_score IS NOT NULL")
        completed = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT url) FROM discovered_urls WHERE league IN ('ECNL', 'ECNL RL')")
        total_teams = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM discovered_urls WHERE league IN ('ECNL', 'ECNL RL') AND scrape_status = 'completed'")
        scraped_teams = cur.fetchone()[0]
        
        print(f"Total ECNL Games: {total_games}")
        print(f"Completed Games: {completed}")
        print(f"Teams Discovered: {total_teams}")
        print(f"Teams Scraped: {scraped_teams}")
        print("="*60)
        
        conn.close()

    def cleanup_data(self):
        """Clean up corrupted data"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM games WHERE home_team IS NULL OR away_team IS NULL")
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        print(f"🧹 Cleaned up {deleted} invalid games")


async def main_async():
    parser = argparse.ArgumentParser(description='ECNL Scraper v72')
    parser.add_argument('--db', help='Database path')
    parser.add_argument('--discover', action='store_true', help='Discover team URLs')
    parser.add_argument('--scrape', action='store_true', help='Scrape pending teams')
    parser.add_argument('--scrape-all', action='store_true', help='Scrape all teams')
    parser.add_argument('--league', choices=['ECNL', 'ECNL RL', 'ecnl', 'ecnl-rl', 'both'], 
                       help='Specific league (default: both)')
    parser.add_argument('--age', help='Age group filter')
    parser.add_argument('--limit', type=int, help='Limit teams')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--cleanup', action='store_true', help='Clean corrupted data')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--headless', action='store_true', help='Hide browser (default: visible)')
    parser.add_argument('--gender', choices=['girls', 'boys', 'both'], default='both')
    parser.add_argument('--ages', help='Comma-separated age groups')
    parser.add_argument('--days', type=int, help='Only games from last N days')
    parser.add_argument('--players', action='store_true', help='Include player scraping')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--no-confirm', action='store_true', help='Skip prompts')
    parser.add_argument('--reset-status', action='store_true', help='Reset teams to pending')
    
    args = parser.parse_args()
    
    db_path = args.db or DATABASE_PATH
    
    print("=" * 60)
    print("🏃 ECNL COMPREHENSIVE SCRAPER v72")
    print("=" * 60)
    print(f"📂 Database: {db_path}")
    
    # Determine league filter
    league_filter = args.league
    if league_filter:
        if league_filter.lower() == 'ecnl-rl':
            league_filter = 'ECNL RL'
        elif league_filter.lower() == 'ecnl':
            league_filter = 'ECNL'
        elif league_filter.lower() == 'both':
            league_filter = 'both'
    else:
        league_filter = 'both'
    
    league_display = 'ECNL + ECNL RL (both)' if league_filter == 'both' else league_filter
    print(f"🏆 League: {league_display}")
    print(f"👤 Gender: {args.gender}")
    print(f"📅 Age groups: {args.ages or 'all'}")
    print(f"👥 Including players: {'Yes' if args.players else 'No'}")
    print(f"🖥️  Browser: {'Hidden' if args.headless else 'Visible'}")
    
    # Create scraper - V74: Pass output_dir
    scraper = ECNLScraper(
        db_path, 
        headless=args.headless,  # False by default (visible browser)
        debug=args.debug or args.verbose,
        include_players=args.players,
        days_filter=args.days,
        output_dir=OUTPUT_DIR
    )
    
    if args.stats:
        scraper.show_stats()
        return
    
    if args.cleanup:
        scraper.cleanup_data()
        return
    
    # Parse ages
    age_list = []
    if args.ages:
        age_list = parse_age_filter(args.ages)
    
    # Handle reset-status
    if args.reset_status:
        reset_count = reset_scrape_status(
            db_path, 
            league=league_filter,
            gender=args.gender if args.gender != 'both' else None,
            age_list=age_list if age_list else None
        )
        print(f"🔄 Reset {reset_count} teams to pending status")
    
    # Scrape teams
    if args.scrape or args.scrape_all or args.reset_status:
        status = None if args.scrape_all else 'pending'
        mode = "All teams" if args.scrape_all else "Pending teams only"
        print(f"🔄 Mode: {mode}")
        
        teams = get_teams_from_db(
            db_path, 
            league=league_filter,
            age=args.ages,
            gender=args.gender if args.gender != 'both' else None,
            status=status,
            limit=args.limit
        )
        
        print(f"📋 {len(teams)} teams to scrape")
        
        if teams:
            # V74: Initialize CSV files BEFORE scraping starts
            print(f"\n📁 Output folder: {OUTPUT_DIR}")
            scraper.initialize_csv_files('ECNL')
            
            if not args.no_confirm:
                input("\nPress Enter to start scraping...")
            
            new_cnt, upd_cnt = await scraper.scrape_teams(teams)
            
            print(f"\n✅ Complete: {new_cnt} new games, {upd_cnt} updated")
            
            # V74: Show CSV files that were updated (no need to re-export)
            print(f"\n📄 CSV Files (updated incrementally):")
            if scraper.games_csv_path:
                print(f"   Games:   {scraper.games_csv_path}")
            if scraper.teams_csv_path:
                print(f"   Teams:   {scraper.teams_csv_path}")
            if scraper.players_csv_path:
                print(f"   Players: {scraper.players_csv_path}")
            
            # V74: Show summary
            print(f"\n📊 Session Summary:")
            print(f"   Teams scraped: {len(scraper.all_teams)}")
            print(f"   Games found: {len(scraper.all_games)}")
            print(f"   Players found: {len(scraper.all_players)}")
            print(f"   Errors: {scraper.errors}")
            
            scraper.show_stats()
    else:
        print("\nNo action specified. Use --scrape, --stats, or --help")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
