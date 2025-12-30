#!/usr/bin/env python3
"""
TotalGlobalSports Event Extractor v8
- Anti-bot detection measures
- Option to show browser: --visible
- Option to rescrape all: --rescrape
- Detailed debugging for every page
- Longer waits for JavaScript rendering

Requirements:
    pip install selenium webdriver-manager

Usage:
    python tgs_details_extractor_final.py                    # Scan 1-9999, headless
    python tgs_details_extractor_final.py 100-500            # Scan range
    python tgs_details_extractor_final.py --visible          # Show browser window
    python tgs_details_extractor_final.py --rescrape         # Don't skip existing IDs
    python tgs_details_extractor_final.py 1-100 --visible --rescrape
"""

import csv
import time
import re
import sys
import os
from datetime import datetime
from collections import Counter

# Check dependencies
print("Checking dependencies...")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    print("  ✓ selenium")
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "selenium"], check=True)
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    print("  ✓ webdriver-manager")
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "webdriver-manager"], check=True)
    from webdriver_manager.chrome import ChromeDriverManager

OUTPUT_FILE = "tgs_master_database.csv"
PROGRESS_FILE = "tgs_progress.txt"

# Classification keywords
TOURNAMENT_KEYWORDS = [
    'cup', 'classic', 'invitational', 'showcase', 'tournament', 'challenge',
    'shootout', 'kickoff', 'memorial', 'championship', 'presidents',
    'thanksgiving', 'holiday', 'winter', 'spring', 'summer', 'fall',
    'college id', 'id camp', 'friendlies', 'scrimmage', 'jamboree'
]

NON_SOCCER_KEYWORDS = [
    'concert', 'music', 'band', 'tribute', 'boots in the park', 'festival',
    'flea', 'vintage', 'market', 'trivia', 'cinco de mayo', 'acoustic',
    'beer', 'brew', 'wine', 'tickets', 'dj ', 'live music', 'summerfest',
    'food truck', 'bbq', 'craft'
]

LEAGUE_KEYWORDS = [
    'soccer league', 'football club', 'ayso', 'rec league', 'recreational'
]


def setup_driver(visible=False):
    """Setup Chrome with anti-detection measures"""
    print(f"\n  Setting up Chrome ({'VISIBLE' if visible else 'HEADLESS'})...")
    
    options = Options()
    
    # Headless or visible
    if not visible:
        options.add_argument("--headless=new")
    
    # Anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Standard options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
    # Real browser user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable images for faster loading (optional)
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # options.add_experimental_option("prefs", prefs)
    
    print("  Downloading/checking ChromeDriver...")
    try:
        driver_path = ChromeDriverManager().install()
        print(f"  ✓ ChromeDriver ready")
    except Exception as e:
        print(f"  ✗ ChromeDriver failed: {e}")
        sys.exit(1)
    
    print("  Starting browser...")
    try:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Additional anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        print("  ✓ Browser started!")
        return driver
    except Exception as e:
        print(f"  ✗ Browser failed: {e}")
        sys.exit(1)


def wait_for_page_load(driver, timeout=10):
    """Wait for page to fully load including JavaScript"""
    try:
        # Wait for document ready state
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Extra wait for React/Vue/Angular to render
        time.sleep(3)
        return True
    except:
        time.sleep(3)
        return False


