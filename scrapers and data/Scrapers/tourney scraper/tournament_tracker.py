#!/usr/bin/env python3
"""
Tournament Tracker - Master Coordinator

Coordinates tournament discovery and game scraping across multiple platforms:
- GotSport (system.gotsport.com)
- TotalGlobalSports (public.totalglobalsports.com)
- SincSports (soccer.sincsports.com)
- Athletes2Events (sts.athletes2events.com)

Features:
- Loads tournaments from tournament_urls_v2.csv
- Scrapes game data from each platform
- Tracks which tournaments have been scraped
- Re-checks tournaments for new schedules periodically
- Consolidates all games into a master database

Usage:
    python tournament_tracker.py scrape              # Scrape all pending tournaments
    python tournament_tracker.py scrape --platform gotsport  # Only GotSport
    python tournament_tracker.py recheck             # Re-check tournaments without schedules
    python tournament_tracker.py status              # Show scraping status
    python tournament_tracker.py export              # Export all games to CSV

Requirements:
    pip install selenium webdriver-manager
"""

import csv
import json
import time
import re
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Import platform-specific scrapers
try:
    from gotsport_game_scraper_final import setup_driver, scrape_event_games as scrape_gotsport
except ImportError:
    scrape_gotsport = None

try:
    from tgs_game_scraper import scrape_event_games as scrape_tgs
except ImportError:
    scrape_tgs = None

try:
    from sincsports_game_scraper_final import scrape_event_games as scrape_sincsports
except ImportError:
    scrape_sincsports = None


# Configuration
TOURNAMENT_FILE = "tournament_urls_v2.csv"
MASTER_GAMES_FILE = "tournament_games_master.csv"
SCRAPE_STATUS_FILE = "tournament_scrape_status.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_tournaments(filepath=None):
    """Load tournaments from CSV"""
    filepath = filepath or os.path.join(SCRIPT_DIR, TOURNAMENT_FILE)
    tournaments = []

    if not os.path.exists(filepath):
        print(f"Tournament file not found: {filepath}")
        return tournaments

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tournaments.append(row)

    return tournaments


def load_scrape_status():
    """Load scrape status from JSON"""
    filepath = os.path.join(SCRIPT_DIR, SCRAPE_STATUS_FILE)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}


def save_scrape_status(status):
    """Save scrape status to JSON"""
    filepath = os.path.join(SCRIPT_DIR, SCRAPE_STATUS_FILE)
    with open(filepath, 'w') as f:
        json.dump(status, f, indent=2)


def get_platform_scraper(platform):
    """Get the appropriate scraper function for a platform"""
    scrapers = {
        'gotsport': scrape_gotsport,
        'totalglobalsports': scrape_tgs,
        'sincsports': scrape_sincsports,
    }
    return scrapers.get(platform.lower())


def scrape_tournament(driver, tournament, visible=False):
    """Scrape games from a single tournament"""
    platform = tournament.get('schedule_platform', '').lower()
    event_id = tournament.get('event_id', '')
    name = tournament.get('name', 'Unknown')

    if not platform or not event_id:
        return [], {'error': 'missing_platform_or_id'}

    scraper = get_platform_scraper(platform)
    if not scraper:
        return [], {'error': f'no_scraper_for_{platform}'}

    try:
        games, event_info = scraper(driver, event_id, visible)
        return games, {
            'success': True,
            'game_count': len(games),
            'event_name': event_info.get('name', name),
            'scraped_at': datetime.now().isoformat()
        }
    except Exception as e:
        return [], {'error': str(e)}


