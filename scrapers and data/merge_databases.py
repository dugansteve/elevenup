#!/usr/bin/env python3
r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATABASE MERGE SCRIPT - Combine Two Seedline Databases
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PURPOSE:
  Merges data from a SOURCE database into a TARGET database without duplicates.
  Useful when you accidentally scraped into the wrong database location.

WHAT IT DOES:
  1. Copies new games (by game_id) from source to target
  2. Updates scores if source has them but target doesn't
  3. Merges teams, ga_teams, and discovered_urls tables
  4. Creates a backup of target before modifying

USAGE:
  python merge_databases.py SOURCE_DB TARGET_DB
  python merge_databases.py --dry-run SOURCE_DB TARGET_DB    # Preview only
  
EXAMPLE (Windows - note the quotes around paths with spaces):
  python merge_databases.py "C:\Users\dugan\Seedline\seedlinedata.db" "C:\Users\dugan\Dropbox\Seedline\seedlinedata.db"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sqlite3
import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path


def get_db_stats(db_path):
    """Get statistics for a database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = {'path': db_path, 'size': os.path.getsize(db_path)}
    
    # Games by league
    cursor.execute("""
        SELECT league, 
               COUNT(*) as total,
               SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) as complete
        FROM games 
        GROUP BY league
    """)
    stats['games_by_league'] = {row[0]: {'total': row[1], 'complete': row[2]} for row in cursor.fetchall()}
    
    # Total games
    cursor.execute("SELECT COUNT(*) FROM games")
    stats['total_games'] = cursor.fetchone()[0]
    
    # Other tables
    for table in ['teams', 'ga_teams', 'discovered_urls']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except:
            stats[table] = 0
    
    conn.close()
    return stats


def print_stats(stats, label):
    """Print database statistics"""
    print(f"\n{'='*60}")
    print(f"📊 {label}")
    print(f"{'='*60}")
    print(f"Path: {stats['path']}")
    print(f"Size: {stats['size']:,} bytes")
    print(f"\nGames by league:")
    for league, counts in sorted(stats['games_by_league'].items()):
        print(f"  {league}: {counts['total']:,} total, {counts['complete']:,} complete")
    print(f"\nTotal games: {stats['total_games']:,}")
    print(f"Teams: {stats.get('teams', 0):,}")
    print(f"GA Teams: {stats.get('ga_teams', 0):,}")
    print(f"Discovered URLs: {stats.get('discovered_urls', 0):,}")


def merge_games(source_conn, target_conn, dry_run=False):
    """Merge games from source to target"""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Get all game_ids in target
    target_cursor.execute("SELECT game_id FROM games")
    target_ids = {row[0] for row in target_cursor.fetchall()}
    
    # Get all games from source
    source_cursor.execute("""
        SELECT game_id, age_group, game_date, game_time, home_team, away_team,
               home_score, away_score, conference, location, scraped_at, 
               source_url, game_status, league, home_team_url, away_team_url
        FROM games
    """)
    source_games = source_cursor.fetchall()
    
    new_games = []
    updated_scores = []
    
    for game in source_games:
        game_id = game[0]
        home_score = game[6]
        away_score = game[7]
        
        if game_id not in target_ids:
            # New game - add it
            new_games.append(game)
        else:
            # Existing game - check if we should update scores
            if home_score is not None and away_score is not None:
                target_cursor.execute(
                    "SELECT home_score, away_score FROM games WHERE game_id = ?",
                    (game_id,)
                )
                target_scores = target_cursor.fetchone()
                if target_scores[0] is None or target_scores[1] is None:
                    updated_scores.append((home_score, away_score, game_id))
    
    print(f"\n📋 GAMES MERGE SUMMARY:")
    print(f"  Source games: {len(source_games):,}")
    print(f"  Already in target: {len(target_ids):,}")
    print(f"  New games to add: {len(new_games):,}")
    print(f"  Scores to update: {len(updated_scores):,}")
    
    if dry_run:
        print("\n  🔍 DRY RUN - No changes made")
        return len(new_games), len(updated_scores)
    
    # Insert new games
    if new_games:
        target_cursor.executemany("""
            INSERT INTO games (game_id, age_group, game_date, game_time, home_team, away_team,
                              home_score, away_score, conference, location, scraped_at,
                              source_url, game_status, league, home_team_url, away_team_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, new_games)
        print(f"  ✅ Added {len(new_games):,} new games")
    
    # Update scores
    if updated_scores:
        target_cursor.executemany(
            "UPDATE games SET home_score = ?, away_score = ? WHERE game_id = ?",
            updated_scores
        )
        print(f"  ✅ Updated {len(updated_scores):,} scores")
    
    return len(new_games), len(updated_scores)


