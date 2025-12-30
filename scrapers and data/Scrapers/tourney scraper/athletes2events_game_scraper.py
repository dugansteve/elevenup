#!/usr/bin/env python3
"""
Athletes2Events Tournament Game Scraper

Scrapes games from Athletes2Events tournament pages.
URL format: sts.athletes2events.com/events/{EVENT_ID}/groups

Usage:
    python athletes2events_game_scraper.py EVENT_ID
    python athletes2events_game_scraper.py EVENT_ID --visible

Examples:
    python athletes2events_game_scraper.py 13   # Coronado Holiday Cup Boys
    python athletes2events_game_scraper.py 11   # Coronado Holiday Cup Girls

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


def get_flight_ids(driver, event_id):
    """Get all flight IDs from the groups page"""
    url = f"https://sts.athletes2events.com/events/{event_id}/groups"
    print(f"  Loading groups page: {url}")

    try:
        driver.get(url)
        human_delay()

        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Find all schedule links with flight-id parameter
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='flight-id=']")

        flight_data = []
        seen_ids = set()

        for link in links:
            href = link.get_attribute('href')
            match = re.search(r'flight-id=(\d+)', href)
            if match:
                flight_id = match.group(1)
                if flight_id not in seen_ids:
                    seen_ids.add(flight_id)
                    # Try to get flight name from link text
                    flight_name = link.text.strip() or f"Flight {flight_id}"
                    flight_data.append({
                        'id': flight_id,
                        'name': flight_name
                    })

        print(f"  Found {len(flight_data)} flights")
        return flight_data

    except Exception as e:
        print(f"  Error getting flights: {e}")
        return []


def get_event_name(driver, event_id):
    """Get event name from the page"""
    try:
        # Look for title or header
        title_elem = driver.find_element(By.TAG_NAME, "h1")
        if title_elem:
            return title_elem.text.strip()
    except:
        pass

    try:
        title = driver.title
        if title and "Athletes2Events" not in title:
            return title.strip()
    except:
        pass

    return f"Athletes2Events Event {event_id}"


def parse_game_row(cells, division_name, event_name):
    """Parse a single row of game data"""
    try:
        if len(cells) < 8:
            return None

        # Expected columns: Game#, Division/Flight, Group, Time, Home Team, Result, Away Team, Field, Location
        game_num = cells[0].text.strip() if len(cells) > 0 else ""
        division = cells[1].text.strip() if len(cells) > 1 else division_name
        group = cells[2].text.strip() if len(cells) > 2 else ""
        time_str = cells[3].text.strip() if len(cells) > 3 else ""
        home_team = cells[4].text.strip() if len(cells) > 4 else ""
        result = cells[5].text.strip() if len(cells) > 5 else ""
        away_team = cells[6].text.strip() if len(cells) > 6 else ""
        field = cells[7].text.strip() if len(cells) > 7 else ""
        location = cells[8].text.strip() if len(cells) > 8 else ""

        # Skip if no teams
        if not home_team or not away_team:
            return None

        # Skip header rows
        if home_team.lower() in ['home team', 'home', 'team']:
            return None

        # Parse result (format: "1 - 2" or similar)
        home_score = ""
        away_score = ""
        if result and '-' in result:
            parts = result.split('-')
            if len(parts) == 2:
                home_score = parts[0].strip()
                away_score = parts[1].strip()

        # Extract age group from division (e.g., "Boys (2013)" -> "B13")
        age_group = ""
        gender = ""
        if division:
            # Check for gender
            if 'boy' in division.lower():
                gender = 'Boys'
            elif 'girl' in division.lower():
                gender = 'Girls'

            # Extract birth year
            # Convention: Gxx = birth year 20xx (G14 = born 2014, NOT age 14)
            year_match = re.search(r'\((\d{4})\)', division)
            if year_match:
                birth_year_suffix = year_match.group(1)[2:]  # "2014" → "14"
                prefix = 'B' if gender == 'Boys' else 'G'
                age_group = f"{prefix}{birth_year_suffix}"

        return {
            'game_num': game_num,
            'division': division,
            'group': group,
            'time': time_str,
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'field': field,
            'location': location,
            'age_group': age_group,
            'gender': gender,
            'tournament': event_name
        }

    except Exception as e:
        print(f"    Error parsing row: {e}")
        return None


def scrape_flight(driver, event_id, flight_id, flight_name, event_name):
    """Scrape games from a single flight's schedule page"""
    url = f"https://sts.athletes2events.com/events/{event_id}/schedules?flight-id={flight_id}"

    try:
        driver.get(url)
        human_delay(1.5, 3.0)

        # Wait for table to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        games = []
        current_date = ""

        # Find all tables (might be multiple for different dates)
        tables = driver.find_elements(By.TAG_NAME, "table")

        for table in tables:
            rows = table.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                # Check if this is a date header row
                row_text = row.text.strip()
                date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}', row_text, re.IGNORECASE)
                if date_match:
                    current_date = date_match.group(0)
                    continue

                # Try to parse as game row
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    game = parse_game_row(cells, flight_name, event_name)
                    if game:
                        game['date'] = current_date
                        games.append(game)

        return games

    except TimeoutException:
        print(f"    Timeout loading flight {flight_id}")
        return []
    except Exception as e:
        print(f"    Error scraping flight {flight_id}: {e}")
        return []


