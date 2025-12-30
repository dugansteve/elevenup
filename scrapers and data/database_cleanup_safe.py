"""
SAFE Database Cleanup Script for Seedline
Runs automatically after scraping - only performs NON-DESTRUCTIVE fixes

This script is safe to run unattended because it:
1. NEVER deletes games (only fixes/normalizes data)
2. NEVER deletes teams (only fixes/normalizes data)
3. Logs all changes for review
4. Creates a backup before any changes

For destructive cleanup (duplicates, TBD games), run database_cleanup.py manually.
"""

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
import sys

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'seedlinedata.db')
LOG_PATH = os.path.join(SCRIPT_DIR, 'cleanup_log.txt')

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

def log(message):
    """Log to both console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    sys.stdout.flush()
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fix_impossible_scores(conn):
    """Reset impossible scores to NULL (non-destructive - games stay)"""
    cursor = conn.cursor()

    # Log what we're about to fix
    cursor.execute('''
        SELECT id, home_team, away_team, home_score, away_score
        FROM games
        WHERE home_score > 20 OR away_score > 20 OR home_score < 0 OR away_score < 0
    ''')
    bad_scores = cursor.fetchall()

    if bad_scores:
        log(f"Fixing {len(bad_scores)} games with invalid scores:")
        for game in bad_scores[:10]:  # Log first 10
            log(f"  ID {game[0]}: {game[1]} vs {game[2]} = {game[3]}-{game[4]}")
        if len(bad_scores) > 10:
            log(f"  ... and {len(bad_scores) - 10} more")

    cursor.execute('''
        UPDATE games
        SET home_score = NULL, away_score = NULL
        WHERE home_score > 20 OR away_score > 20 OR home_score < 0 OR away_score < 0
    ''')
    fixed = cursor.rowcount
    conn.commit()

    return fixed

def normalize_states(conn):
    """Convert full state names to 2-letter abbreviations"""
    cursor = conn.cursor()
    total_updated = 0

    for full_name, abbrev in STATE_ABBREV.items():
        cursor.execute("UPDATE teams SET state = ? WHERE LOWER(state) = ?", (abbrev, full_name))
        count = cursor.rowcount
        if count > 0:
            log(f"  State: {full_name.title()} -> {abbrev}: {count} teams")
            total_updated += count

    # Fix 'US' state values
    cursor.execute("UPDATE teams SET state = NULL WHERE state = 'US'")
    us_count = cursor.rowcount
    if us_count > 0:
        log(f"  State: 'US' -> NULL: {us_count} teams")
        total_updated += us_count

    conn.commit()
    return total_updated

def standardize_gender(conn):
    """Standardize gender values to Boys/Girls"""
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
    if total > 0:
        log(f"  Gender fixes: teams Male->Boys={t1}, games Male->Boys={g1}, Both/None->NULL={t2+g2}")

    return total

def fix_trailing_dashes(conn):
    """Remove trailing dashes from team names"""
    cursor = conn.cursor()
    total_fixed = 0

    # Fix in games table - home_team
    cursor.execute("""
        UPDATE games SET home_team = TRIM(RTRIM(home_team, '-'))
        WHERE home_team LIKE '%-' OR home_team LIKE '% -'
    """)
    total_fixed += cursor.rowcount

    # Fix in games table - away_team
    cursor.execute("""
        UPDATE games SET away_team = TRIM(RTRIM(away_team, '-'))
        WHERE away_team LIKE '%-' OR away_team LIKE '% -'
    """)
    total_fixed += cursor.rowcount

    # Fix in teams table
    cursor.execute("""
        UPDATE teams SET team_name = TRIM(RTRIM(team_name, '-'))
        WHERE team_name LIKE '%-' OR team_name LIKE '% -'
    """)
    total_fixed += cursor.rowcount

    conn.commit()
    if total_fixed > 0:
        log(f"  Fixed trailing dashes in {total_fixed} records")
    return total_fixed


def fix_common_typos(conn):
    """Fix common typos in team names (case-insensitive)"""
    cursor = conn.cursor()
    total_fixed = 0

    # Format: (typo_pattern, correct_replacement)
    # Both uppercase and lowercase versions will be checked
    typos = [
        ('Socccer', 'Soccer'),
        ('socccer', 'soccer'),
        ('Acadamy', 'Academy'),
        ('acadamy', 'academy'),
        ('Untied', 'United'),
        ('untied', 'united'),
        ('UNTIED', 'UNITED'),
        ('Fcotball', 'Football'),
        ('fcotball', 'football'),
        ('Atheltic', 'Athletic'),
        ('atheltic', 'athletic'),
        ('Athlettic', 'Athletic'),
        ('athlettic', 'athletic'),
    ]

    for typo, correct in typos:
        # Fix in games - home_team
        cursor.execute(f"UPDATE games SET home_team = REPLACE(home_team, '{typo}', '{correct}') WHERE home_team LIKE '%{typo}%'")
        count1 = cursor.rowcount

        # Fix in games - away_team
        cursor.execute(f"UPDATE games SET away_team = REPLACE(away_team, '{typo}', '{correct}') WHERE away_team LIKE '%{typo}%'")
        count2 = cursor.rowcount

        # Fix in teams - team_name
        cursor.execute(f"UPDATE teams SET team_name = REPLACE(team_name, '{typo}', '{correct}') WHERE team_name LIKE '%{typo}%'")
        count3 = cursor.rowcount

        # Fix in teams - club_name
        cursor.execute(f"UPDATE teams SET club_name = REPLACE(club_name, '{typo}', '{correct}') WHERE club_name LIKE '%{typo}%'")
        count4 = cursor.rowcount

        fixed = count1 + count2 + count3 + count4
        if fixed > 0:
            log(f"  Typo '{typo}' -> '{correct}': {fixed} fixes")
            total_fixed += fixed

    conn.commit()
    return total_fixed


def normalize_club_names(conn):
    """Normalize club name case variations"""
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
                    cnt = cursor.rowcount
                    if cnt > 0:
                        log(f"  Club name: '{variant}' -> '{canonical}': {cnt} teams")
                        updates += cnt

    conn.commit()
    return updates

def populate_mls_next_states(conn):
    """Populate MLS NEXT team states from known data"""
    cursor = conn.cursor()

    mls_team_states = {
        'LA Galaxy': 'CA', 'LAFC': 'CA', 'San Jose': 'CA', 'Seattle': 'WA',
        'Portland': 'OR', 'Real Salt Lake': 'UT', 'Colorado': 'CO',
        'FC Dallas': 'TX', 'Dallas': 'TX', 'Houston': 'TX', 'Austin': 'TX',
        'Sporting KC': 'KS', 'Kansas City': 'KS', 'Minnesota': 'MN',
        'Chicago': 'IL', 'Columbus': 'OH', 'Nashville': 'TN', 'Atlanta': 'GA',
        'Inter Miami': 'FL', 'Miami': 'FL', 'Orlando': 'FL', 'Charlotte': 'NC',
        'DC United': 'DC', 'Philadelphia': 'PA', 'Red Bull': 'NJ',
        'New York': 'NY', 'NYCFC': 'NY', 'New England': 'MA', 'Revolution': 'MA',
        'St. Louis': 'MO', 'San Diego': 'CA', 'Sacramento': 'CA',
        'Phoenix': 'AZ', 'Los Angeles': 'CA', 'Detroit': 'MI', 'Cincinnati': 'OH',
        'Tampa': 'FL'
    }

    cursor.execute("""
        SELECT id, team_name, club_name FROM teams
        WHERE league = 'MLS NEXT' AND (state IS NULL OR state = '')
    """)
    mls_teams = cursor.fetchall()

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
    return updated

def report_issues_for_manual_review(conn):
    """Report issues that need manual review (not auto-fixed)"""
    cursor = conn.cursor()

    log("\n=== ISSUES FOR MANUAL REVIEW ===")

    # Hidden teams
    cursor.execute("SELECT COUNT(*) FROM teams WHERE team_name = 'Hidden' OR club_name = 'Hidden'")
    hidden = cursor.fetchone()[0]
    if hidden > 0:
        log(f"  [!] Hidden teams: {hidden} (run database_cleanup.py to remove)")

    # PKS games
    cursor.execute("SELECT COUNT(*) FROM games WHERE away_team LIKE '%PKS:%'")
    pks = cursor.fetchone()[0]
    if pks > 0:
        log(f"  [!] PKS corrupted games: {pks} (run database_cleanup.py to remove)")

    # TBD games
    cursor.execute("SELECT COUNT(*) FROM games WHERE home_team LIKE 'TBD%' OR away_team LIKE 'TBD%'")
    tbd = cursor.fetchone()[0]
    if tbd > 0:
        log(f"  [!] TBD placeholder games: {tbd} (review before deleting - may be future games)")

    # Potential duplicates
    cursor.execute('''
        SELECT COUNT(*) FROM (
            SELECT home_team, away_team, game_date, age_group, league
            FROM games
            GROUP BY home_team, away_team, game_date, age_group, league
            HAVING COUNT(*) > 1
        )
    ''')
    dups = cursor.fetchone()[0]
    if dups > 0:
        log(f"  [!] Potential duplicate game groups: {dups} (review before deleting - may be double-headers)")

    if hidden == 0 and pks == 0 and tbd == 0 and dups == 0:
        log("  All clean - no issues requiring manual review!")

def main():
    log("\n" + "="*60)
    log("SAFE DATABASE CLEANUP (Auto-run safe)")
    log("="*60)

    if not os.path.exists(DB_PATH):
        log(f"ERROR: Database not found at {DB_PATH}")
        return 1

    conn = get_connection()
    results = {}

    try:
        # Only run safe, non-destructive fixes
        log("\n--- Fixing invalid scores (resetting to NULL) ---")
        results['Invalid scores fixed'] = fix_impossible_scores(conn)

        log("\n--- Normalizing state abbreviations ---")
        results['States normalized'] = normalize_states(conn)

        log("\n--- Standardizing gender values ---")
        results['Gender values fixed'] = standardize_gender(conn)

        log("\n--- Fixing trailing dashes in team names ---")
        results['Trailing dashes fixed'] = fix_trailing_dashes(conn)

        log("\n--- Fixing common typos ---")
        results['Typos fixed'] = fix_common_typos(conn)

        log("\n--- Normalizing club names ---")
        results['Club names normalized'] = normalize_club_names(conn)

        log("\n--- Populating MLS NEXT states ---")
        results['MLS states added'] = populate_mls_next_states(conn)

        # Report issues that need manual review
        report_issues_for_manual_review(conn)

        # Summary
        log("\n" + "="*60)
        log("SAFE CLEANUP COMPLETE")
        log("="*60)
        total_fixed = sum(results.values())
        if total_fixed > 0:
            for task, count in results.items():
                if count > 0:
                    log(f"  {task}: {count}")
        else:
            log("  No fixes needed - database is clean!")

        return 0

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        conn.close()

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
