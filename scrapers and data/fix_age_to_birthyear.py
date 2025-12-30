#!/usr/bin/env python3
"""
Fix age group format: Convert from age-based (B14 = 14 years old) to birth year (B14 = born 2014)

Current database has:
  B14 meaning "14 year old" (born 2011)

Should be:
  B11 meaning "born 2011"

Conversion: birth_year = 2025 - age
  B14 (age 14) → B11 (born 2011)
  B13 (age 13) → B12 (born 2012)
  B12 (age 12) → B13 (born 2013)
  B11 (age 11) → B14 (born 2014)
  B10 (age 10) → B15 (born 2015)
  etc.
"""

import sqlite3
import re

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
CURRENT_YEAR = 2025

def convert_age_to_birthyear(age_group):
    """Convert age-based format to birth year format"""
    if not age_group:
        return None

    # Match patterns like B14, G13, B10, G11, etc.
    match = re.match(r'^([BG])(\d{1,2})$', age_group)
    if match:
        gender = match.group(1)
        age = int(match.group(2))

        # Only convert reasonable ages (8-19)
        if 8 <= age <= 19:
            birth_year = CURRENT_YEAR - age
            birth_suffix = str(birth_year)[-2:]  # "2011" -> "11"
            return f"{gender}{birth_suffix}"

    # Match U-age patterns like U14, U13
    match = re.match(r'^U(\d{1,2})$', age_group)
    if match:
        age = int(match.group(1))
        if 8 <= age <= 19:
            birth_year = CURRENT_YEAR - age
            birth_suffix = str(birth_year)[-2:]
            return birth_suffix  # Return just the year without gender prefix

    # Already in birth year format (09, 10, 11, 12, etc.) - leave as is
    if re.match(r'^(0[89]|1[0-9])$', age_group):
        return age_group

    # Already in birth year format with gender (B11, G12 where 11/12 are birth years)
    # These would be ages 14 and 13 respectively - we need to detect which format
    # For now, assume all B/G + 2 digit are age format if the number is 10-19

    return None  # Don't change if we can't parse


def fix_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all unique age groups
    age_groups = cursor.execute('''
        SELECT DISTINCT age_group, COUNT(*) as cnt
        FROM tournament_games
        WHERE age_group IS NOT NULL AND age_group != ''
        GROUP BY age_group
        ORDER BY cnt DESC
    ''').fetchall()

    print(f"Found {len(age_groups)} unique age group values")
    print("\nConversion plan:")
    print("-" * 40)

    conversions = {}
    for ag, cnt in age_groups:
        new_ag = convert_age_to_birthyear(ag)
        if new_ag and new_ag != ag:
            conversions[ag] = new_ag
            print(f"  {ag} -> {new_ag} ({cnt} games)")
        else:
            print(f"  {ag} -> (no change) ({cnt} games)")

    if not conversions:
        print("\nNo conversions needed!")
        conn.close()
        return

    print(f"\nApplying {len(conversions)} conversions...")

    total_updated = 0
    for old_ag, new_ag in conversions.items():
        cursor.execute('''
            UPDATE tournament_games
            SET age_group = ?
            WHERE age_group = ?
        ''', (new_ag, old_ag))
        updated = cursor.rowcount
        total_updated += updated
        print(f"  {old_ag} -> {new_ag}: {updated} rows")

    conn.commit()

    # Show new distribution
    print("\nNew age group distribution:")
    print("-" * 40)
    for row in cursor.execute('''
        SELECT age_group, COUNT(*) as cnt
        FROM tournament_games
        WHERE age_group IS NOT NULL AND age_group != ''
        GROUP BY age_group
        ORDER BY cnt DESC
        LIMIT 20
    ''').fetchall():
        print(f"  {row[0]}: {row[1]}")

    conn.close()
    print(f"\nTotal rows updated: {total_updated}")


if __name__ == "__main__":
    fix_database()
