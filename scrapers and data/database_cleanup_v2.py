"""
Database Cleanup Script v2

Cleans the seedlinedata.db database by removing/fixing:
1. Self-play games (team playing itself)
2. Exact duplicate games (same teams, date, scores)
3. Reversed-score duplicates (same game scraped from both teams)
4. Cross-league duplicates (same game in ECNL and ECNL-RL)
5. Games with invalid team names
6. Completed games with NULL scores (fix status)

Does NOT remove:
- Old games (historical data may be valuable)
- Different-score same-day games (legitimate tournament double-headers)

Author: Claude Code
Date: 2025-12-21
"""

import sqlite3
import argparse
from datetime import datetime


def cleanup_self_play(cursor, dry_run=False):
    """Remove games where a team plays itself."""
    cursor.execute('''
        SELECT game_id, game_date, home_team, home_score, away_score, league, age_group
        FROM games
        WHERE home_team = away_team AND game_status = 'completed'
    ''')
    games = cursor.fetchall()

    print(f"\n1. SELF-PLAY GAMES: {len(games)}")
    if games:
        for g in games[:5]:
            print(f"   {g[1]} | {g[2]} vs itself | {g[3]}-{g[4]} | {g[5]} {g[6]}")
        if len(games) > 5:
            print(f"   ... and {len(games) - 5} more")

        if not dry_run:
            cursor.execute('''
                DELETE FROM games WHERE home_team = away_team AND game_status = 'completed'
            ''')
            print(f"   DELETED {len(games)} self-play games")

    return len(games)


def cleanup_exact_duplicates(cursor, dry_run=False):
    """Remove exact duplicate games (same teams, date, scores, league)."""
    cursor.execute('''
        SELECT g2.game_id, g1.game_date, g1.home_team, g1.away_team,
               g1.home_score, g1.away_score, g1.league, g1.age_group
        FROM games g1
        JOIN games g2 ON g1.game_date = g2.game_date
            AND g1.home_team = g2.home_team
            AND g1.away_team = g2.away_team
            AND g1.age_group = g2.age_group
            AND g1.league = g2.league
            AND g1.home_score = g2.home_score
            AND g1.away_score = g2.away_score
            AND g1.game_id < g2.game_id
        WHERE g1.game_status = 'completed' AND g2.game_status = 'completed'
    ''')
    duplicates = cursor.fetchall()

    print(f"\n2. EXACT DUPLICATES: {len(duplicates)}")
    if duplicates:
        for d in duplicates[:5]:
            print(f"   {d[1]} | {d[2]} vs {d[3]} | {d[4]}-{d[5]} | {d[6]} {d[7]}")
        if len(duplicates) > 5:
            print(f"   ... and {len(duplicates) - 5} more")

        if not dry_run:
            game_ids = [d[0] for d in duplicates]
            cursor.executemany('DELETE FROM games WHERE game_id = ?', [(gid,) for gid in game_ids])
            print(f"   DELETED {len(duplicates)} exact duplicates")

    return len(duplicates)


def cleanup_reversed_duplicates(cursor, dry_run=False):
    """Remove reversed-score duplicates (same game, home/away swapped with reversed scores)."""
    cursor.execute('''
        SELECT g2.game_id, g1.game_date, g1.home_team, g1.away_team,
               g1.home_score, g1.away_score, g2.home_score, g2.away_score,
               g1.league, g1.age_group
        FROM games g1
        JOIN games g2 ON g1.game_date = g2.game_date
            AND g1.home_team = g2.away_team
            AND g1.away_team = g2.home_team
            AND g1.age_group = g2.age_group
            AND g1.league = g2.league
            AND g1.home_score = g2.away_score
            AND g1.away_score = g2.home_score
            AND g1.game_id < g2.game_id
        WHERE g1.game_status = 'completed' AND g2.game_status = 'completed'
    ''')
    duplicates = cursor.fetchall()

    print(f"\n3. REVERSED-SCORE DUPLICATES: {len(duplicates)}")
    if duplicates:
        for d in duplicates[:5]:
            print(f"   {d[1]} | {d[2]} {d[4]}-{d[5]} {d[3]} == {d[3]} {d[6]}-{d[7]} {d[2]}")
        if len(duplicates) > 5:
            print(f"   ... and {len(duplicates) - 5} more")

        if not dry_run:
            game_ids = [d[0] for d in duplicates]
            cursor.executemany('DELETE FROM games WHERE game_id = ?', [(gid,) for gid in game_ids])
            print(f"   DELETED {len(duplicates)} reversed duplicates")

    return len(duplicates)


