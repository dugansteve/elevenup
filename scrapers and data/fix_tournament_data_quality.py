#!/usr/bin/env python3
"""
Fix Tournament Data Quality

This script fixes data quality issues in existing tournament games:
1. Convert U-format age groups to birth year format (U12 -> G12/B12)
2. Parse game_date to game_date_iso where missing
3. Infer gender from age_group (G12 -> Girls, B11 -> Boys)
4. Extract age/gender from team names where missing
5. Convert "13s", "14/15", "13 B" patterns in team names

Run: python fix_tournament_data_quality.py
     python fix_tournament_data_quality.py --dry-run  # Preview changes
"""

import sqlite3
import re
from datetime import datetime
import sys

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
CURRENT_YEAR = 2025

# Date parsing patterns
MONTHS = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
    'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
    'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}


def parse_date_to_iso(date_str):
    """Parse various date formats to ISO (YYYY-MM-DD)."""
    if not date_str or date_str.strip() == '':
        return None

    date_str = date_str.strip()

    # Already ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # Pattern 1: "Oct 11, 2025" or "October 11, 2025"
    match = re.match(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', date_str)
    if match:
        month_name, day, year = match.groups()
        month = MONTHS.get(month_name.lower()[:3])
        if month:
            try:
                return f"{year}-{month:02d}-{int(day):02d}"
            except:
                pass

    # Pattern 2: US format "10/11/2025"
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if match:
        try:
            month, day, year = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        except:
            pass

    return None


def extract_age_gender_from_team_name(team_name):
    """
    Extract age (birth year) and gender from team name.
    Returns: (birth_year, gender) where gender is 'G' or 'B' or None
    """
    if not team_name:
        return None, None

    birth_year = None
    gender = None

    # Pattern 1a: G13, B11, F14, M12 format
    match = re.search(r'\b([GBFM])(0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE)
    if match:
        g = match.group(1).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        birth_year = 2000 + int(match.group(2))
        return birth_year, gender

    # Pattern 1b: 13G, 11B, 14F format
    match = re.search(r'\b(0[5-9]|1[0-9]|20)([GBFM])\b', team_name, re.IGNORECASE)
    if match:
        birth_year = 2000 + int(match.group(1))
        g = match.group(2).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        return birth_year, gender

    # Pattern 1c: 2014G, G2014, 2013B, B2012 format
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

    # Pattern 2: "13 B", "14 G" with space
    match = re.search(r'\b(0[5-9]|1[0-9]|20)\s+([GBFM])\b', team_name, re.IGNORECASE)
    if match:
        birth_year = 2000 + int(match.group(1))
        g = match.group(2).upper()
        gender = 'G' if g in ('G', 'F') else 'B'
        return birth_year, gender

    # Pattern 3: "13s" pattern (like "Coppa 13s Black")
    match = re.search(r'\b(0[5-9]|1[0-9])s\b', team_name, re.IGNORECASE)
    if match:
        birth_year = 2000 + int(match.group(1))
        if re.search(r'\b(girl|female)\b', team_name, re.IGNORECASE):
            gender = 'G'
        elif re.search(r'\b(boy|male)\b', team_name, re.IGNORECASE):
            gender = 'B'
        return birth_year, gender

    # Pattern 4: "14/15" dual year pattern
    match = re.search(r'\b(0[5-9]|1[0-9])/(0[5-9]|1[0-9])\b', team_name)
    if match:
        birth_year = 2000 + int(match.group(1))
        if re.search(r'\b(girl|female)\b', team_name, re.IGNORECASE):
            gender = 'G'
        elif re.search(r'\b(boy|male)\b', team_name, re.IGNORECASE):
            gender = 'B'
        return birth_year, gender

    # Pattern 5: Full birth year with gender words
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

    # Pattern 6: Standalone birth year
    match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))\b', team_name)
    if match:
        birth_year = int(match.group(1))
        if re.search(r'\b(girl|female)\b', team_name, re.IGNORECASE):
            gender = 'G'
        elif re.search(r'\b(boy|male)\b', team_name, re.IGNORECASE):
            gender = 'B'
        return birth_year, gender

    return None, None


