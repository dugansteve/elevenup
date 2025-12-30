#!/usr/bin/env python3
"""Find remaining teams with B2011/G2011 patterns that weren't fixed"""

import sqlite3
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
db_path = SCRIPT_DIR / "seedlinedata.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT id, team_name, age_group, gender FROM teams')
teams = cursor.fetchall()

mismatches = []
for team_id, team_name, age_group, gender in teams:
    if not team_name:
        continue

    # Look for patterns like B2011, G2011 (prefix attached to year)
    match = re.search(r'[BG](20[0-1][0-9])', team_name)
    if match:
        full_year = match.group(1)
        suffix = full_year[2:]  # '11' from '2011'

        # Get current age number from age_group
        age_match = re.search(r'[GBU]?(\d+)', str(age_group or ''))
        if age_match:
            current_num = age_match.group(1)
            if suffix != current_num:
                # Determine correct prefix
                prefix = age_group[0] if age_group and age_group[0] in ['G', 'B'] else ('G' if gender == 'Girls' else 'B')
                correct_age = f'{prefix}{suffix}'
                mismatches.append({
                    'id': team_id,
                    'team_name': team_name,
                    'current': age_group,
                    'correct': correct_age,
                    'birth_year': full_year
                })

print(f'Found {len(mismatches)} additional teams with B20XX/G20XX patterns to fix')
print()
print('Sample:')
for m in mismatches[:30]:
    print(f"{m['team_name'][:50]:<50} | {m['current']:<5} -> {m['correct']}")

conn.close()
