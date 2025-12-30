#!/usr/bin/env python3
"""
Export Tournaments to JSON for React App

Exports tournament data from the database to a JSON file
that the React frontend can load.

Usage:
    python export_tournaments_json.py
"""

import json
import os
import sqlite3
import shutil
from datetime import datetime

# Paths
SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(SCRAPER_DIR), 'seedlinedata.db')
OUTPUT_FILE = 'tournaments_data.json'
REACT_PUBLIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(SCRAPER_DIR))),
    'App FrontEnd', 'Seedline_App', 'public'
)


def parse_date_string(dates_str, has_results=False):
    """Parse a date string like 'December 5-7' or 'January 17-19 2026' to ISO format

    Args:
        dates_str: The date string to parse
        has_results: If True, tournament has already occurred (use past year if needed)
                    If False, tournament is upcoming (use future year if needed)
    """
    import re
    if not dates_str:
        return None

    # Month name mapping
    month_map = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
        'oct': '10', 'nov': '11', 'dec': '12'
    }

    now = datetime.now()
    current_year = now.year

    # Try pattern: "Month Day-Day Year" or "Month Day-Day, Year" or "Month Day-Day"
    match = re.search(r'(\w+)\s+(\d{1,2})(?:-\d{1,2})?(?:,?\s*(\d{4}))?', dates_str, re.IGNORECASE)
    if match:
        month_str = match.group(1).lower()
        day = match.group(2).zfill(2)
        explicit_year = match.group(3)

        month = month_map.get(month_str)
        if month:
            if explicit_year:
                # Year was specified in the string
                year = explicit_year
            else:
                # No year specified - determine based on whether tournament has results
                month_num = int(month)
                day_num = int(day)

                if has_results:
                    # Tournament has results, so it's in the past
                    # If the date hasn't occurred yet this year, it was last year
                    tournament_date = datetime(current_year, month_num, day_num)
                    if tournament_date > now:
                        year = str(current_year - 1)
                    else:
                        year = str(current_year)
                else:
                    # Tournament has no results, so it's upcoming
                    # Use 2025 as base year for upcoming tournaments
                    # If date is in a month that's already passed in 2025, use 2026
                    base_year = 2025
                    tournament_date = datetime(base_year, month_num, day_num)
                    # If we're past Dec 2024 and looking at early months, those are 2025
                    # If looking at Dec dates without results, those are Dec 2025
                    year = str(base_year)

                    # If the month is before current month and we're in late year,
                    # it might be next year
                    if month_num < now.month and now.month >= 10:
                        year = str(base_year + 1)

            return f"{year}-{month}-{day}"

    # Try pattern with just month and year: "March 2025"
    match = re.search(r'(\w+)\s+(\d{4})', dates_str, re.IGNORECASE)
    if match:
        month_str = match.group(1).lower()
        year = match.group(2)
        month = month_map.get(month_str)
        if month:
            return f"{year}-{month}-01"

    return None


def export_tournaments():
    """Export tournaments from database to JSON"""
    print("=" * 60)
    print("EXPORT TOURNAMENTS TO JSON")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Output: {OUTPUT_FILE}")

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if tournaments table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tournaments'")
    if not cursor.fetchone():
        print("Tournaments table not found!")
        conn.close()
        return

    # Get all tournaments
    cursor.execute('''
        SELECT
            event_id, platform, name, dates, start_date, state, city,
            age_groups, schedule_url, website_url, status, game_count, sponsor,
            latitude, longitude
        FROM tournaments
        ORDER BY start_date ASC
    ''')

    tournaments = []
    for row in cursor.fetchall():
        # Determine if tournament has results (meaning it's in the past)
        game_count = row['game_count'] or 0
        has_results = game_count > 0

        # Always recalculate start_date from dates field to ensure correct year
        # (based on whether tournament has results or not)
        start_date = None
        if row['dates']:
            start_date = parse_date_string(row['dates'], has_results=has_results)
        # Fall back to DB value if parsing failed
        if not start_date:
            start_date = row['start_date']

        tournament = {
            'event_id': row['event_id'],
            'platform': row['platform'],
            'name': row['name'],
            'dates': row['dates'],
            'start_date': start_date,
            'state': row['state'],
            'city': row['city'] or '',
            'age_groups': row['age_groups'],
            'schedule_url': row['schedule_url'],
            'website_url': row['website_url'],
            'status': row['status'],
            'game_count': row['game_count'] or 0,
            'sponsor': row['sponsor'] or '',
            'latitude': row['latitude'],
            'longitude': row['longitude'],
        }

        # Add gender (default to Both, would need to add to DB)
        tournament['gender'] = 'Both'

        # Add level (default based on name patterns)
        name_lower = (row['name'] or '').lower()
        if 'showcase' in name_lower:
            tournament['level'] = 'Showcase'
        elif 'elite' in name_lower or 'premier' in name_lower:
            tournament['level'] = 'Elite'
        elif 'recreational' in name_lower or 'rec' in name_lower:
            tournament['level'] = 'Recreational'
        else:
            tournament['level'] = 'Competitive'

        tournaments.append(tournament)

    conn.close()

    # Sort by start_date
    tournaments.sort(key=lambda x: x['start_date'] or '9999-99-99')

    # Create output data
    output = {
        'tournaments': tournaments,
        'last_updated': datetime.now().isoformat(),
        'count': len(tournaments)
    }

    # Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\nExported {len(tournaments)} tournaments")

    # Copy to React public folder if it exists
    if os.path.exists(REACT_PUBLIC_DIR):
        dest_path = os.path.join(REACT_PUBLIC_DIR, OUTPUT_FILE)
        shutil.copy(OUTPUT_FILE, dest_path)
        print(f"Copied to: {dest_path}")
    else:
        print(f"React public dir not found: {REACT_PUBLIC_DIR}")
        print("Please copy tournaments_data.json to your React app's public folder")

    print("\nDone!")


if __name__ == "__main__":
    export_tournaments()
