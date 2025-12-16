#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GIRLS ACADEMY EVENTS SCRAPER v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scrapes GA REGIONAL and NATIONAL events (showcases, playoffs, regionals, etc.)
Separate from the main league scraper (GA_scraper_v13.py).

FEATURES:
  ✅ AUTO-DISCOVERS event IDs from girlsacademyleague.com
  ✅ TRACKS event dates and schedules in JSON config
  ✅ SCRAPES games from discovered events
  ✅ ADDS event_type column (SHOWCASE, REGIONAL, PLAYOFFS, FINALS, CHAMPIONS_CUP, TALENT_ID)
  ✅ MATCHES teams by name across events (same team = same canonical ID)
  ✅ REMINDS user to run discovery when needed
  ✅ ADMIN UI INTEGRATION - --no-confirm flag for automated runs
  ✅ KNOWN EVENT IDS - can add events by ID directly

GA EVENTS CALENDAR (2024-25):
  National Events:
    - Winter Showcase & Champions Cup (December) - U13-U19
    - Champions Cup Finals (March) - U13-U19
    - Spring Showcase (April) - U15-U19
    - Summer Playoffs & Showcase (June) - U13-U19
    - GA Finals (July) - U13-U17
    
  Regional Events:
    - East Regional (November) - U12-U14
    - West Regional (March) - U12-U14
    
  Talent ID Events (various dates):
    - Northwest, Northeast, Mid-Atlantic North/South, Southwest, Mid-America, National

USAGE:
  python GA_events_scraper_v2.py                    # Interactive menu
  python GA_events_scraper_v2.py --discover         # Discover new events
  python GA_events_scraper_v2.py --scrape           # Scrape all active events
  python GA_events_scraper_v2.py --scrape-all       # Scrape ALL discovered events
  python GA_events_scraper_v2.py --scrape-event 47820  # Scrape specific event
  python GA_events_scraper_v2.py --add-event 47820  # Add event by ID
  python GA_events_scraper_v2.py --status           # Show event status
  python GA_events_scraper_v2.py --no-confirm       # Skip prompts (for admin UI)
  python GA_events_scraper_v2.py --db path/to/db    # Specify database

LOCATION: Seedline_App/scrapers/
DATABASE: Auto-detected or specified with --db
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

# === CONFIGURATION ===========================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Config file location - check multiple locations in priority order:
# 1. Seedline_Data folder (sibling to Seedline_App) - preferred for persistence
# 2. Current script directory (scrapers folder) - legacy/standalone
# 3. Parent directory (Seedline_App folder)
def find_config_file():
    """Find config file, preferring Seedline_Data folder for persistence"""
    possible_paths = [
        # Seedline_Data folder (recommended - persists across updates)
        os.path.join(SCRIPT_DIR, "..", "..", "Seedline_Data", "ga_events_config.json"),
        # Current directory (scrapers folder)
        os.path.join(SCRIPT_DIR, "ga_events_config.json"),
        # Parent directory (Seedline_App folder)
        os.path.join(SCRIPT_DIR, "..", "ga_events_config.json"),
    ]
    
    # Check for existing config
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    # Return Seedline_Data path for new configs (will create folder if needed)
    data_folder = os.path.join(SCRIPT_DIR, "..", "..", "Seedline_Data")
    if not os.path.exists(data_folder):
        try:
            os.makedirs(data_folder, exist_ok=True)
        except:
            pass  # Fall back to script dir if can't create
        return os.path.join(data_folder, "ga_events_config.json")
    return possible_paths[0]

CONFIG_FILE = find_config_file()
DEFAULT_DB_PATH = os.path.join(SCRIPT_DIR, "..", "seedlinedata.db")

# GA Website URLs
GA_EVENTS_URL = "https://girlsacademyleague.com/events/"
GOTSPORT_BASE = "https://system.gotsport.com"

# Event type patterns (for classifying events)
EVENT_TYPE_PATTERNS = {
    'CHAMPIONS_CUP': ['champions cup', 'champions-cup', 'championscup'],
    'SHOWCASE': ['showcase', 'winter showcase', 'spring showcase', 'summer showcase'],
    'PLAYOFFS': ['playoff', 'playoffs'],
    'FINALS': ['finals', 'final', 'ga finals', 'national finals'],
    'REGIONAL': ['regional', 'east regional', 'west regional'],
    'TALENT_ID': ['talent id', 'talent-id', 'talentid', 'tid'],
}

# Known GA Event IDs for 2024-25 Season
# These can be used as fallback or to manually add events
KNOWN_EVENTS_2024_25 = {
    # Main League (NOT scraped by this script - use GA_scraper_v13.py)
    # '42137': {'name': 'GA League 2024-25', 'type': 'LEAGUE'},
    
    # Winter Events (December 2024)
    '47820': {'name': 'Winter Showcase & Champions Cup 2024-25', 'type': 'CHAMPIONS_CUP', 
              'start': '2024-12-05', 'end': '2024-12-09'},
    
    # Regional Events
    '47750': {'name': 'East Regional 2024-25', 'type': 'REGIONAL',
              'start': '2024-11-07', 'end': '2024-11-09'},
    
    # Champions Cup Finals (March 2025)
    '37249': {'name': 'Champions Cup Finals 2024-25', 'type': 'FINALS',
              'start': '2025-03-06', 'end': '2025-03-11'},
    
    # Summer Events (June 2025)
    '37251': {'name': 'Summer Showcase & Playoffs 2024-25', 'type': 'PLAYOFFS',
              'start': '2025-06-19', 'end': '2025-06-24'},
}

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

MIN_DELAY = 2.0
MAX_DELAY = 5.0

