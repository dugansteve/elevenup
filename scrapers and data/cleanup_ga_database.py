#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════
SEEDLINE DATABASE CLEANUP - GA TEAMS & GAMES
════════════════════════════════════════════════════════════════════════════════

Fixes multiple issues with GA Events data:
1. Age group extraction (08/07G pattern must be checked before 08G)
2. Team name normalization (remove "GA", "Girls Academy" suffixes)
3. Duplicate team merging
4. Game-to-team linking

Usage:
    python cleanup_ga_database.py                    # Analyze only (dry run)
    python cleanup_ga_database.py --apply            # Apply all fixes
    python cleanup_ga_database.py --db path/to/db    # Custom database path

════════════════════════════════════════════════════════════════════════════════
"""

import sqlite3
import re
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()

def find_database():
    """Find the seedlinedata.db file"""
    candidates = [
        SCRIPT_DIR / "seedlinedata.db",
        SCRIPT_DIR.parent / "scrapers and data" / "seedlinedata.db",
        SCRIPT_DIR.parent.parent / "scrapers and data" / "seedlinedata.db",
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"),
    ]
    
    for path in candidates:
        if path.exists():
            return str(path)
    
    return None

# ============================================================================
# IMPROVED AGE GROUP EXTRACTION
# ============================================================================

def extract_age_from_team_name(team_name: str) -> str:
    """
    Extract G-format age from team name.
    
    IMPORTANT: Check combined patterns (08/07G) BEFORE single patterns (08G)
    to avoid incorrect matches!
    """
    if not team_name:
        return None
    
    # Pattern 1: Combined age groups like 08/07G (CHECK FIRST!)
    match = re.search(r'(\d{2})/(\d{2})G', team_name)
    if match:
        return f"G{match.group(1)}/{match.group(2)}"
    
    # Pattern 2: Birth year with G like 08G, 09G, 10G, 11G, 12G, 13G
    # Make sure it's not part of a combined pattern
    match = re.search(r'(?<!/)\b(\d{2})G\b', team_name)
    if match:
        return f"G{match.group(1)}"
    
    # Pattern 3: Full birth year like 2008, 2009, 2010
    match = re.search(r'\b20(\d{2})\b', team_name)
    if match:
        return f"G{match.group(1)}"
    
    # Pattern 4: Already in G-format like G08, G09
    match = re.search(r'\bG(\d{2})\b', team_name)
    if match:
        return f"G{match.group(1)}"
    
    # Pattern 5: Combined G-format like G08/07
    match = re.search(r'\bG(\d{2})/(\d{2})\b', team_name)
    if match:
        return f"G{match.group(1)}/{match.group(2)}"
    
    return None


def normalize_team_name(name: str) -> str:
    """
    Normalize team name for consistent matching.
    
    Removes suffixes like "GA", "Girls Academy" while preserving age.
    """
    if not name:
        return ""
    
    normalized = name.strip()
    
    # Remove common suffixes (but keep age designations)
    normalized = re.sub(r'\s+(GA|Girls Academy)\s*$', '', normalized, flags=re.I)
    normalized = re.sub(r'\s+GA\s+', ' ', normalized, flags=re.I)
    
    # Clean up extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def get_team_base_name(name: str) -> str:
    """
    Get the base team name without age suffix.
    Used for grouping potential duplicates.
    """
    if not name:
        return ""
    
    base = name.strip()
    
    # Remove GA suffix
    base = re.sub(r'\s+(GA|Girls Academy)\s*$', '', base, flags=re.I)
    
    # Remove age suffixes
    base = re.sub(r'\s+\d{2}/\d{2}G\s*$', '', base)  # 08/07G
    base = re.sub(r'\s+\d{2}G\s*$', '', base)         # 08G
    base = re.sub(r'\s+G\d{2}/\d{2}\s*$', '', base)   # G08/07
    base = re.sub(r'\s+G\d{2}\s*$', '', base)         # G08
    base = re.sub(r'\s+20\d{2}\s*$', '', base)        # 2008
    
    return base.strip()

# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def analyze_games_without_matching_teams(conn):
    """Find games where team names don't match any team in rankings"""
    cursor = conn.cursor()
    
    # Get all unique team names from games
    cursor.execute("""
        SELECT DISTINCT home_team FROM games WHERE league = 'GA' OR event_type IS NOT NULL
        UNION
        SELECT DISTINCT away_team FROM games WHERE league = 'GA' OR event_type IS NOT NULL
    """)
    game_teams = set(row[0] for row in cursor.fetchall() if row[0])
    
    # This would need the rankings data, but for now we'll identify variations
    team_variations = defaultdict(list)
    
    for team in game_teams:
        base = get_team_base_name(team)
        if base:
            team_variations[base].append(team)
    
    # Find bases with multiple variations
    duplicates = {k: v for k, v in team_variations.items() if len(v) > 1}
    
    return duplicates