def merge_teams(source_conn, target_conn, dry_run=False):
    """Merge teams table"""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Check if teams table exists in both
    try:
        source_cursor.execute("SELECT team_name, team_url, league, age_group, conference FROM teams")
        source_teams = source_cursor.fetchall()
    except:
        print("\n📋 TEAMS: No teams table in source")
        return 0
    
    try:
        target_cursor.execute("SELECT team_name, team_url FROM teams")
        target_teams = {(row[0], row[1]) for row in target_cursor.fetchall()}
    except:
        # Create teams table if it doesn't exist
        target_cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT,
                team_url TEXT,
                league TEXT,
                age_group TEXT,
                conference TEXT,
                UNIQUE(team_name, team_url)
            )
        """)
        target_teams = set()
    
    new_teams = [t for t in source_teams if (t[0], t[1]) not in target_teams]
    
    print(f"\n📋 TEAMS MERGE:")
    print(f"  Source teams: {len(source_teams):,}")
    print(f"  New teams to add: {len(new_teams):,}")
    
    if dry_run:
        return len(new_teams)
    
    if new_teams:
        target_cursor.executemany("""
            INSERT OR IGNORE INTO teams (team_name, team_url, league, age_group, conference)
            VALUES (?, ?, ?, ?, ?)
        """, new_teams)
        print(f"  ✅ Added {len(new_teams):,} teams")
    
    return len(new_teams)


def merge_ga_teams(source_conn, target_conn, dry_run=False):
    """Merge ga_teams table"""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    try:
        source_cursor.execute("""
            SELECT team_id, team_name, club_name, age_group, conference, event_id, source_url, added_at
            FROM ga_teams
        """)
        source_teams = source_cursor.fetchall()
    except:
        print("\n📋 GA_TEAMS: No ga_teams table in source")
        return 0
    
    try:
        target_cursor.execute("SELECT team_id FROM ga_teams")
        target_ids = {row[0] for row in target_cursor.fetchall()}
    except:
        target_cursor.execute("""
            CREATE TABLE IF NOT EXISTS ga_teams (
                team_id TEXT PRIMARY KEY,
                team_name TEXT,
                club_name TEXT,
                age_group TEXT,
                conference TEXT,
                event_id TEXT,
                source_url TEXT,
                added_at TIMESTAMP
            )
        """)
        target_ids = set()
    
    new_teams = [t for t in source_teams if t[0] not in target_ids]
    
    print(f"\n📋 GA_TEAMS MERGE:")
    print(f"  Source ga_teams: {len(source_teams):,}")
    print(f"  New ga_teams to add: {len(new_teams):,}")
    
    if dry_run:
        return len(new_teams)
    
    if new_teams:
        target_cursor.executemany("""
            INSERT OR IGNORE INTO ga_teams (team_id, team_name, club_name, age_group, conference, event_id, source_url, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, new_teams)
        print(f"  ✅ Added {len(new_teams):,} ga_teams")
    
    return len(new_teams)


