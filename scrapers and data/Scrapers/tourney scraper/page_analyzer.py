#!/usr/bin/env python3
"""
Page Analyzer - Debug tool to examine tournament page structure

Usage:
    python page_analyzer.py URL
    python page_analyzer.py URL --visible
    python page_analyzer.py URL --save
"""

import time
import re
import sys
import os

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
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    return driver


def analyze_page(driver, url, save_html=False):
    """Analyze a tournament page structure"""
    print(f"\nLoading: {url}")
    driver.get(url)

    # Wait for page load
    time.sleep(5)

    print(f"\nTitle: {driver.title}")
    print(f"Current URL: {driver.current_url}")

    page_source = driver.page_source
    print(f"Page size: {len(page_source):,} characters")

    # Check for common elements
    print("\n--- ELEMENT COUNTS ---")

    elements = {
        'tables': len(driver.find_elements(By.TAG_NAME, "table")),
        'divs': len(driver.find_elements(By.TAG_NAME, "div")),
        'links': len(driver.find_elements(By.TAG_NAME, "a")),
        'h1s': len(driver.find_elements(By.TAG_NAME, "h1")),
        'h2s': len(driver.find_elements(By.TAG_NAME, "h2")),
        'selects': len(driver.find_elements(By.TAG_NAME, "select")),
        'buttons': len(driver.find_elements(By.TAG_NAME, "button")),
    }

    for elem, count in elements.items():
        print(f"  {elem}: {count}")

    # Look for game-related patterns
    print("\n--- GAME PATTERNS ---")

    patterns = {
        'scores (X-Y)': len(re.findall(r'\b\d{1,2}\s*[-–]\s*\d{1,2}\b', page_source)),
        'times (HH:MM)': len(re.findall(r'\d{1,2}:\d{2}\s*(?:AM|PM)?', page_source, re.I)),
        'dates (MM/DD)': len(re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', page_source)),
        'age groups (U##)': len(re.findall(r'\bU[-]?\d+[GB]?\b', page_source, re.I)),
        '"vs" text': len(re.findall(r'\bvs\.?\b', page_source, re.I)),
    }

    for pattern, count in patterns.items():
        print(f"  {pattern}: {count}")

    # Show all H1 and H2 text
    print("\n--- HEADINGS ---")
    h1s = driver.find_elements(By.TAG_NAME, "h1")
    for h1 in h1s[:5]:
        text = h1.text.strip()
        if text:
            print(f"  H1: {text[:80]}")

    h2s = driver.find_elements(By.TAG_NAME, "h2")
    for h2 in h2s[:5]:
        text = h2.text.strip()
        if text:
            print(f"  H2: {text[:80]}")

    # Show tables info
    print("\n--- TABLES ---")
    tables = driver.find_elements(By.TAG_NAME, "table")
    for i, table in enumerate(tables[:5]):
        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"  Table {i}: {len(rows)} rows")
        if rows:
            first_row = rows[0].text[:100]
            print(f"    First row: {first_row}")

    # Show select options
    print("\n--- DROPDOWNS ---")
    selects = driver.find_elements(By.TAG_NAME, "select")
    for i, select in enumerate(selects[:3]):
        try:
            options = select.find_elements(By.TAG_NAME, "option")
            option_texts = [o.text.strip()[:50] for o in options[:5]]
            print(f"  Select {i}: {len(options)} options")
        except:
            pass

    # Look for specific classes that might contain games
    print("\n--- GAME-RELATED CLASSES ---")
    game_classes = [
        "[class*='game']",
        "[class*='match']",
        "[class*='schedule']",
        "[class*='fixture']",
        "[class*='result']",
        "[class*='score']",
        "[class*='team']",
    ]

    for selector in game_classes:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            print(f"  {selector}: {len(elements)} elements")
            sample = elements[0].text[:100] if elements else ""
            if sample:
                print(f"    Sample: {sample}")

    # Show body text excerpt
    print("\n--- PAGE TEXT SAMPLE ---")
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text[:2000]
        # Handle encoding issues
        text = text.encode('ascii', 'replace').decode('ascii')
        print(text)
    except Exception as e:
        print(f"Error getting body text: {e}")

    # Save HTML if requested
    if save_html:
        filename = "page_dump.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"\n--- Saved HTML to {filename} ---")

    return page_source


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        print("\nExample URLs:")
        print("  https://system.gotsport.com/org_event/events/45571")
        print("  https://public.totalglobalsports.com/public/event/3446/schedules-standings")
        print("  https://soccer.sincsports.com/details.aspx?tid=GSSJUN")
        return

    url = args[0]
    visible = '--visible' in args
    save = '--save' in args

    driver = setup_driver(visible=visible)

    try:
        analyze_page(driver, url, save_html=save)
    finally:
        if not visible:
            driver.quit()
        else:
            print("\nBrowser will stay open for inspection. Close manually when done.")
            input("Press Enter to close...")
            driver.quit()


if __name__ == "__main__":
    main()
