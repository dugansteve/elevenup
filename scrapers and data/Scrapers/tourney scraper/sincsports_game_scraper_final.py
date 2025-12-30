#!/usr/bin/env python3
"""
SincSports Tournament Game Scraper v2

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

Improved scraper that navigates through division pages to extract all games.
SincSports URL format: soccer.sincsports.com/schedule.aspx?tid=EVENTCODE

Usage:
    python sincsports_game_scraper_final.py EVENTCODE
    python sincsports_game_scraper_final.py EVENTCODE --visible

Examples:
    python sincsports_game_scraper_final.py GSSJUN    # Gulf States Juniors
    python sincsports_game_scraper_final.py GSTATSS   # Gulf States College Showcase

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
MIN_DELAY = 2.0
MAX_DELAY = 5.0

def human_delay(min_sec=None, max_sec=None):
    """Add random human-like delay"""
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


def get_event_info(driver, event_code):
    """Get basic event info"""
    info = {
        'event_id': event_code,
        'name': '',
        'dates': '',
        'location': '',
        'url': f'https://soccer.sincsports.com/schedule.aspx?tid={event_code}'
    }

    # Try the main page first
    try:
        driver.get(f'https://soccer.sincsports.com/TTContent.aspx?tid={event_code}&tab=1')
        time.sleep(3)

        # Get title
        title = driver.title
        if title:
            clean = title.replace(' - Soccer', '').replace(' | SincSports', '').strip()
            if clean and 'sincsports' not in clean.lower():
                info['name'] = clean

        # Look for event name in content
        body_text = driver.find_element(By.TAG_NAME, 'body').text

        # Try to find location info
        location_match = re.search(r'(?:in|at)\s+([A-Za-z\s]+(?:,\s*[A-Z]{2})?)', body_text)
        if location_match:
            info['location'] = location_match.group(1).strip()

        # Find dates
        date_match = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:\s*[-&]\s*\d{1,2})?,?\s*\d{4}', body_text)
        if date_match:
            info['dates'] = date_match.group(0)

    except Exception as e:
        print(f"  Error getting event info: {e}")

    return info


def get_division_links(driver, event_code):
    """Get list of division schedule page URLs"""
    divisions = []

    # Go to schedule page
    schedule_url = f'https://soccer.sincsports.com/schedule.aspx?tid={event_code}&tab=3&sub=0'
    driver.get(schedule_url)
    time.sleep(4)

    # Find all division links
    links = driver.find_elements(By.TAG_NAME, 'a')
    for link in links:
        href = link.get_attribute('href') or ''
        text = link.text.strip()

        # Look for division links (contain year like 2015, 2014 or U14, U13)
        if 'div=' in href and ('schedule.aspx' in href or 'TTSchedules' in href):
            # Extract division name from link text or URL
            div_match = re.search(r'div=([A-Za-z0-9]+)', href)
            div_id = div_match.group(1) if div_match else ''

            divisions.append({
                'name': text,
                'url': href,
                'div_id': div_id
            })

    # Dedupe by URL
    seen = set()
    unique_divisions = []
    for d in divisions:
        if d['url'] not in seen:
            seen.add(d['url'])
            unique_divisions.append(d)

    return unique_divisions


def parse_division_games(driver, division_info, event_code, event_name):
    """Parse all games from a division page"""
    games = []

    try:
        driver.get(division_info['url'])
        time.sleep(3)

        body_text = driver.find_element(By.TAG_NAME, 'body').text
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]

        # Parse games - they follow pattern:
        # Day of week
        # Date (MM/DD/YYYY)
        # Time (HH:MM AM/PM)
        # Game # (#XXXXX)
        # H: Home Team Name
        # A: Away Team Name
        # [Home Score]
        # [Away Score]
        # Division Name
        # Field Name

        current_date = ''
        current_time = ''
        current_game_num = ''
        home_team = ''
        away_team = ''
        home_score = None
        away_score = None
        field = ''

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for date
            date_match = re.match(r'^(\d{1,2}/\d{1,2}/\d{2,4})$', line)
            if date_match:
                current_date = date_match.group(1)
                i += 1
                continue

            # Check for time
            time_match = re.match(r'^(\d{1,2}:\d{2}\s*(?:AM|PM))$', line, re.IGNORECASE)
            if time_match:
                current_time = time_match.group(1)
                i += 1
                continue

            # Check for game number
            game_num_match = re.match(r'^#(\d+)$', line)
            if game_num_match:
                current_game_num = game_num_match.group(1)
                i += 1
                continue

            # Check for home team
            if line.startswith('H:'):
                home_team = line[2:].strip()
                i += 1
                continue

            # Check for away team
            if line.startswith('A:'):
                away_team = line[2:].strip()

                # After away team, look for scores in next lines
                home_score = None
                away_score = None

                # Check next lines for scores
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if re.match(r'^\d{1,2}$', next_line):
                        home_score = int(next_line)
                        i += 1
                        if i + 1 < len(lines):
                            next_line2 = lines[i + 1]
                            if re.match(r'^\d{1,2}$', next_line2):
                                away_score = int(next_line2)
                                i += 1

                # Look for field info in following lines
                for j in range(i + 1, min(i + 4, len(lines))):
                    if 'Field' in lines[j] or 'Foley' in lines[j] or 'Stadium' in lines[j]:
                        field = lines[j]
                        break

                # If we have both teams, create game record
                if home_team and away_team:
                    status = 'final' if home_score is not None else 'scheduled'

                    game = {
                        'game_date': current_date,
                        'game_time': current_time,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score,
                        'age_group': division_info['name'],
                        'division': division_info['div_id'],
                        'field': field,
                        'status': status,
                        'game_number': current_game_num,
                        'tournament_id': event_code,
                        'tournament_name': event_name,
                        'source_url': division_info['url'],
                        'scraped_at': datetime.now().isoformat()
                    }
                    games.append(game)

                # Reset for next game
                home_team = ''
                away_team = ''
                home_score = None
                away_score = None
                field = ''
                i += 1
                continue

            i += 1

    except Exception as e:
        print(f"    Error parsing division: {e}")

    return games


def scrape_event_games(driver, event_code, visible=False):
    """Scrape all games from a SincSports event"""
    all_games = []

    print(f"\nScraping SincSports event {event_code}...")

    # Get event info
    event_info = get_event_info(driver, event_code)
    print(f"  Event: {event_info['name']}")
    if event_info['location']:
        print(f"  Location: {event_info['location']}")
    if event_info['dates']:
        print(f"  Dates: {event_info['dates']}")

    # Get division links
    divisions = get_division_links(driver, event_code)
    print(f"  Found {len(divisions)} divisions")

    if not divisions:
        print("  No divisions found!")
        return [], event_info

    # Scrape each division
    for i, div in enumerate(divisions):
        print(f"  [{i+1}/{len(divisions)}] {div['name']}")

        games = parse_division_games(driver, div, event_code, event_info['name'])

        if games:
            all_games.extend(games)
            print(f"    Found {len(games)} games")

        # Human-like delay between divisions
        if i < len(divisions) - 1:
            delay = human_delay()
            print(f"    (waiting {delay:.1f}s...)")

    # Dedupe games
    seen = set()
    unique_games = []
    for game in all_games:
        key = (game['home_team'], game['away_team'], game['game_date'], game['game_time'])
        if key not in seen:
            seen.add(key)
            unique_games.append(game)

    print(f"\n  Total unique games: {len(unique_games)}")

    return unique_games, event_info


def save_games(games, output_file):
    """Save games to CSV"""
    if not games:
        print("No games to save!")
        return

    fieldnames = [
        'tournament_id', 'tournament_name', 'game_date', 'game_time',
        'home_team', 'away_team', 'home_score', 'away_score',
        'age_group', 'division', 'field', 'status', 'game_number',
        'source_url', 'scraped_at'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(games)

    print(f"\nSaved {len(games)} games to {output_file}")


def main():
    args = sys.argv[1:]

    visible = '--visible' in args
    args = [a for a in args if a != '--visible']

    if not args:
        print(__doc__)
        return

    event_code = args[0].upper()

    print("=" * 70)
    print("SincSports Game Scraper v2")
    print("=" * 70)

    driver = setup_driver(visible=visible)

    try:
        games, event_info = scrape_event_games(driver, event_code, visible)

        # Save to file
        output_file = f"sincsports_{event_code}_games.csv"
        save_games(games, output_file)

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Event: {event_info['name']}")
        print(f"Games found: {len(games)}")

        if games:
            # By status
            by_status = {}
            for g in games:
                s = g['status']
                by_status[s] = by_status.get(s, 0) + 1
            print(f"By status: {by_status}")

            # By age group
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
