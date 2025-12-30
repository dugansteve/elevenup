"""
Export Conference Games to JSON
Generates a JSON file with all conference games for use in the React simulation.
This allows the frontend to use actual game results instead of re-simulating everything.

Run this after running the ranker to keep game data in sync with rankings.
"""

import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict

# Configuration
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
OUTPUT_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\conference_games.json"
SEASON_START_DATE = datetime(2025, 8, 1)  # Games before this date are previous season


def parse_game_date(date_str):
    """Parse a date string in various formats to a datetime object."""
    if not date_str:
        return None

    # Try ISO format first (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        pass

    # Try "Mon D, YYYY" format (e.g., "Sep 6, 2025")
    try:
        return datetime.strptime(date_str, '%b %d, %Y')
    except ValueError:
        pass

    # Try "Mon DD, YYYY" format
    try:
        return datetime.strptime(date_str, '%b %d, %Y')
    except ValueError:
        pass

    return None

# Excluded placeholder teams
EXCLUDED_TEAMS = {'TBDG', 'TBD', 'TBA', 'BYE'}

# League name normalization to match rankings format
# IMPORTANT: Keep this in sync with team_ranker_final.py (line ~1391)
# The ranker normalizes league names - this export must use the same names
LEAGUE_NAME_MAP = {
    'ECNL RL': 'ECNL-RL',  # Database uses space, rankings uses hyphen
}


def normalize_league_name(league):
    """Normalize league name to match rankings format."""
    return LEAGUE_NAME_MAP.get(league, league)

# Tournament/showcase keywords to exclude from conference simulations
# These are NOT regular conference games
TOURNAMENT_KEYWORDS = [
    'champions cup', 'showcase', 'playoffs', 'finals', 'tournament',
    'classic', 'cup', 'invitational', 'national event'
]

# Event types that indicate non-conference games
NON_CONFERENCE_EVENT_TYPES = ['CHAMPIONS_CUP', 'PLAYOFFS', 'FINALS', 'REGIONAL', 'SHOWCASE']


def is_conference_game(conference, event_type):
    """
    Determine if a game is a regular conference game vs tournament/showcase.
    Returns True for regular conference games, False for tournaments.
    """
    # If event_type indicates non-conference, exclude it
    if event_type and event_type.upper() in NON_CONFERENCE_EVENT_TYPES:
        return False

    # If event_type is LEAGUE, it's definitely a conference game
    if event_type and event_type.upper() == 'LEAGUE':
        return True

    # For NULL event_type, check conference name for tournament keywords
    if conference:
        conf_lower = conference.lower()
        for keyword in TOURNAMENT_KEYWORDS:
            if keyword in conf_lower:
                return False

    # Default to True for regular conference names
    return True


def get_conference_games(cursor):
    """Get all completed conference games with scores (current season only).
    Excludes tournament/showcase games - only returns regular conference play."""
    cursor.execute('''
        SELECT
            game_id,
            game_date,
            home_team,
            away_team,
            home_score,
            away_score,
            league,
            age_group,
            conference,
            gender,
            event_type
        FROM games
        WHERE home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND game_status = 'completed'
          AND home_team NOT IN ('TBDG', 'TBD', 'TBA', 'BYE')
          AND away_team NOT IN ('TBDG', 'TBD', 'TBA', 'BYE')
          AND conference IS NOT NULL
          AND conference != ''
        ORDER BY league, age_group, conference, game_date
    ''')

    games = []
    tournament_excluded = 0
    for row in cursor.fetchall():
        conference = row[8]
        event_type = row[10]

        # Parse and filter by date
        game_date = parse_game_date(row[1])
        if game_date and game_date < SEASON_START_DATE:
            continue  # Skip games before season start

        # Filter out tournament/showcase games
        if not is_conference_game(conference, event_type):
            tournament_excluded += 1
            continue

        # Parse scores safely (handle None, empty string, string numbers)
        try:
            home_score = int(row[4]) if row[4] not in (None, '') else 0
        except (ValueError, TypeError):
            home_score = 0
        try:
            away_score = int(row[5]) if row[5] not in (None, '') else 0
        except (ValueError, TypeError):
            away_score = 0

        games.append({
            'gameId': row[0],
            'date': row[1],
            'homeTeam': row[2],
            'awayTeam': row[3],
            'homeScore': home_score,
            'awayScore': away_score,
            'league': normalize_league_name(row[6]),
            'ageGroup': row[7],
            'conference': row[8],
            'gender': row[9],
            'eventType': row[10]
        })

    print(f"  Excluded {tournament_excluded:,} tournament/showcase games")
    return games


