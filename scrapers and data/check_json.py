import json

with open(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\rankings_for_react.json", "r") as f:
    data = json.load(f)

print(f"Total teams in JSON: {len(data['teamsData'])}")

print("\nSample teams with '2009' in name:")
count = 0
for t in data['teamsData']:
    if '2009' in t.get('name', ''):
        print(f"  {t['ageGroup']} | {t['name'][:60]}")
        count += 1
        if count >= 15:
            break

print("\nSample teams with '2016' in name:")
count = 0
for t in data['teamsData']:
    if '2016' in t.get('name', ''):
        print(f"  {t['ageGroup']} | {t['name'][:60]}")
        count += 1
        if count >= 15:
            break

print("\nSample teams with '2013' in name:")
count = 0
for t in data['teamsData']:
    if '2013' in t.get('name', ''):
        print(f"  {t['ageGroup']} | {t['name'][:60]}")
        count += 1
        if count >= 10:
            break

# Check for any remaining mismatches
print("\n--- Checking for potential mismatches ---")
mismatches = 0
for t in data['teamsData']:
    name = t.get('name', '')
    ag = t.get('ageGroup', '')

    # Extract year from name if present
    import re
    match = re.search(r'\b(200[6-9]|201[0-9])\b', name)
    if match:
        name_year = match.group(1)[-2:]
        ag_match = re.search(r'[GB]?(0[6-9]|1[0-9])', ag)
        if ag_match:
            ag_year = ag_match.group(1)
            if name_year != ag_year:
                mismatches += 1
                if mismatches <= 10:
                    print(f"  MISMATCH: name has '{name_year}', ag is '{ag}': {name[:50]}")

print(f"\nTotal potential mismatches: {mismatches}")
