"""
Team Name Cleanup Script
Fixes data quality issues in the games table:
1. Case variations (ABSC vs Absc) - standardizes to most common form
2. Leading/trailing spaces
3. Prefix artifacts (BEast Bay United -> East Bay United)
4. First-letter-dropped typos (Oise Thorns FC -> Boise Thorns FC)
5. Filters out TBDG placeholder games

Run with --dry-run first to see what would be changed.
"""

import sqlite3
import argparse
from collections import defaultdict
from datetime import datetime
import shutil
import os

# Configuration
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

# Known first-letter-dropped typos (typo -> correct)
KNOWN_TYPOS = {
    # First letter dropped
    'Oise Thorns FC': 'Boise Thorns FC',
    'Oise Timbers FC': 'Boise Timbers FC',
    'Retna Elite Academy': 'Gretna Elite Academy',
    'Ethesda SC': 'Bethesda SC',
    'Last FC Academy': 'Blast FC Academy',
    'Litz Academy FC': 'Blitz Academy FC',
    'Oerne SC': 'Boerne SC',
    'Rentwood SC': 'Brentwood SC',
    'Rooklyn United': 'Brooklyn United',
    'Urlingame SC': 'Burlingame SC',
    'Loomingdale Lightning FC': 'Bloomingdale Lightning FC',

    # Prefix artifacts (B/G prefix from scraper bugs)
    'BEast Bay United': 'East Bay United',
    'BLivermore Fusion SC': 'Livermore Fusion SC',
    'BRevolution FC': 'Revolution FC',
    'BSan Ramon FC': 'San Ramon FC',
    'BSouth Valley United': 'South Valley United',
    'BStanford Strikers FC': 'Stanford Strikers FC',
    'BStockton TLJ FC': 'Stockton TLJ FC',
    'BUnion Sacramento FC': 'Union Sacramento FC',
    'GBurlingame SC': 'Burlingame SC',
    'GFolsom Lake Surf': 'Folsom Lake Surf',
    'GLivermore Fusion SC': 'Livermore Fusion SC',
}


