"""Fix remaining age group mismatches."""
import sqlite3
import re

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

def extract_birth_year_enhanced(team_name):
    """Enhanced extraction that handles more patterns."""
    if not team_name:
        return None, None

    team_upper = team_name.upper()

    # Skip dates
    if re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d', team_upper):
        return None, None

    # Pattern: 4-digit year with gender suffix (2009B, 2009G)
    match = re.search(r'\b(200[6-9]|201[0-9])([GB])\b', team_upper)
    if match:
        return match.group(1)[-2:], match.group(2)

    # Pattern: 4-digit year followed by gender word
    match = re.search(r'\b(200[6-9]|201[0-9])\s*(GIRLS?|BOYS?)\b', team_upper)
    if match:
        gender = 'G' if 'GIRL' in match.group(2) else 'B'
        return match.group(1)[-2:], gender

    # Pattern: 4-digit year standalone
    match = re.search(r'\b(200[6-9]|201[0-9])\b', team_upper)
    if match:
        # Try to get gender from elsewhere in name
        year = match.group(1)[-2:]
        if 'GIRLS' in team_upper or 'GIRL' in team_upper:
            return year, 'G'
        if 'BOYS' in team_upper or 'BOY' in team_upper:
            return year, 'B'
        return year, None

    # Pattern: G09, B13 prefix
    match = re.search(r'\b([GB])(0[6-9]|1[0-9])\b', team_upper)
    if match:
        return match.group(2), match.group(1)

    # Pattern: 09G, 13B suffix
    match = re.search(r'\b(0[6-9]|1[0-9])([GB])\b', team_upper)
    if match:
        return match.group(1), match.group(2)

    return None, None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Fetching all games...")
    cur.execute("SELECT game_id, home_team, away_team, age_group, gender FROM games")
    games = cur.fetchall()
    print(f"Total games: {len(games)}")

    updates = []
    for game_id, home, away, ag, gender in games:
        # Extract from home team
        home_year, home_gender = extract_birth_year_enhanced(home)
        # Extract from away team
        away_year, away_gender = extract_birth_year_enhanced(away)

        # Use the first valid extraction
        name_year = home_year or away_year
        name_gender = home_gender or away_gender

        if not name_year:
            continue

        # Determine final gender
        if name_gender:
            final_gender = name_gender
        elif gender:
            if gender.lower() in ('girls', 'female'):
                final_gender = 'G'
            elif gender.lower() in ('boys', 'male'):
                final_gender = 'B'
            else:
                continue
        else:
            continue

        # Build correct age_group
        correct_ag = f"{final_gender}{name_year}"

        # Check if current age_group year matches
        ag_match = re.search(r'[GB]?(0[6-9]|1[0-9])', ag or '')
        current_year = ag_match.group(1) if ag_match else None

        if current_year != name_year:
            updates.append((correct_ag, final_gender, game_id))

    print(f"\nApplying {len(updates)} updates...")

    # Update age_group and fix gender at the same time
    for correct_ag, final_gender, game_id in updates:
        gender_str = 'Girls' if final_gender == 'G' else 'Boys'
        cur.execute("""
            UPDATE games
            SET age_group = ?, gender = ?
            WHERE game_id = ?
        """, (correct_ag, gender_str, game_id))

    conn.commit()
    print(f"Done! Updated {len(updates)} games.")

    # Verify
    print("\nVerifying remaining mismatches...")
    cur.execute("""
        SELECT COUNT(*) FROM games
        WHERE (home_team LIKE '%2009%' AND age_group NOT LIKE '%09%')
    """)
    print(f"  2009 teams with wrong age_group: {cur.fetchone()[0]}")

    conn.close()

if __name__ == '__main__':
    main()
