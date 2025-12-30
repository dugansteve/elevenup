"""
Database Cleanup Script for Seedline
Fixes data quality issues in priority order
"""

import sqlite3
import re
from datetime import datetime
from collections import defaultdict
import sys

DB_PATH = r'C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db'

# State name to abbreviation mapping
STATE_ABBREV = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
}

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def backup_database():
    """Create a backup before making changes"""
    import shutil
    backup_path = DB_PATH.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy(DB_PATH, backup_path)
    print(f"[OK] Database backed up to: {backup_path}")
    sys.stdout.flush()
    return backup_path

def fix_duplicate_games(conn):
    """Remove duplicate game entries using efficient SQL"""
    print("\n" + "="*60)
    print("1. FIXING DUPLICATE GAMES")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    # More efficient approach: delete duplicates keeping lowest id
    # First count
    cursor.execute('''
        SELECT COUNT(*) FROM games g1
        WHERE EXISTS (
            SELECT 1 FROM games g2
            WHERE g2.home_team = g1.home_team
              AND g2.away_team = g1.away_team
              AND g2.game_date = g1.game_date
              AND COALESCE(g2.age_group, '') = COALESCE(g1.age_group, '')
              AND COALESCE(g2.league, '') = COALESCE(g1.league, '')
              AND g2.id < g1.id
        )
    ''')
    dup_count = cursor.fetchone()[0]
    print(f"Found {dup_count:,} duplicate game entries to delete")
    sys.stdout.flush()

    if dup_count > 0:
        # Delete duplicates (keep lowest id = oldest record)
        cursor.execute('''
            DELETE FROM games
            WHERE id IN (
                SELECT g1.id FROM games g1
                WHERE EXISTS (
                    SELECT 1 FROM games g2
                    WHERE g2.home_team = g1.home_team
                      AND g2.away_team = g1.away_team
                      AND g2.game_date = g1.game_date
                      AND COALESCE(g2.age_group, '') = COALESCE(g1.age_group, '')
                      AND COALESCE(g2.league, '') = COALESCE(g1.league, '')
                      AND g2.id < g1.id
                )
            )
        ''')
        conn.commit()
        print(f"[OK] Deleted {dup_count:,} duplicate games")
    else:
        print("[OK] No duplicates found")
    sys.stdout.flush()

    return dup_count

def fix_hidden_teams(conn):
    """Remove 'Hidden' placeholder teams and their games"""
    print("\n" + "="*60)
    print("2. FIXING 'HIDDEN' PLACEHOLDER DATA")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    # Count and delete Hidden teams
    cursor.execute("SELECT COUNT(*) FROM teams WHERE team_name = 'Hidden' OR club_name = 'Hidden'")
    hidden_teams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM games WHERE home_team = 'Hidden' OR away_team = 'Hidden'")
    hidden_games = cursor.fetchone()[0]

    print(f"Found {hidden_teams} 'Hidden' teams, {hidden_games} games")

    cursor.execute("DELETE FROM teams WHERE team_name = 'Hidden' OR club_name = 'Hidden'")
    cursor.execute("DELETE FROM games WHERE home_team = 'Hidden' OR away_team = 'Hidden'")

    conn.commit()
    print(f"[OK] Deleted Hidden teams and games")
    sys.stdout.flush()

    return hidden_teams, hidden_games

def fix_pks_scores(conn):
    """Fix games where PKS results were parsed as team names"""
    print("\n" + "="*60)
    print("3. FIXING PKS SCORE PARSING ERRORS")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM games WHERE away_team LIKE '%PKS:%'")
    pks_games = cursor.fetchone()[0]

    cursor.execute("DELETE FROM games WHERE away_team LIKE '%PKS:%'")
    cursor.execute("DELETE FROM teams WHERE team_name LIKE '%PKS:%'")

    conn.commit()
    print(f"[OK] Deleted {pks_games} corrupted PKS games")
    sys.stdout.flush()

    return pks_games

