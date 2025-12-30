#!/usr/bin/env python3
"""Debug address lookup issue"""

import sqlite3
import pandas as pd
import re

db_path = 'seedlinedata.db'
conn = sqlite3.connect(db_path)

address_query = """
    SELECT DISTINCT team_name, club_name, city, state, street_address, zip_code
    FROM teams
    WHERE team_name IS NOT NULL AND team_name != ''
"""
address_df = pd.read_sql_query(address_query, conn)
print(f'Loaded {len(address_df)} team address rows from database')

# Build team_addresses dict like ranker does
team_addresses = {}

def normalize_team_for_state(team_name):
    if not team_name:
        return team_name
    name = team_name.lower().strip()
    name = re.sub(r'\s+\d{2}/\d{2}[gGbB]?', '', name)
    name = re.sub(r'\s+[gGbB]\d{1,2}[gGbB]?', '', name)
    name = re.sub(r'\s+(ga|ecnl|ecnl-rl|rl|aspire|npl)$', '', name, flags=re.IGNORECASE)
    return name.strip()

for _, row in address_df.iterrows():
    team_name = row['team_name'].strip() if pd.notna(row['team_name']) else ''
    if team_name:
        address_data = {
            'city': row['city'] if pd.notna(row['city']) else '',
            'state': row['state'] if pd.notna(row['state']) else '',
            'streetAddress': row['street_address'] if pd.notna(row['street_address']) else '',
            'zipCode': row['zip_code'] if pd.notna(row['zip_code']) else ''
        }
        team_key = team_name.lower().strip()
        team_addresses[team_key] = address_data
        normalized = normalize_team_for_state(team_name)
        if normalized and normalized != team_key:
            team_addresses[normalized] = address_data

print(f'Built team_addresses with {len(team_addresses)} entries')

# Now look up Bay Area Surf
test_teams = ['Bay Area Surf', 'Bay Area Surf 15G ECNL', 'Bay Area Surf RL', 'Mustang SC', 'San Juan SC', 'San Juan SC RL']
print()
print('=== LOOKUP TESTS ===')
for team in test_teams:
    team_key = team.lower().strip()
    if team_key in team_addresses:
        addr = team_addresses[team_key]
        print(f'{team} -> FOUND: city="{addr["city"]}", street="{addr["streetAddress"]}"')
    else:
        # Try normalized
        normalized = normalize_team_for_state(team)
        if normalized in team_addresses:
            addr = team_addresses[normalized]
            print(f'{team} -> FOUND (normalized "{normalized}"): city="{addr["city"]}", street="{addr["streetAddress"]}"')
        else:
            print(f'{team} -> NOT FOUND (key="{team_key}", normalized="{normalized}")')
            # Try partial matches
            partial = [k for k in team_addresses.keys() if 'bay area surf' in k or 'mustang' in k or 'san juan' in k][:5]
            if partial:
                print(f'     Partial matches: {partial}')

conn.close()
