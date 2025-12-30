#!/usr/bin/env python3
"""
Scheduled Scraper for League Games and Tournaments
===================================================
Smart scheduling based on actual game patterns:
- Saturday/Sunday: Full scrape (95% of games happen on weekends)
- Monday/Tuesday: Follow-up scrape for weekend games missing results
- Wednesday-Friday: Skip unless games are specifically scheduled

League game day patterns (from historical data):
- ECNL/ECNL RL: 93%+ on Sat/Sun
- GA: 86% on Sat/Sun (some Thu/Fri)
- ASPIRE: 99% on Sat/Sun
- NPL: 97% on Sat/Sun

Usage:
    python scheduled_scraper.py                    # Smart scrape based on day
    python scheduled_scraper.py --force            # Force full scrape regardless of day
    python scheduled_scraper.py --dry-run          # Show what would be scraped
    python scheduled_scraper.py --missing-only     # Only scrape games missing results
    python scheduled_scraper.py --ecnl-only        # Only scrape ECNL games
    python scheduled_scraper.py --ga-only          # Only scrape GA games
    python scheduled_scraper.py --aspire-only      # Only scrape ASPIRE games
"""

import sqlite3
import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Optional
import json
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'scraper_schedule.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "seedlinedata.db"
SCRAPERS_DIR = BASE_DIR / "Scrapers"

# Scraper configurations
SCRAPERS = {
    'ECNL': {
        'name': 'ECNL + ECNL RL',
        'folder': 'ECNL and ECNL RL Scraper',
        'pattern': 'ecnl_scraper_final.py',
        'leagues': ['ECNL', 'ECNL RL'],
        'game_days': [5, 6],  # Saturday=5, Sunday=6 (0=Monday)
        'extra_args': ['--headless', '--no-confirm'],  # Run without visible browser
    },
    'GA': {
        'name': 'Girls Academy',
        'folder': 'girls academy league scraper',
        'pattern': 'GA_league_scraper_final.py',
        'leagues': ['GA'],
        'game_days': [5, 6],  # Some Thu/Fri but mostly weekends
        'extra_args': ['--no-confirm'],  # Uses requests, no browser needed
    },
    'ASPIRE': {
        'name': 'ASPIRE',
        'folder': 'aspire scraper',
        'pattern': 'ASPIRE_league_scraper_final.py',
        'leagues': ['ASPIRE'],
        'game_days': [5, 6],  # Almost exclusively weekends
        'extra_args': ['--no-confirm'],  # Uses requests, no browser needed
    },
    'REGIONAL': {
        'name': 'Regional Leagues & State Cups',
        'folder': 'California Regional Leagues',
        'pattern': 'california_regional_scraper_final.py',
        'leagues': ['ICSL', 'SLYSA', 'SOCAL', 'SoCal Soccer League', 'NorCal Premier',
                    'State Cup', 'Presidents Cup', 'EDP', 'WFPL', 'SEFPL', 'MSPSP',
                    'Georgia Soccer', 'TCSL', 'Northwest Conference', 'WYSA State League',
                    'Baltimore Mania', 'Real CO Cup', 'LVYSL', 'APL', 'WVFC Capital Cup'],
        'game_days': [5, 6],  # Mostly weekends
        'extra_args': ['--auto'],  # Use event tracking to scrape due events
        'use_event_tracking': True,  # Uses league_events table for smart scheduling
    },
    'NPL': {
        'name': 'NPL Leagues',
        'folder': 'NPL league scraper',
        'pattern': 'us_club_npl_league_scraper_final.py',
        'leagues': ['NPL', 'FCL NPL (Florida)', 'Great Lakes Alliance NPL', 'NorCal NPL',
                    'SOCAL NPL', 'Central States NPL', 'Minnesota NPL', 'Wisconsin NPL'],
        'game_days': [5, 6],  # Mostly weekends
        'extra_args': ['--all', '--no-confirm'],
    },
    'MLS_NEXT': {
        'name': 'MLS NEXT',
        'folder': 'MLS NEXT scraper',
        'pattern': 'mls_next_scraper_final.py',
        'leagues': ['MLS NEXT'],
        'game_days': [5, 6],  # Mostly weekends
        'extra_args': ['--no-confirm'],
    },
}