# Age group conversion (U-format to G-format for ranker)
U_TO_G_MAPPING = {
    'U12': 'G14', 'U13': 'G13', 'U14': 'G12', 'U15': 'G11', 
    'U16': 'G10', 'U17': 'G09', 'U18': 'G08', 'U19': 'G08/07',
}


# === UTILITY FUNCTIONS =======================================================

def find_all_databases() -> List[str]:
    """Find all seedlinedata.db files in common locations"""
    found = []
    search_paths = [
        SCRIPT_DIR,
        os.path.join(SCRIPT_DIR, ".."),
        os.path.join(SCRIPT_DIR, "..", ".."),
        os.path.join(SCRIPT_DIR, "..", "..", ".."),
    ]
    
    for base in search_paths:
        db_path = os.path.join(base, "seedlinedata.db")
        if os.path.exists(db_path):
            abs_path = os.path.abspath(db_path)
            if abs_path not in found:
                found.append(abs_path)
    
    return found


def get_db_path(explicit_path: str = None) -> str:
    """Find the database path"""
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path
    
    found = find_all_databases()
    
    if not found:
        print(f"📁 No existing database found. Will create: {DEFAULT_DB_PATH}")
        return DEFAULT_DB_PATH
    
    if len(found) == 1:
        return found[0]
    
    # Multiple found - use first
    print(f"⚠️  Multiple databases found, using: {found[0]}")
    return found[0]


def convert_age_group(age_str: str, team_name: str = "") -> str:
    """Convert U-format to G-format age group"""
    if not age_str:
        return extract_age_from_team_name(team_name)
    
    # Already in G-format
    if age_str.startswith('G'):
        return age_str
    
    # Direct mapping
    if age_str in U_TO_G_MAPPING:
        return U_TO_G_MAPPING[age_str]
    
    # Try to extract from string
    match = re.search(r'U?(\d+)', age_str)
    if match:
        age_num = int(match.group(1))
        if age_num <= 19:
            u_format = f"U{age_num}"
            if u_format in U_TO_G_MAPPING:
                return U_TO_G_MAPPING[u_format]
    
    return extract_age_from_team_name(team_name) or age_str


def extract_age_from_team_name(team_name: str) -> Optional[str]:
    """
    Extract G-format age from team name like 'TopHat 13G GA' or 'Lamorinda SC 08/07G'
    
    IMPORTANT: Check combined patterns (08/07G) BEFORE single patterns (08G)
    to avoid incorrect matches!
    """
    if not team_name:
        return None
    
    # Pattern 1: Combined age groups like 08/07G (CHECK FIRST!)
    match = re.search(r'(\d{2})/(\d{2})G', team_name)
    if match:
        return f"G{match.group(1)}/{match.group(2)}"
    
    # Pattern 2: Combined G-format like G08/07
    match = re.search(r'G(\d{2})/(\d{2})', team_name)
    if match:
        return f"G{match.group(1)}/{match.group(2)}"
    
    # Pattern 3: Single birth year with G like 08G, 09G, 10G, 11G, 12G, 13G
    # Use word boundary to avoid matching part of combined pattern
    match = re.search(r'(?<!/)\b(\d{2})G\b', team_name)
    if match:
        return f"G{match.group(1)}"
    
    # Pattern 4: Full birth year like 2008, 2009, 2010
    match = re.search(r'\b20(\d{2})\b', team_name)
    if match:
        return f"G{match.group(1)}"
    
    # Pattern 5: Already in G-format like G08, G09
    match = re.search(r'\bG(\d{2})\b', team_name)
    if match:
        return f"G{match.group(1)}"
    
    return None


def make_canonical_game_id(date: str, team1: str, team2: str, event_type: str = "") -> str:
    """Create a canonical game ID"""
    t1_clean = re.sub(r'[^a-zA-Z0-9]', '_', team1.strip())[:35]
    t2_clean = re.sub(r'[^a-zA-Z0-9]', '_', team2.strip())[:35]
    teams_sorted = sorted([t1_clean, t2_clean])
    
    prefix = "ga_event" if event_type else "ga"
    return f"{prefix}_{date}_{teams_sorted[0]}_{teams_sorted[1]}"


def normalize_team_name(name: str) -> str:
    """Normalize team name for matching across events"""
    if not name:
        return ""
    
    # Remove common suffixes
    normalized = name.strip()
    normalized = re.sub(r'\s+(GA|Girls Academy|Academy)$', '', normalized, flags=re.I)
    normalized = re.sub(r'\s+\d{2}G$', '', normalized)  # Remove "13G" suffix
    normalized = re.sub(r'\s+20\d{2}$', '', normalized)  # Remove "2013" suffix
    normalized = re.sub(r'\s+U\d{2}$', '', normalized, flags=re.I)  # Remove "U13" suffix
    
    return normalized.strip()


# === EVENT CONFIG MANAGER ====================================================

