#!/usr/bin/env python3
"""
MLS NEXT League Scraper v1.0
============================
Comprehensive scraper for MLS NEXT league data from modular11.com and GotSport.

⚠️⚠️⚠️ CRITICAL: AGE GROUP FORMAT USES BIRTH YEAR ⚠️⚠️⚠️
=====================================================
ALL THESE PATTERNS ARE EQUIVALENT: 12G = G12 = 2012 = 2012G = birth year 2012

The number in team names and age groups is ALWAYS the birth year!
Current ages are NEVER in team names (except U-format).

| Pattern | Meaning          | Age Group | Players' Age in 2025 |
|---------|------------------|-----------|----------------------|
| G12     | Girls, Born 2012 | G12       | 13 years old         |
| B11     | Boys, Born 2011  | B11       | 14 years old         |
| 12G     | Born 2012, Girls | G12       | 13 years old         |
| 14F     | Born 2014, Female| G14       | 11 years old         |

Only U-format (U13, U11) means "under age X" where the number IS an age.

Formula: 12G → birth_year = 2012 → age_group = G12

THIS MISTAKE HAS BEEN MADE MULTIPLE TIMES - DO NOT REPEAT IT!
=====================================================

Features:
- Scrapes MLS NEXT league standings and schedules from modular11.com
- Scrapes MLS NEXT tournament games from GotSport
- Human-like behavior (delays, rotating user agents)
- Saves to seedlinedata.db (games, teams tables)
- CSV export for backup

MLS NEXT Structure:
- Age Groups: U13, U14, U15, U16, U17, U19
- Divisions: Florida, Frontier, Mid-America, Mid-Atlantic, Northeast, Northwest, Southeast, Southwest
- Two tiers: Allstate Homegrown Division, Academy Division

Platforms:
- modular11.com - Official MLS NEXT schedules/standings (Tournament ID: 12)
- system.gotsport.com - MLS NEXT tournaments (Dreams Cup, MLS NEXT Cup, etc.)

Author: Claude (with Steve)
Version: 1.0
"""

# Version constant for filename tracking
SCRAPER_VERSION = "v1"

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
    print(f"Missing dependency: {e}")
    print("Install with: pip install playwright beautifulsoup4 requests")
    print("Then run: playwright install chromium")
    sys.exit(1)


# =============================================================================
# STEALTH CONFIGURATION - Human-like behavior
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Delay ranges (in seconds)
MIN_DELAY = 2.0
MAX_DELAY = 5.0
MIN_COFFEE_BREAK = 30.0
MAX_COFFEE_BREAK = 60.0
COFFEE_BREAK_INTERVAL = (15, 20)
READING_PAUSE_CHANCE = 0.2

SCREENSHOT_TIMEOUT = 60000
TAKE_SCREENSHOTS = True


# =============================================================================
# MLS NEXT CONFIGURATION
# =============================================================================

@dataclass
class MLSNextDivision:
    """Configuration for an MLS NEXT division"""
    name: str
    region: str
    gender: str        # "Boys" or "Girls" or "Both"
    age_groups: List[str]  # ["U13", "U14", "U15", "U16", "U17", "U19"]
    modular11_id: Optional[int] = None
    gotsport_event_id: Optional[str] = None


