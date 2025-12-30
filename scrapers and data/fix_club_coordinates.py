#!/usr/bin/env python3
"""
Fix clubs that have incorrect coordinates (state centroids instead of actual addresses)
"""

import json
import time
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Clubs that need to be fixed with correct addresses
CLUBS_TO_FIX = {
    "Bay Area Surf": {
        "streetAddress": "6081 Meridian Ave",
        "city": "San Jose",
        "state": "CA",
        "zipCode": "95120"
    },
    "FC Bay Area Surf": {
        "streetAddress": "6081 Meridian Ave",
        "city": "San Jose",
        "state": "CA",
        "zipCode": "95120"
    },
    "Bay Area Surf 15G": {
        "streetAddress": "6081 Meridian Ave",
        "city": "San Jose",
        "state": "CA",
        "zipCode": "95120"
    },
    "Mustang SC": {
        "streetAddress": "4680 Camino Tassajara",
        "city": "Danville",
        "state": "CA",
        "zipCode": "94506"
    },
    "YellowMustang SC": {
        "streetAddress": "4680 Camino Tassajara",
        "city": "Danville",
        "state": "CA",
        "zipCode": "94506"
    },
    "Walnut Creek Surf": {
        "streetAddress": "185 Lennon Lane",
        "city": "Walnut Creek",
        "state": "CA",
        "zipCode": "94598"
    },
    "San Juan SC": {
        "streetAddress": "",
        "city": "Sacramento",
        "state": "CA",
        "zipCode": "95864"
    },
    "San Juan SC -": {
        "streetAddress": "",
        "city": "Sacramento",
        "state": "CA",
        "zipCode": "95864"
    },
    "San Juan South SC": {
        "streetAddress": "",
        "city": "San Juan Capistrano",
        "state": "CA",
        "zipCode": "92675"
    },
    "San Juan South": {
        "streetAddress": "",
        "city": "San Juan Capistrano",
        "state": "CA",
        "zipCode": "92675"
    },
    "River Islands Surf": {
        "streetAddress": "1051 River Islands Pkwy",
        "city": "Lathrop",
        "state": "CA",
        "zipCode": "95330"
    },
    "YellowRiver Islands Surf": {
        "streetAddress": "1051 River Islands Pkwy",
        "city": "Lathrop",
        "state": "CA",
        "zipCode": "95330"
    },
    "LA Surf Soccer Club": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "Solano Surf SC": {
        "streetAddress": "1600 Capitola Way",
        "city": "Fairfield",
        "state": "CA",
        "zipCode": "94534"
    },
    "Solano Surf": {
        "streetAddress": "1600 Capitola Way",
        "city": "Fairfield",
        "state": "CA",
        "zipCode": "94534"
    },
    "Monterey Surf SC": {
        "streetAddress": "950 Casanova Ave",
        "city": "Monterey",
        "state": "CA",
        "zipCode": "93940"
    },
    "Valley Surf": {
        "streetAddress": "",
        "city": "Stockton",
        "state": "CA",
        "zipCode": "95207"
    },
    # SD Surf clubs with wrong parent (should be San Diego)
    "SD Surf Academy Girls (Arturo)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Girls (Becerra)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Girls (Kim)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Girls (Williams)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Girls (Jeff)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Boys (Rastok)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Boys (Kim)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Boys (Jens)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Academy Boys (Miller)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SD Surf Pre (Brookfield)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SDSC Surf 13G Pre-GA": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SDSC Surf 13G Pre-GA2": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    "SDSC Surf 15G": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
    # Empire Surf (Coachella Valley/Palm Desert area)
    "Empire Surf G2014 Academy Palm Desert - Cortes": {
        "streetAddress": "",
        "city": "Palm Desert",
        "state": "CA",
        "zipCode": "92260"
    },
    "Empire Surf G2016 Academy Palm Desert": {
        "streetAddress": "",
        "city": "Palm Desert",
        "state": "CA",
        "zipCode": "92260"
    },
    # Ventura Surf
    "Ventura Surf Soccer Club B2011": {
        "streetAddress": "",
        "city": "Ventura",
        "state": "CA",
        "zipCode": "93003"
    },
    # San Clemente Surf
    "San Clemente Surf Soccer Blue Lervold": {
        "streetAddress": "",
        "city": "San Clemente",
        "state": "CA",
        "zipCode": "92672"
    },
    "San Clemente Surf Soccer Cortes": {
        "streetAddress": "",
        "city": "San Clemente",
        "state": "CA",
        "zipCode": "92672"
    },
    "San Clemente Surf Soccer White Lervold": {
        "streetAddress": "",
        "city": "San Clemente",
        "state": "CA",
        "zipCode": "92672"
    },
    # South Bay Surf (Torrance/South Bay area)
    "South Bay Surf B2015": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "South Bay Surf G2015": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    # Sunrise Surf (Florida)
    "Sunrise Surf": {
        "streetAddress": "",
        "city": "Sunrise",
        "state": "FL",
        "zipCode": "33323"
    },
    # More major clubs
    "Beach FC": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "Beach FC (CA)": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "Beach Futbol Club": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "Beach Futbol Club B2014 ES Kerns": {
        "streetAddress": "",
        "city": "El Segundo",
        "state": "CA",
        "zipCode": "90245"
    },
    "Beach Futbol Club B2015 LB Cardenas": {
        "streetAddress": "",
        "city": "Long Beach",
        "state": "CA",
        "zipCode": "90802"
    },
    "Beach Futbol Club B2015 SB Caldwell": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "Beach Futbol Club B2016 SB Osborne": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "Beach Futbol Club G2012 SB Boswell": {
        "streetAddress": "",
        "city": "Torrance",
        "state": "CA",
        "zipCode": "90503"
    },
    "Beach Futbol Club G2014 LB A. Zavala": {
        "streetAddress": "",
        "city": "Long Beach",
        "state": "CA",
        "zipCode": "90802"
    },
    "Beach Futbol Club G2014 LB Diaz": {
        "streetAddress": "",
        "city": "Long Beach",
        "state": "CA",
        "zipCode": "90802"
    },
    "ALBION SC": {
        "streetAddress": "2525 Bacon St",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92107"
    },
    "ALBION SC San Diego": {
        "streetAddress": "2525 Bacon St",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92107"
    },
    "ALBION SC Colorado": {
        "streetAddress": "",
        "city": "Denver",
        "state": "CO",
        "zipCode": "80209"
    },
    "ALBION SC Santa Monica": {
        "streetAddress": "",
        "city": "Santa Monica",
        "state": "CA",
        "zipCode": "90401"
    },
    "ALBION SC Central Valley": {
        "streetAddress": "",
        "city": "Fresno",
        "state": "CA",
        "zipCode": "93711"
    },
    "Alameda SC": {
        "streetAddress": "875-A Island Drive",
        "city": "Alameda",
        "state": "CA",
        "zipCode": "94502"
    },
    "Alameda Soccer Club": {
        "streetAddress": "875-A Island Drive",
        "city": "Alameda",
        "state": "CA",
        "zipCode": "94502"
    },
}

