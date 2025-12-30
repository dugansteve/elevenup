"""
Fast SQL-based age group fix for Seedline Database

Uses direct SQL pattern matching for faster execution.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

CURRENT_YEAR = 2025

def apply_fixes(db_path: str):
    """Apply age group fixes using SQL updates."""

    # Create backup first
    backup_path = db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path, timeout=60)  # 60 second timeout
    cur = conn.cursor()

    print("\n" + "="*80)
    print("APPLYING AGE GROUP FIXES")
    print("="*80)

    total_fixed = 0

    # =========================================================================
    # GAMES TABLE FIXES
    # =========================================================================
    print("\nFixing games table...")

    # Fix: Birth year patterns like "2014 Girls" or "Girls 2014" -> G11
    # Formula: 2025 - birth_year = age
    for birth_year in range(2005, 2020):
        age = CURRENT_YEAR - birth_year
        for gender, prefix in [('Girls', 'G'), ('Boys', 'B')]:
            correct_ag = f'{prefix}{age:02d}'

            # Pattern: "2014 Girls" or "Girls 2014" in team names
            cur.execute(f"""
                UPDATE games
                SET age_group = ?
                WHERE age_group != ?
                AND (
                    home_team LIKE '%{gender}%{birth_year}%'
                    OR home_team LIKE '%{birth_year}%{gender}%'
                    OR away_team LIKE '%{gender}%{birth_year}%'
                    OR away_team LIKE '%{birth_year}%{gender}%'
                )
            """, (correct_ag, correct_ag))
            fixed = cur.rowcount
            if fixed > 0:
                total_fixed += fixed
                print(f"  Fixed {fixed} games: {birth_year} {gender} -> {correct_ag}")

    # Fix: G2014 / B2014 patterns -> G11/B11
    for birth_year in range(2005, 2020):
        age = CURRENT_YEAR - birth_year
        year_suffix = str(birth_year)

        for prefix in ['G', 'B']:
            correct_ag = f'{prefix}{age:02d}'
            pattern = f'{prefix}{birth_year}'

            cur.execute(f"""
                UPDATE games
                SET age_group = ?
                WHERE age_group != ?
                AND (
                    home_team LIKE '%{pattern}%'
                    OR away_team LIKE '%{pattern}%'
                )
            """, (correct_ag, correct_ag))
            fixed = cur.rowcount
            if fixed > 0:
                total_fixed += fixed
                print(f"  Fixed {fixed} games: {pattern} -> {correct_ag}")

    # Fix: 2014G / 2014B patterns -> G11/B11
    for birth_year in range(2005, 2020):
        age = CURRENT_YEAR - birth_year

        for suffix in ['G', 'B']:
            correct_ag = f'{suffix}{age:02d}'
            pattern = f'{birth_year}{suffix}'

            cur.execute(f"""
                UPDATE games
                SET age_group = ?
                WHERE age_group != ?
                AND (
                    home_team LIKE '%{pattern}%'
                    OR away_team LIKE '%{pattern}%'
                )
            """, (correct_ag, correct_ag))
            fixed = cur.rowcount
            if fixed > 0:
                total_fixed += fixed
                print(f"  Fixed {fixed} games: {pattern} -> {correct_ag}")

    conn.commit()
    print(f"\nTotal games fixed: {total_fixed}")

    # =========================================================================
    # TEAMS TABLE FIXES
    # =========================================================================
    print("\nFixing teams table...")

    teams_fixed = 0

    # Same patterns for teams
    for birth_year in range(2005, 2020):
        age = CURRENT_YEAR - birth_year

        for gender, prefix in [('Girls', 'G'), ('Boys', 'B')]:
            correct_ag = f'{prefix}{age:02d}'

            cur.execute(f"""
                UPDATE teams
                SET age_group = ?
                WHERE age_group != ?
                AND (
                    team_name LIKE '%{gender}%{birth_year}%'
                    OR team_name LIKE '%{birth_year}%{gender}%'
                )
            """, (correct_ag, correct_ag))
            teams_fixed += cur.rowcount

    # G2014/B2014 patterns
    for birth_year in range(2005, 2020):
        age = CURRENT_YEAR - birth_year

        for prefix in ['G', 'B']:
            correct_ag = f'{prefix}{age:02d}'
            pattern = f'{prefix}{birth_year}'

            cur.execute(f"""
                UPDATE teams
                SET age_group = ?
                WHERE age_group != ?
                AND team_name LIKE '%{pattern}%'
            """, (correct_ag, correct_ag))
            teams_fixed += cur.rowcount

    # 2014G/2014B patterns
    for birth_year in range(2005, 2020):
        age = CURRENT_YEAR - birth_year

        for suffix in ['G', 'B']:
            correct_ag = f'{suffix}{age:02d}'
            pattern = f'{birth_year}{suffix}'

            cur.execute(f"""
                UPDATE teams
                SET age_group = ?
                WHERE age_group != ?
                AND team_name LIKE '%{pattern}%'
            """, (correct_ag, correct_ag))
            teams_fixed += cur.rowcount

    conn.commit()
    print(f"Total teams fixed: {teams_fixed}")

    conn.close()
    print(f"\n[DONE] Backup saved to: {backup_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fast SQL-based age group fix')
    parser.add_argument('--db', default='seedlinedata.db', help='Database path')
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        return

    apply_fixes(args.db)


if __name__ == '__main__':
    main()
