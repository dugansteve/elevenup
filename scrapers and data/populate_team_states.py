#!/usr/bin/env python3
"""
Populate state data for teams that are missing it.
Extracts state from team names, club names, and conference mappings.
"""

import sqlite3
import re
from pathlib import Path

# City to state mapping - common cities in team names
CITY_TO_STATE = {
    # Texas
    'dallas': 'TX', 'houston': 'TX', 'htx': 'TX', 'san antonio': 'TX', 'austin': 'TX',
    'frisco': 'TX', 'plano': 'TX', 'fort worth': 'TX', 'dfw': 'TX', 'texas': 'TX',
    'lonestar': 'TX', 'lone star': 'TX', 'texans': 'TX',

    # California
    'san diego': 'CA', 'los angeles': 'CA', 'la ': 'CA', 'socal': 'CA', 'so cal': 'CA',
    'norcal': 'CA', 'bay area': 'CA', 'sf ': 'CA', 'san francisco': 'CA', 'oakland': 'CA',
    'sacramento': 'CA', 'irvine': 'CA', 'orange county': 'CA', 'oc ': 'CA',
    'california': 'CA', 'marin': 'CA', 'palo alto': 'CA', 'san jose': 'CA',
    'santa clara': 'CA', 'fremont': 'CA', 'pleasanton': 'CA', 'albion sc': 'CA',
    'legends fc': 'CA', 'surf sc': 'CA', 'strikers fc': 'CA', 'real so cal': 'CA',
    'lafc': 'CA', 'la galaxy': 'CA', 'beach fc': 'CA', 'slammers': 'CA',
    # NorCal clubs in GA Northwest conference (NOT Washington!)
    'lamorinda': 'CA', 'orinda': 'CA', 'walnut creek': 'CA', 'danville': 'CA',
    'san ramon': 'CA', 'concord': 'CA', 'antioch': 'CA', 'benicia': 'CA',
    'vallejo': 'CA', 'napa': 'CA', 'santa rosa': 'CA', 'petaluma': 'CA',
    'sonoma': 'CA', 'novato': 'CA', 'san rafael': 'CA', 'berkeley': 'CA',
    'alameda': 'CA', 'hayward': 'CA', 'union city': 'CA', 'newark': 'CA',
    'milpitas': 'CA', 'sunnyvale': 'CA', 'cupertino': 'CA', 'mountain view': 'CA',
    'menlo park': 'CA', 'redwood city': 'CA', 'san mateo': 'CA', 'burlingame': 'CA',
    'daly city': 'CA', 'san bruno': 'CA', 'pacifica': 'CA', 'half moon bay': 'CA',
    'mustang sc': 'CA', 'deanza force': 'CA', 'de anza': 'CA', 'earthquakes': 'CA',
    'clovis': 'CA', 'fresno': 'CA', 'bakersfield': 'CA', 'visalia': 'CA',
    'modesto': 'CA', 'stockton': 'CA', 'tracy': 'CA', 'livermore': 'CA',
    'dublin': 'CA', 'castro valley': 'CA', 'san leandro': 'CA',

    # Florida
    'miami': 'FL', 'orlando': 'FL', 'tampa': 'FL', 'jacksonville': 'FL', 'florida': 'FL',
    'boca': 'FL', 'fort lauderdale': 'FL', 'naples': 'FL', 'sarasota': 'FL',
    'palm beach': 'FL', 'clearwater': 'FL', 'st pete': 'FL', 'pinellas': 'FL',
    'gainesville': 'FL', 'tallahassee': 'FL', 'pensacola': 'FL', 'fl premier': 'FL',
    'florida premier': 'FL', 'img academy': 'FL', 'dme academy': 'FL',

    # Ohio
    'cincinnati': 'OH', 'columbus': 'OH', 'cleveland': 'OH', 'ohio': 'OH',
    'dayton': 'OH', 'akron': 'OH', 'toledo': 'OH',

    # Pennsylvania
    'pittsburgh': 'PA', 'philadelphia': 'PA', 'philly': 'PA', 'pa classics': 'PA',
    'penn': 'PA', 'keystone': 'PA', 'harrisburg': 'PA', 'lehigh': 'PA',

    # Missouri
    'st louis': 'MO', 'st. louis': 'MO', 'kansas city': 'MO', 'lou fusz': 'MO',
    'scott gallagher': 'MO', 'slsg': 'MO', 'missouri': 'MO', 'gateway': 'MO',

    # Illinois
    'chicago': 'IL', 'illinois': 'IL', 'naperville': 'IL', 'schaumburg': 'IL',
    'sockers fc': 'IL', 'eclipse': 'IL',

    # Indiana
    'indianapolis': 'IN', 'indy': 'IN', 'indiana': 'IN', 'carmel': 'IN',

    # Tennessee
    'nashville': 'TN', 'knoxville': 'TN', 'memphis': 'TN', 'tennessee': 'TN',
    'chattanooga': 'TN',

    # Georgia
    'atlanta': 'GA', 'georgia': 'GA', 'marietta': 'GA', 'alpharetta': 'GA',
    'tophat': 'GA', 'concorde fire': 'GA', 'united fa': 'GA',

    # North Carolina
    'charlotte': 'NC', 'raleigh': 'NC', 'durham': 'NC', 'greensboro': 'NC',
    'cary': 'NC', 'ncfc': 'NC', 'north carolina': 'NC', 'nc fusion': 'NC',

    # South Carolina
    'charleston': 'SC', 'columbia': 'SC', 'greenville': 'SC', 'south carolina': 'SC',
    'sc surf': 'SC', 'sc united': 'SC',

    # Virginia
    'virginia': 'VA', 'richmond': 'VA', 'norfolk': 'VA', 'vb city': 'VA',
    'virginia beach': 'VA', 'arlington': 'VA', 'alexandria': 'VA', 'fairfax': 'VA',
    'loudoun': 'VA', 'vda': 'VA', 'virginia dev': 'VA', 'stafford': 'VA',

    # Maryland
    'baltimore': 'MD', 'maryland': 'MD', 'bethesda': 'MD', 'rockville': 'MD',
    'coppermine': 'MD', 'pipeline': 'MD',

    # New Jersey
    'new jersey': 'NJ', 'nj ': 'NJ', 'pda': 'NJ', 'sjeb': 'NJ', 'jersey': 'NJ',
    'princeton': 'NJ', 'toms river': 'NJ', 'match fit': 'NJ',

    # New York
    'new york': 'NY', 'nyc': 'NY', 'brooklyn': 'NY', 'manhattan': 'NY',
    'buffalo': 'NY', 'rochester': 'NY', 'wny': 'NY', 'long island': 'NY',
    'westchester': 'NY', 'albany': 'NY',

    # Colorado
    'denver': 'CO', 'colorado': 'CO', 'boulder': 'CO', 'aurora': 'CO',
    'real colorado': 'CO', 'rapids': 'CO',

    # Arizona
    'phoenix': 'AZ', 'arizona': 'AZ', 'scottsdale': 'AZ', 'tucson': 'AZ',
    'az arsenal': 'AZ', 'sc del sol': 'AZ', 'real salt lake az': 'AZ',

    # Nevada
    'las vegas': 'NV', 'vegas': 'NV', 'nevada': 'NV', 'henderson': 'NV',
    'lv heat': 'NV',

    # Utah
    'salt lake': 'UT', 'utah': 'UT', 'provo': 'UT', 'ogden': 'UT',
    'real salt lake': 'UT', 'la roca': 'UT', 'utah celtic': 'UT',

    # Washington state
    'seattle': 'WA', 'tacoma': 'WA', 'washington': 'WA', 'bellevue': 'WA',
    'spokane': 'WA', 'eastside fc': 'WA', 'crossfire': 'WA',

    # Oregon
    'portland': 'OR', 'oregon': 'OR', 'eugene': 'OR', 'salem': 'OR',
    'thorns': 'OR', 'timbers': 'OR',

    # Michigan
    'detroit': 'MI', 'michigan': 'MI', 'ann arbor': 'MI', 'grand rapids': 'MI',
    'lansing': 'MI', 'vardar': 'MI', 'crew juniors': 'MI', 'michigan jaguars': 'MI',

    # Wisconsin
    'milwaukee': 'WI', 'wisconsin': 'WI', 'madison': 'WI', 'elmbrook': 'WI',
    'sc waukesha': 'WI',

    # Minnesota
    'minnesota': 'MN', 'minneapolis': 'MN', 'twin cities': 'MN', 'st paul': 'MN',
    'mn thunder': 'MN', 'tonka': 'MN',

    # Oklahoma
    'oklahoma': 'OK', 'tulsa': 'OK', 'okc': 'OK', 'ok energy': 'OK',

    # Kansas
    'kansas': 'KS', 'wichita': 'KS', 'sporting kc': 'KS', 'kc': 'KS',

    # Iowa
    'iowa': 'IA', 'des moines': 'IA',

    # Nebraska
    'nebraska': 'NE', 'omaha': 'NE', 'lincoln': 'NE',

    # Louisiana
    'louisiana': 'LA', 'new orleans': 'LA', 'baton rouge': 'LA', 'cajun': 'LA',

    # Alabama
    'alabama': 'AL', 'birmingham': 'AL', 'huntsville': 'AL', 'mobile': 'AL',

    # Kentucky
    'kentucky': 'KY', 'louisville': 'KY', 'lexington': 'KY', 'racing lou': 'KY',

    # Connecticut
    'connecticut': 'CT', 'hartford': 'CT', 'ct ': 'CT',

    # Massachusetts
    'boston': 'MA', 'massachusetts': 'MA', 'new england': 'MA',

    # Misc specific clubs
    'solar sc': 'TX', 'sting': 'TX', 'lonestar sc': 'TX', 'challenge sc': 'CO',
    'fc dallas': 'TX', 'fc united': 'IL', 'midwest united': 'IN',
    'internationals sc': 'OH', 'crew': 'OH',

    # MLS NEXT Teams (affiliate academy names)
    'inter miami': 'FL', 'miami cf': 'FL', 'cf inter miami': 'FL',
    'orlando city': 'FL', 'oc lions': 'FL', 'ocsc': 'FL',
    'atlanta utd': 'GA', 'atlanta united': 'GA', 'atlanta utd fc': 'GA',
    'dc united': 'DC', 'dcu': 'DC', 'd.c. united': 'DC',
    'philadelphia union': 'PA', 'pu academy': 'PA', 'union academy': 'PA',
    'red bulls': 'NJ', 'ny red bulls': 'NJ', 'nyrb': 'NJ', 'new york red bulls': 'NJ',
    'nycfc': 'NY', 'nyc fc': 'NY', 'new york city fc': 'NY',
    'new england revolution': 'MA', 'revolution': 'MA', 'ne revolution': 'MA', 'revs': 'MA',
    'nashville sc': 'TN', 'nsc': 'TN',
    'charlotte fc': 'NC', 'clt fc': 'NC',
    'austin fc': 'TX', 'verde': 'TX', 'atx': 'TX',
    'houston dynamo': 'TX', 'dynamo': 'TX',
    'sporting kc academy': 'KS', 'skc academy': 'KS', 'sporting academy': 'KS',
    'st louis city': 'MO', 'stl city': 'MO', 'city sc': 'MO',
    'fc cincinnati': 'OH', 'fcc academy': 'OH',
    'columbus crew': 'OH', 'crew academy': 'OH',
    'chicago fire': 'IL', 'cf academy': 'IL', 'fire academy': 'IL',
    'minnesota utd': 'MN', 'mnufc': 'MN', 'loons academy': 'MN',
    'real salt lake academy': 'UT', 'rsl academy': 'UT',
    'colorado rapids academy': 'CO',
    'portland timbers academy': 'OR', 'timbers academy': 'OR',
    'seattle sounders academy': 'WA', 'sounders academy': 'WA', 'sounders fc academy': 'WA',
    'vancouver whitecaps': 'BC',
    'la galaxy academy': 'CA', 'galaxy academy': 'CA',
    'lafc academy': 'CA',
    'san jose quakes': 'CA', 'earthquakes academy': 'CA',
    'san diego fc': 'CA', 'sd loyal': 'CA',

    # ECNL/ECNL RL clubs
    'lvu rush': 'NV', 'fc wisconsin': 'WI', 'fc dallas yth': 'TX',
    'dksc': 'TX', 'dfeeters': 'TX', 'texans soccer': 'TX',
    'btb rush': 'ID', 'fc idaho': 'ID', 'idaho rush': 'ID',
    'connecticut fc': 'CT', 'ct fc': 'CT',
    'btc premier': 'PA', 'btc fc': 'PA',
    'albion hurricanes': 'TX', 'albion hurr': 'TX',
    'fc alliance': 'VA', 'beach fc va': 'VA',
    'beach fc ': 'CA',  # Default Beach FC is California
    'arsenal fc az': 'AZ', 'arsenal fc ': 'AZ',
    'mustang sc': 'CA', 'mustang ': 'CA',
    'de anza force': 'CA', 'deanza': 'CA',
    'psc baltimore': 'MD', 'pipeline sc': 'MD',
    'dcfc': 'MI',
    'north carolina fc': 'NC', 'ncfc youth': 'NC',
    'galacticos': 'TX',
    'waza fc': 'MI',

    # More ECNL/ECNL RL clubs
    'nc courage': 'NC', 'courage academy': 'NC',
    'wilmington hammerheads': 'NC', 'hammerheads': 'NC',
    'mvla': 'CA', 'mountain view': 'CA', 'los gatos': 'CA',
    'doral soccer': 'FL', 'doral sc': 'FL', 'key biscayne': 'FL',
    'west pines': 'FL',
    'prior lake': 'MN',
    'nationals soccer': 'MI',
    'brentwood sc': 'TN', 'brentwood ': 'TN',
    'fc pride': 'IN',
    'hex fc': 'PA', 'hex pa': 'PA',
    'petersburg fc': 'VA',
    'pioneers fc': 'WA',
    'eastshore alliance': 'MD',

    # Texas region codes
    'stxcl': 'TX', 'ntx': 'TX', 'ctx': 'TX', 'etx': 'TX',
    ' tx ': 'TX', ' tx-': 'TX',
    'pearland': 'TX', 'kaptiva': 'TX', 'rise sc': 'TX',
    'avanti sa': 'TX', 'challenge united': 'TX',
    'agsa force': 'TX', 'atc premier': 'TX',
    'bvbia': 'TX',

    # More California
    'surf cup': 'CA', 'albion sc': 'CA',

    # More Florida
    'atl xpress': 'FL', 'futboltech': 'FL',
    'mount pleasant': 'SC',

    # More Pennsylvania
    'dominion sc': 'PA',

    # Additional patterns from remaining teams
    'el paso': 'TX', 'locomotive fc': 'TX',
    'ny surf': 'NY',
    'rockford': 'IL', 'raptors fc': 'IL',
    'st croix': 'MN',
    'lakeville': 'MN',
    'germantown': 'TN',
    'rebels sc': 'CA', 's.cal': 'CA', 'scal': 'CA',
    'wellington sc': 'FL',
    'one fc': 'FL',
    'jam doral': 'FL',
    'colo colo': 'FL',
    'cyclones fc': 'FL', 'csh': 'FL',
    'wasa sc': 'FL',
    'copa academy': 'TX',
    'cosmos fc': 'NY',
    'forge fc': 'FL',
}

