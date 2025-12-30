#!/usr/bin/env python3
"""
Export club addresses from database to club_addresses.json for the React app map.
Includes geocoding to get lat/lng coordinates for accurate map pins.

UPDATED: Added validation to prevent GA (Georgia) / GA (Girls Academy) confusion.
"""

import sqlite3
import json
import time
from pathlib import Path

# Known Georgia clubs - used to validate Georgia state assignments
GEORGIA_CLUBS = [
    'tophat', 'concorde fire', 'gwinnett', 'southern soccer', 'ssa swarm',
    'nasa tophat', 'nth tophat', 'nth-nasa', 'nth nasa', 'atlanta fire',
    'atlanta united', 'inter atlanta', 'united futbol', 'ufa ', 'georgia',
    'legion futbol', 'legion fc', 'peach', 'afc lightning', 'all-in fc',
    'alliance sc', 'athens united', 'auburn soccer', 'chargers soccer',
    'decatur', 'eastshore', 'fayetteville', 'villarreal force', 'north georgia',
    'roswell santos', 'rush union', 'springs soccer', 'steamers fc',
    'triumph youth', 'ymca arsenal rome', 'metro atlanta', 'lanier soccer',
    'pike soccer', 'fury fc', 'brevard', 'gsa force', 'winnett soccer',
]

def is_georgia_club(name: str) -> bool:
    """Check if a name matches a known Georgia club."""
    if not name:
        return False
    name_lower = name.lower()
    return any(club in name_lower for club in GEORGIA_CLUBS)

def has_ga_league_suffix(name: str) -> bool:
    """Check if name has ' GA' suffix indicating Girls Academy league."""
    if not name:
        return False
    name_upper = name.upper().strip()
    return name_upper.endswith(' GA') or ' GA ' in name_upper

def validate_state(state: str, team_name: str, club_name: str) -> str:
    """
    Validate state to prevent GA (Georgia) / GA (Girls Academy) confusion.

    Returns empty string if the state assignment appears to be incorrect.
    """
    if not state:
        return ''

    state_upper = state.upper().strip()

    # Check for Georgia/GA state
    if state_upper in ('GA', 'GEORGIA'):
        # If team/club name has ' GA' suffix (league indicator)
        # and is NOT a known Georgia club, clear the state
        if has_ga_league_suffix(team_name) or has_ga_league_suffix(club_name):
            if not is_georgia_club(team_name) and not is_georgia_club(club_name):
                return ''  # Clear - this is likely GA league, not Georgia state

    return state

# US ZIP code to approximate lat/lng (major zip prefixes)
# This is a fallback when geocoding isn't available
ZIP_PREFIX_COORDS = {
    '010': (42.1, -72.6),   # MA
    '020': (42.3, -71.1),   # MA Boston
    '030': (42.9, -71.4),   # NH
    '040': (43.7, -70.3),   # ME
    '050': (44.0, -72.7),   # VT
    '060': (41.6, -72.7),   # CT
    '070': (40.7, -74.2),   # NJ
    '080': (39.9, -74.9),   # NJ
    '100': (40.7, -74.0),   # NY NYC
    '110': (40.8, -73.2),   # NY Long Island
    '120': (42.7, -73.8),   # NY Albany
    '130': (43.0, -76.1),   # NY Syracuse
    '140': (42.9, -78.9),   # NY Buffalo
    '150': (40.4, -80.0),   # PA Pittsburgh
    '160': (40.3, -76.9),   # PA
    '170': (40.3, -76.9),   # PA Harrisburg
    '180': (40.6, -75.4),   # PA
    '190': (40.0, -75.1),   # PA Philadelphia
    '200': (38.9, -77.0),   # DC
    '210': (39.3, -76.6),   # MD Baltimore
    '220': (38.8, -77.1),   # VA Northern
    '230': (37.5, -77.4),   # VA Richmond
    '240': (37.3, -79.9),   # VA
    '270': (35.8, -78.6),   # NC Raleigh
    '280': (35.2, -80.8),   # NC Charlotte
    '290': (33.0, -80.0),   # SC
    '300': (33.7, -84.4),   # GA Atlanta
    '320': (30.3, -81.7),   # FL Jacksonville
    '330': (25.8, -80.2),   # FL Miami
    '340': (28.5, -81.4),   # FL Orlando
    '350': (33.5, -86.8),   # AL Birmingham
    '370': (36.2, -86.8),   # TN Nashville
    '380': (35.1, -90.0),   # TN Memphis
    '400': (38.3, -85.8),   # KY Louisville
    '430': (40.0, -83.0),   # OH Columbus
    '440': (41.5, -81.7),   # OH Cleveland
    '450': (39.1, -84.5),   # OH Cincinnati
    '460': (39.8, -86.2),   # IN Indianapolis
    '480': (42.3, -83.0),   # MI Detroit
    '490': (42.9, -85.7),   # MI Grand Rapids
    '530': (43.0, -89.4),   # WI Madison
    '550': (44.9, -93.3),   # MN Minneapolis
    '600': (41.9, -87.6),   # IL Chicago
    '630': (38.6, -90.2),   # MO St Louis
    '640': (39.1, -94.6),   # MO Kansas City
    '660': (39.0, -95.7),   # KS
    '680': (41.3, -96.0),   # NE Omaha
    '700': (30.0, -90.1),   # LA New Orleans
    '730': (35.5, -97.5),   # OK Oklahoma City
    '750': (32.8, -96.8),   # TX Dallas
    '770': (29.8, -95.4),   # TX Houston
    '780': (29.4, -98.5),   # TX San Antonio
    '790': (31.8, -106.4),  # TX El Paso
    '800': (39.7, -105.0),  # CO Denver
    '850': (33.4, -112.1),  # AZ Phoenix
    '870': (35.1, -106.6),  # NM Albuquerque
    '890': (36.2, -115.1),  # NV Las Vegas
    '900': (34.0, -118.2),  # CA Los Angeles
    '910': (34.2, -118.5),  # CA LA area
    '920': (32.7, -117.2),  # CA San Diego
    '930': (34.4, -119.7),  # CA Santa Barbara
    '940': (37.8, -122.4),  # CA San Francisco
    '950': (37.3, -121.9),  # CA San Jose
    '960': (38.6, -121.5),  # CA Sacramento
    '970': (45.5, -122.7),  # OR Portland
    '980': (47.6, -122.3),  # WA Seattle
    '990': (47.7, -117.4),  # WA Spokane
}