# MLS NEXT Divisions (8 regions)
MLS_NEXT_DIVISIONS = [
    MLSNextDivision("MLS NEXT Florida", "Florida", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Frontier", "Frontier", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Mid-America", "Mid-America", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Mid-Atlantic", "Mid-Atlantic", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Northeast", "Northeast", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Northwest", "Northwest", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Southeast", "Southeast", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
    MLSNextDivision("MLS NEXT Southwest", "Southwest", "Boys",
                    ["U13", "U14", "U15", "U16", "U17", "U19"]),
]

# Known MLS NEXT GotSport tournament event IDs
# Format: (name, event_id, description)
MLS_NEXT_GOTSPORT_EVENTS = [
    ("Dreams Cup 2025", "40863", "Inter Miami CF hosted tournament"),
    # Add more events as discovered
]

# Age group mappings
AGE_GROUP_MAP = {
    "U13": "B12",  # Birth year 2012 = age 13 in 2025
    "U14": "B11",
    "U15": "B10",
    "U16": "B09",
    "U17": "B08",
    "U19": "B06",
}

def u_age_to_birth_year(u_age: str) -> str:
    """Convert U-age to birth year format (U14 -> B11 for 2025)"""
    current_year = 2025
    match = re.search(r'U(\d+)', u_age, re.I)
    if match:
        age = int(match.group(1))
        birth_year = current_year - age
        return str(birth_year)[-2:]  # "11" for 2011
    return u_age


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
# DATABASE FUNCTIONS
# =============================================================================

def find_database_path():
    """Find the seedlinedata.db database file"""
    script_dir = Path(__file__).parent.resolve()
    search_paths = [
        script_dir.parent.parent / "seedlinedata.db",
        script_dir.parent / "seedlinedata.db",
        script_dir / "seedlinedata.db",
        Path.cwd() / "seedlinedata.db",
        script_dir.parent / "scrapers and data" / "seedlinedata.db",
    ]

    for path in search_paths:
        if path.exists():
            return str(path)

    return None


def save_mls_next_game_to_db(db_path: str, game: Dict) -> bool:
    """Save MLS NEXT game to games table in database"""
    if not db_path:
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    game_id = game.get('game_id', '')
    if not game_id:
        # Generate game ID if not provided
        home = game.get('home_team', '')[:20]
        away = game.get('away_team', '')[:20]
        date = game.get('game_date', '')
        game_id = f"mlsnext_{date}_{home}_{away}".replace(' ', '_').lower()
        game_id = re.sub(r'[^a-z0-9_-]', '', game_id)

    # Check for existing game
    cur.execute("SELECT id FROM games WHERE game_id = ?", (game_id,))
    if cur.fetchone():
        conn.close()
        return False  # Already exists

    # Parse date - convert to YYYY-MM-DD format for consistency
    game_date = game.get('game_date', '')
    game_date_iso = ''
    if game_date:
        try:
            # Try multiple date formats including 2-digit year (MM/DD/YY)
            for fmt in ["%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y"]:
                try:
                    dt = datetime.strptime(game_date, fmt)
                    game_date_iso = dt.strftime("%Y-%m-%d")
                    break
                except:
                    continue
        except:
            pass

    # Use ISO format as the primary game_date for consistency with other scrapers
    if game_date_iso:
        game_date = game_date_iso

    # Get age group in standard format (B11, G14, etc.)
    # Convention: Gxx = birth year 20xx (G14 = born 2014, NOT age 14)
    age_group = game.get('age_group', '')
    if age_group.startswith('U'):
        birth_year_suffix = u_age_to_birth_year(age_group)  # U14 → "11" (born 2011)
        gender = game.get('gender', 'Boys')
        prefix = 'G' if gender.lower().startswith('g') else 'B'
        age_group = f"{prefix}{birth_year_suffix}"  # "B11"

    # Conference/region
    conference = game.get('region', game.get('conference', game.get('division', '')))

    cur.execute("""INSERT INTO games (game_id, game_date, game_date_iso, game_time, home_team, away_team,
                  home_score, away_score, league, age_group, conference, location, game_status, source_url, scraped_at, gender)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
               (game_id, game_date, game_date_iso, game.get('game_time'),
                game.get('home_team') or game.get('home_team_normalized'),
                game.get('away_team') or game.get('away_team_normalized'),
                game.get('home_score'), game.get('away_score'),
                'MLS NEXT', age_group, conference,
                game.get('location', ''), game.get('game_status', ''),
                game.get('source_url', ''), game.get('gender', 'Boys')))
    conn.commit()
    conn.close()
    return True


def save_mls_next_team_to_db(db_path: str, team: Dict) -> bool:
    """Save MLS NEXT team to teams table in database"""
    if not db_path:
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    team_url = team.get('schedule_url') or team.get('profile_url') or ''
    if not team_url:
        team_url = f"mlsnext_{team.get('team_name', 'unknown')}_{team.get('age_group', '')}".lower()
        team_url = re.sub(r'[^a-z0-9_-]', '', team_url)

    # Check existing
    cur.execute("SELECT id FROM teams WHERE team_url = ?", (team_url,))
    if cur.fetchone():
        conn.close()
        return False

    # Get age group in standard format (B11, G14, etc.)
    # Convention: Gxx = birth year 20xx (G14 = born 2014, NOT age 14)
    age_group = team.get('age_group', '')
    if age_group.startswith('U'):
        birth_year_suffix = u_age_to_birth_year(age_group)  # U14 → "11" (born 2011)
        gender = team.get('gender', 'Boys')
        prefix = 'G' if gender.lower().startswith('g') else 'B'
        age_group = f"{prefix}{birth_year_suffix}"  # "B11"

    gender = team.get('gender', 'Boys')
    state = team.get('state', '')
    city = team.get('city', '')

    cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference,
                  state, city, street_address, zip_code, official_website, team_id, scraped_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
               (team_url, team.get('club_name'), team.get('team_name'), age_group,
                gender, 'MLS NEXT', team.get('region'),
                state, city, team.get('street_address', ''), team.get('zip_code', ''),
                team.get('official_website', ''), team.get('team_id')))
    conn.commit()
    conn.close()
    return True


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_random_user_agent() -> str:
    """Get a random user agent from the pool."""
    return random.choice(USER_AGENTS)


def normalize_team_name(name: str) -> str:
    """Normalize team name for matching."""
    if not name:
        return ""

    normalized = name.lower().strip()

    # Remove common suffixes
    patterns = [
        r'\s+mls\s*next\s*$', r'\s+academy\s*$', r'\s+fc\s*$', r'\s+sc\s*$',
        r'\s+u\d{2}\s*$', r'\s+\d{4}\s*$',
    ]
    for pattern in patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.I)

    return re.sub(r'\s+', ' ', normalized).strip()


def extract_club_name(team_name: str) -> str:
    """Extract club name from full team name."""
    if not team_name:
        return ""

    club = team_name.strip()

    # Remove age patterns
    club = re.sub(r'\s+U\d{2}\b', '', club, flags=re.I)
    club = re.sub(r'\s+\d{4}\b', '', club)
    club = re.sub(r'\s+(B|G)\d{2}\b', '', club, flags=re.I)

    # Remove common suffixes
    club = re.sub(r'\s+(MLS NEXT|Academy|FC|SC)\s*$', '', club, flags=re.I)

    return club.strip()


def parse_score(score_str: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse score string to (home, away) tuple."""
    if not score_str:
        return None, None

    # Handle "3-1", "3 - 1", "3:1" formats
    match = re.match(r'(\d+)\s*[-:]\s*(\d+)', score_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2))

    # Handle PKS format: "2-2 PKS 5-4"
    pks_match = re.match(r'(\d+)\s*-\s*(\d+)\s+PKS\s+(\d+)\s*-\s*(\d+)', score_str.strip())
    if pks_match:
        return int(pks_match.group(1)), int(pks_match.group(2))

    return None, None


def determine_game_status(game_date: str, home_score: Optional[int], away_score: Optional[int]) -> str:
    """Determine if game is completed, scheduled, or unknown."""
    if home_score is not None and away_score is not None:
        return "completed"

    if game_date:
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
                try:
                    game_dt = datetime.strptime(game_date, fmt)
                    break
                except:
                    continue
            else:
                return "scheduled"

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if game_dt < today:
                return "unknown"  # Past game without score
            else:
                return "scheduled"
        except:
            pass

    return "scheduled"


def parse_time(time_str: str) -> Optional[str]:
    """Parse time string to HH:MM format."""
    if not time_str:
        return None

    # Handle AM/PM format
    am_pm_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.I)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minute = am_pm_match.group(2)
        meridiem = am_pm_match.group(3).upper()

        if meridiem == 'PM' and hour < 12:
            hour += 12
        elif meridiem == 'AM' and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute}"

    # Handle 24-hour format
    time_24_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if time_24_match:
        hour = int(time_24_match.group(1))
        minute = time_24_match.group(2)
        if 0 <= hour <= 23:
            return f"{hour:02d}:{minute}"

    return None


