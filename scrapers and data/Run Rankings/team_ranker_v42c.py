#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOCCER TEAM RANKING SYSTEM - V42 (ASPIRE + NPL SUPPORT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V42 CHANGES FROM V41:
  [OK] ASPIRE LEAGUE FACTOR - Added ASPIRE league with 0.90 multiplier
  [OK] NPL LEAGUE FACTORS - Added all NPL regional leagues with 0.90 multiplier
  [OK] DEFAULT LEAGUE FACTOR - Changed from 0.90 to 0.75 for unknown leagues
     This ensures teams from top-tier leagues (ECNL, GA) are properly weighted
     above teams from lesser-known or regional leagues

V41 features retained:
  [OK] OFFENSIVE POWER SCORE - Measures attacking strength (goals/game, big wins)
  [OK] DEFENSIVE POWER SCORE - Measures defensive strength (goals against, clean sheets)
  [OK] OFFENSIVE/DEFENSIVE RANKINGS - Ranks teams by offensive and defensive power
  [OK] EXPANDED JSON EXPORT - Includes all Excel columns in React JSON:
     - bestWin, secondBestWin, worstLoss, secondWorstLoss
     - recordWithin50, recordVsHigher, recordVsLower
     - confStrength, avgGD
     - offensivePowerScore, defensivePowerScore
     - offensiveRank, defensiveRank

V40 features retained:
  [OK] MINIMUM WINS RULE - Teams with < 5 wins cannot be ranked higher than #10
     This prevents teams with records like 4-2-0 from being #1 just because
     they beat a couple strong teams. They need more games to prove themselves.

V39 features retained:
  [OK] BOYS SUPPORT - Ranks Boys age groups (B08-B13) in addition to Girls
  [OK] PLAYER EXPORT - Exports player data from database to JSON for React app
  [OK] STATE LOOKUP - Gets states from teams table instead of conference mapping
  [OK] GENDER FILTER - Adds genders list to JSON output for React filter

V38 features retained:
  - Team name alias system (170+ aliases)
  - Self-play filter
  - Cross-league deduplication
  - GA ceiling compression
  - Competitive game weighting
  - Iterative cross-conference calibration
  - SOS penalty system
  - Opponent quality in predictability

USAGE:
  python team_ranker_v42.py                        # Interactive mode
  python team_ranker_v42.py --cleanup              # Force cleanup first  
  python team_ranker_v42.py --no-cleanup           # Skip cleanup
  python team_ranker_v42.py --dry-run              # Preview cleanup only
  python team_ranker_v42.py --verbose              # Extra diagnostics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sqlite3
import json
import sys
import re
import argparse
import os
import shutil
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - UPDATE THESE PATHS FOR YOUR SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

# Where to copy the JSON file for the React app
# Using stable folder name (not versioned) so you don't have to update this
REACT_APP_PUBLIC_FOLDER = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public"


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT CLEANUP MODULE
# ═══════════════════════════════════════════════════════════════════════════════

CLEANUP_AVAILABLE = False
try:
    from cleanup_database_v3 import DatabaseCleanup, cleanup_database
    CLEANUP_AVAILABLE = True
except ImportError:
    try:
        import importlib.util
        cleanup_paths = [
            Path(__file__).parent / 'cleanup_database_v3.py',
            Path('cleanup_database_v3.py'),
            Path('../cleanup_database_v3.py'),
        ]
        for cp in cleanup_paths:
            if cp.exists():
                spec = importlib.util.spec_from_file_location("cleanup_database_v3", cp)
                cleanup_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cleanup_module)
                DatabaseCleanup = cleanup_module.DatabaseCleanup
                cleanup_database = cleanup_module.cleanup_database
                CLEANUP_AVAILABLE = True
                break
    except Exception:
        pass

if not CLEANUP_AVAILABLE:
    print("WARNING:  Warning: cleanup_database_v3.py not found. Cleanup features disabled.")


