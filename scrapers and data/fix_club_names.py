#!/usr/bin/env python3
"""
================================================================================
FIX CLUB NAMES - Correct team-to-club associations
================================================================================

Fixes club_name field where birth year patterns were incorrectly included:
  - "Lamorinda SC 08/" → "Lamorinda SC"
  - "ALBION SC San Diego 08/" → "ALBION SC San Diego"
  - "Ancient City SC /" → "Ancient City SC"

Usage:
    python fix_club_names.py                    # Dry run (analyze only)
    python fix_club_names.py --apply            # Apply fixes
    python fix_club_names.py --db path/to/db    # Custom database path

================================================================================
"""

import sqlite3
import re
import os
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
# CLUB NAME EXTRACTION
# ============================================================================

def extract_correct_club_name(club_name: str) -> str:
    """
    Extract the correct club name by removing trailing year/slash patterns.

    Handles:
      - "Club Name 08/" → "Club Name"
      - "Club Name 07/" → "Club Name"
      - "Club Name /" → "Club Name"
      - "Club Name 08/07" → "Club Name"
      - "Club Name G2008/" → "Club Name"
      - "Club Name 2010/2011" → "Club Name"
    """
    if not club_name:
        return club_name

    corrected = club_name.strip()

    # Pattern 1: Ends with "XX/" where XX is 2 digits (e.g., "08/", "07/")
    corrected = re.sub(r'\s+\d{2}/$', '', corrected)

    # Pattern 2: Ends with just "/"
    corrected = re.sub(r'\s+/$', '', corrected)

    # Pattern 3: Ends with "XX/YY" combined years (e.g., "08/07", "2010/2011")
    corrected = re.sub(r'\s+\d{2,4}/\d{2,4}$', '', corrected)

    # Pattern 4: Ends with "GXXXX/" like "G2008/"
    corrected = re.sub(r'\s+G\d{4}/$', '', corrected)

    # Pattern 5: Ends with single digit pattern like " 08", " 07", " 09" etc
    corrected = re.sub(r'\s+0[7-9]$', '', corrected)

    # Pattern 6: Ends with numbers like "09", "10", "11", "12", "13" (for clubs like "Florida Kraze Krush 09")
    # Only remove if it looks like a birth year, not part of club name
    # Be careful not to remove from names like "FC 1974" or "Americas FC '12"

    # Pattern 7: PKS patterns (score artifacts)
    if 'PKS' in corrected:
        return None  # These are invalid records

    # Clean up any trailing whitespace
    corrected = corrected.strip()

    return corrected if corrected != club_name else None


def is_problem_club_name(club_name: str) -> bool:
    """Check if a club_name has issues that need fixing."""
    if not club_name:
        return False

    # Check for trailing slash patterns
    if re.search(r'\s+\d{2}/$', club_name):
        return True
    if re.search(r'\s+/$', club_name):
        return True
    if re.search(r'\s+\d{2,4}/\d{2,4}$', club_name):
        return True
    if re.search(r'\s+G\d{4}/$', club_name):
        return True

    # Check for PKS (score artifacts)
    if 'PKS' in club_name:
        return True

    return False


# ============================================================================
# ANALYSIS
# ============================================================================

def analyze_club_name_issues(conn):
    """Analyze all club_name issues in the database."""
    cursor = conn.cursor()

    # Get all teams with problematic club names
    cursor.execute("SELECT id, club_name, team_name, league FROM teams ORDER BY club_name")
    all_teams = cursor.fetchall()

    issues = []
    pks_records = []

    for team_id, club_name, team_name, league in all_teams:
        if not is_problem_club_name(club_name):
            continue

        corrected = extract_correct_club_name(club_name)

        if corrected is None:
            # PKS or other invalid record
            pks_records.append({
                'id': team_id,
                'club_name': club_name,
                'team_name': team_name,
                'league': league
            })
        elif corrected != club_name:
            # Check if corrected club exists
            cursor.execute("SELECT COUNT(*) FROM teams WHERE club_name = ?", (corrected,))
            existing_count = cursor.fetchone()[0]

            issues.append({
                'id': team_id,
                'current_club': club_name,
                'corrected_club': corrected,
                'team_name': team_name,
                'league': league,
                'existing_club_teams': existing_count
            })

    return issues, pks_records