# =============================================================================
# DIAGNOSTIC LOGGER
# =============================================================================

class DiagnosticLogger:
    """Handles all diagnostic output."""

    def __init__(self, debug: bool = False, quiet: bool = False):
        self.debug = debug
        self.quiet = quiet
        self.start_time = datetime.now()
        self.errors: List[Dict] = []
        self.warnings: List[str] = []

    def header(self, text: str):
        if not self.quiet:
            print("\n" + "=" * 70)
            print(text)
            print("=" * 70)

    def subheader(self, text: str):
        if not self.quiet:
            print("\n" + "-" * 50)
            print(f"  {text}")
            print("-" * 50)

    def info(self, text: str):
        if not self.quiet:
            print(f"  {text}")

    def success(self, text: str):
        if not self.quiet:
            print(f"  [OK] {text}")

    def warning(self, text: str):
        self.warnings.append(text)
        if not self.quiet:
            print(f"  [WARN] {text}")

    def error(self, text: str, exception: Optional[Exception] = None):
        error_info = {'message': text, 'time': datetime.now().isoformat()}
        if exception:
            error_info['exception'] = str(exception)
        self.errors.append(error_info)

        if not self.quiet:
            print(f"  [ERROR] {text}")
            if self.debug and exception:
                traceback.print_exc()

    def debug_msg(self, text: str):
        if self.debug:
            print(f"  [DEBUG] {text}")

    def progress(self, current: int, total: int, item: str):
        if not self.quiet:
            pct = (current / total * 100) if total > 0 else 0
            print(f"\n  [{current}/{total}] ({pct:.0f}%) {item}")

    def stats(self, label: str, value):
        if not self.quiet:
            print(f"     {label}: {value}")

    def delay_message(self, seconds: float):
        if not self.quiet:
            print(f"  Waiting {seconds:.1f}s...")

    def summary(self, stats: Dict):
        duration = datetime.now() - self.start_time

        print("\n" + "=" * 70)
        print("SCRAPING SUMMARY - MLS NEXT")
        print("=" * 70)
        print(f"   Duration: {duration}")
        print(f"   Divisions scraped: {stats.get('divisions_scraped', 0)}")
        print(f"   Schedules processed: {stats.get('schedules_scraped', 0)}")
        print(f"   Games found: {stats.get('games_found', 0)}")
        print(f"   New games: {stats.get('games_new', 0)}")
        print(f"   Teams found: {stats.get('teams_found', 0)}")
        print(f"   Errors: {len(self.errors)}")
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
        if random.random() < READING_PAUSE_CHANCE:
            delay = random.uniform(max_sec, max_sec * 1.5)
        else:
            delay = random.uniform(min_sec, max_sec)

        self.logger.delay_message(delay)
        await asyncio.sleep(delay)

    async def maybe_coffee_break(self):
        self.request_count += 1

        if self.request_count >= self.next_break_at:
            break_time = random.uniform(MIN_COFFEE_BREAK, MAX_COFFEE_BREAK)
            self.logger.info(f"Taking a coffee break for {break_time:.1f}s...")
            await asyncio.sleep(break_time)

            self.request_count = 0
            self.next_break_at = random.randint(COFFEE_BREAK_INTERVAL[0], COFFEE_BREAK_INTERVAL[1])

    async def random_scroll(self, page: Page):
        try:
            await page.evaluate("""
                () => {
                    const scrollAmount = Math.random() * 500 + 200;
                    window.scrollBy({ top: scrollAmount, behavior: 'smooth' });
                }
            """)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except:
            pass


