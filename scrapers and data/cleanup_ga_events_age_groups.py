#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════
GA EVENTS AGE GROUP CLEANUP SCRIPT
════════════════════════════════════════════════════════════════════════════════

Fixes age groups on GA Events games that were incorrectly assigned based on
division name (U15, U14, etc.) instead of team name birth year (08G, 09G, etc.)

What this script does:
1. Finds all GA Events games (event_type is not null)
2. Extracts correct age group from team names (e.g., "Lamorinda SC 08G" → G08)
3. Updates games with corrected age groups
4. Identifies and optionally merges duplicate teams

Usage:
    python cleanup_ga_events_age_groups.py                    # Dry run (preview)
    python cleanup_ga_events_age_groups.py --apply            # Apply changes
    python cleanup_ga_events_age_groups.py --db path/to/db    # Custom database

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
        SCRIPT_DIR.parent.parent / "scrapers and data" / "seedlinedata.db",
        SCRIPT_DIR.parent / "scrapers and data" / "seedlinedata.db",
        SCRIPT_DIR / "seedlinedata.db",
        Path(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"),
    ]
    
    for path in candidates:
        if path.exists():
            return str(path)
    
    return None

# ============================================================================
# AGE GROUP EXTRACTION
# ============================================================================

def extract_age_from_team_name(team_name: str) -> str:
    """Extract G-format age from team name like 'TopHat 13G GA' or 'Lamorinda SC 08G'"""
    if not team_name:
        return None
    
    # Pattern: 08G, 09G, 10G, 11G, 12G, 13G, 14G etc.
    match = re.search(r'(\d{2})G', team_name)
    if match:
        return f"G{match.group(1)}"
    
    # Pattern: 2008G, 2009G, 2010G etc. (full birth year)
    match = re.search(r'20(\d{2})G?', team_name)
    if match:
        birth_year = int(match.group(1))
        return f"G{birth_year:02d}"
    
    # Pattern: 08/07G (combined age groups)
    match = re.search(r'(\d{2})/(\d{2})G', team_name)
    if match:
        return f"G{match.group(1)}/{match.group(2)}"
    
    # Pattern: G08, G09, G10 etc. (already in correct format)
    match = re.search(r'G(\d{2})', team_name)
    if match:
        return f"G{match.group(1)}"
    
    return None

