#!/usr/bin/env python3
"""
Tournament Suggestion Review Tool

Reviews user-submitted tournament suggestions and imports approved ones.

Usage:
    python review_suggestions.py                    # Show pending suggestions
    python review_suggestions.py --import FILE      # Import suggestions from JSON file
    python review_suggestions.py --approve ID       # Approve a suggestion
    python review_suggestions.py --reject ID        # Reject a suggestion
    python review_suggestions.py --stats            # Show suggestion statistics

The JSON file should be exported from the React app's localStorage.
"""

import json
import os
import sys
import sqlite3
import re
from datetime import datetime
from glob import glob

# Paths
SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(SCRAPER_DIR), 'seedlinedata.db')
SUGGESTIONS_DIR = os.path.join(SCRAPER_DIR, 'suggestions')


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables(conn):
    """Ensure suggestion tables exist"""
    cursor = conn.cursor()

    # Tournament suggestions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suggestion_id TEXT UNIQUE,
            name TEXT,
            url TEXT NOT NULL,
            dates TEXT,
            state TEXT,
            suggested_by_user_id TEXT NOT NULL,
            suggested_by_user_name TEXT,
            status TEXT DEFAULT 'pending',
            review_notes TEXT,
            approved_event_id TEXT,
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_suggestions_status ON tournament_suggestions(status)')
    conn.commit()


def import_suggestions_file(conn, filepath):
    """Import suggestions from a JSON file"""
    cursor = conn.cursor()

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    suggestions = data.get('suggestions', [])
    imported = 0
    skipped = 0

    for sugg in suggestions:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO tournament_suggestions
                (suggestion_id, name, url, dates, state, suggested_by_user_id,
                 suggested_by_user_name, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sugg.get('id'),
                sugg.get('name'),
                sugg.get('url'),
                sugg.get('dates'),
                sugg.get('state'),
                sugg.get('suggested_by_user_id', 'unknown'),
                sugg.get('suggested_by_user_name', 'Unknown'),
                'pending',
                sugg.get('created_at')
            ))

            if cursor.rowcount > 0:
                imported += 1
            else:
                skipped += 1

        except sqlite3.Error as e:
            print(f"  Error importing: {e}")
            skipped += 1

    conn.commit()
    print(f"\nImported: {imported} suggestions")
    print(f"Skipped (duplicates): {skipped}")
    return imported


