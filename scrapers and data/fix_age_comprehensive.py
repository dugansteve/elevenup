#!/usr/bin/env python3
"""
Comprehensive age group fixer - handles all remaining edge cases:
1. Tournament name gender detection (e.g., "Boys Invitational")
2. Bare numbers (12, 11) -> detect gender from division/team names -> B12, G11
3. Extract age from team names for missing age groups
4. U-age formats (U11 Boys) -> B14 (birth year)
5. Complex division strings -> extract birth year
"""

import sqlite3
import re

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
CURRENT_YEAR = 2025


def detect_tournament_gender(tournament_name):
    """Detect if tournament is gender-specific from name"""
    if not tournament_name:
        return None
    name = tournament_name.lower()
    # Only if explicitly one gender, not both
    if re.search(r'\bboys?\b', name) and not re.search(r'\bgirls?\b', name):
        return 'B'
    if re.search(r'\bgirls?\b', name) and not re.search(r'\bboys?\b', name):
        return 'G'
    return None


def detect_gender(division, home_team, away_team, tournament_name=None):
    """Detect gender from division, team names, or tournament"""
    text = f"{division or ''} {home_team or ''} {away_team or ''}".lower()

    if re.search(r'\b(girl|female|women)', text):
        return 'G'
    if re.search(r'\b(boy|male|men)', text):
        return 'B'

    # Check for B2011/G2012 patterns in team names
    full_text = f"{home_team or ''} {away_team or ''}"
    if re.search(r'\bG20\d{2}\b', full_text):
        return 'G'
    if re.search(r'\bB20\d{2}\b', full_text):
        return 'B'
    if re.search(r'\b20\d{2}G\b', full_text):
        return 'G'
    if re.search(r'\b20\d{2}B\b', full_text):
        return 'B'

    # Fall back to tournament name
    if tournament_name:
        return detect_tournament_gender(tournament_name)

    return None


def extract_birth_year_from_text(text):
    """Extract birth year from text (2011, 2012, etc.)"""
    if not text:
        return None

    match = re.search(r'\b20(0[6-9]|1[0-9])\b', text)
    if match:
        return match.group(1)  # Return "11" for 2011
    return None