# =============================================================================
# CSV EXPORTER
# =============================================================================

class CSVExporter:
    """Handles CSV export with deduplication and database saving."""

    def __init__(self, output_dir: str, logger: DiagnosticLogger):
        self.output_dir = output_dir
        self.logger = logger
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.games_file = os.path.join(output_dir, f"mls_next_games_{SCRAPER_VERSION}_{timestamp}.csv")
        self.teams_file = os.path.join(output_dir, f"mls_next_teams_{SCRAPER_VERSION}_{timestamp}.csv")

        self.seen_game_ids: Set[str] = set()
        self.seen_team_keys: Set[str] = set()

        self.stats = {
            'games_written': 0,
            'games_skipped_duplicate': 0,
            'games_saved_to_db': 0,
            'teams_written': 0,
            'teams_saved_to_db': 0,
        }

        self.db_path = find_database_path()
        if self.db_path:
            self.logger.info(f"Database found: {self.db_path}")
        else:
            self.logger.warning("Database not found - games will only be saved to CSV")

        self._init_files()

    def _init_files(self):
        with open(self.games_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=GAMES_CSV_COLUMNS)
            writer.writeheader()

        with open(self.teams_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=TEAMS_CSV_COLUMNS)
            writer.writeheader()

        self.logger.info(f"Games CSV: {self.games_file}")
        self.logger.info(f"Teams CSV: {self.teams_file}")

    def write_game(self, game: Dict) -> bool:
        game_id = game.get('game_id', '')

        if game_id in self.seen_game_ids:
            self.stats['games_skipped_duplicate'] += 1
            return False

        self.seen_game_ids.add(game_id)

        row = {col: game.get(col, '') for col in GAMES_CSV_COLUMNS}
        row['scraped_at'] = datetime.now().isoformat()
        row['league'] = 'MLS NEXT'

        with open(self.games_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=GAMES_CSV_COLUMNS)
            writer.writerow(row)

        self.stats['games_written'] += 1

        if self.db_path:
            try:
                if save_mls_next_game_to_db(self.db_path, game):
                    self.stats['games_saved_to_db'] += 1
            except Exception as e:
                self.logger.debug_msg(f"Database game save error: {e}")

        return True

    def write_team(self, team: Dict) -> bool:
        team_key = f"{team.get('team_name', '')}_{team.get('age_group', '')}"

        if team_key in self.seen_team_keys:
            return False

        self.seen_team_keys.add(team_key)

        row = {col: team.get(col, '') for col in TEAMS_CSV_COLUMNS}
        row['discovered_at'] = datetime.now().isoformat()
        row['league'] = 'MLS NEXT'

        with open(self.teams_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=TEAMS_CSV_COLUMNS)
            writer.writerow(row)

        self.stats['teams_written'] += 1

        if self.db_path:
            try:
                if save_mls_next_team_to_db(self.db_path, team):
                    self.stats['teams_saved_to_db'] += 1
            except Exception as e:
                self.logger.debug_msg(f"Database team save error: {e}")

        return True


# =============================================================================
# MODULAR11 SCRAPER (Official MLS NEXT Platform)
# =============================================================================