def fix_impossible_scores(conn):
    """Fix games with impossible scores"""
    print("\n" + "="*60)
    print("4. FIXING IMPOSSIBLE SCORES")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE games
        SET home_score = NULL, away_score = NULL
        WHERE home_score > 20 OR away_score > 20 OR home_score < 0 OR away_score < 0
    """)
    fixed = cursor.rowcount

    conn.commit()
    print(f"[OK] Reset {fixed} games with invalid scores to NULL")
    sys.stdout.flush()

    return fixed

def normalize_states(conn):
    """Convert full state names to 2-letter abbreviations"""
    print("\n" + "="*60)
    print("5. NORMALIZING STATE ABBREVIATIONS")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()
    total_updated = 0

    for full_name, abbrev in STATE_ABBREV.items():
        cursor.execute("UPDATE teams SET state = ? WHERE LOWER(state) = ?", (abbrev, full_name))
        count = cursor.rowcount
        if count > 0:
            print(f"  {full_name.title()} -> {abbrev}: {count} teams")
            total_updated += count

    # Fix 'US' state values
    cursor.execute("UPDATE teams SET state = NULL WHERE state = 'US'")
    us_count = cursor.rowcount
    if us_count > 0:
        print(f"  'US' -> NULL: {us_count} teams")
        total_updated += us_count

    conn.commit()
    print(f"[OK] Normalized {total_updated} state values")
    sys.stdout.flush()

    return total_updated

def standardize_gender(conn):
    """Standardize gender values to Boys/Girls"""
    print("\n" + "="*60)
    print("6. STANDARDIZING GENDER VALUES")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    cursor.execute("UPDATE teams SET gender = 'Boys' WHERE gender = 'Male'")
    t1 = cursor.rowcount
    cursor.execute("UPDATE games SET gender = 'Boys' WHERE gender = 'Male'")
    g1 = cursor.rowcount
    cursor.execute("UPDATE teams SET gender = NULL WHERE gender = 'Both'")
    t2 = cursor.rowcount
    cursor.execute("UPDATE games SET gender = NULL WHERE gender IN ('Both', 'None')")
    g2 = cursor.rowcount

    conn.commit()
    total = t1 + g1 + t2 + g2
    print(f"[OK] Standardized {total} gender values (Male->Boys, Both/None->NULL)")
    sys.stdout.flush()

    return total

def fix_tbd_games(conn):
    """Remove TBD placeholder games"""
    print("\n" + "="*60)
    print("7. FIXING TBD PLACEHOLDER GAMES")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM games
        WHERE home_team LIKE 'TBD%' OR away_team LIKE 'TBD%'
           OR home_team = '' OR away_team = ''
           OR home_team IS NULL OR away_team IS NULL
    """)
    tbd_count = cursor.fetchone()[0]

    cursor.execute("""
        DELETE FROM games
        WHERE home_team LIKE 'TBD%' OR away_team LIKE 'TBD%'
           OR home_team = '' OR away_team = ''
           OR home_team IS NULL OR away_team IS NULL
    """)

    conn.commit()
    print(f"[OK] Deleted {tbd_count} TBD/empty team games")
    sys.stdout.flush()

    return tbd_count

def create_missing_team_records(conn):
    """Create team records for teams in games but not in teams table"""
    print("\n" + "="*60)
    print("8. CREATING MISSING TEAM RECORDS")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    # Get unique teams from games not in teams table
    cursor.execute("""
        SELECT DISTINCT g.home_team as team, g.league, g.age_group, g.gender
        FROM games g
        LEFT JOIN teams t ON g.home_team = t.team_name AND g.league = t.league
        WHERE t.team_name IS NULL
          AND g.home_team IS NOT NULL AND g.home_team != ''
        UNION
        SELECT DISTINCT g.away_team as team, g.league, g.age_group, g.gender
        FROM games g
        LEFT JOIN teams t ON g.away_team = t.team_name AND g.league = t.league
        WHERE t.team_name IS NULL
          AND g.away_team IS NOT NULL AND g.away_team != ''
    """)

    missing = cursor.fetchall()
    print(f"Found {len(missing)} teams needing records")

    inserted = 0
    for row in missing:
        try:
            cursor.execute("""
                INSERT INTO teams (team_name, league, age_group, gender, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            """, (row[0], row[1], row[2], row[3], datetime.now().isoformat()))
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    print(f"[OK] Created {inserted} missing team records")
    sys.stdout.flush()

    return inserted

