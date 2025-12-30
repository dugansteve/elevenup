#!/usr/bin/env python3
"""
Find New Teams from Tournament Data

Identifies teams in tournament game data that aren't in the main database,
then searches for them on TGS or GotSport to find their team profile pages.

Usage:
    python find_new_teams.py                    # Find new teams
    python find_new_teams.py --search           # Search for new teams on platforms
    python find_new_teams.py --export new_teams.csv  # Export to CSV
"""

import csv
import os
import sys
import sqlite3
import re
import json
from datetime import datetime
from collections import defaultdict

# Configuration
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
TOURNEY_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_TEAMS_FILE = "new_teams_from_tournaments.json"

# Patterns to normalize team names for matching
def normalize_team_name(name):
    """Normalize team name for fuzzy matching"""
    if not name:
        return ""

    # Convert to lowercase
    name = name.lower().strip()

    # Remove common suffixes/prefixes
    patterns_to_remove = [
        r'\s+\d{2,4}[bg]?\s*$',  # Year suffixes like "2010G", "17B"
        r'\s+u\d{1,2}\s*$',      # Age groups like "U14"
        r'\s*-\s*(ecnl|ga|rl|npl|academy)\s*$',  # League identifiers
        r'\s+(boys?|girls?|b|g)\s*$',  # Gender suffixes
        r'\s+(red|blue|white|black|gold|silver|green|purple)\s*$',  # Color suffixes
        r'\s+(premier|elite|select|academy|competitive|rec)\s*$',  # Level suffixes
        r'\s+sc\s*$',  # Soccer Club
        r'\s+fc\s*$',  # Football Club
        r'\s+academy\s*$',
    ]

    for pattern in patterns_to_remove:
        name = re.sub(pattern, '', name, flags=re.I)

    # Normalize spaces
    name = ' '.join(name.split())

    return name


def load_db_teams():
    """Load all team names from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all team names
    cursor.execute("SELECT DISTINCT team_name FROM teams")
    teams = set()
    for row in cursor.fetchall():
        if row[0]:
            teams.add(row[0])
            teams.add(normalize_team_name(row[0]))

    # Also get club names
    cursor.execute("SELECT DISTINCT club_name FROM teams")
    clubs = set()
    for row in cursor.fetchall():
        if row[0]:
            clubs.add(row[0])
            clubs.add(normalize_team_name(row[0]))

    conn.close()

    return teams, clubs


def load_tournament_teams():
    """Load all unique teams from tournament game CSV files"""
    tourney_teams = defaultdict(lambda: {'count': 0, 'tournaments': set(), 'original_names': set()})

    # Find all tournament game CSV files
    csv_files = []
    for f in os.listdir(TOURNEY_DIR):
        if f.endswith('_games.csv') and any(x in f for x in ['gotsport_', 'tgs_', 'sincsports_']):
            csv_files.append(f)

    print(f"Found {len(csv_files)} tournament game files")

    for filename in csv_files:
        filepath = os.path.join(TOURNEY_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tourney_name = row.get('tournament_name', filename)

                    for team_field in ['home_team', 'away_team']:
                        team_name = row.get(team_field, '')
                        if team_name and len(team_name) >= 3:
                            normalized = normalize_team_name(team_name)
                            if normalized:
                                tourney_teams[normalized]['count'] += 1
                                tourney_teams[normalized]['tournaments'].add(tourney_name)
                                tourney_teams[normalized]['original_names'].add(team_name)
        except Exception as e:
            print(f"  Error reading {filename}: {e}")

    return tourney_teams


def find_new_teams():
    """Find teams in tournament data that aren't in database"""
    print("Loading database teams...")
    db_teams, db_clubs = load_db_teams()
    print(f"  {len(db_teams)} unique team names, {len(db_clubs)} club names")

    print("\nLoading tournament teams...")
    tourney_teams = load_tournament_teams()
    print(f"  {len(tourney_teams)} unique teams from tournaments")

    # Find teams not in database
    new_teams = []

    for normalized, info in tourney_teams.items():
        # Skip if in database
        if normalized in db_teams or normalized in db_clubs:
            continue

        # Skip common variations
        skip = False
        for db_team in db_teams:
            # Check if one contains the other
            if normalized in db_team or db_team in normalized:
                skip = True
                break
            # Check similar start
            if len(normalized) >= 5 and len(db_team) >= 5:
                if normalized[:5] == db_team[:5]:
                    skip = True
                    break

        if not skip:
            new_teams.append({
                'normalized_name': normalized,
                'original_names': list(info['original_names']),
                'appearances': info['count'],
                'tournaments': list(info['tournaments'])
            })

    # Sort by appearances (more common teams first)
    new_teams.sort(key=lambda x: -x['appearances'])

    print(f"\nFound {len(new_teams)} potentially new teams")

    return new_teams