def analyze_age_group_issues(conn):
    """Find games with potentially incorrect age groups"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT game_id, game_date, home_team, away_team, age_group, event_type
        FROM games 
        WHERE (league = 'GA' OR event_type IS NOT NULL)
        ORDER BY game_date DESC
    """)
    
    games = cursor.fetchall()
    issues = []
    
    for game_id, game_date, home_team, away_team, current_age, event_type in games:
        # Extract correct age from team names
        home_age = extract_age_from_team_name(home_team)
        away_age = extract_age_from_team_name(away_team)
        
        # Use home team's age, fall back to away team's
        correct_age = home_age or away_age
        
        if correct_age and correct_age != current_age:
            issues.append({
                'game_id': game_id,
                'game_date': game_date,
                'home_team': home_team,
                'away_team': away_team,
                'current_age': current_age,
                'correct_age': correct_age,
                'event_type': event_type
            })
    
    return issues


def analyze_team_name_variations(conn):
    """
    Find all variations of team names that should be the same team.
    
    Example: "Lamorinda SC 08/07G GA", "Lamorinda SC 08/07G", "Lamorinda SC 08G"
    """
    cursor = conn.cursor()
    
    # Get all team names from games
    cursor.execute("""
        SELECT DISTINCT home_team FROM games WHERE league = 'GA' OR event_type IS NOT NULL
        UNION
        SELECT DISTINCT away_team FROM games WHERE league = 'GA' OR event_type IS NOT NULL
    """)
    
    all_teams = [row[0] for row in cursor.fetchall() if row[0]]
    
    # Group by base name + age
    # Structure: {key: {'names': set(), 'counts': dict()}}
    team_groups = {}
    
    for team in all_teams:
        base = get_team_base_name(team)
        age = extract_age_from_team_name(team)
        
        if base and age:
            key = f"{base}|{age}"
            
            # Initialize if needed
            if key not in team_groups:
                team_groups[key] = {'names': set(), 'counts': {}}
            
            team_groups[key]['names'].add(team)
            
            # Count games for this team name
            cursor.execute("""
                SELECT COUNT(*) FROM games 
                WHERE (home_team = ? OR away_team = ?)
                AND (league = 'GA' OR event_type IS NOT NULL)
            """, (team, team))
            count = cursor.fetchone()[0]
            team_groups[key]['counts'][team] = count
    
    # Find groups with multiple name variations
    variations = {}
    for key, data in team_groups.items():
        if len(data['names']) > 1:
            variations[key] = {
                'names': list(data['names']),
                'counts': data['counts']
            }
    
    return variations


def find_08_vs_0807_issues(conn):
    """
    Specifically find cases where 08G and 08/07G teams might be confused.
    """
    cursor = conn.cursor()
    
    # Find all teams with 08G or 08/07G in their name
    cursor.execute("""
        SELECT DISTINCT home_team FROM games 
        WHERE (home_team LIKE '%08G%' OR home_team LIKE '%08/07G%')
        AND (league = 'GA' OR event_type IS NOT NULL)
        UNION
        SELECT DISTINCT away_team FROM games 
        WHERE (away_team LIKE '%08G%' OR away_team LIKE '%08/07G%')
        AND (league = 'GA' OR event_type IS NOT NULL)
    """)
    
    teams = [row[0] for row in cursor.fetchall() if row[0]]
    
    # Group by club
    club_teams = defaultdict(list)
    for team in teams:
        base = get_team_base_name(team)
        age = extract_age_from_team_name(team)
        club_teams[base].append({
            'full_name': team,
            'age': age
        })
    
    # Find clubs with both 08G and 08/07G
    issues = {}
    for club, team_list in club_teams.items():
        ages = set(t['age'] for t in team_list)
        if 'G08' in ages and 'G08/07' in ages:
            issues[club] = team_list
    
    return issues


