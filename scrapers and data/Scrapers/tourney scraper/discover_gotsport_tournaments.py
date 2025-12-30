#!/usr/bin/env python3
"""
GotSport Tournament Discovery Tool

Systematically discovers tournaments from GotSport by:
1. Scraping the featured tournaments page
2. Searching by state for all available tournaments
3. Finding tournament event IDs from schedule pages

Usage:
    python discover_gotsport_tournaments.py --featured     # Get featured tournaments
    python discover_gotsport_tournaments.py --state CA     # Search California tournaments
    python discover_gotsport_tournaments.py --all-states   # Search all US states
    python discover_gotsport_tournaments.py --add-premier  # Add known premier tournaments

Requirements:
    pip install selenium webdriver-manager beautifulsoup4
"""

import csv
import json
import time
import re
import sys
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "selenium"], check=True)
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "webdriver-manager"], check=True)
    from webdriver_manager.chrome import ChromeDriverManager


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOURNAMENTS_JSON = os.path.join(SCRIPT_DIR, "tournaments_data.json")
DISCOVERED_FILE = os.path.join(SCRIPT_DIR, "discovered_tournaments.json")

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

# Known premier tournaments that should always be tracked
# These are high-quality showcase/competitive tournaments
PREMIER_TOURNAMENTS = [
    # Mustang Stampede (California) - August 2025
    {
        "event_id": "42583",
        "platform": "gotsport",
        "name": "2025 Mustang Stampede U11-U13",
        "dates": "August 2-3, 2025",
        "start_date": "2025-08-02",
        "state": "CA",
        "city": "Danville",
        "age_groups": "U11-U13 Boys and Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/42583",
        "website_url": "https://mustangsoccer.com/tournaments/stampede-tournaments",
        "status": "upcoming",
        "sponsor": "Mustang Soccer",
        "gender": "Both",
        "level": "Competitive"
    },
    {
        "event_id": "42745",
        "platform": "gotsport",
        "name": "2025 Mustang Stampede U14-U17",
        "dates": "August 9-10, 2025",
        "start_date": "2025-08-09",
        "state": "CA",
        "city": "Danville",
        "age_groups": "U14-U17 Boys and Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/42745",
        "website_url": "https://mustangsoccer.com/tournaments/stampede-tournaments",
        "status": "upcoming",
        "sponsor": "Mustang Soccer",
        "gender": "Both",
        "level": "Competitive"
    },
    # IMG Cup (Florida) - Premier showcase
    {
        "event_id": "45941",
        "platform": "gotsport",
        "name": "IMG Cup - Boys Invitational 2025",
        "dates": "December 19-21, 2025",
        "start_date": "2025-12-19",
        "state": "FL",
        "city": "Bradenton",
        "age_groups": "U13-U19 Boys",
        "schedule_url": "https://system.gotsport.com/org_event/events/45941",
        "website_url": "https://www.imgacademy.com",
        "status": "upcoming",
        "sponsor": "IMG Academy",
        "gender": "Boys",
        "level": "Showcase"
    },
    # Weston Cup (Florida) - Major showcase
    {
        "event_id": "45745",
        "platform": "gotsport",
        "name": "Weston Cup & Showcase 2026",
        "dates": "February 13-16, 2026",
        "start_date": "2026-02-13",
        "state": "FL",
        "city": "Weston",
        "age_groups": "U9-U19 Boys and Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/45745",
        "website_url": "https://westoncup.com/",
        "status": "upcoming",
        "sponsor": "Weston FC",
        "gender": "Both",
        "level": "Showcase"
    },
    # Disney tournaments
    {
        "event_id": "5426",
        "platform": "gotsport",
        "name": "2025 Disney Young Legends Soccer Tournament",
        "dates": "December 28-30, 2025",
        "start_date": "2025-12-28",
        "state": "FL",
        "city": "Kissimmee",
        "age_groups": "U8-U14 Boys and Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/5426",
        "website_url": "https://www.disneysoccer.com",
        "status": "upcoming",
        "sponsor": "Disney Sports",
        "gender": "Both",
        "level": "Competitive"
    },
    # Jefferson Cup (Virginia) - Major East Coast showcase
    {
        "event_id": "5460",
        "platform": "gotsport",
        "name": "2026 Jefferson Cup Boys Weekend",
        "dates": "March 7-8, 2026",
        "start_date": "2026-03-07",
        "state": "VA",
        "city": "Richmond",
        "age_groups": "U9-U19 Boys",
        "schedule_url": "https://system.gotsport.com/org_event/events/5460",
        "website_url": "https://jeffersoncup.com",
        "status": "upcoming",
        "sponsor": "Richmond Strikers",
        "gender": "Boys",
        "level": "Showcase"
    },
    {
        "event_id": "5461",
        "platform": "gotsport",
        "name": "2026 Jefferson Cup Girls Weekend",
        "dates": "March 14-15, 2026",
        "start_date": "2026-03-14",
        "state": "VA",
        "city": "Richmond",
        "age_groups": "U9-U19 Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/5461",
        "website_url": "https://jeffersoncup.com",
        "status": "upcoming",
        "sponsor": "Richmond Strikers",
        "gender": "Girls",
        "level": "Showcase"
    },
    # Players College Showcase (Las Vegas)
    {
        "event_id": "5507",
        "platform": "gotsport",
        "name": "Players College Showcase Boys 2026",
        "dates": "March 6-8, 2026",
        "start_date": "2026-03-06",
        "state": "NV",
        "city": "Las Vegas",
        "age_groups": "U15-U19 Boys",
        "schedule_url": "https://system.gotsport.com/org_event/events/5507",
        "website_url": "https://playerscollegeshowcase.com",
        "status": "upcoming",
        "sponsor": "Players Showcase",
        "gender": "Boys",
        "level": "Showcase"
    },
    {
        "event_id": "5508",
        "platform": "gotsport",
        "name": "Players College Showcase Girls 2026",
        "dates": "March 13-15, 2026",
        "start_date": "2026-03-13",
        "state": "NV",
        "city": "Las Vegas",
        "age_groups": "U15-U19 Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/5508",
        "website_url": "https://playerscollegeshowcase.com",
        "status": "upcoming",
        "sponsor": "Players Showcase",
        "gender": "Girls",
        "level": "Showcase"
    },
    # Blues City Blowout (Tennessee)
    {
        "event_id": "5435",
        "platform": "gotsport",
        "name": "25th Annual Blues City Blowout",
        "dates": "February 27 - March 1, 2026",
        "start_date": "2026-02-27",
        "state": "TN",
        "city": "Memphis",
        "age_groups": "U8-U19 Boys and Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/5435",
        "website_url": "https://memphiscityfootball.com",
        "status": "upcoming",
        "sponsor": "Memphis City FC",
        "gender": "Both",
        "level": "Competitive"
    },
    # Dimitri Cup (Florida) - Well-known tournament
    {
        "event_id": "5409",
        "platform": "gotsport",
        "name": "23rd Annual Dimitri Cup U8-U12",
        "dates": "January 17-19, 2026",
        "start_date": "2026-01-17",
        "state": "FL",
        "city": "Lakewood Ranch",
        "age_groups": "U8-U12 Boys and Girls",
        "schedule_url": "https://system.gotsport.com/org_event/events/5409",
        "website_url": "https://dimitricup.com",
        "status": "upcoming",
        "sponsor": "Dimitri Cup",
        "gender": "Both",
        "level": "Competitive"
    },
]


