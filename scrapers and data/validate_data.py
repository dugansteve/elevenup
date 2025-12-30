#!/usr/bin/env python3
"""
Data Validation Script

Checks for team name mismatches between discovered_urls and teams tables
across all leagues. Run periodically to catch data inconsistencies early.

Usage:
    python validate_data.py           # Check all leagues
    python validate_data.py --fix     # Fix all mismatches
    python validate_data.py --league ECNL  # Check specific league
"""

import sqlite3
import argparse
import sys

DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

def check_mismatches(db_path, league=None):
    """Check for team name mismatches"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    leagues = [league] if league else ['ECNL', 'ECNL RL', 'GA', 'ASPIRE']
    total_mismatches = 0

    for lg in leagues:
        league_filter = f"= '{lg}'" if lg not in ['ECNL', 'ECNL RL'] else f"IN ('ECNL', 'ECNL RL')"
        if lg == 'ECNL RL':
            continue  # Already covered by ECNL

        cur.execute(f"""
            SELECT d.url, d.team_name, t.team_name, d.age_group
            FROM discovered_urls d
            JOIN teams t ON d.url = t.team_url
            WHERE d.team_name != t.team_name
            AND d.league {league_filter}
        """)
        mismatches = cur.fetchall()

        if mismatches:
            print(f"\n{'='*60}")
            print(f"{lg}: {len(mismatches)} mismatches")
            print('='*60)
            for url, d_name, t_name, age in mismatches[:5]:
                print(f"  {age}: \"{d_name}\" vs \"{t_name}\"")
            if len(mismatches) > 5:
                print(f"  ... and {len(mismatches) - 5} more")
            total_mismatches += len(mismatches)
        else:
            print(f"{lg}: OK - No mismatches")

    conn.close()
    return total_mismatches


def fix_mismatches(db_path, league=None):
    """Fix mismatches by syncing discovered_urls to teams (teams has better names)"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    leagues = [league] if league else ['ECNL', 'ECNL RL', 'GA', 'ASPIRE']
    total_fixed = 0

    for lg in leagues:
        league_filter = f"= '{lg}'" if lg not in ['ECNL', 'ECNL RL'] else f"IN ('ECNL', 'ECNL RL')"
        if lg == 'ECNL RL':
            continue

        cur.execute(f"""
            UPDATE discovered_urls SET team_name = (
                SELECT t.team_name FROM teams t WHERE t.team_url = discovered_urls.url
            )
            WHERE url IN (
                SELECT d.url FROM discovered_urls d
                JOIN teams t ON d.url = t.team_url
                WHERE d.team_name != t.team_name
                AND d.league {league_filter}
            )
        """)
        fixed = cur.rowcount
        if fixed:
            print(f"{lg}: Fixed {fixed} entries")
            total_fixed += fixed
        else:
            print(f"{lg}: No fixes needed")

    conn.commit()
    conn.close()
    return total_fixed


def main():
    parser = argparse.ArgumentParser(description='Validate Seedline Data')
    parser.add_argument('--db', default=DB_PATH, help='Database path')
    parser.add_argument('--fix', action='store_true', help='Fix mismatches')
    parser.add_argument('--league', choices=['ECNL', 'GA', 'ASPIRE'], help='Specific league')
    args = parser.parse_args()

    print("="*60)
    print("SEEDLINE DATA VALIDATION")
    print("="*60)

    if args.fix:
        print("\nFixing mismatches...")
        fixed = fix_mismatches(args.db, args.league)
        print(f"\nTotal fixed: {fixed}")
    else:
        print("\nChecking for mismatches...")
        mismatches = check_mismatches(args.db, args.league)
        print(f"\nTotal mismatches: {mismatches}")
        if mismatches > 0:
            print("\nRun with --fix to correct these issues")
            sys.exit(1)

    print("\nDone!")


if __name__ == "__main__":
    main()
