"""
Conference Simulator - Proof of Concept
Monte Carlo simulation for predicting conference outcomes

This script demonstrates how to:
1. Pull team rankings and game data from the database
2. Run Monte Carlo simulations for remaining games
3. Calculate probabilities for each team's finish position
4. Generate structured output ready for Claude narrative generation
"""

import sqlite3
import json
import numpy as np
from collections import defaultdict
from datetime import datetime
import os

# Configuration
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
RANKINGS_JSON = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\rankings_for_react.json"
N_SIMULATIONS = 10000
HOME_ADVANTAGE = 30  # Rating points boost for home team
SEASON_START_DATE = '2025-08-01'  # Games before this date are previous season

# Teams to exclude from analysis
EXCLUDED_TEAMS = {'TBDG', 'TBD', 'TBA', 'BYE'}  # Placeholder team names


def load_rankings():
    """Load team rankings from JSON file."""
    with open(RANKINGS_JSON, 'r') as f:
        data = json.load(f)

    # Create lookup by team name
    rankings = {}
    for team in data['teamsData']:
        # Normalize name for matching
        name_key = team['name'].lower().strip()
        rankings[name_key] = {
            'name': team['name'],
            'power_score': team['powerScore'],
            'predictability': team.get('predictability', 70) / 100,  # Convert to 0-1
            'wins': team['wins'],
            'losses': team['losses'],
            'draws': team['draws'],
            'league': team['league'],
            'age_group': team['ageGroup'],
        }

    return rankings


def get_conference_teams(conn, league, age_group, conference, min_conference_games=3):
    """
    Get teams that primarily belong to this conference.

    A team is included if:
    1. They have at least min_conference_games in this conference
    2. This conference is their primary conference (most games)
    3. They are not a placeholder team (TBDG, TBD, etc.)
    """
    cursor = conn.cursor()

    # Get all teams that appear in this conference with their game counts
    cursor.execute('''
        WITH conference_teams AS (
            SELECT home_team as team FROM games
            WHERE league = ? AND age_group = ? AND conference = ?
            UNION ALL
            SELECT away_team as team FROM games
            WHERE league = ? AND age_group = ? AND conference = ?
        ),
        team_counts AS (
            SELECT team, COUNT(*) as conf_games
            FROM conference_teams
            GROUP BY team
        )
        SELECT team, conf_games FROM team_counts
        WHERE conf_games >= ?
        ORDER BY conf_games DESC
    ''', (league, age_group, conference, league, age_group, conference, min_conference_games))

    candidate_teams = [(row[0], row[1]) for row in cursor.fetchall()]

    # Filter to only teams where this is their primary conference
    primary_conference_teams = []
    for team, conf_games in candidate_teams:
        # Skip placeholder teams
        if team in EXCLUDED_TEAMS:
            continue

        # Check if this is their primary conference
        cursor.execute('''
            SELECT conference, COUNT(*) as cnt
            FROM games
            WHERE (home_team = ? OR away_team = ?)
            AND league = ? AND age_group = ?
            AND conference IS NOT NULL AND conference != ''
            GROUP BY conference
            ORDER BY cnt DESC
            LIMIT 1
        ''', (team, team, league, age_group))

        result = cursor.fetchone()
        if result and result[0] == conference:
            primary_conference_teams.append(team)

    return primary_conference_teams


def get_conference_games(conn, league, age_group, conference, conference_teams=None, season_start=SEASON_START_DATE):
    """
    Get all games for a conference, split into completed and remaining.

    If conference_teams is provided, only includes games where BOTH teams
    are in the conference (filters out cross-conference showcase games).
    Also excludes games involving placeholder teams (TBDG, etc.).
    Games before season_start are excluded (previous season).
    """
    cursor = conn.cursor()

    cursor.execute('''
        SELECT game_date, home_team, away_team, home_score, away_score
        FROM games
        WHERE league = ? AND age_group = ? AND conference = ?
        AND game_date >= ?
        ORDER BY game_date
    ''', (league, age_group, conference, season_start))

    completed = []
    remaining = []

    for row in cursor.fetchall():
        home_team = row[1]
        away_team = row[2]

        # Skip games with placeholder teams
        if home_team in EXCLUDED_TEAMS or away_team in EXCLUDED_TEAMS:
            continue

        # If conference_teams provided, only include games where both teams are in conference
        if conference_teams:
            if home_team not in conference_teams or away_team not in conference_teams:
                continue

        game = {
            'date': row[0],
            'home': home_team,
            'away': away_team,
            'home_score': row[3],
            'away_score': row[4]
        }

        # Check if game has been played (has scores)
        if row[3] is not None and row[4] is not None:
            completed.append(game)
        else:
            remaining.append(game)

    return completed, remaining


