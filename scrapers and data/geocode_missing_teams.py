#!/usr/bin/env python3
"""
Geocode teams that are missing from club_addresses.json by extracting
city/state from team names.
"""

import json
import time
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# City patterns that appear in team names
CITY_PATTERNS = {
    'detroit': ('Detroit', 'MI'),
    'chicago': ('Chicago', 'IL'),
    'atlanta': ('Atlanta', 'GA'),
    'dallas': ('Dallas', 'TX'),
    'houston': ('Houston', 'TX'),
    'phoenix': ('Phoenix', 'AZ'),
    'seattle': ('Seattle', 'WA'),
    'portland': ('Portland', 'OR'),
    'denver': ('Denver', 'CO'),
    'boston': ('Boston', 'MA'),
    'miami': ('Miami', 'FL'),
    'tampa': ('Tampa', 'FL'),
    'orlando': ('Orlando', 'FL'),
    'jacksonville': ('Jacksonville', 'FL'),
    'austin': ('Austin', 'TX'),
    'san antonio': ('San Antonio', 'TX'),
    'san diego': ('San Diego', 'CA'),
    'san jose': ('San Jose', 'CA'),
    'san francisco': ('San Francisco', 'CA'),
    'los angeles': ('Los Angeles', 'CA'),
    'sacramento': ('Sacramento', 'CA'),
    'charlotte': ('Charlotte', 'NC'),
    'raleigh': ('Raleigh', 'NC'),
    'nashville': ('Nashville', 'TN'),
    'memphis': ('Memphis', 'TN'),
    'minneapolis': ('Minneapolis', 'MN'),
    'milwaukee': ('Milwaukee', 'WI'),
    'indianapolis': ('Indianapolis', 'IN'),
    'columbus': ('Columbus', 'OH'),
    'cleveland': ('Cleveland', 'OH'),
    'cincinnati': ('Cincinnati', 'OH'),
    'pittsburgh': ('Pittsburgh', 'PA'),
    'philadelphia': ('Philadelphia', 'PA'),
    'baltimore': ('Baltimore', 'MD'),
    'richmond': ('Richmond', 'VA'),
    'virginia beach': ('Virginia Beach', 'VA'),
    'laredo': ('Laredo', 'TX'),
    'tulsa': ('Tulsa', 'OK'),
    'kansas city': ('Kansas City', 'MO'),
    'st louis': ('St. Louis', 'MO'),
    'st. louis': ('St. Louis', 'MO'),
    'new york': ('New York', 'NY'),
    'brooklyn': ('Brooklyn', 'NY'),
    'queens': ('Queens', 'NY'),
    'long island': ('Long Island', 'NY'),
    'albany': ('Albany', 'NY'),
    'buffalo': ('Buffalo', 'NY'),
    'rochester': ('Rochester', 'NY'),
    'new jersey': ('Newark', 'NJ'),
    'newark': ('Newark', 'NJ'),
    'trenton': ('Trenton', 'NJ'),
    'jersey city': ('Jersey City', 'NJ'),
    'washington': ('Washington', 'DC'),
    'dc united': ('Washington', 'DC'),
    'louisville': ('Louisville', 'KY'),
    'lexington': ('Lexington', 'KY'),
    'omaha': ('Omaha', 'NE'),
    'oklahoma city': ('Oklahoma City', 'OK'),
    'albuquerque': ('Albuquerque', 'NM'),
    'tucson': ('Tucson', 'AZ'),
    'las vegas': ('Las Vegas', 'NV'),
    'salt lake': ('Salt Lake City', 'UT'),
    'boise': ('Boise', 'ID'),
    'spokane': ('Spokane', 'WA'),
    'tacoma': ('Tacoma', 'WA'),
    'reno': ('Reno', 'NV'),
    'fresno': ('Fresno', 'CA'),
    'bakersfield': ('Bakersfield', 'CA'),
    'san bernardino': ('San Bernardino', 'CA'),
    'riverside': ('Riverside', 'CA'),
    'anaheim': ('Anaheim', 'CA'),
    'irvine': ('Irvine', 'CA'),
    'pasadena': ('Pasadena', 'CA'),
    'oakland': ('Oakland', 'CA'),
    'stockton': ('Stockton', 'CA'),
    'modesto': ('Modesto', 'CA'),
    'fort worth': ('Fort Worth', 'TX'),
    'el paso': ('El Paso', 'TX'),
    'arlington': ('Arlington', 'TX'),
    'corpus christi': ('Corpus Christi', 'TX'),
    'plano': ('Plano', 'TX'),
    'fort lauderdale': ('Fort Lauderdale', 'FL'),
    'west palm': ('West Palm Beach', 'FL'),
    'hialeah': ('Hialeah', 'FL'),
    'st pete': ('St. Petersburg', 'FL'),
    'st. pete': ('St. Petersburg', 'FL'),
    'clearwater': ('Clearwater', 'FL'),
    'sarasota': ('Sarasota', 'FL'),
    'tallahassee': ('Tallahassee', 'FL'),
    'gainesville': ('Gainesville', 'FL'),
    'pensacola': ('Pensacola', 'FL'),
    'birmingham': ('Birmingham', 'AL'),
    'montgomery': ('Montgomery', 'AL'),
    'mobile': ('Mobile', 'AL'),
    'huntsville': ('Huntsville', 'AL'),
    'new orleans': ('New Orleans', 'LA'),
    'baton rouge': ('Baton Rouge', 'LA'),
    'shreveport': ('Shreveport', 'LA'),
    'little rock': ('Little Rock', 'AR'),
    'jackson': ('Jackson', 'MS'),
    'chattanooga': ('Chattanooga', 'TN'),
    'knoxville': ('Knoxville', 'TN'),
    'greenville': ('Greenville', 'SC'),
    'charleston': ('Charleston', 'SC'),
    'columbia': ('Columbia', 'SC'),
    'greensboro': ('Greensboro', 'NC'),
    'durham': ('Durham', 'NC'),
    'winston-salem': ('Winston-Salem', 'NC'),
    'wilmington': ('Wilmington', 'NC'),
    'norfolk': ('Norfolk', 'VA'),
    'chesapeake': ('Chesapeake', 'VA'),
    'hampton': ('Hampton', 'VA'),
    'newport news': ('Newport News', 'VA'),
    'alexandria': ('Alexandria', 'VA'),
    'annapolis': ('Annapolis', 'MD'),
    'bethesda': ('Bethesda', 'MD'),
    'rockville': ('Rockville', 'MD'),
    'hartford': ('Hartford', 'CT'),
    'new haven': ('New Haven', 'CT'),
    'stamford': ('Stamford', 'CT'),
    'bridgeport': ('Bridgeport', 'CT'),
    'providence': ('Providence', 'RI'),
    'worcester': ('Worcester', 'MA'),
    'springfield': ('Springfield', 'MA'),
    'cambridge': ('Cambridge', 'MA'),
    'manchester': ('Manchester', 'NH'),
    'burlington': ('Burlington', 'VT'),
    'portland me': ('Portland', 'ME'),
    'des moines': ('Des Moines', 'IA'),
    'cedar rapids': ('Cedar Rapids', 'IA'),
    'davenport': ('Davenport', 'IA'),
    'wichita': ('Wichita', 'KS'),
    'topeka': ('Topeka', 'KS'),
    'sioux falls': ('Sioux Falls', 'SD'),
    'fargo': ('Fargo', 'ND'),
    'grand rapids': ('Grand Rapids', 'MI'),
    'ann arbor': ('Ann Arbor', 'MI'),
    'lansing': ('Lansing', 'MI'),
    'flint': ('Flint', 'MI'),
    'akron': ('Akron', 'OH'),
    'toledo': ('Toledo', 'OH'),
    'dayton': ('Dayton', 'OH'),
    'youngstown': ('Youngstown', 'OH'),
    'fort wayne': ('Fort Wayne', 'IN'),
    'evansville': ('Evansville', 'IN'),
    'south bend': ('South Bend', 'IN'),
    'peoria': ('Peoria', 'IL'),
    'rockford': ('Rockford', 'IL'),
    'naperville': ('Naperville', 'IL'),
    'aurora': ('Aurora', 'IL'),
    'green bay': ('Green Bay', 'WI'),
    'madison': ('Madison', 'WI'),
    'st paul': ('St. Paul', 'MN'),
    'st. paul': ('St. Paul', 'MN'),
    'duluth': ('Duluth', 'MN'),
    'rochester mn': ('Rochester', 'MN'),
    'colorado springs': ('Colorado Springs', 'CO'),
    'aurora co': ('Aurora', 'CO'),
    'boulder': ('Boulder', 'CO'),
    'fort collins': ('Fort Collins', 'CO'),
    'provo': ('Provo', 'UT'),
    'ogden': ('Ogden', 'UT'),
    'billings': ('Billings', 'MT'),
    'missoula': ('Missoula', 'MT'),
    'anchorage': ('Anchorage', 'AK'),
    'honolulu': ('Honolulu', 'HI'),
}