class EventConfigManager:
    """Manages the events configuration file"""
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load config from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default config
        return {
            "last_discovery": None,
            "events": {},
            "team_mapping": {},  # canonical_name -> {event_id -> team_id}
        }
    
    def save_config(self):
        """Save config to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2, default=str)
    
    def add_event(self, event_id: str, event_info: Dict):
        """Add or update an event"""
        self.config["events"][event_id] = event_info
        self.save_config()
    
    def remove_event(self, event_id: str):
        """Remove an event"""
        if event_id in self.config.get("events", {}):
            del self.config["events"][event_id]
            self.save_config()
    
    def get_events(self) -> Dict:
        """Get all events"""
        return self.config.get("events", {})
    
    def get_active_events(self) -> Dict:
        """Get events that should be scraped (within 2 weeks of start or ongoing)"""
        now = datetime.now()
        active = {}
        
        for event_id, info in self.config.get("events", {}).items():
            try:
                start_date = datetime.strptime(info.get("start_date", ""), "%Y-%m-%d")
                end_date = datetime.strptime(info.get("end_date", ""), "%Y-%m-%d")
                
                # Active if: within 2 weeks before start OR currently happening OR ended within last week
                days_until_start = (start_date - now).days
                days_since_end = (now - end_date).days
                
                if days_until_start <= 14 or (days_until_start < 0 and days_since_end <= 7):
                    active[event_id] = info
                    
            except (ValueError, TypeError):
                # If dates invalid, include it anyway
                active[event_id] = info
        
        return active
    
    def needs_discovery(self) -> bool:
        """Check if discovery should be run"""
        last_discovery = self.config.get("last_discovery")
        if not last_discovery:
            return True
        
        try:
            last_dt = datetime.fromisoformat(last_discovery)
            days_since = (datetime.now() - last_dt).days
            return days_since >= 7  # Run discovery weekly
        except:
            return True
    
    def update_team_mapping(self, canonical_name: str, event_id: str, team_id: str):
        """Map a team across events"""
        if "team_mapping" not in self.config:
            self.config["team_mapping"] = {}
        
        if canonical_name not in self.config["team_mapping"]:
            self.config["team_mapping"][canonical_name] = {}
        
        self.config["team_mapping"][canonical_name][event_id] = team_id
        self.save_config()
    
    def get_team_id_for_event(self, canonical_name: str, event_id: str) -> Optional[str]:
        """Get team_id for a canonical team name in a specific event"""
        mapping = self.config.get("team_mapping", {})
        return mapping.get(canonical_name, {}).get(event_id)


# === EVENT DISCOVERY =========================================================

class GAEventDiscovery:
    """Discovers GA events from the official website"""
    
    def __init__(self, config_manager: EventConfigManager):
        self.config = config_manager
        self.session = requests.Session()
        self.update_headers()
    
    def update_headers(self):
        """Update session headers"""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
    
    def add_known_events(self) -> int:
        """Add known events from the hardcoded list"""
        added = 0
        existing = self.config.get_events()
        
        for event_id, info in KNOWN_EVENTS_2024_25.items():
            if event_id not in existing:
                event_info = {
                    "event_id": event_id,
                    "name": info['name'],
                    "event_type": info['type'],
                    "source_url": f"{GOTSPORT_BASE}/org_event/events/{event_id}",
                    "gotsport_url": f"{GOTSPORT_BASE}/org_event/events/{event_id}",
                    "start_date": info.get('start'),
                    "end_date": info.get('end'),
                    "discovered_at": datetime.now().isoformat(),
                    "last_scraped": None,
                    "groups": [],
                }
                self.config.add_event(event_id, event_info)
                added += 1
                print(f"   ✅ Added known event {event_id}: {info['name']}")
        
        return added
    
    def add_event_by_id(self, event_id: str) -> bool:
        """Add a single event by its GotSport ID"""
        print(f"\n🔍 Looking up event {event_id}...")
        
        url = f"{GOTSPORT_BASE}/org_event/events/{event_id}"
        
        try:
            self.update_headers()
            time.sleep(1)
            
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"   ❌ HTTP {resp.status_code} - Event not found")
                return False
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract event name
            title_elem = soup.find('div', class_='widget-title')
            event_name = title_elem.get_text(strip=True) if title_elem else f"Event {event_id}"
            
            # Try to classify
            event_type = self._classify_event(event_name, event_name, url)
            
            # Try to extract dates
            dates = self._extract_dates_from_page(soup, event_name)
            
            event_info = {
                "event_id": event_id,
                "name": event_name,
                "event_type": event_type,
                "source_url": url,
                "gotsport_url": url,
                "start_date": dates.get("start"),
                "end_date": dates.get("end"),
                "discovered_at": datetime.now().isoformat(),
                "last_scraped": None,
                "groups": [],
            }
            
            self.config.add_event(event_id, event_info)
            print(f"   ✅ Added event {event_id}: {event_name} ({event_type})")
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def discover_events(self) -> Dict[str, Dict]:
        """Discover events from GA website"""
        print("\n" + "="*70)
        print("🔍 DISCOVERING GA EVENTS")
        print("="*70)
        
        discovered = {}
        
        # First, add any known events not yet in config
        print("\n📋 Checking known events...")
        added_known = self.add_known_events()
        print(f"   Added {added_known} known events")
        
        # Event pages to check (comprehensive list for 2024-25)
        event_pages = [
            # Main events page
            ("https://girlsacademyleague.com/events/", "Main Events"),
            
            # National Events
            ("https://girlsacademyleague.com/winter-showcase/", "Winter Showcase"),
            ("https://girlsacademyleague.com/champions-cup/", "Champions Cup"),
            ("https://girlsacademyleague.com/champions-cup-finals/", "Champions Cup Finals"),
            ("https://girlsacademyleague.com/spring-showcase/", "Spring Showcase"),
            ("https://girlsacademyleague.com/playoffs-summer-showcase/", "Summer Playoffs"),
            ("https://girlsacademyleague.com/summer-showcase/", "Summer Showcase"),
            ("https://girlsacademyleague.com/national-finals/", "GA Finals"),
            ("https://girlsacademyleague.com/ga-finals/", "GA Finals Alt"),
            
            # Regional Events
            ("https://girlsacademyleague.com/regional-east/", "East Regional"),
            ("https://girlsacademyleague.com/regional-east-2024/", "East Regional 2024"),
            ("https://girlsacademyleague.com/regional-east-2025/", "East Regional 2025"),
            ("https://girlsacademyleague.com/u13-14-west-regional/", "West Regional"),
            ("https://girlsacademyleague.com/regional-west/", "West Regional Alt"),
            ("https://girlsacademyleague.com/regional-west-2025/", "West Regional 2025"),
            
            # Talent ID Events
            ("https://girlsacademyleague.com/talent-id/", "Talent ID"),
            ("https://girlsacademyleague.com/northwest-talent-id/", "NW Talent ID"),
            ("https://girlsacademyleague.com/northeast-talent-id/", "NE Talent ID"),
            ("https://girlsacademyleague.com/mid-atlantic-talent-id/", "Mid-Atlantic Talent ID"),
            ("https://girlsacademyleague.com/southwest-talent-id/", "SW Talent ID"),
            ("https://girlsacademyleague.com/mid-america-talent-id/", "Mid-America Talent ID"),
            ("https://girlsacademyleague.com/national-talent-id/", "National Talent ID"),
        ]
        
        print("\n📄 Scanning GA website for events...")
        
        for url, name in event_pages:
            print(f"\n   Checking: {name}...", end=" ", flush=True)
            time.sleep(random.uniform(1, 2))
            
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200:
                    print(f"HTTP {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find GotSport event links
                gotsport_links = soup.find_all('a', href=re.compile(r'gotsport\.com.*events/(\d+)'))
                
                found_on_page = 0
                for link in gotsport_links:
                    href = link.get('href', '')
                    match = re.search(r'events/(\d+)', href)
                    if match:
                        event_id = match.group(1)
                        
                        # Skip league events
                        if event_id in ['42137', '42138', '46969', '36330']:
                            continue
                        
                        if event_id not in discovered and event_id not in self.config.get_events():
                            # Get link text for event name hints
                            link_text = link.get_text(strip=True) or ""
                            
                            # Try to determine event type
                            event_type = self._classify_event(name, link_text, href)
                            
                            # Try to extract dates from surrounding content
                            dates = self._extract_dates_from_page(soup, name)
                            
                            discovered[event_id] = {
                                "event_id": event_id,
                                "name": name,
                                "event_type": event_type,
                                "source_url": url,
                                "gotsport_url": f"{GOTSPORT_BASE}/org_event/events/{event_id}",
                                "start_date": dates.get("start"),
                                "end_date": dates.get("end"),
                                "discovered_at": datetime.now().isoformat(),
                                "last_scraped": None,
                                "groups": [],
                            }
                            
                            found_on_page += 1
                
                if found_on_page > 0:
                    print(f"found {found_on_page} new event(s)")
                else:
                    print("no new events")
            
            except Exception as e:
                print(f"error: {e}")
        
        # Update config
        for event_id, info in discovered.items():
            existing = self.config.get_events().get(event_id, {})
            # Merge with existing info
            merged = {**existing, **info}
            self.config.add_event(event_id, merged)
        
        self.config.config["last_discovery"] = datetime.now().isoformat()
        self.config.save_config()
        
        total_events = len(self.config.get_events())
        print(f"\n✅ Discovery complete! {len(discovered)} new events found.")
        print(f"   Total events in config: {total_events}")
        return discovered
    
    def _classify_event(self, page_name: str, link_text: str, url: str) -> str:
        """Classify event type based on context"""
        combined = f"{page_name} {link_text} {url}".lower()
        
        # Check patterns in priority order
        priority_order = ['TALENT_ID', 'FINALS', 'PLAYOFFS', 'CHAMPIONS_CUP', 'REGIONAL', 'SHOWCASE']
        
        for event_type in priority_order:
            patterns = EVENT_TYPE_PATTERNS.get(event_type, [])
            for pattern in patterns:
                if pattern in combined:
                    return event_type
        
        return "SHOWCASE"  # Default
    
    def _extract_dates_from_page(self, soup: BeautifulSoup, event_name: str) -> Dict:
        """Try to extract event dates from page content"""
        dates = {"start": None, "end": None}
        
        # Look for date patterns in the page
        text = soup.get_text()
        
        # Pattern: "December 4-9, 2025" or "Dec. 4 - Dec. 9, 2025"
        date_patterns = [
            r'(\w+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s*(\d{4})',  # Dec 4-9, 2025
            r'(\w+)\s+(\d{1,2})\s*[-–]\s*(\w+)\s+(\d{1,2}),?\s*(\d{4})',  # Dec 4 - Dec 9, 2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 4:
                        month, start_day, end_day, year = groups
                        month_num = self._month_to_num(month)
                        if month_num:
                            dates["start"] = f"{year}-{month_num:02d}-{int(start_day):02d}"
                            dates["end"] = f"{year}-{month_num:02d}-{int(end_day):02d}"
                            break
                except:
                    pass
        
        return dates
    
    def _month_to_num(self, month_str: str) -> Optional[int]:
        """Convert month name to number"""
        months = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
            'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
            'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
            'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
            'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        return months.get(month_str.lower().rstrip('.'))


# === EVENT SCRAPER ===========================================================

class GAEventScraper:
    """Scrapes games from GA events"""
    
    def __init__(self, db_path: str, config_manager: EventConfigManager, debug: bool = False):
        self.db_path = db_path
        self.config = config_manager
        self.debug = debug
        self.session = requests.Session()
        self.update_headers()
        
        self.games_scraped = 0
        self.teams_discovered = 0
        self.errors = []
        
        # Ensure database has event_type column
        self._ensure_db_schema()
    
    def update_headers(self):
        """Update session headers"""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://system.gotsport.com/",
        })
    
    def _ensure_db_schema(self):
        """Ensure database has required columns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if games table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        if not cursor.fetchone():
            # Create games table
            cursor.execute("""
                CREATE TABLE games (
                    game_id TEXT PRIMARY KEY,
                    age_group TEXT,
                    game_date TEXT,
                    game_time TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    home_score INTEGER,
                    away_score INTEGER,
                    conference TEXT,
                    location TEXT,
                    scraped_at TEXT,
                    source_url TEXT,
                    game_status TEXT,
                    league TEXT,
                    event_type TEXT
                )
            """)
            print("✅ Created games table")
        else:
            # Check for event_type column
            cursor.execute("PRAGMA table_info(games)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'event_type' not in columns:
                cursor.execute("ALTER TABLE games ADD COLUMN event_type TEXT")
                print("✅ Added event_type column to games table")
        
        conn.commit()
        conn.close()
    
    def rate_limit(self):
        """Rate limiting"""
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
    
    def scrape_event(self, event_id: str, event_info: Dict = None) -> int:
        """Scrape all games from an event"""
        print(f"\n" + "="*70)
        print(f"🎯 SCRAPING EVENT {event_id}")
        if event_info:
            print(f"   {event_info.get('name', 'Unknown')} - {event_info.get('event_type', 'Unknown')}")
        print("="*70)
        
        # First, get the event main page to find all groups/divisions
        event_url = f"{GOTSPORT_BASE}/org_event/events/{event_id}"
        
        try:
            self.update_headers()
            resp = self.session.get(event_url, timeout=20)
            
            if resp.status_code != 200:
                print(f"❌ HTTP {resp.status_code} for event page")
                return 0
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract event name from page
            title_elem = soup.find('div', class_='widget-title')
            event_name = title_elem.get_text(strip=True) if title_elem else f"Event {event_id}"
            print(f"📋 Event: {event_name}")
            
            # Find all group/division schedule links
            # Pattern: /org_event/events/{event_id}/schedules?group={group_id}
            group_links = soup.find_all('a', href=re.compile(rf'events/{event_id}/schedules\?group=\d+'))
            
            groups = []
            for link in group_links:
                href = link.get('href', '')
                match = re.search(r'group=(\d+)', href)
                if match:
                    group_id = match.group(1)
                    
                    # Get division name from surrounding context
                    parent = link.find_parent('div', class_='row')
                    div_name = ""
                    if parent:
                        b_tag = parent.find('b')
                        if b_tag:
                            div_name = b_tag.get_text(strip=True)
                    
                    # Also try link text
                    if not div_name:
                        div_name = link.get_text(strip=True)
                    
                    if group_id not in [g['group_id'] for g in groups]:
                        groups.append({
                            'group_id': group_id,
                            'division_name': div_name,
                            'url': f"{GOTSPORT_BASE}{href}" if href.startswith('/') else href
                        })
            
            print(f"📊 Found {len(groups)} divisions/groups")
            
            if not groups:
                # Try alternative: scrape by age group
                print("   Trying age-based scraping...")
                for age in [12, 13, 14, 15, 16, 17, 19]:
                    groups.append({
                        'group_id': f"age_{age}",
                        'division_name': f"U{age}",
                        'url': f"{GOTSPORT_BASE}/org_event/events/{event_id}/schedules?age={age}&gender=f"
                    })
            
            # Update config with discovered groups
            if event_info:
                event_info['groups'] = groups
                self.config.add_event(event_id, event_info)
            
            # Scrape each group
            all_games = []
            for i, group in enumerate(groups, 1):
                print(f"\n[{i}/{len(groups)}] {group['division_name']} (group {group['group_id']})")
                
                self.rate_limit()
                games = self._scrape_group(group['url'], event_id, event_info, group['division_name'])
                
                if games:
                    print(f"   ✅ Found {len(games)} games")
                    all_games.extend(games)
                else:
                    print(f"   ℹ️ No games found")
            
            # Save to database
            if all_games:
                saved = self._save_games(all_games)
                print(f"\n💾 Saved {saved} games to database")
                
                # Update last scraped time
                if event_info:
                    event_info['last_scraped'] = datetime.now().isoformat()
                    self.config.add_event(event_id, event_info)
                
                return saved
            
            return 0
            
        except Exception as e:
            print(f"❌ Error scraping event: {e}")
            self.errors.append(str(e))
            return 0
    
    def _scrape_group(self, url: str, event_id: str, event_info: Dict, division_name: str) -> List[Dict]:
        """Scrape games from a single group/division"""
        games = []
        
        try:
            self.update_headers()
            resp = self.session.get(url, timeout=20)
            
            if resp.status_code != 200:
                return games
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find schedule table
            tables = soup.find_all('table')
            
            for table in tables:
                header_row = table.find('tr')
                if not header_row:
                    continue
                
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                # Check if this is a schedule table
                is_schedule = any(h in headers for h in ['Match #', 'Home Team', 'Home', 'Away Team', 'Away', 'Time', 'Date'])
                
                if is_schedule or 'Match' in str(headers):
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows:
                        game = self._parse_game_row(row, event_id, event_info, division_name)
                        if game:
                            games.append(game)
                            
                            # Track team discovery
                            self._track_team(game['home_team'], event_id, game.get('home_team_id'))
                            self._track_team(game['away_team'], event_id, game.get('away_team_id'))
            
            return games
            
        except Exception as e:
            if self.debug:
                print(f"   ❌ Error: {e}")
            return games
    
    def _parse_game_row(self, row, event_id: str, event_info: Dict, division_name: str) -> Optional[Dict]:
        """Parse a single game row"""
        try:
            cells = row.find_all(['td', 'th'])
            
            if not cells or len(cells) < 5:
                return None
            
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            # Skip header rows
            if cell_texts[0] == 'Match #' or ('Match' in cell_texts[0] and '#' in cell_texts[0]):
                return None
            
            game_data = {}
            
            # Column 0: Match ID
            game_data['match_id'] = cell_texts[0] if len(cell_texts) > 0 else None
            
            # Column 1: Date and Time
            if len(cell_texts) > 1 and cell_texts[1]:
                date_time_str = cell_texts[1]
                
                # Parse date
                date_match = re.search(r'([A-Za-z]+ \d{1,2}, \d{4})', date_time_str)
                if date_match:
                    date_str = date_match.group(1)
                    for fmt in ["%b %d, %Y", "%B %d, %Y"]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            game_data['game_date'] = dt.strftime("%Y-%m-%d")
                            break
                        except:
                            continue
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
                
                # Parse time
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)', date_time_str, re.I)
                game_data['game_time'] = time_match.group(1).strip() if time_match else ""
            else:
                return None
            
            # Column 2: Home Team
            home_cell = cells[2] if len(cells) > 2 else None
            game_data['home_team'] = cell_texts[2] if len(cell_texts) > 2 else None
            
            # Extract team ID from link
            if home_cell:
                home_link = home_cell.find('a', href=re.compile(r'team=(\d+)'))
                if home_link:
                    match = re.search(r'team=(\d+)', home_link.get('href', ''))
                    if match:
                        game_data['home_team_id'] = match.group(1)
            
            # Column 4: Away Team (sometimes column 3 is score)
            away_idx = 4
            if len(cell_texts) > 4:
                # Check if column 3 looks like a score
                if re.match(r'^[\d\s\-–—]+$', cell_texts[3]):
                    away_idx = 4
                else:
                    away_idx = 4
            
            away_cell = cells[away_idx] if len(cells) > away_idx else None
            game_data['away_team'] = cell_texts[away_idx] if len(cell_texts) > away_idx else None
            
            # Check if away_team looks like a score and adjust
            if game_data['away_team'] and re.match(r'^[\d\s\-–—]+$', game_data['away_team']):
                away_idx += 1
                away_cell = cells[away_idx] if len(cells) > away_idx else None
                game_data['away_team'] = cell_texts[away_idx] if len(cell_texts) > away_idx else None
            
            # Extract away team ID
            if away_cell:
                away_link = away_cell.find('a', href=re.compile(r'team=(\d+)'))
                if away_link:
                    match = re.search(r'team=(\d+)', away_link.get('href', ''))
                    if match:
                        game_data['away_team_id'] = match.group(1)
            
            # Validate teams
            if not game_data.get('home_team') or not game_data.get('away_team'):
                return None
            
            # Extract scores
            home_score, away_score = self._extract_scores(cells, cell_texts)
            game_data['home_score'] = home_score
            game_data['away_score'] = away_score
            game_data['game_status'] = 'completed' if home_score is not None and away_score is not None else 'scheduled'
            
            # Location
            for i in [5, 6, 7]:
                if len(cell_texts) > i and cell_texts[i]:
                    if not re.match(r'^[\d\s\-–—WLT]+$', cell_texts[i]):
                        game_data['location'] = cell_texts[i]
                        break
            else:
                game_data['location'] = ""
            
            # Age group - extract from team name (preferred) or division name
            # Pass game_date to correctly calculate birth year from U-age
            age_group = self._extract_age_group(division_name, game_data['home_team'], game_data.get('game_date'))
            game_data['age_group'] = age_group
            
            # Event type
            event_type = event_info.get('event_type', 'SHOWCASE') if event_info else 'SHOWCASE'
            game_data['event_type'] = event_type
            
            # Conference = division name
            game_data['conference'] = division_name
            
            # Generate game ID
            game_data['game_id'] = make_canonical_game_id(
                game_data['game_date'],
                game_data['home_team'],
                game_data['away_team'],
                event_type
            )
            
            # Metadata
            game_data['league'] = 'GA'
            game_data['event_id'] = event_id
            game_data['scraped_at'] = datetime.now().isoformat()
            
            return game_data
            
        except Exception as e:
            if self.debug:
                print(f"      ❌ Parse error: {e}")
            return None
    
    def _extract_scores(self, cells: List, cell_texts: List) -> Tuple[Optional[int], Optional[int]]:
        """Extract scores from row"""
        home_score = None
        away_score = None
        
        # Method 1: Look for "X-Y" pattern
        for text in cell_texts:
            score_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                return home_score, away_score
        
        # Method 2: Check cell at position 3
        if len(cell_texts) > 3 and cell_texts[3]:
            text = cell_texts[3].strip()
            score_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                return home_score, away_score
        
        # Method 3: Adjacent cells with just numbers
        for i in range(len(cell_texts) - 1):
            if re.match(r'^\d+$', cell_texts[i].strip()) and re.match(r'^\d+$', cell_texts[i+1].strip()):
                home_score = int(cell_texts[i])
                away_score = int(cell_texts[i+1])
                return home_score, away_score
        
        return home_score, away_score
    
    def _extract_age_group(self, division_name: str, team_name: str, event_date: str = None) -> str:
        """Extract age group from team name or division name.
        
        Priority:
        1. Team name birth year (most reliable - e.g. "Lamorinda SC 08G" → G08)
        2. Division U-age converted to birth year based on event date
        """
        # ALWAYS try team name first - it has the actual birth year
        team_age = extract_age_from_team_name(team_name)
        if team_age:
            return team_age
        
        # Fall back to division name, converting U-age to birth year
        if division_name:
            match = re.search(r'U(\d+)', division_name, re.I)
            if match:
                u_age = int(match.group(1))
                # Calculate birth year based on event date
                birth_year = self._calculate_birth_year(u_age, event_date)
                if birth_year:
                    return f"G{birth_year:02d}"
        
        return "Unknown"
    
    def _calculate_birth_year(self, u_age: int, event_date: str = None) -> Optional[int]:
        """Calculate birth year from U-age and event date.
        
        The soccer season runs Aug-Jul. U-age is based on age at start of season.
        - U13 in 2024-25 season = birth year 2012
        - U13 in 2025-26 season = birth year 2013
        
        Formula: birth_year = season_start_year - u_age + 1
        """
        from datetime import datetime
        
        try:
            if event_date:
                # Parse event date to determine season
                if isinstance(event_date, str):
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d']:
                        try:
                            dt = datetime.strptime(event_date.split()[0], fmt)
                            break
                        except:
                            continue
                    else:
                        dt = datetime.now()
                else:
                    dt = event_date
                
                # Determine season start year (Aug-Dec = current year, Jan-Jul = previous year)
                if dt.month >= 8:
                    season_year = dt.year
                else:
                    season_year = dt.year - 1
            else:
                # Default to current season
                now = datetime.now()
                if now.month >= 8:
                    season_year = now.year
                else:
                    season_year = now.year - 1
            
            # Calculate birth year: U13 in 2024 season = born 2012
            birth_year = season_year - u_age + 1
            return birth_year % 100  # Return just last 2 digits (e.g., 12 for 2012)
            
        except Exception as e:
            print(f"   ⚠️ Could not calculate birth year: {e}")
            return None
    
    def _track_team(self, team_name: str, event_id: str, team_id: str = None):
        """Track team for cross-event matching"""
        if not team_name or not team_id:
            return
        
        canonical = normalize_team_name(team_name)
        if canonical:
            self.config.update_team_mapping(canonical, event_id, team_id)
            self.teams_discovered += 1
    
    def _save_games(self, games: List[Dict]) -> int:
        """Save games to database"""
        if not games:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        
        for game in games:
            try:
                # Check if exists
                cursor.execute("SELECT game_id FROM games WHERE game_id = ?", (game['game_id'],))
                exists = cursor.fetchone()
                
                if exists:
                    # Update
                    cursor.execute("""
                        UPDATE games SET
                            home_score = COALESCE(?, home_score),
                            away_score = COALESCE(?, away_score),
                            game_status = ?,
                            event_type = ?,
                            scraped_at = ?
                        WHERE game_id = ?
                    """, (
                        game.get('home_score'),
                        game.get('away_score'),
                        game['game_status'],
                        game.get('event_type'),
                        game['scraped_at'],
                        game['game_id']
                    ))
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO games (
                            game_id, age_group, game_date, game_time,
                            home_team, away_team, home_score, away_score,
                            conference, location, scraped_at, source_url,
                            game_status, league, event_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        game['game_id'], game['age_group'], game['game_date'],
                        game.get('game_time', ''), game['home_team'], game['away_team'],
                        game.get('home_score'), game.get('away_score'),
                        game.get('conference', ''), game.get('location', ''),
                        game['scraped_at'], game.get('source_url', ''),
                        game['game_status'], game['league'],
                        game.get('event_type', '')
                    ))
                
                if cursor.rowcount > 0:
                    saved += 1
                    
            except Exception as e:
                if self.debug:
                    print(f"   ⚠️ DB error: {e}")
        
        conn.commit()
        conn.close()
        
        self.games_scraped += saved
        return saved


