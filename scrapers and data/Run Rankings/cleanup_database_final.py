#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATABASE CLEANUP TOOL v3 - COMPREHENSIVE FIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This script performs comprehensive cleanup of the seedlinedata.db:

1. DUPLICATE REMOVAL
   - Identifies duplicates by (home_team, away_team, normalized_date, league)
   - Keeps the most recent version with scores
   - Handles date format variations (11/16/2025 vs 2025-11-16)

2. BAD TEAM NAME REMOVAL
   - "Box Score" (scraping artifact - found in 652+ games)
   - "Regional League" (standalone)
   - Date/time strings captured as team names
   - Conference/venue names captured as teams
   - Empty or too-short names

3. TEAM NAME NORMALIZATION
   - Removes "Regional League" prefix (stuck to team names)
   - Removes conference prefixes (Virginia, Eastern, Western, etc.)
   - Removes league/age suffixes (ECNL RL G13, etc.)
   - Standardizes team names for consistency

4. LEAGUE FIELD CORRECTION
   - Detects actual league from team name (overrides DB field)
   - Fixes teams with "ECNL RL" in name but stored as league='ECNL'
   - Normalizes "ECNL RL" (space) to "ECNL-RL" (hyphen)

5. DATE NORMALIZATION
   - Converts all dates to YYYY-MM-DD format

USAGE:
  python cleanup_database_final.py                    # Interactive mode
  python cleanup_database_final.py --dry-run          # Preview changes only
  python cleanup_database_final.py --auto             # Auto-confirm all changes
  python cleanup_database_final.py path/to/db.db      # Specify database path

CAN BE IMPORTED:
  from cleanup_database_final import DatabaseCleanup, cleanup_database
  
  # Quick cleanup
  stats = cleanup_database('seedlinedata.db', auto_confirm=True)
  
  # Or use the class
  cleaner = DatabaseCleanup('seedlinedata.db')
  stats = cleaner.run(auto_confirm=True)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sqlite3
import os
import re
import sys
import argparse
from datetime import datetime
from collections import defaultdict
from pathlib import Path


