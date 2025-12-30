"""
Comprehensive Age Group Fix for Seedline Database

This script fixes age group mismatches by analyzing team names and determining
the correct age group based on clear indicators.

Key rules:
1. 4-digit year (2014) = BIRTH YEAR → age = 2025 - 2014 = 11 → G11/B11
2. G2014 / 2014G = Girls/Boys BIRTH YEAR 2014 → G11/B11
3. U14 / GU14 / BU14 = Under 14 = AGE 14 → G14/B14
4. G14 / B14 (with word boundaries) = AGE 14 → G14/B14

v1 - 2024-12-21: Comprehensive fix
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime
import shutil
from collections import defaultdict

CURRENT_YEAR = 2025


def get_correct_age_group(team_name: str, gender_hint: str = None) -> tuple:
    """
    Determine the correct age group from a team name.

    Returns: (age_group, indicator_type, confidence)
    - age_group: 'G14', 'B11', etc. or None if can't determine
    - indicator_type: 'birth_year', 'age', or None
    - confidence: 'high', 'medium', 'low'
    """
    if not team_name:
        return None, None, None

    # Determine gender from team name
    gender = None
    if re.search(r'\bgirls?\b', team_name, re.I):
        gender = 'G'
    elif re.search(r'\bboys?\b', team_name, re.I):
        gender = 'B'
    elif gender_hint:
        gender = gender_hint[0].upper() if gender_hint else None

    # =========================================================================
    # BIRTH YEAR PATTERNS (highest priority - most specific)
    # =========================================================================

    # Pattern: "Girls 2014" or "Boys 2015" (very clear birth year)
    match = re.search(r'\b(Girls?|Boys?)\s*(20(?:0[5-9]|1[0-9]|2[0-5]))\b', team_name, re.I)
    if match:
        g = 'G' if match.group(1).lower().startswith('g') else 'B'
        year = int(match.group(2))
        age = CURRENT_YEAR - year
        if 6 <= age <= 19:
            return f'{g}{age:02d}', 'birth_year', 'high'

    # Pattern: G2014 or B2015 (gender + 4-digit birth year)
    match = re.search(r'\b([GB])(20(?:0[5-9]|1[0-9]|2[0-5]))\b', team_name, re.I)
    if match:
        g = match.group(1).upper()
        year = int(match.group(2))
        age = CURRENT_YEAR - year
        if 6 <= age <= 19:
            return f'{g}{age:02d}', 'birth_year', 'high'

    # Pattern: 2014G or 2015B (birth year + gender suffix)
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))([GB])\b', team_name, re.I)
    if match:
        year = int(match.group(1))
        g = match.group(2).upper()
        age = CURRENT_YEAR - year
        if 6 <= age <= 19:
            return f'{g}{age:02d}', 'birth_year', 'high'

    # Pattern: Standalone 4-digit year (2014, 2015) with gender context
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))\b', team_name)
    if match and gender:
        year = int(match.group(1))
        age = CURRENT_YEAR - year
        if 6 <= age <= 19:
            return f'{gender}{age:02d}', 'birth_year', 'medium'

    # =========================================================================
    # AGE PATTERNS (secondary priority)
    # =========================================================================

    # Pattern: GU14 or BU15 (very clear age format)
    match = re.search(r'\b([GB])U(\d{1,2})\b', team_name, re.I)
    if match:
        g = match.group(1).upper()
        age = int(match.group(2))
        if 6 <= age <= 19:
            return f'{g}{age:02d}', 'age', 'high'

    # Pattern: U14 or U15 with gender context
    match = re.search(r'\bU[\s-]?(\d{1,2})\b', team_name, re.I)
    if match and gender:
        age = int(match.group(1))
        if 6 <= age <= 19:
            return f'{gender}{age:02d}', 'age', 'medium'

    # Pattern: " G14 " or " B15 " with clear word boundaries
    # This is tricky - need to distinguish from G2014 which we already handled
    match = re.search(r'(?:^|[\s\-_/])([GB])(\d{2})(?:[\s\-_/]|$)', team_name, re.I)
    if match:
        g = match.group(1).upper()
        num = int(match.group(2))
        # Only treat as age if it's in the valid range AND not part of a year
        # Check that there isn't a "20" before this
        full_match_start = match.start()
        prefix = team_name[max(0, full_match_start-2):full_match_start]
        if '20' not in prefix and 6 <= num <= 19:
            return f'{g}{num:02d}', 'age', 'medium'

    # Pattern: 14G or 15B with word boundaries
    match = re.search(r'(?:^|[\s\-_/])(\d{2})([GB])(?:[\s\-_/]|$)', team_name, re.I)
    if match:
        num = int(match.group(1))
        g = match.group(2).upper()
        if 6 <= num <= 19:
            return f'{g}{num:02d}', 'age', 'medium'

    return None, None, None


def analyze_and_fix_games(db_path: str, dry_run: bool = True):
    """
    Analyze all games and fix age groups where possible.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"Analyzing database: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLYING FIXES'}")
    print("="*80)

    # Stats
    stats = {
        'total_games': 0,
        'games_with_indicators': 0,
        'games_needing_fix': 0,
        'games_fixed': 0,
        'conflicts': 0,
        'by_transition': defaultdict(int),
        'by_league': defaultdict(int)
    }

    # Collect fixes to apply
    fixes = []  # list of (game_id, new_age_group)

    # Process all games with age_group set
    cur.execute("""
        SELECT game_id, home_team, away_team, age_group, gender, league, conference
        FROM games
        WHERE age_group IS NOT NULL AND age_group != ''
    """)

    for row in cur.fetchall():
        stats['total_games'] += 1

        game_id = row['game_id']
        home = row['home_team']
        away = row['away_team']
        current_ag = row['age_group']
        gender = row['gender']
        league = row['league']

        # Get age group from both teams
        home_ag, home_type, home_conf = get_correct_age_group(home, gender)
        away_ag, away_type, away_conf = get_correct_age_group(away, gender)

        # Determine the correct age group
        correct_ag = None

        if home_ag and away_ag:
            if home_ag == away_ag:
                # Both teams agree
                correct_ag = home_ag
            else:
                # Conflict - trust higher confidence or birth year over age
                if home_type == 'birth_year' and away_type == 'age':
                    # Birth year is more reliable (4-digit year is unambiguous)
                    correct_ag = home_ag
                elif away_type == 'birth_year' and home_type == 'age':
                    correct_ag = away_ag
                elif home_conf == 'high' and away_conf != 'high':
                    correct_ag = home_ag
                elif away_conf == 'high' and home_conf != 'high':
                    correct_ag = away_ag
                else:
                    # Can't decide - skip this game
                    stats['conflicts'] += 1
                    continue
        elif home_ag:
            correct_ag = home_ag
        elif away_ag:
            correct_ag = away_ag
        else:
            # No indicators found
            continue

        stats['games_with_indicators'] += 1

        if correct_ag != current_ag:
            stats['games_needing_fix'] += 1
            stats['by_transition'][f'{current_ag} -> {correct_ag}'] += 1
            stats['by_league'][league] += 1
            fixes.append((game_id, correct_ag))

    # Print stats
    print(f"\nTotal games analyzed: {stats['total_games']:,}")
    print(f"Games with age indicators in team names: {stats['games_with_indicators']:,}")
    print(f"Games needing fix: {stats['games_needing_fix']:,}")
    print(f"Conflicts (skipped): {stats['conflicts']:,}")

    print("\n" + "-"*60)
    print("TOP TRANSITIONS:")
    print("-"*60)
    sorted_trans = sorted(stats['by_transition'].items(), key=lambda x: -x[1])[:20]
    for trans, count in sorted_trans:
        print(f"  {trans}: {count:,}")

    print("\n" + "-"*60)
    print("BY LEAGUE:")
    print("-"*60)
    sorted_leagues = sorted(stats['by_league'].items(), key=lambda x: -x[1])[:15]
    for league, count in sorted_leagues:
        print(f"  {league}: {count:,}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with --apply to fix.")
        conn.close()
        return stats

    # Create backup
    backup_path = db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    print(f"\nCreating backup: {backup_path}")
    conn.close()
    shutil.copy2(db_path, backup_path)

    # Apply fixes in batches for better performance
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    batch_size = 1000
    for i in range(0, len(fixes), batch_size):
        batch = fixes[i:i+batch_size]
        # Use executemany for better performance
        cur.executemany("UPDATE games SET age_group = ? WHERE game_id = ?",
                       [(new_ag, game_id) for game_id, new_ag in batch])
        stats['games_fixed'] += len(batch)
        if i % 10000 == 0:
            print(f"  Progress: {i:,}/{len(fixes):,} games updated...")
            conn.commit()  # Commit periodically

    conn.commit()
    conn.close()

    print(f"\n[DONE] Fixed {stats['games_fixed']:,} games")
    print(f"Backup saved to: {backup_path}")

    return stats


