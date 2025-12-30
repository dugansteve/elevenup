#!/usr/bin/env python3
"""
GotSport Tournament Game Scraper v4

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

Improvements over v3:
- Better age group extraction from page headers, division text, and team names
- Extracts age from birth year patterns (2011, 2012, etc.)
- Falls back to team name parsing when page-level age not found

Usage:
    python gotsport_game_scraper_final.py EVENT_ID
    python gotsport_game_scraper_final.py EVENT_ID --visible
    python gotsport_game_scraper_final.py EVENT_ID --limit 20

Requirements:
    pip install selenium webdriver-manager beautifulsoup4
"""

import csv
import time
import re
import sys
import os
import json
import random
from datetime import datetime
from bs4 import BeautifulSoup

# Human-like behavior settings
MIN_DELAY = 2.0
MAX_DELAY = 5.0
PAGE_LOAD_WAIT = 3.0


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

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4"], check=True)
    from bs4 import BeautifulSoup


def extract_age_group(text, context_gender=None):
    """
    Extract age group from text. Returns tuple (age_group, gender) or (None, None).

    Handles patterns like:
    - U13, U14, U15 (with optional gender suffix)
    - B13, G14 (Boys 13, Girls 14)
    - 2011, 2012, 2013 (birth years)
    - "Boys 14", "Girls U15"
    - "18B", "17G" in team names
    """
    if not text:
        return None, None

    # Pattern 1: B13, G14 format
    match = re.search(r'\b([BG])(\d{1,2})\b', text)
    if match:
        gender = 'Boys' if match.group(1) == 'B' else 'Girls'
        age = match.group(2)
        return f"{match.group(1)}{age}", gender

    # Pattern 2: 18B, 17G format (age then gender letter)
    match = re.search(r'\b(\d{1,2})([BG])\b', text)
    if match:
        age = match.group(1)
        gender_letter = match.group(2)
        gender = 'Boys' if gender_letter == 'B' else 'Girls'
        return f"{gender_letter}{age}", gender

    # Pattern 3: U13, U14 format with optional gender
    match = re.search(r'\bU(\d{1,2})\s*([BG])?\b', text, re.IGNORECASE)
    if match:
        age = match.group(1)
        gender_suffix = match.group(2)

        if gender_suffix:
            gender = 'Boys' if gender_suffix.upper() == 'B' else 'Girls'
            return f"{gender_suffix.upper()}{age}", gender

        # Check context for gender
        if re.search(r'\b(boy|male)\b', text, re.IGNORECASE) or context_gender == 'Male':
            return f"B{age}", 'Boys'
        elif re.search(r'\b(girl|female)\b', text, re.IGNORECASE) or context_gender == 'Female':
            return f"G{age}", 'Girls'

        return f"U{age}", None

    # Pattern 4: Birth year (2011, 2012, etc.)
    # Convention: Gxx = birth year 20xx (G14 = born 2014, NOT age 14)
    match = re.search(r'\b20(0[89]|1[0-9])\b', text)
    if match:
        birth_year_suffix = match.group(1)  # "11" for 2011, "14" for 2014

        if re.search(r'\b(boy|male|^B\s)', text, re.IGNORECASE) or context_gender == 'Male':
            return f"B{birth_year_suffix}", 'Boys'
        elif re.search(r'\b(girl|female|^G\s)', text, re.IGNORECASE) or context_gender == 'Female':
            return f"G{birth_year_suffix}", 'Girls'

        return birth_year_suffix, None

    # Pattern 5: "Boys 14", "Girls U15"
    match = re.search(r'\b(Boys?|Girls?)\s*U?(\d{1,2})\b', text, re.IGNORECASE)
    if match:
        gender = 'Boys' if 'boy' in match.group(1).lower() else 'Girls'
        age = match.group(2)
        prefix = 'B' if gender == 'Boys' else 'G'
        return f"{prefix}{age}", gender

    return None, None


