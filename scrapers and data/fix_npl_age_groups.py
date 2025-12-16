#!/usr/bin/env python3
"""
NPL Age Group Fix Script
========================
Fixes age group formatting in seedlinedata.db for NPL leagues.

Problem: NPL games were stored with graduation year format (G30, G31, G36)
         instead of U-age format (G12, G13, G17).

Solution: Convert graduation year to U-age format.
         G30 (grad 2030) → birth year 2012 → age 13 → G13

This script:
- Only affects NPL leagues (Central States NPL, FCL NPL, CPSL NPL, Frontier, etc.)
- Creates a backup before making changes
- Shows preview of changes before applying
- Updates both games and teams tables
- Does NOT modify any other data

Usage:
  python fix_npl_age_groups.py                    # Interactive mode
  python fix_npl_age_groups.py --db path/to/db   # Specify database path
  python fix_npl_age_groups.py --dry-run         # Preview only, no changes
  python fix_npl_age_groups.py --no-backup       # Skip backup (not recommended)

Author: Claude
Version: 1.0
"""

import sqlite3
import shutil
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional


def find_database() -> Optional[str]:
    """Find seedlinedata.db in common locations."""
    search_paths = [
        Path.cwd() / "seedlinedata.db",
        Path.cwd().parent / "seedlinedata.db",
        Path.cwd().parent.parent / "seedlinedata.db",
        Path(__file__).parent / "seedlinedata.db",
        Path(__file__).parent.parent / "seedlinedata.db",
        Path(__file__).parent.parent.parent / "seedlinedata.db",
    ]
    
    # Also check for Windows-style paths
    windows_paths = [
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"),
    ]
    search_paths.extend(windows_paths)
    
    for path in search_paths:
        if path.exists():
            return str(path.resolve())
    
    return None


def create_backup(db_path: str) -> str:
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f"_backup_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def convert_grad_year_to_u_age(age_group: str, current_year: int = 2025) -> Tuple[str, bool]:
    """
    Convert graduation year format to U-age format.
    
    Examples:
        G30 (grad 2030) → birth year 2012 → age 13 → G13
        B28 (grad 2028) → birth year 2010 → age 15 → B15
        G36 (grad 2036) → birth year 2018 → age 7 → G07
    
    Returns:
        Tuple of (new_age_group, was_converted)
    """
    if not age_group or len(age_group) < 2:
        return age_group, False
    
    # Check if it looks like a graduation year format (G/B followed by number > 20)
    prefix = age_group[0].upper()
    if prefix not in ('G', 'B'):
        return age_group, False
    
    try:
        num = int(age_group[1:])
    except ValueError:
        return age_group, False
    
    # If the number is > 20, it's likely a graduation year
    # (No youth player is U21 or older in these leagues)
    if num <= 20:
        return age_group, False  # Already in correct format
    
    # Convert: grad_year (e.g., 30 for 2030) → birth_year → age
    grad_year = 2000 + num  # 30 → 2030
    birth_year = grad_year - 18  # 2030 → 2012
    age = current_year - birth_year  # 2025 - 2012 = 13
    
    # Sanity check: age should be reasonable (5-19 for youth soccer)
    if age < 5 or age > 19:
        return age_group, False  # Something's wrong, don't convert
    
    new_age_group = f"{prefix}{age:02d}"
    return new_age_group, True


def get_npl_leagues_filter() -> str:
    """Return SQL WHERE clause to identify NPL leagues."""
    return """(
        league LIKE '%NPL%' 
        OR league LIKE '%Frontier%' 
        OR league LIKE '%Central States%'
        OR league LIKE '%CPSL%'
        OR league LIKE '%FCL%'
        OR league LIKE '%VPSL%'
        OR league LIKE '%NISL%'
        OR league LIKE '%MDL%'
        OR league LIKE '%SOCAL%'
        OR league LIKE '%NorCal%'
    )"""


def preview_changes(db_path: str) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Preview what changes would be made.
    
    Returns:
        Tuple of (games_to_fix, teams_to_fix)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    current_year = datetime.now().year
    npl_filter = get_npl_leagues_filter()
    
    # Find games that need fixing
    cur.execute(f"""
        SELECT rowid, game_id, league, age_group, gender, home_team, away_team
        FROM games 
        WHERE {npl_filter}
        AND age_group IS NOT NULL
        AND age_group != ''
    """)
    
    games_to_fix = []
    for row in cur.fetchall():
        rowid, game_id, league, age_group, gender, home_team, away_team = row
        new_age_group, needs_fix = convert_grad_year_to_u_age(age_group, current_year)
        if needs_fix:
            games_to_fix.append((rowid, game_id, league, age_group, new_age_group, home_team, away_team))
    
    # Find teams that need fixing
    cur.execute(f"""
        SELECT rowid, team_name, league, age_group, gender
        FROM teams 
        WHERE {npl_filter}
        AND age_group IS NOT NULL
        AND age_group != ''
    """)
    
    teams_to_fix = []
    for row in cur.fetchall():
        rowid, team_name, league, age_group, gender = row
        new_age_group, needs_fix = convert_grad_year_to_u_age(age_group, current_year)
        if needs_fix:
            teams_to_fix.append((rowid, team_name, league, age_group, new_age_group))
    
    conn.close()
    return games_to_fix, teams_to_fix


