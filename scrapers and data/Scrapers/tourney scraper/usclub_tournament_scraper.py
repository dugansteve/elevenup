#!/usr/bin/env python3
"""
US Club Soccer Tournament List Scraper

Scrapes the US Club Soccer sanctioned tournaments list and extracts:
- Tournament names, dates, locations
- Links to tournament websites
- Identifies the scheduling platform (GotSport, TGS, SincSports, etc.)

Usage:
    python usclub_tournament_scraper.py
    python usclub_tournament_scraper.py --visible  # Show browser

Requirements:
    pip install selenium webdriver-manager
"""

import csv
import time
import re
import sys
import os
from datetime import datetime
from urllib.parse import urlparse

# Check dependencies
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

OUTPUT_FILE = "usclub_tournaments.csv"
USCLUB_URL = "https://usclubsoccer.org/list-of-sanctioned-tournaments/"


def setup_driver(visible=False):
    """Setup Chrome with anti-detection measures"""
    print(f"\n  Setting up Chrome ({'VISIBLE' if visible else 'HEADLESS'})...")

    options = Options()

    if not visible:
        options.add_argument("--headless=new")

    # Anti-detection
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

    print("  Browser ready!")
    return driver


def identify_platform(url):
    """Identify the scheduling platform from a URL"""
    if not url:
        return None, None

    url_lower = url.lower()

    # GotSport
    if 'gotsport.com' in url_lower:
        # Extract event ID from URL patterns like:
        # https://system.gotsport.com/org_event/events/45571
        # https://system.gotsport.com/event_regs/1984898f0c
        match = re.search(r'/events?/(\w+)', url)
        if match:
            return 'gotsport', match.group(1)
        match = re.search(r'/event_regs/(\w+)', url)
        if match:
            return 'gotsport', match.group(1)
        return 'gotsport', None

    # TotalGlobalSports
    if 'totalglobalsports.com' in url_lower:
        # https://public.totalglobalsports.com/public/event/4067/schedules-standings
        match = re.search(r'/event/(\d+)', url)
        if match:
            return 'totalglobalsports', match.group(1)
        return 'totalglobalsports', None

    # SincSports
    if 'sincsports.com' in url_lower:
        # https://soccer.sincsports.com/details.aspx?tid=GSSJUN
        match = re.search(r'tid=(\w+)', url)
        if match:
            return 'sincsports', match.group(1)
        return 'sincsports', None

    # Athletes2Events
    if 'athletes2events.com' in url_lower:
        # https://sts.athletes2events.com/events/13/groups
        match = re.search(r'/events/(\d+)', url)
        if match:
            return 'athletes2events', match.group(1)
        return 'athletes2events', None

    return None, None


def extract_tournament_links(driver, tournament_element):
    """Extract all links from a tournament entry and identify schedule platform"""
    links = tournament_element.find_elements(By.TAG_NAME, "a")

    website_url = None
    schedule_url = None
    schedule_platform = None
    event_id = None

    for link in links:
        href = link.get_attribute("href")
        if not href:
            continue

        platform, eid = identify_platform(href)

        if platform:
            # This is a scheduling platform link
            schedule_url = href
            schedule_platform = platform
            event_id = eid
        elif not website_url and 'usclubsoccer.org' not in href:
            # First non-platform link is likely the tournament website
            website_url = href

    return website_url, schedule_url, schedule_platform, event_id


