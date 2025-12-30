"""
Cleanup duplicate player records from seedlinedata.db

The players table has a UNIQUE constraint on (team_url, player_name, jersey_number),
but SQLite treats NULL jersey_numbers as distinct, allowing duplicates.

This script keeps only one record per (team_url, player_name), preferring:
1. Records with a valid jersey_number
2. The most recent scraped_at if no jersey numbers
"""

import sqlite3
import argparse
from datetime import datetime

def cleanup_duplicates(db_path, dry_run=True):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get counts before
    cursor.execute('SELECT COUNT(*) FROM players')
    total_before = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM (SELECT DISTINCT team_url, player_name FROM players)')
    unique_count = cursor.fetchone()[0]

    duplicates_to_remove = total_before - unique_count

    print(f"Database: {db_path}")
    print(f"Total player records: {total_before:,}")
    print(f"Unique (team_url, player_name): {unique_count:,}")
    print(f"Duplicate records to remove: {duplicates_to_remove:,}")
    print()

    if duplicates_to_remove == 0:
        print("No duplicates found. Database is clean.")
        return

    if dry_run:
        print("DRY RUN - No changes will be made.")
        print("Run with --execute to perform cleanup.")
        return

    print("Cleaning up duplicates...")

    # Strategy: For each (team_url, player_name) group, keep the record with:
    # 1. A valid jersey_number (not NULL and not equal to player_name)
    # 2. If no valid jersey, keep the most recent (highest id)

    # Create a temp table with IDs to keep
    cursor.execute('''
        CREATE TEMP TABLE ids_to_keep AS
        SELECT MAX(CASE
            WHEN jersey_number IS NOT NULL
                 AND jersey_number != player_name
                 AND jersey_number != ''
            THEN id
            ELSE NULL
        END) as jersey_id,
        MAX(id) as latest_id,
        team_url,
        player_name
        FROM players
        GROUP BY team_url, player_name
    ''')

    # Get the IDs to keep (prefer jersey_id, fall back to latest_id)
    cursor.execute('''
        CREATE TEMP TABLE final_keep_ids AS
        SELECT COALESCE(jersey_id, latest_id) as keep_id
        FROM ids_to_keep
    ''')

    # Delete all records NOT in the keep list
    cursor.execute('''
        DELETE FROM players
        WHERE id NOT IN (SELECT keep_id FROM final_keep_ids)
    ''')

    deleted = cursor.rowcount

    # Cleanup temp tables
    cursor.execute('DROP TABLE ids_to_keep')
    cursor.execute('DROP TABLE final_keep_ids')

    conn.commit()

    # Verify
    cursor.execute('SELECT COUNT(*) FROM players')
    total_after = cursor.fetchone()[0]

    print(f"Deleted {deleted:,} duplicate records")
    print(f"Players remaining: {total_after:,}")

    # Vacuum to reclaim space
    print("Vacuuming database...")
    conn.execute('VACUUM')

    conn.close()
    print("Done!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cleanup duplicate players from database')
    parser.add_argument('--db', default='seedlinedata.db', help='Path to database')
    parser.add_argument('--execute', action='store_true', help='Actually perform the cleanup (default is dry run)')

    args = parser.parse_args()

    cleanup_duplicates(args.db, dry_run=not args.execute)
