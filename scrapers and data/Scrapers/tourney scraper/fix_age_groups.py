#!/usr/bin/env python3
"""Fix blank age groups by extracting from division names"""

import sqlite3
import re

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

def extract_age_group(division):
    """Extract age group from division string"""
    if not division:
        return None

    # Birth year patterns: B2011, G2014, 2011B, etc
    # Convention: Gxx = birth year 20xx (G14 = born 2014, NOT age 14)
    match = re.search(r'[BG]?20(1[0-9]|0[89])[BG]?', division)
    if match:
        birth_year_suffix = match.group(1)  # "11" for 2011, "14" for 2014
        # Determine gender from context
        if 'B20' in match.group() or match.group().endswith('B'):
            return f'B{birth_year_suffix}'
        elif 'G20' in match.group() or match.group().endswith('G'):
            return f'G{birth_year_suffix}'
        # Check broader context
        if re.search(r'\bboy', division, re.IGNORECASE):
            return f'B{birth_year_suffix}'
        elif re.search(r'\bgirl', division, re.IGNORECASE):
            return f'G{birth_year_suffix}'
        return birth_year_suffix  # Just birth year suffix without gender

    # U-age patterns: U13, U14, U15B, U16G
    match = re.search(r'U(1[0-9])\s*([BG])?', division, re.IGNORECASE)
    if match:
        age = match.group(1)
        gender = match.group(2)
        if gender:
            return f'{gender.upper()}{age}'
        # Check context
        if re.search(r'\bboy', division, re.IGNORECASE):
            return f'B{age}'
        elif re.search(r'\bgirl', division, re.IGNORECASE):
            return f'G{age}'
        return f'U{age}'

    # Age-U patterns: 13U, 14U
    match = re.search(r'(1[0-9])U', division, re.IGNORECASE)
    if match:
        age = match.group(1)
        if re.search(r'\bboy', division, re.IGNORECASE):
            return f'B{age}'
        elif re.search(r'\bgirl', division, re.IGNORECASE):
            return f'G{age}'
        return f'U{age}'

    # Boys/Girls with age number
    match = re.search(r'(Boys?|Girls?)\s*\(?(\d{1,2})\)?', division, re.IGNORECASE)
    if match:
        gender = 'B' if 'Boy' in match.group(1) else 'G'
        age = match.group(2)
        if int(age) >= 8 and int(age) <= 19:
            return f'{gender}{age}'

    return None


def fix_age_groups():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all games with blank age groups but have division info
    games = cursor.execute('''
        SELECT id, division, tournament_name
        FROM tournament_games
        WHERE (age_group IS NULL OR age_group = '')
        AND division IS NOT NULL AND division != ''
    ''').fetchall()

    print(f'Found {len(games)} games with blank age_group but have division')

    updated = 0
    samples = []

    for game_id, division, tournament in games:
        age_group = extract_age_group(division)

        if age_group:
            cursor.execute('UPDATE tournament_games SET age_group = ? WHERE id = ?',
                         (age_group, game_id))
            updated += 1
            if len(samples) < 10:
                samples.append((division[:50], age_group))

    conn.commit()

    print(f'\nUpdated {updated} games with extracted age groups')
    print('\nSamples:')
    for div, ag in samples:
        print(f'  "{div}" -> {ag}')

    # Check remaining blanks
    blanks = cursor.execute('SELECT COUNT(*) FROM tournament_games WHERE age_group IS NULL OR age_group = ""').fetchone()[0]
    print(f'\nRemaining blank age groups: {blanks}')

    conn.close()


if __name__ == "__main__":
    fix_age_groups()