def apply_fixes(db_path: str, games_to_fix: List[Tuple], teams_to_fix: List[Tuple]) -> Tuple[int, int]:
    """
    Apply the age group fixes to the database.
    
    Returns:
        Tuple of (games_fixed, teams_fixed)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    games_fixed = 0
    teams_fixed = 0
    
    # Fix games
    for rowid, game_id, league, old_age, new_age, home_team, away_team in games_to_fix:
        cur.execute("UPDATE games SET age_group = ? WHERE rowid = ?", (new_age, rowid))
        games_fixed += 1
    
    # Fix teams
    for rowid, team_name, league, old_age, new_age in teams_to_fix:
        cur.execute("UPDATE teams SET age_group = ? WHERE rowid = ?", (new_age, rowid))
        teams_fixed += 1
    
    conn.commit()
    conn.close()
    
    return games_fixed, teams_fixed


def show_age_distribution(db_path: str, table: str = "games"):
    """Show current age group distribution for NPL leagues."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    npl_filter = get_npl_leagues_filter()
    
    cur.execute(f"""
        SELECT age_group, COUNT(*) as count
        FROM {table}
        WHERE {npl_filter}
        AND age_group IS NOT NULL
        AND age_group != ''
        GROUP BY age_group
        ORDER BY count DESC
        LIMIT 20
    """)
    
    results = cur.fetchall()
    conn.close()
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Fix NPL age group formatting in seedlinedata.db',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fix_npl_age_groups.py                    # Interactive mode
  python fix_npl_age_groups.py --db path/to/db   # Specify database
  python fix_npl_age_groups.py --dry-run         # Preview only
        """
    )
    
    parser.add_argument('--db', type=str, help='Path to seedlinedata.db')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup (not recommended)')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  NPL AGE GROUP FIX SCRIPT")
    print("  Converts graduation year format (G30) to U-age format (G13)")
    print("=" * 70)
    print()
    
    # Find database
    db_path = args.db or find_database()
    
    if not db_path:
        print("❌ Could not find seedlinedata.db")
        print("   Please specify path with --db option")
        db_path = input("   Enter database path: ").strip()
        if not db_path or not os.path.exists(db_path):
            print("❌ Invalid path. Exiting.")
            return 1
    
    print(f"📂 Database: {db_path}")
    print()
    
    # Show current state
    print("CURRENT STATE (NPL games):")
    print("-" * 40)
    dist = show_age_distribution(db_path, "games")
    if dist:
        for age_group, count in dist[:10]:
            # Check if it needs fixing
            new_age, needs_fix = convert_grad_year_to_u_age(age_group)
            indicator = f" → {new_age}" if needs_fix else " ✓"
            print(f"  {age_group}: {count:,} games{indicator}")
    else:
        print("  No NPL games found")
    print()
    
    # Preview changes
    print("ANALYZING CHANGES...")
    print("-" * 40)
    games_to_fix, teams_to_fix = preview_changes(db_path)
    
    print(f"  Games to fix: {len(games_to_fix):,}")
    print(f"  Teams to fix: {len(teams_to_fix):,}")
    print()
    
    if not games_to_fix and not teams_to_fix:
        print("✅ No changes needed! All age groups are already in correct format.")
        return 0
    
    # Show sample of changes
    print("SAMPLE CHANGES:")
    print("-" * 40)
    for i, (rowid, game_id, league, old_age, new_age, home, away) in enumerate(games_to_fix[:5]):
        print(f"  Game: {home[:30]} vs {away[:30]}")
        print(f"        {old_age} → {new_age} ({league})")
    if len(games_to_fix) > 5:
        print(f"  ... and {len(games_to_fix) - 5:,} more games")
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes made")
        return 0
    
    # Confirm
    if not args.yes:
        print("⚠️  This will modify the database.")
        response = input("   Proceed? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("❌ Cancelled")
            return 1
    
    # Create backup
    if not args.no_backup:
        print()
        print("CREATING BACKUP...")
        backup_path = create_backup(db_path)
        print(f"  ✅ Backup: {backup_path}")
    
    # Apply fixes
    print()
    print("APPLYING FIXES...")
    games_fixed, teams_fixed = apply_fixes(db_path, games_to_fix, teams_to_fix)
    
    print(f"  ✅ Games fixed: {games_fixed:,}")
    print(f"  ✅ Teams fixed: {teams_fixed:,}")
    print()
    
    # Show new state
    print("NEW STATE (NPL games):")
    print("-" * 40)
    dist = show_age_distribution(db_path, "games")
    for age_group, count in dist[:10]:
        print(f"  {age_group}: {count:,} games")
    print()
    
    print("=" * 70)
    print("  ✅ COMPLETE!")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    exit(main())