def find_teams_without_age_suffix(conn):
    """
    Find teams in GA games that don't have an age suffix in their name.
    These might be duplicates of teams that do have the suffix.
    
    Example: "Lou Fusz Athletic" should match "Lou Fusz Athletic 08G" in G08/07 games
    """
    cursor = conn.cursor()
    
    # Get all team names and their age groups from games
    cursor.execute("""
        SELECT DISTINCT home_team, age_group FROM games 
        WHERE league = 'GA' OR event_type IS NOT NULL
        UNION
        SELECT DISTINCT away_team, age_group FROM games 
        WHERE league = 'GA' OR event_type IS NOT NULL
    """)
    
    teams_by_age = defaultdict(set)
    for team, age_group in cursor.fetchall():
        if team and age_group:
            teams_by_age[age_group].add(team)
    
    issues = {}
    
    for age_group, teams in teams_by_age.items():
        # Find teams without age suffix
        teams_no_suffix = []
        teams_with_suffix = []
        
        for team in teams:
            extracted_age = extract_age_from_team_name(team)
            if extracted_age:
                teams_with_suffix.append({'name': team, 'age': extracted_age})
            else:
                teams_no_suffix.append(team)
        
        # For each team without suffix, check if there's a matching team with suffix
        for no_suffix_team in teams_no_suffix:
            base = get_team_base_name(no_suffix_team)
            
            for with_suffix in teams_with_suffix:
                suffix_base = get_team_base_name(with_suffix['name'])
                
                # Check if bases match (allowing for small variations)
                if base.lower() == suffix_base.lower():
                    key = f"{age_group}|{base}"
                    if key not in issues:
                        issues[key] = {
                            'age_group': age_group,
                            'no_suffix': [],
                            'with_suffix': []
                        }
                    if no_suffix_team not in issues[key]['no_suffix']:
                        issues[key]['no_suffix'].append(no_suffix_team)
                    if with_suffix['name'] not in issues[key]['with_suffix']:
                        issues[key]['with_suffix'].append(with_suffix['name'])
    
    return issues


def fix_teams_without_age_suffix(conn, issues, dry_run=True):
    """
    For teams without age suffix, rename them to match the team with suffix.
    Uses the name with suffix as the canonical name.
    """
    if dry_run:
        return []
    
    cursor = conn.cursor()
    renames = []
    
    for key, data in issues.items():
        # Use the first team with suffix as canonical
        if data['with_suffix']:
            canonical = data['with_suffix'][0]
            
            for old_name in data['no_suffix']:
                cursor.execute("UPDATE games SET home_team = ? WHERE home_team = ?", (canonical, old_name))
                cursor.execute("UPDATE games SET away_team = ? WHERE away_team = ?", (canonical, old_name))
                renames.append((old_name, canonical))
    
    conn.commit()
    return renames