def calculate_current_standings(completed_games, teams):
    """Calculate current standings from completed games."""
    standings = {team: {'points': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                        'gf': 0, 'ga': 0, 'gd': 0, 'played': 0}
                 for team in teams}

    for game in completed_games:
        home = game['home']
        away = game['away']
        home_score = game['home_score']
        away_score = game['away_score']

        if home not in standings or away not in standings:
            continue

        standings[home]['played'] += 1
        standings[away]['played'] += 1
        standings[home]['gf'] += home_score
        standings[home]['ga'] += away_score
        standings[away]['gf'] += away_score
        standings[away]['ga'] += home_score

        if home_score > away_score:
            standings[home]['wins'] += 1
            standings[home]['points'] += 3
            standings[away]['losses'] += 1
        elif away_score > home_score:
            standings[away]['wins'] += 1
            standings[away]['points'] += 3
            standings[home]['losses'] += 1
        else:
            standings[home]['draws'] += 1
            standings[away]['draws'] += 1
            standings[home]['points'] += 1
            standings[away]['points'] += 1

    for team in standings:
        standings[team]['gd'] = standings[team]['gf'] - standings[team]['ga']
        # Calculate points per game
        if standings[team]['played'] > 0:
            standings[team]['ppg'] = standings[team]['points'] / standings[team]['played']
        else:
            standings[team]['ppg'] = 0

    return standings


def match_team_to_rankings(team_name, rankings, league, age_group):
    """Try to match a team name from games to rankings data."""
    # Try exact match first
    name_key = team_name.lower().strip()
    if name_key in rankings:
        return rankings[name_key]

    # Try matching with league/age suffix patterns
    # e.g., "Eclipse Select SC" might be "Eclipse Select SC ECNL G13" in rankings
    for pattern in [f"{team_name} {league} {age_group}",
                    f"{team_name} {age_group}",
                    f"{team_name}"]:
        key = pattern.lower().strip()
        if key in rankings:
            return rankings[key]

    # Try partial match
    for key, data in rankings.items():
        if team_name.lower() in key or key in team_name.lower():
            if data['league'] == league and data['age_group'] == age_group:
                return data

    # Return default values if no match
    return {
        'name': team_name,
        'power_score': 1500,  # Default rating
        'predictability': 0.70,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'league': league,
        'age_group': age_group,
    }


def calculate_win_probability(home_power, away_power, home_advantage=HOME_ADVANTAGE):
    """
    Calculate win/draw/loss probabilities using Elo-style formula.
    """
    adjusted_home = home_power + home_advantage
    rating_diff = adjusted_home - away_power

    # Elo expected score
    expected_home = 1 / (1 + 10 ** (-rating_diff / 400))

    # Draw probability - higher when teams are close
    draw_base = 0.26  # Soccer averages ~26% draws
    draw_prob = draw_base * (1 - abs(expected_home - 0.5) * 1.2)
    draw_prob = max(0.12, min(0.35, draw_prob))

    # Remaining probability split by expected score
    remaining = 1 - draw_prob
    win_home = remaining * expected_home
    win_away = remaining * (1 - expected_home)

    return win_home, draw_prob, win_away


def add_uncertainty(power_score, predictability, game_idx=0):
    """
    Add random variance based on predictability.
    Less predictable teams have higher variance.
    """
    # Base std dev: predictability=1.0 -> std=25, predictability=0.5 -> std=75
    base_std = 25 + 100 * (1 - predictability)

    # Slight increase for games further in future
    time_factor = 1 + (game_idx * 0.01)
    std = base_std * time_factor

    return np.random.normal(power_score, std)


