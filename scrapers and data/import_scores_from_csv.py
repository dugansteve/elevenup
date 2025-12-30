#!/usr/bin/env python3
"""
Import scores from scraper CSV into database
Updates games missing scores by matching on date, teams, age, league
"""
import sqlite3
import csv
import re
from pathlib import Path

DB_PATH = r'C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db'
CSV_DIR = Path(r'C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\Scrapers\ECNL and ECNL RL Scraper')

def normalize(team):
    if not team:
        return ""
    n = team.lower().strip()
    n = re.sub(r'\s+(sc|fc)\s*$', '', n, flags=re.I)
    n = re.sub(r'\s+soccer\s*club\s*$', '', n, flags=re.I)
    for word in ['soccer', 'fc', 'sc', 'academy', 'club', 'united']:
        n = re.sub(r'\b' + word + r'\b', '', n, flags=re.I)
    n = re.sub(r'[^a-z0-9]', '', n)
    return n[:25]

def main():
    # Find most recent CSV
    csv_files = sorted(CSV_DIR.glob('ECNL_games_2025122*.csv'))
    if not csv_files:
        print("No CSV files found")
        return

    csv_path = csv_files[-1]
    print(f"Reading {csv_path.name}")

    # Load games with scores from CSV
    games_with_scores = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('home_score') and row['home_score'].strip():
                try:
                    home_score = int(row['home_score'])
                    away_score = int(row.get('away_score', 0) or 0)
                    games_with_scores.append({
                        'date': row.get('game_date_iso', ''),
                        'home': normalize(row.get('home_team', '')),
                        'away': normalize(row.get('away_team', '')),
                        'age': row.get('age_group', ''),
                        'league': row.get('league', ''),
                        'home_score': home_score,
                        'away_score': away_score,
                        'home_team_orig': row.get('home_team', ''),
                        'away_team_orig': row.get('away_team', ''),
                    })
                except (ValueError, TypeError):
                    pass

    print(f"Found {len(games_with_scores)} games with scores in CSV")

    import time
    for attempt in range(5):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=60)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")
            break
        except sqlite3.OperationalError as e:
            if attempt < 4:
                print(f"Database locked, retrying in {5*(attempt+1)}s...")
                time.sleep(5 * (attempt + 1))
            else:
                raise
    cur = conn.cursor()

    # Get games missing scores
    cur.execute('''
        SELECT rowid, game_date_iso, home_team, away_team, age_group, league
        FROM games
        WHERE home_score IS NULL AND league LIKE '%ECNL%'
    ''')
    missing_games = cur.fetchall()
    print(f"Found {len(missing_games)} games missing scores in DB")

    # Build lookup
    missing_lookup = {}
    for row in missing_games:
        rowid, date, home, away, age, league = row
        home_n = normalize(home)
        away_n = normalize(away)
        key = (date, home_n, away_n, age)
        if key not in missing_lookup:
            missing_lookup[key] = []
        missing_lookup[key].append(rowid)
        # Also add reversed key
        key_rev = (date, away_n, home_n, age)
        if key_rev not in missing_lookup:
            missing_lookup[key_rev] = []
        missing_lookup[key_rev].append(rowid)

    # Update games with retry
    updated = 0
    batch = []
    for g in games_with_scores:
        key = (g['date'], g['home'], g['away'], g['age'])
        if key in missing_lookup:
            for rowid in missing_lookup[key]:
                batch.append((g['home_score'], g['away_score'], rowid))

    print(f"Updating {len(batch)} matches...")
    for home_score, away_score, rowid in batch:
        for attempt in range(3):
            try:
                cur.execute('''
                    UPDATE games SET home_score = ?, away_score = ?
                    WHERE rowid = ? AND home_score IS NULL
                ''', (home_score, away_score, rowid))
                if cur.rowcount > 0:
                    updated += 1
                break
            except sqlite3.OperationalError:
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise

    for attempt in range(3):
        try:
            conn.commit()
            break
        except sqlite3.OperationalError:
            if attempt < 2:
                time.sleep(2)
                continue
            raise
    print(f"Updated {updated} games with scores")

    # Clean up exact duplicates (same date, teams, age, league)
    # Keep the one with a score or the one with a game_id
    cur.execute('''
        DELETE FROM games
        WHERE rowid NOT IN (
            SELECT MIN(CASE WHEN home_score IS NOT NULL THEN rowid ELSE rowid + 1000000000 END)
            FROM games
            WHERE league LIKE '%ECNL%'
            GROUP BY game_date_iso, home_team, away_team, age_group, league
        )
        AND league LIKE '%ECNL%'
        AND home_score IS NULL
    ''')
    deleted = cur.rowcount
    conn.commit()
    print(f"Deleted {deleted} duplicate entries without scores")

    # Check Dec 14
    cur.execute('''
        SELECT
            SUM(CASE WHEN home_score IS NOT NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN home_score IS NULL THEN 1 ELSE 0 END)
        FROM games WHERE game_date_iso = '2025-12-14' AND league LIKE '%ECNL%'
    ''')
    row = cur.fetchone()
    print(f"\nDec 14 status: {row[0]} with scores, {row[1]} missing")

    conn.close()
    print("Done!")

if __name__ == '__main__':
    main()
