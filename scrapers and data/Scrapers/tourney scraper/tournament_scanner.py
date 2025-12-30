#!/usr/bin/env python3
"""
Tournament Platform Scanner - Run Locally
Scans GotSport (1-99999) and TotalGlobalSports (1-9999) for valid event IDs

Usage:
    python tournament_scanner.py gotsport      # Scan GotSport only
    python tournament_scanner.py tgs           # Scan TotalGlobalSports only  
    python tournament_scanner.py both          # Scan both platforms

Requirements:
    pip install requests
"""

import requests
import csv
import re
import time
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
GOTSPORT_OUTPUT = "gotsport_events.csv"
TGS_OUTPUT = "totalglobalsports_events.csv"
GOTSPORT_PROGRESS = "gotsport_progress.txt"
TGS_PROGRESS = "tgs_progress.txt"

# Request settings - MODERATE SPEED (safe but faster than ultra-slow)
TIMEOUT = 15
CONCURRENT_REQUESTS = 5      # 5 concurrent is still safe
DELAY_BETWEEN_BATCHES = 1.5  # 1.5 seconds between batches

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ============== GOTSPORT SCANNER ==============

def check_gotsport(event_id):
    """Check if a GotSport event ID is valid"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)

        if response.status_code != 200:
            return None

        html = response.text

        # Skip error/empty pages
        if len(html) < 5000:
            return None
        if "Page Not Found" in html or "404" in html[:500]:
            return None
        if "No event found" in html or "does not exist" in html.lower():
            return None

        # IMPORTANT: Empty placeholder pages are exactly ~72,666 bytes with no schedule groups
        # Real events are larger (100K+) OR have schedule group links
        schedule_groups = re.findall(r'group=(\d+)', html)
        has_custom_background = 'background_images' in html

        # Must have EITHER schedule groups OR be significantly larger than placeholder
        if len(schedule_groups) == 0 and len(html) < 80000 and not has_custom_background:
            return None

        # Try to extract event name from various sources
        name = ""

        # Method 1: Look for event name in URL patterns in the HTML
        name_match = re.search(r'/events/\d+["\']?\s*[^>]*>([^<]{5,80})<', html)
        if name_match:
            name = name_match.group(1).strip()

        # Method 2: Look in background image filename (often contains event name)
        if not name or len(name) < 5:
            bg_match = re.search(r'background[^>]+/([A-Za-z0-9_-]+)\.(png|jpg)', html)
            if bg_match:
                name = bg_match.group(1).replace('_', ' ').replace('-', ' ')

        # Method 3: Page title (might just be "GotSport" but try anyway)
        if not name or len(name) < 5:
            title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                name = title_match.group(1).replace(" | GotSport", "").strip()

        # Default name if nothing found
        if not name or name.lower() in ['gotsport', 'error', 'not found', '']:
            name = f"Event {event_id}"

        # Try to extract date/year info
        dates = ""
        year = ""

        # Pattern 1: "January 15-17, 2025" or "Jan 15-17 2025"
        date_match = re.search(r'(\w{3,9}\s+\d{1,2}[-–]\d{1,2},?\s*(\d{4}))', html)
        if date_match:
            dates = date_match.group(1)
            year = date_match.group(2)

        # Pattern 2: Look for year in the page
        if not year:
            year_match = re.search(r'\b(202[5-9])\b', html)  # Future years first
            if year_match:
                year = year_match.group(1)
            else:
                year_match = re.search(r'\b(202[4])\b', html)  # Then 2024
                if year_match:
                    year = year_match.group(1)

        # Extract location/state if possible
        state = ""
        state_patterns = [
            r',\s*([A-Z]{2})\s+\d{5}',  # City, ST 12345
            r'\b([A-Z]{2})\s*,?\s*(?:USA|United States)',
        ]
        for pattern in state_patterns:
            state_match = re.search(pattern, html)
            if state_match:
                state = state_match.group(1)
                break

        return {
            "event_id": event_id,
            "name": name[:100],  # Limit name length
            "dates": dates,
            "year": year,
            "state": state,
            "url": url,
            "found_at": datetime.now().isoformat()
        }

    except Exception as e:
        return None

def scan_gotsport(start_from=1, end_at=100000):
    """Scan GotSport event IDs"""
    print("\n" + "=" * 70)
    print("GOTSPORT SCANNER")
    print(f"Scanning event IDs {start_from} to {end_at-1}")
    print("=" * 70 + "\n")
    
    # Resume from progress file
    if os.path.exists(GOTSPORT_PROGRESS):
        with open(GOTSPORT_PROGRESS, 'r') as f:
            saved = int(f.read().strip())
            if saved > start_from:
                start_from = saved + 1
                print(f"Resuming from ID {start_from}")
    
    file_exists = os.path.exists(GOTSPORT_OUTPUT)
    found_count = 0
    
    with open(GOTSPORT_OUTPUT, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['event_id', 'name', 'dates', 'year', 'state', 'url', 'found_at']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        batch_size = CONCURRENT_REQUESTS
        
        for batch_start in range(start_from, end_at, batch_size):
            batch_end = min(batch_start + batch_size, end_at)
            batch_ids = list(range(batch_start, batch_end))
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {executor.submit(check_gotsport, eid): eid for eid in batch_ids}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        writer.writerow(result)
                        csvfile.flush()
                        found_count += 1
                        year_str = f" ({result['year']})" if result.get('year') else ""
                        # Encode safely for Windows console
                        name_safe = result['name'][:50].encode('ascii', 'replace').decode('ascii')
                        print(f"  + {result['event_id']:5d}: {name_safe}{year_str}")
            
            # Progress update
            if batch_start % 1000 == 0:
                print(f"\n[Progress] Checked {batch_start:,}/{end_at-1:,} | Found: {found_count}\n")
                with open(GOTSPORT_PROGRESS, 'w') as f:
                    f.write(str(batch_start))
            
            # Random delay to appear more human-like
            import random
            delay = DELAY_BETWEEN_BATCHES + random.uniform(0, 1.5)
            time.sleep(delay)
    
    print(f"\n{'=' * 70}")
    print(f"GotSport scan complete! Found {found_count} events")
    print(f"Results saved to: {GOTSPORT_OUTPUT}")
    print("=" * 70)
    
    return found_count

# ============== TOTALGLOBALSPORTS SCANNER ==============

def check_tgs(event_id):
    """Check if a TotalGlobalSports event ID is valid"""
    url = f"https://public.totalglobalsports.com/public/event/{event_id}/schedules-standings"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        
        if response.status_code != 200:
            return None
            
        html = response.text
        
        # Skip error pages
        if len(html) < 500:
            return None
        if "not found" in html.lower() or "error" in html.lower()[:200]:
            return None
            
        # Extract event name
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        name = title_match.group(1).strip() if title_match else ""
        name = name.replace(" | TotalGlobalSports", "").replace(" - Schedules", "").strip()
        
        if not name or len(name) < 3:
            name = f"Event {event_id}"
            
        # Try to extract date info
        date_match = re.search(r'(\w+ \d+[-–]\d+,? \d{4})', html)
        dates = date_match.group(1) if date_match else ""
        
        return {
            "event_id": event_id,
            "name": name,
            "dates": dates,
            "url": url,
            "found_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return None

def scan_tgs(start_from=1, end_at=10000):
    """Scan TotalGlobalSports event IDs"""
    print("\n" + "=" * 70)
    print("TOTALGLOBALSPORTS SCANNER")
    print(f"Scanning event IDs {start_from} to {end_at-1}")
    print("=" * 70 + "\n")
    
    # Resume from progress file
    if os.path.exists(TGS_PROGRESS):
        with open(TGS_PROGRESS, 'r') as f:
            saved = int(f.read().strip())
            if saved > start_from:
                start_from = saved + 1
                print(f"Resuming from ID {start_from}")
    
    file_exists = os.path.exists(TGS_OUTPUT)
    found_count = 0
    
    with open(TGS_OUTPUT, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['event_id', 'name', 'dates', 'url', 'found_at']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        batch_size = CONCURRENT_REQUESTS
        
        for batch_start in range(start_from, end_at, batch_size):
            batch_end = min(batch_start + batch_size, end_at)
            batch_ids = list(range(batch_start, batch_end))
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {executor.submit(check_tgs, eid): eid for eid in batch_ids}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        writer.writerow(result)
                        csvfile.flush()
                        found_count += 1
                        print(f"  ✓ {result['event_id']:4d}: {result['name'][:60]}")
            
            # Progress update
            if batch_start % 500 == 0:
                print(f"\n[Progress] Checked {batch_start:,}/{end_at-1:,} | Found: {found_count}\n")
                with open(TGS_PROGRESS, 'w') as f:
                    f.write(str(batch_start))
            
            # Random delay to appear more human-like
            import random
            delay = DELAY_BETWEEN_BATCHES + random.uniform(0, 1.5)
            time.sleep(delay)
    
    print(f"\n{'=' * 70}")
    print(f"TotalGlobalSports scan complete! Found {found_count} events")
    print(f"Results saved to: {TGS_OUTPUT}")
    print("=" * 70)
    
    return found_count

# ============== MAIN ==============

def print_usage():
    print("""