def save_new_teams(teams):
    """Save new teams to JSON file"""
    filepath = os.path.join(TOURNEY_DIR, NEW_TEAMS_FILE)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'total_teams': len(teams),
            'teams': teams
        }, f, indent=2)

    print(f"Saved to {NEW_TEAMS_FILE}")


def search_team_on_gotsport(driver, team_name):
    """Search for a team on GotSport and return potential matches"""
    from selenium.webdriver.common.by import By
    import time

    search_url = f"https://system.gotsport.com/clubs/search?q={team_name.replace(' ', '+')}"

    try:
        driver.get(search_url)
        time.sleep(3)

        # Look for club links
        results = []
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()

            if '/clubs/' in href and text:
                club_id = re.search(r'/clubs/(\d+)', href)
                if club_id:
                    results.append({
                        'name': text,
                        'url': href,
                        'club_id': club_id.group(1)
                    })

        return results[:5]  # Top 5 matches
    except:
        return []


def search_team_on_tgs(driver, team_name):
    """Search for a team on TotalGlobalSports"""
    from selenium.webdriver.common.by import By
    import time

    # TGS team search
    search_url = f"https://public.totalglobalsports.com/clubs?q={team_name.replace(' ', '+')}"

    try:
        driver.get(search_url)
        time.sleep(3)

        results = []
        # Look for team/club links
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()

            if ('/club/' in href or '/team/' in href) and text:
                results.append({
                    'name': text,
                    'url': href
                })

        return results[:5]
    except:
        return []


def search_for_teams(new_teams, limit=20):
    """Search for new teams on platforms"""
    from gotsport_game_scraper_final import setup_driver
    import time
    import random

    print(f"\nSearching for top {limit} new teams on platforms...")

    driver = setup_driver(visible=False)
    found_teams = []

    try:
        for i, team in enumerate(new_teams[:limit]):
            original = team['original_names'][0] if team['original_names'] else team['normalized_name']
            print(f"\n[{i+1}/{limit}] Searching: {original}")

            # Search GotSport
            gs_results = search_team_on_gotsport(driver, team['normalized_name'])
            if gs_results:
                print(f"  GotSport: Found {len(gs_results)} matches")
                for r in gs_results[:2]:
                    print(f"    - {r['name']}: {r['url']}")
                team['gotsport_matches'] = gs_results

            # Wait between searches
            time.sleep(random.uniform(2, 4))

            # Search TGS
            tgs_results = search_team_on_tgs(driver, team['normalized_name'])
            if tgs_results:
                print(f"  TGS: Found {len(tgs_results)} matches")
                team['tgs_matches'] = tgs_results

            found_teams.append(team)

            # Delay between teams
            time.sleep(random.uniform(3, 6))

    finally:
        driver.quit()

    return found_teams


def export_to_csv(teams, filename="new_teams_export.csv"):
    """Export new teams to CSV"""
    filepath = os.path.join(TOURNEY_DIR, filename)

    fieldnames = ['normalized_name', 'original_names', 'appearances', 'tournaments', 'gotsport_url', 'tgs_url']

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for team in teams:
            row = {
                'normalized_name': team['normalized_name'],
                'original_names': '; '.join(team['original_names']),
                'appearances': team['appearances'],
                'tournaments': '; '.join(team['tournaments']),
                'gotsport_url': team.get('gotsport_matches', [{}])[0].get('url', '') if team.get('gotsport_matches') else '',
                'tgs_url': team.get('tgs_matches', [{}])[0].get('url', '') if team.get('tgs_matches') else ''
            }
            writer.writerow(row)

    print(f"Exported to {filename}")


def main():
    args = sys.argv[1:]

    do_search = '--search' in args
    export_file = None

    for i, arg in enumerate(args):
        if arg == '--export' and i + 1 < len(args):
            export_file = args[i + 1]

    # Find new teams
    new_teams = find_new_teams()

    # Show top teams
    print("\nTop 20 potentially new teams:")
    for i, team in enumerate(new_teams[:20]):
        names = ', '.join(list(team['original_names'])[:2])
        print(f"  {i+1}. {names} ({team['appearances']} appearances)")

    # Save to JSON
    save_new_teams(new_teams)

    # Search if requested
    if do_search:
        new_teams = search_for_teams(new_teams, limit=20)
        save_new_teams(new_teams)

    # Export if requested
    if export_file:
        export_to_csv(new_teams, export_file)


if __name__ == "__main__":
    main()