def merge_discovered_urls(source_conn, target_conn, dry_run=False):
    """Merge discovered_urls table"""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    try:
        source_cursor.execute("SELECT url, discovered_at, league, age_group FROM discovered_urls")
        source_urls = source_cursor.fetchall()
    except:
        print("\n📋 DISCOVERED_URLS: No discovered_urls table in source")
        return 0
    
    try:
        target_cursor.execute("SELECT url FROM discovered_urls")
        target_urls = {row[0] for row in target_cursor.fetchall()}
    except:
        target_cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovered_urls (
                url TEXT PRIMARY KEY,
                discovered_at TIMESTAMP,
                league TEXT,
                age_group TEXT
            )
        """)
        target_urls = set()
    
    new_urls = [u for u in source_urls if u[0] not in target_urls]
    
    print(f"\n📋 DISCOVERED_URLS MERGE:")
    print(f"  Source URLs: {len(source_urls):,}")
    print(f"  New URLs to add: {len(new_urls):,}")
    
    if dry_run:
        return len(new_urls)
    
    if new_urls:
        target_cursor.executemany("""
            INSERT OR IGNORE INTO discovered_urls (url, discovered_at, league, age_group)
            VALUES (?, ?, ?, ?)
        """, new_urls)
        print(f"  ✅ Added {len(new_urls):,} URLs")
    
    return len(new_urls)


def main():
    parser = argparse.ArgumentParser(
        description='Merge two Seedline databases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python merge_databases.py source.db target.db
  python merge_databases.py --dry-run source.db target.db
        """
    )
    
    parser.add_argument('source_db', help='Source database (data to copy FROM)')
    parser.add_argument('target_db', help='Target database (data to copy TO)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Preview changes without modifying anything')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip creating backup of target database')
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.source_db):
        print(f"❌ Source database not found: {args.source_db}")
        sys.exit(1)
    
    if not os.path.exists(args.target_db):
        print(f"❌ Target database not found: {args.target_db}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("🔄 DATABASE MERGE TOOL")
    print("="*70)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Show stats for both databases
    source_stats = get_db_stats(args.source_db)
    target_stats = get_db_stats(args.target_db)
    
    print_stats(source_stats, "SOURCE DATABASE (copy FROM)")
    print_stats(target_stats, "TARGET DATABASE (copy TO)")
    
    # Create backup
    if not args.dry_run and not args.no_backup:
        backup_path = args.target_db + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n💾 Creating backup: {backup_path}")
        shutil.copy2(args.target_db, backup_path)
        print("  ✅ Backup created")
    
    # Connect to databases
    source_conn = sqlite3.connect(args.source_db)
    target_conn = sqlite3.connect(args.target_db)
    
    # Merge all tables
    print("\n" + "="*70)
    print("🔄 MERGING DATA")
    print("="*70)
    
    games_added, scores_updated = merge_games(source_conn, target_conn, args.dry_run)
    teams_added = merge_teams(source_conn, target_conn, args.dry_run)
    ga_teams_added = merge_ga_teams(source_conn, target_conn, args.dry_run)
    urls_added = merge_discovered_urls(source_conn, target_conn, args.dry_run)
    
    # Commit and close
    if not args.dry_run:
        target_conn.commit()
    
    source_conn.close()
    target_conn.close()
    
    # Summary
    print("\n" + "="*70)
    print("📊 MERGE COMPLETE" if not args.dry_run else "📊 DRY RUN COMPLETE")
    print("="*70)
    print(f"  Games added: {games_added:,}")
    print(f"  Scores updated: {scores_updated:,}")
    print(f"  Teams added: {teams_added:,}")
    print(f"  GA Teams added: {ga_teams_added:,}")
    print(f"  URLs added: {urls_added:,}")
    
    if not args.dry_run:
        # Show final stats
        final_stats = get_db_stats(args.target_db)
        print_stats(final_stats, "FINAL TARGET DATABASE")
        
        print("\n✅ Merge complete! You can now delete the old database if desired.")
    else:
        print("\n🔍 Run without --dry-run to apply these changes.")


if __name__ == '__main__':
    main()