def run_simulation(teams_data, current_standings, remaining_games, n_sims=N_SIMULATIONS):
    """
    Run Monte Carlo simulation for remaining season.
    Uses points per game (PPG) to determine standings (accounts for uneven schedules).
    """
    # Track results
    final_positions = defaultdict(list)
    final_points = defaultdict(list)
    final_ppg = defaultdict(list)  # Points per game
    conference_winners = defaultdict(int)

    team_names = list(current_standings.keys())

    for sim in range(n_sims):
        # Start with current points and games played
        sim_points = {team: current_standings[team]['points'] for team in team_names}
        sim_games = {team: current_standings[team]['played'] for team in team_names}

        # Simulate each remaining game
        for game_idx, game in enumerate(remaining_games):
            home = game['home']
            away = game['away']

            if home not in teams_data or away not in teams_data:
                continue

            # Track games played
            sim_games[home] += 1
            sim_games[away] += 1

            # Get power scores with uncertainty
            home_power = add_uncertainty(
                teams_data[home]['power_score'],
                teams_data[home]['predictability'],
                game_idx
            )
            away_power = add_uncertainty(
                teams_data[away]['power_score'],
                teams_data[away]['predictability'],
                game_idx
            )

            # Calculate probabilities
            p_home_win, p_draw, p_away_win = calculate_win_probability(home_power, away_power)

            # Simulate outcome
            rand = np.random.random()
            if rand < p_home_win:
                sim_points[home] += 3
            elif rand < p_home_win + p_draw:
                sim_points[home] += 1
                sim_points[away] += 1
            else:
                sim_points[away] += 3

        # Calculate points per game for each team
        sim_ppg = {}
        for team in team_names:
            if sim_games[team] > 0:
                sim_ppg[team] = sim_points[team] / sim_games[team]
            else:
                sim_ppg[team] = 0

        # Sort by points per game (and goal diff as tiebreaker)
        sorted_teams = sorted(
            sim_ppg.items(),
            key=lambda x: (x[1], current_standings[x[0]]['gd']),
            reverse=True
        )

        # Record positions
        for pos, (team, ppg) in enumerate(sorted_teams, 1):
            final_positions[team].append(pos)
            final_points[team].append(sim_points[team])
            final_ppg[team].append(ppg)

        # Track winner
        conference_winners[sorted_teams[0][0]] += 1

    return final_positions, final_points, final_ppg, conference_winners