# === MAIN APPLICATION ========================================================

def show_status(config: EventConfigManager):
    """Show status of all events"""
    print("\n" + "="*70)
    print("📊 GA EVENTS STATUS")
    print("="*70)
    
    events = config.get_events()
    
    if not events:
        print("\n⚠️  No events discovered yet. Run with --discover first.")
        return
    
    now = datetime.now()
    
    print(f"\n{'Event ID':<10} {'Name':<30} {'Type':<15} {'Status':<12} {'Last Scraped':<15}")
    print("-" * 85)
    
    for event_id, info in sorted(events.items(), key=lambda x: x[1].get('start_date', '') or ''):
        name = info.get('name', 'Unknown')[:28]
        event_type = info.get('event_type', 'Unknown')[:13]
        
        # Determine status
        start_date = info.get('start_date')
        end_date = info.get('end_date')
        
        status = "Unknown"
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                
                if now < start:
                    days_until = (start - now).days
                    if days_until <= 14:
                        status = f"In {days_until}d ⏰"
                    else:
                        status = f"In {days_until}d"
                elif now <= end:
                    status = "🔴 ACTIVE"
                else:
                    status = "Completed"
            except:
                pass
        
        # Last scraped
        last_scraped = info.get('last_scraped')
        if last_scraped:
            try:
                last_dt = datetime.fromisoformat(last_scraped)
                hours_ago = (now - last_dt).total_seconds() / 3600
                if hours_ago < 24:
                    last_str = f"{hours_ago:.0f}h ago"
                else:
                    last_str = last_dt.strftime("%m/%d %H:%M")
            except:
                last_str = "Unknown"
        else:
            last_str = "Never"
        
        print(f"{event_id:<10} {name:<30} {event_type:<15} {status:<12} {last_str:<15}")
    
    print("\n")
    
    # Show reminder if discovery needed
    if config.needs_discovery():
        print("💡 TIP: Run --discover to check for new events (recommended weekly)")