def fix_age_group(age_group, division, home_team, away_team):
    """Fix age group to proper BXX/GXX format"""
    if not age_group:
        return None

    age_group = age_group.strip()

    # Already correct format (B06-B19, G06-G19)
    if re.match(r'^[BG](0[6-9]|1[0-9])$', age_group):
        return age_group

    # Single/double digit (12, 11, 9, etc.) - needs gender
    match = re.match(r'^(\d{1,2})$', age_group)
    if match:
        num = match.group(1).zfill(2)  # Pad to 2 digits
        # If it's 06-19, it's likely a birth year suffix
        if 6 <= int(num) <= 19:
            gender = detect_gender(division, home_team, away_team)
            if gender:
                return f"{gender}{num}"
            return num  # Return padded number without gender
        return None

    # B7/G7 format -> B07/G07
    match = re.match(r'^([BG])(\d)$', age_group)
    if match:
        gender = match.group(1)
        num = match.group(2).zfill(2)
        return f"{gender}{num}"

    # U-age with gender (U11 Boys, U13 Girls, etc.)
    match = re.search(r'U(\d{1,2})\s*(Boy|Girl|Male|Female)?', age_group, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        gender_word = match.group(2)

        if 8 <= age <= 19:
            birth_year = CURRENT_YEAR - age
            suffix = str(birth_year)[-2:]

            if gender_word:
                gender = 'B' if gender_word.lower() in ['boy', 'boys', 'male'] else 'G'
            else:
                gender = detect_gender(division, home_team, away_team)

            if gender:
                return f"{gender}{suffix}"
            return suffix

    # "Under XX" patterns
    match = re.search(r'Under\s*(\d{1,2})', age_group, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 8 <= age <= 19:
            birth_year = CURRENT_YEAR - age
            suffix = str(birth_year)[-2:]
            gender = detect_gender(age_group + ' ' + (division or ''), home_team, away_team)
            if gender:
                return f"{gender}{suffix}"
            return suffix

    # Birth year in age_group (2011, 2012 patterns)
    birth_suffix = extract_birth_year_from_text(age_group)
    if birth_suffix:
        gender = detect_gender(age_group + ' ' + (division or ''), home_team, away_team)
        if gender:
            return f"{gender}{birth_suffix}"
        return birth_suffix

    # Check division for birth year
    birth_suffix = extract_birth_year_from_text(division)
    if birth_suffix:
        gender = detect_gender(age_group + ' ' + (division or ''), home_team, away_team)
        if gender:
            return f"{gender}{birth_suffix}"
        return birth_suffix

    return None  # Can't fix


def extract_from_team_name(team_name):
    """Extract birth year and gender from team name"""
    if not team_name:
        return None, None

    # Pattern: B2011, G2012
    match = re.search(r'\b([BG])20(0[6-9]|1[0-9])\b', team_name)
    if match:
        return match.group(2), match.group(1)

    # Pattern: 2011B, 2012G
    match = re.search(r'\b20(0[6-9]|1[0-9])([BG])\b', team_name)
    if match:
        return match.group(1), match.group(2)

    # Pattern: 2011 Boys, 2012 Girls
    match = re.search(r'\b20(0[6-9]|1[0-9])\s*(Boys?|Girls?)\b', team_name, re.IGNORECASE)
    if match:
        gender = 'B' if 'boy' in match.group(2).lower() else 'G'
        return match.group(1), gender

    # Just birth year: 2011, 2012
    match = re.search(r'\b20(0[6-9]|1[0-9])\b', team_name)
    if match:
        return match.group(1), None

    # U-age pattern
    match = re.search(r'\bU(\d{1,2})\b', team_name, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 8 <= age <= 19:
            birth_suffix = str(CURRENT_YEAR - age)[-2:]
            return birth_suffix, None

    # Age suffix like 'CFC 17', 'FPFC 09'
    match = re.search(r'\s(0[6-9]|1[0-9])\s*$', team_name)
    if match:
        return match.group(1), None

    return None, None


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 70)
    print("STEP 1: Fix bare birth years using tournament gender")
    print("=" * 70)

    # Get tournaments with bare birth year games
    tournaments = cursor.execute('''
        SELECT DISTINCT tournament_name
        FROM tournament_games
        WHERE age_group IN ('12', '11', '10', '13', '15', '14', '06', '16', '17', '08', '09', '07')
    ''').fetchall()

    step1_fixed = 0
    for (tournament_name,) in tournaments:
        gender = detect_tournament_gender(tournament_name)
        if gender:
            cursor.execute('''
                UPDATE tournament_games
                SET age_group = ? || age_group
                WHERE tournament_name = ?
                AND age_group IN ('12', '11', '10', '13', '15', '14', '06', '16', '17', '08', '09', '07')
                AND length(age_group) = 2
            ''', (gender, tournament_name))
            if cursor.rowcount > 0:
                print(f"  {gender} + {cursor.rowcount:3} games: {tournament_name[:50]}")
                step1_fixed += cursor.rowcount

    conn.commit()
    print(f"\nStep 1 fixed: {step1_fixed} games")

    print("\n" + "=" * 70)
    print("STEP 2: Fix missing age groups from team names")
    print("=" * 70)

    games = cursor.execute('''
        SELECT id, home_team, away_team, tournament_name
        FROM tournament_games
        WHERE age_group IS NULL OR age_group = ''
    ''').fetchall()

    print(f"Checking {len(games)} games with missing age groups...")

    step2_fixed = 0
    samples = []

    for game_id, home_team, away_team, tournament_name in games:
        birth_suffix, gender = extract_from_team_name(home_team)
        if not birth_suffix:
            birth_suffix, gender = extract_from_team_name(away_team)

        if birth_suffix and not gender:
            gender = detect_tournament_gender(tournament_name)

        if birth_suffix:
            new_ag = f"{gender}{birth_suffix}" if gender else birth_suffix
            cursor.execute('UPDATE tournament_games SET age_group = ? WHERE id = ?',
                          (new_ag, game_id))
            step2_fixed += 1
            if len(samples) < 8:
                samples.append((home_team[:30] if home_team else '', new_ag))

    conn.commit()
    print(f"Step 2 fixed: {step2_fixed} games")
    if samples:
        print("\nSamples:")
        for team, ag in samples:
            print(f"  {team:30} -> {ag}")

    print("\n" + "=" * 70)
    print("STEP 3: Fix remaining bare birth years from team names")
    print("=" * 70)

    games = cursor.execute('''
        SELECT id, age_group, home_team, away_team
        FROM tournament_games
        WHERE age_group IN ('12', '11', '10', '13', '15', '14', '06', '16', '17', '08', '09', '07')
    ''').fetchall()

    print(f"Checking {len(games)} remaining bare birth years...")
    step3_fixed = 0

    for game_id, age_group, home_team, away_team in games:
        _, gender = extract_from_team_name(home_team)
        if not gender:
            _, gender = extract_from_team_name(away_team)
        if gender:
            new_ag = f"{gender}{age_group.zfill(2)}"
            cursor.execute('UPDATE tournament_games SET age_group = ? WHERE id = ?',
                          (new_ag, game_id))
            step3_fixed += 1

    conn.commit()
    print(f"Step 3 fixed: {step3_fixed} games")

    # Final stats
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    total = cursor.execute('SELECT COUNT(*) FROM tournament_games').fetchone()[0]
    with_age = cursor.execute("SELECT COUNT(*) FROM tournament_games WHERE age_group IS NOT NULL AND age_group <> ''").fetchone()[0]
    correct = cursor.execute('''
        SELECT COUNT(*) FROM tournament_games
        WHERE (age_group LIKE 'B0_' OR age_group LIKE 'B1_' OR
               age_group LIKE 'G0_' OR age_group LIKE 'G1_')
        AND length(age_group) = 3
    ''').fetchone()[0]
    bare = cursor.execute('''
        SELECT COUNT(*) FROM tournament_games
        WHERE age_group IN ('12', '11', '10', '13', '15', '14', '06', '16', '17', '08', '09', '07')
    ''').fetchone()[0]

    print(f"Total games: {total}")
    print(f"Correct format (BXX/GXX): {correct} ({100*correct/total:.1f}%)")
    print(f"Bare birth year: {bare} ({100*bare/total:.1f}%)")
    print(f"Missing age group: {total - with_age} ({100*(total-with_age)/total:.1f}%)")
    print(f"\nTotal fixed this run: {step1_fixed + step2_fixed + step3_fixed}")

    print("\n" + "-" * 70)
    print("Tournaments still needing re-scrape (most missing age groups):")
    for row in cursor.execute('''
        SELECT tournament_name, tournament_id, COUNT(*) as cnt
        FROM tournament_games
        WHERE age_group IS NULL OR age_group = ''
        GROUP BY tournament_name, tournament_id
        ORDER BY cnt DESC
        LIMIT 10
    ''').fetchall():
        print(f"  {row[2]:4} games - ID {row[1]}: {row[0][:45]}")

    conn.close()


if __name__ == "__main__":
    main()
