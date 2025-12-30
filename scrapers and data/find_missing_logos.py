"""
Find clubs that still need logos.
"""
import sqlite3
import json

# Extended mappings in the JS file
JS_MAPPINGS = {
    'albion sc san diego', 'albion sc', 'albion hurricanes fc', 'albion hurricanes',
    'albion sc central valley', 'albion sc las vegas', 'albion sc merced',
    'albion sc riverside', 'albion sc santa monica', 'beach futbol club', 'beach fc',
    'cda slammers', 'slammers', 'slammers fc', 'rebels soccer club', 'rebels sc',
    'fc dallas', 'solar sc', 'solar soccer club', 'concorde fire', 'concorde fire platinum',
    'georgia soccer academy', 'gsa', 'dallas texans', 'texans sc', 'colorado rush',
    'rush soccer', 'rush', 'idaho rush', 'kansas rush', 'surf soccer club', 'surf sc',
    'utah surf', 'st louis scott gallagher', 'scott gallagher', 'players soccer academy',
    'real colorado', 'real colorado foxes', 'sporting kansas city', 'sporting kc',
    'sporting iowa', 'utah avalanche', 'avalanche', 'colorado rapids',
    'colorado rapids youth', 'phoenix rising', 'phoenix rising fc', 'lions fc',
    'livermore fusion', 'la roca fc', 'la roca', 'racing louisville',
    'tennessee soccer club', 'wilmington hammerheads', 'eastside timbers fc',
    'eastside timbers', 'boise thorns fc', 'boise timbers thorns fc', 'arsenal colorado',
    'city sc utah', 'city sc', 'pittsburgh riverhounds', 'riverhounds', 'world class fc',
    'susa fc', 'susa', 'charlotte soccer academy', 'charlotte sa', 'nc fusion',
    'fc stars', 'fc stars of mass'
}

# Load existing lookup
lookup_path = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\club_logo_lookup.json"
with open(lookup_path, 'r') as f:
    logo_lookup = json.load(f)

all_keys = set(logo_lookup.keys()) | JS_MAPPINGS

# Connect to database
db_path = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get clubs with team counts in major leagues
cursor.execute("""
    SELECT club_name, league, COUNT(*) as team_count
    FROM teams
    WHERE club_name IS NOT NULL
    AND club_name != ''
    AND league IN ('ECNL', 'ECNL-RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT')
    AND club_name NOT LIKE '%%(%%)%%'
    AND LENGTH(club_name) > 3
    GROUP BY club_name
    ORDER BY team_count DESC
    LIMIT 150
""")

clubs = cursor.fetchall()

# Check which don't have logos
missing = []
for club_name, league, count in clubs:
    normalized = club_name.lower()
    has_logo = False
    for key in all_keys:
        if key in normalized or normalized in key:
            has_logo = True
            break
    if not has_logo:
        missing.append((club_name, league, count))

print('MAJOR CLUBS STILL NEEDING LOGOS (sorted by team count):')
print('=' * 60)
for club_name, league, count in missing[:40]:
    print(f'{count:3d} teams | {league:8s} | {club_name}')

conn.close()