def get_coords_from_zip(zip_code):
    """Get approximate coordinates from zip code prefix."""
    if not zip_code or len(zip_code) < 3:
        return None, None
    prefix = zip_code[:3]
    if prefix in ZIP_PREFIX_COORDS:
        return ZIP_PREFIX_COORDS[prefix]
    # Try 2-digit prefix
    prefix2 = zip_code[:2] + '0'
    if prefix2 in ZIP_PREFIX_COORDS:
        return ZIP_PREFIX_COORDS[prefix2]
    return None, None

def main():
    db_path = Path(__file__).parent / 'seedlinedata.db'
    output_path = Path(__file__).parent.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'

    print(f"Reading from: {db_path}")
    print(f"Writing to: {output_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all teams with address data
    cursor.execute('''
        SELECT DISTINCT team_name, club_name, city, state, street_address, zip_code
        FROM teams
        WHERE team_name IS NOT NULL AND team_name != ''
    ''')

    teams = {}
    clubs = {}

    validated_count = 0
    cleared_count = 0

    for row in cursor.fetchall():
        team_name, club_name, city, state, street_address, zip_code = row

        # Validate state to prevent GA (Georgia) / GA (Girls Academy) confusion
        validated_state = validate_state(state, team_name, club_name)
        if state and not validated_state:
            cleared_count += 1
        if validated_state:
            validated_count += 1

        # Get coordinates from zip code
        lat, lng = get_coords_from_zip(zip_code)

        address_data = {
            'city': city or '',
            'state': validated_state,  # Use validated state
            'streetAddress': street_address or '',
            'zipCode': zip_code or '',
        }

        if lat and lng:
            address_data['lat'] = lat
            address_data['lng'] = lng

        # Store team
        if team_name:
            teams[team_name] = address_data

        # Store club (use first occurrence)
        if club_name and club_name not in clubs:
            clubs[club_name] = address_data.copy()

    conn.close()

    # Build output
    output = {
        'clubs': clubs,
        'teams': teams
    }

    # Count stats
    clubs_with_coords = sum(1 for c in clubs.values() if c.get('lat'))
    teams_with_coords = sum(1 for t in teams.values() if t.get('lat'))

    print(f"\nExported:")
    print(f"  Clubs: {len(clubs)} ({clubs_with_coords} with coordinates)")
    print(f"  Teams: {len(teams)} ({teams_with_coords} with coordinates)")
    print(f"  States validated: {validated_count}")
    print(f"  GA/Georgia confusion cleared: {cleared_count}")

    # Save
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to: {output_path}")

    # Verify Lamorinda
    if 'Lamorinda SC' in clubs:
        print(f"\nLamorinda SC: {clubs['Lamorinda SC']}")

if __name__ == '__main__':
    main()