class SmartScheduler:
    """Smart scraper scheduler that considers game day patterns"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.today = datetime.now()
        self.day_of_week = self.today.weekday()  # 0=Monday, 6=Sunday
        self.day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][self.day_of_week]

    def get_games_needing_scrape(self, days_back: int = 7) -> Dict[str, Dict]:
        """Get games that need scraping, grouped by league"""
        if not self.db_path.exists():
            logger.error(f"Database not found: {self.db_path}")
            return {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        today_str = self.today.strftime('%Y-%m-%d')
        start_date = (self.today - timedelta(days=days_back)).strftime('%Y-%m-%d')

        results = {}

        for scraper_id, config in SCRAPERS.items():
            leagues_placeholder = ','.join(['?' for _ in config['leagues']])

            # Games missing results
            cursor.execute(f'''
                SELECT COUNT(*), game_date FROM games
                WHERE league IN ({leagues_placeholder})
                AND game_date >= ? AND game_date <= ?
                AND (home_score IS NULL OR away_score IS NULL)
                GROUP BY game_date
                ORDER BY game_date DESC
            ''', config['leagues'] + [start_date, today_str])

            missing_by_date = cursor.fetchall()
            total_missing = sum(count for count, _ in missing_by_date)

            # Games from today
            cursor.execute(f'''
                SELECT COUNT(*) FROM games
                WHERE league IN ({leagues_placeholder})
                AND game_date = ?
            ''', config['leagues'] + [today_str])
            today_games = cursor.fetchone()[0]

            # Games from yesterday
            yesterday_str = (self.today - timedelta(days=1)).strftime('%Y-%m-%d')
            cursor.execute(f'''
                SELECT COUNT(*) FROM games
                WHERE league IN ({leagues_placeholder})
                AND game_date = ?
                AND (home_score IS NULL OR away_score IS NULL)
            ''', config['leagues'] + [yesterday_str])
            yesterday_missing = cursor.fetchone()[0]

            results[scraper_id] = {
                'name': config['name'],
                'total_missing': total_missing,
                'today_games': today_games,
                'yesterday_missing': yesterday_missing,
                'missing_by_date': missing_by_date,
                'should_scrape': total_missing > 0 or today_games > 0,
            }

        conn.close()
        return results

    def should_run_today(self, force: bool = False) -> Dict[str, bool]:
        """Determine which scrapers should run based on day of week and game data"""
        if force:
            return {scraper_id: True for scraper_id in SCRAPERS}

        games_status = self.get_games_needing_scrape()
        should_run = {}

        for scraper_id, config in SCRAPERS.items():
            status = games_status.get(scraper_id, {})

            # Always run if there are games missing results
            if status.get('total_missing', 0) > 0:
                should_run[scraper_id] = True
                continue

            # Run on game days (Sat/Sun) or day after (Mon for Sunday games)
            if self.day_of_week in [5, 6]:  # Saturday or Sunday
                should_run[scraper_id] = True
            elif self.day_of_week == 0:  # Monday - catch Sunday games
                should_run[scraper_id] = status.get('yesterday_missing', 0) > 0
            elif self.day_of_week == 1:  # Tuesday - final weekend cleanup
                should_run[scraper_id] = status.get('total_missing', 0) > 0
            else:  # Wed-Fri - only if games exist
                should_run[scraper_id] = status.get('today_games', 0) > 0

        return should_run

    def find_latest_scraper(self, scraper_id: str) -> Optional[Path]:
        """Find the latest version of a scraper"""
        config = SCRAPERS.get(scraper_id)
        if not config:
            return None

        folder = SCRAPERS_DIR / config['folder']
        if not folder.exists():
            logger.warning(f"Scraper folder not found: {folder}")
            return None

        # Find matching files
        pattern = config['pattern']
        files = list(folder.glob(pattern))

        if not files:
            logger.warning(f"No scraper files matching {pattern} in {folder}")
            return None

        # Sort by version number
        def get_version(f):
            match = re.search(r'v(\d+)', f.name)
            return int(match.group(1)) if match else 0

        files.sort(key=get_version, reverse=True)
        return files[0]

    def run_scraper(self, scraper_id: str, dry_run: bool = False, background: bool = True) -> bool:
        """Run a specific scraper

        Args:
            scraper_id: Which scraper to run
            dry_run: If True, just log what would run
            background: If True, run in background (for scheduled tasks)
                       If False, open visible CMD window (for manual runs)
        """
        scraper_path = self.find_latest_scraper(scraper_id)
        if not scraper_path:
            logger.error(f"Could not find scraper for {scraper_id}")
            return False

        config = SCRAPERS[scraper_id]
        extra_args = config.get('extra_args', [])
        args_str = ' '.join(extra_args)

        logger.info(f"{'[DRY RUN] Would run' if dry_run else 'Running'}: {config['name']} ({scraper_path.name}) {args_str}")

        if dry_run:
            return True

        try:
            if background:
                # Run in background - no visible window, output to log
                log_file = BASE_DIR / f"scraper_{scraper_id.lower()}.log"
                cmd = f'cd /d "{scraper_path.parent}" && python "{scraper_path.name}" {args_str} >> "{log_file}" 2>&1'

                # Use subprocess to run in background
                subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                logger.info(f"  Started in background, logging to: {log_file.name}")
            else:
                # Run in visible CMD window (for manual testing)
                window_title = f"Seedline - {config['name']}"
                cmd = f'start "{window_title}" cmd /k "cd /d \\"{scraper_path.parent}\\" && python \\"{scraper_path.name}\\" {args_str} && echo. && echo Scrape complete. && pause"'
                os.system(cmd)

            return True
        except Exception as e:
            logger.error(f"Error running {scraper_id}: {e}")
            return False

    def run_scheduled_scrape(self, force: bool = False, dry_run: bool = False,
                             ecnl_only: bool = False, ga_only: bool = False,
                             aspire_only: bool = False, missing_only: bool = False,
                             visible: bool = False) -> Dict:
        """Main entry point for scheduled scraping"""
        logger.info("=" * 60)
        logger.info("SMART SCHEDULED SCRAPER")
        logger.info(f"Date: {self.today.strftime('%Y-%m-%d')} ({self.day_name})")
        logger.info(f"Options: force={force}, dry_run={dry_run}")
        logger.info("=" * 60)

        # Get game status
        games_status = self.get_games_needing_scrape()

        # Report current status
        logger.info("\nGames needing scrape:")
        for scraper_id, status in games_status.items():
            logger.info(f"  {status['name']}: {status['total_missing']} missing, {status['today_games']} today")

        # Determine what to run
        if ecnl_only:
            scrapers_to_run = {'ECNL': True}
        elif ga_only:
            scrapers_to_run = {'GA': True}
        elif aspire_only:
            scrapers_to_run = {'ASPIRE': True}
        else:
            scrapers_to_run = self.should_run_today(force=force)

        # Filter by missing_only
        if missing_only:
            scrapers_to_run = {
                sid: run for sid, run in scrapers_to_run.items()
                if games_status.get(sid, {}).get('total_missing', 0) > 0
            }

        logger.info(f"\nScrapers to run on {self.day_name}:")
        for scraper_id, should_run in scrapers_to_run.items():
            status = games_status.get(scraper_id, {})
            reason = ""
            if status.get('total_missing', 0) > 0:
                reason = f"({status['total_missing']} games missing results)"
            elif self.day_of_week in [5, 6]:
                reason = "(weekend game day)"
            elif self.day_of_week == 0:
                reason = "(Monday follow-up)"

            logger.info(f"  {SCRAPERS[scraper_id]['name']}: {'YES' if should_run else 'SKIP'} {reason}")

        # Run scrapers
        results = {'ran': [], 'skipped': [], 'failed': []}
        background = not visible  # Run in background unless --visible flag

        for scraper_id, should_run in scrapers_to_run.items():
            if should_run:
                if self.run_scraper(scraper_id, dry_run=dry_run, background=background):
                    results['ran'].append(scraper_id)
                else:
                    results['failed'].append(scraper_id)
            else:
                results['skipped'].append(scraper_id)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info(f"  Ran: {', '.join(results['ran']) or 'None'}")
        logger.info(f"  Skipped: {', '.join(results['skipped']) or 'None'}")
        if results['failed']:
            logger.info(f"  Failed: {', '.join(results['failed'])}")
        logger.info("=" * 60)

        return results


def main():
    parser = argparse.ArgumentParser(
        description='Smart scheduled scraper - runs based on game day patterns'
    )
    parser.add_argument('--force', action='store_true',
                       help='Force run all scrapers regardless of day')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would run without actually running')
    parser.add_argument('--missing-only', action='store_true',
                       help='Only run scrapers for leagues with missing results')
    parser.add_argument('--ecnl-only', action='store_true',
                       help='Only run ECNL scraper')
    parser.add_argument('--ga-only', action='store_true',
                       help='Only run GA scraper')
    parser.add_argument('--aspire-only', action='store_true',
                       help='Only run ASPIRE scraper')
    parser.add_argument('--visible', action='store_true',
                       help='Show browser windows (default: run in background)')
    parser.add_argument('--db', type=str, default=str(DB_PATH),
                       help='Path to database file')

    args = parser.parse_args()

    try:
        scheduler = SmartScheduler(Path(args.db))
        scheduler.run_scheduled_scrape(
            force=args.force,
            dry_run=args.dry_run,
            missing_only=args.missing_only,
            ecnl_only=args.ecnl_only,
            ga_only=args.ga_only,
            aspire_only=args.aspire_only,
            visible=args.visible,
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