def extract_age_from_team_name(home_team, away_team):
    """Extract age group from team names as fallback"""
    for team in [home_team, away_team]:
        if not team:
            continue

        age_group, gender = extract_age_group(team)
        if age_group:
            return age_group, gender

    return None, None


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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    return driver


def wait_for_content(driver, timeout=10):
    """Wait for page content to load"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(random.uniform(PAGE_LOAD_WAIT, PAGE_LOAD_WAIT + 1.5))
    except:
        time.sleep(PAGE_LOAD_WAIT)


def get_event_info(driver, event_id):
    """Get basic event info"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}"
    driver.get(url)
    wait_for_content(driver)

    info = {'event_id': event_id, 'name': '', 'url': url}

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]
        for line in lines[:10]:
            if len(line) > 5 and len(line) < 100:
                if not any(skip in line.lower() for skip in ['home', 'website', 'register', 'english', 'gotsport', 'powered', 'cookie']):
                    info['name'] = line
                    break
    except:
        pass

    return info


def discover_divisions(driver, event_id):
    """
    Discover all divisions/age groups from the event page.
    Returns list of {age_group, gender, group_id, text} dicts.
    """
    divisions = []
    seen_groups = set()

    base_url = f"https://system.gotsport.com/org_event/events/{event_id}"
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Method 1: Find all links with schedule URLs containing group IDs
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)

        # Look for group= parameter in URL
        group_match = re.search(r'group=(\d+)', href)
        if group_match:
            group_id = group_match.group(1)
            if group_id not in seen_groups:
                seen_groups.add(group_id)

                # Extract age/gender from link text and parent context
                # Get parent text for more context
                parent_text = ""
                if link.parent:
                    parent_text = link.parent.get_text(strip=True)

                combined_text = f"{text} {parent_text}"
                age_group, gender = extract_age_group(combined_text)

                divisions.append({
                    'age_group': age_group or '',
                    'gender': gender or '',
                    'group_id': group_id,
                    'text': text[:50]
                })

    # Method 2: Look for age/gender patterns in page and construct URLs
    body_text = driver.find_element(By.TAG_NAME, "body").text

    # Find all age groups mentioned (U13, U14, etc.)
    ages = set(re.findall(r'U(\d+)', body_text, re.I))

    # Sort ages to process in natural order
    sorted_ages = sorted(ages, key=lambda x: int(x))

    for age in sorted_ages:
        for gender, gender_code in [('Boys', 'Male'), ('Girls', 'Female')]:
            try:
                test_url = f"{base_url}/schedules?age=U{age}&gender={gender_code}"
                driver.get(test_url)
                wait_for_content(driver, timeout=5)

                test_html = driver.page_source
                group_match = re.search(r'group=(\d+)', test_html)

                if group_match:
                    group_id = group_match.group(1)
                    if group_id not in seen_groups:
                        seen_groups.add(group_id)
                        prefix = 'B' if gender == 'Boys' else 'G'
                        divisions.append({
                            'age_group': f"{prefix}{age}",
                            'gender': gender,
                            'group_id': group_id,
                            'text': f"U{age} {gender}"
                        })

                human_delay(1.0, 2.0)
            except:
                pass

    print(f"  Found {len(divisions)} unique divisions (by group ID)")
    return divisions