class Modular11Scraper:
    """Scraper for modular11.com - official MLS NEXT platform.

    Uses the standings page which shows all games when down arrows are clicked.
    No login required for public standings data.
    """

    STANDINGS_URL = "https://www.modular11.com/standings"

    # Age group dropdown values (from the page HTML)
    AGE_GROUP_VALUES = {
        "U13": "21",
        "U14": "22",
        "U15": "33",
        "U16": "14",
        "U17": "15",
        "U19": "26",
    }

    # Gender dropdown values
    GENDER_VALUES = {
        "All": "0",
        "Male": "1",
        "Female": "2",
    }

    def __init__(self, csv_exporter: CSVExporter, logger: DiagnosticLogger,
                 human: HumanBehavior, take_screenshots: bool = True):
        self.csv = csv_exporter
        self.logger = logger
        self.human = human
        self.take_screenshots = take_screenshots

        self.stats = {
            'divisions_scraped': 0,
            'schedules_scraped': 0,
            'games_found': 0,
            'teams_found': 0,
            'errors': 0,
        }

    async def scrape_all(self, page: Page, gender: str = "Male",
                         age_groups: List[str] = None) -> Tuple[List[Dict], List[Dict]]:
        """Scrape all MLS NEXT data from modular11.com standings page"""
        all_games = []
        all_teams = []

        if age_groups is None:
            age_groups = ["U13", "U14", "U15", "U16", "U17", "U19"]

        self.logger.header("MLS NEXT - modular11.com Scraper")
        self.logger.info(f"Gender: {gender}")
        self.logger.info(f"Age Groups: {', '.join(age_groups)}")

        try:
            # Navigate to standings page
            self.logger.info("Loading standings page...")
            await page.goto(self.STANDINGS_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            # Scrape each age group
            for i, age_group in enumerate(age_groups, 1):
                self.logger.progress(i, len(age_groups), f"{gender} {age_group}")

                try:
                    games, teams = await self._scrape_age_group(page, gender, age_group)
                    all_games.extend(games)
                    all_teams.extend(teams)

                    for game in games:
                        self.csv.write_game(game)
                    for team in teams:
                        self.csv.write_team(team)

                    self.stats['schedules_scraped'] += 1
                    self.logger.stats("Games", len(games))
                    self.logger.stats("Teams", len(teams))

                except Exception as e:
                    self.logger.error(f"Error scraping {age_group}: {e}", e)
                    self.stats['errors'] += 1

                await self.human.delay(1, 2)

        except Exception as e:
            self.logger.error(f"Modular11 scraper error: {e}", e)
            self.stats['errors'] += 1

        self.stats['games_found'] = len(all_games)
        self.stats['teams_found'] = len(all_teams)

        return all_games, all_teams

    async def _scrape_age_group(self, page: Page, gender: str, age_group: str) -> Tuple[List[Dict], List[Dict]]:
        """Scrape games for a specific age group by:
        1. Selecting the age group from dropdown
        2. Clicking all down arrows to expand game data
        3. Parsing the game rows
        """
        games = []
        teams = []

        # Select gender from dropdown
        gender_value = self.GENDER_VALUES.get(gender, "1")
        try:
            gender_selector = await page.query_selector('select[js-tournament-type="gender"]')
            if gender_selector:
                await gender_selector.select_option(value=gender_value)
                await page.wait_for_timeout(1500)
                self.logger.debug_msg(f"Selected gender: {gender}")
        except Exception as e:
            self.logger.debug_msg(f"Gender selection error: {e}")

        # Select age group from dropdown
        age_value = self.AGE_GROUP_VALUES.get(age_group)
        if not age_value:
            self.logger.warning(f"Unknown age group: {age_group}")
            return games, teams

        try:
            age_selector = await page.query_selector('select[js-tournament-type="year"]')
            if age_selector:
                await age_selector.select_option(value=age_value)
                await page.wait_for_timeout(2000)
                self.logger.debug_msg(f"Selected age group: {age_group} (value={age_value})")
        except Exception as e:
            self.logger.debug_msg(f"Age group selection error: {e}")
            return games, teams

        # Wait for standings to load
        await page.wait_for_timeout(2000)

        # Click all down arrows to expand game data
        arrows = await page.query_selector_all('button.open-table')
        self.logger.info(f"Found {len(arrows)} teams to expand")

        for idx, arrow in enumerate(arrows):
            try:
                # Check if visible
                is_visible = await arrow.is_visible()
                if not is_visible:
                    continue

                # Click the arrow
                await arrow.click()

                # Small delay to let content load (games load via AJAX)
                if idx < 5:  # First few take longer
                    await page.wait_for_timeout(1500)
                else:
                    await page.wait_for_timeout(500)

            except Exception as e:
                self.logger.debug_msg(f"Arrow click error {idx}: {e}")

        # Wait for all game data to finish loading
        await page.wait_for_timeout(2000)

        # Parse the expanded game data
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Find all game rows (desktop version has full data)
        game_rows = soup.select('.table-content-row.hidden-xs')
        self.logger.debug_msg(f"Found {len(game_rows)} game rows")

        for row in game_rows:
            game = self._parse_modular11_game(row, gender, age_group)
            if game:
                games.append(game)

                # Extract teams
                for team_name in [game.get('home_team'), game.get('away_team')]:
                    if team_name:
                        teams.append({
                            'team_name': team_name,
                            'club_name': extract_club_name(team_name),
                            'age_group': age_group,
                            'gender': gender,
                            'league': 'MLS NEXT',
                            'region': game.get('division', ''),
                            'platform': 'modular11',
                        })

        # Deduplicate teams
        seen = set()
        unique_teams = []
        for t in teams:
            key = t.get('team_name', '')
            if key and key not in seen:
                seen.add(key)
                unique_teams.append(t)

        return games, unique_teams

    def _parse_modular11_game(self, row, gender: str, age_group: str) -> Optional[Dict]:
        """Parse a game row from modular11.com standings page.

        Row structure:
        - col-sm-1: Match ID + Gender
        - col-sm-2: Date/Time + Location
        - col-sm-1: Age (U13, U14, etc.)
        - col-sm-2: Competition + Division
        - col-sm-6: Home Team, Score, Away Team
        """
        try:
            cols = row.select('.col-sm-1, .col-sm-2, .col-sm-6')
            if len(cols) < 4:
                return None

            # Extract Match ID (first column)
            match_id_col = row.select_one('.col-sm-1')
            match_id = ''
            if match_id_col:
                match_text = match_id_col.get_text(strip=True)
                match_id_match = re.search(r'(\d+)', match_text)
                if match_id_match:
                    match_id = match_id_match.group(1)

            # Extract date/time and location (second column)
            details_col = row.select('.col-sm-2')
            date_str = ''
            time_str = ''
            location = ''
            if details_col:
                details_text = details_col[0].get_text(separator='\n', strip=True)
                lines = [l.strip() for l in details_text.split('\n') if l.strip()]

                # First line is usually date/time: "09/06/25 10:00am"
                if lines:
                    dt_match = re.match(r'(\d{2}/\d{2}/\d{2})\s*(\d{1,2}:\d{2}[ap]m)?', lines[0], re.I)
                    if dt_match:
                        date_str = dt_match.group(1)
                        time_str = dt_match.group(2) or ''

                # Location from container-location
                loc_elem = details_col[0].select_one('.container-location p')
                if loc_elem:
                    location = loc_elem.get('data-title', '') or loc_elem.get_text(strip=True)

            # Extract age from third column
            age_col = row.select('.col-sm-1')
            scraped_age = age_group
            if len(age_col) > 1:
                age_text = age_col[1].get_text(strip=True)
                if re.match(r'U\d{2}', age_text):
                    scraped_age = age_text

            # Extract competition and division
            division = ''
            competition = 'League'
            if len(details_col) > 1:
                comp_text = details_col[1].get_text(separator='\n', strip=True)
                lines = [l.strip() for l in comp_text.split('\n') if l.strip()]
                if lines:
                    competition = lines[0]
                if len(lines) > 1:
                    division = lines[1]

            # Extract teams and score (last column)
            teams_col = row.select_one('.col-sm-6')
            home_team = ''
            away_team = ''
            home_score = None
            away_score = None

            if teams_col:
                # Home team
                home_elem = teams_col.select_one('.container-first-team p')
                if home_elem:
                    home_team = home_elem.get('data-title', '') or home_elem.get_text(strip=True)

                # Away team
                away_elem = teams_col.select_one('.container-second-team p')
                if away_elem:
                    away_team = away_elem.get('data-title', '') or away_elem.get_text(strip=True)

                # Score
                score_elem = teams_col.select_one('.score-match-table')
                if score_elem:
                    score_text = score_elem.get_text(strip=True)
                    # Handle "4 : 0" format with &nbsp;
                    score_text = score_text.replace('\xa0', ' ').replace('&nbsp;', ' ')
                    score_match = re.search(r'(\d+)\s*:\s*(\d+)', score_text)
                    if score_match:
                        home_score = int(score_match.group(1))
                        away_score = int(score_match.group(2))

            # Skip if no teams
            if not home_team or not away_team:
                return None

            # Build game ID
            game_id = f"mlsnext_{match_id}_{home_team[:15]}_{away_team[:15]}_{date_str}".lower()
            game_id = re.sub(r'[^a-z0-9_-]', '', game_id)[:100]

            return {
                'game_id': game_id,
                'external_game_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'home_team_normalized': normalize_team_name(home_team),
                'away_team_normalized': normalize_team_name(away_team),
                'home_score': home_score,
                'away_score': away_score,
                'game_date': date_str,
                'game_time': time_str,
                'game_status': determine_game_status(date_str, home_score, away_score),
                'gender': gender,
                'age_group': scraped_age,
                'division': division,
                'league': 'MLS NEXT',
                'platform': 'modular11',
                'source_url': self.STANDINGS_URL,
                'location': location,
            }

        except Exception as e:
            return None

    def _parse_game_element(self, elem, gender: str, age_group: str) -> Optional[Dict]:
        """Legacy parse method - kept for compatibility"""
        try:
            text = elem.get_text(separator=' ', strip=True)

            # Skip header rows or empty
            if not text or 'home' in text.lower() and 'away' in text.lower():
                return None

            # Try to extract teams and score
            # Common patterns: "Team A 3 - 1 Team B" or "Team A vs Team B"

            # Look for score pattern
            score_match = re.search(r'(\d+)\s*[-:]\s*(\d+)', text)
            home_score = None
            away_score = None
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))

            # Try to find team names
            cells = elem.find_all(['td', 'span', 'div'])
            team_names = []
            date_str = ''
            time_str = ''
            location = ''

            for cell in cells:
                cell_text = cell.get_text(strip=True)

                # Check for date
                if re.search(r'\d{1,2}/\d{1,2}|\w{3}\s+\d{1,2}', cell_text):
                    date_str = cell_text
                # Check for time
                elif re.search(r'\d{1,2}:\d{2}', cell_text):
                    time_str = cell_text
                # Check for team (has letters, not just numbers)
                elif re.search(r'[A-Za-z]{3,}', cell_text) and len(cell_text) < 100:
                    if cell_text not in ['vs', 'at', 'Home', 'Away', '-']:
                        team_names.append(cell_text)

            if len(team_names) >= 2:
                home_team = team_names[0]
                away_team = team_names[1]

                game_id = f"mlsnext_{gender}_{age_group}_{home_team}_{away_team}_{date_str}".lower()
                game_id = re.sub(r'[^a-z0-9_-]', '', game_id)[:100]

                return {
                    'game_id': game_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_team_normalized': normalize_team_name(home_team),
                    'away_team_normalized': normalize_team_name(away_team),
                    'home_score': home_score,
                    'away_score': away_score,
                    'game_date': date_str,
                    'game_time': parse_time(time_str),
                    'game_status': determine_game_status(date_str, home_score, away_score),
                    'gender': gender,
                    'age_group': age_group,
                    'league': 'MLS NEXT',
                    'platform': 'modular11',
                    'source_url': self.SCHEDULE_URL,
                    'location': location,
                }

        except Exception as e:
            self.logger.debug_msg(f"Game parse error: {e}")

        return None


