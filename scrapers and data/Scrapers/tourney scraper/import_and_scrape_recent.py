#!/usr/bin/env python3
"""
Import discovered GotSport events and scrape games from recent tournaments.
Filters for events between May 25, 2025 and today.
"""

import csv
import json
import re
import time
import requests
import sqlite3
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
TOURNAMENTS_FILE = "tournaments_data.json"
EVENTS_CSV = "gotsport_events.csv"
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
START_DATE = datetime(2025, 5, 25)
END_DATE = datetime.now()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_event_dates(event_id):
    """Fetch event page and extract actual dates"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        html = response.text

        # Look for date patterns
        # Pattern: "January 15-17, 2025" or "Jan 15-17 2025"
        date_patterns = [
            r'(\w{3,9})\s+(\d{1,2})[-–](\d{1,2}),?\s*(202[4-6])',
            r'(\d{1,2}/\d{1,2}/202[4-6])',
            r'(202[4-6]-\d{2}-\d{2})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, html)
            if match:
                if len(match.groups()) == 4:
                    month, day_start, day_end, year = match.groups()
                    # Convert month name to number
                    months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                              'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                              'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
                              'july': 7, 'august': 8, 'september': 9, 'october': 10,
                              'november': 11, 'december': 12}
                    month_num = months.get(month.lower(), 0)
                    if month_num:
                        try:
                            start = datetime(int(year), month_num, int(day_start))
                            return start, f"{month} {day_start}-{day_end}, {year}"
                        except:
                            pass
                elif len(match.groups()) == 1:
                    # ISO format or slash format
                    date_str = match.group(1)
                    try:
                        if '-' in date_str:
                            start = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            start = datetime.strptime(date_str, '%m/%d/%Y')
                        return start, date_str
                    except:
                        pass

        return None, None
    except:
        return None, None


def get_schedule_groups(event_id):
    """Get schedule group IDs from event page"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        html = response.text
        groups = re.findall(r'group=(\d+)', html)
        return list(set(groups))
    except:
        return []