def get_conference_schedule(cursor):
    """Get upcoming/unplayed conference games (current season only).
    Excludes tournament/showcase games - only returns regular conference play."""
    cursor.execute('''
        SELECT
            game_id,
            game_date,
            home_team,
            away_team,
            league,
            age_group,
            conference,
            gender,
            event_type
        FROM games
        WHERE (home_score IS NULL OR away_score IS NULL OR game_status != 'completed')
          AND home_team NOT IN ('TBDG', 'TBD', 'TBA', 'BYE')
          AND away_team NOT IN ('TBDG', 'TBD', 'TBA', 'BYE')
          AND conference IS NOT NULL
          AND conference != ''
        ORDER BY league, age_group, conference, game_date
    ''')

    schedule = []
    tournament_excluded = 0
    for row in cursor.fetchall():
        conference = row[6]
        event_type = row[8]

        # Parse and filter by date
        game_date = parse_game_date(row[1])
        if game_date and game_date < SEASON_START_DATE:
            continue  # Skip games before season start

        # Filter out tournament/showcase games
        if not is_conference_game(conference, event_type):
            tournament_excluded += 1
            continue

        schedule.append({
            'gameId': row[0],
            'date': row[1],
            'homeTeam': row[2],
            'awayTeam': row[3],
            'league': normalize_league_name(row[4]),
            'ageGroup': row[5],
            'conference': row[6],
            'gender': row[7],
            'eventType': row[8]
        })

    print(f"  Excluded {tournament_excluded:,} tournament/showcase scheduled games")
    return schedule


def get_teams_by_conference(cursor):
    """Get all teams grouped by conference."""
    cursor.execute('''
        SELECT DISTINCT
            team_name,
            league,
            age_group,
            conference,
            gender
        FROM teams
        WHERE conference IS NOT NULL AND conference != ''
        ORDER BY league, age_group, conference, team_name
    ''')

    teams = defaultdict(list)
    for row in cursor.fetchall():
        league = normalize_league_name(row[1])
        key = f"{league}|{row[2]}|{row[3]}"  # league|age_group|conference
        teams[key].append({
            'name': row[0],
            'league': league,
            'ageGroup': row[2],
            'conference': row[3],
            'gender': row[4]
        })

    return dict(teams)


def build_conference_standings(games):
    """Calculate current standings from played games."""
    standings = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'draws': 0,
        'goalsFor': 0, 'goalsAgainst': 0, 'points': 0,
        'gamesPlayed': []
    })

    for game in games:
        conf_key = f"{game['league']}|{game['ageGroup']}|{game['conference']}"
        home = game['homeTeam']
        away = game['awayTeam']
        home_score = game['homeScore']
        away_score = game['awayScore']

        # Update home team
        home_key = f"{conf_key}|{home}"
        standings[home_key]['goalsFor'] += home_score
        standings[home_key]['goalsAgainst'] += away_score
        standings[home_key]['gamesPlayed'].append(game['gameId'])

        # Update away team
        away_key = f"{conf_key}|{away}"
        standings[away_key]['goalsFor'] += away_score
        standings[away_key]['goalsAgainst'] += home_score
        standings[away_key]['gamesPlayed'].append(game['gameId'])

        # Determine winner
        if home_score > away_score:
            standings[home_key]['wins'] += 1
            standings[home_key]['points'] += 3
            standings[away_key]['losses'] += 1
        elif away_score > home_score:
            standings[away_key]['wins'] += 1
            standings[away_key]['points'] += 3
            standings[home_key]['losses'] += 1
        else:
            standings[home_key]['draws'] += 1
            standings[home_key]['points'] += 1
            standings[away_key]['draws'] += 1
            standings[away_key]['points'] += 1

    return dict(standings)


def main():
    print("=" * 70)
    print("CONFERENCE GAMES EXPORT")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Season Start: {SEASON_START_DATE.strftime('%Y-%m-%d')} (games before this date excluded)")
    print()

    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get data
    print("Fetching completed games...")
    completed_games = get_conference_games(cursor)
    print(f"  Found {len(completed_games):,} completed conference games")

    print("Fetching upcoming schedule...")
    upcoming_games = get_conference_schedule(cursor)
    print(f"  Found {len(upcoming_games):,} upcoming/unplayed games")

    print("Building standings from played games...")
    standings = build_conference_standings(completed_games)

    # Organize by conference
    games_by_conference = defaultdict(list)
    for game in completed_games:
        key = f"{game['league']}|{game['ageGroup']}|{game['conference']}"
        games_by_conference[key].append(game)

    schedule_by_conference = defaultdict(list)
    for game in upcoming_games:
        key = f"{game['league']}|{game['ageGroup']}|{game['conference']}"
        schedule_by_conference[key].append(game)

    # Build output structure
    output = {
        'exportedAt': datetime.now().isoformat(),
        'totalCompletedGames': len(completed_games),
        'totalUpcomingGames': len(upcoming_games),
        'completedGames': completed_games,
        'upcomingGames': upcoming_games,
        'conferenceKeys': list(set(games_by_conference.keys()) | set(schedule_by_conference.keys()))
    }

    # Stats by league
    league_stats = defaultdict(lambda: {'completed': 0, 'upcoming': 0})
    for game in completed_games:
        league_stats[game['league']]['completed'] += 1
    for game in upcoming_games:
        league_stats[game['league']]['upcoming'] += 1

    print()
    print("Games by league:")
    for league in sorted(league_stats.keys()):
        stats = league_stats[league]
        print(f"  {league}: {stats['completed']:,} completed, {stats['upcoming']:,} upcoming")

    # Write output
    print()
    print(f"Writing to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    file_size = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"  File size: {file_size:.1f} KB")

    conn.close()

    print()
    print("=" * 70)
    print("EXPORT COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