def find_duplicate_games(conn):
    """
    Find duplicate games: same date, same teams (regardless of order), same score.
    
    This catches issues like:
    - Tennessee SC vs Indy Eleven on same date with same score appearing twice
    - Scrapers run multiple times on same data
    - Team name variations causing different game_ids for same game
    """
    cursor = conn.cursor()
    
    # Find potential duplicates by grouping on date + sorted teams + score
    cursor.execute("""
        SELECT 
            game_date,
            CASE WHEN home_team < away_team THEN home_team ELSE away_team END as team1,
            CASE WHEN home_team < away_team THEN away_team ELSE home_team END as team2,
            CASE WHEN home_team < away_team THEN home_score ELSE away_score END as score1,
            CASE WHEN home_team < away_team THEN away_score ELSE home_score END as score2,
            age_group,
            league,
            COUNT(*) as cnt,
            GROUP_CONCAT(game_id, '|||') as game_ids
        FROM games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        GROUP BY game_date, team1, team2, score1, score2, age_group
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
    """)
    
    duplicates = []
    for row in cursor.fetchall():
        game_date, team1, team2, score1, score2, age_group, league, cnt, game_ids = row
        game_id_list = game_ids.split('|||') if game_ids else []
        
        duplicates.append({
            'game_date': game_date,
            'team1': team1,
            'team2': team2,
            'score': f"{score1}-{score2}",
            'age_group': age_group,
            'league': league,
            'count': cnt,
            'game_ids': game_id_list
        })
    
    return duplicates


def remove_duplicate_games(conn, duplicates, dry_run=True):
    """
    Remove duplicate games, keeping only one copy of each.
    Keeps the game with the "best" game_id (shortest, or first alphabetically).
    """
    if dry_run:
        return 0
    
    cursor = conn.cursor()
    removed = 0
    
    for dup in duplicates:
        game_ids = dup['game_ids']
        if len(game_ids) <= 1:
            continue
        
        # Keep the first game_id (alphabetically), remove the rest
        game_ids_sorted = sorted(game_ids)
        keep_id = game_ids_sorted[0]
        remove_ids = game_ids_sorted[1:]
        
        for remove_id in remove_ids:
            cursor.execute("DELETE FROM games WHERE game_id = ?", (remove_id,))
            removed += 1
    
    conn.commit()
    return removed


def find_near_duplicate_games(conn):
    """
    Find near-duplicates: same date, similar team names, same score.
    
    This catches issues where team names are slightly different:
    - "Tennessee SC" vs "Tennessee SC " (trailing space)
    - "FC Pride" vs "FC Pride SC"
    """
    cursor = conn.cursor()
    
    # Get all games with scores
    cursor.execute("""
        SELECT game_id, game_date, home_team, away_team, home_score, away_score, age_group, league
        FROM games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        ORDER BY game_date, home_team
    """)
    
    games = cursor.fetchall()
    
    # Group by date
    games_by_date = defaultdict(list)
    for game in games:
        game_id, game_date, home, away, h_score, a_score, age, league = game
        games_by_date[game_date].append({
            'game_id': game_id,
            'home': home,
            'away': away,
            'h_score': h_score,
            'a_score': a_score,
            'age': age,
            'league': league
        })
    
    near_duplicates = []
    
    for date, day_games in games_by_date.items():
        # Compare each pair
        for i, g1 in enumerate(day_games):
            for g2 in day_games[i+1:]:
                # Check if scores match (in either direction)
                scores_match = (
                    (g1['h_score'] == g2['h_score'] and g1['a_score'] == g2['a_score']) or
                    (g1['h_score'] == g2['a_score'] and g1['a_score'] == g2['h_score'])
                )
                
                if not scores_match:
                    continue
                
                # Check if teams are similar (normalize and compare)
                g1_teams = {get_team_base_name(g1['home']).lower(), get_team_base_name(g1['away']).lower()}
                g2_teams = {get_team_base_name(g2['home']).lower(), get_team_base_name(g2['away']).lower()}
                
                # If both base team names match, it's a near-duplicate
                if g1_teams == g2_teams and g1['game_id'] != g2['game_id']:
                    near_duplicates.append({
                        'date': date,
                        'game1': g1,
                        'game2': g2,
                        'teams': g1_teams
                    })
    
    return near_duplicates