# MLS NEXT team name patterns
MLS_NEXT_TEAM_STATES = {
    'lafc': 'CA', 'la galaxy': 'CA', 'san jose': 'CA', 'sacramento': 'CA',
    'san diego': 'CA',
    'seattle': 'WA', 'sounders': 'WA',
    'portland': 'OR', 'timbers': 'OR',
    'real salt lake': 'UT', 'rsl': 'UT',
    'colorado rapids': 'CO', 'rapids': 'CO',
    'fc dallas': 'TX', 'dallas': 'TX', 'north texas': 'TX',
    'houston dynamo': 'TX', 'dynamo': 'TX', 'houston': 'TX',
    'austin fc': 'TX', 'austin': 'TX',
    'sporting kc': 'KS', 'sporting kansas': 'KS', 'kansas city': 'KS',
    'minnesota united': 'MN', 'loons': 'MN', 'minnesota': 'MN',
    'st louis city': 'MO', 'st. louis': 'MO',
    'chicago fire': 'IL', 'fire': 'IL', 'chicago': 'IL',
    'columbus crew': 'OH', 'crew': 'OH', 'columbus': 'OH',
    'fc cincinnati': 'OH', 'cincinnati': 'OH',
    'nashville sc': 'TN', 'nashville': 'TN',
    'atlanta united': 'GA', 'atlanta': 'GA',
    'inter miami': 'FL', 'miami': 'FL',
    'orlando city': 'FL', 'orlando': 'FL',
    'charlotte fc': 'NC', 'charlotte': 'NC',
    'dc united': 'DC', 'd.c. united': 'DC',
    'philadelphia union': 'PA', 'union': 'PA', 'philadelphia': 'PA',
    'new york red bulls': 'NJ', 'red bulls': 'NJ', 'nyrb': 'NJ',
    'new york city fc': 'NY', 'nycfc': 'NY',
    'new england revolution': 'MA', 'revolution': 'MA', 'new england': 'MA',
    'detroit': 'MI',
}

