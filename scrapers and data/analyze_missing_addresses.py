#!/usr/bin/env python3
"""Analyze teams missing address data and check if they can be fixed from club_addresses.json"""

import sqlite3
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / 'seedlinedata.db'
CLUB_ADDR_PATH = SCRIPT_DIR.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'

def main():
    # Load club_addresses.json
    with open(CLUB_ADDR_PATH, 'r') as f:
        addresses = json.load(f)

    clubs = addresses.get('clubs', {})
    teams_addr = addresses.get('teams', {})

    print('=' * 70)
    print('ANALYZE MISSING ADDRESS DATA')
    print('=' * 70)
    print()
    print(f'club_addresses.json has:')
    print(f'  - {len(clubs)} clubs with addresses')
    print(f'  - {len(teams_addr)} teams with addresses')
    print()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Find teams missing city but have club_name
    c.execute("""
        SELECT club_name, COUNT(*) as cnt
        FROM teams
        WHERE (city IS NULL OR city = '')
          AND club_name IS NOT NULL AND club_name <> ''
        GROUP BY club_name
        ORDER BY cnt DESC
        LIMIT 30
    """)

    print('Top 30 clubs with teams missing city data:')
    print('-' * 70)
    total_fixable = 0
    total_not_fixable = 0

    for club_name, cnt in c.fetchall():
        # Check if club is in our JSON
        in_json = club_name in clubs
        if in_json:
            total_fixable += cnt
            status = 'CAN FIX'
        else:
            total_not_fixable += cnt
            status = 'NOT IN JSON'
        print(f'  {club_name[:45]:45} | {cnt:4} teams | {status}')

    print()
    print('-' * 70)

    # Total counts
    c.execute("""
        SELECT COUNT(*) FROM teams
        WHERE (city IS NULL OR city = '')
          AND club_name IS NOT NULL AND club_name <> ''
    """)
    missing_with_club = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM teams
        WHERE (city IS NULL OR city = '')
          AND (club_name IS NULL OR club_name = '')
    """)
    missing_no_club = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM teams WHERE city IS NULL OR city = ''")
    total_missing = c.fetchone()[0]

    print()
    print('SUMMARY:')
    print(f'  Teams missing city data: {total_missing:,}')
    print(f'    - With club_name: {missing_with_club:,}')
    print(f'    - Without club_name: {missing_no_club:,}')
    print()

    # Check how many club_names in DB match clubs in JSON
    c.execute("""
        SELECT DISTINCT club_name FROM teams
        WHERE (city IS NULL OR city = '')
          AND club_name IS NOT NULL AND club_name <> ''
    """)
    missing_clubs = [row[0] for row in c.fetchall()]

    matches = sum(1 for club in missing_clubs if club in clubs)
    print(f'  Clubs with missing data that ARE in JSON: {matches}/{len(missing_clubs)}')

    # How many teams could be fixed?
    c.execute("""
        SELECT COUNT(*) FROM teams
        WHERE (city IS NULL OR city = '')
          AND club_name IS NOT NULL AND club_name <> ''
    """)
    # Re-check with actual matches
    fixable_count = 0
    for club in missing_clubs:
        if club in clubs:
            c.execute("SELECT COUNT(*) FROM teams WHERE club_name = ? AND (city IS NULL OR city = '')", (club,))
            fixable_count += c.fetchone()[0]

    print(f'  Teams that COULD be fixed from club_addresses.json: {fixable_count:,}')

    conn.close()

if __name__ == '__main__':
    main()
