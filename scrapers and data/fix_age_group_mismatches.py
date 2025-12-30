"""
Fix Age Group Mismatches in Seedline Database

This script identifies and fixes teams/games where:
1. The team name contains an age indicator (G14, G15, U14, etc.) that doesn't match the stored age_group
2. The team name contains a birth year (2014, 2015) that doesn't match the stored age_group

Key insight:
- "G14" in a team name means "Girls Under 14" = birth year 2011 = should be G14
- "2014" in a team name means birth year 2014 = age 11 in 2025 = should be G11
- "G2014" means Girls born 2014 = should be G11

v1 - 2024-12-21: Initial version
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime
import shutil

# Current year for age calculations
CURRENT_YEAR = 2025

def extract_age_indicator_from_name(team_name: str) -> dict:
    """
    Extract age indicators from team name and determine expected age group.

    Returns dict with:
    - indicator_type: 'age', 'birth_year', or None
    - raw_value: the matched string
    - expected_age_group: the Gxx/Bxx format this should map to
    - gender: 'G' or 'B'
    """
    if not team_name:
        return {'indicator_type': None}

    result = {'indicator_type': None}

    # Priority 1: G2014 / B2015 format (gender + birth year) - most specific
    match = re.search(r'\b([GB])(20(?:0[5-9]|1[0-9]|2[0-5]))\b', team_name, re.I)
    if match:
        gender = match.group(1).upper()
        birth_year = int(match.group(2))
        age = CURRENT_YEAR - birth_year
        return {
            'indicator_type': 'birth_year',
            'raw_value': match.group(0),
            'expected_age_group': f'{gender}{age:02d}',
            'gender': gender
        }

    # Priority 2: 2014G / 2015B format (birth year + gender)
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))([GB])\b', team_name, re.I)
    if match:
        birth_year = int(match.group(1))
        gender = match.group(2).upper()
        age = CURRENT_YEAR - birth_year
        return {
            'indicator_type': 'birth_year',
            'raw_value': match.group(0),
            'expected_age_group': f'{gender}{age:02d}',
            'gender': gender
        }

    # Priority 3: "Girls 2014" / "Boys 2015" format
    match = re.search(r'\b(Girls?|Boys?)\s*(20(?:0[5-9]|1[0-9]|2[0-5]))\b', team_name, re.I)
    if match:
        gender = 'G' if match.group(1).lower().startswith('g') else 'B'
        birth_year = int(match.group(2))
        age = CURRENT_YEAR - birth_year
        return {
            'indicator_type': 'birth_year',
            'raw_value': match.group(0),
            'expected_age_group': f'{gender}{age:02d}',
            'gender': gender
        }

    # Priority 4: GU14 / BU15 format (Girls Under 14 = age 14)
    match = re.search(r'\b([GB])U(\d{1,2})\b', team_name, re.I)
    if match:
        gender = match.group(1).upper()
        age = int(match.group(2))
        if 6 <= age <= 19:
            return {
                'indicator_type': 'age',
                'raw_value': match.group(0),
                'expected_age_group': f'{gender}{age:02d}',
                'gender': gender
            }

    # Priority 5: U14 / U15 format (Under 14 = age 14) - need to infer gender from elsewhere
    match = re.search(r'\bU[\s-]*(\d{1,2})\b', team_name, re.I)
    if match:
        age = int(match.group(1))
        if 6 <= age <= 19:
            # Try to find gender in team name
            gender = None
            if re.search(r'\bgirls?\b', team_name, re.I):
                gender = 'G'
            elif re.search(r'\bboys?\b', team_name, re.I):
                gender = 'B'

            if gender:
                return {
                    'indicator_type': 'age',
                    'raw_value': match.group(0),
                    'expected_age_group': f'{gender}{age:02d}',
                    'gender': gender
                }

    # Priority 6: G14 / B15 format (Girls age 14 = age 14) - THIS IS THE KEY PATTERN
    # Match only when there's a word boundary (space/start/end) around it
    match = re.search(r'(?:^|[\s\-_])([GB])(\d{2})(?:[\s\-_]|$)', team_name, re.I)
    if match:
        gender = match.group(1).upper()
        age = int(match.group(2))
        if 6 <= age <= 19:
            return {
                'indicator_type': 'age',
                'raw_value': f'{match.group(1)}{match.group(2)}',
                'expected_age_group': f'{gender}{age:02d}',
                'gender': gender
            }

    # Priority 7: 14G / 15B format (age 14 Girls = age 14)
    match = re.search(r'\b(\d{2})([GB])\b', team_name, re.I)
    if match:
        age = int(match.group(1))
        gender = match.group(2).upper()
        if 6 <= age <= 19:
            return {
                'indicator_type': 'age',
                'raw_value': match.group(0),
                'expected_age_group': f'{gender}{age:02d}',
                'gender': gender
            }

    # Priority 8: Standalone birth year (2014, 2015) - need gender from context
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))\b', team_name)
    if match:
        birth_year = int(match.group(1))
        age = CURRENT_YEAR - birth_year

        # Try to find gender in team name
        gender = None
        if re.search(r'\bgirls?\b', team_name, re.I):
            gender = 'G'
        elif re.search(r'\bboys?\b', team_name, re.I):
            gender = 'B'

        if gender and 6 <= age <= 19:
            return {
                'indicator_type': 'birth_year',
                'raw_value': match.group(0),
                'expected_age_group': f'{gender}{age:02d}',
                'gender': gender
            }

    return {'indicator_type': None}


def analyze_mismatches(db_path: str, verbose: bool = True):
    """Analyze all teams/games for age group mismatches."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    mismatches = {
        'teams': [],
        'games_home': [],
        'games_away': []
    }

    # Check teams table
    if verbose:
        print("Analyzing teams table...")
    cur.execute("SELECT rowid as id, team_name, age_group, gender, league FROM teams WHERE age_group != ''")
    for row in cur.fetchall():
        indicator = extract_age_indicator_from_name(row['team_name'])
        if indicator['indicator_type'] and indicator['expected_age_group'] != row['age_group']:
            mismatches['teams'].append({
                'rowid': row['id'],
                'team_name': row['team_name'],
                'current_age_group': row['age_group'],
                'expected_age_group': indicator['expected_age_group'],
                'indicator_type': indicator['indicator_type'],
                'raw_value': indicator['raw_value'],
                'league': row['league']
            })

    # Check games table - home teams
    if verbose:
        print("Analyzing games table (home teams)...")
    cur.execute("SELECT rowid as id, home_team, age_group, league FROM games WHERE age_group != ''")
    for row in cur.fetchall():
        indicator = extract_age_indicator_from_name(row['home_team'])
        if indicator['indicator_type'] and indicator['expected_age_group'] != row['age_group']:
            mismatches['games_home'].append({
                'rowid': row['id'],
                'team_name': row['home_team'],
                'current_age_group': row['age_group'],
                'expected_age_group': indicator['expected_age_group'],
                'indicator_type': indicator['indicator_type'],
                'raw_value': indicator['raw_value'],
                'league': row['league']
            })

    # Check games table - away teams
    if verbose:
        print("Analyzing games table (away teams)...")
    cur.execute("SELECT rowid as id, away_team, age_group, league FROM games WHERE age_group != ''")
    for row in cur.fetchall():
        indicator = extract_age_indicator_from_name(row['away_team'])
        if indicator['indicator_type'] and indicator['expected_age_group'] != row['age_group']:
            mismatches['games_away'].append({
                'rowid': row['id'],
                'team_name': row['away_team'],
                'current_age_group': row['age_group'],
                'expected_age_group': indicator['expected_age_group'],
                'indicator_type': indicator['indicator_type'],
                'raw_value': indicator['raw_value'],
                'league': row['league']
            })

    conn.close()
    return mismatches


