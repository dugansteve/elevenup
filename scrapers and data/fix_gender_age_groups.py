"""
Fix mismatched gender in age_group field.

Some games have age_group = 'B14' but the team names clearly indicate
they're Girls teams (contain '14G', '13G', etc.). This script fixes those.

The issue: scrapers sometimes set age_group based on birth year without
checking the actual gender indicated in team names.
"""

import sqlite3
import re
from collections import defaultdict

DB_PATH = r'C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db'

def detect_gender_from_team_name(team_name):
    """
    Detect gender from team name patterns.
    Returns 'G' for Girls, 'B' for Boys, or None if unclear.
    """
    if not team_name:
        return None

    name = team_name.upper()

    # Girls patterns: "14G", "G14", "GIRLS", "Pre-GA", "GA " (Girls Academy)
    girls_patterns = [
        r'\b\d{2}G\b',           # "14G", "13G"
        r'\bG\d{2}\b',           # "G14", "G13"
        r'\bGIRLS?\b',           # "GIRL", "GIRLS"
        r'\bPRE-?GA\b',          # "Pre-GA", "PreGA"
        r'\bPRE GA\b',           # "Pre GA"
        r'\b\d{2}G\s',           # "14G " at word boundary
        r'\d{4}G\b',             # "2014G"
    ]

    # Boys patterns: "14B", "B14", "BOYS"
    boys_patterns = [
        r'\b\d{2}B\b',           # "14B", "13B"
        r'\bB\d{2}\b',           # "B14", "B13"
        r'\bBOYS?\b',            # "BOY", "BOYS"
        r'\b\d{2}B\s',           # "14B " at word boundary
        r'\d{4}B\b',             # "2014B"
    ]

    girls_match = any(re.search(p, name) for p in girls_patterns)
    boys_match = any(re.search(p, name) for p in boys_patterns)

    if girls_match and not boys_match:
        return 'G'
    elif boys_match and not girls_match:
        return 'B'
    else:
        return None


def analyze_mismatches(conn):
    """Find all games where age_group gender doesn't match team name gender."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT game_id, home_team, away_team, age_group, league, game_date
        FROM games
        WHERE age_group IS NOT NULL AND age_group != ''
    ''')

    mismatches = []
    stats = defaultdict(int)

    for row in cursor.fetchall():
        game_id, home_team, away_team, age_group, league, game_date = row

        # Get gender from age_group (first char)
        if not age_group:
            continue
        ag_gender = age_group[0].upper() if age_group[0] in 'GBgb' else None
        if not ag_gender:
            continue

        # Detect gender from team names
        home_gender = detect_gender_from_team_name(home_team)
        away_gender = detect_gender_from_team_name(away_team)

        # If both teams suggest same gender and it differs from age_group
        if home_gender and away_gender and home_gender == away_gender:
            if home_gender != ag_gender:
                # Extract age number
                age_num = ''.join(c for c in age_group[1:] if c.isdigit())
                correct_age_group = f"{home_gender}{age_num}"

                mismatches.append({
                    'game_id': game_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'current_age_group': age_group,
                    'correct_age_group': correct_age_group,
                    'league': league,
                    'game_date': game_date
                })
                stats[f"{league}: {age_group} -> {correct_age_group}"] += 1

        # If only one team has clear gender and it differs
        elif (home_gender or away_gender):
            detected = home_gender or away_gender
            if detected != ag_gender:
                age_num = ''.join(c for c in age_group[1:] if c.isdigit())
                correct_age_group = f"{detected}{age_num}"

                mismatches.append({
                    'game_id': game_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'current_age_group': age_group,
                    'correct_age_group': correct_age_group,
                    'league': league,
                    'game_date': game_date
                })
                stats[f"{league}: {age_group} -> {correct_age_group}"] += 1

    return mismatches, stats


def fix_mismatches(conn, mismatches, dry_run=True):
    """Update the age_group field for mismatched games."""
    cursor = conn.cursor()

    if dry_run:
        print(f"\n[DRY RUN] Would update {len(mismatches)} games")
    else:
        print(f"\nUpdating {len(mismatches)} games...")

    for m in mismatches:
        if not dry_run:
            cursor.execute('''
                UPDATE games
                SET age_group = ?
                WHERE game_id = ?
            ''', (m['correct_age_group'], m['game_id']))

    if not dry_run:
        conn.commit()
        print(f"Updated {len(mismatches)} games")

    return len(mismatches)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix gender mismatches in age_group field')
    parser.add_argument('--fix', action='store_true', help='Actually apply fixes (default is dry-run)')
    parser.add_argument('--show-examples', type=int, default=10, help='Number of examples to show')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    print("Analyzing age_group gender mismatches...")
    mismatches, stats = analyze_mismatches(conn)

    print(f"\nFound {len(mismatches)} games with mismatched age_group gender:\n")

    # Show stats by league/conversion
    for key, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {key}: {count} games")

    # Show examples
    if args.show_examples and mismatches:
        print(f"\nExamples (first {min(args.show_examples, len(mismatches))}):")
        for m in mismatches[:args.show_examples]:
            print(f"  [{m['league']}] {m['current_age_group']} -> {m['correct_age_group']}")
            print(f"    Home: {m['home_team'][:60]}")
            print(f"    Away: {m['away_team'][:60]}")
            print()

    # Fix or dry-run
    if mismatches:
        fix_mismatches(conn, mismatches, dry_run=not args.fix)

    conn.close()

    if not args.fix and mismatches:
        print("\nTo apply fixes, run with --fix flag")


if __name__ == '__main__':
    main()