# Conference to state mapping (fallback)
CONFERENCE_TO_STATE = {
    # GA Conferences
    'Frontier': 'TX',  # Mostly Texas teams
    'Mid-America': 'OH',  # Ohio/Indiana area
    'Mid-Atlantic North': 'MD',  # MD/PA/NJ area
    'Mid-Atlantic South': 'VA',  # VA/NC area
    'Mountain West': 'CO',
    'Northwest': 'WA',
    'Southeast': 'GA',
    'Southwest': 'CA',
    'Pacific': 'CA',

    # ECNL Conferences
    'Texas': 'TX',
    'Midwest': 'IL',
    'Ohio Valley': 'OH',
    'Southeast': 'GA',
    'Mid-Atlantic': 'VA',
    'New England': 'MA',
    'Northwest': 'WA',
    'Southwest': 'CA',
    'Florida': 'FL',

    # ECNL RL Conferences
    'ECNL RL Texas': 'TX',
    'ECNL RL Heartland': 'MO',  # Midwest
    'ECNL RL Great Lakes': 'MI',
    'ECNL RL Southeast': 'GA',
    'ECNL RL Mid-Atlantic': 'VA',
    'ECNL RL Northeast': 'NY',
    'ECNL RL Northwest': 'WA',
    'ECNL RL Southwest': 'CA',
    'ECNL RL Florida': 'FL',
    'ECNL RL National Capital': 'VA',
    'ECNL RL Ohio Valley': 'OH',
    'ECNL RL North Atlantic': 'PA',
    'ECNL RL Southern Cal': 'CA',
    'ECNL RL Northern Cal': 'CA',

    # MLS NEXT Regions
    'MLS NEXT Florida': 'FL',
    'MLS NEXT Frontier': 'TX',
    'MLS NEXT Mid-America': 'MO',
    'MLS NEXT Mid-Atlantic': 'PA',
    'MLS NEXT Northeast': 'NY',
    'MLS NEXT Northwest': 'WA',
    'MLS NEXT Southeast': 'GA',
    'MLS NEXT Southwest': 'CA',
}