def scrape_group_games(event_id, group_id):
    """Scrape games from a schedule group"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}/schedules?group={group_id}"
    games = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        html = response.text

        # Look for game rows
        game_pattern = r'<tr[^>]*class="[^"]*game[^"]*"[^>]*>(.*?)</tr>'
        rows = re.findall(game_pattern, html, re.DOTALL | re.IGNORECASE)

        for row in rows:
            # Extract teams and scores
            team_pattern = r'<td[^>]*class="[^"]*team[^"]*"[^>]*>(.*?)</td>'
            teams = re.findall(team_pattern, row, re.DOTALL)

            score_pattern = r'<td[^>]*class="[^"]*score[^"]*"[^>]*>(\d+)</td>'
            scores = re.findall(score_pattern, row)

            if len(teams) >= 2 and len(scores) >= 2:
                home_team = re.sub(r'<[^>]+>', '', teams[0]).strip()
                away_team = re.sub(r'<[^>]+>', '', teams[1]).strip()

                games.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': int(scores[0]),
                    'away_score': int(scores[1]),
                    'event_id': event_id,
                    'group_id': group_id
                })
    except Exception as e:
        pass

    return games


def import_events_to_tracker():
    """Import discovered events into tournaments_data.json"""
    print("=" * 60)
    print("STEP 1: Importing discovered events to tournament tracker")
    print("=" * 60)

    # Load current tournaments
    with open(TOURNAMENTS_FILE, 'r') as f:
        data = json.load(f)

    existing_ids = set(str(t.get('event_id', '')) for t in data.get('tournaments', []))
    print(f"Existing tournaments: {len(existing_ids)}")

    # Load discovered events
    with open(EVENTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        new_events = list(reader)

    print(f"Discovered events: {len(new_events)}")

    # Add new events
    added = 0
    for e in new_events:
        if str(e['event_id']) not in existing_ids:
            tournament = {
                "event_id": str(e['event_id']),
                "platform": "gotsport",
                "name": e.get('name', f"Event {e['event_id']}"),
                "dates": e.get('dates', ''),
                "year": e.get('year', ''),
                "state": e.get('state', ''),
                "schedule_url": e.get('url', f"https://system.gotsport.com/org_event/events/{e['event_id']}"),
                "status": "discovered",
                "game_count": 0
            }
            data['tournaments'].append(tournament)
            added += 1

    # Save updated tracker
    with open(TOURNAMENTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Added {added} new tournaments to tracker")
    print(f"Total tournaments now: {len(data['tournaments'])}")

    return data['tournaments']


def find_recent_events(tournaments):
    """Find events between May 25, 2025 and today"""
    print()
    print("=" * 60)
    print("STEP 2: Finding events from May 25, 2025 to today")
    print("=" * 60)

    # Filter to 2025 events that need date checking
    candidates = [t for t in tournaments
                  if t.get('platform') == 'gotsport'
                  and (t.get('year') == '2025' or t.get('year') == '2026' or '2025' in str(t.get('dates', '')))]

    print(f"Candidate events to check: {len(candidates)}")
    print(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    print()

    recent_events = []
    checked = 0

    # Check events in batches
    batch_size = 10
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i+batch_size]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(get_event_dates, int(t['event_id'])): t for t in batch}

            for future in as_completed(futures):
                t = futures[future]
                start_date, date_str = future.result()
                checked += 1

                if start_date and START_DATE <= start_date <= END_DATE:
                    t['start_date'] = start_date.strftime('%Y-%m-%d')
                    t['dates'] = date_str or t.get('dates', '')
                    recent_events.append(t)
                    name_safe = t['name'][:40].encode('ascii', 'replace').decode('ascii')
                    print(f"  + {t['event_id']}: {name_safe} ({date_str})")

        if checked % 100 == 0:
            print(f"  [Checked {checked}/{len(candidates)} | Found {len(recent_events)} in range]")

        time.sleep(0.5)  # Be nice to server

    print()
    print(f"Found {len(recent_events)} events in date range")
    return recent_events


def scrape_tournament_games(event_id, event_name):
    """Scrape all games from a tournament"""
    groups = get_schedule_groups(event_id)
    if not groups:
        return []

    all_games = []
    for group in groups:
        games = scrape_group_games(event_id, group)
        all_games.extend(games)
        time.sleep(0.3)

    return all_games


def import_games_to_db(games, tournament_name):
    """Import games to SQLite database"""
    if not games:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    imported = 0
    for game in games:
        try:
            # Check if game exists
            cursor.execute('''
                SELECT 1 FROM games
                WHERE home_team = ? AND away_team = ?
                AND home_score = ? AND away_score = ?
                LIMIT 1
            ''', (game['home_team'], game['away_team'],
                  game['home_score'], game['away_score']))

            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO games (home_team, away_team, home_score, away_score,
                                      league, source_url, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (game['home_team'], game['away_team'],
                      game['home_score'], game['away_score'],
                      'Tournament',
                      f"https://system.gotsport.com/org_event/events/{game['event_id']}",
                      datetime.now().isoformat()))
                imported += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    return imported


def scrape_recent_tournaments(recent_events):
    """Scrape games from recent tournaments"""
    print()
    print("=" * 60)
    print("STEP 3: Scraping games from recent tournaments")
    print("=" * 60)

    total_games = 0
    successful = 0

    for i, event in enumerate(recent_events, 1):
        event_id = int(event['event_id'])
        name = event.get('name', f'Event {event_id}')[:50]
        name_safe = name.encode('ascii', 'replace').decode('ascii')

        print(f"\n[{i}/{len(recent_events)}] Scraping: {name_safe}")

        games = scrape_tournament_games(event_id, name)

        if games:
            imported = import_games_to_db(games, name)
            total_games += imported
            successful += 1
            print(f"  -> Found {len(games)} games, imported {imported} new")
        else:
            print(f"  -> No games found")

        time.sleep(1)  # Be nice to server

    print()
    print("=" * 60)
    print(f"COMPLETE: Scraped {successful} tournaments, imported {total_games} games")
    print("=" * 60)

    return total_games


if __name__ == "__main__":
    print()
    print("GotSport Tournament Importer and Scraper")
    print(f"Date range: May 25, 2025 - {END_DATE.strftime('%B %d, %Y')}")
    print()

    # Step 1: Import to tracker
    tournaments = import_events_to_tracker()

    # Step 2: Find recent events
    recent = find_recent_events(tournaments)

    if not recent:
        print("No events found in date range.")
    else:
        # Step 3: Scrape games
        print(f"\nReady to scrape {len(recent)} tournaments")
        scrape_recent_tournaments(recent)
