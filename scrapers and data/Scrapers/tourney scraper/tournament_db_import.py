#!/usr/bin/env python3
"""
Tournament Database Import

Imports scraped tournament data into seedlinedata.db:
- Creates tournaments table with metadata (name, dates, location, URL)
- Creates tournament_games table for game data
- Links tournament games to main games table format

Usage:
    python tournament_db_import.py                     # Import all scraped data
    python tournament_db_import.py --tournament 45571  # Import specific tournament
    python tournament_db_import.py --status            # Show import status
    python tournament_db_import.py --create-tables     # Create tables only

Tables created:
    tournaments - Tournament metadata for search/browse
    tournament_games - Individual game records
"""

import csv
import json
import os
import sys
import sqlite3
from datetime import datetime
from glob import glob

# Paths
SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
PROGRESS_FILE = os.path.join(SCRAPER_DIR, 'batch_progress.json')
TOURNAMENT_CSV = os.path.join(SCRAPER_DIR, 'tournament_urls_v2.csv')


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    """Create tournaments and tournament_games tables"""
    cursor = conn.cursor()

    # Tournaments table - for searching/browsing upcoming tournaments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            platform TEXT NOT NULL,
            name TEXT,
            dates TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            city TEXT,
            state TEXT,
            venue TEXT,
            schedule_url TEXT,
            registration_url TEXT,
            website_url TEXT,
            age_groups TEXT,
            gender TEXT,
            status TEXT DEFAULT 'upcoming',
            game_count INTEGER DEFAULT 0,
            team_count INTEGER DEFAULT 0,
            suggested_by_user_id TEXT,
            suggestion_source TEXT,
            scraped_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tournament suggestions table - for user-submitted tournament suggestions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT NOT NULL,
            dates TEXT,
            state TEXT,
            suggested_by_user_id TEXT NOT NULL,
            suggested_by_user_name TEXT,
            status TEXT DEFAULT 'pending',
            review_notes TEXT,
            approved_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        )
    ''')

    # Tournament games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL,
            tournament_name TEXT,
            game_date TEXT,
            game_date_iso TEXT,
            game_time TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            age_group TEXT,
            division TEXT,
            bracket TEXT,
            field TEXT,
            game_status TEXT DEFAULT 'scheduled',
            game_number TEXT,
            source_url TEXT,
            scraped_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(event_id)
        )
    ''')

    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournaments_platform ON tournaments(platform)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournaments_state ON tournaments(state)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournaments_start_date ON tournaments(start_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournament_games_tournament_id ON tournament_games(tournament_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournament_games_date ON tournament_games(game_date_iso)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournament_suggestions_status ON tournament_suggestions(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournament_suggestions_user ON tournament_suggestions(suggested_by_user_id)')

    # Add new columns to tournaments table if they don't exist
    try:
        cursor.execute('ALTER TABLE tournaments ADD COLUMN suggested_by_user_id TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE tournaments ADD COLUMN suggestion_source TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE tournaments ADD COLUMN sponsor TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE tournaments ADD COLUMN latitude REAL')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE tournaments ADD COLUMN longitude REAL')
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    print("Tables created successfully")


def parse_date_to_iso(date_str):
    """Convert various date formats to ISO format"""
    if not date_str:
        return None

    # Try common formats
    formats = [
        '%m/%d/%Y',
        '%m/%d/%y',
        '%Y-%m-%d',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


def extract_location_parts(location_str):
    """Extract city, state from location string"""
    if not location_str:
        return None, None

    # Common patterns: "City, ST" or "City, State"
    import re

    # Try "City, ST" format
    match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\b', location_str)
    if match:
        return match.group(1).strip(), match.group(2)

    # Try to find state abbreviation
    states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
              'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
              'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
              'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
              'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']

    for state in states:
        if state in location_str.upper():
            return location_str.replace(state, '').strip(' ,'), state

    return location_str, None


def load_tournament_metadata():
    """Load tournament metadata from CSV - includes ALL tournaments"""
    tournaments = {}

    if not os.path.exists(TOURNAMENT_CSV):
        print(f"Tournament CSV not found: {TOURNAMENT_CSV}")
        return tournaments

    row_num = 0
    with open(TOURNAMENT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_num += 1
            # Use event_id if available, otherwise generate one from row number
            event_id = row.get('event_id', '').strip()
            if not event_id:
                # Generate ID for tournaments without schedule platform
                event_id = f"tourney_{row_num}"

            tournaments[event_id] = {
                'event_id': event_id,
                'platform': row.get('schedule_platform', '').lower() or 'website',
                'name': row.get('name', ''),
                'dates': row.get('dates', ''),
                'state': row.get('state', ''),
                'club': row.get('club', ''),
                'age_groups': row.get('age_groups', ''),
                'schedule_url': row.get('schedule_url', ''),
                'website_url': row.get('website_url', ''),
                'status': row.get('status', 'pending'),
            }

    return tournaments


def load_scrape_progress():
    """Load scraping progress"""
    if not os.path.exists(PROGRESS_FILE):
        return {}

    with open(PROGRESS_FILE, 'r') as f:
        return json.load(f).get('scraped', {})


def import_tournament(conn, event_id, tournament_meta, progress_info):
    """Import a single tournament and its games"""
    cursor = conn.cursor()

    # Merge metadata
    platform = progress_info.get('platform') or tournament_meta.get('platform', 'unknown')
    name = progress_info.get('name') or tournament_meta.get('name', '')
    dates = tournament_meta.get('dates', '')
    state = tournament_meta.get('state', '')
    club = tournament_meta.get('club', '')
    age_groups = tournament_meta.get('age_groups', '')

    # Parse start date from dates field
    start_date = None
    if dates:
        # Try to extract first date
        import re
        date_match = re.search(r'(\w+\s+\d{1,2})', dates)
        if date_match:
            # Add current year if not present
            date_str = date_match.group(1)
            if '202' not in dates:
                date_str += ', 2025'
            start_date = parse_date_to_iso(date_str)

    # Determine status
    game_count = progress_info.get('games', 0)
    status = 'completed' if game_count > 0 else 'upcoming'

    # Get URLs - use schedule_url if available, otherwise website_url
    schedule_url = tournament_meta.get('schedule_url', '')
    website_url = tournament_meta.get('website_url', '')

    # Insert or update tournament
    cursor.execute('''
        INSERT OR REPLACE INTO tournaments
        (event_id, platform, name, dates, start_date, state, age_groups,
         schedule_url, website_url, status, game_count, sponsor,
         scraped_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        event_id, platform, name, dates, start_date, state, age_groups,
        schedule_url,
        website_url,
        status, game_count, club,
        progress_info.get('scraped_at')
    ))

    # Import games if CSV exists
    game_files = [
        f"gotsport_{event_id}_games.csv",
        f"sincsports_{event_id}_games.csv",
        f"tgs_{event_id}_games.csv",
        f"a2e_{event_id}_games.csv",
    ]

    games_imported = 0
    for game_file in game_files:
        filepath = os.path.join(SCRAPER_DIR, game_file)
        if os.path.exists(filepath):
            games_imported += import_games_from_csv(conn, filepath, event_id)

    return games_imported


def import_games_from_csv(conn, filepath, tournament_id):
    """Import games from a CSV file"""
    cursor = conn.cursor()
    imported = 0

    # First, delete existing games for this tournament
    cursor.execute('DELETE FROM tournament_games WHERE tournament_id = ?', (tournament_id,))

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            game_date = row.get('game_date', '')
            game_date_iso = parse_date_to_iso(game_date)

            # Parse scores
            home_score = None
            away_score = None
            try:
                if row.get('home_score'):
                    home_score = int(row['home_score'])
                if row.get('away_score'):
                    away_score = int(row['away_score'])
            except (ValueError, TypeError):
                pass

            cursor.execute('''
                INSERT INTO tournament_games
                (tournament_id, tournament_name, game_date, game_date_iso, game_time,
                 home_team, away_team, home_score, away_score, age_group, division,
                 bracket, field, game_status, game_number, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tournament_id,
                row.get('tournament_name', ''),
                game_date,
                game_date_iso,
                row.get('game_time', ''),
                row.get('home_team', ''),
                row.get('away_team', ''),
                home_score,
                away_score,
                row.get('age_group', ''),
                row.get('division', ''),
                row.get('bracket', ''),
                row.get('field', ''),
                row.get('status', 'scheduled'),
                row.get('game_number', ''),
                row.get('source_url', ''),
                row.get('scraped_at', '')
            ))
            imported += 1

    conn.commit()
    return imported


def import_all(conn):
    """Import all tournaments from CSV and scraped data"""
    tournament_meta = load_tournament_metadata()
    progress = load_scrape_progress()

    print(f"\nFound {len(tournament_meta)} tournaments in CSV")
    print(f"Found {len(progress)} scraped tournaments in progress file")

    total_tournaments = 0
    total_games = 0
    scraped_count = 0
    pending_count = 0

    # Import all tournaments from CSV
    for event_id, meta in tournament_meta.items():
        prog_info = progress.get(event_id, {})
        games = import_tournament(conn, event_id, meta, prog_info)
        total_tournaments += 1
        total_games += games

        if prog_info:
            scraped_count += 1
            print(f"  Imported {event_id}: {meta.get('name', 'Unknown')[:40]} ({games} games)")
        else:
            pending_count += 1

    conn.commit()
    print(f"\nTotal: {total_tournaments} tournaments")
    print(f"  - Scraped with games: {scraped_count}")
    print(f"  - Pending/website only: {pending_count}")
    print(f"  - Total games: {total_games}")


def show_status(conn):
    """Show database status"""
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("DATABASE STATUS")
    print("=" * 60)

    # Tournament counts
    cursor.execute('SELECT COUNT(*) FROM tournaments')
    total = cursor.fetchone()[0]
    print(f"\nTotal tournaments: {total}")

    cursor.execute('SELECT platform, COUNT(*) FROM tournaments GROUP BY platform')
    print("\nBy platform:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute('SELECT status, COUNT(*) FROM tournaments GROUP BY status')
    print("\nBy status:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute('SELECT state, COUNT(*) FROM tournaments WHERE state IS NOT NULL GROUP BY state ORDER BY COUNT(*) DESC LIMIT 10')
    print("\nBy state (top 10):")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Game counts
    cursor.execute('SELECT COUNT(*) FROM tournament_games')
    total_games = cursor.fetchone()[0]
    print(f"\nTotal tournament games: {total_games}")

    cursor.execute('''
        SELECT t.platform, COUNT(g.id)
        FROM tournament_games g
        JOIN tournaments t ON g.tournament_id = t.event_id
        GROUP BY t.platform
    ''')
    print("\nGames by platform:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")


def main():
    args = sys.argv[1:]

    print("=" * 60)
    print("TOURNAMENT DATABASE IMPORT")
    print("=" * 60)
    print(f"Database: {DB_PATH}")

    conn = get_db_connection()

    try:
        if '--create-tables' in args:
            create_tables(conn)
            return

        if '--status' in args:
            show_status(conn)
            return

        if '--tournament' in args:
            idx = args.index('--tournament')
            if idx + 1 < len(args):
                event_id = args[idx + 1]
                print(f"\nImporting tournament: {event_id}")
                tournament_meta = load_tournament_metadata()
                progress = load_scrape_progress()
                meta = tournament_meta.get(event_id, {})
                prog = progress.get(event_id, {})
                games = import_tournament(conn, event_id, meta, prog)
                print(f"Imported {games} games")
            return

        # Default: import all
        create_tables(conn)
        import_all(conn)
        show_status(conn)

    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
