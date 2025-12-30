"""
Cleanup Duplicate Games Script - V2

This script identifies and removes duplicate game entries where:
- Same two teams play on the same day (with normalized team name matching)
- Same age group
- Same scores (or reversed scores)

V2 Changes:
- Normalized team name matching to catch variants like:
  - "Beach FC" vs "Beach FC (CA)"
  - "Slammers FC" vs "Slammers FC HB Koge"
  - Team names with "NTX", "S.Cal", etc. suffixes

Author: Claude Code
Date: 2025-12-22
"""

import sqlite3
import argparse
import re
from collections import defaultdict


def normalize_team(name):
    """Normalize team name for duplicate comparison."""
    name = name.lower().strip()

    # Remove state/region suffixes
    name = re.sub(r'\s*\(ca\)\s*', ' ', name)
    name = re.sub(r'\s*\(va\)\s*', ' ', name)
    name = re.sub(r'\s*s\.?cal\s*', ' ', name)
    name = re.sub(r'\s*ntx\s*', ' ', name)
    name = re.sub(r'\s*stx\s*', ' ', name)
    name = re.sub(r'\s*stxcl\s*', ' ', name)
    name = re.sub(r'\s*hb koge\s*', ' ', name)

    # Remove ECNL RL team suffixes
    name = re.sub(r'\s*ecnl\s*rl\s*', ' ', name)
    name = re.sub(r'\s*g1[0-9]\s*', ' ', name)
    name = re.sub(r'\s*b1[0-9]\s*', ' ', name)

    # Remove Virginia prefix patterns
    name = re.sub(r'^virginia', '', name)

    # Remove extra spaces
    name = ' '.join(name.split())
    return name


def find_duplicates_with_normalization(cursor):
    """Find duplicates using normalized team names."""

    cursor.execute('''
        SELECT game_id, game_date, home_team, away_team, home_score, away_score,
               age_group, league, scraped_at
        FROM games
        WHERE home_score IS NOT NULL
    ''')

    games = cursor.fetchall()
    print(f"Total games to check: {len(games):,}")

    # Group by normalized key
    potential_dupes = defaultdict(list)
    for game in games:
        game_id, date, home, away, h_score, a_score, age, league, scraped_at = game
        # Key includes normalized team names
        key = (date, h_score, a_score, age, normalize_team(home), normalize_team(away))
        potential_dupes[key].append({
            'game_id': game_id,
            'home_team': home,
            'away_team': away,
            'league': league,
            'scraped_at': scraped_at or ''
        })

    # Filter to only groups with duplicates
    duplicates = {key: games for key, games in potential_dupes.items() if len(games) > 1}
    return duplicates


def find_duplicates(cursor):
    """Find exact duplicate game pairs (same home/away order, same scores)."""

    cursor.execute('''
        SELECT
            g1.game_id,
            g2.game_id,
            g1.game_date,
            g1.home_team,
            g1.away_team,
            g1.home_score,
            g1.away_score,
            g2.home_score,
            g2.away_score,
            g1.league,
            g1.age_group,
            'EXACT_DUP' as dup_type
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
            AND g1.home_score IS NOT NULL
    ''')

    return cursor.fetchall()

def find_swapped_duplicates(cursor):
    """Find duplicate game pairs where home/away are swapped AND scores are reversed.

    Only matches games where the scores are the mirror of each other,
    indicating the same game was scraped from both teams' perspectives.

    Example: Team A 3-1 Team B  AND  Team B 1-3 Team A  (same game, reversed)
    Does NOT match: Team A 3-1 Team B AND Team B 2-0 Team A (different games)
    """

    cursor.execute('''
        SELECT
            g1.game_id,
            g2.game_id,
            g1.game_date,
            g1.home_team,
            g1.away_team,
            g1.home_score,
            g1.away_score,
            g2.home_score,
            g2.away_score,
            g1.league,
            g1.age_group,
            'SWAPPED_REVERSED' as dup_type
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
            AND g1.home_score IS NOT NULL
    ''')

    return cursor.fetchall()

def score_game_id(game_id):
    """Score a game_id quality - higher is better."""
    score = 0

    # Longer IDs tend to be more complete
    score += len(game_id)

    # Check for malformed team names (missing letters, doubled underscores, etc.)
    if '__' in game_id:
        score -= 50

    # Check for truncated team names (like "oisetimbers" instead of "boisetimbers")
    # This is a heuristic - IDs that start with common prefixes are likely correct
    parts = game_id.split('_')
    for part in parts:
        if len(part) < 3 and part not in ['fc', 'sc', 'b', 'g']:
            score -= 10

    # IDs with ecnl/ecnlrl prefix are typically the correct format
    if game_id.startswith('ecnl_') or game_id.startswith('ecnlrl_'):
        score += 20

    return score

def decide_which_to_keep(game_id1, game_id2, score1, score2, rev_score1, rev_score2):
    """Decide which game to keep based on game_id quality and score consistency."""

    # Score the game IDs
    id1_score = score_game_id(game_id1)
    id2_score = score_game_id(game_id2)

    # If scores are the same (not reversed), just pick the better ID
    if score1 == rev_score1 and score2 == rev_score2:
        return (game_id2, "same scores, keeping better ID") if id1_score < id2_score else (game_id1, "same scores, keeping better ID")

    # If scores are reversed, pick the one with the better game_id
    if id1_score > id2_score:
        return (game_id2, f"keeping ID with score {id1_score} vs {id2_score}")
    else:
        return (game_id1, f"keeping ID with score {id2_score} vs {id1_score}")

