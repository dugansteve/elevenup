"""Simple age group fix script - runs the fixes directly."""
import sqlite3
import re

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

def extract_birth_year(team_name):
    if not team_name:
        return None
    team_upper = team_name.upper()
    # Skip dates
    if re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d', team_upper):
        return None
    # 4-digit year
    match = re.search(r'\b(200[6-9]|201[0-9])\b', team_upper)
    if match:
        return match.group(1)[-2:]
    # G09, B13
    match = re.search(r'\b[GB](0[6-9]|1[0-9])\b', team_upper)
    if match:
        return match.group(1)
    # 09G, 13B
    match = re.search(r'\b(0[6-9]|1[0-9])[GB]\b', team_upper)
    if match:
        return match.group(1)
    return None

def extract_gender(team_name, existing_gender):
    if not team_name:
        return None
    team_upper = team_name.upper()
    match = re.search(r'\b([GB])(0[6-9]|1[0-9])\b', team_upper)
    if match:
        return match.group(1)
    match = re.search(r'\b(0[6-9]|1[0-9])([GB])\b', team_upper)
    if match:
        return match.group(2)
    if 'GIRLS' in team_upper or 'GIRL' in team_upper:
        return 'G'
    if 'BOYS' in team_upper or 'BOY' in team_upper:
        return 'B'
    if existing_gender:
        if existing_gender.lower() in ('girls', 'female', 'g'):
            return 'G'
        if existing_gender.lower() in ('boys', 'male', 'b'):
            return 'B'
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Fetching games...")
    cur.execute("SELECT game_id, home_team, away_team, age_group, gender FROM games")
    games = cur.fetchall()
    print(f"Processing {len(games)} games...")

    updates = []
    for game_id, home, away, ag, gender in games:
        home_year = extract_birth_year(home)
        away_year = extract_birth_year(away)
        name_year = home_year or away_year
        if not name_year:
            continue

        ag_year = None
        if ag:
            m = re.search(r'[GB]?(0[6-9]|1[0-9])', ag)
            if m:
                ag_year = m.group(1)

        if ag_year == name_year:
            continue

        home_gender = extract_gender(home, gender)
        away_gender = extract_gender(away, gender)
        game_gender = home_gender or away_gender

        if game_gender:
            new_ag = f"{game_gender}{name_year}"
            updates.append((new_ag, game_id))

    print(f"Applying {len(updates)} updates...")
    cur.executemany("UPDATE games SET age_group = ? WHERE game_id = ?", updates)
    conn.commit()
    print(f"Done! Updated {len(updates)} games.")

    # Fix gender mismatches
    print("Fixing gender mismatches...")
    cur.execute("UPDATE games SET gender = 'Girls' WHERE age_group LIKE 'G%' AND gender = 'Boys'")
    g_fixed = cur.rowcount
    cur.execute("UPDATE games SET gender = 'Boys' WHERE age_group LIKE 'B%' AND gender = 'Girls'")
    b_fixed = cur.rowcount
    conn.commit()
    print(f"Fixed gender: {g_fixed} to Girls, {b_fixed} to Boys")

    conn.close()
    print("\nAll done! Now run the team ranker to regenerate rankings.")

if __name__ == '__main__':
    main()
