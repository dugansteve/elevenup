#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GIRLS ACADEMY SCRAPER v13 - ADMIN UI COMPATIBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

def make_canonical_game_id(date: str, team1: str, team2: str) -> str:
    """
    Create a canonical game ID that's the same regardless of home/away order.
    This allows us to detect and merge duplicate games.
    """
    t1_clean = re.sub(r'[^a-zA-Z0-9]', '_', team1.strip())[:35]
    t2_clean = re.sub(r'[^a-zA-Z0-9]', '_', team2.strip())[:35]
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
        Save games to database with smart merging.
        """
        if not games:
            return 0
        
        # Filter by days if specified
        if self.days_filter:
            cutoff_date = (datetime.now() - timedelta(days=self.days_filter)).strftime('%Y-%m-%d')
            games = [g for g in games if g.get('game_date', '') >= cutoff_date]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        merged = 0
        
        for game in games:
            try:
                cursor.execute("""
                    SELECT home_score, away_score, home_team, away_team
                    FROM games WHERE game_id = ?
                """, (game['game_id'],))
                
                existing = cursor.fetchone()
                
                if existing:
                    old_home, old_away, old_home_team, old_away_team = existing
                    new_home = game.get('home_score')
                    new_away = game.get('away_score')
                    
                    final_home = None
                    final_away = None
                    
                    if old_home is not None or old_away is not None:
                        if game['home_team'] == old_home_team:
                            final_home = new_home if new_home is not None else old_home
                            final_away = new_away if new_away is not None else old_away
                        else:
                            final_home = new_away if new_away is not None else old_home
                            final_away = new_home if new_home is not None else old_away
                    else:
                        final_home = new_home
                        final_away = new_away
                    
                    if (final_home is not None and old_home is None) or \
                       (final_away is not None and old_away is None) or \
                       (final_home is not None and final_away is not None and 
                        (old_home is None or old_away is None)):
                        
                        cursor.execute("""
                            UPDATE games SET 
                                home_score = COALESCE(?, home_score),
                                away_score = COALESCE(?, away_score),
                                game_status = CASE WHEN ? IS NOT NULL AND ? IS NOT NULL 
                                              THEN 'completed' ELSE game_status END,
                                scraped_at = ?
                            WHERE game_id = ?
                        """, (final_home, final_away, final_home, final_away,
                              game['scraped_at'], game['game_id']))
                        
                        if cursor.rowcount > 0:
                            merged += 1
                else:
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
    
    # =========================================================================
    # MAIN RUN METHOD
    # =========================================================================
    
    def run(self, age_group: str = "ALL", filter_type: str = "all", max_teams: int = None,
            age_list: List[str] = None):
        """Main scraping process"""
        print("\n" + "="*70)
        print("🏃 STARTING GA SCRAPER v13 - ADMIN UI COMPATIBLE")
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
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🎯 GA SCRAPER v13 - ADMIN UI COMPATIBLE")
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