def human_delay(min_sec=2.0, max_sec=4.0):
    """Add a random delay"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay


def setup_driver(visible=False):
    """Setup Chrome browser"""
    options = Options()
    if not visible:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def load_existing_tournaments():
    """Load existing tournaments from JSON"""
    if os.path.exists(TOURNAMENTS_JSON):
        with open(TOURNAMENTS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('tournaments', [])
    return []


def save_tournaments(tournaments):
    """Save tournaments to JSON"""
    data = {"tournaments": tournaments}
    with open(TOURNAMENTS_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(tournaments)} tournaments to {TOURNAMENTS_JSON}")


def get_existing_event_ids(tournaments):
    """Get set of existing event IDs"""
    return {t.get('event_id') for t in tournaments if t.get('event_id')}


def scrape_featured_tournaments(driver):
    """Scrape GotSport featured tournaments page"""
    print("\nScraping featured tournaments from GotSport...")
    url = "https://home.gotsoccer.com/featured.aspx"

    tournaments = []

    try:
        driver.get(url)
        time.sleep(3)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Find all tournament links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Look for event links
            match = re.search(r'/events?/(\d+)', href)
            if match:
                event_id = match.group(1)

                # Get surrounding text for context
                parent = link.parent
                parent_text = parent.get_text(strip=True) if parent else ""

                # Parse dates
                date_match = re.search(r'(\w+ \d+(?:-\d+)?(?:, \d{4})?)', parent_text)
                dates = date_match.group(1) if date_match else ""

                tournaments.append({
                    'event_id': event_id,
                    'platform': 'gotsport',
                    'name': text or f"Tournament {event_id}",
                    'dates': dates,
                    'schedule_url': f"https://system.gotsport.com/org_event/events/{event_id}",
                    'status': 'discovered'
                })

        print(f"  Found {len(tournaments)} featured tournaments")

    except Exception as e:
        print(f"  Error: {e}")

    return tournaments


def scrape_state_tournaments(driver, state):
    """Scrape tournaments for a specific state"""
    print(f"\nScraping tournaments for {state}...")
    url = f"https://home.gotsoccer.com/events.aspx?type=Tournament&state={state}"

    tournaments = []

    try:
        driver.get(url)
        time.sleep(3)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Find tournament cards/links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Look for event links
            match = re.search(r'events?[/=](\d+)', href)
            if match and len(text) > 3:
                event_id = match.group(1)

                # Skip if this is a navigation link
                if text.lower() in ['next', 'prev', 'previous', 'home']:
                    continue

                tournaments.append({
                    'event_id': event_id,
                    'platform': 'gotsport',
                    'name': text,
                    'state': state,
                    'schedule_url': f"https://system.gotsport.com/org_event/events/{event_id}",
                    'status': 'discovered'
                })

        # Try to find additional pages
        page = 2
        while page <= 5:  # Check up to 5 pages
            try:
                page_url = f"{url}&Page={page}"
                driver.get(page_url)
                time.sleep(2)

                page_html = driver.page_source
                if "No events found" in page_html or len(page_html) < 5000:
                    break

                page_soup = BeautifulSoup(page_html, 'html.parser')
                found_new = False

                for link in page_soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)

                    match = re.search(r'events?[/=](\d+)', href)
                    if match and len(text) > 3:
                        event_id = match.group(1)
                        if event_id not in [t['event_id'] for t in tournaments]:
                            found_new = True
                            tournaments.append({
                                'event_id': event_id,
                                'platform': 'gotsport',
                                'name': text,
                                'state': state,
                                'schedule_url': f"https://system.gotsport.com/org_event/events/{event_id}",
                                'status': 'discovered'
                            })

                if not found_new:
                    break

                page += 1
                human_delay(1, 2)

            except:
                break

        print(f"  Found {len(tournaments)} tournaments in {state}")

    except Exception as e:
        print(f"  Error: {e}")

    return tournaments


def add_premier_tournaments():
    """Add known premier tournaments to the tracking list"""
    print("\n" + "=" * 70)
    print("Adding Premier Tournaments")
    print("=" * 70)

    existing = load_existing_tournaments()
    existing_ids = get_existing_event_ids(existing)

    added = 0
    for t in PREMIER_TOURNAMENTS:
        if t['event_id'] not in existing_ids:
            existing.append(t)
            added += 1
            print(f"  + {t['name']} ({t['state']}) - Event ID: {t['event_id']}")
        else:
            print(f"  = {t['name']} (already exists)")

    if added > 0:
        save_tournaments(existing)
        print(f"\nAdded {added} new premier tournaments")
    else:
        print("\nAll premier tournaments already in tracking list")

    return added


def discover_all_states(visible=False):
    """Discover tournaments from all US states"""
    print("\n" + "=" * 70)
    print("Discovering Tournaments from All US States")
    print("=" * 70)

    existing = load_existing_tournaments()
    existing_ids = get_existing_event_ids(existing)

    driver = setup_driver(visible=visible)
    all_discovered = []

    try:
        for state in US_STATES:
            tournaments = scrape_state_tournaments(driver, state)

            new_tournaments = []
            for t in tournaments:
                if t['event_id'] not in existing_ids:
                    existing_ids.add(t['event_id'])
                    new_tournaments.append(t)

            if new_tournaments:
                all_discovered.extend(new_tournaments)
                print(f"    {len(new_tournaments)} new tournaments")

            human_delay(1.5, 3.0)

    finally:
        driver.quit()

    # Save discovered tournaments
    if all_discovered:
        with open(DISCOVERED_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_discovered, f, indent=2)
        print(f"\nSaved {len(all_discovered)} newly discovered tournaments to {DISCOVERED_FILE}")

    return all_discovered


def main():
    args = sys.argv[1:]

    if not args or args[0] in ['-h', '--help', 'help']:
        print(__doc__)
        print("""
