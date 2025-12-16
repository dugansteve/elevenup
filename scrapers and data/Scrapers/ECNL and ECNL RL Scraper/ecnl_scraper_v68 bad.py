#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ECNL COMPREHENSIVE SCRAPER v67 - ADMIN UI COMPATIBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V67 CHANGES:
  ✅ TEAM DATA COLLECTION - Scrapes and saves team location data (city, state, address, website)
  ✅ TEAMS TABLE - Saves team info to teams table with full location details

V65 CHANGES:
  ✅ ADMIN UI COMPATIBLE - Accepts --gender, --ages, --days, --players, --verbose
  ✅ NO-CONFIRM MODE - Runs without prompts when called from admin UI
  ✅ INCLUDES ALL V64 FEATURES - Database-centric, CSV export, status tracking
  ✅ BOTH GENDERS - Supports Girls and Boys ECNL

ADMIN UI ARGUMENTS:
  --gender girls|boys|both    Filter by gender
  --ages 13,12,11,10,09,08    Comma-separated age groups
  --days 90                   Only games from last N days
  --players                   Include player/roster scraping
  --verbose                   Show detailed output
  --no-confirm                Skip "Press Enter" prompts (for admin UI)

DATABASE STRUCTURE:
  Reads from: discovered_urls (league='ECNL' or 'ECNL RL')
  Writes to: games, teams, players tables

USAGE:
  # From Admin UI (no prompts):
  python ecnl_scraper_v65.py --gender both --ages 13,12,11 --days 90 --no-confirm
  
  # Interactive mode:
  python ecnl_scraper_v65.py
  
  # Original commands still work:
  python ecnl_scraper_v65.py --scrape --limit 10
  python ecnl_scraper_v65.py --stats

OUTPUT:
  - Data saved to: seedlinedata.db
  - CSV exported to: ECNL_games_YYYYMMDD_HHMMSS.csv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import os
import re
import sys
import csv
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
        # v67.1: Added parent.parent for actual folder structure:
        # Script: scrapers and data/Scrapers/ECNL and ECNL RL Scraper/scraper.py
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

# ECNL Event IDs
ECNL_EVENT_ID = "3925"
ECNL_RL_EVENT_ID = "3926"

# Conference URLs
ECNL_CONFERENCES = {
    "ECNL": {
        "event_id": "3925",
        "conferences": [
            "Mid-Atlantic", "New England", "North Atlantic", "Northeast", "Ohio Valley",
            "Florida", "Piedmont", "Southeast", "South Atlantic", "Texas",
            "Midwest", "Heartland", "Southwest",
            "Mountain", "Northwest", "Southern California", "Northern California"
        ]
    },
    "ECNL RL": {
        "event_id": "3926",
        "conferences": [
            "Mid-Atlantic", "New England", "North Atlantic", "Northeast", "Ohio Valley",
            "Florida", "Piedmont", "Southeast", "South Atlantic", "Texas",
            "Midwest", "Heartland", "Southwest",
            "Mountain", "Northwest", "Southern California", "Northern California"
        ]
    }
}

# Age group mappings
AGE_CODE_TO_STANDARD = {
    '13': 'G13', '12': 'G12', '11': 'G11', '10': 'G10', '09': 'G09', '08': 'G08', '07': 'G07',
    'U13': 'G13', 'U14': 'G12', 'U15': 'G11', 'U16': 'G10', 'U17': 'G09', 'U18': 'G08', 'U19': 'G07',
}

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

def standardize_age_group(age_str: str, gender: str = "Girls") -> str:
    """Convert various age formats to standard format like G08, G09, etc."""
    if not age_str:
        return "Unknown"
    
    age_str = str(age_str).upper().strip()
    prefix = 'G' if gender.lower() == 'girls' else 'B'
    
    # Already in correct format
    if re.match(r'^[GB]\d{2}$', age_str):
        return age_str
    
    # G2008/2009 format
    match = re.match(r'[GB]?(\d{4})(?:/(\d{4}))?', age_str)
    if match:
        year = match.group(2) or match.group(1)
        birth_year = int(year)
        grad_year = birth_year + 18
        age_code = str(grad_year)[-2:]
        return f"{prefix}{age_code}"
    
    # U13, U14 format
    match = re.match(r'U(\d{2})', age_str)
    if match:
        u_age = int(match.group(1))
        grad_map = {'13':'13', '14':'12', '15':'11', '16':'10', '17':'09', '18':'08', '19':'07'}
        return f"{prefix}{grad_map.get(str(u_age), match.group(1))}"
    
    return age_str

