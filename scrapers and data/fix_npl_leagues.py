#!/usr/bin/env python3
"""
NPL League/Conference/Region Fix Script
========================================
Fixes league, conference, and region fields for NPL teams and games.

Problem: NPL regional leagues are stored in the league field
         (e.g., "SOCAL NPL", "NorCal NPL") instead of being properly organized

Solution:
- league = "NPL" for all NPL teams/games
- conference = geographic region (Midwest, Southwest, West, etc.)
- region = full regional league name (e.g., "SOCAL NPL", "Great Lakes Alliance NPL")

This script:
- Adds 'region' column if it doesn't exist
- Creates a backup before making changes
- Shows preview of changes before applying
- Updates both games and teams tables

Usage:
  python fix_npl_leagues.py                    # Interactive mode
  python fix_npl_leagues.py --dry-run          # Preview only, no changes
  python fix_npl_leagues.py --yes              # Skip confirmation
"""

import sqlite3
import shutil
import argparse
import os
from datetime import datetime
from pathlib import Path


def find_database():
    """Find seedlinedata.db in common locations."""
    search_paths = [
        Path.cwd() / "seedlinedata.db",
        Path(__file__).parent / "seedlinedata.db",
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"),
    ]

    for path in search_paths:
        if path.exists():
            return str(path.resolve())
    return None


def create_backup(db_path):
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f"_backup_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


# Mapping of current league names to conference (geographic region)
LEAGUE_TO_CONFERENCE = {
    'SOCAL NPL': 'Southwest',
    'NorCal NPL': 'West',
    'Central States NPL': 'Midwest',
    'FCL NPL (Florida)': 'Southeast',
    'Great Lakes Alliance NPL': 'Midwest',
    'VPSL NPL (Virginia)': 'Mid-Atlantic',
    'NISL NPL (Northern Illinois)': 'Midwest',
    'Mountain West NPL': 'Mountain',
    'Minnesota NPL': 'Midwest',
    'Red River NPL': 'Central',
    'CPSL NPL (Chesapeake)': 'Mid-Atlantic',
    'MDL NPL (Midwest Developmental)': 'Midwest',
    'WPL NPL U11-U14 Fall': 'Northwest',
    'WPL NPL Boys Fall HS': 'Northwest',
    'WPL NPL Girls HS': 'Northwest',
    'Frontier Premier League': 'Mountain',
}


def get_npl_leagues_sql():
    """Return SQL to identify NPL leagues."""
    return """(
        league LIKE '%NPL%'
        OR league LIKE '%SOCAL%'
        OR league LIKE '%NorCal%'
        OR league LIKE '%Frontier Premier%'
    )"""


def add_region_column(db_path):
    """Add region column to teams and games tables if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if region column exists in teams
    cur.execute("PRAGMA table_info(teams)")
    teams_columns = [row[1] for row in cur.fetchall()]

    # Check if region column exists in games
    cur.execute("PRAGMA table_info(games)")
    games_columns = [row[1] for row in cur.fetchall()]

    teams_added = False
    games_added = False

    if 'region' not in teams_columns:
        cur.execute("ALTER TABLE teams ADD COLUMN region TEXT")
        teams_added = True

    if 'region' not in games_columns:
        cur.execute("ALTER TABLE games ADD COLUMN region TEXT")
        games_added = True

    conn.commit()
    conn.close()

    return teams_added, games_added


def preview_changes(db_path):
    """Preview what changes would be made."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    npl_filter = get_npl_leagues_sql()

    # Count teams to fix by current league
    cur.execute(f"""
        SELECT league, conference, COUNT(*)
        FROM teams
        WHERE {npl_filter}
        GROUP BY league, conference
        ORDER BY COUNT(*) DESC
    """)
    teams_by_league = cur.fetchall()

    # Count games to fix
    cur.execute(f"""
        SELECT league, conference, COUNT(*)
        FROM games
        WHERE {npl_filter}
        GROUP BY league, conference
        ORDER BY COUNT(*) DESC
    """)
    games_by_league = cur.fetchall()

    total_teams = sum(count for _, _, count in teams_by_league)
    total_games = sum(count for _, _, count in games_by_league)

    conn.close()
    return teams_by_league, games_by_league, total_teams, total_games