def backup_database(db_path):
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.replace('.db', f'_backup_{timestamp}.db')
    shutil.copy2(db_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path


def get_all_team_names(cursor):
    """Get all unique team names from the games table."""
    cursor.execute('''
        SELECT DISTINCT home_team FROM games WHERE home_team IS NOT NULL
        UNION
        SELECT DISTINCT away_team FROM games WHERE away_team IS NOT NULL
    ''')
    return [r[0] for r in cursor.fetchall()]


def build_case_normalization_map(cursor, team_names):
    """
    Build a mapping from variant spellings to canonical form.
    Canonical form is the one with the most games (most common usage).
    """
    # Group by lowercase
    lower_to_variants = defaultdict(list)
    for name in team_names:
        lower_to_variants[name.lower().strip()].append(name)

    # For each group with multiple variants, pick the most common
    normalization_map = {}
    for lower, variants in lower_to_variants.items():
        if len(variants) > 1:
            # Count games for each variant
            variant_counts = []
            for v in variants:
                cursor.execute(
                    'SELECT COUNT(*) FROM games WHERE home_team = ? OR away_team = ?',
                    (v, v)
                )
                count = cursor.fetchone()[0]
                variant_counts.append((v, count))

            # Pick the one with most games as canonical
            canonical = max(variant_counts, key=lambda x: x[1])[0]

            # Map all others to canonical
            for v, _ in variant_counts:
                if v != canonical:
                    normalization_map[v] = canonical

    return normalization_map


def build_full_normalization_map(cursor):
    """Build complete normalization map including all fixes."""
    team_names = get_all_team_names(cursor)

    # Start with known typos
    norm_map = dict(KNOWN_TYPOS)

    # Add case normalizations
    case_map = build_case_normalization_map(cursor, team_names)
    for old, new in case_map.items():
        if old not in norm_map:  # Don't override known typos
            norm_map[old] = new

    # Add leading/trailing space fixes
    for name in team_names:
        stripped = name.strip()
        if stripped != name and name not in norm_map:
            norm_map[name] = stripped

    return norm_map


def apply_fixes(cursor, conn, norm_map, dry_run=True):
    """Apply the normalization map to the database."""

    stats = {
        'home_team_updates': 0,
        'away_team_updates': 0,
        'teams_table_updates': 0,
        'teams_fixed': set(),
    }

    for old_name, new_name in sorted(norm_map.items()):
        # Count affected rows in games table
        cursor.execute(
            'SELECT COUNT(*) FROM games WHERE home_team = ?',
            (old_name,)
        )
        home_count = cursor.fetchone()[0]

        cursor.execute(
            'SELECT COUNT(*) FROM games WHERE away_team = ?',
            (old_name,)
        )
        away_count = cursor.fetchone()[0]

        # Count affected rows in teams table
        cursor.execute(
            'SELECT COUNT(*) FROM teams WHERE team_name = ? OR club_name = ?',
            (old_name, old_name)
        )
        teams_count = cursor.fetchone()[0]

        if home_count > 0 or away_count > 0 or teams_count > 0:
            print(f"  '{old_name}' -> '{new_name}' (games: {home_count}h/{away_count}a, teams: {teams_count})")
            stats['teams_fixed'].add(old_name)
            stats['home_team_updates'] += home_count
            stats['away_team_updates'] += away_count
            stats['teams_table_updates'] += teams_count

            if not dry_run:
                # Fix games table
                cursor.execute(
                    'UPDATE games SET home_team = ? WHERE home_team = ?',
                    (new_name, old_name)
                )
                cursor.execute(
                    'UPDATE games SET away_team = ? WHERE away_team = ?',
                    (new_name, old_name)
                )
                # Fix teams table (both team_name and club_name columns)
                cursor.execute(
                    'UPDATE teams SET team_name = ? WHERE team_name = ?',
                    (new_name, old_name)
                )
                cursor.execute(
                    'UPDATE teams SET club_name = ? WHERE club_name = ?',
                    (new_name, old_name)
                )

    if not dry_run:
        conn.commit()

    return stats


def analyze_tbdg_games(cursor):
    """Analyze TBDG placeholder games."""
    cursor.execute('''
        SELECT COUNT(*) FROM games
        WHERE home_team = 'TBDG' OR away_team = 'TBDG'
    ''')
    count = cursor.fetchone()[0]

    cursor.execute('''
        SELECT DISTINCT league, conference FROM games
        WHERE home_team = 'TBDG' OR away_team = 'TBDG'
        LIMIT 10
    ''')
    contexts = cursor.fetchall()

    return count, contexts


def main():
    parser = argparse.ArgumentParser(description='Fix team name data quality issues')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be changed without making changes (default)')
    parser.add_argument('--apply', action='store_true',
                        help='Actually apply the changes')
    parser.add_argument('--db', type=str, default=DB_PATH,
                        help='Path to database file')

    args = parser.parse_args()
    dry_run = not args.apply

    print("=" * 70)
    print("TEAM NAME CLEANUP SCRIPT")
    print("=" * 70)
    print(f"Database: {args.db}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLYING CHANGES'}")
    print()

    # Check database exists
    if not os.path.exists(args.db):
        print(f"ERROR: Database not found: {args.db}")
        return

    # Create backup if applying changes
    if not dry_run:
        backup_database(args.db)

    # Connect to database
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Get initial stats
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(DISTINCT team) FROM (
            SELECT home_team as team FROM games
            UNION SELECT away_team as team FROM games
        )
    ''')
    unique_teams = cursor.fetchone()[0]

    print(f"Total games: {total_games:,}")
    print(f"Unique team names (before): {unique_teams:,}")
    print()

    # Build normalization map
    print("Building normalization map...")
    norm_map = build_full_normalization_map(cursor)
    print(f"Found {len(norm_map)} team names to normalize")
    print()

    # Show known typos first
    print("-" * 70)
    print("KNOWN TYPOS TO FIX:")
    print("-" * 70)
    known_found = 0
    for old, new in sorted(KNOWN_TYPOS.items()):
        cursor.execute(
            'SELECT COUNT(*) FROM games WHERE home_team = ? OR away_team = ?',
            (old, old)
        )
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  '{old}' -> '{new}' ({count} games)")
            known_found += 1
    print(f"Found {known_found}/{len(KNOWN_TYPOS)} known typos in database")
    print()

    # Show case variations
    print("-" * 70)
    print("CASE VARIATIONS TO FIX (sample):")
    print("-" * 70)
    case_fixes = [(k, v) for k, v in norm_map.items() if k not in KNOWN_TYPOS]
    for old, new in sorted(case_fixes)[:20]:
        cursor.execute(
            'SELECT COUNT(*) FROM games WHERE home_team = ? OR away_team = ?',
            (old, old)
        )
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  '{old}' -> '{new}' ({count} games)")
    if len(case_fixes) > 20:
        print(f"  ... and {len(case_fixes) - 20} more")
    print()

    # Apply fixes
    print("-" * 70)
    print("APPLYING FIXES:" if not dry_run else "WOULD APPLY FIXES:")
    print("-" * 70)
    stats = apply_fixes(cursor, conn, norm_map, dry_run)
    print()

    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"Team names fixed: {len(stats['teams_fixed'])}")
    print(f"Games table - home_team updates: {stats['home_team_updates']:,}")
    print(f"Games table - away_team updates: {stats['away_team_updates']:,}")
    print(f"Teams table updates: {stats['teams_table_updates']:,}")
    print(f"Total records affected: {stats['home_team_updates'] + stats['away_team_updates'] + stats['teams_table_updates']:,}")
    print()

    # TBDG analysis
    print("-" * 70)
    print("TBDG PLACEHOLDER ANALYSIS")
    print("-" * 70)
    tbdg_count, contexts = analyze_tbdg_games(cursor)
    print(f"Games with TBDG placeholder: {tbdg_count:,}")
    print("(These should be excluded from conference analysis, not deleted)")
    print()

    # Final stats
    if not dry_run:
        cursor.execute('''
            SELECT COUNT(DISTINCT team) FROM (
                SELECT home_team as team FROM games
                UNION SELECT away_team as team FROM games
            )
        ''')
        new_unique = cursor.fetchone()[0]
        print(f"Unique team names (after): {new_unique:,}")
        print(f"Reduction: {unique_teams - new_unique:,} duplicate names eliminated")

    conn.close()

    if dry_run:
        print()
        print("=" * 70)
        print("This was a DRY RUN. No changes were made.")
        print("To apply changes, run with --apply flag:")
        print("  python fix_team_names.py --apply")
        print("=" * 70)


if __name__ == '__main__':
    main()