Tournament Platform Scanner
===========================

Usage:
    python tournament_scanner.py gotsport [start] [end]   # Scan GotSport (default: 1-99999)
    python tournament_scanner.py tgs [start] [end]        # Scan TotalGlobalSports (default: 1-9999)
    python tournament_scanner.py both                     # Scan both platforms
    python tournament_scanner.py test                     # Quick test (first 100 of each)

Examples:
    python tournament_scanner.py gotsport                 # Full GotSport scan
    python tournament_scanner.py gotsport 40000 50000     # Scan GotSport IDs 40000-49999
    python tournament_scanner.py tgs                      # Full TGS scan
    python tournament_scanner.py test                     # Quick connectivity test

Output files:
    gotsport_events.csv       - Found GotSport events
    totalglobalsports_events.csv - Found TGS events
    *_progress.txt            - Resume checkpoints
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "gotsport":
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        end = int(sys.argv[3]) if len(sys.argv) > 3 else 100000
        scan_gotsport(start, end)
        
    elif command == "tgs":
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        end = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
        scan_tgs(start, end)
        
    elif command == "both":
        scan_tgs()
        scan_gotsport()
        
    elif command == "test":
        print("Running quick test (first 100 IDs of each platform)...")
        scan_tgs(1, 101)
        scan_gotsport(1, 101)
        
    else:
        print_usage()
