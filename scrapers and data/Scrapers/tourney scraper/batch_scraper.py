#!/usr/bin/env python3
"""
Tournament Batch Scraper

Scrapes multiple tournaments sequentially, one platform at a time.
- Only one GotSport tournament runs at a time
- Only one TGS tournament runs at a time
- Human-like delays between tournaments (30-60 seconds)
- Saves progress and can resume
- Skips already-scraped tournaments

Usage:
    python batch_scraper.py                    # Scrape all pending tournaments
    python batch_scraper.py --platform gotsport # Only GotSport
    python batch_scraper.py --platform tgs      # Only TotalGlobalSports
    python batch_scraper.py --limit 5           # Only first 5 per platform
    python batch_scraper.py --resume            # Resume from last position
    python batch_scraper.py --status            # Show scraping status

Requirements:
    pip install selenium webdriver-manager beautifulsoup4
"""

import csv
import json
import time
import random
import sys
import os
from datetime import datetime

# Configuration
TOURNAMENT_FILE = "tournament_urls_v2.csv"
PROGRESS_FILE = "batch_progress.json"
MASTER_OUTPUT = "tournament_games_master.csv"

# Delays between tournaments (seconds) - be polite to servers
MIN_TOURNAMENT_DELAY = 30
MAX_TOURNAMENT_DELAY = 60

# Delays between platforms when switching
PLATFORM_SWITCH_DELAY = 10


def load_tournaments(filepath=None):
    """Load tournaments from CSV"""
    filepath = filepath or TOURNAMENT_FILE
    tournaments = []

    if not os.path.exists(filepath):
        print(f"Tournament file not found: {filepath}")
        return tournaments

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only include tournaments with schedule URLs and event IDs
            if row.get('schedule_url') and row.get('event_id') and row.get('status') == 'found':
                tournaments.append(row)

    return tournaments


def load_progress():
    """Load scraping progress from JSON"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'scraped': {},  # event_id -> {games, scraped_at, status}
        'last_platform': None,
        'last_event_id': None
    }


def save_progress(progress):
    """Save scraping progress to JSON"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def is_already_scraped(event_id, progress):
    """Check if tournament was already scraped"""
    return event_id in progress.get('scraped', {})


def get_output_file(platform, event_id):
    """Get the output CSV filename for a tournament"""
    return f"{platform}_{event_id}_games.csv"


def count_games_in_file(filepath):
    """Count games in a CSV file"""
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f) - 1  # Subtract header


def scrape_gotsport(event_id, event_name):
    """Scrape a GotSport tournament"""
    from gotsport_game_scraper_final import setup_driver, scrape_event

    print(f"\n{'='*60}")
    print(f"Scraping GotSport: {event_name}")
    print(f"Event ID: {event_id}")
    print(f"{'='*60}")

    driver = setup_driver(visible=False)

    try:
        games, event_info = scrape_event(driver, event_id, visible=False)
        return {
            'success': True,
            'games': len(games),
            'event_name': event_info.get('name', event_name)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'success': False,
            'error': str(e),
            'games': 0
        }
    finally:
        driver.quit()


def scrape_tgs(event_id, event_name):
    """Scrape a TotalGlobalSports tournament"""
    from tgs_game_scraper import setup_driver, scrape_event_games

    print(f"\n{'='*60}")
    print(f"Scraping TGS: {event_name}")
    print(f"Event ID: {event_id}")
    print(f"{'='*60}")

    driver = setup_driver(visible=False)

    try:
        games, event_info = scrape_event_games(driver, event_id, visible=False)

        # Save games to file
        if games:
            output_file = get_output_file('tgs', event_id)
            save_tgs_games(games, output_file)

        return {
            'success': True,
            'games': len(games),
            'event_name': event_info.get('name', event_name)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'success': False,
            'error': str(e),
            'games': 0
        }
    finally:
        driver.quit()