def extract_name(driver, page_source):
    """Try multiple methods to extract event name"""
    name = ""
    method = ""
    
    # Method 1: Page title
    try:
        title = driver.title
        if title and len(title) > 5:
            # Clean up title
            clean_title = title.replace(" - Schedules & Standings", "")
            clean_title = clean_title.replace(" | TotalGlobalSports", "")
            clean_title = clean_title.replace("Total Global Sports", "").strip()
            if clean_title and len(clean_title) > 3:
                name = clean_title
                method = "title"
    except:
        pass
    
    # Method 2: H1 tags
    if not name:
        try:
            h1s = driver.find_elements(By.TAG_NAME, "h1")
            for h1 in h1s:
                text = h1.text.strip()
                if text and len(text) > 3 and "Total Global" not in text:
                    name = text
                    method = "h1"
                    break
        except:
            pass
    
    # Method 3: H2 tags
    if not name:
        try:
            h2s = driver.find_elements(By.TAG_NAME, "h2")
            for h2 in h2s:
                text = h2.text.strip()
                if text and len(text) > 3 and "Total Global" not in text and "Schedule" not in text:
                    name = text
                    method = "h2"
                    break
        except:
            pass
    
    # Method 4: Look for specific class patterns
    if not name:
        try:
            selectors = [
                "[class*='event-name']", "[class*='eventName']",
                "[class*='event-title']", "[class*='eventTitle']",
                "[class*='tournament']", "[class*='header'] h1",
                "[class*='header'] h2", ".title", "#title"
            ]
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 3 and "Total Global" not in text:
                        name = text.split('\n')[0]  # First line only
                        method = f"css:{selector}"
                        break
                if name:
                    break
        except:
            pass
    
    # Method 5: Regex in page source
    if not name:
        try:
            patterns = [
                r'"eventName"\s*:\s*"([^"]+)"',
                r'"name"\s*:\s*"([^"]+)"',
                r'"title"\s*:\s*"([^"]+)"',
                r'<h1[^>]*>([^<]+)</h1>',
                r'<h2[^>]*>([^<]+)</h2>',
            ]
            for pattern in patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    text = match.group(1).strip()
                    if text and len(text) > 3 and "Total Global" not in text:
                        name = text
                        method = "regex"
                        break
        except:
            pass
    
    # Method 6: Any prominent text element
    if not name:
        try:
            # Get all text content
            body = driver.find_element(By.TAG_NAME, "body")
            all_text = body.text
            lines = [l.strip() for l in all_text.split('\n') if l.strip()]
            for line in lines[:20]:  # Check first 20 lines
                if len(line) > 5 and len(line) < 100:
                    if "Total Global" not in line and "Schedule" not in line:
                        if not line.startswith("http") and not line.isdigit():
                            name = line
                            method = "body_text"
                            break
        except:
            pass
    
    return name, method


