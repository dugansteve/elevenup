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

# Request settings
TIMEOUT = 10
CONCURRENT_REQUESTS = 20
DELAY_BETWEEN_BATCHES = 0.5

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
        
        # Skip error pages
        if "Page Not Found" in html or len(html) < 1000:
            return None
        if "No event found" in html or "does not exist" in html.lower():
            return None
            
        # Extract event name
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        name = title_match.group(1).strip() if title_match else ""
        name = name.replace(" | GotSport", "").replace(" - GotSport", "").strip()
        
        if not name or name.lower() in ['gotsport', 'error', 'not found']:
            return None
        
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
        fieldnames = ['event_id', 'name', 'dates', 'url', 'found_at']
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
                        print(f"  ✓ {result['event_id']:5d}: {result['name'][:60]}")
            
            # Progress update
            if batch_start % 1000 == 0:
                print(f"\n[Progress] Checked {batch_start:,}/{end_at-1:,} | Found: {found_count}\n")
                with open(GOTSPORT_PROGRESS, 'w') as f:
                    f.write(str(batch_start))
            
            time.sleep(DELAY_BETWEEN_BATCHES)
    
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
            
            time.sleep(DELAY_BETWEEN_BATCHES)
    
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