def summarize_mismatches(mismatches: dict):
    """Print summary of mismatches found."""
    print("\n" + "="*80)
    print("AGE GROUP MISMATCH ANALYSIS")
    print("="*80)

    print(f"\nTeams with mismatches: {len(mismatches['teams'])}")
    print(f"Games with home team mismatches: {len(mismatches['games_home'])}")
    print(f"Games with away team mismatches: {len(mismatches['games_away'])}")

    # Group by current -> expected transition
    transitions = {}
    all_mismatches = (
        mismatches['teams'] +
        mismatches['games_home'] +
        mismatches['games_away']
    )

    for m in all_mismatches:
        key = f"{m['current_age_group']} -> {m['expected_age_group']}"
        if key not in transitions:
            transitions[key] = {'count': 0, 'indicator_types': set(), 'examples': []}
        transitions[key]['count'] += 1
        transitions[key]['indicator_types'].add(m['indicator_type'])
        if len(transitions[key]['examples']) < 3:
            transitions[key]['examples'].append(m['team_name'][:60])

    print("\n" + "-"*60)
    print("TRANSITIONS (current -> expected):")
    print("-"*60)
    for transition, data in sorted(transitions.items(), key=lambda x: -x[1]['count']):
        types = ', '.join(data['indicator_types'])
        print(f"\n{transition} ({data['count']} occurrences)")
        print(f"  Indicator types: {types}")
        print(f"  Examples:")
        for ex in data['examples']:
            print(f"    - {ex}")

    # Separate age-based from birth-year-based
    age_based = [m for m in all_mismatches if m['indicator_type'] == 'age']
    birth_year_based = [m for m in all_mismatches if m['indicator_type'] == 'birth_year']

    print("\n" + "-"*60)
    print(f"Age-based indicators (G14, U15, etc.): {len(age_based)} mismatches")
    print(f"Birth-year-based indicators (2014, G2015, etc.): {len(birth_year_based)} mismatches")
    print("-"*60)

    return transitions


