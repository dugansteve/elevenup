#!/usr/bin/env python3
"""Fix remaining data quality issues - to be run after fix_tournament_data_quality.py"""

import sqlite3
import re
import sys

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
CURRENT_YEAR = 2025

def extract_gender_only(team_name):
    """Quick gender extraction from team name."""
    if not team_name:
        return None

    # Pattern: G13, B11, F14, M12
    if re.search(r'\b[GF](0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE):
        return 'Girls'
    if re.search(r'\b[BM](0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE):
        return 'Boys'

    # Pattern: 13G, 11B
    if re.search(r'\b(0[5-9]|1[0-9]|20)[GF]\b', team_name, re.IGNORECASE):
        return 'Girls'
    if re.search(r'\b(0[5-9]|1[0-9]|20)[BM]\b', team_name, re.IGNORECASE):
        return 'Boys'

    # Pattern: 2014G, G2014
    if re.search(r'\b20(0[5-9]|1[0-9]|20)[GF]\b|\b[GF]20(0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE):
        return 'Girls'
    if re.search(r'\b20(0[5-9]|1[0-9]|20)[BM]\b|\b[BM]20(0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE):
        return 'Boys'

    # Words
    if re.search(r'\b(girls?|female)\b', team_name, re.IGNORECASE):
        return 'Girls'
    if re.search(r'\b(boys?|male)\b', team_name, re.IGNORECASE):
        return 'Boys'

    return None


def extract_birth_year_and_gender(team_name):
    """Extract birth year and gender from team name."""
    if not team_name:
        return None, None

    birth_year = None
    gender = None

    # G13, B11, F14, M12
    match = re.search(r'\b([GBFM])(0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE)
    if match:
        g = match.group(1).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        birth_year = 2000 + int(match.group(2))
        return birth_year, gender

    # 13G, 11B
    match = re.search(r'\b(0[5-9]|1[0-9]|20)([GBFM])\b', team_name, re.IGNORECASE)
    if match:
        birth_year = 2000 + int(match.group(1))
        g = match.group(2).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        return birth_year, gender

    # 2014G, G2014
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))([GBFM])\b', team_name, re.IGNORECASE)
    if match:
        birth_year = int(match.group(1))
        g = match.group(2).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        return birth_year, gender

    match = re.search(r'\b([GBFM])(20(?:0[5-9]|1[0-9]|20))\b', team_name, re.IGNORECASE)
    if match:
        g = match.group(1).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        birth_year = int(match.group(2))
        return birth_year, gender

    # 13 B, 14 G with space
    match = re.search(r'\b(0[5-9]|1[0-9]|20)\s+([GBFM])\b', team_name, re.IGNORECASE)
    if match:
        birth_year = 2000 + int(match.group(1))
        g = match.group(2).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        return birth_year, gender

    # 13s pattern
    match = re.search(r'\b(0[5-9]|1[0-9])s\b', team_name, re.IGNORECASE)
    if match:
        birth_year = 2000 + int(match.group(1))
        if re.search(r'\b(girl|female)\b', team_name, re.IGNORECASE):
            gender = 'G'
        elif re.search(r'\b(boy|male)\b', team_name, re.IGNORECASE):
            gender = 'B'
        return birth_year, gender

    # 14/15 dual year
    match = re.search(r'\b(0[5-9]|1[0-9])/(0[5-9]|1[0-9])\b', team_name)
    if match:
        birth_year = 2000 + int(match.group(1))
        if re.search(r'\b(girl|female)\b', team_name, re.IGNORECASE):
            gender = 'G'
        elif re.search(r'\b(boy|male)\b', team_name, re.IGNORECASE):
            gender = 'B'
        return birth_year, gender

    # 2012 Girls, Girls 2012
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))\s*(Girls?|Boys?|Female|Male)\b', team_name, re.IGNORECASE)
    if match:
        birth_year = int(match.group(1))
        g = match.group(2).lower()
        gender = 'B' if g.startswith('boy') or g.startswith('male') else 'G'
        return birth_year, gender

    match = re.search(r'\b(Girls?|Boys?|Female|Male)\s*(20(?:0[5-9]|1[0-9]|20))\b', team_name, re.IGNORECASE)
    if match:
        g = match.group(1).lower()
        gender = 'B' if g.startswith('boy') or g.startswith('male') else 'G'
        birth_year = int(match.group(2))
        return birth_year, gender

    # Standalone year
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))\b', team_name)
    if match:
        birth_year = int(match.group(1))
        if re.search(r'\b(girl|female)\b', team_name, re.IGNORECASE):
            gender = 'G'
        elif re.search(r'\b(boy|male)\b', team_name, re.IGNORECASE):
            gender = 'B'
        return birth_year, gender

    return None, None