def normalize_team_for_id(team: str) -> str:
    """Normalize team name for game ID generation - removes variations that cause duplicates"""
    if not team:
        return ""
    
    # Strip whitespace
    normalized = team.strip()
    
    # Remove common suffixes that cause variations
    normalized = re.sub(r'\s+(SC|FC|Academy|Soccer|Club)\s*$', '', normalized, flags=re.I)
    
    # Remove age suffixes
    normalized = re.sub(r'\s+\d{2}G\s*$', '', normalized)
    normalized = re.sub(r'\s+G\d{2}\s*$', '', normalized)
    normalized = re.sub(r'\s+U\d{2}\s*$', '', normalized, flags=re.I)
    
    # Convert to lowercase and remove non-alphanumeric
    normalized = re.sub(r'[^a-zA-Z0-9]', '', normalized.lower())
    
    return normalized[:20]

def make_game_id(date: str, team1: str, team2: str, league: str, age: str = "") -> str:
    # Normalize team names to prevent duplicates from name variations
    t1_norm = normalize_team_for_id(team1)
    t2_norm = normalize_team_for_id(team2)
    teams = sorted([t1_norm, t2_norm])
    date_clean = re.sub(r'[^0-9]', '', str(date))[:8]
    league_prefix = "ECNL" if "ECNL" in league else "RL"
    return f"{league_prefix}_{date_clean}_{teams[0][:12]}_{teams[1][:12]}_{age}"

def parse_age_filter(ages_str: str) -> List[str]:
    """Parse comma-separated ages into list of standard age codes"""
    if not ages_str:
        return []
    
    ages = []
    for age in ages_str.split(','):
        age = age.strip()
        if age in AGE_CODE_TO_STANDARD:
            ages.append(AGE_CODE_TO_STANDARD[age])
        elif re.match(r'^[GB]\d{2}$', age.upper()):
            ages.append(age.upper())
        else:
            # Try to convert raw number
            if age.isdigit() and len(age) == 2:
                ages.append(f"G{age}")
    return ages

def get_teams_from_db(db_path: str, league: str = None, age: str = None, 
                      pending_only: bool = True, limit: int = None,
                      gender: str = None, age_list: List[str] = None,
                      days_back: int = None) -> List[Dict]:
    """Get teams from database with flexible filtering"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    if league:
        q = "SELECT team_name, url, age_group, league, event_id, conference, gender FROM discovered_urls WHERE league = ?"
        p = [league]
    else:
        q = "SELECT team_name, url, age_group, league, event_id, conference, gender FROM discovered_urls WHERE league IN ('ECNL', 'ECNL RL')"
        p = []
    
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
    
    # Gender filter
    if gender and gender != 'both':
        gender_value = 'Girls' if gender == 'girls' else 'Boys'
        q += " AND gender = ?"
        p.append(gender_value)
    
    q += " ORDER BY league, age_group, team_name"
    if limit:
        q += f" LIMIT {limit}"
    
    cur.execute(q, p)
    rows = cur.fetchall()
    conn.close()
    
    teams = []
    for r in rows:
        teams.append({
            'team_name': r[0], 'url': r[1], 'age_group': r[2],
            'league': r[3], 'event_id': r[4], 'conference': r[5] or '',
            'gender': r[6] or 'Girls'
        })
    return teams

def update_status(db_path: str, url: str, status: str):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE discovered_urls SET scrape_status = ?, last_scraped = datetime('now') WHERE url = ?", (status, url))
    conn.commit()
    conn.close()

def save_games(db_path: str, games: List[Dict], days_filter: int = None) -> Tuple[int, int]:
    """Save games to database, optionally filtering by date"""
    if not games:
        return 0, 0
    
    # Filter by days if specified
    if days_filter:
        cutoff_date = (datetime.now() - timedelta(days=days_filter)).strftime('%Y-%m-%d')
        games = [g for g in games if g.get('game_date_iso', '') >= cutoff_date]
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    new_count, updated, skipped = 0, 0, 0
    
    for g in games:
        # Primary check: exact game_id match
        cur.execute("SELECT rowid, home_score, away_score FROM games WHERE game_id = ?", (g['game_id'],))
        ex = cur.fetchone()
        if ex:
            if (g.get('home_score') is not None) and (ex[1] is None or ex[2] is None):
                cur.execute("UPDATE games SET home_score=COALESCE(?,home_score), away_score=COALESCE(?,away_score) WHERE rowid=?",
                           (g.get('home_score'), g.get('away_score'), ex[0]))
                updated += 1
        else:
            # Secondary check: In ECNL/ECNL-RL league, teams can only play 1 game per day
            # Check if either team already has a game on this date in this league
            league = g.get('league', '')
            if league in ('ECNL', 'ECNL-RL'):
                cur.execute("""
                    SELECT game_id FROM games 
                    WHERE game_date_iso = ? 
                    AND age_group = ?
                    AND league = ?
                    AND (home_team = ? OR away_team = ? OR home_team = ? OR away_team = ?)
                """, (
                    g.get('game_date_iso'),
                    g.get('age_group'),
                    league,
                    g.get('home_team'), g.get('home_team'),
                    g.get('away_team'), g.get('away_team')
                ))
                
                existing_game = cur.fetchone()
                if existing_game:
                    # Team already has a game on this date - skip as duplicate
                    skipped += 1
                    continue
            
            # No duplicate found, insert
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
    if skipped > 0:
        print(f"   ⚠️ Skipped {skipped} duplicate games (team already has game on that date)")
    return new_count, updated

def save_team(db_path: str, team: Dict) -> bool:
    """Save team to database with location data (state, city, address, website)"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT rowid FROM teams WHERE team_url = ?", (team.get('team_url'),))
    existing = cur.fetchone()
    
    if existing:
        # Update existing team with location data if we have new data
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
    
    cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference, 
                  event_id, state, city, street_address, zip_code, official_website, scraped_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
               (team.get('team_url'), team.get('club_name'), team.get('team_name'), team.get('age_group'),
                team.get('gender'), team.get('league'), team.get('conference'), team.get('event_id'),
                team.get('state'), team.get('city'), team.get('street_address'), 
                team.get('zip_code'), team.get('official_website')))
    conn.commit()
    conn.close()
    return True