def save_tgs_games(games, output_file):
    """Save TGS games to CSV"""
    if not games:
        return

    fieldnames = [
        'tournament_id', 'tournament_name', 'game_date', 'game_time',
        'home_team', 'away_team', 'home_score', 'away_score',
        'age_group', 'division', 'bracket', 'field', 'status',
        'source_url', 'scraped_at'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(games)


def scrape_sincsports(event_id, event_name):
    """Scrape a SincSports tournament"""
    from sincsports_game_scraper_final import setup_driver, scrape_event_games

    print(f"\n{'='*60}")
    print(f"Scraping SincSports: {event_name}")
    print(f"Event ID: {event_id}")
    print(f"{'='*60}")

    driver = setup_driver(visible=False)

    try:
        games, event_info = scrape_event_games(driver, event_id, visible=False)

        # Save games to file
        if games:
            output_file = get_output_file('sincsports', event_id)
            save_sincsports_games(games, output_file)

        return {
            'success': True,
            'games': len(games),
            'event_name': event_info.get('name', event_name)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'success': False,
            'error': str(e),
            'games': 0
        }
    finally:
        driver.quit()


def save_sincsports_games(games, output_file):
    """Save SincSports games to CSV"""
    if not games:
        return

    fieldnames = [
        'tournament_id', 'tournament_name', 'game_date', 'game_time',
        'home_team', 'away_team', 'home_score', 'away_score',
        'age_group', 'division', 'field', 'status',
        'source_url', 'scraped_at'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(games)


def human_delay_between_tournaments():
    """Add a random delay between tournaments"""
    delay = random.uniform(MIN_TOURNAMENT_DELAY, MAX_TOURNAMENT_DELAY)
    print(f"\n  Waiting {delay:.0f} seconds before next tournament...")
    time.sleep(delay)


def run_batch(platform_filter=None, limit=None, resume=False):
    """Run batch scraping"""
    tournaments = load_tournaments()
    progress = load_progress()

    if not tournaments:
        print("No tournaments found to scrape!")
        return

    print(f"\nLoaded {len(tournaments)} tournaments with schedule URLs")

    # Group by platform
    by_platform = {}
    for t in tournaments:
        platform = t.get('schedule_platform', '').lower()
        if platform:
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(t)

    print("\nTournaments by platform:")
    for platform, items in sorted(by_platform.items()):
        already = sum(1 for t in items if is_already_scraped(t['event_id'], progress))
        print(f"  {platform}: {len(items)} total, {already} already scraped")

    # Filter by platform if specified
    if platform_filter:
        platform_filter = platform_filter.lower()
        if platform_filter == 'tgs':
            platform_filter = 'totalglobalsports'
        by_platform = {k: v for k, v in by_platform.items() if k == platform_filter}

    # Process each platform sequentially
    total_scraped = 0
    total_games = 0

    for platform, tournaments_list in by_platform.items():
        print(f"\n{'#'*60}")
        print(f"# Processing {platform.upper()}")
        print(f"{'#'*60}")

        # Filter out already scraped
        pending = [t for t in tournaments_list if not is_already_scraped(t['event_id'], progress)]

        if limit:
            pending = pending[:limit]

        print(f"  {len(pending)} tournaments to scrape")

        for i, tournament in enumerate(pending):
            event_id = tournament['event_id']
            event_name = tournament.get('name', 'Unknown')

            print(f"\n[{i+1}/{len(pending)}] {event_name}")

            # Scrape based on platform
            if platform == 'gotsport':
                result = scrape_gotsport(event_id, event_name)
            elif platform == 'totalglobalsports':
                result = scrape_tgs(event_id, event_name)
            elif platform == 'sincsports':
                result = scrape_sincsports(event_id, event_name)
            else:
                print(f"  Skipping unknown platform: {platform}")
                continue

            # Update progress
            progress['scraped'][event_id] = {
                'platform': platform,
                'name': event_name,
                'games': result.get('games', 0),
                'success': result.get('success', False),
                'scraped_at': datetime.now().isoformat()
            }
            progress['last_platform'] = platform
            progress['last_event_id'] = event_id
            save_progress(progress)

            total_scraped += 1
            total_games += result.get('games', 0)

            print(f"  Result: {result.get('games', 0)} games")

            # Delay before next tournament (unless it's the last one)
            if i < len(pending) - 1:
                human_delay_between_tournaments()

        # Delay before switching platforms
        if platform != list(by_platform.keys())[-1]:
            print(f"\n  Switching platforms, waiting {PLATFORM_SWITCH_DELAY}s...")
            time.sleep(PLATFORM_SWITCH_DELAY)

    # Summary
    print(f"\n{'='*60}")
    print("BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"Tournaments scraped: {total_scraped}")
    print(f"Total games: {total_games}")
    print(f"Progress saved to: {PROGRESS_FILE}")


def show_status():
    """Show current scraping status"""
    progress = load_progress()
    tournaments = load_tournaments()

    print(f"\n{'='*60}")
    print("SCRAPING STATUS")
    print(f"{'='*60}")

    scraped = progress.get('scraped', {})
    print(f"\nTotal tournaments scraped: {len(scraped)}")

    if scraped:
        total_games = sum(s.get('games', 0) for s in scraped.values())
        print(f"Total games collected: {total_games}")

        # By platform
        by_platform = {}
        for event_id, info in scraped.items():
            p = info.get('platform', 'unknown')
            if p not in by_platform:
                by_platform[p] = {'count': 0, 'games': 0}
            by_platform[p]['count'] += 1
            by_platform[p]['games'] += info.get('games', 0)

        print("\nBy platform:")
        for platform, stats in sorted(by_platform.items()):
            print(f"  {platform}: {stats['count']} tournaments, {stats['games']} games")

    # Pending
    pending = [t for t in tournaments if t['event_id'] not in scraped]
    print(f"\nPending tournaments: {len(pending)}")

    # By platform
    pending_by_platform = {}
    for t in pending:
        p = t.get('schedule_platform', 'unknown')
        pending_by_platform[p] = pending_by_platform.get(p, 0) + 1

    if pending_by_platform:
        print("  By platform:")
        for platform, count in sorted(pending_by_platform.items()):
            print(f"    {platform}: {count}")


def combine_all_games():
    """Combine all scraped games into master file"""
    import glob

    print("\nCombining all game files...")

    # Find all game CSV files
    game_files = glob.glob("gotsport_*_games.csv") + \
                 glob.glob("tgs_*_games.csv") + \
                 glob.glob("sincsports_*_games.csv")

    if not game_files:
        print("No game files found!")
        return

    print(f"Found {len(game_files)} game files")

    # Read and combine
    all_games = []
    header = None

    for filepath in game_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not header:
                header = reader.fieldnames
            for row in reader:
                all_games.append(row)

    # Write master file
    with open(MASTER_OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_games)

    print(f"Created {MASTER_OUTPUT} with {len(all_games)} games")


def main():
    args = sys.argv[1:]

    # Parse arguments
    platform = None
    limit = None
    resume = False

    i = 0
    while i < len(args):
        if args[i] == '--platform' and i + 1 < len(args):
            platform = args[i + 1]
            i += 2
        elif args[i] == '--limit' and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except:
                pass
            i += 2
        elif args[i] == '--resume':
            resume = True
            i += 1
        elif args[i] == '--status':
            show_status()
            return
        elif args[i] == '--combine':
            combine_all_games()
            return
        elif args[i] in ['-h', '--help', 'help']:
            print(__doc__)
            return
        else:
            i += 1

    print("=" * 60)
    print("TOURNAMENT BATCH SCRAPER")
    print("=" * 60)
    print(f"Platform filter: {platform or 'all'}")
    print(f"Limit per platform: {limit or 'none'}")
    print(f"Resume mode: {resume}")

    run_batch(platform_filter=platform, limit=limit, resume=resume)

    # Combine all games at the end
    combine_all_games()


if __name__ == "__main__":
    main()
