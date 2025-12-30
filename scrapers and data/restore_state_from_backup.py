#!/usr/bin/env python3
"""
Restore State Data from December 17 Backup

This script restores state (and other address fields) from the Dec 17 backup
where the main database has NULL/empty values. It NEVER overwrites existing data.

Backup: seedlinedata_backup_20251217_144015.db (16,808 teams with 100% state)
Target: seedlinedata.db (55,247 teams, ~83% state coverage)
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
MAIN_DB = SCRIPT_DIR / 'seedlinedata.db'
BACKUP_DB = SCRIPT_DIR / 'seedlinedata_backup_20251217_144015.db'

def restore_state_from_backup(dry_run=False):
    """Restore state data from backup to main database."""

    print("="*60)
    print("RESTORE STATE DATA FROM DECEMBER 17 BACKUP")
    print("="*60)
    print()

    # Verify files exist
    if not MAIN_DB.exists():
        print(f"ERROR: Main database not found: {MAIN_DB}")
        return False
    if not BACKUP_DB.exists():
        print(f"ERROR: Backup database not found: {BACKUP_DB}")
        return False

    # Connect to databases
    backup_conn = sqlite3.connect(BACKUP_DB)
    backup_conn.row_factory = sqlite3.Row
    main_conn = sqlite3.connect(MAIN_DB)
    main_conn.row_factory = sqlite3.Row

    backup_cur = backup_conn.cursor()
    main_cur = main_conn.cursor()

    # Get current state coverage
    main_cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as with_state
        FROM teams
    """)
    row = main_cur.fetchone()
    before_total, before_with_state = row['total'], row['with_state']
    print(f"Before: {before_with_state:,}/{before_total:,} teams have state ({100*before_with_state/before_total:.1f}%)")
    print()

    # Get all teams with state from backup
    backup_cur.execute("""
        SELECT team_url, team_name, club_name, state, city, street_address, zip_code
        FROM teams
        WHERE state IS NOT NULL AND state != ''
    """)
    backup_teams = backup_cur.fetchall()
    print(f"Backup has {len(backup_teams):,} teams with state data")
    print()

    # Strategy 1: Match by team_url (most reliable)
    updated_by_url = 0
    updated_by_name = 0
    skipped_has_state = 0
    not_found = 0

    print("Restoring by team_url match...")
    for team in backup_teams:
        team_url = team['team_url']
        state = team['state']
        city = team['city']
        street = team['street_address']
        zip_code = team['zip_code']

        if not team_url:
            continue

        # Check if team exists in main DB and needs state
        main_cur.execute("""
            SELECT id, state FROM teams WHERE team_url = ?
        """, (team_url,))
        main_team = main_cur.fetchone()

        if main_team:
            if main_team['state'] and main_team['state'].strip():
                skipped_has_state += 1
                continue

            if not dry_run:
                # Update with backup data - ONLY fill NULL/empty fields
                main_cur.execute("""
                    UPDATE teams
                    SET state = ?,
                        city = CASE WHEN city IS NULL OR city = '' THEN ? ELSE city END,
                        street_address = CASE WHEN street_address IS NULL OR street_address = '' THEN ? ELSE street_address END,
                        zip_code = CASE WHEN zip_code IS NULL OR zip_code = '' THEN ? ELSE zip_code END
                    WHERE team_url = ?
                      AND (state IS NULL OR state = '')
                """, (state, city, street, zip_code, team_url))
            updated_by_url += 1
        else:
            not_found += 1

    print(f"  Updated by URL: {updated_by_url:,}")
    print(f"  Skipped (already has state): {skipped_has_state:,}")
    print(f"  Not found in main DB: {not_found:,}")
    print()

    # Strategy 2: Match by team_name (including club_name fill)
    print("Restoring by team_name match...")
    backup_cur.execute("""
        SELECT team_name, club_name, state, city, street_address, zip_code
        FROM teams
        WHERE state IS NOT NULL AND state != ''
          AND team_name IS NOT NULL AND team_name != ''
    """)

    for team in backup_cur.fetchall():
        team_name = team['team_name']
        club_name = team['club_name']
        state = team['state']
        city = team['city']
        street = team['street_address']
        zip_code = team['zip_code']

        if not dry_run:
            # Update teams with same name - fill in ALL missing address fields AND club_name
            result = main_cur.execute("""
                UPDATE teams
                SET state = ?,
                    club_name = CASE WHEN club_name IS NULL OR club_name = '' THEN ? ELSE club_name END,
                    city = CASE WHEN city IS NULL OR city = '' THEN ? ELSE city END,
                    street_address = CASE WHEN street_address IS NULL OR street_address = '' THEN ? ELSE street_address END,
                    zip_code = CASE WHEN zip_code IS NULL OR zip_code = '' THEN ? ELSE zip_code END
                WHERE team_name = ?
                  AND (state IS NULL OR state = '')
            """, (state, club_name, city, street, zip_code, team_name))
            updated_by_name += result.rowcount

    print(f"  Updated by name: {updated_by_name:,}")
    print()

    # Strategy 2b: Match by partial team_name (extract club name pattern)
    print("Restoring by partial team_name match...")
    partial_updates = 0
    backup_cur.execute("""
        SELECT DISTINCT club_name, state, city, street_address, zip_code
        FROM teams
        WHERE state IS NOT NULL AND state != ''
          AND club_name IS NOT NULL AND club_name != ''
    """)

    for team in backup_cur.fetchall():
        club_name = team['club_name']
        state = team['state']
        city = team['city']
        street = team['street_address']
        zip_code = team['zip_code']

        if not club_name or len(club_name) < 4:
            continue

        if not dry_run:
            # Find teams whose name contains this club name
            result = main_cur.execute("""
                UPDATE teams
                SET state = ?,
                    club_name = CASE WHEN club_name IS NULL OR club_name = '' THEN ? ELSE club_name END,
                    city = CASE WHEN city IS NULL OR city = '' THEN ? ELSE city END,
                    street_address = CASE WHEN street_address IS NULL OR street_address = '' THEN ? ELSE street_address END,
                    zip_code = CASE WHEN zip_code IS NULL OR zip_code = '' THEN ? ELSE zip_code END
                WHERE team_name LIKE ? || '%'
                  AND (state IS NULL OR state = '')
            """, (state, club_name, city, street, zip_code, club_name))
            partial_updates += result.rowcount

    print(f"  Updated by club prefix: {partial_updates:,}")
    print()

    # Strategy 3: Match by club_name (fill in from any team with same club)
    print("Filling from same club...")
    if not dry_run:
        result = main_cur.execute("""
            UPDATE teams
            SET state = (
                SELECT t2.state FROM teams t2
                WHERE t2.club_name = teams.club_name
                  AND t2.state IS NOT NULL AND t2.state != ''
                LIMIT 1
            )
            WHERE (state IS NULL OR state = '')
              AND club_name IS NOT NULL AND club_name != ''
              AND EXISTS (
                  SELECT 1 FROM teams t2
                  WHERE t2.club_name = teams.club_name
                    AND t2.state IS NOT NULL AND t2.state != ''
              )
        """)
        updated_by_club = result.rowcount
        print(f"  Updated from same club: {updated_by_club:,}")
    else:
        main_cur.execute("""
            SELECT COUNT(*) FROM teams
            WHERE (state IS NULL OR state = '')
              AND club_name IS NOT NULL AND club_name != ''
              AND EXISTS (
                  SELECT 1 FROM teams t2
                  WHERE t2.club_name = teams.club_name
                    AND t2.state IS NOT NULL AND t2.state != ''
              )
        """)
        would_update = main_cur.fetchone()[0]
        print(f"  Would update from same club: {would_update:,}")
    print()

    if not dry_run:
        main_conn.commit()

    # Get final state coverage
    main_cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as with_state
        FROM teams
    """)
    row = main_cur.fetchone()
    after_total, after_with_state = row['total'], row['with_state']

    print("="*60)
    print("RESULTS")
    print("="*60)
    print(f"Before: {before_with_state:,}/{before_total:,} ({100*before_with_state/before_total:.1f}%)")
    print(f"After:  {after_with_state:,}/{after_total:,} ({100*after_with_state/after_total:.1f}%)")
    print(f"Improvement: +{after_with_state - before_with_state:,} teams")
    print()

    # Show by major league
    print("Coverage by major league:")
    main_cur.execute("""
        SELECT league,
            COUNT(*) as total,
            SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as with_state
        FROM teams
        WHERE league IN ('ECNL', 'ECNL RL', 'GA', 'ASPIRE', 'MLS NEXT', 'NPL')
        GROUP BY league
        ORDER BY total DESC
    """)
    for row in main_cur.fetchall():
        pct = 100*row['with_state']/row['total'] if row['total'] > 0 else 0
        print(f"  {row['league']:15} {row['with_state']:5}/{row['total']:5} ({pct:.1f}%)")

    backup_conn.close()
    main_conn.close()

    if dry_run:
        print("\n[DRY RUN - No changes made]")
    else:
        print(f"\n[Changes committed to {MAIN_DB.name}]")

    return True


if __name__ == '__main__':
    import sys

    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if dry_run:
        print("Running in DRY RUN mode (no changes will be made)")
        print()

    restore_state_from_backup(dry_run=dry_run)