def main():
    addresses_path = Path(__file__).parent.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'
    cache_path = Path(__file__).parent / 'geocode_cache.json'

    print("Loading addresses...")
    with open(addresses_path, 'r') as f:
        addresses = json.load(f)

    # Load cache
    cache = {}
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached geocodes")

    geolocator = Nominatim(user_agent="seedline_soccer_app")
    fixed = 0
    geocoded = 0

    for club_name, addr_info in CLUBS_TO_FIX.items():
        city = addr_info['city']
        state = addr_info['state']
        street = addr_info['streetAddress']
        zipcode = addr_info['zipCode']

        # Build geocoding address
        if street:
            geo_address = f"{street}, {city}, {state} {zipcode}, USA"
        elif city:
            geo_address = f"{city}, {state}, USA"
        else:
            print(f"  Skipping {club_name} - no location info")
            continue

        # Check cache first
        cache_key = geo_address.lower()
        if cache_key in cache and cache[cache_key].get('lat'):
            lat, lng = cache[cache_key]['lat'], cache[cache_key]['lng']
            print(f"  {club_name}: Using cached coords ({lat:.4f}, {lng:.4f})")
        else:
            # Geocode
            try:
                location = geolocator.geocode(geo_address, timeout=10)
                if location:
                    lat, lng = location.latitude, location.longitude
                    cache[cache_key] = {'lat': lat, 'lng': lng}
                    geocoded += 1
                    print(f"  {club_name}: Geocoded {geo_address} -> ({lat:.4f}, {lng:.4f})")
                else:
                    # Try without street
                    if street:
                        geo_address2 = f"{city}, {state}, USA"
                        location = geolocator.geocode(geo_address2, timeout=10)
                        if location:
                            lat, lng = location.latitude, location.longitude
                            cache[geo_address2.lower()] = {'lat': lat, 'lng': lng}
                            geocoded += 1
                            print(f"  {club_name}: Geocoded {geo_address2} -> ({lat:.4f}, {lng:.4f})")
                        else:
                            print(f"  {club_name}: FAILED to geocode")
                            continue
                    else:
                        print(f"  {club_name}: FAILED to geocode")
                        continue

                time.sleep(1.1)  # Rate limit
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                print(f"  {club_name}: Error - {e}")
                time.sleep(2)
                continue

        # Update the address (force update even if exists)
        if 'clubs' not in addresses:
            addresses['clubs'] = {}

        addresses['clubs'][club_name] = {
            'streetAddress': street,
            'city': city,
            'state': state,
            'zipCode': zipcode,
            'lat': lat,
            'lng': lng
        }
        fixed += 1

    # Save cache
    with open(cache_path, 'w') as f:
        json.dump(cache, f)

    # Save addresses
    with open(addresses_path, 'w') as f:
        json.dump(addresses, f, indent=2)

    print(f"\nDone!")
    print(f"  Fixed: {fixed} clubs")
    print(f"  Newly geocoded: {geocoded}")
    print(f"  Saved to: {addresses_path}")

if __name__ == '__main__':
    main()