# =============================================================================
# GOTSPORT SCRAPER (for MLS NEXT tournaments)
# =============================================================================

class GotSportMLSNextScraper:
    """Scraper for MLS NEXT events on GotSport platform."""

    BASE_URL = "https://system.gotsport.com"

    def __init__(self, csv_exporter: CSVExporter, logger: DiagnosticLogger,
                 human: HumanBehavior, take_screenshots: bool = True):
        self.csv = csv_exporter
        self.logger = logger
        self.human = human
        self.take_screenshots = take_screenshots

        self.stats = {
            'events_scraped': 0,
            'games_found': 0,
            'teams_found': 0,
            'errors': 0,
        }

    async def scrape_event(self, page: Page, event_id: str, event_name: str = "") -> Tuple[List[Dict], List[Dict]]:
        """Scrape games from a GotSport MLS NEXT event"""
        games = []
        teams = []

        event_url = f"{self.BASE_URL}/org_event/events/{event_id}"

        self.logger.header(f"MLS NEXT Tournament: {event_name or event_id}")
        self.logger.info(f"URL: {event_url}")

        try:
            await page.goto(event_url, timeout=60000)
            await self.human.delay(3, 5)
            await self.human.random_scroll(page)

            # Find all schedule/division links
            sections = await self._find_schedule_sections(page)
            self.logger.info(f"Found {len(sections)} schedule sections")

            for i, section in enumerate(sections, 1):
                section_name = section.get('name', f'Section {i}')
                section_url = section.get('url')

                self.logger.progress(i, len(sections), section_name)

                try:
                    section_games, section_teams = await self._scrape_section(
                        page, section_url, section_name, event_id
                    )
                    games.extend(section_games)
                    teams.extend(section_teams)

                    for game in section_games:
                        self.csv.write_game(game)
                    for team in section_teams:
                        self.csv.write_team(team)

                    self.logger.stats("Games", len(section_games))

                except Exception as e:
                    self.logger.error(f"Section error: {e}", e)
                    self.stats['errors'] += 1

                await self.human.delay()
                await self.human.maybe_coffee_break()

            self.stats['events_scraped'] += 1

        except Exception as e:
            self.logger.error(f"Event scrape error: {e}", e)
            self.stats['errors'] += 1

        self.stats['games_found'] += len(games)
        self.stats['teams_found'] += len(teams)

        return games, teams

    async def _find_schedule_sections(self, page: Page) -> List[Dict]:
        """Find all schedule/division links on the event page."""
        sections = []

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Look for age/gender schedule links
        schedule_links = soup.find_all('a', href=re.compile(r'schedules\?.*age=\d+.*gender=[mf]', re.I))

        for link in schedule_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if href:
                full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                sections.append({'name': text or "Schedule", 'url': full_url})

        # Also look for division/bracket links
        division_links = soup.find_all('a', href=re.compile(r'schedules\?.*group=', re.I))
        for link in division_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if href and text:
                full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                if not any(s['url'] == full_url for s in sections):
                    sections.append({'name': text, 'url': full_url})

        return sections

    async def _scrape_section(self, page: Page, url: str, section_name: str,
                               event_id: str) -> Tuple[List[Dict], List[Dict]]:
        """Scrape games from a schedule section"""
        games = []
        teams = []

        if url:
            await page.goto(url, timeout=60000)
            await self.human.delay(2, 3)

        # Try to click "All" or expand all games
        try:
            all_button = await page.query_selector('button:has-text("All"), a:has-text("All")')
            if all_button:
                await all_button.click()
                await self.human.delay(2, 3)
        except:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Extract age/gender from section name or URL
        age_match = re.search(r'U(\d{2})', section_name)
        age_group = f"U{age_match.group(1)}" if age_match else ""
        gender = "Girls" if re.search(r'\b(girl|female|f)\b', section_name, re.I) else "Boys"

        # Find game rows in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                game = self._parse_gotsport_row(row, age_group, gender, event_id, url)
                if game:
                    games.append(game)

                    for team_name in [game.get('home_team'), game.get('away_team')]:
                        if team_name and team_name.lower() != 'bye':
                            teams.append({
                                'team_name': team_name,
                                'club_name': extract_club_name(team_name),
                                'age_group': age_group,
                                'gender': gender,
                                'league': 'MLS NEXT',
                                'platform': 'gotsport',
                            })

        # Deduplicate teams
        seen = set()
        unique_teams = []
        for t in teams:
            key = t.get('team_name', '')
            if key and key not in seen:
                seen.add(key)
                unique_teams.append(t)

        return games, unique_teams

    def _parse_gotsport_row(self, row, age_group: str, gender: str,
                             event_id: str, source_url: str) -> Optional[Dict]:
        """Parse a game row from GotSport table"""
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                return None

            text = row.get_text(separator=' ', strip=True).lower()
            if 'bye' in text or 'home' in text and 'away' in text:
                return None

            # Try to extract data from cells
            home_team = ''
            away_team = ''
            score = ''
            date_str = ''
            time_str = ''
            location = ''
            match_num = ''

            for cell in cells:
                cell_text = cell.get_text(strip=True)
                cell_class = ' '.join(cell.get('class', []))

                # Match number
                if re.match(r'^#?\d+$', cell_text):
                    match_num = cell_text
                # Date
                elif re.search(r'\d{1,2}/\d{1,2}|[A-Z][a-z]{2}\s+\d{1,2}', cell_text):
                    date_str = cell_text
                # Time
                elif re.search(r'\d{1,2}:\d{2}\s*(AM|PM)?', cell_text, re.I):
                    time_str = cell_text
                # Score
                elif re.match(r'^\d+\s*[-:]\s*\d+', cell_text):
                    score = cell_text
                # Team names
                elif len(cell_text) > 3 and re.search(r'[A-Za-z]', cell_text):
                    if 'home' in cell_class.lower() or not home_team:
                        home_team = cell_text
                    else:
                        away_team = cell_text

            if not home_team or not away_team:
                return None

            home_score, away_score = parse_score(score)

            game_id = f"gotsport_{event_id}_{match_num or home_team[:10]}_{away_team[:10]}_{date_str}".lower()
            game_id = re.sub(r'[^a-z0-9_-]', '', game_id)[:100]

            return {
                'game_id': game_id,
                'external_game_id': match_num,
                'home_team': home_team,
                'away_team': away_team,
                'home_team_normalized': normalize_team_name(home_team),
                'away_team_normalized': normalize_team_name(away_team),
                'home_score': home_score,
                'away_score': away_score,
                'game_date': date_str,
                'game_time': parse_time(time_str),
                'game_status': determine_game_status(date_str, home_score, away_score),
                'gender': gender,
                'age_group': age_group,
                'league': 'MLS NEXT',
                'platform': 'gotsport',
                'source_url': source_url,
                'location': location,
            }

        except Exception as e:
            return None