class TeamRankerV30:
    """
    Youth Soccer Team Ranking System V31
    
    NEW IN V31:
    - Preserves database capitalization (MVLA, HTX, VDA not title-cased)
    - Comprehensive team aliases (50+ patterns) to merge duplicates
    - Fixes duplicate game counting issue (both home AND away normalized)
    
    V30b features:
    - GA ceiling: compresses ratings above 1700 to prevent top 5 dominance
    - Team name aliases to merge basic duplicates
    
    V30 features:
    - Low game count penalty to prevent 5-game teams from ranking #1
    - Fixed "Soccer" bad team name
    - Predictability score (1-100) for each team
    
    V29b features:
    - Rebalanced league factors for better distribution
    - ECNL-RL performance bonus for elite regional teams
    - Enhanced GA bonus
    - Gender filtering to separate Boys and Girls data
    - Fixed deduplication to preserve doubleheader games
    - Detailed diagnostics showing filtered data
    """
    
    # V30: Added "Soccer" to bad patterns
    BAD_TEAM_PATTERNS = [
        r'^Regional League$',
        r'^- Regional League',
        r'^Box Score',
        r'^Game Status',
        r'^Game Preview',
        r'^Location$',
        r'^Conference$',
        r'^Unknown$',
        r'^TBD[A-Z]?$',
        r'^TBA$',
        r'^BYE$',
        r'^\d{1,2}/\d{1,2}/\d{4}',
        r'^\d{4}-\d{2}-\d{2}',
        r'^\d{1,2}:\d{2}\s*(AM|PM)?',
        r'^[A-Z][a-z]{2}\s+\d{1,2},?\s*\d{4}',
        r'^#\d+$',
        r'^Score$',
        r'^Home$',
        r'^Away$',
        r'^vs\.?$',
        r'^Venue$',
        r'^Field$',
        r'^STXCL$',
        r'^NTX$',
        r'^S\.?Cal$',
        r'^SoCal$',
        r'^RL$',
        r'^ECNL$',
        r'^ECNL-RL$',
        r'^GA$',
        r'^SG$',
        r'^XF$',
        r'^FC$',
        r'^Soccer$',  # V30: Too generic, filtering this out
        r'^Cal$',     # V38: Truncated team name from scraping
        r'^Ca$',      # V38: Truncated team name from scraping  
        r'^CA$',      # V38: Truncated team name from scraping
    ]
    
    # Conference prefixes that get stuck to team names
    # V31: Fixed patterns - only strip obvious conference codes, not parts of team names
    # Key insight: Real team names like "South Carolina Surf" should NOT be touched
    # Conference prefixes are typically WITHOUT space like "SouthFC" or have specific patterns
    CONFERENCE_PREFIXES = [
        r'^Virginia(?=[A-Z])',       # VirginiaBeach -> Beach, but "Virginia Revolution" untouched
        r'^Eastern(?=[A-Z])',
        r'^Western\s*[AB]?(?=[A-Z])', 
        r'^Central\s*Girls?(?=[A-Z])',
        r'^South(?=[A-Z])',          # SouthFC -> FC, but "South Carolina" untouched
        r'^North(?=[A-Z])',          # NorthFL -> FL, but "North Shore" untouched  
        r'^East(?=[A-Z])',               
        r'^West(?=[A-Z])',               
        r'^south\s*Girls?(?=[A-Z])',     
        r'^NB(?=[A-Z])',                 
        r'^RL(?=[A-Z])',                 
        r'^GLA(?=[A-Z])',                
        r'^Regional\s*League\s*',    # Always strip "Regional League" prefix
        r'^Midwest(?=[A-Z])',
        r'^Southeast(?=[A-Z])',
        r'^Southwest(?=[A-Z])',
        r'^Northeast(?=[A-Z])',
        r'^Northwest(?=[A-Z])',
        r'^Atlantic(?=[A-Z])',
        r'^Pacific(?=[A-Z])',
        r'^Mountain(?=[A-Z])',
        r'^Plains(?=[A-Z])',
        r'^Texas(?=[A-Z])',
        r'^Florida(?=[A-Z])',
        r'^California(?=[A-Z])',
        r'^Ohio(?=[A-Z])',
        r'^Commonwealth(?=[A-Z])',
    ]
    
    # V32: Comprehensive team name aliases using DATABASE CAPITALIZATION
    # Format: 'variant name (lowercase)': 'canonical name (from database)'
    # These are applied AFTER stripping Regional League prefix and NTX suffix
    TEAM_ALIASES = {
        # === MVLA variants ===
        'mvla soccer club': 'MVLA',
        'mvla': 'MVLA',
        
        # === Solar variants (ALL are the same club) ===
        'solar soccer club': 'Solar SC',
        'solar sc': 'Solar SC',
        'solar blue': 'Solar SC',
        'solar red': 'Solar SC',
        'solar white': 'Solar SC',
        'solar black': 'Solar SC',
        'solar silver': 'Solar SC',
        
        # === Tulsa variants (switched from ECNL-RL to GA in Aug 2025) ===
        'tulsa sc': 'Tulsa Soccer Club',
        'tulsa soccer club': 'Tulsa Soccer Club',
        'tulsa soccer club 11g': 'Tulsa Soccer Club',
        'tulsa soccer club 11g ga': 'Tulsa Soccer Club',
        
        # === Tennessee variants ===
        'tennessee soccer club': 'Tennessee SC',
        'tennessee sc': 'Tennessee SC',
        'tennessee united': 'Tennessee SC',
        
        # === So Cal Blues variants ===
        'so cal blues sc': 'SO Cal Blues',
        'so cal blues': 'SO Cal Blues',
        'so cal blues sc socal': 'SO Cal Blues',
        
        # === Marin variants ===
        'marin football club': 'Marin FC',
        'marin fc': 'Marin FC',
        
        # === Minnesota Thunder variants ===
        'minnesota thunder academy': 'Minnesota Thunder',
        'minnesota thunder': 'Minnesota Thunder',
        
        # === VDA variants ===
        'virginia development academy': 'VDA',
        'vda': 'VDA',
        
        # === OK Energy variants ===
        'oklahoma energy fc': 'OK Energy FC',
        'ok energy fc': 'OK Energy FC',
        
        # === Legends FC variants ===
        'legends fc san diego': 'Legends FC',
        'legends fc sd (dmcv)': 'Legends FC',
        'legends fc michigan': 'Legends FC',
        'legends fc': 'Legends FC',
        
        # === Real Colorado variants (merge ALL) ===
        'real colorado athletico': 'Real Colorado',
        'real colorado - athletico': 'Real Colorado',
        'real colorado national': 'Real Colorado',
        'real colorado': 'Real Colorado',
        
        # === Colorado Rush variants ===
        'colorado rush academy blue': 'Colorado Rush',
        'colorado rush academy white': 'Colorado Rush',
        'colorado rush': 'Colorado Rush',
        
        # === Classics Elite variants ===
        'classics elite soccer academy': 'Classics Elite',
        'classics elite sa': 'Classics Elite',
        'classics elite': 'Classics Elite',
        
        # === Dallas Texans variants ===
        'dallas texans -': 'Dallas Texans',
        'dallas texans': 'Dallas Texans',
        'dallas texans red': 'Dallas Texans',
        
        # === Sting variants (merge ALL for dedup) ===
        'sting soccer club': 'Sting Dallas',
        'sting black': 'Sting Dallas',
        'sting': 'Sting Dallas',
        'sting royal': 'Sting Dallas',  # V32: Merge for dedup
        'sting brave': 'Sting Dallas',   # V32: Merge for dedup
        'sting bold': 'Sting Dallas',    # V32: Merge for dedup
        
        # === DKSC variants ===
        'dksc': 'DKSC',
        'dksc white': 'DKSC',
        
        # === NTX Celtic variants ===
        'ntx celtic fc': 'NTX Celtic FC',
        'ntx celtic fc green': 'NTX Celtic FC',
        
        # === Beach FC variants ===
        'beach fc (ca)': 'Beach FC (CA)',
        'beach fc (va)': 'Beach FC (VA)',
        
        # === FC Dallas variants (merge all sub-teams) ===
        'fc dallas': 'FC Dallas',
        'fc dallas blue': 'FC Dallas',
        'fc dallas white': 'FC Dallas',
        'fc dallas red': 'FC Dallas',
        
        # === Nationals variants ===
        'nationals soccer club': 'Nationals SC',
        'nationals sc': 'Nationals SC',
        'nationals': 'Nationals SC',
        
        # === Eagles variants ===
        'eagles soccer club': 'Eagles SC',
        'eagles sc': 'Eagles SC',
        
        # === DE Anza Force variants ===
        'de anza force': 'DE Anza Force',
        'de anza force -': 'DE Anza Force',
        
        # === COSC variants ===
        'cosc': 'COSC',
        
        # === Slammers variants ===
        'slammers fc': 'Slammers FC',
        'slammers fc hb koge': 'Slammers FC HB Koge',
        
        # === Rockford Raptors variants ===
        'rockford raptors': 'Rockford Raptors',
        'rockford raptors fc': 'Rockford Raptors',
        
        # === Phoenix Rising variants ===
        'phoenix rising': 'Phoenix Rising',
        'phoenix rising fc': 'Phoenix Rising',
        
        # === Placer United variants ===
        'placer united': 'Placer United',
        'placer united soccer club': 'Placer United',
        
        # === Pleasanton Rage variants ===
        'pleasanton rage': 'Pleasanton Rage',
        
        # === San Francisco Elite variants ===
        'san francisco elite': 'San Francisco Elite',
        'san francisco elite academy': 'San Francisco Elite',
        
        # === Concorde Fire variants (merge sub-teams) ===
        'concorde fire': 'Concorde Fire',
        'concorde fire premier': 'Concorde Fire',
        'concorde fire platinum': 'Concorde Fire',
        
        # === Charlotte SA variants ===
        'charlotte sa': 'Charlotte SA',
        'charlotte sa blue': 'Charlotte SA',
        'charlotte sa white': 'Charlotte SA',
        'charlotte sa gold': 'Charlotte SA',
        
        # === Lonestar variants ===
        'lonestar soccer club': 'Lonestar SC',
        'lonestar sc': 'Lonestar SC',
        'lonestar sc red': 'Lonestar SC',
        'lonestar sc black': 'Lonestar SC',
        'lonestar sc nth': 'Lonestar SC',
        'lonestar sc sth': 'Lonestar SC',
        
        # === Dallas Surf variants ===
        'dallas surf': 'Dallas Surf',
        
        # === Fever United variants ===
        'fever united fc': 'Fever United',
        'fever united': 'Fever United',
        
        # === Avanti variants ===
        'avanti sa': 'Avanti SA',
        'avanti soccer academy': 'Avanti SA',
        
        # === Atletico Dallas Youth variants ===
        'atletico dallas youth': 'Atletico Dallas Youth',
        'atletico dallas youth blue': 'Atletico Dallas Youth',
        'atlético dallas youth': 'Atletico Dallas Youth',
        'atlético dallas youth blue': 'Atletico Dallas Youth',
        
        # === Idaho Rush variants ===
        'idaho rush': 'Idaho Rush',
        'idaho rush sc': 'Idaho Rush',
        
        # === LA Roca variants ===
        'la roca': 'LA Roca',
        'la roca fc': 'LA Roca',
        
        # === LAFC So Cal variants ===
        'lafc so cal': 'LAFC So Cal',
        
        # === Liverpool FC IA variants ===
        'liverpool fc ia michigan': 'Liverpool FC IA Michigan',
        'liverpool fc ia michigan north oakland': 'Liverpool FC IA Michigan',
        'liverpool ia michigan north oakland': 'Liverpool FC IA Michigan',
        
        # === NC Courage variants ===
        'nc courage': 'NC Courage',
        'nc courage academy': 'NC Courage',
        
        # === NC Fusion variants ===
        'nc fusion': 'NC Fusion',
        
        # === WNY Flash variants ===
        'wny flash': 'WNY Flash',
        'wny flash rochester': 'WNY Flash',
        'wny flash binghamton': 'WNY Flash',
        
        # === PDA variants ===
        'pda blue': 'PDA Blue',
        'pda white': 'PDA White',
        'pda blue (north)': 'PDA Blue (North)',
        'pda white (shore)': 'PDA White (Shore)',
        'pda south': 'PDA South',
        'pda south blue': 'PDA South',
        'pda south white': 'PDA South',
        
        # === SLSG variants ===
        'slsg navy': 'SLSG Navy',
        'slsg green': 'SLSG Green',
        'slsg mo': 'SLSG MO',
        
        # === GSA variants ===
        'gsa': 'GSA',
        'gsa -': 'GSA',
        'gsa force': 'GSA Force',
        'gsa force blue': 'GSA Force',
        
        # === Richmond United variants ===
        'richmond united': 'Richmond United',
        'richmond united blue': 'Richmond United',
        'richmond united red': 'Richmond United',
        'richmond united orange': 'Richmond United',
        
        # === Match Fit Surf variants ===
        'match fit surf': 'Match Fit Surf',
        'match fit surf blue': 'Match Fit Surf',
        'match fit surf white': 'Match Fit Surf',
        'match fit surf blue ii': 'Match Fit Surf',
        
        # === Challenge variants ===
        'challenge': 'Challenge SC',
        'challenge sc': 'Challenge SC',
        'challenge red': 'Challenge SC',
        
        # === FC Stars variants ===
        'fc stars': 'FC Stars',
        'fc stars blue': 'FC Stars',
        'fc stars white': 'FC Stars',
        
        # === Stanislaus variants ===
        'stanislaus united': 'Stanislaus United',
        'stanislaus united sc': 'Stanislaus United',
        
        # === HTX variants (GA team) ===
        'htx 13g': 'HTX',
        'htx 12g': 'HTX',
        'htx 11g': 'HTX',
        'htx 10g': 'HTX',
        'htx 09g': 'HTX',
        'htx 08g': 'HTX',
        'htx': 'HTX',
        
        # === TopHat variants (GA team) ===
        'tophat 13g ga gold': 'TopHat GA Gold',
        'tophat 13g ga navy': 'TopHat GA Navy',
        'tophat 12g ga gold': 'TopHat GA Gold',
        'tophat 12g ga navy': 'TopHat GA Navy',
        'tophat 11g ga gold': 'TopHat GA Gold',
        'tophat 11g ga navy': 'TopHat GA Navy',
        'tophat 10g ga gold': 'TopHat GA Gold',
        'tophat 10g ga navy': 'TopHat GA Navy',
        'tophat 09g ga gold': 'TopHat GA Gold',
        'tophat 09g ga navy': 'TopHat GA Navy',
        'tophat 08/07g ga gold': 'TopHat GA Gold',
        'tophat 08/07g ga navy': 'TopHat GA Navy',
        
        # === Lou Fusz variants (GA team) ===
        'lou fusz athletic 13g': 'Lou Fusz Athletic',
        'lou fusz athletic 12g': 'Lou Fusz Athletic',
        'lou fusz athletic 11g': 'Lou Fusz Athletic',
        'lou fusz athletic 10g': 'Lou Fusz Athletic',
        'lou fusz athletic 09g': 'Lou Fusz Athletic',
        'lou fusz athletic 08/07g': 'Lou Fusz Athletic',
        
        # === Colorado Edge variants ===
        'colorado edge': 'Colorado Edge',
        'colorado edge sc': 'Colorado Edge',
        
        # === South Valley Chivas variants ===
        'south valley chivas': 'South Valley Chivas',
        'south valley chivas academy': 'South Valley Chivas',
        
        # === West Side Alliance variants ===
        'west side alliance': 'West Side Alliance',
        'west side alliance okc': 'West Side Alliance OKC',
        'west side alliance tulsa': 'West Side Alliance Tulsa',
        'west side alliance tulsa blue': 'West Side Alliance Tulsa',
    }
    
    MIN_GAMES = 5          # Minimum games for inclusion in rankings
    IDEAL_GAMES = 10       # V30: Teams with fewer than this get penalty
    
    # V40: Minimum wins rule - teams with fewer wins cannot be ranked too high
    MIN_WINS_FOR_TOP_RANKS = 5   # Minimum wins needed to be in top 10
    MAX_RANK_WITHOUT_MIN_WINS = 10  # Teams with < MIN_WINS cannot be higher than this
    
    LEAGUE_FACTORS = {
        'ECNL': 2.00,
        'GA': 1.55,       # V33: Increased from 1.45 for better GA representation in top 100
        'ECNL-RL': 1.05,  # V35: Reduced back to 1.05 (V34 had 1.10 which was too high)
        # V42: Added ASPIRE and NPL leagues
        'ASPIRE': 0.90,
        # NPL regional leagues - all at 0.90 (slightly below ASPIRE)
        'FCL NPL (Florida)': 0.90,
        'CPSL NPL (Chesapeake)': 0.90,
        'Central States NPL': 0.90,
        'Frontier Premier League': 0.90,
        'Great Lakes Alliance NPL': 0.90,
        'Mid-Atlantic Premier League': 0.90,
        'MDL NPL (Midwest Developmental)': 0.90,
        'Minnesota NPL': 0.90,
        'Mountain West NPL': 0.90,
        'NISL NPL (Northern Illinois)': 0.90,
        'NorCal NPL': 0.90,
        'Red River NPL': 0.90,
        'SOCAL NPL': 0.90,
        'South Atlantic Premier League': 0.90,
        'Texas Premier League': 0.90,
        'Wisconsin NPL': 0.90,
        'NPL': 0.90,  # Generic NPL fallback
    }
    
    # V42: Default league factor for unknown leagues (was 0.90, now 0.75)
    DEFAULT_LEAGUE_FACTOR = 0.75
    
    RECENCY_DECAY = 0.90
    MAX_GAME_AGE_MONTHS = 12
    
    # V30b: Restored GA bonuses for top 100 representation
    GA_UNDEFEATED_BONUS = 0.25      # Restored from 0.15
    GA_HIGH_WIN_BONUS = 0.10        # Restored from 0.08
    GA_GOOD_WIN_BONUS = 0.05        # Restored from 0.04
    
    # V30b: GA ceiling to prevent dominating top 5
    # If GA team rating exceeds this, compress the excess
    GA_RATING_CEILING = 1700        # Ratings above this get compressed
    GA_CEILING_COMPRESSION = 0.20   # Keep only 20% of rating above ceiling
    
    # V29b: ECNL-RL performance bonuses (similar to GA)
    ECNLRL_UNDEFEATED_BONUS = 0.08  # V33: Reduced from 0.15 - undefeated vs weak teams shouldn't rank high
    ECNLRL_HIGH_WIN_BONUS = 0.04    # V33: Reduced from 0.06
    ECNLRL_GOOD_WIN_BONUS = 0.02    # V33: Reduced from 0.04
    
    # V33: SOS penalty thresholds - penalize teams with weak schedules
    SOS_PENALTY_THRESHOLD = 1000    # Avg opp rating below this triggers penalty
    SOS_PENALTY_MAX = 200           # Maximum penalty points for very weak schedule
    SOS_BONUS_FACTOR = 0.08         # V33: Reduced from 0.10 (was avg_opp/1000 * 100)
    
    # V30: Predictability score weights
    PRED_GAMES_WEIGHT = 30          # V33: Reduced from 40 to make room for opponent quality
    PRED_CONSISTENCY_WEIGHT = 25    # V33: Reduced from 30
    PRED_MARGIN_WEIGHT = 20         # V33: Reduced from 30
    PRED_OPP_QUALITY_WEIGHT = 25    # V33: NEW - points for playing ranked opponents
    PRED_IDEAL_GAMES = 15           # Games needed for full games score
    
    def __init__(self, db_path='../seedlinedata.db', verbose=False):
        self.db_path = Path(db_path)
        self.games_df = None
        # V39: Added Boys age groups
        # V42c: Added all age groups
        # Note: G06/B06 = birth year 2006 (oldest ~19yo), G19/B19 = U-19 (also oldest)
        # Both formats coexist in data from different leagues
        self.all_age_groups = [
            'G06', 'G07', 'G19', 'G18', 'G17', 'G16', 'G15', 'G14',  # Girls older (birth yr & U-age)
            'G13', 'G12', 'G11', 'G10', 'G09', 'G08/07',              # Girls younger
            'B06', 'B07', 'B19', 'B18', 'B17', 'B16', 'B15', 'B14',  # Boys older (birth yr & U-age)
            'B13', 'B12', 'B11', 'B10', 'B09', 'B08'                  # Boys younger
        ]
        self.cleanup_stats = {
            'bad_teams_removed': 0, 
            'names_cleaned': 0,
            'league_detected_from_name': 0
        }
        self.db_cleanup_stats = None
        self.partial_score_stats = {}
        self.verbose = verbose
        
        # V39: Store team state lookup from database
        self.team_states = {}
        
        # V29: Diagnostics tracking
        self.diagnostics = {
            'bad_team_names_found': [],
            'duplicates_removed_samples': [],
            'gender_filtered_count': 0,
            'age_group_gender_breakdown': {},
        }
        
        self._bad_patterns = [re.compile(p, re.IGNORECASE) for p in self.BAD_TEAM_PATTERNS]
        # V31: Don't use IGNORECASE - it makes (?=[A-Z]) match any letter
        # The patterns are designed for specific cases
        self._prefix_patterns = [re.compile(p) for p in self.CONFERENCE_PREFIXES]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE CLEANUP
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_database_cleanup(self, dry_run=False):
        """Run comprehensive database cleanup before ranking"""
        if not CLEANUP_AVAILABLE:
            print("\nWARNING:  Database cleanup not available (cleanup_database_v3.py not found)")
            return None
        
        print(f"\n{'='*80}")
        print("[CHART] PHASE 1: DATABASE CLEANUP")
        print(f"{'='*80}")
        
        try:
            cleaner = DatabaseCleanup(self.db_path, dry_run=dry_run, verbose=True)
            stats = cleaner.run(auto_confirm=True)
            self.db_cleanup_stats = stats
            return stats
        except Exception as e:
            print(f"\n[ERROR] Cleanup error: {e}")
            return None
    
    def check_partial_scores(self):
        """Check for games with partial scores"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT league,
                   SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) as complete,
                   SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NULL THEN 1 ELSE 0 END) as home_only,
                   SUM(CASE WHEN home_score IS NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) as away_only,
                   SUM(CASE WHEN home_score IS NULL AND away_score IS NULL THEN 1 ELSE 0 END) as no_scores
            FROM games
            GROUP BY league
        """)
        
        results = {}
        for row in cursor.fetchall():
            league, complete, home_only, away_only, no_scores = row
            results[league] = {
                'complete': complete,
                'partial': home_only + away_only,
                'none': no_scores
            }
        
        conn.close()
        self.partial_score_stats = results
        return results
    
    def check_gender_distribution(self):
        """V29: Check gender distribution in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT age_group, gender, COUNT(*) as cnt
            FROM games
            WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            GROUP BY age_group, gender
            ORDER BY age_group, gender
        """)
        
        results = defaultdict(dict)
        for row in cursor.fetchall():
            age_group, gender, cnt = row
            gender_str = gender if gender else 'NULL/Unknown'
            results[age_group][gender_str] = cnt
        
        conn.close()
        self.diagnostics['age_group_gender_breakdown'] = dict(results)
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEAM NAME UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def is_bad_team_name(self, name):
        """Check if team name is a scraping artifact"""
        if not name or pd.isna(name):
            return True, "Empty or null"
        name = str(name).strip()
        
        if len(name) < 3:
            return True, f"Too short ({len(name)} chars): '{name}'"
        if len(name) > 100:
            return True, f"Too long ({len(name)} chars): '{name[:50]}...'"
        if re.match(r'^\d+$', name):
            return True, f"Numbers only: '{name}'"
            
        for pattern in self._bad_patterns:
            if pattern.match(name):
                return True, f"Matches bad pattern: '{name}'"
        return False, None
    
    def detect_league_from_name(self, name):
        """Detect the actual league from team name"""
        if not name or pd.isna(name):
            return None
            
        name_upper = str(name).upper()
        
        ecnl_rl_indicators = [
            'ECNL RL', 'ECNL-RL', ' RL G', ' RL B', 
            'RL NTX', 'RL STXCL', 'RL SOCAL', 'RL GLA',
            ' RL ', 'ECNL RL NTX', 'ECNL RL STXCL'
        ]
        if any(x in name_upper for x in ecnl_rl_indicators):
            return 'ECNL-RL'
        
        ga_indicators = [' GA ', ' GA$', '13G GA', '14G GA', '15G GA', 
                        'GIRLS ACADEMY', '12G GA', '11G GA', '10G GA',
                        '09G GA', '08G GA', '07G GA']
        if any(x in name_upper or name_upper.endswith(x.rstrip('$')) 
               for x in ga_indicators):
            return 'GA'
        
        if 'ECNL' in name_upper and 'RL' not in name_upper:
            return 'ECNL'
        
        return None
    
    def clean_team_name(self, name, db_league=None):
        """Clean up corrupted team names and detect true league"""
        if not name or pd.isna(name):
            return name, None
            
        original = str(name).strip()
        detected_league = self.detect_league_from_name(original)
        name = original
        
        name = re.sub(r'^-\s*', '', name)
        name = re.sub(r'^-?\s*ECNL\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^Regional\s*League\s*-?\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^-?\s*Regional\s+League\s*-?\s*\w*', '', name, flags=re.IGNORECASE)
        
        for pattern in self._prefix_patterns:
            name = pattern.sub('', name)
        
        suffixes = [
            r'\s+ECNL\s+RL\s+STXCL\s*G?\d*\s*$',
            r'\s+ECNL\s+RL\s+NTX\s*G?\d*\s*$',
            r'\s+ECNL\s+RL\s+SoCal\s*G?\d*\s*$',
            r'\s+ECNL\s+RL\s+GLA\s*G?\d*\s*$',
            r'\s+ECNL\s+RL\s*G?\d*\s*$',
            r'\s+ECNL-RL\s*G?\d*\s*$',
            r'\s+ECNL\s+G\d{2}/\d{2}\s*$',
            r'\s+ECNL\s+G\d{2}\s*$',
            r'\s+ECNL\s*$',
            r'\s+RL\s+STXCL\s*G?\d*\s*$',
            r'\s+RL\s+NTX\s*G?\d*\s*$',
            r'\s+RL\s+G\s*\d*\s*$',
            r'\s+RL\s+B\s*\d*\s*$',
            r'\s+RL\s*$',
            # V32: Only strip " GA" at end, NOT "11G GA" - preserve age group suffix
            # Old patterns that stripped too much:
            # r'\s+\d+G\s+GA\s*$',  # Removed - was stripping "11G GA"
            # r'\s+G\d+\s+GA\s*$',  # Removed - was stripping "G11 GA"
            r'\s+GA\s*$',  # Only strip trailing " GA"
            r'\s+STXCL\s*$',
            r'\s+NTX\s*$',
            r'\s+SoCal\s*$',
            r'\s+GLA\s*$',
            r'\s+PRE\s*$',
            r'\s+-\s+ECNL\s*$',
            r'\s+-\s+ECNL\s+RL\s*$',
            # V32: Don't strip age group suffixes from GA teams
            # r'\s+G\d{2}/\d{2}\s*$',  # Removed - was stripping "G08/07"
            # r'\s+G\d{2}\s*$',        # Removed - was stripping "G11"
            r'\s+\d{4}\s*$',
        ]
        
        for pattern in suffixes:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        name = ' '.join(name.split())
        
        if name != original:
            self.cleanup_stats['names_cleaned'] += 1
        if detected_league:
            self.cleanup_stats['league_detected_from_name'] += 1
            
        return name if name and len(name) >= 3 else original, detected_league
    
    def determine_team_league(self, team_name, db_leagues):
        """Determine the correct league for a team"""
        detected = self.detect_league_from_name(team_name)
        if detected:
            return detected
            
        if db_leagues and len(db_leagues) > 0:
            from collections import Counter
            normalized = []
            for lg in db_leagues:
                if lg in ['ECNL RL', 'ECNL-RL']:
                    normalized.append('ECNL-RL')
                elif lg == 'ECNL':
                    normalized.append('ECNL')
                elif lg == 'GA':
                    normalized.append('GA')
                else:
                    normalized.append(lg)
            
            if normalized:
                return Counter(normalized).most_common(1)[0][0]
                
        return 'ECNL'
    
    def extract_club_name(self, team_name):
        """
        Extract club name from team name.
        e.g., "Beach FC G13" -> "Beach FC"
              "Solar SC ECNL" -> "Solar SC"
        """
        if not team_name:
            return team_name
        
        # Most team names are already clean at this point
        # The club is typically the team name itself after cleaning
        return team_name
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA LOADING - V29: WITH GENDER FILTERING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def load_game_data(self):
        """Load game data with runtime cleanup - V29: Gender filtered"""
        print(f"\n{'='*80}")
        print("[CHART] PHASE 2: LOADING DATA FROM DATABASE")
        print(f"{'='*80}")
        print(f"Database: {self.db_path}")
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        partial_stats = self.check_partial_scores()
        
        print("\n Score completeness by league:")
        for league, stats in partial_stats.items():
            total = stats['complete'] + stats['partial'] + stats['none']
            pct = (stats['complete'] / total * 100) if total > 0 else 0
            print(f"  {league}: {stats['complete']:,} complete, {stats['partial']:,} partial ({pct:.0f}% usable)")
            if stats['partial'] > 100:
                print(f"    WARNING:  {stats['partial']} games have partial scores - scraper issue!")
        
        # V29: Check gender distribution before loading
        print("\n[CHART] Gender distribution in database:")
        gender_dist = self.check_gender_distribution()
        # V39: Show both Girls and Boys age groups
        all_age_groups = ['G13', 'G12', 'G11', 'G10', 'G09', 'G08', 'G07', 'G08/07',
                         'B13', 'B12', 'B11', 'B10', 'B09', 'B08']
        for age in all_age_groups:
            if age in gender_dist:
                for gender, count in gender_dist[age].items():
                    print(f"  {age} / {gender}: {count:,} games")
        
        conn = sqlite3.connect(self.db_path)
        
        # V39: Load BOTH Boys and Girls games
        # Boys games have age_group starting with 'B', Girls with 'G' or 'U'
        query = """
            SELECT 
                game_id, age_group, game_date, home_team, away_team,
                home_score, away_score, league, conference, game_status, gender
            FROM games
            WHERE home_score IS NOT NULL AND away_score IS NOT NULL
              AND (age_group LIKE 'G%' OR age_group LIKE 'U%' OR age_group LIKE 'B%')
        """
        
        self.games_df = pd.read_sql_query(query, conn)
        
        # V39: Load team states from teams table for state lookup
        print("\n Loading team states from database...")
        state_query = """
            SELECT DISTINCT team_name, state 
            FROM teams 
            WHERE state IS NOT NULL AND state != ''
        """
        state_df = pd.read_sql_query(state_query, conn)
        for _, row in state_df.iterrows():
            team_name = row['team_name']
            state = row['state']
            if team_name and state:
                self.team_states[team_name.lower().strip()] = state
        print(f"   Loaded states for {len(self.team_states):,} teams")
        
        conn.close()
        
        initial_count = len(self.games_df)
        print(f"\nGames loaded (Boys and Girls, with complete scores): {initial_count:,}")
        
        # V29: Report on gender filtering
        if 'gender' in self.games_df.columns:
            gender_counts = self.games_df['gender'].value_counts(dropna=False)
            print(f"\n[CHART] Loaded games by gender field:")
            for gender, count in gender_counts.items():
                gender_str = gender if gender else 'NULL/Unknown'
                print(f"  {gender_str}: {count:,}")
        
        # Clean up scores
        self.games_df['home_score'] = pd.to_numeric(
            self.games_df['home_score'], errors='coerce'
        ).fillna(0).astype(int)
        self.games_df['away_score'] = pd.to_numeric(
            self.games_df['away_score'], errors='coerce'
        ).fillna(0).astype(int)
        
        # Step 1: Normalize league values
        print("\nStep 1: Normalizing league values...")
        self.games_df['league'] = self.games_df['league'].replace({
            'ECNL RL': 'ECNL-RL',
        })
        
        # Step 2: Clean team names
        print("Step 2: Cleaning team names and detecting leagues...")
        
        home_original = self.games_df['home_team'].copy()
        away_original = self.games_df['away_team'].copy()
        
        home_cleaned = self.games_df['home_team'].apply(lambda x: self.clean_team_name(x)[0])
        home_leagues = home_original.apply(lambda x: self.detect_league_from_name(x))
        
        away_cleaned = self.games_df['away_team'].apply(lambda x: self.clean_team_name(x)[0])
        away_leagues = away_original.apply(lambda x: self.detect_league_from_name(x))
        
        # Step 3: Update league based on team names
        print("Step 3: Correcting league based on team name detection...")
        league_corrections = 0
        
        for idx in self.games_df.index:
            home_lg = home_leagues[idx]
            away_lg = away_leagues[idx]
            db_lg = self.games_df.at[idx, 'league']
            
            if home_lg == 'ECNL-RL' or away_lg == 'ECNL-RL':
                if db_lg != 'ECNL-RL':
                    self.games_df.at[idx, 'league'] = 'ECNL-RL'
                    league_corrections += 1
            elif home_lg == 'GA' or away_lg == 'GA':
                if db_lg != 'GA':
                    self.games_df.at[idx, 'league'] = 'GA'
                    league_corrections += 1
        
        print(f"  League corrections made: {league_corrections:,}")
        
        self.games_df['home_team'] = home_cleaned
        self.games_df['away_team'] = away_cleaned
        
        # Step 4: Filter bad team names - V29: WITH DIAGNOSTICS
        print("Step 4: Filtering bad team names...")
        bad_teams_detail = []
        
        for idx, row in self.games_df.iterrows():
            is_bad_home, reason_home = self.is_bad_team_name(row['home_team'])
            is_bad_away, reason_away = self.is_bad_team_name(row['away_team'])
            
            if is_bad_home:
                bad_teams_detail.append({
                    'team': row['home_team'],
                    'reason': reason_home,
                    'position': 'home',
                    'game_date': row['game_date']
                })
            if is_bad_away:
                bad_teams_detail.append({
                    'team': row['away_team'],
                    'reason': reason_away,
                    'position': 'away',
                    'game_date': row['game_date']
                })
        
        # Store for diagnostics report
        self.diagnostics['bad_team_names_found'] = bad_teams_detail
        
        bad_home = self.games_df['home_team'].apply(lambda x: self.is_bad_team_name(x)[0])
        bad_away = self.games_df['away_team'].apply(lambda x: self.is_bad_team_name(x)[0])
        
        games_with_bad_teams = (bad_home | bad_away).sum()
        self.games_df = self.games_df[~bad_home & ~bad_away]
        
        print(f"  Games with bad team names removed: {games_with_bad_teams:,}")
        print(f"  Clean games remaining: {len(self.games_df):,}")
        
        # V29: Show sample of bad team names
        if bad_teams_detail and self.verbose:
            print(f"\n   Sample bad team names (first 20 unique):")
            seen = set()
            for item in bad_teams_detail:
                if item['team'] not in seen and len(seen) < 20:
                    seen.add(item['team'])
                    print(f"     '{item['team']}' - {item['reason']}")
        
        # Step 5: Filter old games
        print("Step 5: Filtering old games (>12 months)...")
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=self.MAX_GAME_AGE_MONTHS * 30)).strftime('%Y-%m-%d')
        before_filter = len(self.games_df)
        self.games_df = self.games_df[self.games_df['game_date'] >= cutoff_date]
        old_games_removed = before_filter - len(self.games_df)
        print(f"  Cutoff date: {cutoff_date}")
        print(f"  Old games removed: {old_games_removed:,}")
        print(f"  Recent games remaining: {len(self.games_df):,}")
        
        # Step 6: Normalize case
        print("Step 6: Normalizing team name case...")
        self.games_df['home_team'] = self.games_df['home_team'].apply(self.normalize_team_case)
        self.games_df['away_team'] = self.games_df['away_team'].apply(self.normalize_team_case)
        
        # V30b: Apply team aliases to merge duplicates
        print("Step 6b: Applying team name aliases...")
        before_alias = len(self.games_df['home_team'].unique()) + len(self.games_df['away_team'].unique())
        self.games_df['home_team'] = self.games_df['home_team'].apply(self.apply_team_alias)
        self.games_df['away_team'] = self.games_df['away_team'].apply(self.apply_team_alias)
        after_alias = len(self.games_df['home_team'].unique()) + len(self.games_df['away_team'].unique())
        print(f"  Team names merged: {before_alias - after_alias} duplicates resolved")
        
        # V32: Remove self-play games (bad data where team plays itself)
        print("Step 6c: Removing self-play games...")
        before_selfplay = len(self.games_df)
        self.games_df = self.games_df[self.games_df['home_team'] != self.games_df['away_team']]
        selfplay_removed = before_selfplay - len(self.games_df)
        print(f"  Self-play games removed: {selfplay_removed:,}")
        
        # V32: Step 6d - Split teams that have games in both ECNL and ECNL-RL
        # Many clubs have both an ECNL team and an ECNL-RL team that should be ranked separately
        # For teams with games in BOTH leagues, rename the ECNL-RL version to "{Team} RL"
        print("Step 6d: Splitting ECNL/ECNL-RL teams from same club...")
        
        # Find teams with games in both leagues
        ecnl_home = set(self.games_df[self.games_df['league'] == 'ECNL']['home_team'].unique())
        ecnl_away = set(self.games_df[self.games_df['league'] == 'ECNL']['away_team'].unique())
        ecnl_teams = ecnl_home | ecnl_away
        
        ecnlrl_home = set(self.games_df[self.games_df['league'] == 'ECNL-RL']['home_team'].unique())
        ecnlrl_away = set(self.games_df[self.games_df['league'] == 'ECNL-RL']['away_team'].unique())
        ecnlrl_teams = ecnlrl_home | ecnlrl_away
        
        # Teams in BOTH leagues need to be split
        dual_league_teams = ecnl_teams & ecnlrl_teams
        
        if dual_league_teams:
            # Use vectorized operations for reliable renaming
            ecnlrl_mask = self.games_df['league'] == 'ECNL-RL'
            
            # Rename home teams in ECNL-RL games
            home_needs_rename = ecnlrl_mask & self.games_df['home_team'].isin(dual_league_teams)
            self.games_df.loc[home_needs_rename, 'home_team'] = self.games_df.loc[home_needs_rename, 'home_team'] + ' RL'
            
            # Rename away teams in ECNL-RL games
            away_needs_rename = ecnlrl_mask & self.games_df['away_team'].isin(dual_league_teams)
            self.games_df.loc[away_needs_rename, 'away_team'] = self.games_df.loc[away_needs_rename, 'away_team'] + ' RL'
            
            print(f"  Teams split into ECNL + ECNL-RL versions: {len(dual_league_teams)}")
        else:
            print(f"  No dual-league teams found")
        
        # V34: Step 6e - Safety check for " GA" suffix stripping
        # NOTE: Most GA suffix stripping happens in step 6 (normalize_team_case)
        # This is a backup check for any remaining cases
        print("Step 6e: Checking for remaining ' GA' suffixes in GA team names...")
        
        # Pattern: team name ending in " GA" (but not part of the team name like "Tophat GA Gold")
        # We only strip if it ends with a age group + " GA" pattern like "13G GA", "12G GA", etc.
        import re
        ga_suffix_pattern = re.compile(r'^(.+\d+G) GA$')
        
        def strip_ga_suffix(name):
            match = ga_suffix_pattern.match(name)
            if match:
                return match.group(1)  # Return without " GA"
            return name
        
        ga_mask = self.games_df['league'] == 'GA'
        ga_home_before = self.games_df.loc[ga_mask, 'home_team'].copy()
        ga_away_before = self.games_df.loc[ga_mask, 'away_team'].copy()
        
        self.games_df.loc[ga_mask, 'home_team'] = self.games_df.loc[ga_mask, 'home_team'].apply(strip_ga_suffix)
        self.games_df.loc[ga_mask, 'away_team'] = self.games_df.loc[ga_mask, 'away_team'].apply(strip_ga_suffix)
        
        # Count changes
        home_changes = (ga_home_before != self.games_df.loc[ga_mask, 'home_team']).sum()
        away_changes = (ga_away_before != self.games_df.loc[ga_mask, 'away_team']).sum()
        if home_changes + away_changes > 0:
            print(f"  Additional GA suffixes stripped: {home_changes + away_changes} references")
        else:
            print(f"  No additional changes needed (handled in step 6)")
        
        # Step 7: Remove duplicates - V29: FIXED KEY INCLUDES SCORES
        print("Step 7: Removing duplicate games...")
        before_dedup = len(self.games_df)
        
        # V29: Include scores in dedup key to preserve doubleheaders
        def make_game_key(row):
            teams = sorted([row['home_team'].lower().strip(), row['away_team'].lower().strip()])
            scores = sorted([int(row['home_score']), int(row['away_score'])])
            return f"{row['game_date']}_{teams[0]}_{teams[1]}_{scores[0]}_{scores[1]}"
        
        self.games_df['game_key'] = self.games_df.apply(make_game_key, axis=1)
        
        # V29: Track duplicates for diagnostics
        if self.verbose:
            dup_mask = self.games_df.duplicated(subset='game_key', keep='first')
            dup_samples = self.games_df[dup_mask].head(20)
            self.diagnostics['duplicates_removed_samples'] = dup_samples.to_dict('records')
        
        self.games_df = self.games_df.drop_duplicates(subset='game_key', keep='first')
        self.games_df = self.games_df.drop(columns=['game_key'])
        self.games_df = self.games_df.reset_index(drop=True)
        
        duplicates_removed = before_dedup - len(self.games_df)
        print(f"  Exact duplicates removed: {duplicates_removed:,}")
        
        # V31: Step 7b - Remove ECNL/ECNL-RL cross-league duplicates only
        # This catches data errors where the SAME game is recorded in both leagues with different scores
        # Only applies to ECNL<->ECNL-RL duplicates, not GA games
        print("Step 7b: Removing ECNL/ECNL-RL cross-duplicates...")
        before_cross_dedup = len(self.games_df)
        
        # Only process ECNL and ECNL-RL games
        ecnl_mask = self.games_df['league'].isin(['ECNL', 'ECNL-RL'])
        ecnl_games = self.games_df[ecnl_mask].copy()
        other_games = self.games_df[~ecnl_mask].copy()
        
        # Sort to prefer ECNL over ECNL-RL when deduplicating
        league_priority = {'ECNL': 1, 'ECNL-RL': 2}
        ecnl_games['league_priority'] = ecnl_games['league'].map(league_priority)
        ecnl_games = ecnl_games.sort_values('league_priority')
        
        def make_cross_league_key(row):
            teams = sorted([row['home_team'].lower().strip(), row['away_team'].lower().strip()])
            return f"{row['game_date']}_{row['age_group']}_{teams[0]}_{teams[1]}"
        
        ecnl_games['cross_key'] = ecnl_games.apply(make_cross_league_key, axis=1)
        ecnl_games = ecnl_games.drop_duplicates(subset='cross_key', keep='first')
        ecnl_games = ecnl_games.drop(columns=['cross_key', 'league_priority'])
        
        # Recombine with GA games
        self.games_df = pd.concat([ecnl_games, other_games], ignore_index=True)
        
        cross_dups_removed = before_cross_dedup - len(self.games_df)
        print(f"  Cross-league duplicates removed: {cross_dups_removed:,}")
        print(f"  Final game count: {len(self.games_df):,}")
        
        # Step 8: Recency weights
        print("Step 8: Calculating recency weights...")
        today = datetime.now()
        def calc_recency_weight(game_date):
            try:
                gd = datetime.strptime(str(game_date)[:10], '%Y-%m-%d')
                months_ago = (today - gd).days / 30.0
                return self.RECENCY_DECAY ** months_ago
            except:
                return 0.5
        
        self.games_df['recency_weight'] = self.games_df['game_date'].apply(calc_recency_weight)
        avg_weight = self.games_df['recency_weight'].mean()
        print(f"  Average recency weight: {avg_weight:.2f}")
        
        print(f"\nFinal league distribution:")
        for league, count in self.games_df['league'].value_counts().items():
            print(f"  {league}: {count:,} games")
        
        # V29: Final age group distribution
        print(f"\nFinal age group distribution:")
        for age, count in self.games_df['age_group'].value_counts().items():
            print(f"  {age}: {count:,} games")
        
        return self.games_df
    
    def normalize_team_case(self, name):
        """
        V32: Normalize team name - strip common prefixes/suffixes for better dedup.
        """
        if not name or pd.isna(name):
            return name
        name = str(name).strip()
        
        # V32: Strip "Regional League" prefix (appears in ECNL-RL data)
        if name.startswith('Regional League'):
            name = name[15:].strip()
        
        # V32: Strip NTX suffix (North Texas region identifier)
        if name.endswith(' NTX'):
            name = name[:-4].strip()
        elif name.endswith(' Ntx'):
            name = name[:-4].strip()
        
        # V32: Handle "GA White" / "GA Blue" patterns from GA events
        # "City SC 11G GA White" -> "City SC 11G White"
        name = name.replace(' GA White', ' White')
        name = name.replace(' GA Blue', ' Blue')
        name = name.replace(' GA Red', ' Red')
        
        # V32: Strip trailing " GA" suffix from GA event team names
        # "Lamorinda SC 11G GA" -> "Lamorinda SC 11G"
        # BUT preserve "TopHat GA Gold" / "TopHat GA Navy" (those are actual team names)
        if name.endswith(' GA') and 'TopHat' not in name:
            name = name[:-3].strip()
        
        # V31: DON'T use .title() - it breaks MVLA, HTX, VDA, etc.
        # Only fix VA -> Virginia abbreviation
        name = re.sub(r'\bVA\b', 'Virginia', name)
        
        # Clean up extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()
    
    def apply_team_alias(self, name):
        """V30b: Apply team name aliases to merge duplicate teams"""
        if not name or pd.isna(name):
            return name
        
        # Normalize for lookup
        lookup_name = str(name).strip().lower()
        
        # Check for alias match
        if lookup_name in self.TEAM_ALIASES:
            return self.TEAM_ALIASES[lookup_name]
        
        return name
    
    def get_age_group_games(self, age_group):
        """Get games for a specific age group
        
        V39: Updated to handle Boys age groups (B08-B13)
        """
        if age_group == 'G08/07':
            # Combined youngest Girls group
            mask = self.games_df['age_group'].isin(['G08/07', 'G08', 'G07', 'U09', 'U08'])
        elif age_group.startswith('B'):
            # Boys age groups - just match directly (no U format for boys)
            mask = self.games_df['age_group'] == age_group
        else:
            # Girls age groups - match G and U formats
            ga_age = age_group.replace('G', 'U')
            mask = self.games_df['age_group'].isin([age_group, ga_age])
        return self.games_df[mask].copy()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATS CALCULATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_stats(self, games_df):
        """Calculate team statistics with recency weighting
        
        V32: Determines team league from most recent games rather than first game.
        This handles teams that switch leagues mid-season (e.g., ECNL-RL to GA).
        """
        team_stats = {}
        
        # V30: Store game-level data for predictability calculation
        team_games = defaultdict(list)
        
        # V32: Track all leagues for each team with game dates to determine current league
        team_leagues = defaultdict(list)  # team -> [(date, league), ...]
        
        for _, game in games_df.iterrows():
            home = game['home_team']
            away = game['away_team']
            hs = int(game['home_score'])
            aws = int(game['away_score'])
            league = game['league']
            conference = game.get('conference', '')
            weight = game.get('recency_weight', 1.0)
            game_date = game.get('game_date', '')
            
            # Track leagues with dates for later determination
            team_leagues[home].append((game_date, league))
            team_leagues[away].append((game_date, league))
            
            for team in [home, away]:
                if team not in team_stats:
                    team_stats[team] = {
                        'games_played': 0,
                        'wins': 0,
                        'losses': 0,
                        'ties': 0,
                        'goals_for': 0,
                        'goals_against': 0,
                        'league': league,  # Will be updated after all games processed
                        'conference': conference,
                        'opponents': [],
                        'big_wins': 0,
                        'blowout_losses': 0,
                        'game_margins': [],
                        'weighted_wins': 0,
                        'weighted_games': 0,
                    }
            
            margin_home = hs - aws
            margin_away = aws - hs
            
            team_stats[home]['games_played'] += 1
            team_stats[away]['games_played'] += 1
            team_stats[home]['opponents'].append(away)
            team_stats[away]['opponents'].append(home)
            team_stats[home]['weighted_games'] += weight
            team_stats[away]['weighted_games'] += weight
            
            team_stats[home]['goals_for'] += hs
            team_stats[home]['goals_against'] += aws
            team_stats[away]['goals_for'] += aws
            team_stats[away]['goals_against'] += hs
            team_stats[home]['game_margins'].append(margin_home)
            team_stats[away]['game_margins'].append(margin_away)
            
            # V30: Store game-level data for predictability
            team_games[home].append({
                'opponent': away,
                'margin': margin_home,
                'result': 'W' if hs > aws else ('L' if hs < aws else 'T'),
                'goals_for': hs,
                'goals_against': aws
            })
            team_games[away].append({
                'opponent': home,
                'margin': margin_away,
                'result': 'W' if aws > hs else ('L' if aws < hs else 'T'),
                'goals_for': aws,
                'goals_against': hs
            })
            
            if hs > aws:
                team_stats[home]['wins'] += 1
                team_stats[home]['weighted_wins'] += weight
                team_stats[away]['losses'] += 1
                if margin_home >= 4:
                    team_stats[home]['big_wins'] += 1
                if margin_away <= -4:
                    team_stats[away]['blowout_losses'] += 1
            elif aws > hs:
                team_stats[away]['wins'] += 1
                team_stats[away]['weighted_wins'] += weight
                team_stats[home]['losses'] += 1
                if margin_away >= 4:
                    team_stats[away]['big_wins'] += 1
                if margin_home <= -4:
                    team_stats[home]['blowout_losses'] += 1
            else:
                team_stats[home]['ties'] += 1
                team_stats[away]['ties'] += 1
        
        # V32: Determine each team's league using smart priority + recency
        # Logic:
        # 1. If a team CLEARLY dominates one league (2x+ games), use that league
        # 2. If team switched leagues (recent games 100% in different league than history), use recent
        # 3. Otherwise use priority system (ECNL > GA > ECNL-RL)
        LEAGUE_PRIORITY = {'ECNL': 3, 'GA': 2, 'ECNL-RL': 1}
        
        for team in team_stats:
            if team in team_leagues:
                from collections import Counter
                
                # Sort by date
                sorted_games = sorted(team_leagues[team], key=lambda x: x[0], reverse=True)
                
                # Recent games = last 5
                recent_leagues = [lg for _, lg in sorted_games[:5]]
                recent_count = Counter(recent_leagues)
                
                # All games
                all_league_list = [lg for _, lg in sorted_games]
                all_counts = Counter(all_league_list)
                
                # Check if team SWITCHED leagues (100% recent games in one league that's NOT their historical dominant)
                if recent_leagues and len(all_counts) > 1:
                    most_recent_league = recent_count.most_common(1)[0][0]
                    
                    # Find historical dominant league (league with most total games)
                    historical_dominant = all_counts.most_common(1)[0][0]
                    
                    # If ALL recent games are in a DIFFERENT league than historical, team switched
                    if most_recent_league != historical_dominant:
                        recent_pct = recent_count[most_recent_league] / len(recent_leagues)
                        if recent_pct >= 1.0:  # 100% of recent games in new league
                            team_stats[team]['league'] = most_recent_league
                            continue
                
                # For established teams, use priority system
                # Find highest-priority league with at least 3 games
                best_league = None
                best_priority = 0
                
                for league, count in all_counts.items():
                    if count >= 3:
                        priority = LEAGUE_PRIORITY.get(league, 0)
                        if priority > best_priority:
                            best_priority = priority
                            best_league = league
                
                # If no league has 3+ games, use most common
                if best_league is None:
                    if all_counts:
                        best_league = all_counts.most_common(1)[0][0]
                
                if best_league:
                    team_stats[team]['league'] = best_league
        
        # Store game-level data for predictability calculation
        for team in team_stats:
            team_stats[team]['game_details'] = team_games[team]
        
        return team_stats
    
    def apply_min_wins_rule(self, sorted_teams):
        """
        V40: Apply minimum wins rule to rankings.
        
        Teams with fewer than MIN_WINS_FOR_TOP_RANKS wins cannot be ranked
        higher than MAX_RANK_WITHOUT_MIN_WINS.
        
        This prevents teams with records like 4-2-0 from being #1 just because
        they beat a couple strong teams - they haven't proven themselves enough.
        """
        if not sorted_teams:
            return sorted_teams
        
        # Separate teams by win count
        enough_wins = []
        not_enough_wins = []
        
        for team, stats in sorted_teams:
            wins = stats.get('wins', 0)
            if wins >= self.MIN_WINS_FOR_TOP_RANKS:
                enough_wins.append((team, stats))
            else:
                not_enough_wins.append((team, stats))
        
        # If no teams need demotion, return as-is
        if not not_enough_wins:
            return sorted_teams
        
        # Build new rankings:
        # - Teams with enough wins fill positions 1, 2, 3, ...
        # - Teams without enough wins start at MAX_RANK_WITHOUT_MIN_WINS
        result = []
        
        # First, add teams with enough wins
        for team, stats in enough_wins:
            result.append((team, stats))
        
        # Track how many teams with enough wins we have
        num_qualified = len(enough_wins)
        
        # Calculate where low-win teams should start
        start_position = max(num_qualified, self.MAX_RANK_WITHOUT_MIN_WINS - 1)
        
        # Insert low-win teams at appropriate positions
        # They maintain their relative order by rating
        for i, (team, stats) in enumerate(not_enough_wins):
            # Insert at position start_position + i
            insert_pos = start_position + i
            if insert_pos < len(result):
                result.insert(insert_pos, (team, stats))
            else:
                result.append((team, stats))
        
        # Log demotions for visibility
        demoted = []
        original_ranks = {team: i+1 for i, (team, _) in enumerate(sorted_teams)}
        new_ranks = {team: i+1 for i, (team, _) in enumerate(result)}
        
        for team, stats in not_enough_wins:
            old_rank = original_ranks.get(team, 999)
            new_rank = new_ranks.get(team, 999)
            if old_rank < self.MAX_RANK_WITHOUT_MIN_WINS and new_rank > old_rank:
                wins = stats.get('wins', 0)
                demoted.append(f"   {team[:35]:<35} #{old_rank:>2} -> #{new_rank:>2} ({wins} wins)")
        
        if demoted:
            print(f"\nWARNING:  Demoted {len(demoted)} teams (< {self.MIN_WINS_FOR_TOP_RANKS} wins):")
            for d in demoted[:10]:
                print(d)
            if len(demoted) > 10:
                print(f"   ... and {len(demoted) - 10} more")
        
        return result
    
    def calculate_rankings(self, games_df):
        """Calculate team rankings - V32: with iterative cross-conference calibration"""
        team_stats = self.calculate_stats(games_df)
        
        # First pass: basic ratings (win pct * league factor + goal diff bonus)
        for team, stats in team_stats.items():
            games = stats['games_played']
            wins = stats['wins']
            gf = stats['goals_for']
            ga = stats['goals_against']
            
            if games == 0:
                stats['win_pct'] = 0
                stats['goal_diff'] = 0
                stats['rating'] = 0
                stats['base_rating'] = 0
                continue
            
            win_pct = wins / games
            stats['win_pct'] = win_pct
            stats['goal_diff'] = gf - ga
            
            league = stats['league']
            league_factor = self.LEAGUE_FACTORS.get(league, self.DEFAULT_LEAGUE_FACTOR)
            
            base_rating = win_pct * 1000 * league_factor
            
            avg_gd = stats['goal_diff'] / games
            gd_bonus = min(max(avg_gd * 10, -50), 50)
            
            big_win_pct = stats['big_wins'] / games if games > 0 else 0
            big_win_bonus = big_win_pct * 30
            
            blowout_pct = stats['blowout_losses'] / games if games > 0 else 0
            blowout_penalty = blowout_pct * 40
            
            # V30: Low game count penalty
            games_penalty = 0
            if games < self.IDEAL_GAMES:
                penalty_pct = (self.IDEAL_GAMES - games) / (self.IDEAL_GAMES - self.MIN_GAMES) * 0.15
                games_penalty = base_rating * penalty_pct
            stats['games_penalty'] = games_penalty
            
            stats['base_rating'] = base_rating + gd_bonus + big_win_bonus - blowout_penalty - games_penalty
            stats['rating'] = stats['base_rating']
            stats['league_factor'] = league_factor
        
        # V32: Iterative SOS propagation for cross-conference calibration
        # This is key for comparing teams from different conferences/regions
        # Cross-conference games (showcases, nationals) act as bridges that
        # propagate strength information between otherwise isolated groups
        ITERATIONS = 5  # Number of iterations for rating propagation
        SOS_WEIGHT = 0.10  # How much SOS affects rating each iteration (10%)
        
        for iteration in range(ITERATIONS):
            # Store previous ratings to check convergence
            prev_ratings = {team: stats['rating'] for team, stats in team_stats.items()}
            
            # Update ratings based on opponent strength
            for team, stats in team_stats.items():
                if stats['games_played'] < self.MIN_GAMES:
                    continue
                
                # Calculate strength of schedule from current opponent ratings
                opp_ratings = []
                for opp in stats['opponents']:
                    if opp in team_stats:
                        opp_ratings.append(team_stats[opp].get('rating', 0))
                
                if opp_ratings:
                    avg_opp_rating = np.mean(opp_ratings)
                    
                    # V32: Weight results against opponent quality
                    # A win against a 1500-rated team is worth more than against 500-rated
                    game_details = stats.get('game_details', [])
                    quality_adjusted_wins = 0
                    quality_adjusted_games = 0
                    
                    for game in game_details:
                        opp = game['opponent']
                        opp_rating = team_stats.get(opp, {}).get('rating', 500)
                        result = game['result']
                        
                        # Weight by opponent strength (normalized around 1000)
                        opp_weight = max(0.5, min(2.0, opp_rating / 1000))
                        quality_adjusted_games += opp_weight
                        
                        if result == 'W':
                            quality_adjusted_wins += opp_weight
                        elif result == 'T':
                            quality_adjusted_wins += opp_weight * 0.5
                    
                    # Quality-adjusted win rate
                    if quality_adjusted_games > 0:
                        quality_win_rate = quality_adjusted_wins / quality_adjusted_games
                    else:
                        quality_win_rate = stats['win_pct']
                    
                    # Blend base rating with quality-adjusted performance
                    # This allows cross-conference results to calibrate ratings
                    sos_adjusted_rating = quality_win_rate * 1000 * stats['league_factor']
                    
                    # Blend: keep most of base rating, adjust with SOS-informed rating
                    stats['rating'] = (1 - SOS_WEIGHT) * stats['base_rating'] + SOS_WEIGHT * sos_adjusted_rating
                    
                    # Add SOS bonus (average opponent strength)
                    sos_bonus = (avg_opp_rating / 1000) * 100
                    stats['sos_bonus'] = sos_bonus
                    stats['sos'] = avg_opp_rating / 2000
                    stats['rating'] += sos_bonus
                else:
                    stats['sos_bonus'] = 0
                    stats['sos'] = 0
            
            # Check convergence (optional - for debugging)
            max_change = max(abs(team_stats[t]['rating'] - prev_ratings[t]) 
                           for t in team_stats if t in prev_ratings)
            # Uncomment to see convergence: print(f"  Iteration {iteration+1}: max rating change = {max_change:.1f}")
        
        # Store final SOS values after iteration completes
        for team, stats in team_stats.items():
            if stats['games_played'] < self.MIN_GAMES:
                stats['sos_bonus'] = 0
                stats['sos'] = 0
                continue
            
            opp_ratings = []
            for opp in stats['opponents']:
                if opp in team_stats:
                    opp_ratings.append(team_stats[opp].get('rating', 0))
            
            if opp_ratings:
                avg_opp_rating = np.mean(opp_ratings)
                stats['sos_bonus'] = (avg_opp_rating / 1000) * 100
                stats['sos'] = avg_opp_rating / 2000
                stats['avg_opp_rating'] = avg_opp_rating
        
        # V33: SOS penalty pass - penalize teams with weak schedules
        # This prevents undefeated teams that only play weak opponents from ranking too high
        for team, stats in team_stats.items():
            if stats['games_played'] < self.MIN_GAMES:
                stats['sos_penalty'] = 0
                continue
            
            avg_opp = stats.get('avg_opp_rating', 0)
            
            if avg_opp < self.SOS_PENALTY_THRESHOLD:
                # Scale penalty: 0 at threshold, max at 0 avg_opp_rating
                penalty_ratio = (self.SOS_PENALTY_THRESHOLD - avg_opp) / self.SOS_PENALTY_THRESHOLD
                penalty = penalty_ratio * self.SOS_PENALTY_MAX
                stats['sos_penalty'] = penalty
                stats['rating'] -= penalty
            else:
                stats['sos_penalty'] = 0
        
        # V37: Conference Strength Calibration
        # Calculate how each conference performs in cross-conference games
        # If a conference loses most cross-conference games, teams from that conference
        # should have their intra-conference wins devalued
        
        # Step 1: Build conference lookup and identify each team's conference
        team_conferences = {}
        for team, stats in team_stats.items():
            conf = stats.get('conference', '')
            league = stats.get('league', '')
            # Create a unique key combining league and conference
            conf_key = f"{league}|{conf}" if conf else f"{league}|Unknown"
            team_conferences[team] = conf_key
            stats['conf_key'] = conf_key
        
        # Step 2: Calculate cross-conference results for each conference
        conf_cross_results = {}  # conf_key -> {'wins': 0, 'losses': 0, 'ties': 0, 'gd': 0}
        
        for team, stats in team_stats.items():
            if stats['games_played'] < self.MIN_GAMES:
                continue
            
            my_conf = team_conferences.get(team, '')
            game_details = stats.get('game_details', [])
            
            for game in game_details:
                opp = game['opponent']
                opp_conf = team_conferences.get(opp, '')
                
                # Only count games where opponent is from a different conference
                # and both conferences are known
                if opp_conf and my_conf and opp_conf != my_conf:
                    if my_conf not in conf_cross_results:
                        conf_cross_results[my_conf] = {'wins': 0, 'losses': 0, 'ties': 0, 'gd': 0}
                    
                    result = game['result']
                    gf = game.get('goals_for', 0)
                    ga = game.get('goals_against', 0)
                    
                    if result == 'W':
                        conf_cross_results[my_conf]['wins'] += 1
                    elif result == 'L':
                        conf_cross_results[my_conf]['losses'] += 1
                    else:
                        conf_cross_results[my_conf]['ties'] += 1
                    conf_cross_results[my_conf]['gd'] += (gf - ga)
        
        # Step 3: Calculate conference strength factor
        # A conference with 60%+ cross-conference win rate gets a bonus
        # A conference with 40%- cross-conference win rate gets a penalty
        conf_strength_factors = {}
        
        for conf_key, results in conf_cross_results.items():
            total_games = results['wins'] + results['losses'] + results['ties']
            if total_games >= 5:  # Need at least 5 cross-conference games
                win_rate = (results['wins'] + 0.5 * results['ties']) / total_games
                avg_gd = results['gd'] / total_games
                
                # V37: Conference strength factor: 1.0 is neutral
                # STRONGER formula - Range from 0.60 (very weak) to 1.40 (very strong)
                # Based on win rate: 0% = 0.60, 50% = 1.0, 100% = 1.40
                strength_factor = 0.60 + (win_rate * 0.80)
                strength_factor = max(0.60, min(1.40, strength_factor))  # Clamp to range
                
                # Adjust by goal difference (stronger impact)
                gd_adjustment = max(-0.10, min(0.10, avg_gd * 0.02))
                strength_factor += gd_adjustment
                strength_factor = max(0.60, min(1.40, strength_factor))
                
                conf_strength_factors[conf_key] = {
                    'factor': strength_factor,
                    'win_rate': win_rate,
                    'games': total_games,
                    'gd': results['gd']
                }
            else:
                # Not enough cross-conference games - use neutral factor
                conf_strength_factors[conf_key] = {
                    'factor': 1.0,
                    'win_rate': 0.5,
                    'games': total_games,
                    'gd': 0
                }
        
        # Step 4: Apply conference strength adjustment to team ratings
        # Teams from strong conferences get a bonus, weak conferences get a penalty
        for team, stats in team_stats.items():
            if stats['games_played'] < self.MIN_GAMES:
                stats['conf_strength_adj'] = 0
                continue
            
            conf_key = stats.get('conf_key', '')
            conf_data = conf_strength_factors.get(conf_key, {'factor': 1.0})
            strength_factor = conf_data['factor']
            
            # Calculate adjustment: deviation from neutral (1.0)
            # V37: STRONGER adjustment - max ±720 rating points
            adjustment = (strength_factor - 1.0) * 1800  # Much stronger impact
            
            stats['conf_strength_factor'] = strength_factor
            stats['conf_strength_adj'] = adjustment
            stats['rating'] += adjustment
        
        # V33: Quality Wins pass - reward wins against top-ranked opponents
        # This is more important than average opponent strength
        # First, get preliminary rankings to identify top opponents
        prelim_sorted = sorted(team_stats.items(), key=lambda x: x[1].get('rating', 0), reverse=True)
        prelim_ranks = {team: rank+1 for rank, (team, _) in enumerate(prelim_sorted)}
        
        # V34: Reduced quality win point values (was 40/25/15/8)
        # These bonuses were too large and unfairly punished ECNL-RL teams
        QW_TOP10_POINTS = 25      # Win vs top 10 team (was 40)
        QW_TOP25_POINTS = 15      # Win vs top 11-25 team (was 25)
        QW_TOP50_POINTS = 10      # Win vs top 26-50 team (was 15)
        QW_TOP100_POINTS = 5      # Win vs top 51-100 team (was 8)
        
        # Margin multiplier: close wins count less, blowouts count more
        # margin 1 = 0.7x, margin 2 = 0.85x, margin 3+ = 1.0x
        def margin_multiplier(margin):
            if margin <= 0:
                return 0  # Ties/losses don't count
            elif margin == 1:
                return 0.7
            elif margin == 2:
                return 0.85
            else:
                return 1.0
        
        # V34: Only apply quality wins penalties to ECNL/GA teams
        # ECNL-RL teams can't get quality wins because top opponents are all ECNL/GA
        NO_QUALITY_WINS_PENALTY = 75   # V34: Reduced from 100
        FEW_QUALITY_WINS_PENALTY = 35  # V34: Reduced from 50
        
        for team, stats in team_stats.items():
            if stats['games_played'] < self.MIN_GAMES:
                stats['quality_wins_bonus'] = 0
                stats['quality_wins_penalty'] = 0
                stats['quality_wins_count'] = 0
                continue
            
            game_details = stats.get('game_details', [])
            quality_bonus = 0
            quality_wins_count = 0
            
            for game in game_details:
                if game['result'] != 'W':
                    continue
                
                opp = game['opponent']
                opp_rank = prelim_ranks.get(opp, 999)
                margin = game['margin']
                mult = margin_multiplier(margin)
                
                if opp_rank <= 10:
                    quality_bonus += QW_TOP10_POINTS * mult
                    quality_wins_count += 1
                elif opp_rank <= 25:
                    quality_bonus += QW_TOP25_POINTS * mult
                    quality_wins_count += 1
                elif opp_rank <= 50:
                    quality_bonus += QW_TOP50_POINTS * mult
                    quality_wins_count += 1
                elif opp_rank <= 100:
                    quality_bonus += QW_TOP100_POINTS * mult
                    quality_wins_count += 1
            
            stats['quality_wins_bonus'] = quality_bonus
            stats['quality_wins_count'] = quality_wins_count
            stats['rating'] += quality_bonus
            
            # V34: Only penalize ECNL/GA teams for no quality wins
            # ECNL-RL teams can't get quality wins - they only play within their league
            if stats['league'] in ['ECNL', 'GA']:
                # Penalty for teams with few/no quality wins
                # An undefeated team with 0 quality wins hasn't proven anything
                if quality_wins_count == 0 and stats['wins'] >= 5:
                    stats['quality_wins_penalty'] = NO_QUALITY_WINS_PENALTY
                    stats['rating'] -= NO_QUALITY_WINS_PENALTY
                elif quality_wins_count <= 2 and stats['wins'] >= 10:
                    # Team with 10+ wins but only 1-2 quality wins
                    stats['quality_wins_penalty'] = FEW_QUALITY_WINS_PENALTY
                    stats['rating'] -= FEW_QUALITY_WINS_PENALTY
                else:
                    stats['quality_wins_penalty'] = 0
            else:
                stats['quality_wins_penalty'] = 0
            
            # V33: Quality win RATIO penalty
            # Teams with lots of wins but few quality wins are padding stats vs weak teams
            # A team with 13 wins but only 5 quality wins (38%) should be penalized heavily
            # V34: Only apply quality ratio penalty to ECNL/GA teams
            # ECNL-RL teams can't accumulate quality wins
            if stats['league'] in ['ECNL', 'GA'] and stats['wins'] >= 8:
                quality_ratio = quality_wins_count / stats['wins'] if stats['wins'] > 0 else 0
                # Penalty if less than 60% of wins are quality wins
                # V34: Reduced penalties (was 300 and 150)
                if quality_ratio < 0.60:
                    base_penalty = (0.60 - quality_ratio) * 200  # V34: Reduced from 300
                    if quality_ratio < 0.40:
                        base_penalty += (0.40 - quality_ratio) * 100  # V34: Reduced from 150
                    stats['quality_ratio_penalty'] = base_penalty
                    stats['rating'] -= base_penalty
                else:
                    stats['quality_ratio_penalty'] = 0
            else:
                stats['quality_ratio_penalty'] = 0
            
            # V34: "Unproven at Elite Level" penalty - only for ECNL/GA teams
            # ECNL-RL teams can't play top-25 opponents
            game_details = stats.get('game_details', [])
            top25_wins = 0
            top25_win_margin_total = 0
            
            for game in game_details:
                if game['result'] == 'W':
                    opp = game['opponent']
                    opp_rank = prelim_ranks.get(opp, 999)
                    if opp_rank <= 25:
                        top25_wins += 1
                        top25_win_margin_total += game['margin']
            
            stats['top25_wins'] = top25_wins
            
            # V34: Only apply unproven penalty to ECNL/GA undefeated teams
            if stats['league'] in ['ECNL', 'GA'] and stats['wins'] >= 10 and stats['losses'] == 0:
                if top25_wins == 0:
                    # Undefeated with ZERO top-25 wins = heavily unproven
                    stats['unproven_penalty'] = 200  # V34: Reduced from 250
                    stats['rating'] -= 200
                elif top25_wins == 1:
                    # Only 1 top-25 win - partially unproven
                    if top25_win_margin_total >= 3:
                        stats['unproven_penalty'] = 60  # V34: Reduced from 80
                    else:
                        stats['unproven_penalty'] = 120  # V34: Reduced from 150
                    stats['rating'] -= stats['unproven_penalty']
                elif top25_wins == 2:
                    if top25_win_margin_total >= 4:
                        stats['unproven_penalty'] = 15  # V34: Reduced from 20
                    else:
                        stats['unproven_penalty'] = 35  # V34: Reduced from 50
                    stats['rating'] -= stats['unproven_penalty']
                else:
                    stats['unproven_penalty'] = 0
            else:
                stats['unproven_penalty'] = 0
        
        # Third pass: GA performance bonus
        for team, stats in team_stats.items():
            if stats['league'] != 'GA':
                stats['ga_bonus'] = 0
                continue
            
            games = stats['games_played']
            if games < self.MIN_GAMES:
                stats['ga_bonus'] = 0
                continue
            
            wins = stats['wins']
            losses = stats['losses']
            win_rate = wins / games if games > 0 else 0
            
            if losses == 0 and wins > 0:
                bonus_pct = self.GA_UNDEFEATED_BONUS
            elif win_rate > 0.80:
                bonus_pct = self.GA_HIGH_WIN_BONUS
            elif win_rate > 0.70:
                bonus_pct = self.GA_GOOD_WIN_BONUS
            else:
                bonus_pct = 0
            
            ga_bonus = stats['rating'] * bonus_pct
            stats['ga_bonus'] = ga_bonus
            stats['rating'] += ga_bonus
        
        # Fourth pass: ECNL-RL performance bonus
        for team, stats in team_stats.items():
            if stats['league'] != 'ECNL-RL':
                stats['ecnlrl_bonus'] = 0
                continue
            
            games = stats['games_played']
            if games < self.MIN_GAMES:
                stats['ecnlrl_bonus'] = 0
                continue
            
            wins = stats['wins']
            losses = stats['losses']
            win_rate = wins / games if games > 0 else 0
            
            if losses == 0 and wins > 0:
                bonus_pct = self.ECNLRL_UNDEFEATED_BONUS
            elif win_rate > 0.80:
                bonus_pct = self.ECNLRL_HIGH_WIN_BONUS
            elif win_rate > 0.70:
                bonus_pct = self.ECNLRL_GOOD_WIN_BONUS
            else:
                bonus_pct = 0
            
            ecnlrl_bonus = stats['rating'] * bonus_pct
            stats['ecnlrl_bonus'] = ecnlrl_bonus
            stats['rating'] += ecnlrl_bonus
        
        # V35: ECNL-RL ceiling/penalty - prevent too many ECNL-RL teams in top 100
        # ECNL-RL teams can't prove themselves against top competition
        # Apply both a flat penalty and ceiling compression to keep ~5-15 ECNL-RL teams in top 100
        ECNLRL_FLAT_PENALTY = 110     # V35: Flat penalty for playing in lower tier league
        ECNLRL_RATING_CEILING = 850   # V35: Cap ECNL-RL ratings
        ECNLRL_CEILING_COMPRESSION = 0.08  # V35: Keep 8% of excess (compress 92%)
        
        for team, stats in team_stats.items():
            if stats['league'] != 'ECNL-RL':
                stats['ecnlrl_ceiling_penalty'] = 0
                stats['ecnlrl_flat_penalty'] = 0
                continue
            
            # First apply flat penalty
            stats['ecnlrl_flat_penalty'] = ECNLRL_FLAT_PENALTY
            stats['rating'] -= ECNLRL_FLAT_PENALTY
            
            # Then apply ceiling compression
            if stats['rating'] > ECNLRL_RATING_CEILING:
                excess = stats['rating'] - ECNLRL_RATING_CEILING
                compressed_excess = excess * ECNLRL_CEILING_COMPRESSION
                penalty = excess - compressed_excess
                stats['ecnlrl_ceiling_penalty'] = penalty
                stats['rating'] -= penalty
            else:
                stats['ecnlrl_ceiling_penalty'] = 0
        
        # V30b: Fifth pass: GA ceiling compression (prevent GA from dominating top 5)
        for team, stats in team_stats.items():
            if stats['league'] != 'GA':
                stats['ga_ceiling_penalty'] = 0
                continue
            
            if stats['rating'] > self.GA_RATING_CEILING:
                excess = stats['rating'] - self.GA_RATING_CEILING
                compressed_excess = excess * self.GA_CEILING_COMPRESSION
                penalty = excess - compressed_excess
                stats['ga_ceiling_penalty'] = penalty
                stats['rating'] -= penalty
            else:
                stats['ga_ceiling_penalty'] = 0
        
        # V32: Sixth pass: Competitive game weighting
        # Games against similarly-rated opponents count more heavily
        # This ensures head-to-head results between comparable teams matter more
        COMPETITIVE_THRESHOLD = 300  # Teams within ±300 rating are "competitive"
        COMPETITIVE_WIN_BONUS = 15   # Bonus per competitive win
        COMPETITIVE_LOSS_PENALTY = 10  # Penalty per competitive loss
        
        for team, stats in team_stats.items():
            if stats['games_played'] < self.MIN_GAMES:
                stats['competitive_bonus'] = 0
                stats['competitive_wins'] = 0
                stats['competitive_losses'] = 0
                stats['competitive_draws'] = 0
                continue
            
            my_rating = stats['rating']
            game_details = stats.get('game_details', [])
            
            comp_wins = 0
            comp_losses = 0
            comp_draws = 0
            
            for game in game_details:
                opp = game['opponent']
                opp_rating = team_stats.get(opp, {}).get('rating', 0)
                rating_diff = abs(my_rating - opp_rating)
                
                # Only count games against teams within competitive threshold
                if rating_diff <= COMPETITIVE_THRESHOLD:
                    result = game['result']
                    if result == 'W':
                        comp_wins += 1
                    elif result == 'L':
                        comp_losses += 1
                    else:
                        comp_draws += 1
            
            # Calculate competitive bonus/penalty
            # More weight to wins against comparable teams, penalty for losses
            competitive_adjustment = (comp_wins * COMPETITIVE_WIN_BONUS) - (comp_losses * COMPETITIVE_LOSS_PENALTY)
            
            stats['competitive_bonus'] = competitive_adjustment
            stats['competitive_wins'] = comp_wins
            stats['competitive_losses'] = comp_losses
            stats['competitive_draws'] = comp_draws
            stats['rating'] += competitive_adjustment
        
        # V30: Seventh pass: Calculate predictability score
        self.calculate_predictability_scores(team_stats)
        
        # Filter and sort
        ranked_teams = {
            team: stats for team, stats in team_stats.items()
            if stats['games_played'] >= self.MIN_GAMES
        }
        
        sorted_teams = sorted(
            ranked_teams.items(), 
            key=lambda x: x[1]['rating'], 
            reverse=True
        )
        
        # V40: Apply minimum wins rule - teams with < 5 wins can't be in top 10
        sorted_teams = self.apply_min_wins_rule(sorted_teams)
        
        # V35: Eighth pass: Calculate records against different rank tiers
        # Create rank lookup from final sorted order
        final_ranks = {team: rank+1 for rank, (team, _) in enumerate(sorted_teams)}
        
        for rank, (team, stats) in enumerate(sorted_teams, 1):
            game_details = stats.get('game_details', [])
            
            # Initialize counters
            within50_w, within50_l, within50_t = 0, 0, 0  # Against teams within 50 ranks
            higher_w, higher_l, higher_t = 0, 0, 0        # Against higher ranked (lower number)
            lower_w, lower_l, lower_t = 0, 0, 0          # Against lower ranked (higher number)
            
            for game in game_details:
                opp = game['opponent']
                opp_rank = final_ranks.get(opp, 999)
                result = game['result']
                
                # Skip unranked opponents
                if opp_rank == 999:
                    continue
                
                rank_diff = abs(rank - opp_rank)
                
                # Record against teams within 50 spots
                if rank_diff <= 50:
                    if result == 'W':
                        within50_w += 1
                    elif result == 'L':
                        within50_l += 1
                    else:
                        within50_t += 1
                
                # Record against higher ranked teams (opponent has lower rank number)
                if opp_rank < rank:
                    if result == 'W':
                        higher_w += 1
                    elif result == 'L':
                        higher_l += 1
                    else:
                        higher_t += 1
                
                # Record against lower ranked teams (opponent has higher rank number)
                elif opp_rank > rank:
                    if result == 'W':
                        lower_w += 1
                    elif result == 'L':
                        lower_l += 1
                    else:
                        lower_t += 1
            
            # Store as formatted strings
            stats['record_within_50'] = f"{within50_w}-{within50_l}-{within50_t}"
            stats['record_vs_higher'] = f"{higher_w}-{higher_l}-{higher_t}"
            stats['record_vs_lower'] = f"{lower_w}-{lower_l}-{lower_t}"
            
            # V35: Calculate best/worst wins and losses
            # Formula: win_value = (500 - opponent_rank) + (margin * 12)
            # Higher value = better win
            # For losses: loss_badness = opponent_rank + (margin * 12)
            # Higher value = worse loss
            
            wins_with_value = []
            losses_with_value = []
            
            for game in game_details:
                opp = game['opponent']
                opp_rank = final_ranks.get(opp, 999)
                result = game['result']
                my_score = game.get('goals_for', 0)
                opp_score = game.get('goals_against', 0)
                margin = abs(my_score - opp_score)
                
                # Skip unranked opponents for this calculation
                if opp_rank == 999:
                    continue
                
                if result == 'W':
                    # win_value: higher rank opponent (lower number) + bigger margin = better
                    win_value = (500 - opp_rank) + (margin * 12)
                    wins_with_value.append((win_value, opp, my_score, opp_score, opp_rank))
                elif result == 'L':
                    # loss_badness: lower rank opponent (higher number) + bigger margin = worse
                    loss_badness = opp_rank + (margin * 12)
                    losses_with_value.append((loss_badness, opp, my_score, opp_score, opp_rank))
            
            # Sort wins by value (descending - best first)
            wins_with_value.sort(reverse=True)
            # Sort losses by badness (descending - worst first)
            losses_with_value.sort(reverse=True)
            
            # V36: Format: "#26 Team Name (3-1)" or empty string if none
            def format_result(data_list, index):
                if len(data_list) > index:
                    _, opp, my_s, opp_s, opp_r = data_list[index]
                    # Truncate long team names
                    opp_short = opp[:22] + "..." if len(opp) > 25 else opp
                    return f"#{opp_r} {opp_short} ({my_s}-{opp_s})"
                return ""
            
            stats['best_win'] = format_result(wins_with_value, 0)
            stats['second_best_win'] = format_result(wins_with_value, 1)
            stats['worst_loss'] = format_result(losses_with_value, 0)
            stats['second_worst_loss'] = format_result(losses_with_value, 1)
        
        # V41: Calculate offensive and defensive power scores
        self.calculate_offensive_defensive_power(sorted_teams, ranked_teams)
        
        return sorted_teams
    
    def calculate_predictability_scores(self, team_stats):
        """
        V33: Calculate predictability score (1-100) for each team
        
        Components:
        1. Games Component (0-30 pts): More games = more predictable
        2. Consistency Component (0-25 pts): Beats worse teams, loses to better teams
        3. Margin Alignment (0-20 pts): Margins correlate with opponent strength
        4. Opponent Quality (0-25 pts): V33 NEW - Have they played ranked opponents?
        """
        
        # First, calculate all teams' approximate ranks for opponent quality scoring
        sorted_teams = sorted(team_stats.items(), key=lambda x: x[1].get('rating', 0), reverse=True)
        team_ranks = {team: rank+1 for rank, (team, _) in enumerate(sorted_teams)}
        
        for team, stats in team_stats.items():
            games = stats['games_played']
            
            if games < self.MIN_GAMES:
                stats['predictability'] = 0
                stats['pred_games_score'] = 0
                stats['pred_consistency_score'] = 0
                stats['pred_margin_score'] = 0
                stats['pred_opp_quality_score'] = 0
                continue
            
            # Component 1: Games played (0-30 points)
            # Scale: 5 games = 0, 15+ games = 30
            games_score = min(games / self.PRED_IDEAL_GAMES, 1.0) * self.PRED_GAMES_WEIGHT
            
            # Component 2: Result consistency (0-25 points)
            # Do results match expectations based on opponent strength?
            game_details = stats.get('game_details', [])
            expected_results = 0
            total_decisive = 0
            
            my_rating = stats.get('rating', 0)
            
            for game in game_details:
                opp = game['opponent']
                opp_rating = team_stats.get(opp, {}).get('rating', 0)
                result = game['result']
                
                if result == 'T':
                    continue  # Ties are neutral
                
                total_decisive += 1
                rating_diff = my_rating - opp_rating
                
                # Expected: beat weaker teams (rating_diff > 0), lose to stronger (rating_diff < 0)
                if result == 'W' and rating_diff > -100:
                    # Won against weaker or roughly equal team
                    expected_results += 1
                elif result == 'L' and rating_diff < 100:
                    # Lost to stronger or roughly equal team
                    expected_results += 1
                elif result == 'W' and rating_diff <= -100:
                    # Upset win (beat stronger team) - partially expected
                    expected_results += 0.5
                elif result == 'L' and rating_diff >= 100:
                    # Upset loss (lost to weaker team) - unexpected
                    expected_results += 0
            
            if total_decisive > 0:
                consistency_rate = expected_results / total_decisive
                consistency_score = consistency_rate * self.PRED_CONSISTENCY_WEIGHT
            else:
                consistency_score = self.PRED_CONSISTENCY_WEIGHT * 0.5  # Neutral if all ties
            
            # Component 3: Margin alignment (0-20 points)
            # Do margins correlate with opponent strength?
            margins = []
            rating_diffs = []
            
            for game in game_details:
                opp = game['opponent']
                opp_rating = team_stats.get(opp, {}).get('rating', 0)
                margin = game['margin']
                rating_diff = my_rating - opp_rating
                
                margins.append(margin)
                rating_diffs.append(rating_diff)
            
            if len(margins) >= 3 and np.std(rating_diffs) > 0 and np.std(margins) > 0:
                # Calculate correlation between margin and rating difference
                # Expect: higher margin against weaker teams (positive correlation)
                try:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        correlation = np.corrcoef(margins, rating_diffs)[0, 1]
                    if np.isnan(correlation) or np.isinf(correlation):
                        correlation = 0
                    # Transform correlation (-1 to 1) to score (0 to 20)
                    # correlation of 0.5+ is good, -0.5 is bad
                    margin_score = max(0, min(1, (correlation + 0.5) / 1.0)) * self.PRED_MARGIN_WEIGHT
                except:
                    margin_score = self.PRED_MARGIN_WEIGHT * 0.5
            else:
                # Not enough data or variance for correlation
                margin_score = self.PRED_MARGIN_WEIGHT * 0.3
            
            # Component 4: V33 NEW - Opponent Quality (0-25 points)
            # Have they played any top-ranked opponents?
            # If all opponents are ranked 200+, we can't really predict how they'd do vs top teams
            top50_opponents = 0
            top100_opponents = 0
            top200_opponents = 0
            
            for game in game_details:
                opp = game['opponent']
                opp_rank = team_ranks.get(opp, 999)
                if opp_rank <= 50:
                    top50_opponents += 1
                if opp_rank <= 100:
                    top100_opponents += 1
                if opp_rank <= 200:
                    top200_opponents += 1
            
            # Score based on quality of opponents faced
            # Max points if played 3+ top-50 opponents OR 5+ top-100 opponents
            if top50_opponents >= 3:
                opp_quality_score = self.PRED_OPP_QUALITY_WEIGHT
            elif top50_opponents >= 1:
                opp_quality_score = self.PRED_OPP_QUALITY_WEIGHT * 0.7 + (top100_opponents / 5) * self.PRED_OPP_QUALITY_WEIGHT * 0.3
            elif top100_opponents >= 3:
                opp_quality_score = self.PRED_OPP_QUALITY_WEIGHT * 0.6
            elif top100_opponents >= 1:
                opp_quality_score = self.PRED_OPP_QUALITY_WEIGHT * 0.4
            elif top200_opponents >= 3:
                opp_quality_score = self.PRED_OPP_QUALITY_WEIGHT * 0.3
            else:
                # Never played a top-200 opponent - very low predictability
                opp_quality_score = self.PRED_OPP_QUALITY_WEIGHT * 0.1
            
            opp_quality_score = min(opp_quality_score, self.PRED_OPP_QUALITY_WEIGHT)
            
            # Total predictability (0-100)
            total_predictability = games_score + consistency_score + margin_score + opp_quality_score
            
            # Store components
            stats['pred_games_score'] = round(games_score, 1)
            stats['pred_consistency_score'] = round(consistency_score, 1)
            stats['pred_margin_score'] = round(margin_score, 1)
            stats['pred_opp_quality_score'] = round(opp_quality_score, 1)
            stats['predictability'] = round(total_predictability, 0)
    
    def calculate_offensive_defensive_power(self, sorted_teams, team_stats):
        """
        V41: Calculate offensive and defensive power scores and rankings.
        
        Offensive Power Score (0-100):
        - Goals per game (0-40 pts): Higher scoring = better
        - Big win percentage (0-25 pts): % of games won by 4+ goals
        - Scoring vs top teams (0-20 pts): Goals scored against ranked opponents
        - Comeback wins (0-15 pts): Wins when trailing
        
        Defensive Power Score (0-100):
        - Goals against per game (0-40 pts): Lower = better
        - Clean sheet percentage (0-25 pts): % of games with 0 goals against
        - Goals allowed vs top teams (0-20 pts): Goals allowed against ranked opponents
        - Blowout loss avoidance (0-15 pts): Avoiding 4+ goal losses
        """
        # Create rank lookup from sorted teams
        team_ranks = {team: rank+1 for rank, (team, _) in enumerate(sorted_teams)}
        
        # First pass: calculate raw offensive and defensive scores
        for team, stats in team_stats.items():
            games = stats.get('games_played', 0)
            
            if games < self.MIN_GAMES:
                stats['offensive_power_score'] = 0
                stats['defensive_power_score'] = 0
                stats['offensive_rank'] = 999
                stats['defensive_rank'] = 999
                stats['goals_per_game'] = 0
                stats['goals_against_per_game'] = 0
                stats['clean_sheets'] = 0
                continue
            
            gf = stats.get('goals_for', 0)
            ga = stats.get('goals_against', 0)
            big_wins = stats.get('big_wins', 0)
            blowout_losses = stats.get('blowout_losses', 0)
            game_details = stats.get('game_details', [])
            
            # ═══════════════════════════════════════════════════════════════
            # OFFENSIVE POWER CALCULATION
            # ═══════════════════════════════════════════════════════════════
            
            # Component 1: Goals per game (0-40 pts)
            # Scale: 0 goals = 0, 3+ goals/game = 40
            goals_per_game = gf / games
            stats['goals_per_game'] = round(goals_per_game, 2)
            offensive_gpg_score = min(goals_per_game / 3.0, 1.0) * 40
            
            # Component 2: Big win percentage (0-25 pts)
            # Winning by 4+ goals shows offensive dominance
            big_win_pct = big_wins / games
            offensive_big_win_score = min(big_win_pct / 0.30, 1.0) * 25  # 30% big wins = max
            
            # Component 3: Scoring vs ranked opponents (0-20 pts)
            goals_vs_ranked = 0
            games_vs_ranked = 0
            for game in game_details:
                opp = game['opponent']
                opp_rank = team_ranks.get(opp, 999)
                if opp_rank <= 100:  # Against top 100 opponents
                    goals_vs_ranked += game.get('goals_for', 0)
                    games_vs_ranked += 1
            
            if games_vs_ranked > 0:
                gpg_vs_ranked = goals_vs_ranked / games_vs_ranked
                offensive_vs_ranked_score = min(gpg_vs_ranked / 2.0, 1.0) * 20  # 2+ goals/game vs ranked = max
            else:
                offensive_vs_ranked_score = 5  # Default if no ranked opponents
            
            # Component 4: Multi-goal games bonus (0-15 pts)
            # Games with 2+ goals scored
            multi_goal_games = sum(1 for g in game_details if g.get('goals_for', 0) >= 2)
            multi_goal_pct = multi_goal_games / games
            offensive_multi_goal_score = min(multi_goal_pct / 0.80, 1.0) * 15  # 80% multi-goal games = max
            
            # Total Offensive Power (0-100)
            offensive_power = offensive_gpg_score + offensive_big_win_score + offensive_vs_ranked_score + offensive_multi_goal_score
            stats['offensive_power_score'] = round(min(offensive_power, 100), 1)
            
            # ═══════════════════════════════════════════════════════════════
            # DEFENSIVE POWER CALCULATION
            # ═══════════════════════════════════════════════════════════════
            
            # Component 1: Goals against per game (0-40 pts)
            # Scale: 3+ goals against = 0, 0 goals against = 40
            goals_against_per_game = ga / games
            stats['goals_against_per_game'] = round(goals_against_per_game, 2)
            defensive_gapg_score = max(0, (3.0 - goals_against_per_game) / 3.0) * 40
            
            # Component 2: Clean sheet percentage (0-25 pts)
            clean_sheets = sum(1 for g in game_details if g.get('goals_against', 0) == 0)
            stats['clean_sheets'] = clean_sheets
            clean_sheet_pct = clean_sheets / games
            defensive_clean_sheet_score = min(clean_sheet_pct / 0.40, 1.0) * 25  # 40% clean sheets = max
            
            # Component 3: Goals allowed vs ranked opponents (0-20 pts)
            goals_allowed_vs_ranked = 0
            for game in game_details:
                opp = game['opponent']
                opp_rank = team_ranks.get(opp, 999)
                if opp_rank <= 100:  # Against top 100 opponents
                    goals_allowed_vs_ranked += game.get('goals_against', 0)
            
            if games_vs_ranked > 0:
                gapg_vs_ranked = goals_allowed_vs_ranked / games_vs_ranked
                defensive_vs_ranked_score = max(0, (2.5 - gapg_vs_ranked) / 2.5) * 20  # 0 goals vs ranked = max
            else:
                defensive_vs_ranked_score = 5  # Default if no ranked opponents
            
            # Component 4: Blowout loss avoidance (0-15 pts)
            # Not losing by 4+ goals
            blowout_pct = blowout_losses / games
            defensive_no_blowout_score = max(0, (0.20 - blowout_pct) / 0.20) * 15  # 0 blowouts = max
            
            # Total Defensive Power (0-100)
            defensive_power = defensive_gapg_score + defensive_clean_sheet_score + defensive_vs_ranked_score + defensive_no_blowout_score
            stats['defensive_power_score'] = round(min(defensive_power, 100), 1)
        
        # Second pass: calculate rankings within this age group
        # Get all teams with valid scores
        valid_teams = [(team, stats) for team, stats in team_stats.items() 
                       if stats.get('games_played', 0) >= self.MIN_GAMES]
        
        # Sort by offensive power and assign ranks
        offensive_sorted = sorted(valid_teams, key=lambda x: x[1].get('offensive_power_score', 0), reverse=True)
        for rank, (team, _) in enumerate(offensive_sorted, 1):
            team_stats[team]['offensive_rank'] = rank
        
        # Sort by defensive power and assign ranks
        defensive_sorted = sorted(valid_teams, key=lambda x: x[1].get('defensive_power_score', 0), reverse=True)
        for rank, (team, _) in enumerate(defensive_sorted, 1):
            team_stats[team]['defensive_rank'] = rank
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_state_from_conference(self, conference):
        """Extract state abbreviation from conference name"""
        if not conference:
            return ''
        
        conf = str(conference).upper()
        
        # V34: Fixed state extraction - use word boundary matching
        # Order matters - check longer patterns first to avoid false matches
        import re
        
        # Patterns that should NOT match to states (multi-state regions)
        no_match_patterns = [
            'MID-ATLANTIC', 'MID-AMERICA', 'MIDATLANTIC', 'MIDAMERICA',
            'PACIFIC-NORTHWEST', 'PACIFIC NORTHWEST',
            'NORTHEAST', 'NORTHWEST', 'SOUTHEAST', 'SOUTHWEST',
            'MIDWEST', 'FRONTIER', 'MOUNTAIN', 'GREATER', 'TWIN CITIES'
        ]
        
        for pattern in no_match_patterns:
            if pattern in conf:
                return ''  # Multi-state region, no single state
        
        # Now check for specific state patterns (use word boundaries)
        state_patterns = [
            (r'\bTEXAS\b', 'TX'), (r'\bTX\b', 'TX'), (r'\bNTX\b', 'TX'), (r'\bSTX\b', 'TX'),
            (r'\bCALIFORNIA\b', 'CA'), (r'\bSOCAL\b', 'CA'), (r'\bNORCAL\b', 'CA'), 
            (r'\bSOUTHERN CAL\b', 'CA'),
            (r'\bFLORIDA\b', 'FL'),
            (r'\bOHIO\b', 'OH'), (r'\bOHIO VALLEY\b', 'OH'),
            (r'\bGEORGIA\b', 'GA'),
            (r'\bARIZONA\b', 'AZ'),
            (r'\bWASHINGTON\b', 'WA'),
            (r'\bNEW YORK\b', 'NY'),
            (r'\bMISSOURI\b', 'MO'),
            (r'\bILLINOIS\b', 'IL'),
            (r'\bPENNSYLVANIA\b', 'PA'),
            (r'\bVIRGINIA\b', 'VA'),
            (r'\bNORTH CAROLINA\b', 'NC'),
            (r'\bSOUTH CAROLINA\b', 'SC'),
            (r'\bIOWA\b', 'IA'),
            (r'\bCOLORADO\b', 'CO'),
            (r'\bTENNESSEE\b', 'TN'),
            (r'\bMARYLAND\b', 'MD'),
            (r'\bMICHIGAN\b', 'MI'),
            (r'\bMINNESOTA\b', 'MN'),
            (r'\bINDIANA\b', 'IN'),
            (r'\bWISCONSIN\b', 'WI'),
            (r'\bNEW JERSEY\b', 'NJ'),
            (r'\bNEW ENGLAND\b', 'MA'),  # Default to MA for New England
            (r'\bNORTH ATLANTIC\b', 'NY'),  # Default to NY for North Atlantic
        ]
        
        for pattern, state in state_patterns:
            if re.search(pattern, conf):
                return state
        
        return ''
    
    # V39: State name to abbreviation mapping
    STATE_ABBREVIATIONS = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
        # Common abbreviations that might be in the data
        'co': 'CO', 'ca': 'CA', 'tx': 'TX', 'fl': 'FL', 'ny': 'NY',
    }
    
    def get_team_state(self, team_name, conference=''):
        """
        V39: Get state for a team, first checking the teams table, 
        then falling back to conference mapping
        """
        if not team_name:
            return ''
        
        # First, try to look up from teams table
        team_key = team_name.lower().strip()
        if team_key in self.team_states:
            state_name = self.team_states[team_key].lower().strip()
            # Convert to abbreviation if it's a full name
            if state_name in self.STATE_ABBREVIATIONS:
                return self.STATE_ABBREVIATIONS[state_name]
            # Already an abbreviation
            if len(state_name) == 2:
                return state_name.upper()
            return state_name.upper()[:2]  # Fallback
        
        # Fall back to conference-based lookup
        return self.get_state_from_conference(conference)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # V29: DIAGNOSTICS REPORT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_diagnostics_report(self):
        """Print detailed diagnostics about data quality issues"""
        print(f"\n{'='*80}")
        print(" DATA QUALITY DIAGNOSTICS REPORT")
        print(f"{'='*80}")
        
        # Bad team names
        bad_names = self.diagnostics.get('bad_team_names_found', [])
        if bad_names:
            # Count by reason
            reason_counts = defaultdict(int)
            unique_bad_names = set()
            for item in bad_names:
                reason_counts[item['reason']] += 1
                unique_bad_names.add(item['team'])
            
            print(f"\n Bad Team Names: {len(bad_names)} instances, {len(unique_bad_names)} unique")
            print("   Breakdown by reason:")
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"     {count:5,} - {reason}")
            
            print(f"\n   Sample bad team name strings:")
            for name in list(unique_bad_names)[:15]:
                print(f"     '{name}'")
        
        # Duplicate samples
        dup_samples = self.diagnostics.get('duplicates_removed_samples', [])
        if dup_samples:
            print(f"\n Sample Duplicates Removed:")
            for sample in dup_samples[:10]:
                print(f"     {sample.get('game_date', 'N/A')} | {sample.get('home_team', 'N/A')[:25]} vs {sample.get('away_team', 'N/A')[:25]} | {sample.get('home_score', 0)}-{sample.get('away_score', 0)}")
        
        # Gender breakdown
        gender_breakdown = self.diagnostics.get('age_group_gender_breakdown', {})
        if gender_breakdown:
            print(f"\n Age Group / Gender in Database:")
            for age, genders in sorted(gender_breakdown.items()):
                parts = [f"{g}:{c:,}" for g, c in genders.items()]
                print(f"     {age}: {', '.join(parts)}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN RUNNER
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_all_age_groups(self, do_cleanup=None, dry_run=False):
        """Generate rankings for all age groups"""
        print(f"\n{'='*80}")
        print("[TROPHY] SOCCER TEAM RANKING SYSTEM V42")
        print(f"{'='*80}")
        print(f"Database: {self.db_path}")
        print(f"League Factors: ECNL={self.LEAGUE_FACTORS['ECNL']}, "
              f"GA={self.LEAGUE_FACTORS['GA']}, ECNL-RL={self.LEAGUE_FACTORS['ECNL-RL']}, "
              f"ASPIRE={self.LEAGUE_FACTORS['ASPIRE']}, NPL=0.90, Default={self.DEFAULT_LEAGUE_FACTOR}")
        print(f"Performance Bonuses: GA undefeated={self.GA_UNDEFEATED_BONUS:.0%}, "
              f"ECNL-RL undefeated={self.ECNLRL_UNDEFEATED_BONUS:.0%}")
        print(f"GA Ceiling: {self.GA_RATING_CEILING} (compress {1-self.GA_CEILING_COMPRESSION:.0%} of excess)")
        print(f"Game Count: Min={self.MIN_GAMES}, Ideal={self.IDEAL_GAMES} (penalty if <{self.IDEAL_GAMES})")
        print(f"Team Aliases: {len(self.TEAM_ALIASES)} patterns configured")
        
        if do_cleanup is None and CLEANUP_AVAILABLE:
            print("\n" + "="*60)
            response = input(" Run database cleanup first? (y/n): ").strip().lower()
            do_cleanup = response in ['y', 'yes']
        elif do_cleanup is None:
            do_cleanup = False
        
        if do_cleanup:
            self.run_database_cleanup(dry_run=dry_run)
        else:
            print("\n  Skipping database cleanup")
        
        self.load_game_data()
        
        all_rankings = {}
        
        for age_group in self.all_age_groups:
            print(f"\n{'='*60}")
            print(f" RANKING: {age_group}")
            print(f"{'='*60}")
            
            games = self.get_age_group_games(age_group)
            print(f"Games: {len(games):,}")
            
            if len(games) < 10:
                print("  Insufficient games for ranking")
                continue
            
            print(f"League distribution:")
            for league, count in games['league'].value_counts().items():
                print(f"  {league}: {count:,}")
            
            rankings = self.calculate_rankings(games)
            all_rankings[age_group] = rankings
            
            # V30: Updated display with predictability
            print(f"\n[TROPHY] Top 15 {age_group}:")
            print("-" * 80)
            print(f"{'Rk':>2}  {'Team':<32} {'League':<8} {'Record':<10} {'Rating':>6} {'Pred':>4}")
            print("-" * 80)
            
            for rank, (team, stats) in enumerate(rankings[:15], 1):
                record = f"{stats['wins']}-{stats['losses']}-{stats['ties']}"
                league = stats['league']
                rating = stats['rating']
                pred = stats.get('predictability', 0)
                print(f"{rank:2}. {team[:32]:<32} ({league:<7}) {record:<10} {rating:6.0f} {pred:4.0f}")
            
            print(f"\n[CHART] Top 100 by League:")
            top_100 = rankings[:100]
            league_counts = {}
            for _, stats in top_100:
                lg = stats['league']
                league_counts[lg] = league_counts.get(lg, 0) + 1
            for lg, count in sorted(league_counts.items()):
                print(f"  {lg}: {count}")
        
        # V29: Print diagnostics if verbose
        if self.verbose:
            self.print_diagnostics_report()
        
        # Save outputs
        self.save_outputs(all_rankings)
    
    def save_outputs(self, all_rankings):
        """
        Save rankings to JSON (for React app) and Excel
        
        V39: Includes player data and improved state lookup
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ═══════════════════════════════════════════════════════════════════
        # BUILD teamsData - flat array with all teams across age groups
        # ═══════════════════════════════════════════════════════════════════
        
        teams_data = []
        team_id = 1
        all_states = set()
        all_leagues = set()
        all_genders = set()  # V39: Track genders
        
        for age_group, rankings in all_rankings.items():
            # V39: Determine gender from age group
            if age_group.startswith('B'):
                gender = 'Boys'
            else:
                gender = 'Girls'
            all_genders.add(gender)
            
            for rank, (team, stats) in enumerate(rankings[:500], 1):
                # V39: Use get_team_state instead of get_state_from_conference
                state = self.get_team_state(team, stats.get('conference', ''))
                if state:
                    all_states.add(state)
                all_leagues.add(stats['league'])
                
                # V41: Calculate average goal differential
                games_played = stats['games_played']
                avg_gd = stats['goal_diff'] / games_played if games_played > 0 else 0
                
                # V41: Format conference strength
                conf_strength_factor = stats.get('conf_strength_factor', 1.0)
                conf_strength_diff = conf_strength_factor - 1.0
                conf_strength_str = f"+{conf_strength_diff:.2f}" if conf_strength_diff >= 0 else f"{conf_strength_diff:.2f}"
                
                teams_data.append({
                    'id': team_id,
                    'name': team,
                    'club': self.extract_club_name(team),
                    'state': state,
                    'league': stats['league'],
                    'ageGroup': age_group,
                    'gender': gender,  # V39: Add gender field
                    'powerScore': round(stats['rating'], 1),
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'draws': stats['ties'],
                    'goalsFor': stats['goals_for'],
                    'goalsAgainst': stats['goals_against'],
                    'goalDiff': stats['goal_diff'],
                    'gamesPlayed': stats['games_played'],
                    'winPct': round(stats['win_pct'], 3),
                    'sos': round(stats.get('sos', 0), 3),
                    'blowoutLosses': stats['blowout_losses'],
                    'bigWins': stats['big_wins'],
                    'rank': rank,  # Rank within age group
                    'predictability': stats.get('predictability', 0),
                    # V41: New fields - Offensive/Defensive Power
                    'offensivePowerScore': stats.get('offensive_power_score', 0),
                    'defensivePowerScore': stats.get('defensive_power_score', 0),
                    'offensiveRank': stats.get('offensive_rank', 999),
                    'defensiveRank': stats.get('defensive_rank', 999),
                    'goalsPerGame': stats.get('goals_per_game', 0),
                    'goalsAgainstPerGame': stats.get('goals_against_per_game', 0),
                    'cleanSheets': stats.get('clean_sheets', 0),
                    # V41: New fields - Best/Worst Results
                    'bestWin': stats.get('best_win', ''),
                    'secondBestWin': stats.get('second_best_win', ''),
                    'worstLoss': stats.get('worst_loss', ''),
                    'secondWorstLoss': stats.get('second_worst_loss', ''),
                    # V41: New fields - Record breakdowns
                    'recordWithin50': stats.get('record_within_50', '0-0-0'),
                    'recordVsHigher': stats.get('record_vs_higher', '0-0-0'),
                    'recordVsLower': stats.get('record_vs_lower', '0-0-0'),
                    # V41: New fields - Conference and scoring
                    'confStrength': conf_strength_str,
                    'avgGD': round(avg_gd, 2),
                })
                team_id += 1
        
        # ═══════════════════════════════════════════════════════════════════
        # BUILD gamesData - individual games for team schedules
        # ═══════════════════════════════════════════════════════════════════
        
        games_data = []
        game_id = 1
        
        for _, game in self.games_df.iterrows():
            age_group = game['age_group']
            # V39: Keep B format for Boys, convert U to G for Girls only
            if age_group.startswith('U'):
                age_num = age_group[1:]
                age_group = f'G{age_num}'
            
            games_data.append({
                'id': game_id,
                'date': str(game['game_date'])[:10],  # YYYY-MM-DD
                'homeTeam': game['home_team'],
                'awayTeam': game['away_team'],
                'homeScore': int(game['home_score']),
                'awayScore': int(game['away_score']),
                'ageGroup': age_group,
                'league': game['league'],
            })
            game_id += 1
        
        # ═══════════════════════════════════════════════════════════════════
        # V39: BUILD playersData - from players table in database
        # ═══════════════════════════════════════════════════════════════════
        
        players_data = []
        print("\n Loading players from database...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            player_query = """
                SELECT 
                    id, player_name, first_name, last_name, team_name, 
                    jersey_number, position, graduation_year, height,
                    hometown, high_school, club, college_commitment,
                    age_group, league
                FROM players
            """
            players_df = pd.read_sql_query(player_query, conn)
            conn.close()
            
            for _, player in players_df.iterrows():
                # Determine gender from age_group
                age_group = player['age_group'] or ''
                if age_group.startswith('B'):
                    gender = 'Boys'
                else:
                    gender = 'Girls'
                
                players_data.append({
                    'id': int(player['id']),
                    'name': player['player_name'] or '',
                    'firstName': player['first_name'] or '',
                    'lastName': player['last_name'] or '',
                    'teamName': player['team_name'] or '',
                    'jerseyNumber': player['jersey_number'] or '',
                    'position': player['position'] or '',
                    'graduationYear': player['graduation_year'] or '',
                    'height': player['height'] or '',
                    'hometown': player['hometown'] or '',
                    'highSchool': player['high_school'] or '',
                    'club': player['club'] or '',
                    'collegeCommitment': player['college_commitment'] or '',
                    'ageGroup': age_group,
                    'league': player['league'] or '',
                    'gender': gender,
                })
            
            print(f"   Loaded {len(players_data):,} players")
        except Exception as e:
            print(f"   WARNING: Could not load players: {e}")
            players_data = []
        
        # ═══════════════════════════════════════════════════════════════════
        # ASSEMBLE FINAL JSON
        # ═══════════════════════════════════════════════════════════════════
        
        react_data = {
            'teamsData': teams_data,
            'gamesData': games_data,
            'playersData': players_data,  # V39: Added players
            'ageGroups': self.all_age_groups,
            'leagues': sorted(list(all_leagues)),
            'states': sorted(list(all_states)),
            'genders': sorted(list(all_genders)),  # V39: Added genders
            'lastUpdated': datetime.now().isoformat(),
        }
        
        # Save locally
        json_path = Path('rankings_for_react.json')
        with open(json_path, 'w') as f:
            json.dump(react_data, f, indent=2)
        print(f"\n[OK] Saved: {json_path}")
        print(f"   Teams: {len(teams_data):,}")
        print(f"   Games: {len(games_data):,}")
        print(f"   Players: {len(players_data):,}")
        print(f"   States: {len(all_states)}")
        print(f"   Genders: {list(all_genders)}")
        
        # ═══════════════════════════════════════════════════════════════════
        # COPY TO REACT APP PUBLIC FOLDER
        # ═══════════════════════════════════════════════════════════════════
        
        if os.path.exists(REACT_APP_PUBLIC_FOLDER):
            dest_path = Path(REACT_APP_PUBLIC_FOLDER) / 'rankings_for_react.json'
            shutil.copy(json_path, dest_path)
            print(f"[OK] Copied to React app: {dest_path}")
        else:
            print(f"WARNING:  React app folder not found: {REACT_APP_PUBLIC_FOLDER}")
            print("   Update REACT_APP_PUBLIC_FOLDER in the script to enable auto-copy")
        
        # ═══════════════════════════════════════════════════════════════════
        # SAVE EXCEL - V41: With offensive/defensive power scores
        # ═══════════════════════════════════════════════════════════════════
        
        try:
            all_rows = []
            for age_group, rankings in all_rankings.items():
                for rank, (team, stats) in enumerate(rankings, 1):
                    games_played = stats['games_played']
                    avg_gd = stats['goal_diff'] / games_played if games_played > 0 else 0
                    
                    all_rows.append({
                        'Rank': f"#{rank}",
                        'Team': team,
                        'Age Group': age_group,
                        'Gender': 'Boys' if age_group.startswith('B') else 'Girls',
                        'League': stats['league'],
                        'Conf Strength': f"+{(stats.get('conf_strength_factor', 1.0) - 1.0):.2f}" if stats.get('conf_strength_factor', 1.0) >= 1.0 else f"{(stats.get('conf_strength_factor', 1.0) - 1.0):.2f}",
                        'State': self.get_team_state(team, stats.get('conference', '')),
                        'Power Score': round(stats['rating'], 1),
                        # V41: New offensive/defensive columns
                        'Off Power': stats.get('offensive_power_score', 0),
                        'Off Rank': f"#{stats.get('offensive_rank', 999)}" if stats.get('offensive_rank', 999) < 999 else '-',
                        'Def Power': stats.get('defensive_power_score', 0),
                        'Def Rank': f"#{stats.get('defensive_rank', 999)}" if stats.get('defensive_rank', 999) < 999 else '-',
                        'Goals/Game': stats.get('goals_per_game', 0),
                        'GA/Game': stats.get('goals_against_per_game', 0),
                        'Clean Sheets': stats.get('clean_sheets', 0),
                        'Predictability': stats.get('predictability', 0),
                        'Record': f"{stats['wins']}-{stats['losses']}-{stats['ties']}",
                        'vs Within 50': stats.get('record_within_50', '0-0-0'),
                        'vs Higher Ranked': stats.get('record_vs_higher', '0-0-0'),
                        'vs Lower Ranked': stats.get('record_vs_lower', '0-0-0'),
                        'Best Win': stats.get('best_win', ''),
                        '2nd Best Win': stats.get('second_best_win', ''),
                        'Worst Loss': stats.get('worst_loss', ''),
                        '2nd Worst Loss': stats.get('second_worst_loss', ''),
                        'Avg GD': f"+{avg_gd:.2f}" if avg_gd > 0 else f"{avg_gd:.2f}",
                        'Games': stats['games_played'],
                    })
            
            df = pd.DataFrame(all_rows)
            excel_path = Path(f'All_Age_Groups_Rankings_V41_{timestamp}.xlsx')
            df.to_excel(excel_path, index=False)
            print(f"[OK] Saved: {excel_path}")
        except Exception as e:
            print(f"WARNING: Could not save Excel: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def find_database():
    """Find the database file in common locations"""
    candidates = [
        r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db",
        '../seedlinedata.db',
        './seedlinedata.db',
        'seedlinedata.db',
        '/mnt/user-data/uploads/seedlinedata.db',
        '/home/claude/seedline/seedlinedata.db',
    ]
    
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Soccer Team Ranking System V41 - Offensive/Defensive Power Scores',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python team_ranker_v41.py                        # Interactive
  python team_ranker_v41.py --cleanup              # Force cleanup first  
  python team_ranker_v41.py --no-cleanup           # Skip cleanup
  python team_ranker_v41.py --dry-run              # Preview cleanup only
  python team_ranker_v41.py --verbose              # Show detailed diagnostics
  python team_ranker_v41.py path/to/data.db        # Specify database

V41 Changes:
  - Offensive Power Score (0-100): Measures attacking strength
  - Defensive Power Score (0-100): Measures defensive strength
  - Offensive/Defensive Rankings within each age group
  - Expanded JSON export with all Excel columns for React app
        """
    )
    
    parser.add_argument('db_path', nargs='?', default=None,
                       help='Path to database file')
    
    cleanup_group = parser.add_mutually_exclusive_group()
    cleanup_group.add_argument('--cleanup', '-c', action='store_true',
                              help='Run database cleanup before ranking')
    cleanup_group.add_argument('--no-cleanup', '-n', action='store_true',
                              help='Skip database cleanup')
    
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Preview cleanup without modifying database')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed diagnostics about filtered data')
    
    args = parser.parse_args()
    
    if args.cleanup:
        do_cleanup = True
    elif args.no_cleanup:
        do_cleanup = False
    else:
        do_cleanup = None
    
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = find_database()
        if not db_path:
            print("[ERROR] Database not found. Please provide path as argument.")
            sys.exit(1)
    
    try:
        ranker = TeamRankerV30(db_path, verbose=args.verbose)
        ranker.run_all_age_groups(do_cleanup=do_cleanup, dry_run=args.dry_run)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
