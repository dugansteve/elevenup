#!/usr/bin/env python3
"""
================================================================================
FIX AGE GROUPS FROM BIRTH YEAR - Correct age_group based on birth year in name
================================================================================

Fixes age_group field where teams have 4-digit birth years in their names
but the age_group doesn't match the birth year.

Convention: Age group uses birth year suffix (NOT calculated age)
  - Birth year 2011 -> G11 or B11 (not G14 which would be calculated age)
  - Birth year 2012 -> G12 or B12
  - Birth year 2007 -> G07 or B07

Examples:
  - "San Diego FORCE FC 2011 Girls Academy" with G14 -> G11
  - "Strikers FC Irvine 2017 Ayala" with B08 -> B17
  - "Gateway Rush 2012 Girls United" with G13 -> G12

Usage:
    python fix_age_groups_from_birth_year.py              # Dry run (analyze only)
    python fix_age_groups_from_birth_year.py --apply      # Apply fixes
    python fix_age_groups_from_birth_year.py --db path    # Custom database path

================================================================================
"""

import sqlite3
import re
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()

def find_database():
    """Find the seedlinedata.db file"""
    candidates = [
        SCRIPT_DIR / "seedlinedata.db",
        SCRIPT_DIR.parent / "scrapers and data" / "seedlinedata.db",
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None

# ============================================================================
# AGE EXTRACTION FUNCTIONS
# ============================================================================

def extract_birth_year_suffix(name):
    """
    Extract 2-digit birth year suffix from team name.
    Handles multiple patterns:
      - "Team 2011 Girls" -> "11"
      - "Team B2011" -> "11"
      - "Team G2010" -> "10"
    """
    if not name:
        return None

    # Pattern 1: Standalone 4-digit year (2005-2020)
    match = re.search(r'\b20([0-1][0-9]|20)\b', name)
    if match:
        return match.group(1)

    # Pattern 2: B/G prefix attached to year (B2011, G2010)
    match = re.search(r'[BG](20[0-1][0-9])', name)
    if match:
        return match.group(1)[2:]  # Return last 2 digits

    return None


def extract_age_number(age_group):
    """Extract number string from age_group field like G14, B11 -> "14", "11" """
    if not age_group:
        return None
    match = re.search(r'[GBU]?(\d+)', str(age_group))
    if match:
        return match.group(1)
    return None


def get_gender_prefix(age_group, gender):
    """Determine gender prefix (G, B, or U)"""
    if age_group and len(age_group) > 0 and age_group[0] in ['G', 'B', 'U']:
        return age_group[0]
    if gender == 'Girls':
        return 'G'
    elif gender == 'Boys':
        return 'B'
    return 'U'


# ============================================================================
# ANALYSIS
# ============================================================================

def analyze_age_mismatches(conn):
    """Find all teams with birth year vs age_group mismatches"""
    cursor = conn.cursor()

    cursor.execute('SELECT id, club_name, team_name, age_group, gender, league FROM teams')
    teams = cursor.fetchall()

    mismatches = []

    for team_id, club_name, team_name, age_group, gender, league in teams:
        # Only process teams with 4-digit birth years in their names
        birth_suffix = extract_birth_year_suffix(team_name)
        if not birth_suffix:
            continue

        # Get current age number from age_group
        current_age_num = extract_age_number(age_group)
        if current_age_num is None:
            continue

        # Check if birth year suffix matches age group number
        if birth_suffix != current_age_num:
            prefix = get_gender_prefix(age_group, gender)
            correct_age_group = f'{prefix}{birth_suffix}'

            mismatches.append({
                'id': team_id,
                'team_name': team_name,
                'club_name': club_name,
                'birth_year': f'20{birth_suffix}',
                'current_age_group': age_group,
                'correct_age_group': correct_age_group,
                'league': league
            })

    return mismatches


def print_analysis(mismatches):
    """Print analysis results"""
    print("\n" + "=" * 80)
    print("AGE GROUP MISMATCH ANALYSIS")
    print("=" * 80)

    if not mismatches:
        print("\n[OK] No age group mismatches found!")
        return

    # Group by league
    by_league = defaultdict(list)
    for m in mismatches:
        by_league[m['league']].append(m)

    print(f"\n[STATS] Found {len(mismatches)} teams with age_group mismatches:")
    for league, items in sorted(by_league.items(), key=lambda x: -len(x[1])):
        print(f"   {league}: {len(items)} teams")

    # Show sample fixes
    print(f"\n[FIXES] Sample corrections (first 30):")
    print("-" * 80)

    for m in mismatches[:30]:
        print(f"   {m['team_name'][:50]:<50}")
        print(f"      Birth year: {m['birth_year']}")
        print(f"      Current: {m['current_age_group']:<5} -> Correct: {m['correct_age_group']}")
        print()

    if len(mismatches) > 30:
        print(f"   ... and {len(mismatches) - 30} more")

    print("=" * 80)


# ============================================================================
# FIX APPLICATION
# ============================================================================

def apply_fixes(conn, mismatches, dry_run=True):
    """Apply the age_group fixes to the database"""
    if dry_run:
        print("\n[DRY RUN] No changes will be made")
        print("   Run with --apply to make changes")
        return

    cursor = conn.cursor()

    print("\n[APPLYING] Applying age group fixes...")

    fixed_count = 0
    for m in mismatches:
        cursor.execute(
            "UPDATE teams SET age_group = ? WHERE id = ?",
            (m['correct_age_group'], m['id'])
        )
        fixed_count += 1

    conn.commit()

    print(f"\n[OK] Results:")
    print(f"   Age groups fixed: {fixed_count}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fix age_group based on birth year in team names")
    parser.add_argument("--db", help="Path to database file")
    parser.add_argument("--apply", action="store_true", help="Apply fixes (default is dry run)")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    args = parser.parse_args()

    # Find database
    db_path = args.db or find_database()
    if not db_path:
        print("[ERROR] Could not find seedlinedata.db")
        print("   Use --db to specify path")
        sys.exit(1)

    print(f"[DB] Database: {db_path}")
    print(f"[INFO] Convention: Birth year 2011 -> G11/B11 (age group = birth year suffix)")

    # Create backup before applying changes
    if args.apply and not args.no_backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.replace('.db', f'_backup_{timestamp}.db')
        print(f"[BACKUP] Creating backup: {backup_path}")
        shutil.copy2(db_path, backup_path)

    # Connect and analyze
    conn = sqlite3.connect(db_path)

    mismatches = analyze_age_mismatches(conn)
    print_analysis(mismatches)

    # Apply fixes
    if mismatches:
        apply_fixes(conn, mismatches, dry_run=not args.apply)

    conn.close()

    if args.apply:
        print("\n[OK] Database updated successfully!")
    else:
        print("\n[TIP] To apply these fixes, run:")
        print(f"   python {Path(__file__).name} --apply")


if __name__ == "__main__":
    main()