class DatabaseCleanup:
    """Comprehensive database cleanup for seedlinedata.db"""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BAD TEAM NAME PATTERNS
    # These are patterns that indicate scraping artifacts, not real teams
    # ═══════════════════════════════════════════════════════════════════════════
    BAD_TEAM_PATTERNS = [
        # Scraping artifacts
        r'^Regional League$',
        r'^- Regional League',
        r'^Box Score',
        r'^Game Status',
        r'^Location$',
        r'^Conference$',
        r'^Unknown$',
        r'^TBD$',
        r'^BYE$',
        r'^Forfeit',
        r'^Canceled',
        r'^Postponed',
        
        # Dates captured as team names
        r'^\d{1,2}/\d{1,2}/\d{2,4}',           # 11/16/2025 or 11/16/25
        r'^\d{4}-\d{2}-\d{2}',                 # 2025-11-16
        r'^[A-Z][a-z]{2}\s+\d{1,2},?\s*\d{4}', # Nov 16, 2025
        r'^\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}',   # 16 Nov 2025
        
        # Times captured as team names
        r'^\d{1,2}:\d{2}\s*(AM|PM)?$',         # 3:00 PM
        r'^\d{1,2}:\d{2}:\d{2}',               # 15:30:00
        
        # Full datetime strings
        r'^\w+\s+\d{1,2},\s*\d{4}\s+\d{1,2}:\d{2}',
        
        # Score/field markers
        r'^#\d+$',
        r'^Score$',
        r'^Home$',
        r'^Away$',
        r'^vs\.?$',
        r'^Venue$',
        r'^Field\s*\d*$',
        r'^Pitch\s*\d*$',
        r'^Stadium$',
        
        # League/conference names as teams
        r'^STXCL$',
        r'^NTX$',
        r'^S\.?Cal$',
        r'^SoCal$',
        r'^RL$',
        r'^ECNL$',
        r'^ECNL-RL$',
        r'^ECNL RL$',
        r'^GA$',
        r'^Girls Academy$',
        r'^MLS NEXT$',
        
        # Venue names (common ones we've seen)
        r'^Truist Soccer Complex',
        r'^Bryan Park$',
        r'^Toyota Stadium',
        r'^SoccerPlex',
        r'Training (Center|Facility|Ground)',
        
        # School venues
        r'Middle School$',
        r'High School$',
        r'Elementary School$',
        r'University$',
        r'^Athletic Complex$',
        
        # Generic placeholders
        r'^Team\s*\d*$',
        r'^Opponent$',
        r'^N/A$',
        r'^None$',
        r'^-$',
        r'^\.$',
    ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFERENCE PREFIXES
    # These get concatenated to team names during scraping
    # Example: "VirginiaGreat Falls Reston SC" should be "Great Falls Reston SC"
    # ═══════════════════════════════════════════════════════════════════════════
    CONFERENCE_PREFIXES = [
        r'^Virginia(?=[A-Z])',          # VirginiaGreat Falls → Great Falls
        r'^Eastern(?=[A-Z])',           # EasternAHFC → AHFC
        r'^Western\s*[AB]?(?=[A-Z])',   # WesternFC Dallas → FC Dallas
        r'^Central\s*Girls?(?=[A-Z])',  # Central GirlsFC → FC
        r'^South(?=[A-Z])',             # SouthTexas Rush → Texas Rush
        r'^North(?=[A-Z])',             
        r'^East(?=[A-Z])',              
        r'^West(?=[A-Z])',              
        r'^south\s*Girls?(?=[A-Z])',    # south GirlsTeam → Team
        r'^NB(?=[A-Z])',                # NBSome Team → Some Team
        r'^RL(?=[A-Z])',                # RLTeam Name → Team Name
        r'^GLA(?=[A-Z])',               # GLATeam → Team (Great Lakes Area)
        r'^Midwest(?=[A-Z])',
        r'^Southeast(?=[A-Z])',
        r'^Southwest(?=[A-Z])',
        r'^Northeast(?=[A-Z])',
        r'^Northwest(?=[A-Z])',
        r'^Atlantic(?=[A-Z])',
        r'^Pacific(?=[A-Z])',
        r'^Mountain(?=[A-Z])',
        r'^Plains(?=[A-Z])',
        r'^Texas(?=[A-Z])',             # TexasFC Dallas → FC Dallas
        r'^Florida(?=[A-Z])',
        r'^California(?=[A-Z])',
        r'^Ohio(?=[A-Z])',
    ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SUFFIXES TO REMOVE
    # League/age/region suffixes that should be stripped from team names
    # Example: "FC Dallas ECNL RL G13" should be "FC Dallas"
    # ═══════════════════════════════════════════════════════════════════════════
    SUFFIXES_TO_REMOVE = [
        # Full league + region + age combinations
        r'\s+ECNL\s+RL\s+STXCL\s*G?\d*\s*$',
        r'\s+ECNL\s+RL\s+NTX\s*G?\d*\s*$',
        r'\s+ECNL\s+RL\s+SoCal\s*G?\d*\s*$',
        r'\s+ECNL\s+RL\s+S\.?Cal\s*G?\d*\s*$',
        r'\s+ECNL\s+RL\s+GLA\s*G?\d*\s*$',
        
        # League + age combinations
        r'\s+ECNL\s+RL\s*G?\d*\s*$',
        r'\s+ECNL-RL\s*G?\d*\s*$',
        r'\s+ECNL\s+G?\d*\s*$',
        r'\s+-\s+ECNL\s*$',
        r'\s+-\s+ECNL\s+RL\s*$',
        
        # RL variations
        r'\s+RL\s+STXCL\s*G?\d*\s*$',
        r'\s+RL\s+NTX\s*G?\d*\s*$',
        r'\s+RL\s+SoCal\s*G?\d*\s*$',
        r'\s+RL\s+GLA\s*G?\d*\s*$',
        r'\s+RL\s+G\s*\d*\s*$',
        r'\s+RL\s+B\s*\d*\s*$',
        r'\s+RL\s*$',
        
        # GA variations
        r'\s+G\d+\s+GA\s*$',           # G13 GA
        r'\s+\d+G\s+GA\s*$',           # 13G GA
        r'\s+GA\s+G?\d*\s*$',
        r'\s+GA\s*$',
        
        # Region codes alone
        r'\s+STXCL\s*$',
        r'\s+NTX\s*$',
        r'\s+SoCal\s*$',
        r'\s+S\.?Cal\s*$',
        r'\s+GLA\s*$',
        
        # Age group suffixes
        r'\s+G\d{2}/\d{2}\s*$',        # G13/14
        r'\s+G\d{2}\s*$',              # G13
        r'\s+B\d{2}\s*$',              # B13 (boys)
        r'\s+U\d{2}\s*$',              # U13
        r'\s+\d{4}\s*$',               # 2013 (birth year)
        r'\s+20(09|10|11|12|13|14|15|16|17)\s*$',  # Specific birth years
        
        # Other
        r'\s+GLA\s*$',                 # Great Lakes Area
        r'\s+PRE\s*$',                 # Pre-ECNL/Academy
        r'\s+Premier\s*$',
        r'\s+Elite\s*$',
        r'\s+Academy\s*$',
        r'\s+I+\s*$',                  # Roman numerals I, II, III
    ]
    
    def __init__(self, db_path, dry_run=False, verbose=True):
        """
        Initialize the cleanup tool
        
        Args:
            db_path: Path to the database file
            dry_run: If True, only analyze without making changes
            verbose: If True, print detailed output
        """
        self.db_path = Path(db_path) if not isinstance(db_path, Path) else db_path
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Statistics tracking
        self.stats = {
            'duplicates_removed': 0,
            'bad_teams_removed': 0,
            'team_names_cleaned': 0,
            'leagues_corrected': 0,
            'dates_normalized': 0,
            'total_before': 0,
            'total_after': 0,
        }
        
        # Compile patterns for performance
        self._bad_patterns = [re.compile(p, re.IGNORECASE) for p in self.BAD_TEAM_PATTERNS]
        self._prefix_patterns = [re.compile(p, re.IGNORECASE) for p in self.CONFERENCE_PREFIXES]
        self._suffix_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUFFIXES_TO_REMOVE]
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def backup_database(self):
        """Create a timestamped backup before making changes"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{timestamp}.db"
        
        source = sqlite3.connect(self.db_path)
        dest = sqlite3.connect(backup_path)
        
        with dest:
            source.backup(dest)
        
        source.close()
        dest.close()
        
        if self.verbose:
            print(f"✅ Backup created: {backup_path}")
        return backup_path
    
    def normalize_date(self, date_str):
        """Convert any date format to YYYY-MM-DD"""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Already correct format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # MM/DD/YYYY or M/D/YYYY format
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
        if match:
            month, day, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # MM/DD/YY format
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2})$', date_str)
        if match:
            month, day, year = match.groups()
            year = f"20{year}" if int(year) < 50 else f"19{year}"
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Month name format (Nov 16, 2025 or Nov 16 2025)
        months = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        
        for month_name, month_num in months.items():
            if month_name in date_str.lower():
                match = re.search(r'(\d{1,2}),?\s*(\d{4})', date_str)
                if match:
                    day = match.group(1).zfill(2)
                    year = match.group(2)
                    return f"{year}-{month_num}-{day}"
        
        # DD Month YYYY format (16 Nov 2025)
        match = re.match(r'^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})$', date_str)
        if match:
            day, month_str, year = match.groups()
            month_num = months.get(month_str[:3].lower())
            if month_num:
                return f"{year}-{month_num}-{day.zfill(2)}"
        
        return date_str
    
    def is_bad_team_name(self, name):
        """Check if team name is invalid/artifact"""
        if not name:
            return True
        
        name = str(name).strip()
        
        # Length checks
        if len(name) < 3:
            return True
        if len(name) > 100:
            return True
        
        # Pure numbers
        if re.match(r'^\d+$', name):
            return True
        
        # Check against bad patterns
        for pattern in self._bad_patterns:
            if pattern.match(name):
                return True
        
        return False
    
    def detect_league_from_name(self, name):
        """
        Detect the actual league from team name
        This overrides the database league field when there's a mismatch
        """
        if not name:
            return None
            
        name_upper = str(name).upper()
        
        # ECNL-RL indicators (check first - more specific)
        ecnl_rl_indicators = [
            'ECNL RL', 'ECNL-RL', ' RL G', ' RL B', 
            'RL NTX', 'RL STXCL', 'RL SOCAL', 'RL GLA',
            ' RL '
        ]
        if any(x in name_upper for x in ecnl_rl_indicators):
            return 'ECNL-RL'
        
        # GA indicators
        ga_indicators = [' GA ', ' GA$', '13G GA', '14G GA', '15G GA', 
                        'GIRLS ACADEMY', '12G GA', '11G GA']
        if any(x in name_upper or name_upper.endswith(x.rstrip('$')) 
               for x in ga_indicators):
            return 'GA'
        
        # Pure ECNL (must check after RL to avoid false positives)
        if 'ECNL' in name_upper and 'RL' not in name_upper:
            return 'ECNL'
        
        return None
    
    def clean_team_name(self, name):
        """
        Clean up a team name by removing prefixes and suffixes
        Returns the cleaned name
        """
        if not name:
            return name
            
        original = str(name).strip()
        name = original
        
        # Remove leading dash/hyphen
        name = re.sub(r'^-\s*', '', name)
        
        # Remove "Regional League" prefix
        name = re.sub(r'^Regional\s*League\s*-?\s*', '', name, flags=re.IGNORECASE)
        
        # Remove conference prefixes
        for pattern in self._prefix_patterns:
            name = pattern.sub('', name)
        
        # Remove league/age suffixes (apply multiple times to catch nested)
        for _ in range(3):  # Multiple passes
            for pattern in self._suffix_patterns:
                name = pattern.sub('', name)
        
        # Clean up whitespace
        name = ' '.join(name.split())
        
        # If we've cleaned it to nothing, return original
        return name if name and len(name) >= 3 else original
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_database(self):
        """
        Analyze database and identify all issues
        Returns a dict with analysis results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print("📊 ANALYZING DATABASE")
            print(f"{'='*60}")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM games")
        self.stats['total_before'] = cursor.fetchone()[0]
        
        if self.verbose:
            print(f"Total games: {self.stats['total_before']:,}")
        
        # Analyze league distribution
        if self.verbose:
            print("\nLeague distribution (before cleanup):")
            cursor.execute("""
                SELECT league, COUNT(*) as cnt 
                FROM games 
                GROUP BY league 
                ORDER BY cnt DESC
            """)
            for league, count in cursor.fetchall():
                print(f"  {league or 'NULL'}: {count:,}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Find bad team names
        # ─────────────────────────────────────────────────────────────────────
        cursor.execute("""
            SELECT DISTINCT home_team FROM games 
            UNION 
            SELECT DISTINCT away_team FROM games
        """)
        all_teams = [row[0] for row in cursor.fetchall()]
        
        bad_teams = [t for t in all_teams if self.is_bad_team_name(t)]
        
        if self.verbose:
            print(f"\n🚫 Bad team names found: {len(bad_teams)}")
            if bad_teams:
                print("  Examples:")
                for t in sorted(bad_teams, key=lambda x: str(x))[:10]:
                    print(f"    - '{t}'")
        
        # Count games with bad teams
        bad_team_games = 0
        for team in bad_teams:
            cursor.execute(
                "SELECT COUNT(*) FROM games WHERE home_team = ? OR away_team = ?",
                (team, team)
            )
            bad_team_games += cursor.fetchone()[0]
        
        if self.verbose:
            print(f"  Games affected: ~{bad_team_games:,}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Find teams needing name cleanup
        # ─────────────────────────────────────────────────────────────────────
        teams_to_clean = []
        for team in all_teams:
            if team and not self.is_bad_team_name(team):
                cleaned = self.clean_team_name(team)
                if cleaned != team:
                    teams_to_clean.append((team, cleaned))
        
        if self.verbose:
            print(f"\n🔧 Team names needing cleanup: {len(teams_to_clean)}")
            if teams_to_clean:
                print("  Examples:")
                for orig, cleaned in teams_to_clean[:5]:
                    print(f"    '{orig[:50]}' → '{cleaned}'")
        
        # ─────────────────────────────────────────────────────────────────────
        # Find league corrections needed
        # ─────────────────────────────────────────────────────────────────────
        cursor.execute("""
            SELECT COUNT(*) FROM games
            WHERE league = 'ECNL' 
            AND (home_team LIKE '%ECNL RL%' 
                 OR home_team LIKE '% RL G%'
                 OR home_team LIKE '% RL B%'
                 OR away_team LIKE '%ECNL RL%' 
                 OR away_team LIKE '% RL G%'
                 OR away_team LIKE '% RL B%')
        """)
        wrong_league_count = cursor.fetchone()[0]
        
        # Count league normalization needed (space vs hyphen)
        cursor.execute("SELECT COUNT(*) FROM games WHERE league = 'ECNL RL'")
        space_league_count = cursor.fetchone()[0]
        
        if self.verbose:
            print(f"\n⚠️  League corrections needed:")
            print(f"  'ECNL RL' → 'ECNL-RL' (normalize): {space_league_count:,}")
            print(f"  Wrong league field (from team names): {wrong_league_count:,}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Find duplicates
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print("\n🔍 Analyzing duplicates...")
        
        cursor.execute("""
            SELECT id, game_date, game_time, home_team, away_team, 
                   home_score, away_score, league, scraped_at
            FROM games
            ORDER BY home_team, away_team, game_date, scraped_at DESC
        """)
        
        all_games = cursor.fetchall()
        game_groups = defaultdict(list)
        
        for row in all_games:
            id_, game_date, game_time, home_team, away_team, \
                home_score, away_score, league, scraped_at = row
            
            norm_date = self.normalize_date(game_date)
            
            # Key for duplicate detection
            # Note: We include league in key, but normalized
            norm_league = 'ECNL-RL' if league in ['ECNL RL', 'ECNL-RL'] else league
            key = (home_team, away_team, norm_date, norm_league)
            
            game_groups[key].append({
                'id': id_,
                'game_date': game_date,
                'home_score': home_score,
                'away_score': away_score,
                'scraped_at': scraped_at or ''
            })
        
        duplicate_count = sum(1 for games in game_groups.values() if len(games) > 1)
        duplicate_records = sum(len(games) - 1 for games in game_groups.values() if len(games) > 1)
        
        if self.verbose:
            print(f"  Duplicate game groups: {duplicate_count:,}")
            print(f"  Records to remove: {duplicate_records:,}")
            
            # Show examples of duplicates
            if duplicate_count > 0:
                print("\n  Sample duplicates:")
                shown = 0
                for key, games in game_groups.items():
                    if len(games) > 1 and shown < 3:
                        home, away, date, league = key
                        print(f"    {home[:30]} vs {away[:30]}")
                        print(f"      Date: {date}, League: {league}")
                        print(f"      Found {len(games)} copies")
                        shown += 1
        
        # ─────────────────────────────────────────────────────────────────────
        # Find dates needing normalization
        # ─────────────────────────────────────────────────────────────────────
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE game_date NOT LIKE '____-__-__'
            AND game_date IS NOT NULL
        """)
        non_standard_dates = cursor.fetchone()[0]
        
        if self.verbose:
            print(f"\n📅 Dates needing normalization: {non_standard_dates:,}")
        
        conn.close()
        
        return {
            'bad_teams': bad_teams,
            'bad_team_games': bad_team_games,
            'teams_to_clean': teams_to_clean,
            'duplicate_records': duplicate_records,
            'game_groups': game_groups,
            'non_standard_dates': non_standard_dates,
            'wrong_league_count': wrong_league_count,
            'space_league_count': space_league_count,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CLEANUP METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def perform_cleanup(self, analysis):
        """Perform all cleanup operations"""
        if self.dry_run:
            if self.verbose:
                print(f"\n{'='*60}")
                print("📝 DRY RUN - No changes will be made")
                print(f"{'='*60}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print("🔧 PERFORMING CLEANUP")
            print(f"{'='*60}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Step 1: Remove games with bad team names
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print("\n1️⃣  Removing games with bad team names...")
        
        bad_teams = analysis['bad_teams']
        if bad_teams:
            for team in bad_teams:
                cursor.execute(
                    "DELETE FROM games WHERE home_team = ? OR away_team = ?",
                    (team, team)
                )
                self.stats['bad_teams_removed'] += cursor.rowcount
            
            if self.verbose:
                print(f"   Removed {self.stats['bad_teams_removed']:,} games")
        else:
            if self.verbose:
                print("   No bad teams found")
        
        # ─────────────────────────────────────────────────────────────────────
        # Step 2: Remove duplicate games
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print("\n2️⃣  Removing duplicate games...")
        
        game_groups = analysis['game_groups']
        duplicate_ids = []
        
        for key, games in game_groups.items():
            if len(games) > 1:
                # Keep the one with scores, or most recent
                games_with_scores = [
                    g for g in games 
                    if g['home_score'] is not None and g['away_score'] is not None
                ]
                
                if games_with_scores:
                    keep = max(games_with_scores, key=lambda x: x['scraped_at'])
                else:
                    keep = max(games, key=lambda x: x['scraped_at'])
                
                for g in games:
                    if g['id'] != keep['id']:
                        duplicate_ids.append(g['id'])
        
        if duplicate_ids:
            # Delete in batches for performance
            batch_size = 500
            for i in range(0, len(duplicate_ids), batch_size):
                batch = duplicate_ids[i:i+batch_size]
                placeholders = ','.join('?' * len(batch))
                cursor.execute(
                    f"DELETE FROM games WHERE id IN ({placeholders})",
                    batch
                )
            
            self.stats['duplicates_removed'] = len(duplicate_ids)
            
            if self.verbose:
                print(f"   Removed {self.stats['duplicates_removed']:,} duplicates")
        else:
            if self.verbose:
                print("   No duplicates found")
        
        # ─────────────────────────────────────────────────────────────────────
        # Step 3: Normalize dates
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print("\n3️⃣  Normalizing dates...")
        
        cursor.execute("""
            SELECT id, game_date FROM games 
            WHERE game_date NOT LIKE '____-__-__'
            AND game_date IS NOT NULL
        """)
        dates_to_fix = cursor.fetchall()
        
        for id_, old_date in dates_to_fix:
            new_date = self.normalize_date(old_date)
            if new_date and new_date != old_date:
                cursor.execute(
                    "UPDATE games SET game_date = ? WHERE id = ?",
                    (new_date, id_)
                )
                self.stats['dates_normalized'] += 1
        
        if self.verbose:
            print(f"   Normalized {self.stats['dates_normalized']:,} dates")
        
        # ─────────────────────────────────────────────────────────────────────
        # Step 4: Clean team names
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print("\n4️⃣  Cleaning team names...")
        
        teams_to_clean = analysis['teams_to_clean']
        
        for old_name, new_name in teams_to_clean:
            cursor.execute(
                "UPDATE games SET home_team = ? WHERE home_team = ?",
                (new_name, old_name)
            )
            cursor.execute(
                "UPDATE games SET away_team = ? WHERE away_team = ?",
                (new_name, old_name)
            )
            self.stats['team_names_cleaned'] += 1
        
        if self.verbose:
            print(f"   Cleaned {self.stats['team_names_cleaned']:,} team names")
        
        # ─────────────────────────────────────────────────────────────────────
        # Step 5: Correct league fields
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print("\n5️⃣  Correcting league fields...")
        
        # Normalize ECNL RL (space) to ECNL-RL (hyphen)
        cursor.execute("UPDATE games SET league = 'ECNL-RL' WHERE league = 'ECNL RL'")
        normalized_count = cursor.rowcount
        
        # Fix games where team name indicates ECNL-RL but league says ECNL
        cursor.execute("""
            UPDATE games SET league = 'ECNL-RL'
            WHERE league = 'ECNL'
            AND (home_team LIKE '%ECNL RL%' 
                 OR home_team LIKE '% RL G%' 
                 OR home_team LIKE '% RL B%'
                 OR home_team LIKE '%RL NTX%'
                 OR home_team LIKE '%RL STXCL%'
                 OR home_team LIKE '%RL SoCal%'
                 OR away_team LIKE '%ECNL RL%' 
                 OR away_team LIKE '% RL G%' 
                 OR away_team LIKE '% RL B%'
                 OR away_team LIKE '%RL NTX%'
                 OR away_team LIKE '%RL STXCL%'
                 OR away_team LIKE '%RL SoCal%')
        """)
        corrected_count = cursor.rowcount
        
        self.stats['leagues_corrected'] = normalized_count + corrected_count
        
        if self.verbose:
            print(f"   Corrected {self.stats['leagues_corrected']:,} league values")
            print(f"     - Normalized (space→hyphen): {normalized_count:,}")
            print(f"     - Fixed from team names: {corrected_count:,}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Commit and optimize
        # ─────────────────────────────────────────────────────────────────────
        conn.commit()
        
        # Get final count
        cursor.execute("SELECT COUNT(*) FROM games")
        self.stats['total_after'] = cursor.fetchone()[0]
        
        # Vacuum database to reclaim space
        if self.verbose:
            print("\n6️⃣  Optimizing database (VACUUM)...")
        cursor.execute("VACUUM")
        
        conn.close()
        
        # ─────────────────────────────────────────────────────────────────────
        # Summary
        # ─────────────────────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n{'='*60}")
            print("✅ CLEANUP COMPLETE")
            print(f"{'='*60}")
            print(f"Games before: {self.stats['total_before']:,}")
            print(f"Games after:  {self.stats['total_after']:,}")
            print(f"Total removed: {self.stats['total_before'] - self.stats['total_after']:,}")
            print(f"\nBreakdown:")
            print(f"  🚫 Bad team games removed: {self.stats['bad_teams_removed']:,}")
            print(f"  🔄 Duplicates removed: {self.stats['duplicates_removed']:,}")
            print(f"  📅 Dates normalized: {self.stats['dates_normalized']:,}")
            print(f"  🔧 Team names cleaned: {self.stats['team_names_cleaned']:,}")
            print(f"  ⚠️  League values corrected: {self.stats['leagues_corrected']:,}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run(self, auto_confirm=False):
        """
        Run the full cleanup process
        
        Args:
            auto_confirm: If True, skip confirmation prompt
        
        Returns:
            dict with cleanup statistics
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print("🧹 DATABASE CLEANUP TOOL v3")
            print(f"{'='*60}")
            print(f"Database: {self.db_path}")
            print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        # Analyze
        analysis = self.analyze_database()
        
        # Calculate total changes
        total_changes = (
            analysis['bad_team_games'] +
            analysis['duplicate_records'] +
            len(analysis['teams_to_clean']) +
            analysis['non_standard_dates'] +
            analysis['wrong_league_count'] +
            analysis['space_league_count']
        )
        
        if total_changes == 0:
            if self.verbose:
                print("\n✅ Database is already clean!")
            return self.stats
        
        if self.dry_run:
            if self.verbose:
                print(f"\n📝 Dry run complete. Would make ~{total_changes:,} changes.")
            return self.stats
        
        # Confirm
        if not auto_confirm:
            print(f"\n⚠️  This will modify approximately {total_changes:,} records")
            response = input("Proceed? (y/yes to confirm, anything else to cancel): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ Cleanup cancelled")
                return self.stats
        
        # Backup
        self.backup_database()
        
        # Clean
        self.perform_cleanup(analysis)
        
        return self.stats


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION (for importing)
# ═══════════════════════════════════════════════════════════════════════════════

def cleanup_database(db_path, dry_run=False, auto_confirm=False, verbose=True):
    """
    Convenience function to run cleanup from other scripts
    
    Args:
        db_path: Path to the database
        dry_run: If True, only analyze without making changes
        auto_confirm: If True, skip confirmation prompt
        verbose: If True, print detailed output
    
    Returns:
        dict with cleanup statistics
    
    Example:
        from cleanup_database_final import cleanup_database
        stats = cleanup_database('seedlinedata.db', auto_confirm=True)
        print(f"Removed {stats['duplicates_removed']} duplicates")
    """
    cleaner = DatabaseCleanup(db_path, dry_run=dry_run, verbose=verbose)
    return cleaner.run(auto_confirm=auto_confirm)


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def find_database():
    """Find the database file in common locations"""
    candidates = [
        r"C:\Users\dugan\Seedline\scrapers and data\seedlinedata.db",
        '../seedlinedata.db',
        './seedlinedata.db',
        'seedlinedata.db',
        '/mnt/user-data/uploads/seedlinedata.db',
    ]
    
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive database cleanup for seedlinedata.db',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_database_final.py                    # Interactive mode
  python cleanup_database_final.py --dry-run          # Preview changes only
  python cleanup_database_final.py --auto             # Auto-confirm all changes
  python cleanup_database_final.py path/to/db.db      # Specify database path
  python cleanup_database_final.py --dry-run --auto   # Preview with full analysis
        """
    )
    parser.add_argument('db_path', nargs='?', default=None, 
                       help='Path to database file')
    parser.add_argument('--dry-run', '-d', action='store_true', 
                       help='Analyze only, no changes')
    parser.add_argument('--auto', '-y', action='store_true', 
                       help='Auto-confirm changes (no prompt)')
    parser.add_argument('--quiet', '-q', action='store_true', 
                       help='Less verbose output')
    
    args = parser.parse_args()
    
    # Find database
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = find_database()
        if not db_path:
            print("❌ Database not found. Please provide path as argument.")
            print("   Example: python cleanup_database_final.py /path/to/seedlinedata.db")
            sys.exit(1)
    
    try:
        cleaner = DatabaseCleanup(
            db_path, 
            dry_run=args.dry_run, 
            verbose=not args.quiet
        )
        stats = cleaner.run(auto_confirm=args.auto)
        
        # Exit code based on whether cleanup was needed
        if stats['total_before'] == stats['total_after']:
            sys.exit(0)  # No changes needed
        else:
            sys.exit(0)  # Changes made successfully
            
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