def extract_dates(page_source):
    """Extract dates from page"""
    patterns = [
        r'(\w+\s+\d{1,2}[-–]\d{1,2},?\s*\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{2,4}\s*[-–]\s*\d{1,2}/\d{1,2}/\d{2,4})',
        r'(\w+\s+\d{1,2},?\s*\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_source)
        if match:
            return match.group(1)
    return ""


def extract_year(date_str, page_source):
    """Extract year"""
    if date_str:
        match = re.search(r'20\d{2}', date_str)
        if match:
            return match.group(0)
    
    if page_source:
        years = re.findall(r'20[12]\d', page_source[:10000])
        if years:
            return Counter(years).most_common(1)[0][0]
    return ""


def extract_team_count(driver, page_source):
    """Extract team count"""
    count = 0
    
    # Method 1: Text patterns
    patterns = [r'(\d+)\s*teams?', r'teams?\s*[:\s]+(\d+)']
    for pattern in patterns:
        matches = re.findall(pattern, page_source.lower())
        for m in matches:
            try:
                n = int(m if isinstance(m, str) else m[0])
                if 2 <= n <= 500:
                    count = max(count, n)
            except:
                pass
    
    # Method 2: Table rows
    if count == 0:
        try:
            tables = driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                if 3 <= len(rows) <= 300:
                    count = max(count, len(rows) - 1)
        except:
            pass
    
    return count


def extract_game_count(driver, page_source):
    """Extract game count"""
    count = 0
    
    # Count time patterns
    times = re.findall(r'\d{1,2}:\d{2}\s*(am|pm|AM|PM)?', page_source)
    if times:
        count = len(times) // 2
    
    # Count score patterns
    if count == 0:
        scores = re.findall(r'\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b', page_source)
        valid = [s for s in scores if int(s[0]) <= 20 and int(s[1]) <= 20]
        count = len(valid)
    
    return count


def classify_event(name, page_text=""):
    """Classify event type"""
    if not name:
        return "invalid"
    
    combined = (name + " " + page_text).lower()
    
    for kw in NON_SOCCER_KEYWORDS:
        if kw in combined:
            return "non_soccer"
    
    for kw in TOURNAMENT_KEYWORDS:
        if kw in name.lower():
            return "tournament"
    
    for kw in LEAGUE_KEYWORDS:
        if kw in name.lower():
            return "league"
    
    if any(w in combined for w in ['bracket', 'semifinal', 'playoff', 'final']):
        return "possible_tournament"
    
    return "unknown"


def extract_event(driver, event_id, debug=True):
    """Extract all details from event page"""
    url = f"https://public.totalglobalsports.com/public/event/{event_id}/schedules-standings"
    
    result = {
        "event_id": event_id,
        "name": "",
        "event_type": "",
        "year": "",
        "full_date": "",
        "team_count": 0,
        "game_count": 0,
        "location": "",
        "has_schedule_data": False,
        "url": url,
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Load page
        driver.get(url)
        wait_for_page_load(driver)
        
        page_source = driver.page_source
        page_len = len(page_source)
        
        # Check for 404
        if "not found" in page_source.lower()[:2000] or "404" in page_source[:1000]:
            result["event_type"] = "not_found"
            if debug:
                print(f"  {event_id}: 404")
            return result
        
        # Check for empty page
        if page_len < 1000:
            result["event_type"] = "empty"
            if debug:
                print(f"  {event_id}: empty ({page_len} bytes)")
            return result
        
        # Extract name
        name, method = extract_name(driver, page_source)
        
        if not name:
            result["event_type"] = "no_name"
            if debug:
                print(f"  {event_id}: no_name ({page_len} bytes, title='{driver.title[:30] if driver.title else 'None'}')")
            return result
        
        # Clean name
        name = ' '.join(name.split())[:200]
        result["name"] = name
        
        # Extract other fields
        result["full_date"] = extract_dates(page_source)
        result["year"] = extract_year(result["full_date"], page_source)
        result["team_count"] = extract_team_count(driver, page_source)
        result["game_count"] = extract_game_count(driver, page_source)
        result["event_type"] = classify_event(name, page_source[:3000])
        result["has_schedule_data"] = result["team_count"] > 0 or result["game_count"] > 0
        
        # Debug output
        if debug:
            icon = "✓" if result["event_type"] == "tournament" else "?" if "possible" in result["event_type"] else " "
            teams = f" [{result['team_count']}t]" if result['team_count'] else ""
            games = f" [{result['game_count']}g]" if result['game_count'] else ""
            year = f" ({result['year']})" if result['year'] else ""
            print(f"{icon} {event_id}: {result['event_type']:12} | {name[:40]}{year}{teams}{games} [{method}]")
        
        return result
        
    except TimeoutException:
        result["event_type"] = "timeout"
        if debug:
            print(f"  {event_id}: TIMEOUT")
        return result
    except Exception as e:
        result["event_type"] = "error"
        if debug:
            print(f"  {event_id}: ERROR - {str(e)[:40]}")
        return result


def load_existing_ids():
    """Load existing event IDs from CSV"""
    ids = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ids.add(int(row['event_id']))
        except:
            pass
    return ids


def save_progress(event_id):
    """Save progress"""
    with open(PROGRESS_FILE, 'w') as f:
        f.write(str(event_id))


def parse_args():
    """Parse command line arguments"""
    start_id = 1
    end_id = 9999
    visible = False
    rescrape = False
    
    for arg in sys.argv[1:]:
        if arg == "--visible":
            visible = True
        elif arg == "--rescrape":
            rescrape = True
        elif "-" in arg and arg[0].isdigit():
            parts = arg.split("-")
            if len(parts) == 2:
                try:
                    start_id = int(parts[0])
                    end_id = int(parts[1])
                except:
                    pass
    
    return start_id, end_id, visible, rescrape


def main():
    start_id, end_id, visible, rescrape = parse_args()
    
    print("\n" + "=" * 80)
    print("TotalGlobalSports Event Extractor v8")
    print("=" * 80)
    print(f"Range: {start_id} to {end_id}")
    print(f"Browser: {'VISIBLE' if visible else 'HEADLESS'}")
    print(f"Mode: {'RESCRAPE ALL' if rescrape else 'SKIP EXISTING'}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 80)
    
    # Load existing if not rescraping
    existing_ids = set() if rescrape else load_existing_ids()
    if existing_ids:
        print(f"\nFound {len(existing_ids)} existing entries - will skip")
    
    # Setup browser
    print("\nInitializing browser...")
    driver = setup_driver(visible=visible)
    
    # Test with known events
    print("\n" + "-" * 80)
    print("TESTING with known events...")
    print("-" * 80)
    
    test_ids = [51, 17, 3446, 4028]  # Known tournaments
    test_passed = 0
    
    for test_id in test_ids:
        result = extract_event(driver, test_id, debug=True)
        if result["name"]:
            test_passed += 1
    
    print(f"\nTest results: {test_passed}/{len(test_ids)} found names")
    
    if test_passed == 0:
        print("\n⚠️  WARNING: No test events found names!")
        print("    The website may be blocking automation.")
        print("    Try running with --visible to see what's happening.")
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            driver.quit()
            return
    
    # Initialize CSV
    file_exists = os.path.exists(OUTPUT_FILE) and not rescrape
    fieldnames = [
        'event_id', 'name', 'event_type', 'year', 'full_date',
        'team_count', 'game_count', 'location', 'has_schedule_data',
        'url', 'scraped_at'
    ]
    
    # Stats
    stats = {
        'tournament': 0, 'possible_tournament': 0, 'league': 0,
        'non_soccer': 0, 'not_found': 0, 'empty': 0, 'no_name': 0,
        'unknown': 0, 'error': 0, 'timeout': 0, 'skipped': 0
    }
    
    start_time = time.time()
    processed = 0
    
    print("\n" + "=" * 80)
    print(f"STARTING SCAN: {start_id} to {end_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    # Open file in write mode if rescraping, append otherwise
    mode = 'w' if rescrape else 'a'
    
    try:
        with open(OUTPUT_FILE, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if mode == 'w' or not file_exists:
                writer.writeheader()
            
            for event_id in range(start_id, end_id + 1):
                # Skip existing unless rescraping
                if event_id in existing_ids:
                    stats['skipped'] += 1
                    continue
                
                processed += 1
                
                # Time update every 20
                if processed % 20 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    remaining = (end_id - event_id) / rate / 60 if rate > 0 else 0
                    now = datetime.now().strftime('%H:%M:%S')
                    
                    print(f"\n--- {now} | {elapsed/60:.1f}min elapsed | ETA: {remaining:.1f}min ---")
                    print(f"--- ID {event_id}/{end_id} | {processed} processed | "
                          f"{stats['tournament']} tournaments found ---\n")
                    save_progress(event_id)
                
                # Extract
                result = extract_event(driver, event_id, debug=True)
                
                # Update stats
                etype = result['event_type']
                stats[etype] = stats.get(etype, 0) + 1
                
                # Write
                writer.writerow(result)
                f.flush()
                
                # Delay
                time.sleep(0.5)
    
    except KeyboardInterrupt:
        print(f"\n\nInterrupted at {event_id}")
        save_progress(event_id)
    
    finally:
        driver.quit()
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"Duration: {elapsed/60:.1f} minutes")
    print(f"Processed: {processed} (skipped {stats['skipped']})")
    print(f"\nResults:")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        if v > 0:
            print(f"  {k}: {v}")
    print(f"\nSaved to: {OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    # Print usage if --help
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    main()