def print_analysis(issues, pks_records):
    """Print analysis results."""
    print("\n" + "=" * 70)
    print("CLUB NAME ANALYSIS RESULTS")
    print("=" * 70)

    if not issues and not pks_records:
        print("\n[OK] No club_name issues found!")
        return

    # Group by league
    by_league = defaultdict(list)
    for issue in issues:
        by_league[issue['league']].append(issue)

    print(f"\n[STATS] Found {len(issues)} teams with fixable club_name issues:")
    for league, league_issues in sorted(by_league.items(), key=lambda x: -len(x[1])):
        print(f"   {league}: {len(league_issues)} teams")

    # Show sample fixes
    print("\n[FIXES] Sample fixes (first 20):")
    print("-" * 70)

    for issue in issues[:20]:
        merge_note = f" (will merge with {issue['existing_club_teams']} existing teams)" if issue['existing_club_teams'] > 0 else ""
        print(f"   [{issue['league']}] \"{issue['current_club']}\"")
        print(f"        -> \"{issue['corrected_club']}\"{merge_note}")
        print()

    if len(issues) > 20:
        print(f"   ... and {len(issues) - 20} more")

    # Show consolidation summary
    consolidations = defaultdict(list)
    for issue in issues:
        consolidations[issue['corrected_club']].append(issue['current_club'])

    multi_merge = {k: v for k, v in consolidations.items() if len(v) > 1}
    if multi_merge:
        print(f"\n[MERGE] Clubs with multiple variants to merge ({len(multi_merge)}):")
        for correct, variants in list(multi_merge.items())[:10]:
            print(f"   \"{correct}\" <- {variants}")

    # PKS records
    if pks_records:
        print(f"\n[WARN] Found {len(pks_records)} invalid PKS records (score artifacts):")
        for rec in pks_records[:5]:
            print(f"   [{rec['league']}] \"{rec['club_name']}\"")
        if len(pks_records) > 5:
            print(f"   ... and {len(pks_records) - 5} more")

    print("\n" + "=" * 70)


# ============================================================================
# FIX APPLICATION
# ============================================================================

def apply_fixes(conn, issues, pks_records, dry_run=True):
    """Apply the club_name fixes to the database."""
    if dry_run:
        print("\n[DRY RUN] No changes will be made")
        print("   Run with --apply to make changes")
        return

    cursor = conn.cursor()

    print("\n[APPLYING] Applying fixes...")

    # Fix club names
    fixed_count = 0
    for issue in issues:
        cursor.execute(
            "UPDATE teams SET club_name = ? WHERE id = ?",
            (issue['corrected_club'], issue['id'])
        )
        fixed_count += 1

    # Optionally delete PKS records (they're garbage data)
    deleted_count = 0
    if pks_records:
        print(f"\n[WARN] Deleting {len(pks_records)} invalid PKS records...")
        for rec in pks_records:
            cursor.execute("DELETE FROM teams WHERE id = ?", (rec['id'],))
            deleted_count += 1

    conn.commit()

    print(f"\n[OK] Results:")
    print(f"   Club names fixed: {fixed_count}")
    print(f"   Invalid records deleted: {deleted_count}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fix club_name associations in teams table")
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

    # Create backup before applying changes
    if args.apply and not args.no_backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.replace('.db', f'_backup_{timestamp}.db')
        print(f"[BACKUP] Creating backup: {backup_path}")
        shutil.copy2(db_path, backup_path)

    # Connect and analyze
    conn = sqlite3.connect(db_path)

    issues, pks_records = analyze_club_name_issues(conn)
    print_analysis(issues, pks_records)

    # Apply fixes
    if issues or pks_records:
        apply_fixes(conn, issues, pks_records, dry_run=not args.apply)

    conn.close()

    if args.apply:
        print("\n[OK] Database updated successfully!")
    else:
        print("\n[TIP] To apply these fixes, run:")
        print(f"   python {Path(__file__).name} --apply")


if __name__ == "__main__":
    main()
