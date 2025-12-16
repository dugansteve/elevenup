#!/usr/bin/env python3
"""
DATABASE CLEANUP SCRIPT v1
==========================

This script fixes all known data quality issues in the seedlinedata.db games table.

ISSUES FIXED:
=============
1. Team names with "ECNL G12", "ECNL G13" suffixes
2. Team names with "12G GA", "13G GA" suffixes (GA league pattern)
3. Team names with "RL G" suffix
4. "Regional League" prefix stuck to team names
5. Conference prefixes stuck (Eastern, Western, Virginia, etc.)
6. Fragment team names (Soccer, United, Union, Courage, Youth, Fusion)
7. Garbage team names (Box Score, Game Preview, TBDG, TBD)
8. Inconsistent age_group formats (G2013 vs G13)
9. Duplicate league values (ECNL RL vs ECNL-RL)
10. Case inconsistencies in team names

BACKUP:
=======
Creates automatic backup before making changes.

MODES:
======
--analyze   : Show what would be fixed (no changes)
--fix       : Actually fix the database
--export    : Export problematic records to CSV for review
"""

import sqlite3
import re
import os
import sys
import shutil
from datetime import datetime
from collections import defaultdict
import argparse


class DatabaseCleaner:
    def __init__(self, db_path):
        self.db_path = db_path
        self.backup_path = None
        self.stats = defaultdict(int)
        self.issues_found = defaultdict(list)
        
        # Known acronyms to preserve in title case
        self.acronyms = [
            'FC', 'SC', 'CF', 'AC', 'CD', 'SD', 'LA', 'NY', 'DC', 'KC',
            'SLSG', 'MVLA', 'VDA', 'PDA', 'NCFC', 'CASL', 'BRYC', 'AHFC',
            'PWSI', 'DKSC', 'TSC', 'RSC', 'YSC', 'ASC', 'OSC', 'ISC',
            'HTX', 'GSA', 'DUSC', 'SJEB', 'NEFC', 'CE', 'STX', 'NLSA',
            'SDA', 'BVB', 'SDSC', 'ALBION', 'RISE', 'LVU', 'VSA',
            'OK', 'LAFC', 'SCP', 'NTX', 'FHFC', 'ABSC', 'SA', 'RL',
            'COSC', 'MVLA', 'FSA', 'NJ', 'PA', 'TX', 'CA', 'FL', 'AZ',
            'CO', 'UT', 'OR', 'WA', 'IL', 'OH', 'MI', 'MO', 'VA', 'NC',
            'GA', 'SC', 'TN', 'IN', 'WI', 'MN', 'IA', 'NE', 'KS',
            'ECNL', 'ECNL-RL'
        ]
        
        # Garbage team names that should cause game deletion
        self.garbage_names = [
            'box score', 'game preview', 'preview', 'final', 'score',
            'details', 'result', 'results', 'schedule', 'standings',
            'roster', 'staff', 'view', 'box'
        ]
        
        # Fragment names that are likely parsing errors
        self.fragment_names = [
            'soccer', 'united', 'union', 'courage', 'youth', 'fusion',
            'academy', 'club', 'select', 'magic', 'thunder', 'rush',
            'hammerheads', 'athletic', 'sporting', 'inter', 'real'
        ]
        
        # TBD variants
        self.tbd_variants = ['tbd', 'tbdg', 'tbdb', 'tbds', 'to be determined']
    
    def create_backup(self):
        """Create timestamped backup of database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.dirname(self.db_path) or '.'
        backup_name = f"seedlinedata_backup_{timestamp}.db"
        self.backup_path = os.path.join(backup_dir, backup_name)
        
        print(f"📦 Creating backup: {self.backup_path}")
        shutil.copy2(self.db_path, self.backup_path)
        print(f"✅ Backup created successfully")
        return self.backup_path
    
    def clean_team_name(self, team_str):
        """
        Comprehensive team name cleaning.
        Returns (cleaned_name, list_of_issues_fixed)
        PRESERVES state suffixes like (Va), (Ca), (Az)
        """
        if not team_str:
            return "", []
        
        original = team_str
        issues = []
        
        team_str = team_str.strip()
        
        # FIRST: Extract and preserve state suffix if present
        # State suffixes are 2-letter codes in parentheses like (Va), (Ca), (Az)
        state_suffix_match = re.search(r'\s*\(([A-Za-z]{2})\)\s*$', team_str)
        state_suffix = None
        if state_suffix_match:
            state_suffix = state_suffix_match.group(1).capitalize()  # Normalize to "Va", "Ca", etc.
            team_str = team_str[:state_suffix_match.start()].strip()
        
        # 1. Remove "ECNL G12", "ECNL G13", "ECNL RL G12" suffixes
        ecnl_suffix = re.search(r'\s+ECNL\s*(?:RL)?\s*[GB]\d{2}\s*$', team_str, re.IGNORECASE)
        if ecnl_suffix:
            team_str = team_str[:ecnl_suffix.start()]
            issues.append('ecnl_age_suffix')
        
        # 2. Remove "12G GA", "13G GA", "08/07G GA" suffixes (GA league pattern)
        ga_suffix = re.search(r'\s+\d{2}(?:/\d{2})?G\s+GA\s*$', team_str, re.IGNORECASE)
        if ga_suffix:
            team_str = team_str[:ga_suffix.start()]
            issues.append('ga_age_suffix')
        
        # 3. Remove "RL G" or "RL B" suffix
        rl_suffix = re.search(r'\s+RL\s+[GB]\s*$', team_str, re.IGNORECASE)
        if rl_suffix:
            team_str = team_str[:rl_suffix.start()]
            issues.append('rl_suffix')
        
        # 3b. Remove " Rl" suffix (e.g., "PDA Blue Rl" → "PDA Blue")
        rl_simple = re.search(r'\s+Rl\s*$', team_str)
        if rl_simple:
            team_str = team_str[:rl_simple.start()]
            issues.append('rl_simple_suffix')
        
        # 3c. Remove "/07" or "/06" suffix (e.g., "FC Delco /07" → "FC Delco")
        slash_suffix = re.search(r'\s*/\d{2}\s*$', team_str)
        if slash_suffix:
            team_str = team_str[:slash_suffix.start()]
            issues.append('slash_suffix')
        
        # 3d. Remove " - /07" suffix (e.g., "Team Name - /07" → "Team Name")
        dash_slash = re.search(r'\s*-\s*/\d{2}\s*$', team_str)
        if dash_slash:
            team_str = team_str[:dash_slash.start()]
            issues.append('dash_slash_suffix')
        
        # 3e. Remove trailing dash artifacts
        team_str = re.sub(r'\s*-\s*$', '', team_str)
        
        # 4. Remove standalone "G" or "B" at end
        gender_suffix = re.search(r'\s+[GB]\s*$', team_str, re.IGNORECASE)
        if gender_suffix:
            team_str = team_str[:gender_suffix.start()]
            issues.append('gender_suffix')
        
        # 5. Remove "ECNL" or "ECNL RL" anywhere in name
        if re.search(r'\bECNL\s*RL\b', team_str, re.IGNORECASE):
            team_str = re.sub(r'\bECNL\s*RL\b', '', team_str, flags=re.IGNORECASE)
            issues.append('ecnl_rl_embedded')
        
        if re.search(r'\bECNL\b', team_str, re.IGNORECASE):
            team_str = re.sub(r'\bECNL\b', '', team_str, flags=re.IGNORECASE)
            issues.append('ecnl_embedded')
        
        # 6. Remove "GA" at end (league indicator)
        if re.search(r'\s+GA\s*$', team_str, re.IGNORECASE):
            team_str = re.sub(r'\s+GA\s*$', '', team_str, flags=re.IGNORECASE)
            issues.append('ga_suffix')
        
        # 7. Remove "Regional League" prefix (stuck or spaced)
        if team_str.lower().startswith('regional league'):
            team_str = re.sub(r'^Regional\s*League\s*', '', team_str, flags=re.IGNORECASE)
            issues.append('regional_league_prefix')
        
        # 8. Conference prefixes stuck to team names
        stuck_prefixes = [
            ('Ecnl', r'^Ecnl([A-Za-z])'),  # Ecnlrichmond United → richmond United
            ('ECNL', r'^ECNL([A-Za-z])'),  # ECNLRichmond United → Richmond United
            ('Yellow', r'^Yellow([A-Za-z])'),  # Yellowmvla → MVLA
            ('West', r'^West([a-z])'),  # Westslsg → SLSG (lowercase after West = stuck)
            ('South', r'^South([a-z])'),  # Southpda → PDA (lowercase after South = stuck)
            ('East', r'^East([a-z])'),  # Eastteam → Team (lowercase after East = stuck)
            ('North', r'^North([a-z])'),  # Northteam → Team
            ('Eastern', r'^Eastern([A-Za-z])'),
            ('Western', r'^Western([A-Za-z])'),
            ('Northern', r'^Northern([A-Za-z])'),
            ('Southern', r'^Southern([A-Za-z])'),
            ('Central', r'^Central([A-Za-z])'),
            ('Virginia', r'^Virginia([A-Za-z])'),
            ('Texas', r'^Texas([A-Za-z])'),
            ('Florida', r'^Florida([A-Za-z])'),
            ('California', r'^California([A-Za-z])'),
            ('Midwest', r'^Midwest([A-Za-z])'),
            ('East Girls', r'^East\s*Girls([a-z])'),
            ('East Boys', r'^East\s*Boys([a-z])'),
            ('West Girls', r'^West\s*Girls([a-z])'),
            ('West Boys', r'^West\s*Boys([a-z])'),
            ('South Girls', r'^South\s*Girls([a-z])'),  # South Girlsfc → fc
            ('South Boys', r'^South\s*Boys([a-z])'),
            ('North Girls', r'^North\s*Girls([a-z])'),
            ('North Boys', r'^North\s*Boys([a-z])'),
        ]
        
        for prefix_name, pattern in stuck_prefixes:
            match = re.match(pattern, team_str)
            if match:
                team_str = re.sub(pattern, r'\1', team_str)
                issues.append(f'{prefix_name.lower().replace(" ", "_")}_stuck')
        
        # 9. Remove age patterns anywhere
        # Birth years: 2008, 2013, 2008/2007
        team_str = re.sub(r'\b\d{4}(?:/\d{2,4})?\b', '', team_str)
        # Age groups: G12, B13, G08
        team_str = re.sub(r'\b[GB]\d{2}\b', '', team_str)
        # U-ages: U12, U13
        team_str = re.sub(r'\bU\d{2}\b', '', team_str)
        
        # 10. Remove conference direction words if standalone
        team_str = re.sub(r'\b(Eastern|Western|Northern|Southern|Central)\s+(Boys?|Girls?)\b', '', team_str, flags=re.IGNORECASE)
        
        # 11. Clean up artifacts
        team_str = re.sub(r'^[-–—\s]+', '', team_str)  # Leading dashes
        team_str = re.sub(r'[-–—\s]+$', '', team_str)  # Trailing dashes
        team_str = re.sub(r'\s+', ' ', team_str)       # Multiple spaces
        team_str = team_str.strip(' -–—,.')
        
        # 12. Title case with acronym preservation
        if team_str:
            team_str = team_str.title()
            for acronym in self.acronyms:
                pattern = rf'\b{acronym.title()}\b'
                team_str = re.sub(pattern, acronym, team_str, flags=re.IGNORECASE)
        
        # 13. RE-ADD STATE SUFFIX if we extracted one earlier
        # This ensures state suffixes like (Va), (Ca), (Az) are preserved
        if state_suffix and team_str:
            team_str = f"{team_str.strip()} ({state_suffix})"
        
        if team_str != original and not issues:
            issues.append('whitespace_cleanup')
        
        return team_str.strip(), issues
    
    def is_garbage_name(self, team_str):
        """Check if team name is garbage that should be deleted"""
        if not team_str:
            return True, "empty"
        
        team_lower = team_str.lower().strip()
        
        # Check garbage names
        if team_lower in self.garbage_names:
            return True, "garbage_name"
        
        # Check TBD variants
        if team_lower in self.tbd_variants:
            return True, "tbd_variant"
        
        if team_lower.startswith('tbd'):
            return True, "tbd_prefix"
        
        # Too short (less than 3 chars after cleaning)
        if len(team_str) < 3:
            return True, "too_short"
        
        # Pure numbers
        if team_str.replace(' ', '').replace('-', '').isdigit():
            return True, "pure_numbers"
        
        # Date patterns leaked through (e.g., "Mar 15" or "March 2025")
        # But NOT team names like "Maryland United"
        if re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d', team_str, re.IGNORECASE):
            return True, "date_pattern"
        if re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s', team_str, re.IGNORECASE):
            return True, "date_pattern"
        
        # Time patterns
        if re.search(r'\d{1,2}:\d{2}', team_str):
            return True, "time_pattern"
        
        # Location leaked as team name
        location_keywords = ['complex', 'stadium', 'field', 'park', 'high school', 'center', 'facility']
        if any(kw in team_lower for kw in location_keywords):
            return True, "location_name"
        
        return False, None
    
    def is_fragment_name(self, team_str):
        """Check if team name is a fragment (partial team name)"""
        team_lower = team_str.lower().strip()
        
        if team_lower in self.fragment_names:
            return True, "fragment_name"
        
        return False, None
    
    def normalize_league(self, league_str):
        """Normalize league names"""
        if not league_str:
            return league_str, False
        
        league_upper = league_str.upper().strip()
        
        # Normalize ECNL RL variants
        if league_upper in ['ECNL RL', 'ECNL-RL', 'ECNLRL', 'ECNL_RL']:
            return 'ECNL-RL', league_str != 'ECNL-RL'
        
        if league_upper == 'ECNL':
            return 'ECNL', False
        
        if league_upper == 'GA':
            return 'GA', False
        
        return league_str, False
    
    def normalize_age_group(self, age_str):
        """Normalize age group to standard format (G12, B13, etc.)"""
        if not age_str or age_str == 'Unknown':
            return age_str, False
        
        original = age_str
        
        # Already in correct format
        if re.match(r'^[GB]\d{2}$', age_str):
            return age_str, False
        
        # Handle G08/07 format
        if re.match(r'^[GB]\d{2}/\d{2}$', age_str):
            return age_str.upper(), age_str != age_str.upper()
        
        # Handle corrupted age groups like G-1193, G-1901, G-1904
        # These appear to be parsing errors - mark as Unknown
        if re.match(r'^[GB]-\d+$', age_str):
            return 'Unknown', True
        
        # Handle G14 (too old, mark as Unknown)
        if re.match(r'^[GB]14$', age_str):
            return 'Unknown', True
        
        # Handle G07/06 format - normalize to G07
        match = re.match(r'^([GB])(\d{2})/(\d{2})$', age_str)
        if match:
            return f"{match.group(1).upper()}{match.group(2)}/{match.group(3)}", age_str != f"{match.group(1).upper()}{match.group(2)}/{match.group(3)}"
        
        # Convert G2013 to G13
        match = re.match(r'^([GB])(\d{4})$', age_str)
        if match:
            gender = match.group(1).upper()
            year = int(match.group(2))
            age_num = year - 2000
            return f"{gender}{age_num:02d}", True
        
        # Convert G2008/2007 to G08/07
        match = re.match(r'^([GB])(\d{4})/(\d{4})$', age_str)
        if match:
            gender = match.group(1).upper()
            year1 = int(match.group(2)) - 2000
            year2 = int(match.group(3)) - 2000
            return f"{gender}{year1:02d}/{year2:02d}", True
        
        # Handle lowercase
        if re.match(r'^[gb]\d{2}$', age_str):
            return age_str.upper(), True
        
        return age_str, False
    
    def analyze(self):
        """Analyze database and report issues without making changes"""
        print("\n" + "=" * 70)
        print("📊 DATABASE ANALYSIS")
        print("=" * 70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total counts
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]
        print(f"\nTotal games in database: {total_games:,}")
        
        # Analyze all games
        cursor.execute("""
            SELECT id, home_team, away_team, age_group, league, game_date
            FROM games
        """)
        
        games_to_delete = []
        games_to_update = []
        fragment_warnings = []
        
        for row in cursor.fetchall():
            game_id, home_team, away_team, age_group, league, game_date = row
            updates = {}
            
            # Check home team
            is_garbage, reason = self.is_garbage_name(home_team)
            if is_garbage:
                games_to_delete.append((game_id, f"home_team: {home_team} ({reason})"))
                continue
            
            # Check away team
            is_garbage, reason = self.is_garbage_name(away_team)
            if is_garbage:
                games_to_delete.append((game_id, f"away_team: {away_team} ({reason})"))
                continue
            
            # Clean team names
            clean_home, home_issues = self.clean_team_name(home_team)
            clean_away, away_issues = self.clean_team_name(away_team)
            
            if home_issues:
                updates['home_team'] = (home_team, clean_home, home_issues)
            if away_issues:
                updates['away_team'] = (away_team, clean_away, away_issues)
            
            # Check for fragment names (warning only)
            is_fragment, _ = self.is_fragment_name(clean_home)
            if is_fragment:
                fragment_warnings.append((game_id, 'home', clean_home))
            
            is_fragment, _ = self.is_fragment_name(clean_away)
            if is_fragment:
                fragment_warnings.append((game_id, 'away', clean_away))
            
            # Check league normalization
            norm_league, league_changed = self.normalize_league(league)
            if league_changed:
                updates['league'] = (league, norm_league, ['league_normalization'])
            
            # Check age group normalization
            norm_age, age_changed = self.normalize_age_group(age_group)
            if age_changed:
                updates['age_group'] = (age_group, norm_age, ['age_normalization'])
            
            if updates:
                games_to_update.append((game_id, updates))
        
        conn.close()
        
        # Report findings
        print(f"\n{'=' * 70}")
        print("FINDINGS")
        print('=' * 70)
        
        print(f"\n🗑️  Games to DELETE (garbage/TBD teams): {len(games_to_delete):,}")
        if games_to_delete[:10]:
            print("   Sample:")
            for game_id, reason in games_to_delete[:10]:
                print(f"      ID {game_id}: {reason}")
            if len(games_to_delete) > 10:
                print(f"      ... and {len(games_to_delete) - 10} more")
        
        print(f"\n📝 Games to UPDATE (team name/league/age fixes): {len(games_to_update):,}")
        
        # Categorize updates
        update_categories = defaultdict(int)
        for game_id, updates in games_to_update:
            for field, (old, new, issues) in updates.items():
                for issue in issues:
                    update_categories[f"{field}: {issue}"] += 1
        
        if update_categories:
            print("   By category:")
            for category, count in sorted(update_categories.items(), key=lambda x: -x[1]):
                print(f"      {category}: {count:,}")
        
        print(f"\n⚠️  Fragment name WARNINGS (may need manual review): {len(fragment_warnings):,}")
        if fragment_warnings[:10]:
            print("   Sample:")
            for game_id, field, name in fragment_warnings[:10]:
                print(f"      ID {game_id}: {field} = '{name}'")
        
        # Store for later use
        self.games_to_delete = games_to_delete
        self.games_to_update = games_to_update
        self.fragment_warnings = fragment_warnings
        
        return {
            'total': total_games,
            'to_delete': len(games_to_delete),
            'to_update': len(games_to_update),
            'fragments': len(fragment_warnings)
        }
    
    def fix(self, delete_fragments=False):
        """Apply fixes to the database"""
        print("\n" + "=" * 70)
        print("🔧 APPLYING FIXES")
        print("=" * 70)
        
        # Create backup first
        self.create_backup()
        
        # Run analysis if not done
        if not hasattr(self, 'games_to_delete'):
            self.analyze()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete garbage games
        print(f"\n🗑️  Deleting {len(self.games_to_delete):,} games with garbage teams...")
        deleted = 0
        for game_id, reason in self.games_to_delete:
            try:
                cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
                deleted += 1
            except Exception as e:
                print(f"   ⚠️ Error deleting {game_id}: {e}")
        print(f"   ✅ Deleted {deleted:,} games")
        
        # Update games
        print(f"\n📝 Updating {len(self.games_to_update):,} games...")
        updated = 0
        for game_id, updates in self.games_to_update:
            try:
                for field, (old, new, issues) in updates.items():
                    cursor.execute(f"UPDATE games SET {field} = ? WHERE id = ?", (new, game_id))
                updated += 1
            except Exception as e:
                print(f"   ⚠️ Error updating {game_id}: {e}")
        print(f"   ✅ Updated {updated:,} games")
        
        # Optionally delete fragment names
        if delete_fragments and self.fragment_warnings:
            print(f"\n🗑️  Deleting {len(self.fragment_warnings):,} games with fragment teams...")
            frag_deleted = 0
            fragment_ids = set(gid for gid, _, _ in self.fragment_warnings)
            for game_id in fragment_ids:
                try:
                    cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
                    frag_deleted += 1
                except Exception as e:
                    pass
            print(f"   ✅ Deleted {frag_deleted:,} games")
        
        conn.commit()
        
        # Remove duplicates
        print("\n🔄 Removing duplicate games...")
        duplicates_removed = self.remove_duplicates(cursor)
        print(f"   ✅ Removed {duplicates_removed:,} duplicate games")
        
        conn.commit()
        
        # Vacuum to reclaim space
        print("\n🧹 Vacuuming database...")
        cursor.execute("VACUUM")
        conn.close()
        
        print(f"\n✅ Database cleanup complete!")
        print(f"   Backup saved to: {self.backup_path}")
    
    def remove_duplicates(self, cursor):
        """Remove duplicate games, keeping only one copy of each unique game"""
        # Find all duplicates (same date + same teams + same score)
        cursor.execute("""
            SELECT game_date, home_team, away_team, home_score, away_score, 
                   GROUP_CONCAT(id) as ids, COUNT(*) as cnt
            FROM games
            GROUP BY game_date, home_team, away_team, home_score, away_score
            HAVING cnt > 1
        """)
        
        total_removed = 0
        for row in cursor.fetchall():
            ids = row[5].split(',')
            # Keep the first ID, delete the rest
            ids_to_delete = ids[1:]  # Skip first one
            for game_id in ids_to_delete:
                cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
                total_removed += 1
        
        return total_removed
    
    def export_issues(self, output_file="db_issues_export.csv"):
        """Export problematic records to CSV for review"""
        import csv
        
        print(f"\n📤 Exporting issues to {output_file}...")
        
        # Run analysis if not done
        if not hasattr(self, 'games_to_delete'):
            self.analyze()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        rows = []
        
        # Add games to delete
        for game_id, reason in self.games_to_delete:
            cursor.execute("""
                SELECT home_team, away_team, age_group, league, game_date 
                FROM games WHERE id = ?
            """, (game_id,))
            result = cursor.fetchone()
            if result:
                rows.append({
                    'id': game_id,
                    'action': 'DELETE',
                    'reason': reason,
                    'home_team': result[0],
                    'away_team': result[1],
                    'age_group': result[2],
                    'league': result[3],
                    'game_date': result[4],
                    'suggested_home': '',
                    'suggested_away': ''
                })
        
        # Add games to update
        for game_id, updates in self.games_to_update:
            cursor.execute("""
                SELECT home_team, away_team, age_group, league, game_date 
                FROM games WHERE id = ?
            """, (game_id,))
            result = cursor.fetchone()
            if result:
                suggested_home = updates.get('home_team', (None, result[0], []))[1]
                suggested_away = updates.get('away_team', (None, result[1], []))[1]
                issues = []
                for field, (old, new, issue_list) in updates.items():
                    issues.extend([f"{field}:{i}" for i in issue_list])
                
                rows.append({
                    'id': game_id,
                    'action': 'UPDATE',
                    'reason': '; '.join(issues),
                    'home_team': result[0],
                    'away_team': result[1],
                    'age_group': result[2],
                    'league': result[3],
                    'game_date': result[4],
                    'suggested_home': suggested_home,
                    'suggested_away': suggested_away
                })
        
        # Add fragment warnings
        for game_id, field, name in self.fragment_warnings:
            cursor.execute("""
                SELECT home_team, away_team, age_group, league, game_date 
                FROM games WHERE id = ?
            """, (game_id,))
            result = cursor.fetchone()
            if result:
                rows.append({
                    'id': game_id,
                    'action': 'WARNING',
                    'reason': f'{field}_fragment: {name}',
                    'home_team': result[0],
                    'away_team': result[1],
                    'age_group': result[2],
                    'league': result[3],
                    'game_date': result[4],
                    'suggested_home': '',
                    'suggested_away': ''
                })
        
        conn.close()
        
        # Write CSV
        fieldnames = ['id', 'action', 'reason', 'home_team', 'away_team', 
                      'age_group', 'league', 'game_date', 'suggested_home', 'suggested_away']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✅ Exported {len(rows):,} records to {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Database Cleanup Script for Seedline Games Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python database_cleanup_v1.py --analyze                    # Just analyze, no changes
  python database_cleanup_v1.py --fix                        # Fix all issues
  python database_cleanup_v1.py --fix --delete-fragments     # Fix and delete fragment names
  python database_cleanup_v1.py --export                     # Export issues to CSV
        """
    )
    
    parser.add_argument('--db', type=str, default='seedlinedata.db',
                        help='Path to database file (default: seedlinedata.db)')
    parser.add_argument('--analyze', action='store_true',
                        help='Analyze database and show what would be fixed')
    parser.add_argument('--fix', action='store_true',
                        help='Actually fix the database (creates backup first)')
    parser.add_argument('--export', action='store_true',
                        help='Export problematic records to CSV')
    parser.add_argument('--delete-fragments', action='store_true',
                        help='Also delete games with fragment team names')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.db):
        print(f"❌ Database not found: {args.db}")
        sys.exit(1)
    
    cleaner = DatabaseCleaner(args.db)
    
    print("=" * 70)
    print("🧹 DATABASE CLEANUP SCRIPT v1")
    print("=" * 70)
    print(f"Database: {args.db}")
    
    if args.analyze or (not args.fix and not args.export):
        results = cleaner.analyze()
        
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total games:        {results['total']:,}")
        print(f"Games to DELETE:    {results['to_delete']:,}")
        print(f"Games to UPDATE:    {results['to_update']:,}")
        print(f"Fragment warnings:  {results['fragments']:,}")
        print("\nRun with --fix to apply changes (backup will be created)")
        print("Run with --export to save issues to CSV for review")
    
    if args.export:
        cleaner.export_issues()
    
    if args.fix:
        confirm = input("\n⚠️  This will modify the database. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            cleaner.fix(delete_fragments=args.delete_fragments)
        else:
            print("❌ Cancelled")


if __name__ == "__main__":
    main()
