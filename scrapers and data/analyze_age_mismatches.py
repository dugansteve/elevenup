#!/usr/bin/env python3
"""Analyze teams where birth year in name doesn't match age group"""

import sqlite3
import re
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
db_path = SCRIPT_DIR / "seedlinedata.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT id, club_name, team_name, age_group, gender, league FROM teams')
teams = cursor.fetchall()

def extract_birth_year_suffix(name):
    """Extract 2-digit birth year from 4-digit year in name (2011 -> 11)"""
    match = re.search(r'\b20([0-1][0-9]|20)\b', name)
    if match:
        return match.group(1)
    return None

def extract_age_number(age_group):
    """Extract number from age_group like G11, B14 -> 11, 14"""
    if not age_group:
        return None
    match = re.search(r'[GBU]?(\d+)', str(age_group))
    if match:
        return match.group(1)
    return None

def get_gender_prefix(age_group, gender):
    if age_group and len(age_group) > 0 and age_group[0] in ['G', 'B']:
        return age_group[0]
    if gender == 'Girls':
        return 'G'
    elif gender == 'Boys':
        return 'B'
    return 'U'

mismatches = []

for team_id, club_name, team_name, age_group, gender, league in teams:
    birth_suffix = extract_birth_year_suffix(team_name)
    if not birth_suffix:
        continue

    age_num = extract_age_number(age_group)
    if not age_num:
        continue

    # Check if birth year suffix matches age group number
    if birth_suffix != age_num:
        prefix = get_gender_prefix(age_group, gender)
        correct_age_group = f'{prefix}{birth_suffix}'

        mismatches.append({
            'id': team_id,
            'team_name': team_name,
            'birth_year': f'20{birth_suffix}',
            'current_age_group': age_group,
            'correct_age_group': correct_age_group,
            'league': league
        })

print(f'=== Teams where birth year does not match age group ===')
print(f'Total mismatches: {len(mismatches)}')
print()

by_league = defaultdict(list)
for m in mismatches:
    by_league[m['league']].append(m)

print('By league:')
for league, items in sorted(by_league.items(), key=lambda x: -len(x[1])):
    print(f'  {league}: {len(items)} teams')

print()
print('Sample fixes (first 50):')
print('-' * 100)
for m in mismatches[:50]:
    print(f"{m['team_name'][:55]:<55} | {m['current_age_group']:<5} -> {m['correct_age_group']:<5} | (birth {m['birth_year']})")

conn.close()