def get_state_from_name(team_name, club_name=None, conference=None):
    """Try to determine state from team name, club name, or conference."""
    # Combine names for searching
    search_text = (team_name or '').lower()
    if club_name:
        search_text += ' ' + club_name.lower()

    # Try city/state mappings
    for pattern, state in CITY_TO_STATE.items():
        if pattern in search_text:
            return state

    # Fall back to conference mapping
    if conference:
        for conf_pattern, state in CONFERENCE_TO_STATE.items():
            if conf_pattern.lower() in conference.lower():
                return state

    return None


def main():
    db_path = Path(__file__).parent / 'seedlinedata.db'

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get teams without state data
    cursor.execute("""
        SELECT id, team_name, club_name, conference, league
        FROM teams
        WHERE state IS NULL OR state = ''
    """)

    teams_without_state = cursor.fetchall()
    print(f"Teams without state data: {len(teams_without_state)}")

    # Track updates
    updates = []
    updated_by_league = {}

    for team_id, team_name, club_name, conference, league in teams_without_state:
        state = get_state_from_name(team_name, club_name, conference)

        if state:
            updates.append((state, team_id))
            updated_by_league[league] = updated_by_league.get(league, 0) + 1

    print(f"\nTeams that can be updated: {len(updates)}")
    print("\nUpdates by league:")
    for league, count in sorted(updated_by_league.items(), key=lambda x: -x[1]):
        print(f"  {league}: {count}")

    # Apply updates
    if updates:
        cursor.executemany("""
            UPDATE teams SET state = ? WHERE id = ?
        """, updates)
        conn.commit()
        print(f"\n[OK] Updated {len(updates)} teams with state data")

    # Report final state
    cursor.execute("""
        SELECT league, COUNT(*) as total,
               SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as with_state
        FROM teams
        GROUP BY league
        ORDER BY league
    """)

    print("\nFinal state coverage by league:")
    print("=" * 60)
    for row in cursor.fetchall():
        league, total, with_state = row
        pct = 100 * with_state / total if total > 0 else 0
        print(f"{league:25} | {with_state:5}/{total:5} ({pct:.0f}%)")

    conn.close()


if __name__ == '__main__':
    main()