def fix_teams_table(db_path: str, dry_run: bool = True):
    """Fix age groups in the teams table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("\n" + "="*80)
    print("FIXING TEAMS TABLE")
    print("="*80)

    stats = {'total': 0, 'fixed': 0}
    fixes = []

    cur.execute("""
        SELECT rowid as id, team_name, age_group, gender
        FROM teams
        WHERE age_group IS NOT NULL AND age_group != ''
    """)

    for row in cur.fetchall():
        stats['total'] += 1
        rowid = row['id']
        team_name = row['team_name']
        current_ag = row['age_group']
        gender = row['gender']

        correct_ag, indicator_type, confidence = get_correct_age_group(team_name, gender)

        if correct_ag and correct_ag != current_ag and confidence in ['high', 'medium']:
            fixes.append((rowid, correct_ag))

    print(f"Teams analyzed: {stats['total']:,}")
    print(f"Teams needing fix: {len(fixes):,}")

    if dry_run:
        print("[DRY RUN] No changes made.")
        conn.close()
        return

    # Batch update for performance
    cur.executemany("UPDATE teams SET age_group = ? WHERE rowid = ?", fixes)
    stats['fixed'] = len(fixes)

    conn.commit()
    conn.close()
    print(f"[DONE] Fixed {stats['fixed']:,} teams")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive age group fix')
    parser.add_argument('--db', default='seedlinedata.db', help='Database path')
    parser.add_argument('--apply', action='store_true', help='Apply fixes (default is dry run)')
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return

    # Fix games
    analyze_and_fix_games(db_path, dry_run=not args.apply)

    # Fix teams
    fix_teams_table(db_path, dry_run=not args.apply)


if __name__ == '__main__':
    main()