def scrape_all_tournaments(platform_filter=None, visible=False, limit=None):
    """Scrape games from all tournaments"""
    tournaments = load_tournaments()
    status = load_scrape_status()

    if not tournaments:
        print("No tournaments loaded!")
        return

    # Filter to tournaments with schedule URLs
    scrapeable = [t for t in tournaments if t.get('schedule_url') and t.get('event_id')]

    if platform_filter:
        scrapeable = [t for t in scrapeable if t.get('schedule_platform', '').lower() == platform_filter.lower()]

    print(f"\nFound {len(scrapeable)} tournaments to scrape")
    if platform_filter:
        print(f"(filtered to {platform_filter})")

    if limit:
        scrapeable = scrapeable[:limit]
        print(f"(limited to {limit})")

    # Setup driver
    try:
        from gotsport_game_scraper_final import setup_driver
    except ImportError:
        from tgs_game_scraper import setup_driver

    driver = setup_driver(visible=visible)
    all_games = []

    try:
        for i, tournament in enumerate(scrapeable):
            name = tournament.get('name', 'Unknown')
            platform = tournament.get('schedule_platform', '')
            event_id = tournament.get('event_id', '')

            print(f"\n[{i+1}/{len(scrapeable)}] {name}")
            print(f"  Platform: {platform}, ID: {event_id}")

            # Check if already scraped recently
            key = f"{platform}_{event_id}"
            if key in status:
                last_scraped = status[key].get('scraped_at', '')
                if last_scraped:
                    try:
                        last_dt = datetime.fromisoformat(last_scraped)
                        if datetime.now() - last_dt < timedelta(hours=24):
                            print(f"  Skipped (scraped within 24h)")
                            continue
                    except:
                        pass

            # Scrape
            games, result = scrape_tournament(driver, tournament, visible)

            if games:
                all_games.extend(games)
                print(f"  Found {len(games)} games")
            else:
                print(f"  No games found: {result}")

            # Update status
            status[key] = result
            save_scrape_status(status)

            # Small delay between tournaments
            time.sleep(2)

    finally:
        driver.quit()

    # Save all games
    if all_games:
        save_master_games(all_games)

    print(f"\n{'='*70}")
    print(f"COMPLETE")
    print(f"{'='*70}")
    print(f"Tournaments scraped: {len(scrapeable)}")
    print(f"Total games: {len(all_games)}")

    return all_games


def save_master_games(games, append=True):
    """Save games to master CSV"""
    filepath = os.path.join(SCRIPT_DIR, MASTER_GAMES_FILE)

    fieldnames = [
        'tournament_id', 'tournament_name', 'game_date', 'game_time',
        'home_team', 'away_team', 'home_score', 'away_score',
        'age_group', 'division', 'bracket', 'field', 'status',
        'platform', 'source_url', 'scraped_at'
    ]

    file_exists = os.path.exists(filepath)
    mode = 'a' if append and file_exists else 'w'

    # Ensure all games have required fields
    for game in games:
        for field in fieldnames:
            if field not in game:
                game[field] = ''

    with open(filepath, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if mode == 'w':
            writer.writeheader()
        writer.writerows(games)

    print(f"Saved {len(games)} games to {MASTER_GAMES_FILE}")


def recheck_pending_tournaments(visible=False):
    """Re-check tournaments that didn't have schedules"""
    tournaments = load_tournaments()

    # Find tournaments with pending status or no schedule URL
    pending = [t for t in tournaments if t.get('status', '').lower() == 'pending']

    print(f"\nFound {len(pending)} pending tournaments to re-check")

    # For each pending tournament, try to find their schedule URL
    # This would require visiting their website and looking for schedule links

    # For now, just list them
    for t in pending[:20]:
        print(f"  - {t.get('name', 'Unknown')}: {t.get('website_url', 'no URL')}")

    if len(pending) > 20:
        print(f"  ... and {len(pending) - 20} more")

    return pending


def show_status():
    """Show scraping status summary"""
    tournaments = load_tournaments()
    status = load_scrape_status()

    print("\n" + "=" * 70)
    print("TOURNAMENT SCRAPING STATUS")
    print("=" * 70)

    # Count by platform
    by_platform = defaultdict(int)
    for t in tournaments:
        platform = t.get('schedule_platform', 'unknown') or 'unknown'
        by_platform[platform] += 1

    print("\nTournaments by platform:")
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"  {platform}: {count}")

    # Count by status
    by_status = defaultdict(int)
    for t in tournaments:
        s = t.get('status', 'unknown') or 'unknown'
        by_status[s] += 1

    print("\nTournaments by status:")
    for s, count in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  {s}: {count}")

    # Scrape results
    print(f"\nScrape history: {len(status)} tournaments attempted")

    success_count = sum(1 for s in status.values() if s.get('success'))
    error_count = sum(1 for s in status.values() if s.get('error'))

    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")

    # Total games
    total_games = sum(s.get('game_count', 0) for s in status.values())
    print(f"\nTotal games scraped: {total_games}")


def export_games():
    """Export all games from status to CSV"""
    filepath = os.path.join(SCRIPT_DIR, MASTER_GAMES_FILE)

    if os.path.exists(filepath):
        # Count rows
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = sum(1 for _ in reader) - 1  # Subtract header

        print(f"\nMaster games file: {filepath}")
        print(f"Total games: {rows}")
    else:
        print(f"\nNo master games file found at {filepath}")
        print("Run 'python tournament_tracker.py scrape' first")