def scrape_event(event_id, visible=False):
    """Scrape all games from an Athletes2Events event"""
    print(f"\n{'='*60}")
    print(f"Scraping Athletes2Events: Event {event_id}")
    print(f"{'='*60}")

    driver = None
    all_games = []

    try:
        driver = setup_driver(visible)

        # Get list of flights
        flights = get_flight_ids(driver, event_id)

        if not flights:
            print("  No flights found!")
            return []

        # Get event name
        event_name = get_event_name(driver, event_id)
        print(f"  Event: {event_name}")

        # Scrape each flight
        for i, flight in enumerate(flights):
            print(f"  [{i+1}/{len(flights)}] Scraping {flight['name']} (flight {flight['id']})...")
            games = scrape_flight(driver, event_id, flight['id'], flight['name'], event_name)

            if games:
                print(f"    Found {len(games)} games")
                all_games.extend(games)
            else:
                print(f"    No games found")

            # Delay between flights
            human_delay(2.0, 4.0)

        print(f"\n  Total games scraped: {len(all_games)}")
        return all_games

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        if driver:
            driver.quit()


def save_games(games, event_id, event_name=""):
    """Save games to CSV file"""
    if not games:
        print("No games to save")
        return None

    # Create output filename
    safe_name = re.sub(r'[^\w\s-]', '', event_name or f"event_{event_id}")
    safe_name = re.sub(r'\s+', '_', safe_name)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"a2e_{safe_name}_{timestamp}.csv"

    # Define CSV columns
    fieldnames = [
        'tournament', 'date', 'time', 'age_group', 'gender',
        'home_team', 'away_team', 'home_score', 'away_score',
        'division', 'group', 'field', 'location', 'game_num'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(games)

    print(f"  Saved {len(games)} games to {filename}")
    return filename


def main():
    if len(sys.argv) < 2:
        print("Usage: python athletes2events_game_scraper.py EVENT_ID [--visible]")
        print("Examples:")
        print("  python athletes2events_game_scraper.py 13   # Coronado Holiday Cup Boys")
        print("  python athletes2events_game_scraper.py 11   # Coronado Holiday Cup Girls")
        sys.exit(1)

    event_id = sys.argv[1]
    visible = "--visible" in sys.argv

    games = scrape_event(event_id, visible)

    if games:
        event_name = games[0].get('tournament', '')
        save_games(games, event_id, event_name)
    else:
        print(f"\nNo games found for event {event_id}")


if __name__ == "__main__":
    main()
