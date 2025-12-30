"""
Fix Age Groups in Database
==========================
This script fixes age_group values in the games table by extracting birth year
from team names and converting to proper format (G09, B13, etc.)

The standard format is BIRTH YEAR based:
- G09 = Girls born in 2009
- B13 = Boys born in 2013
- Lamorinda 13G = players born in 2013 = G13

This script finds teams where the birth year in the team name doesn't match
the age_group field and fixes them.

Run with --dry-run first to see what would be changed.
"""

import sqlite3
import re
import argparse
from collections import defaultdict

# Path to database
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

def extract_birth_year_from_name(team_name):
    """
    Extract birth year from team name.
    Returns 2-digit year string (e.g., "09", "13") or None if not found.

    Examples:
    - "Chicago Fire 2009" -> "09"
    - "Chicago Fire 09" -> "09"
    - "Chicago Fire G09" -> "09"
    - "Chicago Fire 09G" -> "09"
    - "Lamorinda 13G" -> "13"
    - "Mustang B09" -> "09"
    - "So Cal Blues G2019 Lime" -> "19"
    """
    if not team_name:
        return None

    team_upper = team_name.upper()

    # Skip if this looks like a date or game ID
    if re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d', team_upper):
        return None
    if re.search(r'#\d{5,}', team_upper):
        return None

    # Pattern 1: 4-digit year (2006-2019 are valid birth years for youth soccer)
    match = re.search(r'\b(200[6-9]|201[0-9])\b', team_upper)
    if match:
        return match.group(1)[-2:]  # Return last 2 digits

    # Pattern 2: 2-digit with gender prefix (G09, B13)
    match = re.search(r'\b[GB](0[6-9]|1[0-9])\b', team_upper)
    if match:
        return match.group(1)

    # Pattern 3: 2-digit with gender suffix (09G, 13B)
    match = re.search(r'\b(0[6-9]|1[0-9])[GB]\b', team_upper)
    if match:
        return match.group(1)

    # Pattern 4: Standalone 2-digit that looks like a birth year (with word boundaries)
    # Be more conservative here - must have space/separator before and after
    match = re.search(r'[\s\-_](0[6-9]|1[0-9])[\s\-_\)$]', team_upper + ' ')
    if match:
        return match.group(1)

    return None


def extract_gender_from_name(team_name, existing_gender=None):
    """
    Extract gender from team name or use existing.
    Returns 'G' or 'B' or None.
    """
    if not team_name:
        return None

    team_upper = team_name.upper()

    # Look for explicit gender markers
    if re.search(r'\b[GB](0[6-9]|1[0-9])\b', team_upper):
        match = re.search(r'\b([GB])(0[6-9]|1[0-9])\b', team_upper)
        return match.group(1)

    if re.search(r'\b(0[6-9]|1[0-9])([GB])\b', team_upper):
        match = re.search(r'\b(0[6-9]|1[0-9])([GB])\b', team_upper)
        return match.group(2)

    if re.search(r'\b200[6-9]([GB])\b|\b201[0-9]([GB])\b', team_upper):
        match = re.search(r'\b20[01][0-9]([GB])\b', team_upper)
        return match.group(1)

    # Look for gender words
    if re.search(r'\bGIRLS?\b', team_upper):
        return 'G'
    if re.search(r'\bBOYS?\b', team_upper):
        return 'B'

    # Use existing gender field
    if existing_gender:
        if existing_gender.lower() in ('girls', 'female', 'g'):
            return 'G'
        if existing_gender.lower() in ('boys', 'male', 'b'):
            return 'B'

    return None


def get_birth_year_from_age_group(age_group):
    """
    Extract the 2-digit year from an age_group field.
    Returns the year string or None.

    Examples:
    - "G09" -> "09"
    - "B13" -> "13"
    - "G08/07" -> "08"
    """
    if not age_group:
        return None

    match = re.search(r'[GB]?(0[6-9]|1[0-9])', age_group)
    if match:
        return match.group(1)
    return None