def calculate_results(final_positions, final_points, final_ppg, conference_winners, n_sims):
    """
    Calculate statistics from simulation results.
    """
    results = {}
    n_teams = len(final_positions)

    for team in final_positions:
        positions = final_positions[team]
        points = final_points[team]
        ppg = final_ppg[team]

        # Position distribution
        pos_dist = {}
        for p in range(1, n_teams + 1):
            count = positions.count(p)
            pos_dist[p] = round(count / n_sims * 100, 1)

        results[team] = {
            'win_conference_pct': round(conference_winners[team] / n_sims * 100, 1),
            'expected_position': round(np.mean(positions), 2),
            'position_std_dev': round(np.std(positions), 2),
            'position_distribution': pos_dist,
            'expected_points': round(np.mean(points), 1),
            'points_std_dev': round(np.std(points), 1),
            'points_90_ci': (int(np.percentile(points, 5)), int(np.percentile(points, 95))),
            'expected_ppg': round(np.mean(ppg), 2),
            'ppg_std_dev': round(np.std(ppg), 2),
            'top_4_pct': round(sum(1 for p in positions if p <= 4) / n_sims * 100, 1),
            'top_half_pct': round(sum(1 for p in positions if p <= n_teams // 2) / n_sims * 100, 1),
        }

    return results


def format_standings_table(standings, teams_data=None):
    """Format current standings as a table with overall and league records. Sorted by PPG."""
    # Sort by PPG (points per game), then goal diff as tiebreaker
    sorted_standings = sorted(
        standings.items(),
        key=lambda x: (x[1]['ppg'], x[1]['gd']),
        reverse=True
    )

    lines = []
    # Header with Overall Record and League Record
    lines.append(f"{'Pos':<4}{'Team':<30}{'Overall':>12}  {'League Record':>16}{'GD':>5}{'Pts':>5}{'PPG':>6}")
    lines.append(f"{'':4}{'':30}{'(W-L-D)':>12}  {'P':>4}{'W':>4}{'D':>4}{'L':>4}{'':>5}{'':>5}{'':>6}")
    lines.append("-" * 86)

    for pos, (team, data) in enumerate(sorted_standings, 1):
        # Get overall record from teams_data if available
        if teams_data and team in teams_data:
            overall_w = teams_data[team].get('wins', 0)
            overall_l = teams_data[team].get('losses', 0)
            overall_d = teams_data[team].get('draws', 0)
            overall_str = f"{overall_w}-{overall_l}-{overall_d}"
        else:
            overall_str = "---"

        lines.append(
            f"{pos:<4}{team[:28]:<30}{overall_str:>12}  "
            f"{data['played']:>4}{data['wins']:>4}{data['draws']:>4}{data['losses']:>4}"
            f"{data['gd']:>+5}{data['points']:>5}{data['ppg']:>6.2f}"
        )

    return "\n".join(lines)


def format_simulation_results(results, current_standings):
    """Format simulation results as a table."""
    # Sort by expected position
    sorted_results = sorted(results.items(), key=lambda x: x[1]['expected_position'])

    lines = []
    lines.append(f"\n{'Team':<35}{'Win%':>7}{'Exp Pos':>9}{'Exp PPG':>9}{'Top 4%':>8}")
    lines.append("-" * 70)

    for team, data in sorted_results:
        lines.append(
            f"{team[:33]:<35}{data['win_conference_pct']:>6.1f}%"
            f"{data['expected_position']:>9.2f}{data['expected_ppg']:>9.2f}"
            f"{data['top_4_pct']:>7.1f}%"
        )

    return "\n".join(lines)


def format_remaining_games_predictions(remaining_games, teams_data):
    """Format predicted results for remaining games based on team power scores."""
    lines = []
    lines.append(f"\n{'Date':<12}{'Home Team':<28}{'Away Team':<28}{'Prediction':>12}")
    lines.append("-" * 82)

    for game in remaining_games:
        home = game['home']
        away = game['away']
        date = game['date']

        # Get power scores
        home_power = teams_data.get(home, {}).get('power_score', 1500)
        away_power = teams_data.get(away, {}).get('power_score', 1500)

        # Calculate win probabilities
        p_home_win, p_draw, p_away_win = calculate_win_probability(home_power, away_power)

        # Determine prediction
        if p_home_win > p_away_win + 0.15:
            prediction = f"Home ({p_home_win*100:.0f}%)"
        elif p_away_win > p_home_win + 0.15:
            prediction = f"Away ({p_away_win*100:.0f}%)"
        else:
            prediction = f"Toss-up"

        lines.append(
            f"{date:<12}{home[:26]:<28}{away[:26]:<28}{prediction:>12}"
        )

    return "\n".join(lines)


def generate_claude_prompt(conference, league, age_group, standings, results, remaining_count, teams_data=None):
    """Generate prompt for Claude to create narrative analysis."""

    # Sort results by win probability
    sorted_by_odds = sorted(results.items(), key=lambda x: -x[1]['win_conference_pct'])
    top_contenders = sorted_by_odds[:5]

    prompt = f"""Analyze the {league} {age_group} {conference} conference race.

CURRENT STANDINGS (Season starting {SEASON_START_DATE}, sorted by Points Per Game):
{format_standings_table(standings, teams_data)}

REMAINING GAMES: {remaining_count}

SIMULATION RESULTS (10,000 Monte Carlo iterations, ranked by PPG):

Conference Title Odds:
"""

    for team, data in top_contenders:
        prompt += f"- {team}: {data['win_conference_pct']}% (expected finish: #{data['expected_position']:.1f}, exp PPG: {data['expected_ppg']:.2f})\n"

    prompt += f"""
DETAILED PROJECTIONS:
{format_simulation_results(results, standings)}

Write a 3-4 paragraph analysis covering:
1. Who are the favorites and why? Reference specific win percentages.
2. Which teams are in a tight race? (teams with overlapping probability distributions)
3. What's the range of outcomes? Use the position std deviations to discuss uncertainty.
4. Any surprising projections based on current standings vs simulation results?

Be specific with numbers. This is for a Pro user who wants analytical depth."""

    return prompt


def main():
    """Run the conference simulation."""

    # Configuration - change these to analyze different conferences
    LEAGUE = 'ECNL'
    AGE_GROUP = 'G13'
    CONFERENCE = 'Midwest'

    print(f"\n{'='*80}")
    print(f"CONFERENCE SIMULATOR - Proof of Concept")
    print(f"{'='*80}")
    print(f"League: {LEAGUE} | Age Group: {AGE_GROUP} | Conference: {CONFERENCE}")
    print(f"Season Start: {SEASON_START_DATE} | Simulations: {N_SIMULATIONS:,}")
    print(f"Ranking Method: Points Per Game (PPG)")
    print(f"{'='*80}\n")

    # Load data
    print("Loading rankings data...")
    rankings = load_rankings()
    print(f"  Loaded {len(rankings)} teams from rankings JSON")

    print("\nConnecting to database...")
    conn = sqlite3.connect(DB_PATH)

    # Get conference teams (filtered to primary conference members only)
    print(f"\nFinding teams in {CONFERENCE} conference...")
    teams = get_conference_teams(conn, LEAGUE, AGE_GROUP, CONFERENCE)
    print(f"  Found {len(teams)} primary conference teams (excluding cross-conference visitors)")

    # Get games (only games between conference teams)
    print("\nLoading conference games...")
    completed, remaining = get_conference_games(conn, LEAGUE, AGE_GROUP, CONFERENCE, conference_teams=set(teams))
    print(f"  Completed conference games: {len(completed)}")
    print(f"  Remaining conference games: {len(remaining)}")

    # Calculate current standings
    print("\nCalculating current standings...")
    standings = calculate_current_standings(completed, teams)

    # Match teams to rankings
    print("\nMatching teams to rankings...")
    teams_data = {}
    matched = 0
    for team in teams:
        data = match_team_to_rankings(team, rankings, LEAGUE, AGE_GROUP)
        teams_data[team] = data
        if data['power_score'] != 1500:  # Not default
            matched += 1
    print(f"  Matched {matched}/{len(teams)} teams to rankings")

    # Print current standings
    print(f"\n{'='*86}")
    print("CURRENT CONFERENCE STANDINGS (sorted by Points Per Game)")
    print(f"{'='*86}")
    print(format_standings_table(standings, teams_data))

    # Run simulation
    print(f"\n{'='*70}")
    print(f"RUNNING MONTE CARLO SIMULATION ({N_SIMULATIONS:,} iterations)...")
    print(f"{'='*70}")

    import time
    start = time.time()
    final_positions, final_points, final_ppg, conference_winners = run_simulation(
        teams_data, standings, remaining, N_SIMULATIONS
    )
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f} seconds")

    # Calculate results
    results = calculate_results(final_positions, final_points, final_ppg, conference_winners, N_SIMULATIONS)

    # Print results
    print(f"\n{'='*70}")
    print("SIMULATION RESULTS (ranked by Points Per Game)")
    print(f"{'='*70}")
    print(format_simulation_results(results, standings))

    # Print predicted remaining games
    print(f"\n{'='*82}")
    print("PREDICTED RESULTS FOR REMAINING GAMES")
    print(f"{'='*82}")
    print(format_remaining_games_predictions(remaining, teams_data))

    # Print top contenders detail
    print(f"\n{'='*70}")
    print("DETAILED POSITION PROBABILITIES (Top 5 Contenders)")
    print(f"{'='*70}")

    sorted_by_odds = sorted(results.items(), key=lambda x: -x[1]['win_conference_pct'])[:5]
    for team, data in sorted_by_odds:
        print(f"\n{team}")
        print(f"  Win Conference: {data['win_conference_pct']}%")
        print(f"  Expected Finish: #{data['expected_position']:.2f} (+-{data['position_std_dev']:.2f})")
        print(f"  Expected PPG: {data['expected_ppg']:.2f} (+-{data['ppg_std_dev']:.2f})")
        print(f"  Expected Points: {data['expected_points']:.1f} (90% CI: {data['points_90_ci'][0]}-{data['points_90_ci'][1]})")
        print(f"  Position Distribution: ", end="")
        for pos in range(1, 6):
            pct = data['position_distribution'].get(pos, 0)
            if pct > 0:
                print(f"#{pos}:{pct}% ", end="")
        print()

    # Generate Claude prompt
    print(f"\n{'='*70}")
    print("CLAUDE API PROMPT (for narrative generation)")
    print(f"{'='*70}")
    prompt = generate_claude_prompt(CONFERENCE, LEAGUE, AGE_GROUP, standings, results, len(remaining), teams_data)
    print(prompt)

    # Token/cost estimate
    prompt_tokens = len(prompt.split()) * 1.3  # Rough token estimate
    print(f"\n{'='*70}")
    print("COST ESTIMATE")
    print(f"{'='*70}")
    print(f"  Prompt tokens (est): {int(prompt_tokens)}")
    print(f"  Response tokens (est): ~800")
    print(f"  Cost with Sonnet 4: ~${(prompt_tokens/1000000 * 3) + (800/1000000 * 15):.4f}")
    print(f"  Cost with Haiku 3.5: ~${(prompt_tokens/1000000 * 0.8) + (800/1000000 * 4):.4f}")

    conn.close()

    # Save results to JSON
    output = {
        'conference': CONFERENCE,
        'league': LEAGUE,
        'age_group': AGE_GROUP,
        'simulations': N_SIMULATIONS,
        'ranking_method': 'points_per_game',
        'completed_games': len(completed),
        'remaining_games': len(remaining),
        'results': results,
        'generated_at': datetime.now().isoformat()
    }

    output_path = os.path.join(os.path.dirname(DB_PATH), 'simulation_results.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {output_path}")


if __name__ == '__main__':
    main()
