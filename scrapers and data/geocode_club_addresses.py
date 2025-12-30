#!/usr/bin/env python3
"""
Geocode club addresses to get exact lat/lng coordinates for map pins.
Uses OpenStreetMap Nominatim (free) with rate limiting.
"""

import sqlite3
import json
import time
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Rate limit: 1 request per second for Nominatim
RATE_LIMIT_SECONDS = 1.1

def geocode_address(geolocator, address_parts):
    """
    Geocode an address. Returns (lat, lng) or (None, None) if not found.
    Tries progressively less specific addresses if full address fails.
    """
    # Build address variations from most to least specific
    street, city, state, zip_code = address_parts

    address_attempts = []

    # Full address with street
    if street and city and state:
        address_attempts.append(f"{street}, {city}, {state} {zip_code}, USA")

    # City + State + Zip
    if city and state and zip_code:
        address_attempts.append(f"{city}, {state} {zip_code}, USA")

    # City + State only
    if city and state:
        address_attempts.append(f"{city}, {state}, USA")

    # Zip code only
    if zip_code:
        address_attempts.append(f"{zip_code}, USA")

    for address in address_attempts:
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                return location.latitude, location.longitude, address
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"    Geocoder error for '{address}': {e}")
            time.sleep(2)  # Wait longer on error
        except Exception as e:
            print(f"    Error for '{address}': {e}")

    return None, None, None

def main():
    db_path = Path(__file__).parent / 'seedlinedata.db'
    output_path = Path(__file__).parent.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'
    cache_path = Path(__file__).parent / 'geocode_cache.json'

    print(f"Database: {db_path}")
    print(f"Output: {output_path}")

    # Load existing cache
    cache = {}
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached geocodes")

    # Initialize geocoder
    geolocator = Nominatim(user_agent="seedline_soccer_app")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get unique club addresses (one per club)
    cursor.execute('''
        SELECT DISTINCT club_name, city, state, street_address, zip_code
        FROM teams
        WHERE club_name IS NOT NULL AND club_name != ''
        GROUP BY club_name
    ''')

    clubs = {}
    rows = cursor.fetchall()
    total = len(rows)
    geocoded_count = 0
    cached_count = 0
    failed_count = 0

    print(f"\nGeocoding {total} clubs...")
    print("This may take a while (rate limited to 1 request/second)")
    print("-" * 60)

    for i, row in enumerate(rows):
        club_name, city, state, street_address, zip_code = row

        # Build cache key
        cache_key = f"{street_address}|{city}|{state}|{zip_code}"

        address_data = {
            'city': city or '',
            'state': state or '',
            'streetAddress': street_address or '',
            'zipCode': zip_code or '',
        }

        # Check cache first
        if cache_key in cache:
            cached = cache[cache_key]
            if cached.get('lat') and cached.get('lng'):
                address_data['lat'] = cached['lat']
                address_data['lng'] = cached['lng']
                cached_count += 1
        else:
            # Geocode the address
            if city or zip_code:  # Need at least city or zip to geocode
                lat, lng, matched = geocode_address(
                    geolocator,
                    (street_address, city, state, zip_code)
                )

                if lat and lng:
                    address_data['lat'] = lat
                    address_data['lng'] = lng
                    cache[cache_key] = {'lat': lat, 'lng': lng}
                    geocoded_count += 1
                    print(f"  [{i+1}/{total}] {club_name}: ({lat:.4f}, {lng:.4f})")
                else:
                    failed_count += 1
                    cache[cache_key] = {'lat': None, 'lng': None}
                    print(f"  [{i+1}/{total}] {club_name}: FAILED - {city}, {state}")

                # Rate limit
                time.sleep(RATE_LIMIT_SECONDS)
            else:
                failed_count += 1

        clubs[club_name] = address_data

        # Save cache periodically
        if (i + 1) % 50 == 0:
            with open(cache_path, 'w') as f:
                json.dump(cache, f)
            print(f"  ... saved cache ({i+1}/{total} processed)")

    conn.close()

    # Save final cache
    with open(cache_path, 'w') as f:
        json.dump(cache, f)

    # Now get all teams and assign club coordinates
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT team_name, club_name, city, state, street_address, zip_code
        FROM teams
        WHERE team_name IS NOT NULL AND team_name != ''
    ''')

    teams = {}
    for row in cursor.fetchall():
        team_name, club_name, city, state, street_address, zip_code = row

        team_data = {
            'city': city or '',
            'state': state or '',
            'streetAddress': street_address or '',
            'zipCode': zip_code or '',
        }

        # Copy coordinates from club
        if club_name and club_name in clubs:
            club = clubs[club_name]
            if club.get('lat') and club.get('lng'):
                team_data['lat'] = club['lat']
                team_data['lng'] = club['lng']

        teams[team_name] = team_data

    conn.close()

    # Build output
    output = {
        'clubs': clubs,
        'teams': teams
    }

    clubs_with_coords = sum(1 for c in clubs.values() if c.get('lat'))
    teams_with_coords = sum(1 for t in teams.values() if t.get('lat'))

    print("\n" + "=" * 60)
    print(f"COMPLETE")
    print(f"  Clubs: {len(clubs)} ({clubs_with_coords} with exact coordinates)")
    print(f"  Teams: {len(teams)} ({teams_with_coords} with exact coordinates)")
    print(f"  New geocodes: {geocoded_count}")
    print(f"  From cache: {cached_count}")
    print(f"  Failed: {failed_count}")

    # Save
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to: {output_path}")

if __name__ == '__main__':
    main()
