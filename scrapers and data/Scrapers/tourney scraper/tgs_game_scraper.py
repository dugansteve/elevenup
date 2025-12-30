#!/usr/bin/env python3
"""
TotalGlobalSports Tournament Game Scraper

Scrapes game schedules and results from TotalGlobalSports tournament pages.
Extracts: teams, scores, dates, times, age groups, brackets

Usage:
    python tgs_game_scraper.py EVENT_ID
    python tgs_game_scraper.py EVENT_ID --visible
    python tgs_game_scraper.py --batch tournaments.csv

Requirements:
    pip install selenium webdriver-manager
"""

import csv
import json
import time
import re
import sys
import os
import random
from datetime import datetime

# Human-like behavior settings
MIN_DELAY = 2.0  # Minimum seconds between requests
MAX_DELAY = 5.0  # Maximum seconds between requests


def human_delay(min_sec=None, max_sec=None):
    """Add a random human-like delay between requests"""
    min_sec = min_sec or MIN_DELAY
    max_sec = max_sec or MAX_DELAY
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "selenium"], check=True)
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "webdriver-manager"], check=True)
    from webdriver_manager.chrome import ChromeDriverManager


def setup_driver(visible=False):
    """Setup Chrome browser"""
    options = Options()

    if not visible:
        options.add_argument("--headless=new")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)

    return driver