def normalize_club_names(conn):
    """Normalize club name case variations"""
    print("\n" + "="*60)
    print("9. NORMALIZING CLUB NAME DUPLICATES")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT club_name, COUNT(*) as cnt FROM teams
        WHERE club_name IS NOT NULL AND club_name != ''
        GROUP BY club_name
    """)
    clubs = {row[0]: row[1] for row in cursor.fetchall()}

    # Find case variations
    case_groups = defaultdict(list)
    for club in clubs:
        key = club.lower().strip()
        case_groups[key].append((club, clubs[club]))

    updates = 0
    for key, variants in case_groups.items():
        if len(variants) > 1:
            # Keep the one with most teams
            canonical = sorted(variants, key=lambda x: -x[1])[0][0]
            for variant, count in variants:
                if variant != canonical:
                    cursor.execute("UPDATE teams SET club_name = ? WHERE club_name = ?", (canonical, variant))
                    updates += cursor.rowcount

    conn.commit()
    print(f"[OK] Normalized {updates} club name variations")
    sys.stdout.flush()

    return updates

def populate_mls_next_states(conn):
    """Populate MLS NEXT team states from known data"""
    print("\n" + "="*60)
    print("10. POPULATING MLS NEXT MISSING STATES")
    print("="*60)
    sys.stdout.flush()

    cursor = conn.cursor()

    # Known MLS team locations
    mls_team_states = {
        'LA Galaxy': 'CA', 'LAFC': 'CA', 'San Jose': 'CA', 'Seattle': 'WA',
        'Portland': 'OR', 'Real Salt Lake': 'UT', 'Colorado': 'CO',
        'FC Dallas': 'TX', 'Dallas': 'TX', 'Houston': 'TX', 'Austin': 'TX',
        'Sporting KC': 'KS', 'Kansas City': 'KS', 'Minnesota': 'MN',
        'Chicago': 'IL', 'Columbus': 'OH', 'Nashville': 'TN', 'Atlanta': 'GA',
        'Inter Miami': 'FL', 'Miami': 'FL', 'Orlando': 'FL', 'Charlotte': 'NC',
        'DC United': 'DC', 'Philadelphia': 'PA', 'Red Bull': 'NJ',
        'New York': 'NY', 'NYCFC': 'NY', 'New England': 'MA', 'Revolution': 'MA',
        'St. Louis': 'MO', 'San Diego': 'CA'
    }

    cursor.execute("""
        SELECT id, team_name, club_name FROM teams
        WHERE league = 'MLS NEXT' AND (state IS NULL OR state = '')
    """)
    mls_teams = cursor.fetchall()
    print(f"Found {len(mls_teams)} MLS NEXT teams without state")

    updated = 0
    for row in mls_teams:
        team_id, team_name, club_name = row
        name = f"{team_name or ''} {club_name or ''}".lower()

        for mls_club, state in mls_team_states.items():
            if mls_club.lower() in name:
                cursor.execute("UPDATE teams SET state = ? WHERE id = ?", (state, team_id))
                updated += 1
                break

    # Also inherit from other teams with same club name
    cursor.execute("""
        UPDATE teams
        SET state = (
            SELECT t2.state FROM teams t2
            WHERE t2.club_name = teams.club_name
              AND t2.state IS NOT NULL AND t2.state != ''
            LIMIT 1
        )
        WHERE league = 'MLS NEXT'
          AND (state IS NULL OR state = '')
          AND club_name IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM teams t2
              WHERE t2.club_name = teams.club_name
                AND t2.state IS NOT NULL AND t2.state != ''
          )
    """)
    updated += cursor.rowcount

    conn.commit()
    print(f"[OK] Updated {updated} MLS NEXT team states")
    sys.stdout.flush()

    return updated

def main():
    print("="*60)
    print("SEEDLINE DATABASE CLEANUP")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    sys.stdout.flush()

    # Create backup first
    backup_path = backup_database()

    conn = get_connection()
    results = {}

    try:
        results['1. Duplicate games'] = fix_duplicate_games(conn)
        results['2. Hidden data'] = fix_hidden_teams(conn)
        results['3. PKS games'] = fix_pks_scores(conn)
        results['4. Invalid scores'] = fix_impossible_scores(conn)
        results['5. States normalized'] = normalize_states(conn)
        results['6. Gender standardized'] = standardize_gender(conn)
        results['7. TBD games'] = fix_tbd_games(conn)
        results['8. Missing teams created'] = create_missing_team_records(conn)
        results['9. Club names normalized'] = normalize_club_names(conn)
        results['10. MLS states'] = populate_mls_next_states(conn)

        print("\n" + "="*60)
        print("CLEANUP COMPLETE!")
        print("="*60)
        for task, count in results.items():
            print(f"  {task}: {count}")
        sys.stdout.flush()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        conn.close()

if __name__ == '__main__':
    main()