def find_tournament_urls():
    """Find schedule URLs for pending tournaments by visiting their websites"""
    tournaments = load_tournaments()
    pending = [t for t in tournaments if t.get('status', '').lower() == 'pending']

    if not pending:
        print("No pending tournaments to process")
        return

    print(f"\nSearching for schedule URLs for {len(pending)} pending tournaments...")

    try:
        from gotsport_game_scraper_final import setup_driver
    except ImportError:
        from tgs_game_scraper import setup_driver

    driver = setup_driver(visible=False)
    found_count = 0

    try:
        for tournament in pending[:50]:  # Limit to 50 at a time
            name = tournament.get('name', 'Unknown')
            website = tournament.get('website_url', '')

            if not website:
                continue

            print(f"\nChecking: {name}")
            print(f"  URL: {website}")

            try:
                driver.get(website)
                time.sleep(3)

                # Look for schedule-related links
                links = driver.find_elements(By.TAG_NAME, "a")
                schedule_keywords = ['schedule', 'bracket', 'result', 'standings', 'gotsport', 'totalglobalsports', 'sincsports']

                for link in links:
                    href = link.get_attribute("href") or ""
                    text = link.text.lower()

                    if any(kw in href.lower() or kw in text for kw in schedule_keywords):
                        # Check if this is a platform URL
                        if 'gotsport.com' in href:
                            match = re.search(r'/events?/(\w+)', href)
                            if match:
                                print(f"  Found GotSport: {href}")
                                tournament['schedule_url'] = href
                                tournament['schedule_platform'] = 'gotsport'
                                tournament['event_id'] = match.group(1)
                                tournament['status'] = 'found'
                                found_count += 1
                                break

                        elif 'totalglobalsports.com' in href:
                            match = re.search(r'/event/(\d+)', href)
                            if match:
                                print(f"  Found TGS: {href}")
                                tournament['schedule_url'] = href
                                tournament['schedule_platform'] = 'totalglobalsports'
                                tournament['event_id'] = match.group(1)
                                tournament['status'] = 'found'
                                found_count += 1
                                break

                        elif 'sincsports.com' in href:
                            match = re.search(r'tid=(\w+)', href)
                            if match:
                                print(f"  Found SincSports: {href}")
                                tournament['schedule_url'] = href
                                tournament['schedule_platform'] = 'sincsports'
                                tournament['event_id'] = match.group(1)
                                tournament['status'] = 'found'
                                found_count += 1
                                break

            except Exception as e:
                print(f"  Error: {e}")

            time.sleep(1)

    finally:
        driver.quit()

    print(f"\n{'='*70}")
    print(f"Found schedule URLs for {found_count} tournaments")

    # Optionally save updated tournament list
    if found_count > 0:
        save_tournaments(tournaments)


def save_tournaments(tournaments, filepath=None):
    """Save tournaments back to CSV"""
    filepath = filepath or os.path.join(SCRIPT_DIR, TOURNAMENT_FILE)

    fieldnames = [
        'name', 'dates', 'state', 'club', 'age_groups',
        'website_url', 'schedule_url', 'schedule_platform',
        'event_id', 'status', 'notes'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(tournaments)

    print(f"Saved {len(tournaments)} tournaments to {filepath}")


def print_help():
    print(__doc__)
    print("""
Commands:
    scrape              Scrape games from all tournaments with schedule URLs
    scrape --platform X Scrape only from platform X (gotsport, totalglobalsports, sincsports)
    scrape --limit N    Only scrape first N tournaments
    scrape --visible    Show browser window

    recheck             List tournaments without schedule URLs
    find-urls           Visit pending tournament websites to find schedule URLs

    status              Show scraping status summary
    export              Show master games file info

Examples:
    python tournament_tracker.py scrape --platform gotsport --limit 10
    python tournament_tracker.py status
    python tournament_tracker.py find-urls
""")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ['-h', '--help', 'help']:
        print_help()
        return

    command = args[0].lower()
    visible = '--visible' in args
    args = [a for a in args if a != '--visible']

    # Parse --platform
    platform = None
    for i, a in enumerate(args):
        if a == '--platform' and i + 1 < len(args):
            platform = args[i + 1]
            break

    # Parse --limit
    limit = None
    for i, a in enumerate(args):
        if a == '--limit' and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except:
                pass
            break

    if command == 'scrape':
        scrape_all_tournaments(platform_filter=platform, visible=visible, limit=limit)

    elif command == 'recheck':
        recheck_pending_tournaments(visible=visible)

    elif command == 'find-urls':
        find_tournament_urls()

    elif command == 'status':
        show_status()

    elif command == 'export':
        export_games()

    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    main()