# =============================================================================
# MAIN SCRAPER CLASS
# =============================================================================

class MLSNextScraper:
    """Main orchestrator for MLS NEXT scraping."""

    def __init__(self, output_dir: str = None, debug: bool = False,
                 take_screenshots: bool = True):
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "output")
        self.debug = debug
        self.take_screenshots = take_screenshots

        self.logger = DiagnosticLogger(debug=debug)
        self.csv = CSVExporter(self.output_dir, self.logger)
        self.human = HumanBehavior(self.logger)

        self.modular11 = Modular11Scraper(self.csv, self.logger, self.human, take_screenshots)
        self.gotsport = GotSportMLSNextScraper(self.csv, self.logger, self.human, take_screenshots)

    async def run(self, source: str = "all", gender: str = "Male",
                  age_groups: List[str] = None, event_ids: List[str] = None):
        """Run the scraper."""

        self.logger.header("MLS NEXT SCRAPER v1.0")
        self.logger.info(f"Source: {source}")
        self.logger.info(f"Gender: {gender}")
        self.logger.info(f"Output: {self.output_dir}")

        all_games = []
        all_teams = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080},
            )
            page = await context.new_page()

            try:
                # Scrape modular11.com (official MLS NEXT)
                if source in ["all", "modular11"]:
                    games, teams = await self.modular11.scrape_all(page, gender, age_groups)
                    all_games.extend(games)
                    all_teams.extend(teams)

                # Scrape GotSport tournaments
                if source in ["all", "gotsport"] and event_ids:
                    for event_id in event_ids:
                        event_name = next(
                            (e[0] for e in MLS_NEXT_GOTSPORT_EVENTS if e[1] == event_id),
                            f"Event {event_id}"
                        )
                        games, teams = await self.gotsport.scrape_event(page, event_id, event_name)
                        all_games.extend(games)
                        all_teams.extend(teams)

            finally:
                await browser.close()

        # Print summary
        stats = {
            'divisions_scraped': self.modular11.stats.get('divisions_scraped', 0),
            'schedules_scraped': self.modular11.stats.get('schedules_scraped', 0) +
                                 self.gotsport.stats.get('events_scraped', 0),
            'games_found': len(all_games),
            'games_new': self.csv.stats.get('games_saved_to_db', 0),
            'teams_found': len(all_teams),
        }
        self.logger.summary(stats)

        return all_games, all_teams


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="MLS NEXT League Scraper v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mls_next_scraper_v1.py
  python mls_next_scraper_v1.py --source modular11 --gender Male
  python mls_next_scraper_v1.py --source gotsport --events 40863
  python mls_next_scraper_v1.py --ages U15,U16,U17
        """
    )

    parser.add_argument('--source', choices=['all', 'modular11', 'gotsport'],
                        default='all', help='Data source (default: all)')
    parser.add_argument('--gender', choices=['Male', 'Female', 'Both'],
                        default='Male', help='Gender to scrape (default: Male)')
    parser.add_argument('--ages', type=str, default='U13,U14,U15,U16,U17,U19',
                        help='Age groups (comma-separated, default: U13,U14,U15,U16,U17,U19)')
    parser.add_argument('--events', type=str, default='',
                        help='GotSport event IDs to scrape (comma-separated)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output directory for CSV files')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--no-screenshots', action='store_true',
                        help='Disable screenshots')

    args = parser.parse_args()

    age_groups = [a.strip() for a in args.ages.split(',')]
    event_ids = [e.strip() for e in args.events.split(',') if e.strip()]

    # Default to Dreams Cup if no events specified for gotsport
    if args.source in ['all', 'gotsport'] and not event_ids:
        event_ids = ['40863']  # Dreams Cup 2025

    scraper = MLSNextScraper(
        output_dir=args.output,
        debug=args.debug,
        take_screenshots=not args.no_screenshots,
    )

    asyncio.run(scraper.run(
        source=args.source,
        gender=args.gender,
        age_groups=age_groups,
        event_ids=event_ids,
    ))


if __name__ == "__main__":
    main()