def save_players(db_path: str, players: List[Dict], team_url: str, team_name: str) -> int:
    if not players:
        return 0
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    count = 0
    for p in players:
        cur.execute("""INSERT OR IGNORE INTO players (team_url, team_name, player_name, first_name, last_name,
                      jersey_number, position, graduation_year, height, hometown, high_school, club, 
                      college_commitment, age_group, league, scraped_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                   (team_url, team_name, p.get('player_name'), p.get('first_name'), p.get('last_name'),
                    p.get('jersey_number'), p.get('position'), p.get('graduation_year'), p.get('height'),
                    p.get('hometown'), p.get('high_school'), p.get('club'), p.get('college_commitment'),
                    p.get('age_group'), p.get('league')))
        if cur.rowcount > 0:
            count += 1
    conn.commit()
    conn.close()
    return count

def export_csv(games: List[Dict], output_dir: Path, prefix: str) -> str:
    if not games:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = output_dir / f"{prefix}_games_{ts}.csv"
    fields = ['game_id','game_date','game_date_iso','game_time','home_team','away_team','home_score','away_score',
              'age_group','conference','location','game_status','source_url','league','gender']
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(games)
    return str(fp)

class ECNLScraper:
    def __init__(self, db_path: str, headless: bool = True, debug: bool = False, 
                 include_players: bool = False, days_filter: int = None):
        self.db_path = db_path
        self.headless = headless
        self.debug = debug
        self.include_players = include_players
        self.days_filter = days_filter
        self.all_games = []
        self.errors = 0

    async def scrape_team_details(self, page, team: Dict) -> Dict:
        """Scrape team location details (city, state, address, website) from team page"""
        details = {}
        url = team.get('url')
        if not url:
            return details
        
        try:
            # The page should already be loaded from schedule scraping
            # Look for location/address information in the page content
            page_content = await page.content()
            
            # Try to extract location from common patterns on TotalGlobalSports
            # Look for address elements
            address_elem = await page.query_selector('.club-address, .team-address, .address, [class*="address"]')
            if address_elem:
                address_text = await address_elem.inner_text()
                if address_text:
                    details['street_address'] = address_text.strip()
            
            # Look for city/state elements
            location_elem = await page.query_selector('.club-location, .team-location, .location, [class*="city"]')
            if location_elem:
                location_text = await location_elem.inner_text()
                if location_text:
                    # Parse city, state from location text
                    import re
                    state_match = re.search(r',\s*([A-Za-z\s]+)\s*(\d{5})?', location_text)
                    if state_match:
                        state_city = state_match.group(1).strip()
                        # Common US state names
                        us_states = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 
                                    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 
                                    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 
                                    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 
                                    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 
                                    'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 
                                    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 
                                    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 
                                    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 
                                    'West Virginia', 'Wisconsin', 'Wyoming']
                        for state in us_states:
                            if state.lower() in state_city.lower():
                                details['state'] = state
                                city_part = location_text.split(',')[0].strip()
                                if city_part:
                                    details['city'] = city_part
                                break
            
            # Look for zip code
            zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', page_content)
            if zip_match:
                details['zip_code'] = zip_match.group(1)
            
            # Look for website link
            website_elem = await page.query_selector('a[href*="http"]:not([href*="totalglobalsports"]):not([href*="gotsport"])')
            if website_elem:
                href = await website_elem.get_attribute('href')
                if href and 'http' in href:
                    details['official_website'] = href
            
            # Try to get details from meta tags or structured data
            meta_elems = await page.query_selector_all('meta[property*="address"], meta[name*="address"]')
            for meta in meta_elems:
                content = await meta.get_attribute('content')
                if content:
                    details['street_address'] = content
            
        except Exception as e:
            if self.debug:
                print(f"    Team details error: {e}")
        
        return details

    async def scrape_team_schedule(self, page, team: Dict) -> List[Dict]:
        """Scrape games from a team's schedule page"""
        games = []
        url = team.get('url')
        if not url:
            return games
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(2)
            
            game_rows = await page.query_selector_all('tr')
            
            for row in game_rows:
                try:
                    row_text = await row.inner_text()
                    
                    date_match = re.search(r'(\w{3}\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})', row_text)
                    if not date_match:
                        continue
                    date_str = date_match.group(1)
                    
                    team_links = await row.query_selector_all('a')
                    team_names = []
                    for link in team_links:
                        href = await link.get_attribute('href') or ''
                        if 'team' in href.lower() or 'club' in href.lower():
                            name = await link.inner_text()
                            name = name.strip()
                            if name and len(name) > 2:
                                team_names.append(name)
                    
                    if len(team_names) < 2:
                        continue
                    
                    home_team = team_names[0]
                    away_team = team_names[1]
                    
                    score_match = re.search(r'(\d+)\s*[-–:]\s*(\d+)', row_text)
                    home_score = int(score_match.group(1)) if score_match else None
                    away_score = int(score_match.group(2)) if score_match else None
                    
                    age_group = standardize_age_group(team.get('age_group', ''), team.get('gender', 'Girls'))
                    league = team.get('league', 'ECNL')
                    
                    game = {
                        'game_id': make_game_id(date_str, home_team, away_team, league, age_group),
                        'game_date': date_str,
                        'game_date_iso': normalize_date_to_iso(date_str),
                        'game_time': None,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score,
                        'league': league,
                        'age_group': age_group,
                        'conference': team.get('conference', ''),
                        'location': None,
                        'game_status': 'completed' if home_score is not None else 'scheduled',
                        'source_url': url,
                        'gender': team.get('gender', 'Girls')
                    }
                    games.append(game)
                    
                except Exception as e:
                    if self.debug:
                        print(f"    Row parse error: {e}")
                    continue
            
        except Exception as e:
            if self.debug:
                print(f"    Page error: {e}")
            self.errors += 1
        
        return games

    async def scrape_team_roster(self, page, team: Dict) -> List[Dict]:
        """Scrape player roster from team page"""
        players = []
        url = team.get('url')
        if not url:
            return players
        
        try:
            roster_rows = await page.query_selector_all('table tr, .roster-item, .player-row')
            
            for row in roster_rows:
                try:
                    row_text = await row.inner_text()
                    
                    if 'name' in row_text.lower() and 'number' in row_text.lower():
                        continue
                    
                    cells = await row.query_selector_all('td, .cell')
                    if len(cells) < 2:
                        continue
                    
                    player = {
                        'player_name': '',
                        'jersey_number': '',
                        'position': '',
                        'graduation_year': '',
                        'age_group': team.get('age_group'),
                        'league': team.get('league')
                    }
                    
                    for i, cell in enumerate(cells):
                        text = (await cell.inner_text()).strip()
                        if i == 0 and text.isdigit():
                            player['jersey_number'] = text
                        elif i <= 1 and not text.isdigit() and len(text) > 2:
                            player['player_name'] = text
                        elif text in ['GK', 'D', 'M', 'F', 'MF', 'FW', 'DF']:
                            player['position'] = text
                        elif re.match(r'^20\d{2}$', text):
                            player['graduation_year'] = text
                    
                    if player['player_name']:
                        players.append(player)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            if self.debug:
                print(f"    Roster error: {e}")
        
        return players

    async def scrape_teams(self, teams: List[Dict]) -> Tuple[int, int]:
        """Scrape games for a list of teams"""
        total_new, total_upd = 0, 0
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            print(f"\n📥 Scraping {len(teams)} teams...")
            
            for i, team in enumerate(teams, 1):
                team_name = team.get('team_name', 'Unknown')
                league = team.get('league', 'ECNL')
                age = team.get('age_group', '')
                
                print(f"[{i}/{len(teams)}] {team_name} ({league} {age})", end=" ", flush=True)
                
                try:
                    games = await self.scrape_team_schedule(page, team)
                    
                    if games:
                        n, u = save_games(self.db_path, games, self.days_filter)
                        total_new += n
                        total_upd += u
                        self.all_games.extend(games)
                        print(f"✓ {len(games)} games ({n} new)")
                        update_status(self.db_path, team.get('url'), 'completed')
                        
                        # Scrape and save team details (city, state, address, website)
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
                        }
                        save_team(self.db_path, team_data)
                        
                        # Scrape players if requested
                        if self.include_players:
                            players = await self.scrape_team_roster(page, team)
                            if players:
                                saved = save_players(self.db_path, players, team.get('url', ''), team_name)
                                if self.debug:
                                    print(f"    💼 {saved} players saved")
                    else:
                        print("- No games")
                        update_status(self.db_path, team.get('url'), 'no_games')
                        
                        # Still save team data even if no games
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
                        }
                        save_team(self.db_path, team_data)
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"❌ {e}")
                    self.errors += 1
                    update_status(self.db_path, team.get('url'), 'error')
            
            await browser.close()
        
        return total_new, total_upd

    def show_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        print("\n" + "="*60)
        print("📊 ECNL DATABASE STATISTICS")
        print("="*60)
        
        for league in ['ECNL', 'ECNL RL']:
            cur.execute("SELECT COUNT(*) FROM games WHERE league=?", (league,))
            print(f"\n{league} games: {cur.fetchone()[0]:,}")
            cur.execute("SELECT age_group, COUNT(*) FROM games WHERE league=? GROUP BY age_group ORDER BY age_group", (league,))
            for r in cur.fetchall():
                print(f"  {r[0]}: {r[1]:,}")
        
        print("\n" + "-"*40)
        cur.execute("SELECT league, scrape_status, COUNT(*) FROM discovered_urls WHERE league IN ('ECNL','ECNL RL') GROUP BY league, scrape_status")
        print("URL status:")
        for r in cur.fetchall():
            print(f"  {r[0]} - {r[1] or 'pending'}: {r[2]}")
        
        conn.close()

    def cleanup_data(self):
        """Clean corrupted data from database"""
        print("\n🧹 Cleaning corrupted data...")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        invalid_patterns = [
            "Regional League%", "TBD%", "vs%", "ECNL%", 
            "\\d{1,2}:\\d{2}", "\\d{1,2}/\\d{1,2}/\\d{4}"
        ]
        
        deleted = 0
        for pattern in invalid_patterns:
            cur.execute(f"DELETE FROM games WHERE home_team LIKE ? OR away_team LIKE ?", (pattern, pattern))
            deleted += cur.rowcount
        
        cur.execute("""
            UPDATE games SET home_team = REPLACE(home_team, 'Regional League', '')
            WHERE home_team LIKE 'Regional League%'
        """)
        cur.execute("""
            UPDATE games SET away_team = REPLACE(away_team, 'Regional League', '')
            WHERE away_team LIKE 'Regional League%'
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ Removed {deleted} invalid records")


async def main_async():
    parser = argparse.ArgumentParser(description='ECNL Scraper v65 - Admin UI Compatible')
    
    # Original arguments
    parser.add_argument('--db', help='Database path')
    parser.add_argument('--discover', action='store_true', help='Discover team URLs')
    parser.add_argument('--scrape', action='store_true', help='Scrape pending teams')
    parser.add_argument('--scrape-all', action='store_true', help='Scrape all teams')
    parser.add_argument('--league', choices=['ECNL', 'ECNL RL'], help='Specific league')
    parser.add_argument('--age', help='Age group filter (single)')
    parser.add_argument('--limit', type=int, help='Limit teams')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--cleanup', action='store_true', help='Clean corrupted data')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--headed', action='store_true', help='Show browser')
    
    # Admin UI arguments
    parser.add_argument('--gender', choices=['girls', 'boys', 'both'], default='both', 
                       help='Filter by gender')
    parser.add_argument('--ages', help='Comma-separated age groups (e.g., 13,12,11)')
    parser.add_argument('--days', type=int, help='Only games from last N days')
    parser.add_argument('--players', action='store_true', help='Include player scraping')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    db = args.db or DATABASE_PATH
    print("\n" + "="*60)
    print("🏃 ECNL COMPREHENSIVE SCRAPER v67")
    print("="*60)
    print(f"📂 Database: {db}")
    
    if args.gender:
        print(f"👤 Gender: {args.gender}")
    if args.ages:
        print(f"📅 Age groups: {args.ages}")
    if args.days:
        print(f"📆 Days filter: last {args.days} days")
    if args.players:
        print(f"👥 Including players: Yes")
    
    if not os.path.exists(db):
        print(f"❌ Database not found: {db}")
        sys.exit(1)
    
    debug = args.debug or args.verbose
    scraper = ECNLScraper(db, headless=not args.headed, debug=debug,
                          include_players=args.players, days_filter=args.days)
    
    if args.stats:
        scraper.show_stats()
        return
    
    if args.cleanup:
        scraper.cleanup_data()
        return
    
    # Determine if we should scrape
    should_scrape = args.scrape or args.scrape_all or args.no_confirm or args.ages or args.gender
    
    if should_scrape:
        # Parse age filter
        age_list = parse_age_filter(args.ages) if args.ages else None
        
        teams = get_teams_from_db(db, args.league, args.age, 
                                  pending_only=not args.scrape_all,
                                  limit=args.limit,
                                  gender=args.gender,
                                  age_list=age_list)
        
        if not teams:
            print("\n⚠️ No teams to scrape")
            scraper.show_stats()
            return
        
        print(f"\n📋 {len(teams)} teams to scrape")
        
        # Skip prompt if --no-confirm
        if not args.no_confirm:
            try:
                input("Press Enter to start...")
            except EOFError:
                pass
        
        new_cnt, upd_cnt = await scraper.scrape_teams(teams)
        
        if scraper.all_games:
            csv_path = export_csv(scraper.all_games, OUTPUT_DIR, 'ECNL')
            print(f"\n📄 CSV: {csv_path}")
        
        print("\n" + "="*60)
        print("✅ COMPLETE")
        print(f"   Teams: {len(teams)}, New: {new_cnt}, Updated: {upd_cnt}, Errors: {scraper.errors}")
        scraper.show_stats()
    else:
        # Interactive menu
        print("\n📋 OPTIONS:")
        print("  1. Show statistics")
        print("  2. Scrape pending teams")
        print("  3. Scrape all teams")
        print("  4. Cleanup corrupted data")
        print("  5. Exit")
        
        try:
            choice = input("\nSelect option: ").strip()
        except EOFError:
            return
        
        if choice == '1':
            scraper.show_stats()
        elif choice == '2':
            teams = get_teams_from_db(db, args.league, args.age, True, args.limit)
            if teams:
                new_cnt, upd_cnt = await scraper.scrape_teams(teams)
                if scraper.all_games:
                    export_csv(scraper.all_games, OUTPUT_DIR, 'ECNL')
                scraper.show_stats()
        elif choice == '3':
            teams = get_teams_from_db(db, args.league, args.age, False, args.limit)
            if teams:
                new_cnt, upd_cnt = await scraper.scrape_teams(teams)
                if scraper.all_games:
                    export_csv(scraper.all_games, OUTPUT_DIR, 'ECNL')
                scraper.show_stats()
        elif choice == '4':
            scraper.cleanup_data()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
