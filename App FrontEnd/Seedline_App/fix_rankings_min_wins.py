#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════
RANKINGS POST-PROCESSOR: Enforce minimum wins for top rankings
════════════════════════════════════════════════════════════════════════════════

This script adjusts rankings so that teams with fewer than 5 wins cannot be
ranked higher than #10 in their age group.

Usage:
    python fix_rankings_min_wins.py                           # Process rankings_for_react.json
    python fix_rankings_min_wins.py --file path/to/file.json  # Custom file
    python fix_rankings_min_wins.py --min-wins 6              # Different threshold
    python fix_rankings_min_wins.py --max-rank 15             # Different max rank

════════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import sys
import argparse
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.absolute()

def find_rankings_file():
    """Find the rankings_for_react.json file"""
    candidates = [
        SCRIPT_DIR / "rankings_for_react.json",
        SCRIPT_DIR.parent / "Run Rankings" / "rankings_for_react.json",
        SCRIPT_DIR.parent.parent / "scrapers and data" / "Run Rankings" / "rankings_for_react.json",
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\Run Rankings\rankings_for_react.json"),
    ]
    
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def parse_record(record_str):
    """Parse record string like '4-2-0' into (wins, losses, ties)"""
    if not record_str:
        return 0, 0, 0
    
    match = re.match(r'(\d+)-(\d+)-(\d+)', str(record_str))
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0


def enforce_min_wins_ranking(teams, min_wins=5, max_rank_without_min=10):
    """
    Re-rank teams so that teams with fewer than min_wins cannot be
    ranked higher than max_rank_without_min.
    
    Algorithm:
    1. Split into teams with enough wins and teams without
    2. Rank teams with enough wins first (positions 1 to N)
    3. Teams without enough wins start at max_rank_without_min or later
    """
    if not teams:
        return teams
    
    # Separate teams by win count
    enough_wins = []
    not_enough_wins = []
    
    for team in teams:
        record = team.get('record', '')
        wins, _, _ = parse_record(record)
        
        if wins >= min_wins:
            enough_wins.append(team)
        else:
            not_enough_wins.append(team)
    
    # Sort each group by their current power score (descending)
    enough_wins.sort(key=lambda t: t.get('power_score', 0), reverse=True)
    not_enough_wins.sort(key=lambda t: t.get('power_score', 0), reverse=True)
    
    # Assign ranks
    result = []
    rank = 1
    
    # Teams with enough wins get ranks 1, 2, 3, ...
    for team in enough_wins:
        team_copy = team.copy()
        team_copy['rank'] = rank
        result.append(team_copy)
        rank += 1
    
    # If we haven't reached max_rank_without_min yet, pad with enough_wins teams
    # Actually, teams without enough wins should start at max_rank_without_min
    start_rank_for_low_wins = max(rank, max_rank_without_min)
    
    for team in not_enough_wins:
        team_copy = team.copy()
        team_copy['rank'] = start_rank_for_low_wins
        result.append(team_copy)
        start_rank_for_low_wins += 1
    
    # Sort by rank for output
    result.sort(key=lambda t: t['rank'])
    
    return result


def process_rankings_file(input_path, output_path=None, min_wins=5, max_rank=10):
    """Process a rankings JSON file and enforce minimum wins rule"""
    
    print(f"📂 Loading: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    teams = data.get('teams', [])
    print(f"📊 Found {len(teams)} teams")
    
    # Group teams by age group and gender
    groups = defaultdict(list)
    for team in teams:
        key = (team.get('age_group', ''), team.get('gender', ''))
        groups[key].append(team)
    
    print(f"📋 Processing {len(groups)} age/gender groups")
    
    # Track changes
    demotions = []
    
    # Process each group
    all_teams = []
    for (age_group, gender), group_teams in groups.items():
        # Get original top teams
        original_top = sorted(group_teams, key=lambda t: t.get('rank', 9999))[:max_rank]
        
        # Apply minimum wins rule
        fixed_teams = enforce_min_wins_ranking(group_teams, min_wins, max_rank)
        
        # Track demotions
        for team in fixed_teams:
            original_team = next((t for t in group_teams if t.get('team') == team.get('team')), None)
            if original_team:
                original_rank = original_team.get('rank', 9999)
                new_rank = team.get('rank', 9999)
                
                if new_rank > original_rank and original_rank < max_rank:
                    wins, _, _ = parse_record(team.get('record', ''))
                    demotions.append({
                        'team': team.get('team'),
                        'age_group': age_group,
                        'gender': gender,
                        'old_rank': original_rank,
                        'new_rank': new_rank,
                        'wins': wins,
                        'record': team.get('record')
                    })
        
        all_teams.extend(fixed_teams)
    
    # Report demotions
    if demotions:
        print(f"\n⚠️  Demoted {len(demotions)} teams (< {min_wins} wins):")
        for d in sorted(demotions, key=lambda x: (x['age_group'], x['old_rank'])):
            print(f"   {d['age_group']} {d['gender']}: {d['team'][:35]:35} #{d['old_rank']:2} → #{d['new_rank']:2} ({d['record']}, {d['wins']} wins)")
    else:
        print("✅ No teams needed demotion")
    
    # Update data
    data['teams'] = all_teams
    data['min_wins_rule'] = {
        'min_wins': min_wins,
        'max_rank_without_min': max_rank,
        'applied_at': datetime.now().isoformat()
    }
    
    # Save
    if output_path is None:
        output_path = input_path
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Saved to: {output_path}")
    
    return len(demotions)


def main():
    parser = argparse.ArgumentParser(description="Enforce minimum wins for top rankings")
    parser.add_argument('--file', '-f', help='Path to rankings JSON file')
    parser.add_argument('--output', '-o', help='Output file path (default: overwrite input)')
    parser.add_argument('--min-wins', type=int, default=5, help='Minimum wins required for top ranks (default: 5)')
    parser.add_argument('--max-rank', type=int, default=10, help='Teams below min-wins cannot be higher than this (default: 10)')
    args = parser.parse_args()
    
    print("═" * 70)
    print("🏆 RANKINGS POST-PROCESSOR: Minimum Wins Rule")
    print("═" * 70)
    print(f"\n📋 Rule: Teams with < {args.min_wins} wins cannot be ranked higher than #{args.max_rank}")
    
    # Find rankings file
    input_file = args.file or find_rankings_file()
    if not input_file or not os.path.exists(input_file):
        print(f"\n❌ Rankings file not found!")
        print("\nUsage: python fix_rankings_min_wins.py --file path/to/rankings_for_react.json")
        return 1
    
    demotions = process_rankings_file(
        input_file,
        args.output,
        args.min_wins,
        args.max_rank
    )
    
    print("\n" + "═" * 70)
    print("✅ Complete!")
    print("═" * 70)
    
    if demotions > 0:
        print(f"\n⚠️  {demotions} teams were demoted. Re-export to React app to see changes.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