def wait_for_page_load(driver, timeout=15):
    """Wait for TGS page to fully load (React app) with human-like timing"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Extra wait for React to render (human-like random delay)
        time.sleep(random.uniform(3.5, 5.0))
        return True
    except:
        time.sleep(random.uniform(3.5, 5.0))
        return False


def get_event_info(driver, event_id):
    """Get basic event info from TGS"""
    url = f"https://public.totalglobalsports.com/public/event/{event_id}/schedules-standings"
    driver.get(url)
    wait_for_page_load(driver)

    info = {
        'event_id': event_id,
        'name': '',
        'dates': '',
        'location': '',
        'url': url
    }

    # Extract title
    try:
        title = driver.title
        if title:
            clean = title.replace(" - Schedules & Standings", "")
            clean = clean.replace(" | TotalGlobalSports", "").strip()
            if clean and len(clean) > 3:
                info['name'] = clean
    except:
        pass

    # Look for event name in page
    try:
        h1s = driver.find_elements(By.TAG_NAME, "h1")
        for h1 in h1s:
            text = h1.text.strip()
            if text and len(text) > 3 and "Total Global" not in text:
                info['name'] = text
                break

        h2s = driver.find_elements(By.TAG_NAME, "h2")
        for h2 in h2s:
            text = h2.text.strip()
            if text and len(text) > 3 and "Total Global" not in text and "Schedule" not in text:
                if not info['name']:
                    info['name'] = text
                break
    except:
        pass

    return info


def get_divisions(driver, event_id):
    """Get list of divisions/age groups from TGS event"""
    divisions = []

    try:
        # TGS often has tabs or dropdowns for divisions
        # Look for tab navigation
        tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], .tab, [class*='tab']")
        for tab in tabs:
            text = tab.text.strip()
            if re.search(r'\bU[-]?\d+|G\d{2}|B\d{2}|Boys|Girls', text, re.IGNORECASE):
                divisions.append(text)

        # Look for dropdown/select options
        selects = driver.find_elements(By.TAG_NAME, "select")
        for select in selects:
            options = select.find_elements(By.TAG_NAME, "option")
            for opt in options:
                text = opt.text.strip()
                if re.search(r'\bU[-]?\d+|G\d{2}|B\d{2}|Boys|Girls', text, re.IGNORECASE):
                    divisions.append(text)

        # Look for links containing division info
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.strip()
            if re.search(r'\bU[-]?\d+[GB]?\b', text, re.IGNORECASE) and len(text) < 30:
                divisions.append(text)

    except Exception as e:
        print(f"  Error getting divisions: {e}")

    # Dedupe
    divisions = list(set(divisions))
    return sorted(divisions)


def parse_game_row(row_text, cells=None):
    """Parse a game from row text"""
    game = {
        'game_date': '',
        'game_time': '',
        'home_team': '',
        'away_team': '',
        'home_score': None,
        'away_score': None,
        'age_group': '',
        'division': '',
        'bracket': '',
        'field': '',
        'status': 'scheduled'
    }

    # Date patterns
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{2,4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:,?\s*\d{4})?)',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, row_text, re.IGNORECASE)
        if match:
            game['game_date'] = match.group(1)
            break

    # Time pattern
    time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)', row_text, re.IGNORECASE)
    if time_match:
        game['game_time'] = time_match.group(1)

    # Score pattern - look for score in various formats
    # Format: "Team1 3 - 2 Team2" or "3-2" or "(3-2)"
    score_patterns = [
        r'\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b',
        r'\((\d{1,2})\s*[-–]\s*(\d{1,2})\)',
    ]
    for pattern in score_patterns:
        match = re.search(pattern, row_text)
        if match:
            h, a = int(match.group(1)), int(match.group(2))
            if h <= 20 and a <= 20:  # Valid score range
                game['home_score'] = h
                game['away_score'] = a
                game['status'] = 'final'
                break

    # Age group patterns
    age_patterns = [
        r'\b(U[-]?\d+[GB]?)\b',
        r'\b(G\d{2})\b',  # G12, G14 = Girls 2012, 2014 birth year
        r'\b(B\d{2})\b',  # B12, B14 = Boys 2012, 2014 birth year
        r'\b(Boys?\s+U[-]?\d+)\b',
        r'\b(Girls?\s+U[-]?\d+)\b',
        r'\b(20\d{2})\b',  # Birth year
    ]
    for pattern in age_patterns:
        match = re.search(pattern, row_text, re.IGNORECASE)
        if match:
            game['age_group'] = match.group(1).upper()
            break

    # Field/location
    field_match = re.search(r'Field[:\s]+(\w+)', row_text, re.IGNORECASE)
    if field_match:
        game['field'] = field_match.group(1)

    return game


def extract_teams_from_text(text):
    """Try to extract two team names from text"""
    home_team = ''
    away_team = ''

    # Remove common non-team text
    clean_text = text
    clean_text = re.sub(r'\d{1,2}[/:-]\d{1,2}[/:-]?\d{0,4}', '', clean_text)  # dates
    clean_text = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM)?', '', clean_text, flags=re.IGNORECASE)  # times
    clean_text = re.sub(r'\b\d{1,2}\s*[-–]\s*\d{1,2}\b', '', clean_text)  # scores
    clean_text = re.sub(r'\bU[-]?\d+[GB]?\b', '', clean_text, flags=re.IGNORECASE)  # age groups
    clean_text = re.sub(r'\bField[:\s]+\w+', '', clean_text, flags=re.IGNORECASE)  # field
    clean_text = re.sub(r'\b(Final|Scheduled|TBD|vs\.?|v\.?|@)\b', '', clean_text, flags=re.IGNORECASE)

    # Split by common separators
    separators = [' vs ', ' v ', ' @ ', ' - ', '\n', '|']
    parts = [clean_text]
    for sep in separators:
        new_parts = []
        for p in parts:
            new_parts.extend(p.split(sep))
        parts = new_parts

    # Clean and filter parts
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]

    # Take first two substantial parts as teams
    potential_teams = []
    for part in parts:
        # Skip if too short or looks like non-team text
        if len(part) < 3:
            continue
        if part.isdigit():
            continue
        if part.lower() in ['home', 'away', 'score', 'time', 'date', 'field', 'final', 'tbd']:
            continue
        potential_teams.append(part[:60])  # Limit length

    if len(potential_teams) >= 2:
        home_team = potential_teams[0]
        away_team = potential_teams[1]
    elif len(potential_teams) == 1:
        home_team = potential_teams[0]

    return home_team, away_team


def scrape_games_from_page(driver, event_id, event_name=""):
    """Scrape all games from current TGS page"""
    games = []

    # Wait for content to load
    time.sleep(2)

    page_source = driver.page_source

    # Method 1: Look for game cards/rows in common patterns
    game_selectors = [
        "[class*='game']",
        "[class*='match']",
        "[class*='fixture']",
        "[class*='schedule-row']",
        "[class*='event-row']",
        "tr",
    ]

    for selector in game_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)

        for elem in elements:
            text = elem.text.strip()
            if not text or len(text) < 10:
                continue

            # Check if this looks like a game entry
            # Should have either: team names, a time, or a score
            has_time = bool(re.search(r'\d{1,2}:\d{2}', text))
            has_score = bool(re.search(r'\b\d{1,2}\s*[-–]\s*\d{1,2}\b', text))
            has_vs = bool(re.search(r'\bvs\.?\b|\bv\b|\b@\b', text, re.IGNORECASE))

            if not (has_time or has_score or has_vs):
                continue

            # Parse game
            game = parse_game_row(text)
            home, away = extract_teams_from_text(text)

            if home:
                game['home_team'] = home
            if away:
                game['away_team'] = away

            # Only add if we have at least one team
            if game['home_team'] or game['away_team']:
                game['tournament_id'] = event_id
                game['tournament_name'] = event_name
                game['source_url'] = driver.current_url
                game['scraped_at'] = datetime.now().isoformat()
                games.append(game)

    # Method 2: Parse tables directly
    tables = driver.find_elements(By.TAG_NAME, "table")
    for table in tables:
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 2:
                continue

            row_text = ' '.join([c.text for c in cells])

            # Skip if already processed or not a game
            if len(row_text) < 10:
                continue

            has_time = bool(re.search(r'\d{1,2}:\d{2}', row_text))
            has_score = bool(re.search(r'\b\d{1,2}\s*[-–]\s*\d{1,2}\b', row_text))

            if not (has_time or has_score):
                continue

            game = parse_game_row(row_text)
            home, away = extract_teams_from_text(row_text)

            if home:
                game['home_team'] = home
            if away:
                game['away_team'] = away

            if game['home_team'] or game['away_team']:
                game['tournament_id'] = event_id
                game['tournament_name'] = event_name
                game['source_url'] = driver.current_url
                game['scraped_at'] = datetime.now().isoformat()
                games.append(game)

    return games


def click_all_tabs(driver):
    """Click through all division tabs to load their content (with human-like delays)"""
    tabs_clicked = []

    try:
        # Find tab elements
        tab_selectors = [
            "[role='tab']",
            ".tab",
            "[class*='tab-']",
            "[class*='division']",
        ]

        for selector in tab_selectors:
            tabs = driver.find_elements(By.CSS_SELECTOR, selector)
            for tab in tabs:
                try:
                    text = tab.text.strip()
                    if text and text not in tabs_clicked:
                        tab.click()
                        # Human-like delay after clicking
                        human_delay(2.0, 3.5)
                        tabs_clicked.append(text)
                except:
                    pass

    except Exception as e:
        print(f"  Error clicking tabs: {e}")

    return tabs_clicked


def scrape_event_games(driver, event_id, visible=False):
    """Scrape all games from a TGS event"""
    all_games = []

    # Get event info
    print(f"\nScraping TGS event {event_id}...")
    event_info = get_event_info(driver, event_id)
    print(f"  Event: {event_info['name']}")

    # Check if event exists
    if not event_info['name'] or 'not found' in event_info['name'].lower():
        print("  Event not found!")
        return [], event_info

    # Get divisions
    divisions = get_divisions(driver, event_id)
    print(f"  Found {len(divisions)} divisions: {divisions[:5]}...")

    # Main schedules page
    schedules_url = f"https://public.totalglobalsports.com/public/event/{event_id}/schedules-standings"
    driver.get(schedules_url)
    wait_for_page_load(driver)

    # Click through tabs to load all content
    tabs = click_all_tabs(driver)
    print(f"  Clicked {len(tabs)} tabs")

    # Scrape games
    games = scrape_games_from_page(driver, event_id, event_info['name'])
    all_games.extend(games)
    print(f"  Found {len(games)} games on schedules page")

    # Try brackets page
    brackets_url = f"https://public.totalglobalsports.com/public/event/{event_id}/brackets"
    try:
        driver.get(brackets_url)
        wait_for_page_load(driver)
        click_all_tabs(driver)
        games = scrape_games_from_page(driver, event_id, event_info['name'])
        all_games.extend(games)
        print(f"  Found {len(games)} games on brackets page")
    except:
        pass

    # Dedupe games
    seen = set()
    unique_games = []
    for game in all_games:
        key = (game['home_team'], game['away_team'], game['game_date'], game['game_time'])
        if key not in seen and (game['home_team'] or game['away_team']):
            seen.add(key)
            unique_games.append(game)

    print(f"  Total unique games: {len(unique_games)}")

    return unique_games, event_info


def save_games(games, output_file):
    """Save games to CSV"""
    if not games:
        print("No games to save!")
        return

    fieldnames = [
        'tournament_id', 'tournament_name', 'game_date', 'game_time',
        'home_team', 'away_team', 'home_score', 'away_score',
        'age_group', 'division', 'bracket', 'field', 'status',
        'source_url', 'scraped_at'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(games)

    print(f"\nSaved {len(games)} games to {output_file}")


def main():
    args = sys.argv[1:]

    visible = '--visible' in args
    args = [a for a in args if a != '--visible']

    if not args:
        print(__doc__)
        print("\nExample: python tgs_game_scraper.py 4067")
        print("Known tournaments:")
        print("  3446 - Legends FC The Classic (May 2025)")
        print("  4028 - Legends FC Winter Classic (Jan 2026)")
        print("  4067 - Surf College Cup Youngers")
        return

    event_id = args[0]

    print("=" * 70)
    print("TotalGlobalSports Game Scraper")
    print("=" * 70)

    driver = setup_driver(visible=visible)

    try:
        games, event_info = scrape_event_games(driver, event_id, visible)

        # Save to file
        output_file = f"tgs_{event_id}_games.csv"
        save_games(games, output_file)

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Event: {event_info['name']}")
        print(f"Games found: {len(games)}")

        if games:
            by_status = {}
            for g in games:
                s = g['status']
                by_status[s] = by_status.get(s, 0) + 1
            print(f"By status: {by_status}")

            by_age = {}
            for g in games:
                a = g['age_group'] or 'unknown'
                by_age[a] = by_age.get(a, 0) + 1
            print(f"By age group: {dict(sorted(by_age.items())[:10])}")

    finally:
        driver.quit()

    print("\nDone!")


if __name__ == "__main__":
    main()