def main():
    print("=" * 60)
    print("Fixing remaining data quality issues")
    print("=" * 60)
    print()
    sys.stdout.flush()

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    # Check current state
    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0]
    print(f"Total games: {total:,}")
    sys.stdout.flush()

    # FIX 1: Gender from team names
    print("\nFix 1: Extracting gender from team names...")
    sys.stdout.flush()
    cursor.execute('SELECT COUNT(*) FROM games WHERE gender IS NULL OR gender = ""')
    missing = cursor.fetchone()[0]
    print(f"  Missing gender: {missing:,}")
    sys.stdout.flush()

    if missing > 0:
        fixed = 0
        batch_size = 10000

        while True:
            cursor.execute('''
                SELECT game_id, home_team, away_team FROM games
                WHERE (gender IS NULL OR gender = '')
                LIMIT ?
            ''', (batch_size,))
            rows = cursor.fetchall()

            if not rows:
                break

            updates = []
            for game_id, home_team, away_team in rows:
                gender = extract_gender_only(home_team) or extract_gender_only(away_team)
                if gender:
                    updates.append((gender, game_id))

            if updates:
                cursor.executemany('UPDATE games SET gender = ? WHERE game_id = ?', updates)
                conn.commit()
                fixed += len(updates)
                print(f"    Fixed {fixed:,}...")
                sys.stdout.flush()

            # If we didn't find any gender in this batch, break to avoid infinite loop
            if not updates:
                break

        print(f"  -> Total fixed: {fixed:,}")
        sys.stdout.flush()

    # FIX 2: U-format to birth year
    print("\nFix 2: Converting U-format to birth year...")
    sys.stdout.flush()
    u_fixed = 0
    for u_age in range(6, 20):
        birth_year = CURRENT_YEAR - u_age
        suffix = birth_year % 100

        cursor.execute(f"UPDATE games SET age_group = 'G{suffix:02d}' WHERE age_group = 'U{u_age}' AND gender = 'Girls'")
        u_fixed += cursor.rowcount
        cursor.execute(f"UPDATE games SET age_group = 'B{suffix:02d}' WHERE age_group = 'U{u_age}' AND gender = 'Boys'")
        u_fixed += cursor.rowcount
        conn.commit()

    print(f"  -> Converted {u_fixed:,} U-format age groups")
    sys.stdout.flush()

    # FIX 3: Age from team names
    print("\nFix 3: Extracting age from team names...")
    sys.stdout.flush()
    cursor.execute('SELECT COUNT(*) FROM games WHERE age_group IS NULL OR age_group = ""')
    missing = cursor.fetchone()[0]
    print(f"  Missing age: {missing:,}")
    sys.stdout.flush()

    if missing > 0:
        fixed = 0
        batch_size = 10000

        while True:
            cursor.execute('''
                SELECT game_id, home_team, away_team, gender FROM games
                WHERE (age_group IS NULL OR age_group = '')
                LIMIT ?
            ''', (batch_size,))
            rows = cursor.fetchall()

            if not rows:
                break

            updates = []
            for game_id, home_team, away_team, gender in rows:
                for team_name in [home_team, away_team]:
                    birth_year, team_gender = extract_birth_year_and_gender(team_name)
                    if birth_year:
                        suffix = birth_year % 100
                        g = team_gender or ('G' if gender == 'Girls' else 'B' if gender == 'Boys' else None)
                        if g:
                            updates.append((f"{g}{suffix:02d}", game_id))
                            break

            if updates:
                cursor.executemany('UPDATE games SET age_group = ? WHERE game_id = ?', updates)
                conn.commit()
                fixed += len(updates)
                print(f"    Fixed {fixed:,}...")
                sys.stdout.flush()

            # If we didn't find any age in this batch, break
            if not updates:
                break

        print(f"  -> Total fixed: {fixed:,}")
        sys.stdout.flush()

    # Final stats
    print("\n" + "=" * 60)
    print("FINAL STATUS")
    print("=" * 60)

    cursor.execute('SELECT COUNT(*) FROM games WHERE game_date_iso IS NOT NULL AND game_date_iso != ""')
    print(f"Games with ISO date: {cursor.fetchone()[0]:,}")

    cursor.execute('SELECT COUNT(*) FROM games WHERE gender IS NOT NULL AND gender != ""')
    print(f"Games with gender: {cursor.fetchone()[0]:,}")

    cursor.execute('SELECT COUNT(*) FROM games WHERE age_group LIKE "G%" OR age_group LIKE "B%"')
    print(f"Games with birth-year age: {cursor.fetchone()[0]:,}")

    cursor.execute('SELECT COUNT(*) FROM games WHERE age_group LIKE "U%"')
    print(f"Games with U-format age: {cursor.fetchone()[0]:,}")

    cursor.execute('SELECT COUNT(*) FROM games WHERE age_group IS NULL OR age_group = ""')
    print(f"Games missing age: {cursor.fetchone()[0]:,}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