def remove_near_duplicate_games(conn, near_duplicates, dry_run=True):
    """
    Remove near-duplicate games, keeping the one with the "better" team names.
    Prefers names without trailing spaces, with proper capitalization, etc.
    """
    if dry_run:
        return 0
    
    cursor = conn.cursor()
    removed = 0
    seen_pairs = set()
    
    for dup in near_duplicates:
        g1_id = dup['game1']['game_id']
        g2_id = dup['game2']['game_id']
        
        # Avoid processing same pair twice
        pair_key = tuple(sorted([g1_id, g2_id]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        
        # Prefer the game with shorter team names (less likely to have junk)
        g1_len = len(dup['game1']['home']) + len(dup['game1']['away'])
        g2_len = len(dup['game2']['home']) + len(dup['game2']['away'])
        
        if g1_len <= g2_len:
            remove_id = g2_id
        else:
            remove_id = g1_id
        
        cursor.execute("DELETE FROM games WHERE game_id = ?", (remove_id,))
        removed += 1
    
    conn.commit()
    return removed

# ============================================================================
# FIX FUNCTIONS
# ============================================================================

def fix_age_groups(conn, issues, dry_run=True):
    """Update incorrect age groups in games table"""
    if dry_run:
        return 0
    
    cursor = conn.cursor()
    updated = 0
    
    for issue in issues:
        cursor.execute("""
            UPDATE games SET age_group = ? WHERE game_id = ?
        """, (issue['correct_age'], issue['game_id']))
        updated += 1
    
    conn.commit()
    return updated


def normalize_team_names_in_games(conn, dry_run=True):
    """
    Normalize team names in games table.
    Removes "GA" suffix while preserving age designations.
    """
    cursor = conn.cursor()
    
    # Find all team names that need normalization
    cursor.execute("""
        SELECT DISTINCT home_team FROM games 
        WHERE home_team LIKE '% GA' OR home_team LIKE '% GA %'
        UNION
        SELECT DISTINCT away_team FROM games 
        WHERE away_team LIKE '% GA' OR away_team LIKE '% GA %'
    """)
    
    teams_to_fix = [row[0] for row in cursor.fetchall() if row[0]]
    
    fixes = []
    for old_name in teams_to_fix:
        new_name = normalize_team_name(old_name)
        if new_name != old_name:
            fixes.append((old_name, new_name))
    
    if dry_run:
        return fixes
    
    # Apply fixes
    for old_name, new_name in fixes:
        cursor.execute("UPDATE games SET home_team = ? WHERE home_team = ?", (new_name, old_name))
        cursor.execute("UPDATE games SET away_team = ? WHERE away_team = ?", (new_name, old_name))
    
    conn.commit()
    return fixes


def merge_duplicate_teams(conn, variations, dry_run=True):
    """
    Merge duplicate team name variations into a single canonical name.
    Uses the name with the most games as the canonical name.
    """
    if dry_run:
        return []
    
    cursor = conn.cursor()
    merges = []
    
    for key, data in variations.items():
        # Find the name with most games (this is likely the "correct" one)
        names = data['names']
        counts = data['counts']
        
        canonical = max(names, key=lambda n: counts.get(n, 0))
        
        for name in names:
            if name != canonical:
                # Update all games to use canonical name
                cursor.execute("UPDATE games SET home_team = ? WHERE home_team = ?", (canonical, name))
                cursor.execute("UPDATE games SET away_team = ? WHERE away_team = ?", (canonical, name))
                merges.append((name, canonical))
    
    conn.commit()
    return merges

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Clean up GA teams and games in database")
    parser.add_argument('--db', help='Path to database file')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    args = parser.parse_args()
    
    print("═" * 70)
    print("🔧 SEEDLINE DATABASE CLEANUP - GA TEAMS & GAMES")
    print("═" * 70)
    
    # Find database
    db_path = args.db or find_database()
    if not db_path or not os.path.exists(db_path):
        print(f"❌ Database not found!")
        print("\nUsage: python cleanup_ga_database.py --db path/to/seedlinedata.db")
        return 1
    
    print(f"\n📁 Database: {db_path}")
    print(f"📋 Mode: {'APPLY CHANGES' if args.apply else 'DRY RUN (preview only)'}")
    
    conn = sqlite3.connect(db_path)
    
    try:
        # ════════════════════════════════════════════════════════════════════
        # STEP 1: Check for 08G vs 08/07G confusion
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 1: Checking for 08G vs 08/07G confusion...")
        print("─" * 70)
        
        confusion = find_08_vs_0807_issues(conn)
        
        if confusion:
            print(f"\n⚠️  Found {len(confusion)} clubs with both 08G and 08/07G teams:")
            for club, teams in list(confusion.items())[:10]:
                print(f"\n   {club}:")
                for t in teams:
                    print(f"      - {t['full_name']} → {t['age']}")
        else:
            print("✅ No 08G/08/07G confusion found")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 2: Find team name variations
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 2: Finding team name variations...")
        print("─" * 70)
        
        variations = analyze_team_name_variations(conn)
        
        if variations:
            print(f"\n⚠️  Found {len(variations)} teams with multiple name variations:")
            for key, data in list(variations.items())[:15]:
                print(f"\n   {key}:")
                for name in data['names']:
                    count = data['counts'].get(name, 0)
                    print(f"      - \"{name}\" ({count} games)")
        else:
            print("✅ No team name variations found")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 3: Analyze age group issues
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 3: Analyzing age group issues...")
        print("─" * 70)
        
        age_issues = analyze_age_group_issues(conn)
        
        if age_issues:
            print(f"\n⚠️  Found {len(age_issues)} games with incorrect age groups")
            
            # Summarize by change type
            changes = defaultdict(int)
            for issue in age_issues:
                key = f"{issue['current_age']} → {issue['correct_age']}"
                changes[key] += 1
            
            print("\n   Summary of age group changes:")
            for change, count in sorted(changes.items(), key=lambda x: -x[1])[:10]:
                print(f"      {change}: {count} games")
            
            if args.verbose:
                print("\n   Sample issues:")
                for issue in age_issues[:10]:
                    print(f"      {issue['home_team'][:35]:35} | {issue['current_age']} → {issue['correct_age']}")
        else:
            print("✅ No age group issues found")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 4: Find team names to normalize
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 4: Finding team names to normalize...")
        print("─" * 70)
        
        name_fixes = normalize_team_names_in_games(conn, dry_run=True)
        
        if name_fixes:
            print(f"\n⚠️  Found {len(name_fixes)} team names to normalize:")
            for old, new in name_fixes[:15]:
                print(f"      \"{old}\" → \"{new}\"")
            if len(name_fixes) > 15:
                print(f"      ... and {len(name_fixes) - 15} more")
        else:
            print("✅ No team names need normalization")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 5: Find teams without age suffix (e.g., "Lou Fusz Athletic" vs "Lou Fusz Athletic 08G")
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 5: Finding teams without age suffix...")
        print("─" * 70)
        
        no_suffix_issues = find_teams_without_age_suffix(conn)
        
        if no_suffix_issues:
            print(f"\n⚠️  Found {len(no_suffix_issues)} teams without age suffix that match teams with suffix:")
            for key, data in list(no_suffix_issues.items())[:15]:
                print(f"\n   {data['age_group']}: {key.split('|')[1]}")
                print(f"      Without suffix: {data['no_suffix']}")
                print(f"      With suffix:    {data['with_suffix']}")
        else:
            print("✅ No teams without age suffix found")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 6: Find exact duplicate games (same date, teams, score)
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 6: Finding exact duplicate games...")
        print("─" * 70)
        
        duplicates = find_duplicate_games(conn)
        
        if duplicates:
            total_extra = sum(d['count'] - 1 for d in duplicates)
            print(f"\n⚠️  Found {len(duplicates)} sets of duplicate games ({total_extra} extra copies):")
            for dup in duplicates[:10]:
                print(f"   {dup['game_date']} | {dup['team1'][:25]} vs {dup['team2'][:25]} | {dup['score']} | {dup['count']}x")
            if len(duplicates) > 10:
                print(f"   ... and {len(duplicates) - 10} more")
        else:
            print("✅ No exact duplicate games found")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 7: Find near-duplicate games (similar team names, same score)
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("STEP 7: Finding near-duplicate games (similar team names)...")
        print("─" * 70)
        
        near_duplicates = find_near_duplicate_games(conn)
        
        if near_duplicates:
            print(f"\n⚠️  Found {len(near_duplicates)} near-duplicate games:")
            for dup in near_duplicates[:10]:
                g1 = dup['game1']
                g2 = dup['game2']
                print(f"   {dup['date']}:")
                print(f"      Game 1: {g1['home'][:25]} vs {g1['away'][:25]} ({g1['h_score']}-{g1['a_score']})")
                print(f"      Game 2: {g2['home'][:25]} vs {g2['away'][:25]} ({g2['h_score']}-{g2['a_score']})")
            if len(near_duplicates) > 10:
                print(f"   ... and {len(near_duplicates) - 10} more")
        else:
            print("✅ No near-duplicate games found")
        
        # ════════════════════════════════════════════════════════════════════
        # STEP 8: Apply fixes
        # ════════════════════════════════════════════════════════════════════
        if args.apply and (age_issues or name_fixes or variations or no_suffix_issues or duplicates or near_duplicates):
            print("\n" + "─" * 70)
            print("STEP 8: Applying fixes...")
            print("─" * 70)
            
            # Fix age groups
            if age_issues:
                print("\n🔄 Fixing age groups...")
                updated = fix_age_groups(conn, age_issues, dry_run=False)
                print(f"   ✅ Updated {updated} games")
            
            # Normalize team names
            if name_fixes:
                print("\n🔄 Normalizing team names...")
                normalize_team_names_in_games(conn, dry_run=False)
                print(f"   ✅ Normalized {len(name_fixes)} team names")
            
            # Merge duplicates
            if variations:
                print("\n🔄 Merging duplicate team variations...")
                merges = merge_duplicate_teams(conn, variations, dry_run=False)
                print(f"   ✅ Merged {len(merges)} team name variations")
            
            # Fix teams without age suffix
            if no_suffix_issues:
                print("\n🔄 Fixing teams without age suffix...")
                renames = fix_teams_without_age_suffix(conn, no_suffix_issues, dry_run=False)
                print(f"   ✅ Renamed {len(renames)} teams to include age suffix")
            
            # Remove exact duplicates
            if duplicates:
                print("\n🔄 Removing exact duplicate games...")
                removed = remove_duplicate_games(conn, duplicates, dry_run=False)
                print(f"   ✅ Removed {removed} duplicate games")
            
            # Remove near-duplicates
            if near_duplicates:
                print("\n🔄 Removing near-duplicate games...")
                removed = remove_near_duplicate_games(conn, near_duplicates, dry_run=False)
                print(f"   ✅ Removed {removed} near-duplicate games")
        
        elif age_issues or name_fixes or variations or no_suffix_issues or duplicates or near_duplicates:
            print("\n" + "─" * 70)
            print("DRY RUN COMPLETE")
            print("─" * 70)
            print("\n🔍 No changes were made.")
            print("\n   To apply fixes, run:")
            print(f"   python cleanup_ga_database.py --apply")
        
        # ════════════════════════════════════════════════════════════════════
        # FINAL: Show current state
        # ════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 70)
        print("FINAL: Current database state")
        print("─" * 70)
        
        cursor = conn.cursor()
        
        # Count GA games by age group
        cursor.execute("""
            SELECT age_group, COUNT(*) as cnt 
            FROM games 
            WHERE league = 'GA' OR event_type IS NOT NULL
            GROUP BY age_group 
            ORDER BY age_group
        """)
        
        print("\n📊 GA games by age group:")
        for age, count in cursor.fetchall():
            print(f"   {age or 'Unknown':10} : {count:5} games")
        
        # Count total GA games
        cursor.execute("""
            SELECT COUNT(*) FROM games WHERE league = 'GA' OR event_type IS NOT NULL
        """)
        total = cursor.fetchone()[0]
        print(f"\n   Total GA games: {total}")
        
        print("\n" + "═" * 70)
        print("✅ Cleanup complete!")
        print("═" * 70)
        
        if args.apply:
            print("\n⚠️  IMPORTANT: After cleanup, you need to:")
            print("   1. Run the team ranker to regenerate rankings")
            print("   2. Export to React app")
        
    finally:
        conn.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
