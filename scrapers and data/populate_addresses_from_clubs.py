#!/usr/bin/env python3
"""
Populate address data for teams from club_addresses.json

When a team has a club_name that matches a club in club_addresses.json,
copy the club's address (city, state, street_address, zip_code) to the team.

This NEVER overwrites existing address data - only fills in NULL/empty fields.
"""

import sqlite3
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / 'seedlinedata.db'
CLUB_ADDR_PATH = SCRIPT_DIR.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'


def normalize_name(name):
    """Normalize club/team name for matching."""
    if not name:
        return ''
    # Lowercase, strip whitespace
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [' sc', ' fc', ' soccer', ' club', ' academy', ' youth']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name


def find_club_in_compound_name(compound_name, clubs_lower_set):
    """
    Try to find a known club name inside a compound name like
    "Mt Diablo Mustang Soccer Mt. Diablo Mustang"
    Returns the club data if found, None otherwise.
    """
    if not compound_name:
        return None

    name_lower = compound_name.lower()

    # Check if any known club name is a substring
    for club_name in clubs_lower_set:
        if club_name in name_lower and len(club_name) > 4:  # Avoid tiny matches
            return club_name

    return None


def main():
    print("=" * 70)
    print("POPULATE ADDRESS DATA FROM CLUB_ADDRESSES.JSON")
    print("=" * 70)
    print()

    # Load club_addresses.json
    print(f"Loading {CLUB_ADDR_PATH.name}...")
    with open(CLUB_ADDR_PATH, 'r') as f:
        addresses = json.load(f)

    clubs = addresses.get('clubs', {})
    teams_addr = addresses.get('teams', {})

    print(f"  - {len(clubs)} clubs")
    print(f"  - {len(teams_addr)} teams")
    print()

    # Build normalized lookup with multiple key variations
    clubs_normalized = {}
    clubs_by_prefix = {}  # Keyed by first N words

    for name, data in clubs.items():
        if data.get('city') or data.get('state'):
            clubs_normalized[normalize_name(name)] = data
            clubs_normalized[name.lower()] = data  # Also exact match

            # Build prefix lookups (2, 3, 4 word prefixes)
            words = name.lower().split()
            for n in [2, 3, 4]:
                if len(words) >= n:
                    prefix = ' '.join(words[:n])
                    if prefix not in clubs_by_prefix:
                        clubs_by_prefix[prefix] = data

    # Build list of all known club names for substring matching
    clubs_lower_set = set(clubs_normalized.keys())

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Build team name lookup too
    teams_normalized = {}
    for name, data in teams_addr.items():
        if data.get('city') or data.get('state'):
            teams_normalized[normalize_name(name)] = data
            teams_normalized[name.lower()] = data

    # Get teams missing address data
    c.execute("""
        SELECT id, team_name, club_name, city, state, street_address, zip_code
        FROM teams
        WHERE (city IS NULL OR city = '' OR state IS NULL OR state = '')
    """)

    teams_to_update = c.fetchall()
    print(f"Teams missing address data with club_name: {len(teams_to_update)}")
    print()

    # Track updates
    updated_count = 0
    updated_by_league = {}
    not_found = 0

    for team in teams_to_update:
        club_name = team['club_name']
        team_id = team['id']

        # Try to find address data in JSON
        club_data = None
        team_name = team['team_name'] or ''

        # Strategy 1: Exact club match
        if club_name and club_name in clubs:
            club_data = clubs[club_name]
        # Strategy 2: Lowercase club match
        elif club_name and club_name.lower() in clubs_normalized:
            club_data = clubs_normalized[club_name.lower()]
        # Strategy 3: Normalized club match
        elif club_name and normalize_name(club_name) in clubs_normalized:
            club_data = clubs_normalized[normalize_name(club_name)]

        # Strategy 4: Club first 2, 3, 4 words (prefix matching)
        if not club_data and club_name:
            words = club_name.split()
            for n in [4, 3, 2]:  # Try longer prefixes first
                if len(words) >= n:
                    prefix = ' '.join(words[:n]).lower()
                    if prefix in clubs_by_prefix:
                        club_data = clubs_by_prefix[prefix]
                        break
                    # Also try in normalized
                    if prefix in clubs_normalized:
                        club_data = clubs_normalized[prefix]
                        break

        # Strategy 5: Substring matching - find known club name inside compound name
        if not club_data and club_name:
            found_club = find_club_in_compound_name(club_name, clubs_lower_set)
            if found_club:
                club_data = clubs_normalized.get(found_club)

        # Strategy 6: Try team name in teams lookup
        if not club_data and team_name:
            if team_name in teams_addr:
                club_data = teams_addr[team_name]
            elif team_name.lower() in teams_normalized:
                club_data = teams_normalized[team_name.lower()]
            elif normalize_name(team_name) in teams_normalized:
                club_data = teams_normalized[normalize_name(team_name)]

        # Strategy 7: Try team name prefix in clubs
        if not club_data and team_name:
            words = team_name.split()
            for n in [4, 3, 2]:
                if len(words) >= n:
                    prefix = ' '.join(words[:n]).lower()
                    if prefix in clubs_by_prefix:
                        club_data = clubs_by_prefix[prefix]
                        break
                    if prefix in clubs_normalized:
                        club_data = clubs_normalized[prefix]
                        break

        # Strategy 8: Substring matching on team name
        if not club_data and team_name:
            found_club = find_club_in_compound_name(team_name, clubs_lower_set)
            if found_club:
                club_data = clubs_normalized.get(found_club)

        if club_data:
            # Build update - only fill NULL/empty fields
            new_city = club_data.get('city', '')
            new_state = club_data.get('state', '')
            new_street = club_data.get('streetAddress', '')
            new_zip = club_data.get('zipCode', '')

            # Only update if we have something to add
            updates = []
            params = []

            if (not team['city']) and new_city:
                updates.append("city = ?")
                params.append(new_city)
            if (not team['state']) and new_state:
                updates.append("state = ?")
                params.append(new_state)
            if (not team['street_address']) and new_street:
                updates.append("street_address = ?")
                params.append(new_street)
            if (not team['zip_code']) and new_zip:
                updates.append("zip_code = ?")
                params.append(new_zip)

            if updates:
                sql = f"UPDATE teams SET {', '.join(updates)} WHERE id = ?"
                params.append(team_id)
                c.execute(sql, params)
                updated_count += 1

                # Track by league (get league for this team)
                c.execute("SELECT league FROM teams WHERE id = ?", (team_id,))
                league = c.fetchone()[0]
                updated_by_league[league] = updated_by_league.get(league, 0) + 1
        else:
            not_found += 1

    conn.commit()

    print(f"Updated: {updated_count} teams")
    print(f"Not found in JSON: {not_found}")
    print()

    if updated_by_league:
        print("Updates by league:")
        for league, count in sorted(updated_by_league.items(), key=lambda x: -x[1]):
            print(f"  {league}: {count}")

    # Final summary
    print()
    print("=" * 70)
    print("FINAL ADDRESS COVERAGE")
    print("=" * 70)

    c.execute("""
        SELECT league,
            COUNT(*) as total,
            SUM(CASE WHEN city IS NOT NULL AND city <> '' THEN 1 ELSE 0 END) as has_city,
            SUM(CASE WHEN state IS NOT NULL AND state <> '' THEN 1 ELSE 0 END) as has_state
        FROM teams
        WHERE league IN ('ECNL', 'ECNL RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT')
        GROUP BY league
        ORDER BY total DESC
    """)

    print()
    print(f"{'League':15} | {'Total':>6} | {'City':>6} | {'State':>6}")
    print("-" * 50)
    for row in c.fetchall():
        print(f"{row[0]:15} | {row[1]:6} | {row[2]:6} | {row[3]:6}")

    conn.close()


if __name__ == '__main__':
    main()