Commands:
    --add-premier     Add known premier tournaments (Mustang Stampede, IMG Cup, etc.)
    --featured        Scrape GotSport featured tournaments page
    --state XX        Scrape tournaments from state XX (e.g., CA, TX, FL)
    --all-states      Scrape all US states (takes a while)
    --visible         Show browser window

Examples:
    python discover_gotsport_tournaments.py --add-premier
    python discover_gotsport_tournaments.py --state CA
    python discover_gotsport_tournaments.py --featured --visible
""")
        return

    visible = '--visible' in args

    if '--add-premier' in args:
        add_premier_tournaments()

    elif '--featured' in args:
        driver = setup_driver(visible=visible)
        try:
            tournaments = scrape_featured_tournaments(driver)

            # Add to existing
            existing = load_existing_tournaments()
            existing_ids = get_existing_event_ids(existing)

            added = 0
            for t in tournaments:
                if t['event_id'] not in existing_ids:
                    existing.append(t)
                    existing_ids.add(t['event_id'])
                    added += 1

            if added:
                save_tournaments(existing)
                print(f"Added {added} new featured tournaments")
        finally:
            driver.quit()

    elif '--state' in args:
        idx = args.index('--state')
        if idx + 1 < len(args):
            state = args[idx + 1].upper()
            driver = setup_driver(visible=visible)
            try:
                tournaments = scrape_state_tournaments(driver, state)

                existing = load_existing_tournaments()
                existing_ids = get_existing_event_ids(existing)

                added = 0
                for t in tournaments:
                    if t['event_id'] not in existing_ids:
                        existing.append(t)
                        existing_ids.add(t['event_id'])
                        added += 1

                if added:
                    save_tournaments(existing)
                    print(f"Added {added} new tournaments from {state}")
            finally:
                driver.quit()

    elif '--all-states' in args:
        discover_all_states(visible=visible)


if __name__ == "__main__":
    main()