def fix_games_age_groups(db_path: str, dry_run: bool = True):
    """
    Fix games where team names indicate a different age group than stored.

    Strategy:
    - For age-based indicators (G14, U15), trust the team name
    - For birth-year-based indicators, these should match; if not, it's likely a naming issue

    Only fixes 'age' type indicators where the pattern is clear.
    """
    mismatches = analyze_mismatches(db_path, verbose=True)

    # Summarize what we found
    summarize_mismatches(mismatches)

    # Prepare fixes - only for age-based indicators
    # These are cases where team name has "G15" but stored as G10 (or similar)
    fixes_to_apply = []

    # Collect game rowids that need age_group updated
    game_age_updates = {}  # rowid -> expected_age_group

    for m in mismatches['games_home'] + mismatches['games_away']:
        if m['indicator_type'] == 'age':
            # Trust the age indicator in the team name
            rowid = m['rowid']
            expected = m['expected_age_group']

            # If we've already seen this rowid, make sure the expected matches
            if rowid in game_age_updates:
                if game_age_updates[rowid] != expected:
                    # Conflicting expectations - skip this one
                    print(f"  [SKIP] Game {rowid}: Conflicting age expectations ({game_age_updates[rowid]} vs {expected})")
                    continue
            else:
                game_age_updates[rowid] = expected
                fixes_to_apply.append(m)

    # Also handle team table fixes
    team_fixes = [m for m in mismatches['teams'] if m['indicator_type'] == 'age']

    print("\n" + "="*80)
    print(f"PROPOSED FIXES (dry_run={dry_run})")
    print("="*80)
    print(f"\nGames to update: {len(game_age_updates)}")
    print(f"Teams to update: {len(team_fixes)}")

    if dry_run:
        print("\n[DRY RUN] No changes will be made.")
        print("Run with --apply to make changes.")
        return

    # Create backup
    backup_path = db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    print(f"\nCreating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    # Apply fixes
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    games_fixed = 0
    teams_fixed = 0

    # Fix games
    for rowid, expected_age_group in game_age_updates.items():
        cur.execute("UPDATE games SET age_group = ? WHERE rowid = ?", (expected_age_group, rowid))
        games_fixed += 1

    # Fix teams
    for m in team_fixes:
        cur.execute("UPDATE teams SET age_group = ? WHERE rowid = ?", (m['expected_age_group'], m['rowid']))
        teams_fixed += 1

    conn.commit()
    conn.close()

    print(f"\n[DONE] Fixed {games_fixed} games and {teams_fixed} teams")
    print(f"Backup saved to: {backup_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix age group mismatches in Seedline database')
    parser.add_argument('--db', default='seedlinedata.db', help='Database path')
    parser.add_argument('--apply', action='store_true', help='Actually apply fixes (default is dry run)')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze, show detailed report')
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return

    if args.analyze_only:
        mismatches = analyze_mismatches(db_path)
        summarize_mismatches(mismatches)
    else:
        fix_games_age_groups(db_path, dry_run=not args.apply)


if __name__ == '__main__':
    main()
