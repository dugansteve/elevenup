#!/usr/bin/env python3
"""
State Coverage Check - Run after scraping to ensure state data quality

This script:
1. Reports state coverage percentage by league
2. Alerts if coverage drops below threshold (80%)
3. Auto-runs populate_team_states.py if coverage is low
4. Designed to be called from run_daily_scrape.bat after scraping

Exit codes:
  0 = All leagues at or above threshold
  1 = Issues found and auto-fix attempted
  2 = Critical issues remain after auto-fix
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / 'seedlinedata.db'
DEFAULT_THRESHOLD = 80  # Minimum % of teams that should have state

# Major leagues to check with their thresholds
# MLS NEXT has lower threshold due to garbage data in the source
LEAGUE_THRESHOLDS = {
    'ECNL': 85,
    'ECNL RL': 80,
    'GA': 95,
    'ASPIRE': 95,
    'MLS NEXT': 70,  # Lower threshold - source has garbage data like game IDs
    'NPL': 95,
}

MAJOR_LEAGUES = list(LEAGUE_THRESHOLDS.keys())


def get_coverage_by_league():
    """Get state coverage statistics by league."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT league,
               COUNT(*) as total,
               SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as with_state
        FROM teams
        GROUP BY league
        ORDER BY total DESC
    """)

    results = {}
    for league, total, with_state in cursor.fetchall():
        pct = (with_state / total * 100) if total > 0 else 0
        results[league] = {
            'total': total,
            'with_state': with_state,
            'missing': total - with_state,
            'pct': pct
        }

    conn.close()
    return results


def get_overall_coverage():
    """Get overall state coverage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as with_state
        FROM teams
    """)

    total, with_state = cursor.fetchone()
    conn.close()

    return {
        'total': total,
        'with_state': with_state,
        'missing': total - with_state,
        'pct': (with_state / total * 100) if total > 0 else 0
    }


def run_populate_script():
    """Run populate_team_states.py to fix missing state data."""
    populate_script = SCRIPT_DIR / 'populate_team_states.py'

    if not populate_script.exists():
        print(f"ERROR: populate_team_states.py not found at {populate_script}")
        return False

    print("\nRunning populate_team_states.py to fix missing state data...")
    print("-" * 50)

    try:
        result = subprocess.run(
            [sys.executable, str(populate_script)],
            cwd=str(SCRIPT_DIR),
            capture_output=False,
            timeout=300
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("ERROR: populate_team_states.py timed out")
        return False
    except Exception as e:
        print(f"ERROR: Failed to run populate_team_states.py: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("STATE DATA COVERAGE CHECK")
    print("=" * 60)
    print()

    # Get overall coverage
    overall = get_overall_coverage()
    print(f"Overall: {overall['with_state']:,}/{overall['total']:,} ({overall['pct']:.1f}%)")
    print()

    # Get coverage by league
    coverage = get_coverage_by_league()
    if coverage is None:
        return 2

    # Check major leagues
    print("Major leagues (per-league thresholds):")
    print("-" * 60)

    issues = []
    for league in MAJOR_LEAGUES:
        if league not in coverage:
            print(f"  {league:15} | NOT FOUND")
            continue

        data = coverage[league]
        pct = data['pct']
        threshold = LEAGUE_THRESHOLDS.get(league, DEFAULT_THRESHOLD)
        status = 'OK' if pct >= threshold else 'LOW'

        if status == 'LOW':
            issues.append((league, pct, data['missing'], threshold))

        print(f"  {league:15} | {data['with_state']:5}/{data['total']:5} ({pct:.0f}%) [{status}] (min {threshold}%)")

    print()

    # If issues found, try to fix them
    if issues:
        print(f"[!] {len(issues)} league(s) below threshold:")
        for league, pct, missing, threshold in issues:
            print(f"    - {league}: {pct:.0f}% (threshold: {threshold}%, {missing} teams missing)")

        # Run auto-fix
        success = run_populate_script()

        if success:
            print("\nRe-checking coverage after fix:")
            print("-" * 50)

            # Re-check coverage
            new_coverage = get_coverage_by_league()
            new_overall = get_overall_coverage()

            print(f"Overall: {new_overall['with_state']:,}/{new_overall['total']:,} ({new_overall['pct']:.1f}%)")
            print()

            remaining_issues = []
            for league in MAJOR_LEAGUES:
                if league not in new_coverage:
                    continue

                data = new_coverage[league]
                pct = data['pct']
                threshold = LEAGUE_THRESHOLDS.get(league, DEFAULT_THRESHOLD)
                status = 'OK' if pct >= threshold else 'STILL LOW'

                if pct < threshold:
                    remaining_issues.append((league, pct, data['missing']))

                print(f"  {league:15} | {data['with_state']:5}/{data['total']:5} ({pct:.0f}%) [{status}]")

            if remaining_issues:
                print(f"\n[!] {len(remaining_issues)} league(s) still below threshold - manual review needed")
                return 2
            else:
                print("\n[OK] All major leagues now at or above threshold")
                return 1  # Fixed issues
        else:
            print("\n[!] Auto-fix failed - manual intervention needed")
            return 2
    else:
        print("[OK] All major leagues at or above their thresholds")
        return 0


if __name__ == '__main__':
    sys.exit(main())