def analyze_database(conn):
    """Analyze current state of age_group data in database."""
    cur = conn.cursor()

    print("\n" + "="*70)
    print("CURRENT DATABASE STATE ANALYSIS")
    print("="*70)

    # Count by age_group
    cur.execute("""
        SELECT age_group, COUNT(*) as cnt
        FROM games
        GROUP BY age_group
        ORDER BY cnt DESC
        LIMIT 30
    """)
    print("\nTop 30 age_group values:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} games")

    # Count mismatches (e.g., Boys teams with G prefix)
    cur.execute("""
        SELECT age_group, gender, COUNT(*) as cnt
        FROM games
        WHERE (gender = 'Boys' AND age_group LIKE 'G%')
           OR (gender = 'Girls' AND age_group LIKE 'B%')
        GROUP BY age_group, gender
        ORDER BY cnt DESC
        LIMIT 20
    """)
    results = cur.fetchall()
    if results:
        print("\nGender/age_group MISMATCHES (Boys with G prefix or Girls with B prefix):")
        for row in results:
            print(f"  {row[0]} + {row[1]}: {row[2]} games")

    # Find teams where birth year in name doesn't match age_group
    print("\n" + "-"*70)
    print("SAMPLING: Teams where name's birth year != age_group's year")
    print("-"*70)

    cur.execute("""
        SELECT DISTINCT home_team, age_group, gender, league
        FROM games
        WHERE home_team LIKE '%200%' OR home_team LIKE '%201%'
        LIMIT 500
    """)

    mismatches = []
    for team_name, age_group, gender, league in cur.fetchall():
        name_year = extract_birth_year_from_name(team_name)
        ag_year = get_birth_year_from_age_group(age_group)

        if name_year and ag_year and name_year != ag_year:
            mismatches.append((team_name, age_group, gender, league, name_year, ag_year))

    print(f"\nFound {len(mismatches)} teams with year mismatch in sample:")
    for team_name, age_group, gender, league, name_year, ag_year in mismatches[:25]:
        print(f"  Name says '{name_year}', age_group says '{ag_year}': {team_name[:55]} ({league})")


def fix_age_groups(conn, dry_run=True):
    """Fix age_group values based on team names."""
    cur = conn.cursor()

    print("\n" + "="*70)
    print("FIXING AGE GROUPS" + (" (DRY RUN)" if dry_run else " (APPLYING CHANGES)"))
    print("="*70)

    # Get all distinct games with team info
    cur.execute("""
        SELECT DISTINCT home_team, away_team, age_group, gender, league, game_id
        FROM games
    """)

    all_games = cur.fetchall()
    print(f"\nAnalyzing {len(all_games)} games...")

    # Track fixes needed
    fixes_needed = []  # (game_id, old_age_group, new_age_group, team_name, reason)
    stats = defaultdict(int)

    for home_team, away_team, age_group, gender, league, game_id in all_games:
        # Try to extract birth year from either team name
        home_year = extract_birth_year_from_name(home_team)
        away_year = extract_birth_year_from_name(away_team)

        # Get birth year from age_group
        ag_year = get_birth_year_from_age_group(age_group)

        # Determine gender
        home_gender = extract_gender_from_name(home_team, gender)
        away_gender = extract_gender_from_name(away_team, gender)
        game_gender = home_gender or away_gender

        # Check if there's a mismatch that needs fixing
        name_year = home_year or away_year
        team_for_display = home_team if home_year else away_team

        if not name_year:
            stats['no_year_in_name'] += 1
            continue

        if not ag_year:
            stats['no_year_in_age_group'] += 1
            # Age group is missing or invalid - we can fix this
            if game_gender:
                new_age_group = f"{game_gender}{name_year}"
                fixes_needed.append((game_id, age_group, new_age_group, team_for_display, "missing/invalid age_group"))
                stats['needs_fix'] += 1
            continue

        if name_year == ag_year:
            stats['already_correct'] += 1
            continue

        # Years don't match - this needs fixing
        if game_gender:
            new_age_group = f"{game_gender}{name_year}"
            fixes_needed.append((game_id, age_group, new_age_group, team_for_display, f"year mismatch ({ag_year} vs {name_year})"))
            stats['needs_fix'] += 1
        else:
            stats['no_gender'] += 1

    print(f"\nStats:")
    print(f"  Already correct: {stats['already_correct']}")
    print(f"  Needs fix: {stats['needs_fix']}")
    print(f"  No year in team name: {stats['no_year_in_name']}")
    print(f"  No/invalid year in age_group: {stats['no_year_in_age_group']}")
    print(f"  No gender available: {stats['no_gender']}")

    if not fixes_needed:
        print("\nNo fixes needed!")
        return

    # Group fixes by transformation
    fix_groups = defaultdict(list)
    for game_id, old_ag, new_ag, team, reason in fixes_needed:
        fix_groups[(old_ag, new_ag)].append((game_id, team, reason))

    print(f"\nTransformations needed ({len(fix_groups)} unique):")
    shown = 0
    for (old_ag, new_ag), items in sorted(fix_groups.items(), key=lambda x: -len(x[1])):
        if shown >= 40:
            print(f"  ... and {len(fix_groups) - shown} more transformation types")
            break
        print(f"  {old_ag or 'NULL/EMPTY'} -> {new_ag}: {len(items)} games")
        # Show example
        print(f"      e.g., {items[0][1][:55]}")
        shown += 1

    if dry_run:
        print("\n" + "="*70)
        print("[DRY RUN] No changes made. Run with --apply to apply fixes.")
        print("="*70)
        return

    # Apply fixes
    print("\nApplying fixes...")
    total_updated = 0

    for game_id, old_ag, new_ag, team, reason in fixes_needed:
        cur.execute("""
            UPDATE games
            SET age_group = ?
            WHERE game_id = ?
        """, (new_ag, game_id))
        total_updated += cur.rowcount

    conn.commit()
    print(f"\nUpdated {total_updated} game records.")