def interactive_menu(config: EventConfigManager, db_path: str):
    """Interactive menu"""
    while True:
        print("\n" + "="*70)
        print("🏆 GA EVENTS SCRAPER v2.0 - Main Menu")
        print("="*70)
        
        # Show reminder if needed
        if config.needs_discovery():
            print("\n⚠️  REMINDER: Event discovery hasn't run recently.")
            print("   Consider running option 1 to check for new events.\n")
        
        print("  1. 🔍 Discover new events (checks GA website)")
        print("  2. 📊 Show event status")
        print("  3. 🎯 Scrape active events (within 2 weeks)")
        print("  4. 🎯 Scrape specific event")
        print("  5. 🚀 Scrape ALL events")
        print("  6. ➕ Add event by ID")
        print("  7. ❌ Exit")
        print()
        
        choice = input("Enter choice (1-7): ").strip()
        
        if choice == '1':
            discovery = GAEventDiscovery(config)
            discovery.discover_events()
            
        elif choice == '2':
            show_status(config)
            
        elif choice == '3':
            active = config.get_active_events()
            if not active:
                print("\n⚠️  No active events found. Run discovery first or check dates.")
                continue
            
            print(f"\n📋 Found {len(active)} active events:")
            for eid, info in active.items():
                print(f"   - {eid}: {info.get('name', 'Unknown')}")
            
            confirm = input("\nScrape these events? (y/n): ").strip().lower()
            if confirm == 'y':
                scraper = GAEventScraper(db_path, config)
                for event_id, event_info in active.items():
                    scraper.scrape_event(event_id, event_info)
                
                print(f"\n✅ Scraping complete! {scraper.games_scraped} total games saved.")
            
        elif choice == '4':
            events = config.get_events()
            if not events:
                print("\n⚠️  No events discovered yet. Run discovery first.")
                continue
            
            print("\nAvailable events:")
            for eid, info in events.items():
                print(f"   {eid}: {info.get('name', 'Unknown')}")
            
            event_id = input("\nEnter event ID to scrape: ").strip()
            if event_id in events:
                scraper = GAEventScraper(db_path, config)
                scraper.scrape_event(event_id, events[event_id])
                print(f"\n✅ Done! {scraper.games_scraped} games saved.")
            else:
                print(f"❌ Event {event_id} not found")
            
        elif choice == '5':
            events = config.get_events()
            if not events:
                print("\n⚠️  No events discovered yet. Run discovery first.")
                continue
            
            confirm = input(f"\nScrape all {len(events)} events? (y/n): ").strip().lower()
            if confirm == 'y':
                scraper = GAEventScraper(db_path, config)
                for event_id, event_info in events.items():
                    scraper.scrape_event(event_id, event_info)
                
                print(f"\n✅ Complete! {scraper.games_scraped} total games saved.")
            
        elif choice == '6':
            event_id = input("\nEnter GotSport event ID to add: ").strip()
            if event_id:
                discovery = GAEventDiscovery(config)
                discovery.add_event_by_id(event_id)
            
        elif choice == '7':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")