def cleanup_cross_league_duplicates(cursor, dry_run=False):
    """Remove cross-league duplicates (same game appearing in both ECNL and ECNL-RL).

    Keeps the ECNL version if available, otherwise keeps the first one found.
    """
    cursor.execute('''
        SELECT g2.game_id, g1.game_date, g1.home_team, g1.away_team,
               g1.home_score, g1.away_score, g1.league, g2.league, g1.age_group
        FROM games g1
        JOIN games g2 ON g1.game_date = g2.game_date
            AND g1.home_team = g2.home_team
            AND g1.away_team = g2.away_team
            AND g1.age_group = g2.age_group
            AND g1.home_score = g2.home_score
            AND g1.away_score = g2.away_score
            AND g1.league != g2.league
            AND g1.game_id < g2.game_id
        WHERE g1.game_status = 'completed' AND g2.game_status = 'completed'
    ''')
    duplicates = cursor.fetchall()

    print(f"\n4. CROSS-LEAGUE DUPLICATES: {len(duplicates)}")
    if duplicates:
        # Show breakdown by league pair
        league_pairs = {}
        for d in duplicates:
            pair = f"{d[6]} vs {d[7]}"
            league_pairs[pair] = league_pairs.get(pair, 0) + 1
        for pair, count in sorted(league_pairs.items(), key=lambda x: -x[1])[:5]:
            print(f"   {pair}: {count}")

        for d in duplicates[:3]:
            print(f"   {d[1]} | {d[2]} vs {d[3]} | {d[4]}-{d[5]} | {d[6]} & {d[7]}")

        if not dry_run:
            # Prefer keeping ECNL over ECNL-RL, otherwise keep the first
            to_delete = []
            for d in duplicates:
                g2_id, date, home, away, h_score, a_score, league1, league2, age = d
                # g2 is the one we're considering deleting
                # If g1 is ECNL and g2 is ECNL-RL, delete g2
                # If g1 is ECNL-RL and g2 is ECNL, we want to keep g2 (so don't add to delete)
                if 'ECNL' in league1 and 'RL' not in league1 and 'RL' in league2:
                    to_delete.append(g2_id)
                elif 'RL' in league1 and 'ECNL' in league2 and 'RL' not in league2:
                    # g2 is the main ECNL, don't delete it - but we already counted this pair
                    # Actually this case won't happen because g1.game_id < g2.game_id
                    pass
                else:
                    # Other league combos - just delete the second one
                    to_delete.append(g2_id)

            cursor.executemany('DELETE FROM games WHERE game_id = ?', [(gid,) for gid in to_delete])
            print(f"   DELETED {len(to_delete)} cross-league duplicates")

    return len(duplicates)


def cleanup_bad_team_names(cursor, dry_run=False):
    """Remove games with invalid team names (timestamps, null, too short)."""
    cursor.execute('''
        SELECT game_id, game_date, home_team, away_team, league
        FROM games
        WHERE game_status = 'completed'
        AND (
            home_team IS NULL OR away_team IS NULL
            OR LENGTH(TRIM(home_team)) < 3
            OR LENGTH(TRIM(away_team)) < 3
            OR home_team LIKE '%PM #%'
            OR away_team LIKE '%PM #%'
            OR home_team LIKE '%AM #%'
            OR away_team LIKE '%AM #%'
        )
    ''')
    bad_games = cursor.fetchall()

    print(f"\n5. BAD TEAM NAMES: {len(bad_games)}")
    if bad_games:
        for g in bad_games[:5]:
            print(f"   {g[1]} | '{g[2]}' vs '{g[3]}' | {g[4]}")
        if len(bad_games) > 5:
            print(f"   ... and {len(bad_games) - 5} more")

        if not dry_run:
            game_ids = [g[0] for g in bad_games]
            cursor.executemany('DELETE FROM games WHERE game_id = ?', [(gid,) for gid in game_ids])
            print(f"   DELETED {len(bad_games)} games with bad team names")

    return len(bad_games)


def fix_invalid_completed_games(cursor, dry_run=False):
    """Fix games marked as completed but missing scores (change status to unknown)."""
    cursor.execute('''
        SELECT game_id, game_date, home_team, away_team, home_score, away_score
        FROM games
        WHERE game_status = 'completed'
        AND (home_score IS NULL OR away_score IS NULL)
    ''')
    bad_games = cursor.fetchall()

    print(f"\n6. COMPLETED GAMES WITH NULL SCORES: {len(bad_games)}")
    if bad_games:
        for g in bad_games[:5]:
            print(f"   {g[1]} | {g[2]} vs {g[3]} | {g[4]}-{g[5]}")
        if len(bad_games) > 5:
            print(f"   ... and {len(bad_games) - 5} more")

        if not dry_run:
            cursor.execute('''
                UPDATE games SET game_status = 'unknown'
                WHERE game_status = 'completed'
                AND (home_score IS NULL OR away_score IS NULL)
            ''')
            print(f"   FIXED {len(bad_games)} games (status -> unknown)")

    return len(bad_games)


def main():
    parser = argparse.ArgumentParser(description='Clean up the seedline database')
    parser.add_argument('--db', default='seedlinedata.db', help='Database file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("DATABASE CLEANUP v2")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Get initial counts
    cursor.execute("SELECT COUNT(*) FROM games WHERE game_status = 'completed'")
    initial_count = cursor.fetchone()[0]
    print(f"\nInitial completed games: {initial_count:,}")

    # Run all cleanup operations
    total_removed = 0
    total_removed += cleanup_self_play(cursor, args.dry_run)
    total_removed += cleanup_exact_duplicates(cursor, args.dry_run)
    total_removed += cleanup_reversed_duplicates(cursor, args.dry_run)
    total_removed += cleanup_cross_league_duplicates(cursor, args.dry_run)
    total_removed += cleanup_bad_team_names(cursor, args.dry_run)
    fixed = fix_invalid_completed_games(cursor, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if args.dry_run:
        print(f"Would remove: {total_removed:,} games")
        print(f"Would fix: {fixed:,} games")
        print("\n*** DRY RUN - No changes made ***")
    else:
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM games WHERE game_status = 'completed'")
        final_count = cursor.fetchone()[0]
        print(f"Removed: {total_removed:,} games")
        print(f"Fixed: {fixed:,} games")
        print(f"Final completed games: {final_count:,}")
        print("\nDatabase cleanup complete!")

    conn.close()


if __name__ == '__main__':
    main()
