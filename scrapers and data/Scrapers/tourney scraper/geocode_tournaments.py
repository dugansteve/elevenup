#!/usr/bin/env python3
"""
Geocode Tournament Locations

Adds latitude/longitude coordinates to tournaments based on city/state.
Uses OpenStreetMap Nominatim API (free, no API key required).

Usage:
    python geocode_tournaments.py              # Geocode all tournaments without coords
    python geocode_tournaments.py --all        # Re-geocode all tournaments
    python geocode_tournaments.py --status     # Show geocoding status
"""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
import urllib.parse

# Paths
SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(SCRAPER_DIR), 'seedlinedata.db')

# State coordinates (centroids) as fallback
STATE_COORDS = {
    'AL': (32.806671, -86.791130), 'AK': (61.370716, -152.404419),
    'AZ': (33.729759, -111.431221), 'AR': (34.969704, -92.373123),
    'CA': (36.116203, -119.681564), 'CO': (39.059811, -105.311104),
    'CT': (41.597782, -72.755371), 'DE': (39.318523, -75.507141),
    'FL': (27.766279, -81.686783), 'GA': (33.040619, -83.643074),
    'HI': (21.094318, -157.498337), 'ID': (44.240459, -114.478828),
    'IL': (40.349457, -88.986137), 'IN': (39.849426, -86.258278),
    'IA': (42.011539, -93.210526), 'KS': (38.526600, -96.726486),
    'KY': (37.668140, -84.670067), 'LA': (31.169546, -91.867805),
    'ME': (44.693947, -69.381927), 'MD': (39.063946, -76.802101),
    'MA': (42.230171, -71.530106), 'MI': (43.326618, -84.536095),
    'MN': (45.694454, -93.900192), 'MS': (32.741646, -89.678696),
    'MO': (38.456085, -92.288368), 'MT': (46.921925, -110.454353),
    'NE': (41.125370, -98.268082), 'NV': (38.313515, -117.055374),
    'NH': (43.452492, -71.563896), 'NJ': (40.298904, -74.521011),
    'NM': (34.840515, -106.248482), 'NY': (42.165726, -74.948051),
    'NC': (35.630066, -79.806419), 'ND': (47.528912, -99.784012),
    'OH': (40.388783, -82.764915), 'OK': (35.565342, -96.928917),
    'OR': (44.572021, -122.070938), 'PA': (40.590752, -77.209755),
    'RI': (41.680893, -71.511780), 'SC': (33.856892, -80.945007),
    'SD': (44.299782, -99.438828), 'TN': (35.747845, -86.692345),
    'TX': (31.054487, -97.563461), 'UT': (40.150032, -111.862434),
    'VT': (44.045876, -72.710686), 'VA': (37.769337, -78.169968),
    'WA': (47.400902, -121.490494), 'WV': (38.491226, -80.954453),
    'WI': (44.268543, -89.616508), 'WY': (42.755966, -107.302490),
}

# Common city patterns in tournament names
CITY_PATTERNS = [
    r'(?:in|at|@)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "in San Diego"
    r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:Cup|Classic|Tournament|Showcase|Invitational)',  # "Temecula Classic"
    r'Copa\s+([A-Z][a-z]+)',  # "Copa Miami"
]

