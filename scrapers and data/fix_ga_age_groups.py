"""
fix_ga_age_groups.py
====================
Fixes GA (Girls Academy) age groups in seedlinedata.db

Problem: 
  GA games have age_group values like 'U13', 'U14', etc.
  But the ranker expects 'G13', 'G12', etc. (matching ECNL format)

Solution:
  Extract the age group from team names (which have correct format)
  Example: "TopHat 13G GA" -> G13

Mapping:
  U13 -> G13  (13-year-olds)
  U14 -> G12  (12-year-olds)  
  U15 -> G11  (11-year-olds)
  U16 -> G10  (10-year-olds)
  U17 -> G09  (9-year-olds)
  U19 -> G0807 (8/7-year-olds)

Usage:
  python fix_ga_age_groups.py
  
  Or with custom path:
  python fix_ga_age_groups.py "C:\\path\\to\\seedlinedata.db"
"""

import sqlite3
import re
import os
import sys

# Default database path - UPDATE THIS if needed
DEFAULT_DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"


def extract_age_from_team_name(team_name):
    """
    Extract age group from GA team name
    Examples:
        'TopHat 13G GA' -> 'G13'
        'Blues FC 12G GA' -> 'G12'
        'HTX 08/07G GA' -> 'G0807'
    """
    if not team_name:
        return None
    
    # Pattern 1: 08/07G GA format
    match = re.search(r'(\d{2})/(\d{2})G\s*GA', team_name, re.IGNORECASE)
    if match:
        return f'G{match.group(1)}{match.group(2)}'  # G0807
    
    # Pattern 2: 13G GA format  
    match = re.search(r'(\d{2})G\s*GA', team_name, re.IGNORECASE)
    if match:
        return f'G{match.group(1)}'  # G13
    
    return None


def fix_ga_age_groups(db_path):
    """Fix all GA game age groups based on team names"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("   Please provide the correct path as an argument")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🔧 FIX GA AGE GROUPS")
    print("=" * 60)
    print(f"📁 Database: {db_path}")
    
    # Get current state
    cursor.execute("""
        SELECT age_group, COUNT(*) as count 
        FROM games 
        WHERE league='GA' 
        GROUP BY age_group
        ORDER BY count DESC
    """)
    results = cursor.fetchall()
    
    if not results:
        print("\n⚠️  No GA games found in database")
        conn.close()
        return False
    
    print("\n📊 Current GA age groups:")
    for row in results:
        print(f"   {row[0]}: {row[1]:,} games")
    
    # Get all GA games
    cursor.execute("""
        SELECT rowid, home_team, away_team, age_group 
        FROM games 
        WHERE league='GA'
    """)
    games = cursor.fetchall()
    
    print(f"\n📝 Processing {len(games):,} GA games...")
    
    # Find updates needed
    updates = []
    age_mapping = {}
    
    for rowid, home_team, away_team, current_age in games:
        # Try home_team first, then away_team
        new_age = extract_age_from_team_name(home_team)
        if not new_age:
            new_age = extract_age_from_team_name(away_team)
        
        if new_age:
            # Track mapping for display
            if current_age not in age_mapping:
                age_mapping[current_age] = new_age
            
            # Only update if different
            if new_age != current_age:
                updates.append((new_age, rowid))
    
    if not updates:
        print("\n✅ All GA age groups are already correct!")
        conn.close()
        return True
    
    # Show mapping
    print("\n🔄 Age mapping:")
    for old, new in sorted(age_mapping.items()):
        print(f"   {old} -> {new}")
    
    print(f"\n✏️  Updating {len(updates):,} games...")
    
    # Perform updates
    cursor.executemany("UPDATE games SET age_group = ? WHERE rowid = ?", updates)
    conn.commit()
    
    # Show new state
    cursor.execute("""
        SELECT age_group, COUNT(*) as count 
        FROM games 
        WHERE league='GA' 
        GROUP BY age_group
        ORDER BY count DESC
    """)
    print("\n📊 Updated GA age groups:")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]:,} games")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS! GA age groups have been fixed.")
    print("   Re-run your ranking script to include GA teams.")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    # Use command line argument if provided, otherwise use default
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DEFAULT_DB_PATH
    
    fix_ga_age_groups(db_path)
