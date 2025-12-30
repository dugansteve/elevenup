#!/usr/bin/env python3
"""
Quick Tournament Scraper

Scrapes a single tournament and imports games to database.
Uses the tournament ID directly - no need to add to CSV first.

Usage:
    python scrape_tournament.py 42583              # Mustang Stampede U11-U13
    python scrape_tournament.py 42745              # Mustang Stampede U14-U17
    python scrape_tournament.py 45571 --visible    # Show browser
    python scrape_tournament.py --list-premier     # Show premier tournaments

Examples:
    python scrape_tournament.py 42583 42745        # Scrape multiple tournaments
"""

import sys
import os
import csv
import json
import sqlite3
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

# Quick reference for premier tournaments
PREMIER_TOURNAMENTS = {
    '42583': 'Mustang Stampede U11-U13 (Aug 2-3, 2025)',
    '42745': 'Mustang Stampede U14-U17 (Aug 9-10, 2025)',
    '45941': 'IMG Cup Boys Invitational 2025',
    '45745': 'Weston Cup & Showcase 2026',
    '5426': 'Disney Young Legends 2025',
    '5460': 'Jefferson Cup Boys 2026',
    '5461': 'Jefferson Cup Girls 2026',
    '5507': 'Players College Showcase Boys 2026',
    '5508': 'Players College Showcase Girls 2026',
    '5435': 'Blues City Blowout 2026',
}


def scrape_gotsport(event_id, visible=False):
    """Scrape a GotSport tournament"""
    from gotsport_game_scraper_final import setup_driver, scrape_event

    print(f"\n{'='*60}")
    print(f"Scraping GotSport Event: {event_id}")
    if event_id in PREMIER_TOURNAMENTS:
        print(f"Tournament: {PREMIER_TOURNAMENTS[event_id]}")
    print(f"{'='*60}")

    driver = setup_driver(visible=visible)

    try:
        games, event_info = scrape_event(driver, event_id, visible=visible)

        print(f"\nScraped {len(games)} games from {event_info.get('name', 'Unknown')}")

        # Return games for database import
        return games, event_info

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return [], {}
    finally:
        driver.quit()


def import_to_database(games, event_info, event_id):
    """Import games to the seedline database"""
    if not games:
        print("No games to import")
        return 0

    print(f"\nImporting {len(games)} games to database...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure games table exists with tournament source
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='games'
    ''')

    imported = 0
    duplicates = 0

    for game in games:
        # Convert game date to ISO format
        game_date = game.get('game_date', '')
        game_date_iso = ''

        if game_date:
            try:
                # Try parsing various date formats
                for fmt in ['%b %d, %Y', '%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(game_date.strip(), fmt)
                        game_date_iso = dt.strftime('%Y-%m-%d')
                        break
                    except:
                        continue
            except:
                pass

        # Build league name (Tournament: name)
        tournament_name = event_info.get('name', game.get('tournament_name', f'Tournament {event_id}'))
        league = f"Tournament: {tournament_name}"

        # Check for duplicate
        cursor.execute('''
            SELECT game_id FROM games
            WHERE home_team = ? AND away_team = ?
            AND game_date_iso = ? AND game_time = ?
        ''', (
            game.get('home_team', ''),
            game.get('away_team', ''),
            game_date_iso,
            game.get('game_time', '')
        ))

        if cursor.fetchone():
            duplicates += 1
            continue

        # Insert game
        try:
            cursor.execute('''
                INSERT INTO games (
                    game_date, game_date_iso, game_time,
                    home_team, away_team, home_score, away_score,
                    league, age_group, gender, conference,
                    location, game_status, source_url, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_date,
                game_date_iso,
                game.get('game_time', ''),
                game.get('home_team', ''),
                game.get('away_team', ''),
                game.get('home_score'),
                game.get('away_score'),
                league,
                game.get('age_group', ''),
                game.get('gender', ''),
                '',  # conference
                game.get('field', ''),
                game.get('status', 'scheduled'),
                game.get('source_url', ''),
                datetime.now().isoformat()
            ))
            imported += 1
        except Exception as e:
            print(f"  Error inserting game: {e}")

    conn.commit()
    conn.close()

    print(f"Imported {imported} games ({duplicates} duplicates skipped)")
    return imported


def list_premier_tournaments():
    """List known premier tournaments"""
    print("\n" + "="*60)
    print("PREMIER TOURNAMENTS (Quick Reference)")
    print("="*60)
    print("\nEvent ID  | Tournament Name")
    print("-"*60)
    for event_id, name in sorted(PREMIER_TOURNAMENTS.items()):
        print(f"{event_id:9} | {name}")
    print("\nUsage: python scrape_tournament.py EVENT_ID")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ['-h', '--help', 'help']:
        print(__doc__)
        return

    if args[0] == '--list-premier':
        list_premier_tournaments()
        return

    visible = '--visible' in args
    args = [a for a in args if not a.startswith('--')]

    # Scrape each event ID provided
    total_games = 0

    for event_id in args:
        if not event_id.isdigit():
            print(f"Skipping invalid event ID: {event_id}")
            continue

        games, event_info = scrape_gotsport(event_id, visible=visible)

        if games:
            imported = import_to_database(games, event_info, event_id)
            total_games += imported

    print(f"\n{'='*60}")
    print(f"COMPLETE - Total games imported: {total_games}")
    print("="*60)


if __name__ == "__main__":
    main()
