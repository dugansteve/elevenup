"""
Create a mapping of club names to logo files.
"""
import sqlite3
import json
import os
import re

# Path to logos folder
LOGOS_DIR = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\club_logos"

# Get list of logo files
logo_files = os.listdir(LOGOS_DIR)
print(f"Found {len(logo_files)} logo files")

# Create mapping from logo filename to potential club names
# Logo names are like "Alabama_FC_logo.png" -> "Alabama FC"
def logo_filename_to_club_name(filename):
    """Convert logo filename to club name for matching"""
    # Remove extension and _logo suffix
    name = os.path.splitext(filename)[0]
    name = name.replace('_logo', '')
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    return name

# Build initial mapping
logo_mapping = {}
for logo_file in logo_files:
    club_name = logo_filename_to_club_name(logo_file)
    logo_mapping[club_name.lower()] = {
        'filename': logo_file,
        'display_name': club_name,
        'matched_clubs': []
    }

print(f"Initial logo mappings: {len(logo_mapping)}")

# Connect to database and get all unique clubs
db_path = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get distinct clubs that look like real club names (not field names, scores, etc.)
cursor.execute("""
    SELECT DISTINCT club_name
    FROM teams
    WHERE club_name IS NOT NULL
    AND club_name != ''
    AND club_name NOT LIKE '%(11v11)%'
    AND club_name NOT LIKE '%Field%'
    AND club_name NOT LIKE '%PKS%'
    AND club_name NOT LIKE '%Final%'
    AND club_name NOT LIKE '%Semi%'
    AND club_name NOT LIKE '***%'
    AND club_name NOT LIKE '*%'
    AND club_name NOT LIKE '-%'
    AND club_name NOT LIKE '/%'
    AND LENGTH(club_name) > 3
    ORDER BY club_name
""")

all_clubs = [row[0] for row in cursor.fetchall()]
print(f"Found {len(all_clubs)} distinct clubs in database")

# Function to normalize club names for matching
def normalize_for_matching(name):
    """Normalize club name for fuzzy matching"""
    name = name.lower()
    # Remove common suffixes
    name = re.sub(r'\s+(sc|fc|sa|soccer|club|academy|youth|futbol|soccer club)$', '', name)
    name = re.sub(r'\s+(boys?|girls?)$', '', name)
    # Remove age groups
    name = re.sub(r'\s+\d{2,4}[bg]?\s*', ' ', name)
    name = re.sub(r'\s+[gb]\d{2,4}\s*', ' ', name)
    # Remove colors
    name = re.sub(r'\s+(black|blue|red|white|gold|green|orange|yellow|purple|navy|gray|grey)\s*', ' ', name)
    # Clean up
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# Manual mapping for known clubs with different naming
MANUAL_MAPPINGS = {
    # Logo filename -> database club name patterns
    'alabama fc': ['Alabama FC'],
    'ac connecticut': ['AC Connecticut'],
    'albion hurricanes': ['Albion Hurricanes FC'],
    'arizona arsenal': ['Arizona Arsenal'],
    'arlington soccer': ['Arlington Soccer Association'],
    'arsenal colorado': ['Arsenal Colorado'],
    'association fc': ['Association Football Club'],
    'atletico dallas youth': ['Atletico Dallas Youth'],
    'avanti sa': ['Avanti Soccer Academy', 'Avanti SA'],
    'beach fc ca': ['BEACH FC', 'Beach FC'],
    'beach fc va': ['Beach FC VA'],
    'bethesda sc': ['Bethesda SC'],
    'boerne sc': ['Boerne SC'],
    'boise thorns fc': ['Boise Thorns FC', 'Boise Timbers Thorns FC'],
    'bryc academy': ['BRYC', 'BRYC Academy'],
    'bvbia': ['BVBIA', 'BVB IA'],
    'cesa liberty': ['CESA', 'CESA Liberty'],
    'charlotte sa gold': ['Charlotte SA', 'Charlotte Soccer Academy'],
    'chattanooga': ['Chattanooga FC', 'Chattanooga Red Wolves'],
    'city sc utah': ['City SC Utah'],
    'coastal rush': ['Coastal Rush'],
    'colorado edge': ['Colorado EDGE'],
    'colorado rapids central': ['Colorado Rapids', 'Colorado Rapids Youth'],
    'colorado rush academy': ['Colorado Rush', 'Colorado Rush Soccer Club'],
    'concorde fire': ['Concorde Fire'],
    'connecticut fc': ['Connecticut FC'],
    'dallas cosmos sc': ['Dallas Cosmos SC'],
    'dallas surf': ['Dallas Surf', 'Surf'],
    'dallas texans': ['Dallas Texans', 'Texans'],
    'dksc white': ['DKSC', 'Dallas Kicks SC'],
    'eagles sc': ['Eagles SC'],
    'eastside timbers': ['Eastside Timbers FC', 'Eastside Timbers'],
    'evolution': ['Evolution SC'],
    'fc copa academy': ['FC Copa Academy', 'FC Copa'],
    'fc dallas': ['FC Dallas'],
    'fc stars': ['FC Stars', 'FC Stars of Mass'],
    'force': ['Force SC'],
    'fsa fc': ['FSA FC'],
    'great falls reston soccer': ['Great Falls Reston Soccer', 'GFRSC'],
    'gsa': ['GSA', 'Georgia Soccer Academy'],
    'gulf coast': ['Gulf Coast Soccer Club', 'Gulf Coast SC'],
    'hex fc': ['HEX FC'],
    'highland fc': ['Highland FC'],
    'idaho rush': ['Idaho Rush'],
    'indiana': ['Indiana Fire', 'Indiana Fire Academy'],
    'kansas rush': ['Kansas Rush'],
    'kernow storm fc': ['Kernow Storm FC'],
    'la roca fc': ['La Roca FC'],
    'lions': ['Lions FC'],
    'livermore fusion sc': ['Livermore Fusion SC', 'Livermore Fusion'],
    'liverpool fc ia gma': ['Liverpool FC IA', 'Liverpool IA'],
    'manhattan sc': ['Manhattan SC'],
    'mercury': ['Mercury'],
    'michigan': ['Michigan Hawks', 'Michigan Jaguars'],
    'mississippi': ['Mississippi FC', 'Mississippi Rush'],
    'missouri': ['Missouri Rush'],
    'nc fusion': ['NC Fusion'],
    'ncfc youth': ['NCFC Youth', 'NCFC'],
    'nlsa': ['NLSA'],
    'ntx celtic fc green': ['NTX Celtic FC', 'NTX Celtic'],
    'ohio': ['Ohio Premier', 'Ohio Elite SA'],
    'pateadores': ['Pateadores', 'Pateadores Soccer Club'],
    'pda scp': ['PDA', 'PDA South'],
    'pda south white': ['PDA South'],
    'philadelphia': ['Philadelphia SC', 'Philadelphia Union'],
    'phoenix rising': ['Phoenix Rising', 'Phoenix Rising FC'],
    'pittsburgh riverhounds': ['Pittsburgh Riverhounds', 'Riverhounds'],
    'plymouth reign sc': ['Plymouth Reign SC'],
    'pride sc': ['Pride SC', 'Pride Soccer Club'],
    'psa': ['PSA', 'Players Soccer Academy'],
    'psa north': ['PSA North'],
    'pwsi': ['PWSI', 'Prince William Soccer Inc'],
    'racing louisville academy': ['Racing Louisville', 'Racing Louisville Academy'],
    'reading rage surf': ['Reading Rage SC', 'Reading Rage Surf'],
    'real colorado': ['Real Colorado'],
    'rebels sc': ['Rebels SC'],
    'rockford raptors': ['Rockford Raptors'],
    'rush select': ['Rush Select', 'Rush'],
    'scorpions': ['Scorpions SC'],
    'seattle': ['Seattle United', 'Seattle Sounders'],
    'slammers fc hb koge': ['Slammers FC', 'SLAMMERS FC'],
    'slammers fc': ['Slammers FC', 'SLAMMERS FC'],
    'slsg': ['SLSG', 'St. Louis Scott Gallagher'],
    'solar blue': ['Solar SC', 'Solar'],
    'south': ['South Florida United'],
    'sporting iowa': ['Sporting Iowa'],
    'sporting kansas city': ['Sporting Kansas City', 'Sporting KC'],
    'sporting': ['Sporting'],
    'sporting springfield': ['Sporting Springfield'],
    'stafford': ['Stafford Soccer'],
    'stanford strikers': ['Stanford Strikers'],
    'sting nebraska': ['Sting Nebraska'],
    'susa fc': ['SUSA FC', 'SUSA'],
    'tennessee sc': ['Tennessee SC', 'Tennessee Soccer Club'],
    'texoma soccer academy': ['Texoma Soccer Academy'],
    'united': ['United FC'],
    'utah avalanche': ['Utah Avalanche'],
    'utah': ['Utah Celtic', 'Utah FC'],
    'utah surf': ['Utah Surf'],
    'vienna': ['Vienna Youth Soccer'],
    'west mont united': ['West Mont United SA'],
    'wilmington hammerheads': ['Wilmington Hammerheads'],
    'world class fc': ['World Class FC'],
}