def main():
    rankings_path = Path(__file__).parent.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'rankings_for_react.json'
    addresses_path = Path(__file__).parent.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'
    cache_path = Path(__file__).parent / 'geocode_cache.json'

    print(f"Loading data...")

    with open(rankings_path, 'r') as f:
        rankings = json.load(f)

    with open(addresses_path, 'r') as f:
        addresses = json.load(f)

    # Load cache
    cache = {}
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached geocodes")

    # Find teams that need geocoding
    needs_geocoding = []
    for team in rankings['teamsData']:
        club = team.get('club', '')
        name = team.get('name', '')
        state = team.get('state', '')

        # Check if already has coords
        if club in addresses['clubs'] and addresses['clubs'][club].get('lat'):
            continue
        if name in addresses['teams'] and addresses['teams'][name].get('lat'):
            continue

        # Try to extract city from name
        name_lower = name.lower()
        found_city = None
        for pattern, (city, st) in CITY_PATTERNS.items():
            if pattern in name_lower:
                found_city = (city, st)
                break

        if found_city:
            needs_geocoding.append({
                'name': name,
                'club': club,
                'city': found_city[0],
                'state': found_city[1]
            })
        elif state:
            needs_geocoding.append({
                'name': name,
                'club': club,
                'city': '',
                'state': state
            })

    print(f"Teams needing geocoding: {len(needs_geocoding)}")
    print(f"  With city: {sum(1 for t in needs_geocoding if t['city'])}")
    print(f"  State only: {sum(1 for t in needs_geocoding if not t['city'])}")

    # Geocode
    geolocator = Nominatim(user_agent="seedline_soccer_app")
    added = 0
    cached = 0

    # Group by city+state to avoid duplicate geocoding
    locations = {}
    for t in needs_geocoding:
        key = f"{t['city']}|{t['state']}"
        if key not in locations:
            locations[key] = {'city': t['city'], 'state': t['state'], 'teams': []}
        locations[key]['teams'].append(t)

    print(f"\nUnique locations to geocode: {len(locations)}")

    for i, (key, loc) in enumerate(locations.items()):
        city = loc['city']
        state = loc['state']

        if not city and not state:
            continue

        # Check cache
        if key in cache:
            lat, lng = cache[key].get('lat'), cache[key].get('lng')
            if lat and lng:
                # Add to addresses
                for t in loc['teams']:
                    if t['club'] and t['club'] not in addresses['clubs']:
                        addresses['clubs'][t['club']] = {
                            'city': city,
                            'state': state,
                            'streetAddress': '',
                            'zipCode': '',
                            'lat': lat,
                            'lng': lng
                        }
                        added += 1
                    if t['name'] not in addresses['teams']:
                        addresses['teams'][t['name']] = {
                            'city': city,
                            'state': state,
                            'streetAddress': '',
                            'zipCode': '',
                            'lat': lat,
                            'lng': lng
                        }
                        added += 1
                cached += 1
                continue

        # Geocode
        address = f"{city}, {state}, USA" if city else f"{state}, USA"
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                lat, lng = location.latitude, location.longitude
                cache[key] = {'lat': lat, 'lng': lng}

                # Add to addresses
                for t in loc['teams']:
                    if t['club'] and t['club'] not in addresses['clubs']:
                        addresses['clubs'][t['club']] = {
                            'city': city,
                            'state': state,
                            'streetAddress': '',
                            'zipCode': '',
                            'lat': lat,
                            'lng': lng
                        }
                        added += 1
                    if t['name'] not in addresses['teams']:
                        addresses['teams'][t['name']] = {
                            'city': city,
                            'state': state,
                            'streetAddress': '',
                            'zipCode': '',
                            'lat': lat,
                            'lng': lng
                        }
                        added += 1

                if (i + 1) % 20 == 0:
                    print(f"  [{i+1}/{len(locations)}] Geocoded {address}: ({lat:.4f}, {lng:.4f})")
            else:
                cache[key] = {'lat': None, 'lng': None}
                print(f"  [{i+1}/{len(locations)}] FAILED: {address}")

            time.sleep(1.1)  # Rate limit

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"  Error geocoding {address}: {e}")
            time.sleep(2)

        # Save cache periodically
        if (i + 1) % 50 == 0:
            with open(cache_path, 'w') as f:
                json.dump(cache, f)

    # Save final cache
    with open(cache_path, 'w') as f:
        json.dump(cache, f)

    # Save updated addresses
    with open(addresses_path, 'w') as f:
        json.dump(addresses, f, indent=2)

    print(f"\nDone!")
    print(f"  Added: {added} entries")
    print(f"  From cache: {cached}")
    print(f"  Saved to: {addresses_path}")

if __name__ == '__main__':
    main()