def main():
    parser = argparse.ArgumentParser(description="GA Events Scraper v2")
    parser.add_argument('--discover', action='store_true', help='Discover new events')
    parser.add_argument('--scrape', action='store_true', help='Scrape active events')
    parser.add_argument('--scrape-all', action='store_true', help='Scrape ALL discovered events')
    parser.add_argument('--scrape-event', type=str, help='Scrape specific event ID')
    parser.add_argument('--add-event', type=str, help='Add event by GotSport ID')
    parser.add_argument('--status', action='store_true', help='Show event status')
    parser.add_argument('--db', type=str, help='Database path')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation prompts (for admin UI)')
    
    args = parser.parse_args()
    
    # Initialize
    db_path = get_db_path(args.db)
    config = EventConfigManager()
    
    print("\n" + "="*70)
    print("🏆 GA EVENTS SCRAPER v2.0")
    print("="*70)
    print(f"📁 Database: {db_path}")
    print(f"📋 Config: {CONFIG_FILE}")
    
    # Handle command-line arguments
    if args.discover:
        discovery = GAEventDiscovery(config)
        discovery.discover_events()
        
    elif args.add_event:
        discovery = GAEventDiscovery(config)
        discovery.add_event_by_id(args.add_event)
        
    elif args.status:
        show_status(config)
        
    elif args.scrape:
        active = config.get_active_events()
        if not active:
            print("\n⚠️  No active events. Run --discover first.")
            return
        
        print(f"\n📋 Found {len(active)} active events")
        
        if not args.no_confirm:
            confirm = input("Scrape these events? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return
        
        scraper = GAEventScraper(db_path, config, debug=args.debug)
        for event_id, event_info in active.items():
            scraper.scrape_event(event_id, event_info)
        
        print(f"\n✅ Complete! {scraper.games_scraped} games saved.")
        
    elif args.scrape_all:
        events = config.get_events()
        if not events:
            print("\n⚠️  No events discovered. Run --discover first.")
            return
        
        print(f"\n📋 Found {len(events)} events to scrape")
        
        if not args.no_confirm:
            confirm = input(f"Scrape all {len(events)} events? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return
        
        scraper = GAEventScraper(db_path, config, debug=args.debug)
        for event_id, event_info in events.items():
            scraper.scrape_event(event_id, event_info)
        
        print(f"\n✅ Complete! {scraper.games_scraped} games saved.")
        
    elif args.scrape_event:
        events = config.get_events()
        event_info = events.get(args.scrape_event)
        
        if not event_info:
            print(f"\n⚠️  Event {args.scrape_event} not in config. Adding it...")
            discovery = GAEventDiscovery(config)
            if discovery.add_event_by_id(args.scrape_event):
                event_info = config.get_events().get(args.scrape_event)
        
        scraper = GAEventScraper(db_path, config, debug=args.debug)
        scraper.scrape_event(args.scrape_event, event_info)
        
        print(f"\n✅ Done! {scraper.games_scraped} games saved.")
        
    else:
        # Interactive mode (unless --no-confirm which means automated run)
        if args.no_confirm:
            # Default action for automated runs: scrape active events
            print("\n🤖 Automated mode: scraping active events...")
            active = config.get_active_events()
            if active:
                scraper = GAEventScraper(db_path, config, debug=args.debug)
                for event_id, event_info in active.items():
                    scraper.scrape_event(event_id, event_info)
                print(f"\n✅ Complete! {scraper.games_scraped} games saved.")
            else:
                print("No active events to scrape.")
        else:
            interactive_menu(config, db_path)


if __name__ == "__main__":
    main()