def extract_page_age_group(driver, soup, url):
    """Extract age group from the current schedule page"""

    # Method 1: Check URL parameters
    age_match = re.search(r'age=U(\d+)', url, re.I)
    gender_match = re.search(r'gender=(Male|Female)', url, re.I)

    if age_match:
        age = age_match.group(1)
        if gender_match:
            gender = gender_match.group(1)
            prefix = 'B' if gender == 'Male' else 'G'
            return f"{prefix}{age}", 'Boys' if gender == 'Male' else 'Girls'
        return f"U{age}", None

    # Method 2: Check page headers (h1, h2, h3)
    for tag in ['h1', 'h2', 'h3', 'h4']:
        headers = soup.find_all(tag)
        for header in headers:
            header_text = header.get_text(strip=True)
            age_group, gender = extract_age_group(header_text)
            if age_group:
                return age_group, gender

    # Method 3: Check page title
    title = soup.find('title')
    if title:
        title_text = title.get_text(strip=True)
        age_group, gender = extract_age_group(title_text)
        if age_group:
            return age_group, gender

    # Method 4: Look for breadcrumbs or navigation text
    nav_text = ""
    for nav in soup.find_all(['nav', 'ol', 'ul'], class_=re.compile(r'breadcrumb|nav', re.I)):
        nav_text += " " + nav.get_text(strip=True)

    if nav_text:
        age_group, gender = extract_age_group(nav_text)
        if age_group:
            return age_group, gender

    return None, None


def scrape_division(driver, event_id, division, event_name):
    """Scrape games from a single division"""
    games = []
    group_id = division['group_id']
    default_age = division.get('age_group', '')
    default_gender = division.get('gender', '')

    url = f"https://system.gotsport.com/org_event/events/{event_id}/schedules?date=All&group={group_id}"

    try:
        driver.get(url)
        wait_for_content(driver)
    except Exception as e:
        print(f"    Error loading page: {e}")
        return games

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Try to extract age group from page if not already known
    if not default_age:
        page_age, page_gender = extract_page_age_group(driver, soup, url)
        if page_age:
            default_age = page_age
        if page_gender:
            default_gender = page_gender

    # Find all tables
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 4:
                continue

            cell_texts = [c.get_text(strip=True) for c in cells]
            game = parse_game_cells(cells, cell_texts, default_age, default_gender)

            if game and game.get('home_team') and game.get('away_team'):
                game['tournament_id'] = event_id
                game['tournament_name'] = event_name
                game['group_id'] = group_id
                game['source_url'] = url
                game['scraped_at'] = datetime.now().isoformat()
                games.append(game)

    return games


def parse_game_cells(cells, cell_texts, default_age, default_gender):
    """Parse table cells into a game dict"""
    game = {
        'game_date': '',
        'game_time': '',
        'home_team': '',
        'away_team': '',
        'home_score': None,
        'away_score': None,
        'age_group': default_age,
        'gender': default_gender,
        'field': '',
        'status': 'scheduled',
        'external_game_id': ''
    }

    teams = []

    for idx, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        links = cell.find_all('a')

        # Game ID - first cell, just digits
        if idx == 0 and re.match(r'^\d+', text):
            game['external_game_id'] = re.match(r'^(\d+)', text).group(1)
            continue

        # Date/Time cell
        date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})', text, re.I)
        if date_match:
            game['game_date'] = date_match.group(1)
            time_match = re.search(r'\d{4}\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)', text, re.I)
            if time_match:
                game['game_time'] = time_match.group(1)
            else:
                time_match = re.search(r'(?:^|[^\d])(\d{1,2}:\d{2}\s*(?:AM|PM))', text, re.I)
                if time_match:
                    game['game_time'] = time_match.group(1)
            continue

        # Score cell
        score_match = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', text.strip())
        if score_match:
            game['home_score'] = int(score_match.group(1))
            game['away_score'] = int(score_match.group(2))
            game['status'] = 'final'
            continue

        # Team cells
        if links:
            for link in links:
                link_text = link.get_text(strip=True)
                if link_text and len(link_text) >= 3:
                    href = link.get('href', '').lower()
                    if any(x in href for x in ['map', 'location', 'field']):
                        continue
                    teams.append(link_text)

        # Field/Location
        if any(x in text.lower() for x in ['field', 'park', 'complex', 'stadium', 'rrmpc']):
            game['field'] = text

    # Assign teams
    if len(teams) >= 2:
        game['home_team'] = teams[0]
        game['away_team'] = teams[1]
    elif len(teams) == 1:
        game['home_team'] = teams[0]

    # Skip invalid games
    if not game['home_team'] or not game['away_team']:
        return None

    # Skip bye games
    if 'bye' in game['home_team'].lower() or 'bye' in game['away_team'].lower():
        return None

    # FALLBACK: Extract age from team names if not set
    if not game['age_group']:
        team_age, team_gender = extract_age_from_team_name(game['home_team'], game['away_team'])
        if team_age:
            game['age_group'] = team_age
        if team_gender and not game['gender']:
            game['gender'] = team_gender

    return game


