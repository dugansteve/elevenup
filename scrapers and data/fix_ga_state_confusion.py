#!/usr/bin/env python3
"""
Fix GA (Georgia) / GA (Girls Academy) State Confusion

This script fixes a recurring issue where Girls Academy teams get incorrectly
assigned "Georgia" as their state because:
1. Scrapers used 'GA ' as a pattern to detect Georgia state
2. Girls Academy teams often have ' GA' suffix in their names (league indicator)
3. This causes teams from California, Texas, etc. to be mapped to Georgia

This script:
1. Identifies teams in the database with incorrect Georgia state
2. Clears the state field for non-Georgia teams
3. Updates club_addresses.json to remove incorrect entries
4. Logs all changes for review

Usage:
    python fix_ga_state_confusion.py --dry-run  # Preview changes
    python fix_ga_state_confusion.py            # Apply changes
"""

import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime

# Known Georgia clubs - teams from these clubs should keep their Georgia state
GEORGIA_CLUBS = [
    'tophat',
    'concorde fire',
    'gwinnett',
    'southern soccer',
    'ssa swarm',
    'nasa tophat',
    'nth tophat',
    'nth-nasa',
    'nth nasa',
    'atlanta fire',
    'atlanta united',
    'inter atlanta',
    'united futbol academy',
    'ufa ',
    'georgia',
    'legion futbol',
    'legion fc',
    'peach',
    'afc lightning',
    'all-in fc',
    'alliance sc',
    'athens united',
    'auburn soccer',
    'chargers soccer',
    'decatur',
    'eastshore',
    'fayetteville',
    'villarreal force',
    'north georgia',
    'roswell santos',
    'rush union',
    'springs soccer',
    'steamers fc',
    'triumph youth',
    'ymca arsenal rome',
    'metro atlanta',
    'lanier soccer',
    'pike soccer',
    'fury fc',
    'brevard',
    'gsa force',
    'winnett soccer',
]

def is_georgia_club(team_name: str) -> bool:
    """Check if team is from a known Georgia club."""
    name_lower = team_name.lower()
    return any(club in name_lower for club in GEORGIA_CLUBS)

def has_ga_league_suffix(team_name: str) -> bool:
    """Check if team name has ' GA' suffix indicating Girls Academy league."""
    name_upper = team_name.upper().strip()
    # Matches patterns like "12G GA", "13G GA", " GA" at end
    return name_upper.endswith(' GA') or ' GA ' in name_upper

def main():
    parser = argparse.ArgumentParser(description='Fix GA/Georgia state confusion')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying them')
    parser.add_argument('--db', type=str, default=None,
                        help='Path to database file')
    args = parser.parse_args()

    # Find database
    script_dir = Path(__file__).parent
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = script_dir / 'seedlinedata.db'

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    # Find club_addresses.json
    addresses_path = script_dir.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'

    print("=" * 70)
    print("GA (Georgia) / GA (Girls Academy) State Confusion Fixer")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")
    print(f"Addresses: {addresses_path}")
    print(f"Mode: {'DRY RUN (no changes will be made)' if args.dry_run else 'LIVE'}")
    print()

    # Connect to database with timeout
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()

    # Find teams with Georgia state and GA league suffix
    cursor.execute("""
        SELECT team_name, club_name, state, league
        FROM teams
        WHERE (state = 'Georgia' OR state = 'GA')
    """)

    teams_to_fix = []
    teams_correct = []

    for row in cursor.fetchall():
        team_name, club_name, state, league = row

        if not team_name:
            continue

        # Check if this is a false positive (GA league suffix, not Georgia club)
        if has_ga_league_suffix(team_name) and not is_georgia_club(team_name):
            teams_to_fix.append({
                'team_name': team_name,
                'club_name': club_name,
                'state': state,
                'league': league,
                'reason': f"Has ' GA' suffix but not a Georgia club"
            })
        elif is_georgia_club(team_name):
            teams_correct.append({
                'team_name': team_name,
                'club_name': club_name,
                'state': state,
                'league': league
            })

    print(f"Found {len(teams_to_fix)} teams with incorrect Georgia state")
    print(f"Found {len(teams_correct)} teams with correct Georgia state")
    print()

    if teams_to_fix:
        print("Teams to fix (will clear state):")
        print("-" * 70)
        for i, team in enumerate(teams_to_fix[:20], 1):
            print(f"  {i}. {team['team_name'][:50]}")
            print(f"      Club: {team['club_name']}, League: {team['league']}")
            print(f"      Reason: {team['reason']}")
        if len(teams_to_fix) > 20:
            print(f"  ... and {len(teams_to_fix) - 20} more")
        print()

    # Apply database fixes
    if not args.dry_run and teams_to_fix:
        print("Fixing database entries...")
        fixed_count = 0
        try:
            for team in teams_to_fix:
                cursor.execute("""
                    UPDATE teams
                    SET state = NULL
                    WHERE team_name = ? AND (state = 'Georgia' OR state = 'GA')
                """, (team['team_name'],))
                fixed_count += cursor.rowcount

            conn.commit()
            print(f"  Fixed {fixed_count} database entries")
        except sqlite3.OperationalError as e:
            print(f"  WARNING: Could not update database - {e}")
            print(f"  Database may be locked by another process (e.g., Dropbox sync)")
            print(f"  The club_addresses.json will still be fixed.")

    conn.close()

    # Fix club_addresses.json
    if addresses_path.exists():
        print("\nProcessing club_addresses.json...")
        with open(addresses_path, 'r') as f:
            addresses = json.load(f)

        clubs = addresses.get('clubs', {})
        teams = addresses.get('teams', {})

        clubs_to_fix = []
        teams_to_fix_json = []

        # Check clubs
        for name, info in clubs.items():
            state = info.get('state', '')
            if state in ('GA', 'Georgia'):
                if has_ga_league_suffix(name) and not is_georgia_club(name):
                    clubs_to_fix.append(name)

        # Check teams
        for name, info in teams.items():
            state = info.get('state', '')
            if state in ('GA', 'Georgia'):
                if has_ga_league_suffix(name) and not is_georgia_club(name):
                    teams_to_fix_json.append(name)

        print(f"  Clubs with incorrect GA state: {len(clubs_to_fix)}")
        print(f"  Teams with incorrect GA state: {len(teams_to_fix_json)}")

        if clubs_to_fix:
            print("\n  Sample clubs to fix:")
            for name in clubs_to_fix[:10]:
                print(f"    - {name}")
            if len(clubs_to_fix) > 10:
                print(f"    ... and {len(clubs_to_fix) - 10} more")

        if not args.dry_run and (clubs_to_fix or teams_to_fix_json):
            # Clear state for incorrect entries
            for name in clubs_to_fix:
                clubs[name]['state'] = ''
            for name in teams_to_fix_json:
                teams[name]['state'] = ''

            # Save updated file
            with open(addresses_path, 'w') as f:
                json.dump(addresses, f, indent=2)

            print(f"\n  Updated club_addresses.json")
            print(f"    Clubs fixed: {len(clubs_to_fix)}")
            print(f"    Teams fixed: {len(teams_to_fix_json)}")

    print("\n" + "=" * 70)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print("Run without --dry-run to apply changes")
    else:
        print("COMPLETE - Changes applied")
        print("\nNext steps:")
        print("  1. Run the ranker to regenerate rankings_for_react.json")
        print("  2. Run export_club_addresses.py to refresh addresses")
        print("  3. Deploy updated files to the app")
    print("=" * 70)

if __name__ == '__main__':
    main()