def calculate_birth_year_from_u_age(u_age: int, event_date: str) -> int:
    """Calculate birth year from U-age and event date"""
    try:
        # Parse event date
        if isinstance(event_date, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(event_date.split()[0], fmt)
                    break
                except:
                    continue
            else:
                dt = datetime.now()
        else:
            dt = datetime.now()
        
        # Determine season start year (Aug-Dec = current year, Jan-Jul = previous year)
        if dt.month >= 8:
            season_year = dt.year
        else:
            season_year = dt.year - 1
        
        # Calculate birth year: U13 in 2024 season = born 2012
        birth_year = season_year - u_age + 1
        return birth_year % 100  # Return just last 2 digits
        
    except Exception:
        return None

# ============================================================================
# CLEANUP FUNCTIONS
# ============================================================================

def analyze_ga_events_games(conn):
    """Analyze GA Events games and find age group issues"""
    cursor = conn.cursor()
    
    # Get all GA Events games
    cursor.execute("""
        SELECT game_id, game_date, home_team, away_team, age_group, event_type, conference
        FROM games 
        WHERE event_type IS NOT NULL AND event_type != ''
        ORDER BY game_date DESC
    """)
    
    games = cursor.fetchall()
    print(f"\n📊 Found {len(games)} GA Events games")
    
    issues = []
    fixes = []
    
    for game_id, game_date, home_team, away_team, current_age, event_type, conference in games:
        # Extract age from home team
        home_age = extract_age_from_team_name(home_team)
        # Extract age from away team
        away_age = extract_age_from_team_name(away_team)
        
        # Determine correct age group
        correct_age = home_age or away_age
        
        if not correct_age and conference:
            # Try to get from conference/division name using event date
            match = re.search(r'U(\d+)', conference, re.I)
            if match:
                u_age = int(match.group(1))
                birth_year = calculate_birth_year_from_u_age(u_age, game_date)
                if birth_year:
                    correct_age = f"G{birth_year:02d}"
        
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
            fixes.append((correct_age, game_id))
    
    return issues, fixes

def analyze_duplicate_teams(conn):
    """Find teams that appear to be duplicates with different age groups"""
    cursor = conn.cursor()
    
    # Get all unique team names from GA Events games
    cursor.execute("""
        SELECT DISTINCT home_team FROM games WHERE event_type IS NOT NULL
        UNION
        SELECT DISTINCT away_team FROM games WHERE event_type IS NOT NULL
    """)
    
    teams = [row[0] for row in cursor.fetchall()]
    
    # Group by base team name (without age suffix)
    team_groups = defaultdict(list)
    
    for team in teams:
        if not team:
            continue
        # Extract base name (remove age suffix)
        base_name = re.sub(r'\s+\d{2}G$', '', team)
        base_name = re.sub(r'\s+G\d{2}$', '', base_name)
        base_name = re.sub(r'\s+20\d{2}$', '', base_name)
        base_name = re.sub(r'\s+(GA|Girls Academy)$', '', base_name, flags=re.I)
        base_name = base_name.strip()
        
        team_groups[base_name].append(team)
    
    # Find groups with multiple entries (potential duplicates)
    duplicates = {k: v for k, v in team_groups.items() if len(v) > 1}
    
    return duplicates

def apply_age_group_fixes(conn, fixes, dry_run=True):
    """Apply age group fixes to database"""
    if dry_run:
        print(f"\n🔍 DRY RUN - Would update {len(fixes)} games")
        return 0
    
    cursor = conn.cursor()
    updated = 0
    
    for correct_age, game_id in fixes:
        cursor.execute("""
            UPDATE games SET age_group = ? WHERE game_id = ?
        """, (correct_age, game_id))
        updated += 1
    
    conn.commit()
    return updated

def show_summary_by_age_change(issues):
    """Show summary of changes grouped by age transition"""
    changes = defaultdict(int)
    
    for issue in issues:
        key = f"{issue['current_age']} → {issue['correct_age']}"
        changes[key] += 1
    
    print("\n📋 Summary of age group changes:")
    print("─" * 40)
    for change, count in sorted(changes.items(), key=lambda x: -x[1]):
        print(f"   {change}: {count} games")

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fix GA Events age groups in database")
    parser.add_argument('--db', help='Path to database file')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--show-all', action='store_true', help='Show all issues (not just summary)')
    args = parser.parse_args()
    
    print("═" * 70)
    print("🔧 GA EVENTS AGE GROUP CLEANUP")
    print("═" * 70)
    
    # Find database
    db_path = args.db or find_database()
    if not db_path or not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("\nUsage: python cleanup_ga_events_age_groups.py --db path/to/seedlinedata.db")
        return 1
    
    print(f"\n📁 Database: {db_path}")
    
    # Connect
    conn = sqlite3.connect(db_path)
    
    try:
        # Analyze games
        print("\n" + "─" * 70)
        print("STEP 1: Analyzing GA Events games...")
        print("─" * 70)
        
        issues, fixes = analyze_ga_events_games(conn)
        
        if not issues:
            print("✅ No age group issues found!")
        else:
            print(f"\n⚠️  Found {len(issues)} games with incorrect age groups")
            
            # Show summary
            show_summary_by_age_change(issues)
            
            # Show sample issues
            if args.show_all:
                print("\n📋 All issues:")
                for issue in issues:
                    print(f"   {issue['game_date']} | {issue['home_team'][:30]:30} | {issue['current_age']} → {issue['correct_age']}")
            else:
                print("\n📋 Sample issues (first 10):")
                for issue in issues[:10]:
                    print(f"   {issue['game_date']} | {issue['home_team'][:30]:30} | {issue['current_age']} → {issue['correct_age']}")
                if len(issues) > 10:
                    print(f"   ... and {len(issues) - 10} more")
        
        # Analyze duplicates
        print("\n" + "─" * 70)
        print("STEP 2: Checking for duplicate teams...")
        print("─" * 70)
        
        duplicates = analyze_duplicate_teams(conn)
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} potential duplicate team groups:")
            for base_name, team_list in sorted(duplicates.items())[:15]:
                print(f"   {base_name}:")
                for team in team_list[:5]:
                    print(f"      - {team}")
                if len(team_list) > 5:
                    print(f"      ... and {len(team_list) - 5} more")
            if len(duplicates) > 15:
                print(f"\n   ... and {len(duplicates) - 15} more groups")
        else:
            print("✅ No obvious duplicate teams found")
        
        # Apply fixes
        if issues:
            print("\n" + "─" * 70)
            print("STEP 3: Apply fixes")
            print("─" * 70)
            
            if args.apply:
                print("\n🔄 Applying age group fixes...")
                updated = apply_age_group_fixes(conn, fixes, dry_run=False)
                print(f"✅ Updated {updated} games")
            else:
                print("\n🔍 DRY RUN MODE - No changes made")
                print(f"   Would update {len(fixes)} games")
                print("\n   To apply changes, run:")
                print(f"   python cleanup_ga_events_age_groups.py --apply")
        
        # Final stats
        print("\n" + "─" * 70)
        print("FINAL STATS")
        print("─" * 70)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT age_group, COUNT(*) as cnt 
            FROM games 
            WHERE event_type IS NOT NULL AND event_type != ''
            GROUP BY age_group 
            ORDER BY age_group
        """)
        
        print("\n📊 GA Events games by age group:")
        for age, count in cursor.fetchall():
            print(f"   {age or 'Unknown':10} : {count:5} games")
        
        print("\n" + "═" * 70)
        print("✅ Cleanup analysis complete!")
        print("═" * 70)
        
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
