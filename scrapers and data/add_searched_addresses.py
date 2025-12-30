#!/usr/bin/env python3
"""
Add addresses found through web search to club_addresses.json
"""

import json
import time
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Addresses found through web search
SEARCHED_ADDRESSES = {
    # Club name -> address info
    "BRYC": {
        "streetAddress": "6011 Carrindale Ct",
        "city": "Burke",
        "state": "VA",
        "zipCode": "22015"
    },
    "Braddock Road Youth Club": {
        "streetAddress": "6011 Carrindale Ct",
        "city": "Burke",
        "state": "VA",
        "zipCode": "22015"
    },
    "BVB International": {
        "streetAddress": "2335 Sandy Lake Rd",
        "city": "Carrollton",
        "state": "TX",
        "zipCode": "75006"
    },
    "BVB International Academy": {
        "streetAddress": "2335 Sandy Lake Rd",
        "city": "Carrollton",
        "state": "TX",
        "zipCode": "75006"
    },
    "BVB International Texas BVB": {
        "streetAddress": "2335 Sandy Lake Rd",
        "city": "Carrollton",
        "state": "TX",
        "zipCode": "75006"
    },
    "Ballistic United": {
        "streetAddress": "275 Rose Ave",
        "city": "Pleasanton",
        "state": "CA",
        "zipCode": "94566"
    },
    "Barca Residency": {
        "streetAddress": "12684 W Gila Bend Hwy",
        "city": "Casa Grande",
        "state": "AZ",
        "zipCode": "85193"
    },
    "Barca Residency Academy": {
        "streetAddress": "12684 W Gila Bend Hwy",
        "city": "Casa Grande",
        "state": "AZ",
        "zipCode": "85193"
    },
    "GSA": {
        "streetAddress": "12684 W Gila Bend Hwy",
        "city": "Casa Grande",
        "state": "AZ",
        "zipCode": "85122"
    },
    "Grande Sports Academy": {
        "streetAddress": "12684 W Gila Bend Hwy",
        "city": "Casa Grande",
        "state": "AZ",
        "zipCode": "85122"
    },
    "Blau Weiss Gottschee": {
        "streetAddress": "3159 Flatbush Ave",
        "city": "Brooklyn",
        "state": "NY",
        "zipCode": "11234"
    },
    "BW Gottschee": {
        "streetAddress": "3159 Flatbush Ave",
        "city": "Brooklyn",
        "state": "NY",
        "zipCode": "11234"
    },
    "Carolina Elite Soccer": {
        "streetAddress": "18 Boland Court",
        "city": "Greenville",
        "state": "SC",
        "zipCode": "29615"
    },
    "CESA": {
        "streetAddress": "18 Boland Court",
        "city": "Greenville",
        "state": "SC",
        "zipCode": "29615"
    },
    "D.C. United": {
        "streetAddress": "42095 Loudoun United Dr",
        "city": "Leesburg",
        "state": "VA",
        "zipCode": "20175"
    },
    "DC United": {
        "streetAddress": "42095 Loudoun United Dr",
        "city": "Leesburg",
        "state": "VA",
        "zipCode": "20175"
    },
    "Downtown United Soccer Club": {
        "streetAddress": "527 Hudson St",
        "city": "New York",
        "state": "NY",
        "zipCode": "10014"
    },
    "DUSC": {
        "streetAddress": "527 Hudson St",
        "city": "New York",
        "state": "NY",
        "zipCode": "10014"
    },
    "Chula Vista": {
        "streetAddress": "825 Kuhn Dr",
        "city": "Chula Vista",
        "state": "CA",
        "zipCode": "91913"
    },
    "Chula Vista FC": {
        "streetAddress": "825 Kuhn Dr",
        "city": "Chula Vista",
        "state": "CA",
        "zipCode": "91913"
    },
    "CF Montreal": {
        "streetAddress": "4759 rue Sherbrooke Est",
        "city": "Montreal",
        "state": "QC",
        "zipCode": "H1V 3S8"
    },
    "Bavarian United": {
        "streetAddress": "700 W Lexington Blvd",
        "city": "Glendale",
        "state": "WI",
        "zipCode": "53217"
    },
    "Bavarian United SC": {
        "streetAddress": "700 W Lexington Blvd",
        "city": "Glendale",
        "state": "WI",
        "zipCode": "53217"
    },
    "Achilles": {
        "streetAddress": "1008 Westmore Ave",
        "city": "Rockville",
        "state": "MD",
        "zipCode": "20850"
    },
    "Achilles FC": {
        "streetAddress": "1008 Westmore Ave",
        "city": "Rockville",
        "state": "MD",
        "zipCode": "20850"
    },
    "Bwp Football": {
        "streetAddress": "4 Fritz Blvd",
        "city": "Albany",
        "state": "NY",
        "zipCode": "12205"
    },
    "BWP Football Academy": {
        "streetAddress": "4 Fritz Blvd",
        "city": "Albany",
        "state": "NY",
        "zipCode": "12205"
    },
    "Black Watch Premier": {
        "streetAddress": "4 Fritz Blvd",
        "city": "Albany",
        "state": "NY",
        "zipCode": "12205"
    },
    "Lonestar SC": {
        "streetAddress": "12325 Hymeadow Dr",
        "city": "Austin",
        "state": "TX",
        "zipCode": "78750"
    },
    "Lonestar": {
        "streetAddress": "12325 Hymeadow Dr",
        "city": "Austin",
        "state": "TX",
        "zipCode": "78750"
    },
    "PDA": {
        "streetAddress": "1 Upper Pond Rd",
        "city": "Somerset",
        "state": "NJ",
        "zipCode": "08873"
    },
    "Players Development Academy": {
        "streetAddress": "1 Upper Pond Rd",
        "city": "Somerset",
        "state": "NJ",
        "zipCode": "08873"
    },
    "Sporting KC": {
        "streetAddress": "6310 Lewis Road",
        "city": "Kansas City",
        "state": "MO",
        "zipCode": "64132"
    },
    "Sporting Kansas City": {
        "streetAddress": "6310 Lewis Road",
        "city": "Kansas City",
        "state": "MO",
        "zipCode": "64132"
    },
    "Philadelphia Union": {
        "streetAddress": "2485 Seaport Drive",
        "city": "Chester",
        "state": "PA",
        "zipCode": "19013"
    },
    "Union": {
        "streetAddress": "2485 Seaport Drive",
        "city": "Chester",
        "state": "PA",
        "zipCode": "19013"
    },
    "NYCFC": {
        "streetAddress": "",
        "city": "Orangeburg",
        "state": "NY",
        "zipCode": "10962"
    },
    "New York City FC": {
        "streetAddress": "",
        "city": "Orangeburg",
        "state": "NY",
        "zipCode": "10962"
    },
    "FC Copa": {
        "streetAddress": "",
        "city": "Metuchen",
        "state": "NJ",
        "zipCode": "08840"
    },
    "FC Copa Academy": {
        "streetAddress": "",
        "city": "Metuchen",
        "state": "NJ",
        "zipCode": "08840"
    },
    "Inter Miami CF": {
        "streetAddress": "1350 NW 55th St",
        "city": "Fort Lauderdale",
        "state": "FL",
        "zipCode": "33309"
    },
    "Inter Miami": {
        "streetAddress": "1350 NW 55th St",
        "city": "Fort Lauderdale",
        "state": "FL",
        "zipCode": "33309"
    },
    "Brentwood SC": {
        "streetAddress": "",
        "city": "Brentwood",
        "state": "CA",
        "zipCode": "94513"
    },
    "Central Valley Futbol": {
        "streetAddress": "",
        "city": "Fresno",
        "state": "CA",
        "zipCode": "93722"
    },
    "AC River": {
        "streetAddress": "",
        "city": "",
        "state": "TX",
        "zipCode": ""
    },
    "Alliance": {
        "streetAddress": "",
        "city": "Denver",
        "state": "CO",
        "zipCode": ""
    },
    # Round 2 - additional clubs found
    "Racing Louisville": {
        "streetAddress": "801 Edith Road",
        "city": "Louisville",
        "state": "KY",
        "zipCode": "40206"
    },
    "Lamorinda Soccer Club": {
        "streetAddress": "1078 Carol Ln",
        "city": "Lafayette",
        "state": "CA",
        "zipCode": "94549"
    },
    "Gretna Elite": {
        "streetAddress": "10550 S 222nd St",
        "city": "Gretna",
        "state": "NE",
        "zipCode": "68028"
    },
    "Gretna Elite Academy": {
        "streetAddress": "10550 S 222nd St",
        "city": "Gretna",
        "state": "NE",
        "zipCode": "68028"
    },
    "Gretna Elite RL": {
        "streetAddress": "10550 S 222nd St",
        "city": "Gretna",
        "state": "NE",
        "zipCode": "68028"
    },
    "Metropolitan Oval": {
        "streetAddress": "60-58 60th Street",
        "city": "Maspeth",
        "state": "NY",
        "zipCode": "11378"
    },
    "Silicon Valley Soccer": {
        "streetAddress": "",
        "city": "Redwood City",
        "state": "CA",
        "zipCode": "94064"
    },
    "Total Futbol": {
        "streetAddress": "6109 Fairfield St",
        "city": "Los Angeles",
        "state": "CA",
        "zipCode": "90022"
    },
    "Total Futbol Academy": {
        "streetAddress": "6109 Fairfield St",
        "city": "Los Angeles",
        "state": "CA",
        "zipCode": "90022"
    },
    "The Town FC": {
        "streetAddress": "1928 Saint Mary's Road",
        "city": "Moraga",
        "state": "CA",
        "zipCode": "94575"
    },
    "Triangle United Soccer Association": {
        "streetAddress": "121 South Estes Drive",
        "city": "Chapel Hill",
        "state": "NC",
        "zipCode": "27515"
    },
    "Triangle United": {
        "streetAddress": "121 South Estes Drive",
        "city": "Chapel Hill",
        "state": "NC",
        "zipCode": "27515"
    },
    "Hoosier Premier": {
        "streetAddress": "",
        "city": "Indianapolis",
        "state": "IN",
        "zipCode": ""
    },
    "LA Bulls": {
        "streetAddress": "",
        "city": "Los Angeles",
        "state": "CA",
        "zipCode": ""
    },
    "Players Development": {
        "streetAddress": "1 Upper Pond Rd",
        "city": "Somerset",
        "state": "NJ",
        "zipCode": "08873"
    },
    "Ironbound Soccer Club": {
        "streetAddress": "",
        "city": "Newark",
        "state": "NJ",
        "zipCode": ""
    },
    "Match Fit": {
        "streetAddress": "",
        "city": "Linden",
        "state": "NJ",
        "zipCode": ""
    },
    "Match Fit Academy": {
        "streetAddress": "",
        "city": "Linden",
        "state": "NJ",
        "zipCode": ""
    },
    "Woodside Soccer Club Crush": {
        "streetAddress": "",
        "city": "Woodside",
        "state": "NY",
        "zipCode": ""
    },
    "Palo Alto": {
        "streetAddress": "",
        "city": "Palo Alto",
        "state": "CA",
        "zipCode": ""
    },
    "Playmaker Futbol": {
        "streetAddress": "",
        "city": "Phoenix",
        "state": "AZ",
        "zipCode": ""
    },
    "Vision Soccer": {
        "streetAddress": "",
        "city": "Houston",
        "state": "TX",
        "zipCode": ""
    },
    "Winnett Soccer": {
        "streetAddress": "",
        "city": "Atlanta",
        "state": "GA",
        "zipCode": ""
    },
    "Sporting Jax Soccer RL": {
        "streetAddress": "",
        "city": "Jacksonville",
        "state": "FL",
        "zipCode": ""
    },
    "Sporting Jax": {
        "streetAddress": "",
        "city": "Jacksonville",
        "state": "FL",
        "zipCode": ""
    },
    "United Futbol RL": {
        "streetAddress": "",
        "city": "Jacksonville",
        "state": "FL",
        "zipCode": ""
    },
    "XF": {
        "streetAddress": "",
        "city": "Seattle",
        "state": "WA",
        "zipCode": ""
    },
    "Palatine Celtic": {
        "streetAddress": "",
        "city": "Omaha",
        "state": "NE",
        "zipCode": ""
    },
    "Global Football Innovation": {
        "streetAddress": "",
        "city": "Miami",
        "state": "FL",
        "zipCode": ""
    },
    "Lanier Soccer Association": {
        "streetAddress": "",
        "city": "Buford",
        "state": "GA",
        "zipCode": ""
    },
    "KSA": {
        "streetAddress": "",
        "city": "Katy",
        "state": "TX",
        "zipCode": ""
    },
    "TSF": {
        "streetAddress": "",
        "city": "Tampa",
        "state": "FL",
        "zipCode": ""
    },
    # Round 3 - final batch
    "Louisville City": {
        "streetAddress": "801 Edith Road",
        "city": "Louisville",
        "state": "KY",
        "zipCode": "40206"
    },
    "Louisville City FC": {
        "streetAddress": "801 Edith Road",
        "city": "Louisville",
        "state": "KY",
        "zipCode": "40206"
    },
    "Shattuck-St. Mary's": {
        "streetAddress": "1000 Shumway Avenue",
        "city": "Faribault",
        "state": "MN",
        "zipCode": "55021"
    },
    "Idaho Surf": {
        "streetAddress": "1889 N Wildwood St",
        "city": "Boise",
        "state": "ID",
        "zipCode": "83713"
    },
    "Vancouver Whitecaps": {
        "streetAddress": "3700 Willingdon Avenue",
        "city": "Burnaby",
        "state": "BC",
        "zipCode": ""
    },
    "Toronto": {
        "streetAddress": "",
        "city": "Toronto",
        "state": "ON",
        "zipCode": ""
    },
    "Toronto FC": {
        "streetAddress": "",
        "city": "Toronto",
        "state": "ON",
        "zipCode": ""
    },
    "Space Coast United SCU Girls": {
        "streetAddress": "",
        "city": "Melbourne",
        "state": "FL",
        "zipCode": ""
    },
    "Space Coast United": {
        "streetAddress": "",
        "city": "Melbourne",
        "state": "FL",
        "zipCode": ""
    },
    "Napa United": {
        "streetAddress": "",
        "city": "Napa",
        "state": "CA",
        "zipCode": ""
    },
    "Napa United Napa United": {
        "streetAddress": "",
        "city": "Napa",
        "state": "CA",
        "zipCode": ""
    },
    "West Virginia Soccer": {
        "streetAddress": "",
        "city": "Charleston",
        "state": "WV",
        "zipCode": ""
    },
    # Round 4 - California clubs with proper addresses
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
    "Walnut Creek Surf Soccer Club": {
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
    "San Juan South Soccer Club": {
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
    "River Islands Surf /07": {
        "streetAddress": "1051 River Islands Pkwy",
        "city": "Lathrop",
        "state": "CA",
        "zipCode": "95330"
    },
    "River Islands Surf -": {
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
    "LA Surf Soccer Club HW -": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "LA Surf Soccer Club LC -": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "LA Surf Soccer Club SW -": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "LA Surf Soccer Club SM -": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "LA Surf Soccer Club SO -": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "LA Surf Soccer Club SFV -": {
        "streetAddress": "325 N Altadena Dr",
        "city": "Pasadena",
        "state": "CA",
        "zipCode": "91107"
    },
    "Solano Surf": {
        "streetAddress": "1600 Capitola Way",
        "city": "Fairfield",
        "state": "CA",
        "zipCode": "94534"
    },
    "Solano Surf SC": {
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
    "Monterey Surf Soccer Club": {
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
    "South Valley Surf SC G2012": {
        "streetAddress": "6800 Monterey Road",
        "city": "Gilroy",
        "state": "CA",
        "zipCode": "95020"
    },
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
    "SD Surf Academy Boys (Rastok)": {
        "streetAddress": "11305 Rancho Bernardo Road",
        "city": "San Diego",
        "state": "CA",
        "zipCode": "92127"
    },
}

def main():
    addresses_path = Path(__file__).parent.parent / 'App FrontEnd' / 'Seedline_App' / 'public' / 'club_addresses.json'
    cache_path = Path(__file__).parent / 'geocode_cache.json'

    print(f"Loading addresses...")
    with open(addresses_path, 'r') as f:
        addresses = json.load(f)

    # Load cache
    cache = {}
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached geocodes")

    geolocator = Nominatim(user_agent="seedline_soccer_app")
    added = 0
    geocoded = 0

    for club_name, addr_info in SEARCHED_ADDRESSES.items():
        # Skip if already in addresses with coords
        if club_name in addresses.get('clubs', {}) and addresses['clubs'][club_name].get('lat'):
            print(f"  Skipping {club_name} - already has coordinates")
            continue

        city = addr_info['city']
        state = addr_info['state']
        street = addr_info['streetAddress']
        zipcode = addr_info['zipCode']

        # Build geocoding address
        if street:
            geo_address = f"{street}, {city}, {state} {zipcode}, USA"
        elif city:
            geo_address = f"{city}, {state}, USA"
        elif state:
            geo_address = f"{state}, USA"
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
                            cache[cache_key] = {'lat': lat, 'lng': lng}
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

        # Add to addresses
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
        added += 1

    # Save cache
    with open(cache_path, 'w') as f:
        json.dump(cache, f)

    # Save addresses
    with open(addresses_path, 'w') as f:
        json.dump(addresses, f, indent=2)

    print(f"\nDone!")
    print(f"  Added: {added} clubs")
    print(f"  Newly geocoded: {geocoded}")
    print(f"  Saved to: {addresses_path}")

if __name__ == '__main__':
    main()