def save_games_incremental(games, output_file, write_header=False):
    """Save games to CSV incrementally"""
    if not games:
        return

    fieldnames = [
        'tournament_id', 'tournament_name', 'game_date', 'game_time',
        'home_team', 'away_team', 'home_score', 'away_score',
        'age_group', 'gender', 'group_id', 'field', 'status', 'external_game_id',
        'source_url', 'scraped_at'
    ]

    mode = 'w' if write_header else 'a'
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if write_header:
            writer.writeheader()
        writer.writerows(games)


def scrape_event(driver, event_id, visible=False, limit=None):
    """Scrape all games from a GotSport event"""
    print(f"\nScraping GotSport event {event_id}...")

    output_file = f"gotsport_{event_id}_games.csv"
    all_games = []
    games_seen = set()

    event_info = get_event_info(driver, event_id)
    print(f"  Event: {event_info['name']}")

    divisions = discover_divisions(driver, event_id)

    if limit:
        divisions = divisions[:limit]
        print(f"  Limited to {limit} divisions")

    first_save = True

    for i, div in enumerate(divisions):
        print(f"  [{i+1}/{len(divisions)}] {div.get('text', '')} (group {div['group_id']}) age={div.get('age_group', '?')}")

        games = scrape_division(driver, event_id, div, event_info['name'])

        new_games = []
        for g in games:
            key = (g['home_team'], g['away_team'], g['game_date'], g['game_time'])
            if key not in games_seen:
                games_seen.add(key)
                new_games.append(g)

        if new_games:
            all_games.extend(new_games)
            save_games_incremental(new_games, output_file, write_header=first_save)
            first_save = False
            print(f"    {len(new_games)} new games (total: {len(all_games)})")
        else:
            print(f"    No new games")

        delay = human_delay(MIN_DELAY, MAX_DELAY)
        print(f"    (waiting {delay:.1f}s...)")

    print(f"\n  Total unique games: {len(all_games)}")
    return all_games, event_info


def main():
    args = sys.argv[1:]

    visible = '--visible' in args
    limit = None

    for i, a in enumerate(args):
        if a == '--limit' and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except:
                pass

    args = [a for a in args if not a.startswith('--') and not a.isdigit() or a == args[0]]

    if not args or args[0].startswith('--'):
        print(__doc__)
        print("\nExamples:")
        print("  python gotsport_game_scraper_final.py 45571")
        print("  python gotsport_game_scraper_final.py 45571 --limit 10")
        print("  python gotsport_game_scraper_final.py 45571 --visible")
        return

    event_id = args[0]

    print("=" * 70)
    print("GotSport Game Scraper v4 (with improved age group extraction)")
    print("=" * 70)

    driver = setup_driver(visible=visible)

    try:
        games, event_info = scrape_event(driver, event_id, visible, limit)

        output_file = f"gotsport_{event_id}_games.csv"

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Event: {event_info['name']}")
        print(f"Total games: {len(games)}")
        print(f"Output: {output_file}")

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

            # Show age breakdown
            print(f"\nBy age group:")
            for age, count in sorted(by_age.items()):
                print(f"  {age}: {count}")

            # Show sample games
            print("\nSample games:")
            for g in games[:5]:
                print(f"  {g['home_team'][:25]} vs {g['away_team'][:25]} | {g['age_group']} | {g['game_date']}")

        print(f"\n  Result: {len(games)} games")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
