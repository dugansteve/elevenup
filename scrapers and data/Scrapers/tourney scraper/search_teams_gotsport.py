#!/usr/bin/env python3
"""
Search for New Teams on GotSport

Searches for teams found in tournament data on GotSport to find their
club/team page URLs for future tracking.

Usage:
    python search_teams_gotsport.py              # Search top 50 new teams
    python search_teams_gotsport.py --limit 20   # Search top 20 only
"""

import json
import os
import sys
import time
import random
import re
import csv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_TEAMS_FILE = os.path.join(SCRIPT_DIR, "new_teams_from_tournaments.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "teams_found_on_gotsport.csv")

# Human-like delays
MIN_DELAY = 3.0
MAX_DELAY = 6.0


def load_new_teams():
    """Load new teams from JSON file"""
    # First regenerate the list
    print("Regenerating new teams list...")
    os.system("python find_new_teams.py")

    if not os.path.exists(NEW_TEAMS_FILE):
        print(f"File not found: {NEW_TEAMS_FILE}")
        return []

    with open(NEW_TEAMS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('teams', [])


def setup_driver():
    """Setup Chrome browser"""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)

    return driver


def search_gotsport_clubs(driver, search_term):
    """Search for clubs on GotSport"""
    from selenium.webdriver.common.by import By
    from bs4 import BeautifulSoup

    results = []

    # Clean up search term - just use club name portion
    clean_term = search_term.split()[0:3]  # First 3 words
    clean_term = ' '.join(clean_term)

    search_url = f"https://system.gotsport.com/clubs?utf8=%E2%9C%93&search%5Bname%5D={clean_term.replace(' ', '+')}"

    try:
        driver.get(search_url)
        time.sleep(3)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Look for club links in table
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            if '/clubs/' in href and text and len(text) > 2:
                # Extract club ID
                club_match = re.search(r'/clubs/(\d+)', href)
                if club_match:
                    club_id = club_match.group(1)
                    full_url = f"https://system.gotsport.com{href}" if href.startswith('/') else href

                    results.append({
                        'name': text,
                        'club_id': club_id,
                        'url': full_url
                    })

        # Dedupe by club_id
        seen = set()
        unique_results = []
        for r in results:
            if r['club_id'] not in seen:
                seen.add(r['club_id'])
                unique_results.append(r)

        return unique_results[:5]  # Top 5

    except Exception as e:
        print(f"    Error searching: {e}")
        return []


def search_teams(limit=50):
    """Search for new teams on GotSport"""
    teams = load_new_teams()

    if not teams:
        print("No teams to search")
        return

    print(f"\nLoaded {len(teams)} new teams")
    print(f"Will search for top {limit} teams\n")

    driver = setup_driver()
    found_teams = []

    try:
        for i, team in enumerate(teams[:limit]):
            # Get best original name to search
            original_names = team.get('original_names', [])
            if not original_names:
                continue

            # Pick shortest name (usually cleanest)
            search_name = min(original_names, key=len)

            print(f"[{i+1}/{min(limit, len(teams))}] Searching: {search_name[:50]}")

            results = search_gotsport_clubs(driver, search_name)

            if results:
                print(f"    Found {len(results)} matches:")
                for r in results[:3]:
                    print(f"      - {r['name'][:40]} (ID: {r['club_id']})")

                found_teams.append({
                    'search_term': search_name,
                    'normalized_name': team.get('normalized_name', ''),
                    'appearances': team.get('appearances', 0),
                    'tournaments': team.get('tournaments', []),
                    'gotsport_matches': results
                })
            else:
                print(f"    No matches found")

            # Human-like delay
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

    finally:
        driver.quit()

    # Save results
    save_results(found_teams)

    print(f"\n{'='*60}")
    print(f"SEARCH COMPLETE")
    print(f"{'='*60}")
    print(f"Teams searched: {min(limit, len(teams))}")
    print(f"Teams with matches: {len(found_teams)}")

    return found_teams


def save_results(teams):
    """Save results to CSV and JSON"""
    # Save to CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['search_term', 'normalized_name', 'appearances',
                        'tournaments', 'gotsport_name', 'gotsport_club_id', 'gotsport_url'])

        for team in teams:
            tournaments = '; '.join(team.get('tournaments', [])[:3])

            for match in team.get('gotsport_matches', []):
                writer.writerow([
                    team['search_term'],
                    team['normalized_name'],
                    team['appearances'],
                    tournaments,
                    match['name'],
                    match['club_id'],
                    match['url']
                ])

    print(f"Saved to {OUTPUT_FILE}")

    # Also save to JSON
    json_file = OUTPUT_FILE.replace('.csv', '.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'teams': teams
        }, f, indent=2)

    print(f"Saved to {json_file}")


def main():
    args = sys.argv[1:]

    limit = 50
    for i, arg in enumerate(args):
        if arg == '--limit' and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except:
                pass

    print("=" * 60)
    print("GOTSPORT TEAM SEARCH")
    print("=" * 60)

    search_teams(limit=limit)


if __name__ == "__main__":
    main()