def select_keeper(game_list):
    """
    Select which game to keep from a list of duplicates.
    Prefer:
    1. Games with state identifiers (CA/VA) over generic names
    2. Main leagues (ECNL, GA) over regional
    3. Longer team names (more specific)
    """
    def score_game(g):
        score = 0
        home = g['home_team']
        away = g['away_team']

        # Prefer games with state identifiers
        if '(CA)' in home or '(CA)' in away:
            score += 10
        if '(VA)' in home or '(VA)' in away:
            score += 10

        # Prefer longer names (more specific)
        score += len(home) + len(away)

        # Prefer main leagues
        if g['league'] in ['ECNL', 'GA', 'MLS NEXT']:
            score += 20
        elif g['league'] == 'ECNL RL':
            score += 10

        return score

    sorted_games = sorted(game_list, key=lambda g: (-score_game(g), g['scraped_at']))
    return sorted_games[0], sorted_games[1:]


def main():
    parser = argparse.ArgumentParser(description='Clean up duplicate games in database')
    parser.add_argument('--db', default='seedlinedata.db', help='Database file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--normalized', action='store_true', help='Use normalized team name matching (catches more duplicates)')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    print("=" * 60)
    print("DUPLICATE GAME CLEANUP")
    print("=" * 60)

    if args.normalized:
        print("Using NORMALIZED team name matching (catches name variants)")
        print()

        duplicates = find_duplicates_with_normalization(cursor)

        total_groups = len(duplicates)
        total_to_delete = sum(len(games) - 1 for games in duplicates.values())

        print(f"Duplicate groups found: {total_groups:,}")
        print(f"Records to delete: {total_to_delete:,}")
        print()

        if total_to_delete == 0:
            print("No duplicates found!")
            conn.close()
            return

        # Show some examples
        print("Sample duplicates (first 15):")
        print("-" * 60)
        to_delete = []

        for i, (key, game_list) in enumerate(duplicates.items()):
            keeper, dupes_to_remove = select_keeper(game_list)

            if i < 15:
                date, h_score, a_score, age, norm_home, norm_away = key
                print(f"{i+1}. {date} | {age} | Score: {h_score}-{a_score}")
                print(f"   KEEP: {keeper['home_team']} vs {keeper['away_team']} ({keeper['league']})")
                for d in dupes_to_remove:
                    print(f"   DEL:  {d['home_team']} vs {d['away_team']} ({d['league']})")
                print()

            for d in dupes_to_remove:
                to_delete.append(d['game_id'])

        print(f"\n{'='*60}")
        print(f"Total duplicates to delete: {len(to_delete):,}")

        if args.dry_run:
            print("\n*** DRY RUN - No changes made ***")
            print("Run without --dry-run to actually delete duplicates")
        else:
            if args.yes:
                confirm = 'yes'
            else:
                confirm = input("\nProceed with deletion? (yes/no): ")
            if confirm.lower() == 'yes':
                for game_id in to_delete:
                    cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
                conn.commit()
                print(f"\nDeleted {len(to_delete):,} duplicate games.")

                # Verify
                cursor.execute("SELECT COUNT(*) FROM games")
                remaining = cursor.fetchone()[0]
                print(f"Remaining games in database: {remaining:,}")
            else:
                print("\nAborted. No changes made.")

    else:
        print("Using EXACT team name matching")
        print("(Use --normalized to catch team name variants)")
        print()

        duplicates = find_duplicates(cursor)
        swapped_duplicates = find_swapped_duplicates(cursor)
        all_duplicates = duplicates + swapped_duplicates

        print(f"Found {len(duplicates)} exact duplicates (same scores)")
        print(f"Found {len(swapped_duplicates)} swapped/reversed duplicates")
        print(f"Total: {len(all_duplicates)} duplicate pairs to remove\n")

        if len(all_duplicates) == 0:
            print("No duplicates found!")
            conn.close()
            return

        to_delete = []

        for dup in all_duplicates[:50]:  # Show first 50
            game_id1, game_id2, game_date, home, away, score1_h, score1_a, score2_h, score2_a, league, age_group, dup_type = dup

            delete_id, reason = decide_which_to_keep(
                game_id1, game_id2,
                (score1_h, score1_a), (score2_h, score2_a),
                (score2_h, score2_a), (score1_h, score1_a)
            )

            to_delete.append(delete_id)

            print(f"{game_date} | {home[:30]} vs {away[:30]} | {league} {age_group}")
            print(f"  Deleting: {delete_id[:50]}...")
            print()

        # Process rest without printing
        for dup in all_duplicates[50:]:
            game_id1, game_id2, game_date, home, away, score1_h, score1_a, score2_h, score2_a, league, age_group, dup_type = dup
            delete_id, reason = decide_which_to_keep(
                game_id1, game_id2,
                (score1_h, score1_a), (score2_h, score2_a),
                (score2_h, score2_a), (score1_h, score1_a)
            )
            to_delete.append(delete_id)

        print(f"\n{'='*60}")
        print(f"Total duplicates to delete: {len(to_delete)}")

        if args.dry_run:
            print("\n*** DRY RUN - No changes made ***")
        else:
            if args.yes:
                confirm = 'yes'
            else:
                confirm = input("\nProceed with deletion? (yes/no): ")
            if confirm.lower() == 'yes':
                for game_id in to_delete:
                    cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
                conn.commit()
                print(f"\nDeleted {len(to_delete)} duplicate games.")
            else:
                print("\nAborted. No changes made.")

    conn.close()


if __name__ == '__main__':
    main()