# Build final mapping
final_mapping = {}

for logo_key, logo_info in logo_mapping.items():
    # Get manual mappings if available
    if logo_key in MANUAL_MAPPINGS:
        final_mapping[logo_key] = {
            'filename': logo_info['filename'],
            'display_name': logo_info['display_name'],
            'club_patterns': MANUAL_MAPPINGS[logo_key]
        }
    else:
        # Use the display name as the pattern
        final_mapping[logo_key] = {
            'filename': logo_info['filename'],
            'display_name': logo_info['display_name'],
            'club_patterns': [logo_info['display_name']]
        }

# Save as JSON for React to use
output_path = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\club_logos.json"
with open(output_path, 'w') as f:
    json.dump(final_mapping, f, indent=2)

print(f"Saved logo mapping to {output_path}")

# Also create a simpler direct mapping for quick lookup
simple_mapping = {}
for logo_key, info in final_mapping.items():
    for pattern in info['club_patterns']:
        simple_mapping[pattern.lower()] = info['filename']
    # Also add the key itself
    simple_mapping[logo_key] = info['filename']

# Save simple mapping
simple_output = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\club_logo_lookup.json"
with open(simple_output, 'w') as f:
    json.dump(simple_mapping, f, indent=2)

print(f"Saved simple lookup to {simple_output}")

# Count how many database clubs we can match
matched_count = 0
unmatched_clubs = []
for club in all_clubs:
    club_lower = club.lower()
    found = False
    for pattern in simple_mapping.keys():
        if pattern in club_lower or club_lower in pattern:
            matched_count += 1
            found = True
            break
    if not found:
        # Filter out junk entries
        if not any(x in club_lower for x in ['(', ')', 'pks', 'final', 'semi', 'field', '/']):
            unmatched_clubs.append(club)

print(f"\nMatched {matched_count} out of {len(all_clubs)} database clubs")
print(f"Unmatched clubs (first 50): {len(unmatched_clubs)}")
for club in unmatched_clubs[:50]:
    print(f"  - {club}")

conn.close()
