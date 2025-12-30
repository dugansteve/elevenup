"""Test address fallback"""
import json

# Load club_addresses.json
with open('C:/Users/dugan/Smart Human Dynamics Dropbox/Steve Dugan/Seedline/App FrontEnd/Seedline_App/public/club_addresses.json', 'r') as f:
    addresses = json.load(f)

# Load rankings
with open('C:/Users/dugan/Smart Human Dynamics Dropbox/Steve Dugan/Seedline/App FrontEnd/Seedline_App/public/rankings_for_react.json', 'r') as f:
    rankings = json.load(f)

teams = rankings['teamsData']
clubs_lookup = {k.lower(): v for k, v in addresses['clubs'].items()}
teams_lookup = {k.lower(): v for k, v in addresses['teams'].items()}

print(f"Clubs in fallback: {len(clubs_lookup)}")
print(f"Teams in fallback: {len(teams_lookup)}")

# Test a few teams that should have fallback addresses
test_teams = [
    "Solar SC",  # ECNL club
    "Concorde Fire",  # ECNL club
    "PDA Blue",  # ECNL club
]

for team_name in test_teams:
    team_lower = team_name.lower()
    if team_lower in teams_lookup:
        print(f"\n{team_name} found in teams fallback: {teams_lookup[team_lower]}")
    elif team_lower in clubs_lookup:
        print(f"\n{team_name} found in clubs fallback: {clubs_lookup[team_lower]}")
    else:
        print(f"\n{team_name} NOT found in fallback")

# Check how many teams in rankings would match fallback
can_match = 0
cannot_match = 0

def extract_club_name(team_name):
    """Simple club extraction"""
    import re
    # Remove common suffixes
    name = team_name
    name = re.sub(r'\s+\d+[GB].*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(Academy|FC|SC|United|Soccer).*$', '', name, flags=re.IGNORECASE)
    return name.strip()

for team in teams:
    if not team.get('city'):  # Only check teams without city
        name = team.get('name', '')
        club = team.get('club', '')

        name_lower = name.lower()
        club_lower = club.lower() if club else ''

        found = False
        if name_lower in teams_lookup:
            found = True
        elif club_lower and club_lower in clubs_lookup:
            found = True
        else:
            # Try extracted club
            extracted = extract_club_name(name)
            if extracted and extracted.lower() in clubs_lookup:
                found = True

        if found:
            can_match += 1
        else:
            cannot_match += 1

print(f"\n=== Teams without city that COULD be matched by fallback: {can_match}")
print(f"=== Teams without city that CANNOT be matched: {cannot_match}")

# Sample teams that cannot be matched
print("\n=== Sample teams that cannot be matched (first 20): ===")
count = 0
for team in teams:
    if count >= 20:
        break
    if not team.get('city'):
        name = team.get('name', '')
        club = team.get('club', '')

        name_lower = name.lower()
        club_lower = club.lower() if club else ''

        found = False
        if name_lower in teams_lookup:
            found = True
        elif club_lower and club_lower in clubs_lookup:
            found = True
        else:
            extracted = extract_club_name(name)
            if extracted and extracted.lower() in clubs_lookup:
                found = True

        if not found:
            print(f"  {name[:50]:50} | Club: {club[:20] if club else 'N/A':20} | League: {team.get('league', 'N/A')}")
            count += 1