def fix_gender_mismatches(conn, dry_run=True):
    """Fix games where gender field doesn't match age_group prefix."""
    cur = conn.cursor()

    print("\n" + "="*70)
    print("FIXING GENDER FIELD MISMATCHES" + (" (DRY RUN)" if dry_run else " (APPLYING CHANGES)"))
    print("="*70)

    # Count mismatches
    cur.execute("""
        SELECT age_group, gender, COUNT(*) as cnt
        FROM games
        WHERE (age_group LIKE 'G%' AND gender = 'Boys')
           OR (age_group LIKE 'B%' AND gender = 'Girls')
        GROUP BY age_group, gender
    """)

    mismatches = cur.fetchall()
    total = sum(row[2] for row in mismatches)

    print(f"\nFound {total} games with gender/age_group mismatch:")
    for ag, gender, cnt in mismatches[:15]:
        print(f"  {ag} with gender='{gender}': {cnt} games")

    if total == 0:
        return

    if dry_run:
        print("\n[DRY RUN] Would fix these. Run with --apply to apply fixes.")
        return

    # Fix: Update gender to match age_group prefix
    cur.execute("""
        UPDATE games SET gender = 'Girls'
        WHERE age_group LIKE 'G%' AND gender = 'Boys'
    """)
    girls_fixed = cur.rowcount

    cur.execute("""
        UPDATE games SET gender = 'Boys'
        WHERE age_group LIKE 'B%' AND gender = 'Girls'
    """)
    boys_fixed = cur.rowcount

    conn.commit()
    print(f"\nFixed {girls_fixed} games to Girls, {boys_fixed} games to Boys")


def main():
    parser = argparse.ArgumentParser(description='Fix age_group values in database')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be changed without making changes (default)')
    parser.add_argument('--apply', action='store_true',
                        help='Actually apply the fixes')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only show analysis, do not suggest fixes')
    args = parser.parse_args()

    dry_run = not args.apply

    print("="*70)
    print("AGE GROUP FIX SCRIPT")
    print("="*70)
    print(f"Database: {DB_PATH}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLYING CHANGES'}")

    conn = sqlite3.connect(DB_PATH)

    try:
        # Always show analysis
        analyze_database(conn)

        if args.analyze_only:
            return

        # Fix age groups
        fix_age_groups(conn, dry_run=dry_run)

        # Fix gender mismatches (after age groups are fixed)
        fix_gender_mismatches(conn, dry_run=dry_run)

        if not dry_run:
            print("\n" + "="*70)
            print("FIXES APPLIED SUCCESSFULLY")
            print("="*70)
            print("\nNext steps:")
            print("1. Re-run the team ranker to regenerate rankings_for_react.json")
            print("2. Copy the new JSON to the React app's public folder")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