def apply_fixes(db_path):
    """Apply the league/conference/region fixes to the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    teams_fixed = 0
    games_fixed = 0

    for old_league, new_conference in LEAGUE_TO_CONFERENCE.items():
        # Fix teams: set region to old league name, league to NPL, conference to geographic region
        cur.execute(
            "UPDATE teams SET region = ?, league = 'NPL', conference = ? WHERE league = ?",
            (old_league, new_conference, old_league)
        )
        teams_fixed += cur.rowcount

        # Fix games: same treatment
        cur.execute(
            "UPDATE games SET region = ?, league = 'NPL', conference = ? WHERE league = ?",
            (old_league, new_conference, old_league)
        )
        games_fixed += cur.rowcount

    conn.commit()
    conn.close()

    return teams_fixed, games_fixed


def show_current_state(db_path):
    """Show current league distribution."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT league, conference, COUNT(*) as count
        FROM teams
        WHERE league LIKE '%NPL%' OR league = 'NPL' OR league LIKE '%SOCAL%' OR league LIKE '%NorCal%'
        GROUP BY league, conference
        ORDER BY count DESC
        LIMIT 15
    """)
    results = cur.fetchall()
    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description='Fix NPL league/conference/region fields')
    parser.add_argument('--db', type=str, help='Path to seedlinedata.db')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')

    args = parser.parse_args()

    print("=" * 70)
    print("  NPL LEAGUE/CONFERENCE/REGION FIX SCRIPT")
    print("  Organizes: league='NPL', conference=geographic, region=full name")
    print("=" * 70)
    print()

    # Find database
    db_path = args.db or find_database()

    if not db_path or not os.path.exists(db_path):
        print("ERROR: Could not find seedlinedata.db")
        return 1

    print(f"Database: {db_path}")
    print()

    # Show current state
    print("CURRENT STATE:")
    print("-" * 70)
    print(f"{'League':<35} | {'Conference':<15} | {'Teams':>6}")
    print("-" * 70)
    state = show_current_state(db_path)
    for league, conf, count in state:
        conf_str = conf if conf else '(empty)'
        print(f"{league:<35} | {conf_str:<15} | {count:>6}")
    print()

    # Preview changes
    print("ANALYZING CHANGES...")
    print("-" * 70)
    teams_by_league, games_by_league, total_teams, total_games = preview_changes(db_path)

    print(f"  Teams to update: {total_teams:,}")
    print(f"  Games to update: {total_games:,}")
    print()

    print("MAPPING (current league -> new structure):")
    print("-" * 70)
    print(f"{'Current League':<35} | {'New Conf':<12} | Region")
    print("-" * 70)
    for old_league, new_conf in LEAGUE_TO_CONFERENCE.items():
        print(f"{old_league:<35} | {new_conf:<12} | {old_league}")
    print()
    print("  (All will have league='NPL')")
    print()

    if total_teams == 0 and total_games == 0:
        print("OK: No changes needed!")
        return 0

    if args.dry_run:
        print("DRY RUN - No changes made")
        return 0

    # Confirm
    if not args.yes:
        print("WARNING: This will modify the database.")
        response = input("   Proceed? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("Cancelled")
            return 1

    # Create backup
    if not args.no_backup:
        print()
        print("CREATING BACKUP...")
        backup_path = create_backup(db_path)
        print(f"  Backup: {backup_path}")

    # Add region column if needed
    print()
    print("ADDING REGION COLUMN...")
    teams_added, games_added = add_region_column(db_path)
    if teams_added:
        print("  Added 'region' column to teams table")
    else:
        print("  'region' column already exists in teams table")
    if games_added:
        print("  Added 'region' column to games table")
    else:
        print("  'region' column already exists in games table")

    # Apply fixes
    print()
    print("APPLYING FIXES...")
    teams_fixed, games_fixed = apply_fixes(db_path)

    print(f"  Teams fixed: {teams_fixed:,}")
    print(f"  Games fixed: {games_fixed:,}")
    print()

    # Show new state
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("NEW STATE - NPL Teams by Conference:")
    print("-" * 50)
    cur.execute("""
        SELECT conference, COUNT(*)
        FROM teams
        WHERE league = 'NPL'
        GROUP BY conference
        ORDER BY COUNT(*) DESC
    """)
    for conf, count in cur.fetchall():
        print(f"  {count:6} teams | {conf}")

    print()
    print("NEW STATE - NPL Teams by Region:")
    print("-" * 50)
    cur.execute("""
        SELECT region, COUNT(*)
        FROM teams
        WHERE league = 'NPL'
        GROUP BY region
        ORDER BY COUNT(*) DESC
    """)
    for region, count in cur.fetchall():
        print(f"  {count:6} teams | {region}")

    conn.close()
    print()

    print("=" * 70)
    print("  COMPLETE!")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    exit(main())