def show_pending(conn):
    """Show pending suggestions"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, suggestion_id, name, url, dates, state,
               suggested_by_user_name, created_at
        FROM tournament_suggestions
        WHERE status = 'pending'
        ORDER BY created_at DESC
    ''')

    rows = cursor.fetchall()

    if not rows:
        print("\nNo pending suggestions!")
        return

    print(f"\n{'='*80}")
    print(f"PENDING SUGGESTIONS ({len(rows)} total)")
    print('='*80)

    for row in rows:
        print(f"\n[ID: {row['id']}]")
        print(f"  Name:  {row['name'] or '(not provided)'}")
        print(f"  URL:   {row['url']}")
        print(f"  Dates: {row['dates'] or '(not provided)'}")
        print(f"  State: {row['state'] or '(not provided)'}")
        print(f"  By:    {row['suggested_by_user_name']}")
        print(f"  Date:  {row['created_at']}")


def approve_suggestion(conn, suggestion_id, event_id=None, notes=None):
    """Approve a suggestion and optionally add to tournaments table"""
    cursor = conn.cursor()

    # Get the suggestion
    cursor.execute('SELECT * FROM tournament_suggestions WHERE id = ?', (suggestion_id,))
    sugg = cursor.fetchone()

    if not sugg:
        print(f"Suggestion {suggestion_id} not found!")
        return False

    # Generate event_id if not provided
    if not event_id:
        event_id = f"user_{suggestion_id}_{datetime.now().strftime('%Y%m%d')}"

    # Update suggestion status
    cursor.execute('''
        UPDATE tournament_suggestions
        SET status = 'approved',
            approved_event_id = ?,
            review_notes = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (event_id, notes, suggestion_id))

    # Add to tournaments table
    cursor.execute('''
        INSERT OR IGNORE INTO tournaments
        (event_id, platform, name, dates, state, website_url, status,
         suggested_by_user_id, suggestion_source, created_at)
        VALUES (?, 'user_suggested', ?, ?, ?, ?, 'upcoming', ?, 'user_suggestion', CURRENT_TIMESTAMP)
    ''', (
        event_id,
        sugg['name'] or 'User Suggested Tournament',
        sugg['dates'],
        sugg['state'],
        sugg['url'],
        sugg['suggested_by_user_id']
    ))

    conn.commit()
    print(f"\nApproved suggestion {suggestion_id}")
    print(f"  Added to tournaments as: {event_id}")
    return True


def reject_suggestion(conn, suggestion_id, notes=None):
    """Reject a suggestion"""
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE tournament_suggestions
        SET status = 'rejected',
            review_notes = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (notes, suggestion_id))

    if cursor.rowcount > 0:
        conn.commit()
        print(f"\nRejected suggestion {suggestion_id}")
        return True
    else:
        print(f"Suggestion {suggestion_id} not found!")
        return False


def show_stats(conn):
    """Show suggestion statistics"""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("SUGGESTION STATISTICS")
    print("="*60)

    cursor.execute('SELECT COUNT(*) FROM tournament_suggestions')
    total = cursor.fetchone()[0]
    print(f"\nTotal suggestions: {total}")

    cursor.execute('SELECT status, COUNT(*) FROM tournament_suggestions GROUP BY status')
    print("\nBy status:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute('''
        SELECT suggested_by_user_name, COUNT(*)
        FROM tournament_suggestions
        GROUP BY suggested_by_user_id
        ORDER BY COUNT(*) DESC
        LIMIT 10
    ''')
    print("\nTop suggesters:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Count user-suggested tournaments
    cursor.execute("SELECT COUNT(*) FROM tournaments WHERE suggestion_source = 'user_suggestion'")
    approved = cursor.fetchone()[0]
    print(f"\nApproved & added to tournaments: {approved}")


def main():
    args = sys.argv[1:]

    print("="*60)
    print("TOURNAMENT SUGGESTION REVIEW")
    print("="*60)
    print(f"Database: {DB_PATH}")

    conn = get_db_connection()
    ensure_tables(conn)

    try:
        if '--import' in args:
            idx = args.index('--import')
            if idx + 1 < len(args):
                filepath = args[idx + 1]
                if os.path.exists(filepath):
                    print(f"\nImporting: {filepath}")
                    import_suggestions_file(conn, filepath)
                else:
                    print(f"File not found: {filepath}")
            else:
                print("Please provide a JSON file path")

        elif '--approve' in args:
            idx = args.index('--approve')
            if idx + 1 < len(args):
                suggestion_id = int(args[idx + 1])
                event_id = args[idx + 2] if idx + 2 < len(args) else None
                approve_suggestion(conn, suggestion_id, event_id)
            else:
                print("Please provide a suggestion ID")

        elif '--reject' in args:
            idx = args.index('--reject')
            if idx + 1 < len(args):
                suggestion_id = int(args[idx + 1])
                notes = ' '.join(args[idx + 2:]) if idx + 2 < len(args) else None
                reject_suggestion(conn, suggestion_id, notes)
            else:
                print("Please provide a suggestion ID")

        elif '--stats' in args:
            show_stats(conn)

        else:
            # Default: show pending suggestions
            show_pending(conn)
            print("\n" + "-"*60)
            print("Commands:")
            print("  --import FILE     Import suggestions from JSON file")
            print("  --approve ID      Approve a suggestion")
            print("  --reject ID       Reject a suggestion")
            print("  --stats           Show statistics")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
