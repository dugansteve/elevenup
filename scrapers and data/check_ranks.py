"""Check rank field in rankings JSON."""
import json

JSON_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\rankings_for_react.json"

with open(JSON_PATH, 'r') as f:
    data = json.load(f)

# Check first few teams for rank field
print('Checking if teams have rank field:')
for i, t in enumerate(data['teamsData'][:5]):
    rank = t.get('rank', 'NOT PRESENT')
    name = t.get('name', '?')[:40]
    print(f"  {name}: rank={rank}")

# Find teams with 'united' in G13
print('\nG13 teams with "United" in name:')
count = 0
for t in data['teamsData']:
    if t.get('ageGroup') == 'G13' and 'united' in t.get('name', '').lower():
        rank = t.get('rank', '?')
        name = t.get('name')
        print(f"  #{rank} - {name}")
        count += 1
        if count >= 15:
            print("  ... (showing first 15)")
            break

# Check for Florida United, Napa United, Sacramento United specifically
print('\nSearching for specific teams in G13:')
search_terms = ['florida', 'napa', 'sacramento', 'clovis']
for term in search_terms:
    found = False
    for t in data['teamsData']:
        if t.get('ageGroup') == 'G13' and term in t.get('name', '').lower():
            rank = t.get('rank', '?')
            name = t.get('name')
            print(f"  {term.title()}: #{rank} - {name}")
            found = True
            break
    if not found:
        print(f"  {term.title()}: NOT FOUND in G13")