def scrape_tournament_list(driver):
    """Scrape the US Club Soccer tournament list"""
    print(f"\nLoading {USCLUB_URL}...")
    driver.get(USCLUB_URL)

    # Wait for page to load
    time.sleep(5)

    tournaments = []

    # Try to find tournament entries - the page likely has a table or list structure
    # We'll try multiple selectors

    # First, let's see what we're working with
    page_source = driver.page_source

    # Look for month headers and tournament entries
    # The page structure might be: Month header followed by tournament rows

    # Try finding all table rows or list items
    selectors_to_try = [
        "table tbody tr",
        ".tournament-list li",
        ".events-list .event",
        "article",
        ".wp-block-table tr",
        "[class*='tournament']",
        "[class*='event']",
    ]

    found_elements = []
    for selector in selectors_to_try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            print(f"  Found {len(elements)} elements with selector: {selector}")
            found_elements.extend(elements)

    # Also try to find the tournament structure by examining the page
    # Look for patterns in the text
    body_text = driver.find_element(By.TAG_NAME, "body").text

    # Parse by looking for date patterns followed by tournament info
    lines = body_text.split('\n')

    current_month = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if this is a month header
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']

        for month in months:
            if line.startswith(month) and ('2024' in line or '2025' in line or '2026' in line):
                current_month = line
                break

        # Look for tournament patterns: "Name  Date  State  Club  Ages"
        # These often appear as multi-line entries

        i += 1

    # Let's try a more direct approach - save the page HTML and parse it
    print(f"\n  Page title: {driver.title}")
    print(f"  Page has {len(page_source)} characters")

    # Look for tables specifically
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"  Found {len(tables)} tables")

    for idx, table in enumerate(tables):
        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"  Table {idx}: {len(rows)} rows")

        for row in rows[1:]:  # Skip header row
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                try:
                    # Extract cell text
                    name = cells[0].text.strip() if len(cells) > 0 else ""
                    dates = cells[1].text.strip() if len(cells) > 1 else ""
                    state = cells[2].text.strip() if len(cells) > 2 else ""
                    club = cells[3].text.strip() if len(cells) > 3 else ""
                    ages = cells[4].text.strip() if len(cells) > 4 else ""

                    if name and dates:
                        # Get links from the row
                        website_url, schedule_url, platform, event_id = extract_tournament_links(driver, row)

                        tournaments.append({
                            'name': name,
                            'dates': dates,
                            'state': state,
                            'club': club,
                            'age_groups': ages,
                            'website_url': website_url or '',
                            'schedule_url': schedule_url or '',
                            'schedule_platform': platform or '',
                            'event_id': event_id or '',
                            'status': 'found' if schedule_url else 'pending',
                            'scraped_at': datetime.now().isoformat()
                        })

                        print(f"    + {name[:40]} | {dates} | {state}")
                except Exception as e:
                    print(f"    Error parsing row: {e}")

    return tournaments


def scroll_and_load_all(driver, max_scrolls=20):
    """Scroll page to load any lazy-loaded content"""
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        print(f"  Scrolled {i+1}x, page height: {new_height}")

    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


def save_tournaments(tournaments, output_file):
    """Save tournaments to CSV"""
    if not tournaments:
        print("No tournaments to save!")
        return

    fieldnames = [
        'name', 'dates', 'state', 'club', 'age_groups',
        'website_url', 'schedule_url', 'schedule_platform',
        'event_id', 'status', 'scraped_at'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tournaments)

    print(f"\nSaved {len(tournaments)} tournaments to {output_file}")


def main():
    visible = '--visible' in sys.argv

    print("=" * 70)
    print("US Club Soccer Tournament List Scraper")
    print("=" * 70)

    driver = setup_driver(visible=visible)

    try:
        # Scroll to load all content
        driver.get(USCLUB_URL)
        time.sleep(3)
        scroll_and_load_all(driver)

        # Scrape tournaments
        tournaments = scrape_tournament_list(driver)

        # Save results
        save_tournaments(tournaments, OUTPUT_FILE)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total tournaments: {len(tournaments)}")

        by_platform = {}
        for t in tournaments:
            p = t['schedule_platform'] or 'unknown'
            by_platform[p] = by_platform.get(p, 0) + 1

        print("\nBy platform:")
        for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
            print(f"  {platform}: {count}")

        by_status = {}
        for t in tournaments:
            s = t['status']
            by_status[s] = by_status.get(s, 0) + 1

        print("\nBy status:")
        for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
            print(f"  {status}: {count}")

    finally:
        driver.quit()

    print("\nDone!")


if __name__ == "__main__":
    main()