# Club name to city mapping (based on known club locations)
CLUB_CITIES = {
    'lonestar': ('Austin', 'TX'),
    'fc prime': ('Miami', 'FL'),
    'coastal rush': ('Mobile', 'AL'),
    'u90c': ('Dallas', 'TX'),
    'jsc soccer': ('Manteca', 'CA'),
    'united futbol academy': ('Atlanta', 'GA'),
    'palo alto': ('Palo Alto', 'CA'),
    'legends fc sd': ('San Diego', 'CA'),
    'union sacramento': ('Sacramento', 'CA'),
    'coronado': ('Coronado', 'CA'),
    'eli7e': ('San Diego', 'CA'),
    'la jolla': ('La Jolla', 'CA'),
    'legends fc': ('Norco', 'CA'),
    'indy eleven': ('Indianapolis', 'IN'),
    'rangers fc': ('Irvine', 'CA'),
    'surf': ('San Diego', 'CA'),
    'city sc southwest': ('Temecula', 'CA'),
    'sporting slammers': ('Irvine', 'CA'),
    'west coast fc': ('Irvine', 'CA'),
    'sa united': ('San Antonio', 'TX'),
    'san jose rush': ('San Jose', 'CA'),
    'san ramon fc': ('San Ramon', 'CA'),
    'mustang soccer': ('Danville', 'CA'),
    'burlingame': ('Burlingame', 'CA'),
    'el paso premier': ('El Paso', 'TX'),
    'pittsburgh riverhounds': ('Pittsburgh', 'PA'),
    'cardiff sockers': ('Cardiff', 'CA'),
    'strikers fc': ('Costa Mesa', 'CA'),
    'las vegas elite': ('Las Vegas', 'NV'),
    'mvla': ('Mountain View', 'CA'),
    'sdsc': ('San Diego', 'CA'),
    'southwest soccer': ('Chula Vista', 'CA'),
    'albion hurricanes': ('Houston', 'TX'),
    'dynamo': ('Los Angeles', 'CA'),
    'san diego force': ('San Diego', 'CA'),
    'scripps ranch': ('San Diego', 'CA'),
    'la city united': ('Los Angeles', 'CA'),
    'escondido': ('Escondido', 'CA'),
    'pateadores': ('Irvine', 'CA'),
    'magic city legends': ('Minot', 'ND'),
    'albion sc': ('San Diego', 'CA'),
    'celtic': ('San Diego', 'CA'),
    'crossfire': ('Seattle', 'WA'),
    'solar': ('Dallas', 'TX'),
    'concorde fire': ('Atlanta', 'GA'),
    'tophat': ('Atlanta', 'GA'),
    'nasa': ('Atlanta', 'GA'),
    'atlanta fire': ('Atlanta', 'GA'),
    'fc dallas': ('Dallas', 'TX'),
    'houston dynamo': ('Houston', 'TX'),
    'houston premier': ('Houston', 'TX'),
    'dallas surf': ('Dallas', 'TX'),
    'rush': ('Des Moines', 'IA'),
    'force': ('Minneapolis', 'MN'),
    'bloomington': ('Bloomington', 'MN'),
    'maplebrook': ('Brooklyn Park', 'MN'),
    'tri-city': ('Grand Forks', 'ND'),
    'ohio galaxies': ('Columbus', 'OH'),
    'medina': ('Medina', 'OH'),
    'scorpions': ('Boston', 'MA'),
    'jefferson cup': ('Richmond', 'VA'),
    'williamsburg': ('Williamsburg', 'VA'),
    'pensacola': ('Pensacola', 'FL'),
    'ormond beach': ('Ormond Beach', 'FL'),
    'chattanooga': ('Chattanooga', 'TN'),
    'mckinney': ('McKinney', 'TX'),
    'aggieland': ('College Station', 'TX'),
    'gulf coast': ('Gulfport', 'MS'),
    'phoenix': ('Phoenix', 'AZ'),
    'reno': ('Reno', 'NV'),
    'oregon surf': ('Portland', 'OR'),
    'high peaks': ('Lake Placid', 'NY'),
    'manhattan': ('Manhattan', 'NY'),
    'davis legacy': ('Davis', 'CA'),
    'turlock': ('Turlock', 'CA'),
    'santa cruz': ('Santa Cruz', 'CA'),
    'elk grove': ('Elk Grove', 'CA'),
    'express fc': ('San Diego', 'CA'),
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def extract_city_from_club(club_name):
    """Try to extract city from club/sponsor name"""
    if not club_name:
        return None, None

    club_lower = club_name.lower()
    for pattern, (city, state) in CLUB_CITIES.items():
        if pattern in club_lower:
            return city, state

    return None, None


def extract_city_from_name(name):
    """Try to extract city name from tournament name"""
    if not name:
        return None

    # Known city mappings from tournament names
    known_cities = {
        'bat city': 'Austin',
        'copa miami': 'Miami',
        'temecula': 'Temecula',
        'surf cup': 'San Diego',
        'albion cup': 'San Diego',
        'las vegas': 'Las Vegas',
        'santa clarita': 'Santa Clarita',
        'anaheim': 'Anaheim',
        'carlsbad': 'Carlsbad',
        'phoenix': 'Phoenix',
        'vegas': 'Las Vegas',
        'austin': 'Austin',
        'dallas': 'Dallas',
        'houston': 'Houston',
        'san antonio': 'San Antonio',
        'atlanta': 'Atlanta',
        'seattle': 'Seattle',
        'portland': 'Portland',
        'denver': 'Denver',
        'chicago': 'Chicago',
        'boston': 'Boston',
        'new york': 'New York',
        'manhattan': 'Manhattan',
        'reno': 'Reno',
        'pensacola': 'Pensacola',
        'chattanooga': 'Chattanooga',
        'mckinney': 'McKinney',
        'jefferson': 'Richmond',
        'williamsburg': 'Williamsburg',
        'ormond beach': 'Ormond Beach',
    }

    name_lower = name.lower()
    for pattern, city in known_cities.items():
        if pattern in name_lower:
            return city

    return None


def geocode_location(city, state, retries=2):
    """Geocode a location using Nominatim API"""
    if not state:
        return None, None

    # Build query
    if city:
        query = f"{city}, {state}, USA"
    else:
        query = f"{state}, USA"

    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1&countrycodes=us"

    headers = {
        'User-Agent': 'SeedlineTournamentGeocoder/1.0'
    }

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  Geocoding error for {query}: {e}")

    return None, None


def geocode_tournaments(force_all=False):
    """Geocode all tournaments"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get tournaments to geocode (including sponsor for club-based city lookup)
    if force_all:
        cursor.execute('SELECT event_id, name, city, state, sponsor FROM tournaments')
    else:
        cursor.execute('SELECT event_id, name, city, state, sponsor FROM tournaments WHERE latitude IS NULL')

    tournaments = cursor.fetchall()
    print(f"\nGeocoding {len(tournaments)} tournaments...")

    geocoded = 0
    failed = 0
    city_found = 0

    for t in tournaments:
        event_id = t['event_id']
        name = t['name']
        existing_city = t['city']
        state = t['state']
        sponsor = t['sponsor']

        # Try to find city from multiple sources (in priority order)
        city = existing_city

        if not city:
            # 1. Try extracting from tournament name
            city = extract_city_from_name(name)

        if not city:
            # 2. Try extracting from club/sponsor name
            club_city, club_state = extract_city_from_club(sponsor)
            if club_city:
                city = club_city
                # Also use club's state if we don't have one
                if not state and club_state:
                    state = club_state

        if not city:
            # 3. Try extracting from tournament name patterns
            club_city, club_state = extract_city_from_club(name)
            if club_city:
                city = club_city

        if not state:
            # Can't geocode without state
            failed += 1
            continue

        # Try geocoding with city first, then state only
        lat, lng = None, None
        used_city_coords = False

        if city:
            lat, lng = geocode_location(city, state)
            if lat is not None:
                used_city_coords = True
                city_found += 1

        if lat is None and state in STATE_COORDS:
            # Fall back to state centroid
            lat, lng = STATE_COORDS[state]

        if lat is not None:
            cursor.execute('''
                UPDATE tournaments
                SET latitude = ?, longitude = ?, city = ?
                WHERE event_id = ?
            ''', (lat, lng, city, event_id))
            geocoded += 1
            location_str = city if city else state
            marker = "*" if used_city_coords else ""
            print(f"  {name[:40]}: {location_str} -> ({lat:.4f}, {lng:.4f}) {marker}")
        else:
            failed += 1

        # Rate limit for Nominatim (1 request per second)
        time.sleep(1.1)

    conn.commit()
    conn.close()

    print(f"\nGeocoded: {geocoded}")
    print(f"  With city-level coords: {city_found}")
    print(f"  With state-level coords: {geocoded - city_found}")
    print(f"Failed: {failed}")


def show_status():
    """Show geocoding status"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM tournaments')
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM tournaments WHERE latitude IS NOT NULL')
    geocoded = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM tournaments WHERE city IS NOT NULL AND city != ""')
    with_city = cursor.fetchone()[0]

    print(f"\nGeocoding Status:")
    print(f"  Total tournaments: {total}")
    print(f"  With coordinates: {geocoded}")
    print(f"  With city: {with_city}")
    print(f"  Missing coordinates: {total - geocoded}")

    conn.close()


def main():
    args = sys.argv[1:]

    print("=" * 60)
    print("TOURNAMENT GEOCODING")
    print("=" * 60)

    if '--status' in args:
        show_status()
    elif '--all' in args:
        geocode_tournaments(force_all=True)
    else:
        geocode_tournaments(force_all=False)


if __name__ == "__main__":
    main()