def fix_data_quality(dry_run=False):
    """Main function to fix data quality issues."""

    print("=" * 70)
    print("Tournament Data Quality Fix")
    print("=" * 70)
    if dry_run:
        print("*** DRY RUN MODE - No changes will be made ***")
    print()
    sys.stdout.flush()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # Faster writes
    cursor = conn.cursor()

    stats = {
        'date_iso_fixed': 0,
        'u_format_converted': 0,
        'gender_from_age_group': 0,
        'age_from_team_name': 0,
        'gender_from_team_name': 0,
    }

    # =========================================================================
    # FIX 1: Convert game_date to game_date_iso using SQL where possible
    # =========================================================================
    print("Fix 1: Converting game_date to ISO format...")
    sys.stdout.flush()

    # Handle common format: "Oct 11, 2025" etc with SQL
    month_map = [
        ('Jan ', '01'), ('Feb ', '02'), ('Mar ', '03'), ('Apr ', '04'),
        ('May ', '05'), ('Jun ', '06'), ('Jul ', '07'), ('Aug ', '08'),
        ('Sep ', '09'), ('Oct ', '10'), ('Nov ', '11'), ('Dec ', '12')
    ]

    for month_name, month_num in month_map:
        if not dry_run:
            # Pattern: "Oct 11, 2025" -> "2025-10-11"
            cursor.execute(f'''
                UPDATE games SET game_date_iso =
                    substr(game_date, -4) || '-' || '{month_num}' || '-' ||
                    CASE
                        WHEN substr(game_date, 5, 1) = ',' OR substr(game_date, 5, 1) = ' '
                        THEN '0' || substr(game_date, 4, 1)
                        ELSE substr(game_date, 4, 2)
                    END
                WHERE game_date LIKE '{month_name}%'
                AND (game_date_iso IS NULL OR game_date_iso = '')
                AND length(game_date) >= 10
            ''')
            stats['date_iso_fixed'] += cursor.rowcount
            conn.commit()
        print(f"  {month_name.strip()}: processed")
        sys.stdout.flush()

    print(f"  -> Fixed {stats['date_iso_fixed']:,} dates via SQL")
    sys.stdout.flush()

    # =========================================================================
    # FIX 2: Infer gender from age_group (G12 -> Girls, B13 -> Boys) via SQL
    # =========================================================================
    print("\nFix 2: Inferring gender from age_group...")
    sys.stdout.flush()

    if not dry_run:
        cursor.execute('''
            UPDATE games SET gender = 'Girls'
            WHERE (gender IS NULL OR gender = '')
            AND age_group LIKE 'G%'
        ''')
        girls_fixed = cursor.rowcount

        cursor.execute('''
            UPDATE games SET gender = 'Boys'
            WHERE (gender IS NULL OR gender = '')
            AND age_group LIKE 'B%'
        ''')
        boys_fixed = cursor.rowcount

        stats['gender_from_age_group'] = girls_fixed + boys_fixed
        conn.commit()
    print(f"  -> Fixed {stats['gender_from_age_group']:,} genders from age_group")
    sys.stdout.flush()

    # =========================================================================
    # FIX 3: Extract gender from team names (batch processing)
    # =========================================================================
    print("\nFix 3: Extracting gender from team names...")
    sys.stdout.flush()

    cursor.execute('''
        SELECT game_id, home_team, away_team FROM games
        WHERE (gender IS NULL OR gender = '')
        LIMIT 500000
    ''')
    rows = cursor.fetchall()
    print(f"  Found {len(rows):,} games missing gender")
    sys.stdout.flush()

    batch = []
    for i, (game_id, home_team, away_team) in enumerate(rows):
        if i % 50000 == 0 and i > 0:
            print(f"  Processing {i:,}/{len(rows):,}...")
            sys.stdout.flush()

        for team_name in [home_team, away_team]:
            _, team_gender = extract_age_gender_from_team_name(team_name)
            if team_gender:
                new_gender = 'Girls' if team_gender == 'G' else 'Boys'
                batch.append((new_gender, game_id))
                stats['gender_from_team_name'] += 1
                break

    if batch and not dry_run:
        print(f"  Applying {len(batch):,} gender updates...")
        sys.stdout.flush()
        cursor.executemany('UPDATE games SET gender = ? WHERE game_id = ?', batch)
        conn.commit()
    print(f"  -> Fixed {stats['gender_from_team_name']:,} genders from team names")
    sys.stdout.flush()

    # =========================================================================
    # FIX 4: Convert U-format to birth year format
    # =========================================================================
    print("\nFix 4: Converting U-format age groups to birth year format...")
    sys.stdout.flush()

    # U-age to birth year: U13 in 2025 = born 2012 -> G12/B12
    u_conversions = []
    for u_age in range(6, 20):
        birth_year = CURRENT_YEAR - u_age
        year_suffix = birth_year % 100
        u_conversions.append((u_age, year_suffix))

    for u_age, year_suffix in u_conversions:
        if not dry_run:
            cursor.execute(f'''
                UPDATE games SET age_group = 'G{year_suffix:02d}'
                WHERE age_group = 'U{u_age}' AND gender = 'Girls'
            ''')
            girls = cursor.rowcount

            cursor.execute(f'''
                UPDATE games SET age_group = 'B{year_suffix:02d}'
                WHERE age_group = 'U{u_age}' AND gender = 'Boys'
            ''')
            boys = cursor.rowcount

            stats['u_format_converted'] += girls + boys
            conn.commit()

    print(f"  -> Converted {stats['u_format_converted']:,} U-format to birth year")
    sys.stdout.flush()

    # =========================================================================
    # FIX 5: Extract age from team names where still missing
    # =========================================================================
    print("\nFix 5: Extracting age from team names...")
    sys.stdout.flush()

    cursor.execute('''
        SELECT game_id, home_team, away_team, gender FROM games
        WHERE (age_group IS NULL OR age_group = '')
        LIMIT 200000
    ''')
    rows = cursor.fetchall()
    print(f"  Found {len(rows):,} games still missing age_group")
    sys.stdout.flush()

    batch = []
    for i, (game_id, home_team, away_team, gender) in enumerate(rows):
        if i % 25000 == 0 and i > 0:
            print(f"  Processing {i:,}/{len(rows):,}...")
            sys.stdout.flush()

        for team_name in [home_team, away_team]:
            birth_year, team_gender = extract_age_gender_from_team_name(team_name)
            if birth_year:
                year_suffix = birth_year % 100
                g = team_gender or ('G' if gender == 'Girls' else 'B' if gender == 'Boys' else None)
                if g:
                    new_age_group = f"{g}{year_suffix:02d}"
                    batch.append((new_age_group, game_id))
                    stats['age_from_team_name'] += 1
                    break

    if batch and not dry_run:
        print(f"  Applying {len(batch):,} age updates...")
        sys.stdout.flush()
        cursor.executemany('UPDATE games SET age_group = ? WHERE game_id = ?', batch)
        conn.commit()
    print(f"  -> Fixed {stats['age_from_team_name']:,} age groups from team names")
    sys.stdout.flush()

    # =========================================================================
    # Summary
    # =========================================================================
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for key, value in stats.items():
        print(f"  {key}: {value:,}")

    total_fixes = sum(stats.values())
    print(f"\n  Total fixes: {total_fixes:,}")

    if dry_run:
        print("\n*** DRY RUN - No changes were made ***")
    else:
        print("\nAll fixes applied!")

    # Final quality check
    print()
    print("=" * 70)
    print("FINAL DATA QUALITY CHECK")
    print("=" * 70)

    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0]

    cursor.execute('''SELECT
        SUM(CASE WHEN age_group LIKE 'G%' OR age_group LIKE 'B%' THEN 1 ELSE 0 END),
        SUM(CASE WHEN age_group LIKE 'U%' THEN 1 ELSE 0 END),
        SUM(CASE WHEN age_group IS NULL OR age_group = '' THEN 1 ELSE 0 END)
    FROM games''')
    row = cursor.fetchone()
    print(f"\nAge groups:")
    print(f"  Birth year format: {row[0]:,} ({100*row[0]/total:.1f}%)")
    print(f"  U-format:          {row[1]:,} ({100*row[1]/total:.1f}%)")
    print(f"  Missing:           {row[2]:,} ({100*row[2]/total:.1f}%)")

    cursor.execute('''SELECT
        SUM(CASE WHEN gender = 'Boys' OR gender = 'Girls' THEN 1 ELSE 0 END),
        SUM(CASE WHEN gender IS NULL OR gender = '' THEN 1 ELSE 0 END)
    FROM games''')
    row = cursor.fetchone()
    print(f"\nGender:")
    print(f"  Has gender: {row[0]:,} ({100*row[0]/total:.1f}%)")
    print(f"  Missing:    {row[1]:,} ({100*row[1]/total:.1f}%)")

    cursor.execute('''SELECT
        SUM(CASE WHEN game_date_iso IS NOT NULL AND game_date_iso != '' THEN 1 ELSE 0 END),
        SUM(CASE WHEN game_date_iso IS NULL OR game_date_iso = '' THEN 1 ELSE 0 END)
    FROM games''')
    row = cursor.fetchone()
    print(f"\nDates:")
    print(f"  Has ISO date: {row[0]:,} ({100*row[0]/total:.1f}%)")
    print(f"  Missing:      {row[1]:,} ({100*row[1]/total:.1f}%)")

    conn.close()


if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    fix_data_quality(dry_run)
