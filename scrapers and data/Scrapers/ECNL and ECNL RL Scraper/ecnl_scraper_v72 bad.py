#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ECNL COMPREHENSIVE SCRAPER v72 - ADMIN UI COMPATIBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V72 CHANGES:
  ✅ CRITICAL FIX: Fixed JavaScript regex escaping (double backslash needed)
  ✅ Restored EXACT working extraction code from v63
  ✅ Added scroll_to_load_all() function from v63
  ✅ Browser now VISIBLE by default (use --headless to hide)
  ✅ TGS website uses text-based layout, not HTML tables

V68 CHANGES:
  ✅ FIXED 're' module scoping error in scrape_team_details
  ✅ FIXED database path for folder structure (parent.parent)
  ✅ Admin UI: Added --league option (ECNL, ECNL RL, or both)
  ✅ Admin UI: Added --reset-status to reset teams to pending before scraping

ADMIN UI ARGUMENTS:
  --gender girls|boys|both    Filter by gender
  --ages 13,12,11,10,09,08    Comma-separated age groups
  --days 90                   Only games from last N days
  --players                   Include player/roster scraping
  --verbose                   Show detailed output
  --no-confirm                Skip "Press Enter" prompts
  --league ECNL|ECNL RL|both  Specific league (default: both)
  --scrape                    Scrape pending teams only
  --scrape-all                Scrape all teams
  --reset-status              Reset teams to pending before scraping
  --headless                  Hide browser window (default: visible)

USAGE:
  # Visible browser (default):
  python ecnl_scraper_v72.py --scrape --limit 5
  
  # Hidden browser:
  python ecnl_scraper_v72.py --scrape --headless --no-confirm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import os
import re
import sys
import csv
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()

def find_database_path():
    search_paths = [
        SCRIPT_DIR.parent.parent / "seedlinedata.db",
        SCRIPT_DIR.parent / "seedlinedata.db",
        SCRIPT_DIR / "seedlinedata.db",
        Path.cwd() / "seedlinedata.db",
        SCRIPT_DIR.parent / "scrapers and data" / "seedlinedata.db",
    ]
    for path in search_paths:
        if path.exists():
            return str(path.resolve())
    return str(SCRIPT_DIR.parent / "seedlinedata.db")

DATABASE_PATH = find_database_path()
OUTPUT_DIR = SCRIPT_DIR

ECNL_EVENT_ID = "3925"
ECNL_RL_EVENT_ID = "3932"

def normalize_date_to_iso(date_str: str) -> Optional[str]:
    """Convert various date formats to ISO format (YYYY-MM-DD)"""
    if not date_str:
        return None
    date_str = date_str.strip()
    
    # Try "Month Day, Year" format (e.g., "Sep 6, 2025")
    match = re.match(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', date_str)
    if match:
        month_str, day, year = match.groups()
        months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                  'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        month = months.get(month_str.lower()[:3])
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    
    # Try MM/DD/YYYY format
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', date_str)
    if match:
        month, day, year = match.groups()
        if len(year) == 2:
            year = f"20{year}"
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    return None

def standardize_age_group(age_str: str, gender: str = "Girls") -> str:
    """Standardize age group format to 'G08' or 'B08' format"""
    if not age_str:
        return ""
    
    age_str = str(age_str).strip().upper()
    prefix = "G" if gender.lower().startswith('g') else "B"
    
    # Extract just the number part
    numbers = re.findall(r'\d+', age_str)
    if numbers:
        num = numbers[0]
        # Handle 4-digit year format (2008 -> 08)
        if len(num) == 4:
            num = num[2:]
        # Ensure 2 digits
        num = num.zfill(2)[-2:]
        return f"{prefix}{num}"
    
    return age_str

def normalize_team_for_id(team: str) -> str:
    """Normalize team name for game ID generation"""
    if not team:
        return "unknown"
    normalized = team.lower().strip()
    normalized = re.sub(r'\s+(SC|FC|Academy|Soccer|Club)\s*$', '', normalized, flags=re.I)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    normalized = re.sub(r'\s+\d{2}G\s*$', '', normalized)
    normalized = re.sub(r'\s+G\d{2}\s*$', '', normalized)
    normalized = re.sub(r'\s+U\d{2}\s*$', '', normalized, flags=re.I)
    return normalized[:30]

def make_game_id(date: str, team1: str, team2: str, league: str, age: str = "") -> str:
    """Generate unique game ID"""
    date_iso = normalize_date_to_iso(date) or date
    t1 = normalize_team_for_id(team1)
    t2 = normalize_team_for_id(team2)
    teams_sorted = "_".join(sorted([t1, t2]))
    league_short = league.replace(" ", "").lower()[:6]
    age_clean = re.sub(r'[^a-zA-Z0-9]', '', age).lower()
    return f"{date_iso}_{teams_sorted}_{league_short}_{age_clean}"

def parse_age_filter(ages_str: str) -> List[str]:
    """Parse age filter string into list of age groups"""
    if not ages_str:
        return []
    ages = []
    for part in ages_str.split(','):
        part = part.strip()
        if part:
            if part.isdigit():
                ages.append(f"G{part.zfill(2)}")
                ages.append(f"B{part.zfill(2)}")
            else:
                ages.append(part.upper())
    return ages

def get_teams_from_db(db_path: str, league: str = None, age: str = None, 
                      gender: str = None, status: str = 'pending', limit: int = None) -> List[Dict]:
    """Get teams from discovered_urls table"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = "SELECT * FROM discovered_urls WHERE 1=1"
    params = []
    
    if league and league.lower() != 'both':
        if league.lower() == 'ecnl-rl':
            league = 'ECNL RL'
        elif league.lower() == 'ecnl':
            league = 'ECNL'
        query += " AND league = ?"
        params.append(league)
    elif league and league.lower() == 'both':
        query += " AND league IN ('ECNL', 'ECNL RL')"
    
    if age:
        age_list = parse_age_filter(age)
        if age_list:
            placeholders = ','.join(['?' for _ in age_list])
            query += f" AND age_group IN ({placeholders})"
            params.extend(age_list)
    
    if gender:
        if gender.lower() == 'girls':
            query += " AND (gender = 'Girls' OR age_group LIKE 'G%')"
        elif gender.lower() == 'boys':
            query += " AND (gender = 'Boys' OR age_group LIKE 'B%')"
    
    if status:
        query += " AND (scrape_status = ? OR scrape_status IS NULL)"
        params.append(status)
    
    query += " ORDER BY league, age_group, team_name"
    
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_status(db_path: str, url: str, status: str):
    """Update scrape status for a team"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE discovered_urls SET scrape_status = ?, last_scraped = datetime('now') WHERE url = ?",
               (status, url))
    conn.commit()
    conn.close()

def reset_scrape_status(db_path: str, league: str = None, gender: str = None, age_list: List[str] = None) -> int:
    """Reset scrape_status to 'pending' for teams matching filters"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    query = "UPDATE discovered_urls SET scrape_status = 'pending' WHERE 1=1"
    params = []
    
    if league and league.lower() != 'both':
        if league.lower() == 'ecnl-rl':
            league = 'ECNL RL'
        elif league.lower() == 'ecnl':
            league = 'ECNL'
        query += " AND league = ?"
        params.append(league)
    elif league and league.lower() == 'both':
        query += " AND league IN ('ECNL', 'ECNL RL')"
    
    if gender:
        if gender.lower() == 'girls':
            query += " AND (gender = 'Girls' OR age_group LIKE 'G%')"
        elif gender.lower() == 'boys':
            query += " AND (gender = 'Boys' OR age_group LIKE 'B%')"
    
    if age_list:
        placeholders = ','.join(['?' for _ in age_list])
        query += f" AND age_group IN ({placeholders})"
        params.extend(age_list)
    
    cur.execute(query, params)
    count = cur.rowcount
    conn.commit()
    conn.close()
    
    return count

def save_games(db_path: str, games: List[Dict], days_filter: int = None) -> Tuple[int, int]:
    """Save games to database"""
    if not games:
        return 0, 0
    
    if days_filter:
        cutoff_date = (datetime.now() - timedelta(days=days_filter)).strftime('%Y-%m-%d')
        games = [g for g in games if g.get('game_date_iso', '') >= cutoff_date]
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    new_count, updated = 0, 0
    
    for g in games:
        cur.execute("SELECT rowid, home_score, away_score FROM games WHERE game_id = ?", (g['game_id'],))
        ex = cur.fetchone()
        if ex:
            if (g.get('home_score') is not None) and (ex[1] is None or ex[2] is None):
                cur.execute("UPDATE games SET home_score=COALESCE(?,home_score), away_score=COALESCE(?,away_score) WHERE rowid=?",
                           (g.get('home_score'), g.get('away_score'), ex[0]))
                updated += 1
        else:
            cur.execute("""INSERT INTO games (game_id, game_date, game_date_iso, game_time, home_team, away_team, 
                          home_score, away_score, league, age_group, conference, location, game_status, source_url, scraped_at, gender)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                       (g['game_id'], g.get('game_date'), g.get('game_date_iso'), g.get('game_time'), g.get('home_team'),
                        g.get('away_team'), g.get('home_score'), g.get('away_score'), g.get('league'), g.get('age_group'),
                        g.get('conference'), g.get('location'), 'completed' if g.get('home_score') is not None else 'scheduled',
                        g.get('source_url'), g.get('gender', 'Girls')))
            new_count += 1
    conn.commit()
    conn.close()
    return new_count, updated

def save_team(db_path: str, team: Dict) -> bool:
    """Save team to database"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT rowid FROM teams WHERE team_url = ?", (team.get('team_url'),))
    existing = cur.fetchone()
    
    if existing:
        if team.get('state') or team.get('city'):
            cur.execute("""UPDATE teams SET 
                          state = COALESCE(?, state),
                          city = COALESCE(?, city),
                          street_address = COALESCE(?, street_address),
                          zip_code = COALESCE(?, zip_code),
                          official_website = COALESCE(?, official_website),
                          last_updated = datetime('now')
                          WHERE team_url = ?""",
                       (team.get('state'), team.get('city'), team.get('street_address'),
                        team.get('zip_code'), team.get('official_website'), team.get('team_url')))
            conn.commit()
            conn.close()
            return False
    else:
        cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference,
                      state, city, street_address, zip_code, official_website, event_id, scraped_at, last_updated)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
                   (team.get('team_url'), team.get('club_name'), team.get('team_name'), team.get('age_group'),
                    team.get('gender'), team.get('league'), team.get('conference'), team.get('state'),
                    team.get('city'), team.get('street_address'), team.get('zip_code'),
                    team.get('official_website'), team.get('event_id')))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def save_players(db_path: str, players: List[Dict], team_url: str, team_name: str) -> int:
    """Save players to database"""
    if not players:
        return 0
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    saved = 0
    for p in players:
        try:
            cur.execute("""INSERT OR REPLACE INTO players 
                          (team_url, team_name, player_name, first_name, last_name, jersey_number, position, graduation_year, scraped_at)
                          VALUES (?,?,?,?,?,?,?,?,datetime('now'))""",
                       (team_url, team_name, p.get('name'), p.get('first_name'), p.get('last_name'),
                        p.get('number'), p.get('position'), p.get('grad_year')))
            saved += 1
        except:
            pass
    conn.commit()
    conn.close()
    return saved

def export_csv(games: List[Dict], output_dir: Path, prefix: str) -> str:
    """Export games to CSV file"""
    if not games:
        return ""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fp = output_dir / f"{prefix}_games_{ts}.csv"
    fields = ['game_id','game_date','game_date_iso','game_time','home_team','away_team','home_score','away_score',
              'age_group','conference','location','game_status','source_url','league','gender']
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(games)
    return str(fp)


class ECNLScraper:
    def __init__(self, db_path: str, headless: bool = False, debug: bool = False, 
                 include_players: bool = False, days_filter: int = None):
        self.db_path = db_path
        self.headless = headless  # Default to False (visible browser)
        self.debug = debug
        self.include_players = include_players
        self.days_filter = days_filter
        self.all_games = []
        self.errors = 0

    async def scroll_to_load_all(self, page, max_scrolls=30, wait_time=0.8):
        """Scroll page to load all lazy-loaded content (from v63)"""
        try:
            initial_height = await page.evaluate("document.body.scrollHeight")
            stable_count = 0
            
            for _ in range(max_scrolls):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(wait_time)
                
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == initial_height:
                    stable_count += 1
                    if stable_count >= 2:
                        break
                else:
                    stable_count = 0
                initial_height = current_height
            
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ Scroll error: {e}")

    async def scrape_team_details(self, page, team: Dict) -> Dict:
        """Scrape team location details from team page"""
        details = {}
        
        try:
            # Extract location info using JavaScript
            location_info = await page.evaluate("""
                () => {
                    const info = {};
                    const bodyText = document.body.innerText;
                    
                    // Look for address pattern
                    const addressMatch = bodyText.match(/\\d+\\s+[A-Za-z].*?(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Blvd|Way|Court|Ct)/i);
                    if (addressMatch) {
                        info.address = addressMatch[0];
                    }
                    
                    // Look for City, State ZIP
                    const cityStateMatch = bodyText.match(/([A-Za-z\\s]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
                    if (cityStateMatch) {
                        info.city = cityStateMatch[1].trim();
                        info.state = cityStateMatch[2];
                        info.zip = cityStateMatch[3];
                    }
                    
                    // Look for official website link
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        const text = link.textContent.toLowerCase();
                        if (text.includes('official website')) {
                            const href = link.href;
                            if (href && !href.includes('totalglobalsports')) {
                                info.website = href;
                                break;
                            }
                        }
                    }
                    
                    return info;
                }
            """)
            
            if location_info:
                details['city'] = location_info.get('city')
                details['state'] = location_info.get('state')
                details['zip_code'] = location_info.get('zip')
                details['street_address'] = location_info.get('address')
                details['official_website'] = location_info.get('website')
                
        except Exception as e:
            if self.debug:
                print(f"    Details error: {e}")
        
        return details

    async def scrape_team_schedule(self, page, team: Dict) -> List[Dict]:
        """
        Scrape games from team page using text extraction.
        V72: Uses EXACT working code from v63 with proper regex escaping.
        """
        games = []
        url = team.get('url')
        if not url:
            return games
        
        team_name = team.get('team_name', 'Unknown')
        team_league = team.get('league', 'ECNL')
        team_age = team.get('age_group', '')
        team_gender = team.get('gender', 'Girls')
        team_conference = team.get('conference', '')
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Scroll to load all content
            await self.scroll_to_load_all(page)
            
            # V72: Use EXACT JavaScript from v63 with proper double-escaped regex
            # Note: In Python strings, \\ becomes \ which JavaScript sees as regex escape
            games_data = await page.evaluate("""
                () => {
                    const games = [];
                    const seen = new Set();
                    
                    // Get page text
                    const bodyText = document.body.innerText;
                    
                    // Find the Team Information / schedule section
                    const teamInfoIdx = bodyText.indexOf('Team Information');
                    const clubPlayersIdx = bodyText.indexOf('Club Players');
                    
                    let scheduleSection = bodyText;
                    if (teamInfoIdx > -1 && clubPlayersIdx > -1) {
                        scheduleSection = bodyText.substring(teamInfoIdx, clubPlayersIdx);
                    } else if (teamInfoIdx > -1) {
                        scheduleSection = bodyText.substring(teamInfoIdx);
                    }
                    
                    // Date pattern: "Sep 6, 2025" or "Sep 20, 2025"
                    const dateRegex = /(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+(\\d{1,2}),?\\s+(\\d{4})/gi;
                    const dateMatches = [...scheduleSection.matchAll(dateRegex)];
                    
                    dateMatches.forEach((match, idx) => {
                        const date = match[1] + ' ' + match[2] + ', ' + match[3];
                        const matchIdx = match.index;
                        
                        // Get context: 150 chars before and up to next date or 300 chars after
                        const startIdx = Math.max(0, matchIdx - 150);
                        
                        let endIdx;
                        if (idx + 1 < dateMatches.length) {
                            endIdx = dateMatches[idx + 1].index;
                        } else {
                            endIdx = Math.min(scheduleSection.length, matchIdx + 300);
                        }
                        
                        const beforeContext = scheduleSection.substring(startIdx, matchIdx);
                        const afterContext = scheduleSection.substring(matchIdx, endIdx);
                        
                        // Skip if this is from Next Game Preview section
                        if (beforeContext.includes('Next Game Preview') || beforeContext.includes('Parking Fee')) {
                            return;
                        }
                        
                        const game = {
                            date: date,
                            home_away: null,
                            opponent: null,
                            score: null,
                            home_score: null,
                            away_score: null,
                            time: null
                        };
                        
                        // Look for H or A indicator before the date
                        const haMatch = beforeContext.match(/\\b([HA])\\s*$/);
                        if (haMatch) {
                            game.home_away = haMatch[1] === 'H' ? 'Home' : 'Away';
                        }
                        
                        // Look for time pattern after date
                        const timeMatch = afterContext.match(/(\\d{1,2}:\\d{2}\\s*(?:AM|PM))/i);
                        if (timeMatch) {
                            game.time = timeMatch[1];
                        }
                        
                        // OPPONENT EXTRACTION (from v63)
                        let opponent = null;
                        
                        // Pattern 1: "Team Name ECNL RL G08/07"
                        let opponentMatch = afterContext.match(/([A-Za-z][A-Za-z0-9\\s()\\-'&.]+?)\\s+ECNL\\s+RL\\s+[GB]\\d{2,4}(?:\\/\\d{2,4})?/i);
                        if (opponentMatch) {
                            opponent = opponentMatch[1].trim();
                        }
                        
                        // Pattern 2: "Team Name ECNL G08" (no RL)
                        if (!opponent) {
                            opponentMatch = afterContext.match(/([A-Za-z][A-Za-z0-9\\s()\\-'&.]+?)\\s+ECNL\\s+[GB]\\d{2,4}(?:\\/\\d{2,4})?/i);
                            if (opponentMatch) {
                                opponent = opponentMatch[1].trim();
                            }
                        }
                        
                        // Pattern 3: After "field X"
                        if (!opponent) {
                            opponentMatch = afterContext.match(/(?:field|Field)\\s*\\d+[\\s\\n]+([A-Za-z][A-Za-z0-9\\s()\\-'&.]+?)\\s+ECNL/i);
                            if (opponentMatch) {
                                opponent = opponentMatch[1].trim();
                            }
                        }
                        
                        // Pattern 4: Fallback
                        if (!opponent) {
                            opponentMatch = afterContext.match(/([A-Za-z][A-Za-z0-9\\s()\\-'&.]{2,40})\\s+ECNL/i);
                            if (opponentMatch) {
                                opponent = opponentMatch[1].trim();
                            }
                        }
                        
                        // Clean up opponent name
                        if (opponent) {
                            opponent = opponent.replace(/\\s+/g, ' ').trim();
                            opponent = opponent.replace(/^\\d{1,2}:\\d{2}\\s*(AM|PM)?\\s*/i, '').trim();
                            opponent = opponent.replace(/^(field|Field)\\s*\\d+\\s*/i, '').trim();
                            opponent = opponent.replace(/^#\\d+\\s*/i, '').trim();
                            
                            if (opponent.length > 2 && opponent.length < 60) {
                                game.opponent = opponent;
                            }
                        }
                        
                        // SCORE EXTRACTION (from v63)
                        let scoreFound = false;
                        let scoreMatch;
                        
                        // Pattern 1: W/L/D followed by score
                        scoreMatch = afterContext.match(/\\b([WLD])\\b[\\s\\n]+(\\d+)\\s*[-\\u2013]\\s*(\\d+)/i);
                        if (scoreMatch) {
                            game.result = scoreMatch[1].toUpperCase();
                            game.home_score = parseInt(scoreMatch[2]);
                            game.away_score = parseInt(scoreMatch[3]);
                            game.score = scoreMatch[2] + '-' + scoreMatch[3];
                            scoreFound = true;
                        }
                        
                        // Pattern 2: Score near "View Box Score"
                        if (!scoreFound) {
                            const vbsIdx = afterContext.indexOf('View Box Score');
                            if (vbsIdx > 0) {
                                const beforeVBS = afterContext.substring(Math.max(0, vbsIdx - 50), vbsIdx);
                                scoreMatch = beforeVBS.match(/(\\d+)\\s*[-\\u2013]\\s*(\\d+)/);
                                if (scoreMatch) {
                                    game.home_score = parseInt(scoreMatch[1]);
                                    game.away_score = parseInt(scoreMatch[2]);
                                    game.score = scoreMatch[1] + '-' + scoreMatch[2];
                                    scoreFound = true;
                                    const wldMatch = beforeVBS.match(/\\b([WLD])\\b/i);
                                    if (wldMatch) {
                                        game.result = wldMatch[1].toUpperCase();
                                    }
                                }
                            }
                        }
                        
                        // Pattern 3: Standalone W/L/D + newline + score
                        if (!scoreFound) {
                            scoreMatch = afterContext.match(/\\n([WLD])\\n(\\d+)\\s*[-\\u2013]\\s*(\\d+)/i);
                            if (scoreMatch) {
                                game.result = scoreMatch[1].toUpperCase();
                                game.home_score = parseInt(scoreMatch[2]);
                                game.away_score = parseInt(scoreMatch[3]);
                                game.score = scoreMatch[2] + '-' + scoreMatch[3];
                                scoreFound = true;
                            }
                        }
                        
                        // Pattern 4: "D 0 - 0" format
                        if (!scoreFound) {
                            scoreMatch = afterContext.match(/([WLD])\\s*(\\d+)\\s*[-\\u2013]\\s*(\\d+)/i);
                            if (scoreMatch) {
                                game.result = scoreMatch[1].toUpperCase();
                                game.home_score = parseInt(scoreMatch[2]);
                                game.away_score = parseInt(scoreMatch[3]);
                                game.score = scoreMatch[2] + '-' + scoreMatch[3];
                                scoreFound = true;
                            }
                        }
                        
                        // Only add if we have meaningful data
                        const key = date + '-' + (game.opponent || '') + '-' + (game.score || '');
                        if (!seen.has(key) && (game.opponent || game.score)) {
                            seen.add(key);
                            games.push(game);
                        }
                    });
                    
                    return games;
                }
            """)
            
            # Convert to expected format
            age_group = standardize_age_group(team_age, team_gender)
            
            for g in games_data:
                opponent = g.get('opponent', '')
                home_away = g.get('home_away', 'Unknown')
                date_str = g.get('date', '')
                
                # Determine home/away teams
                if home_away == 'Home':
                    home_team = team_name
                    away_team = opponent if opponent else 'Unknown'
                elif home_away == 'Away':
                    home_team = opponent if opponent else 'Unknown'
                    away_team = team_name
                else:
                    home_team = team_name
                    away_team = opponent if opponent else 'Unknown'
                
                game = {
                    'game_id': make_game_id(date_str, home_team, away_team, team_league, age_group),
                    'game_date': date_str,
                    'game_date_iso': normalize_date_to_iso(date_str),
                    'game_time': g.get('time'),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': g.get('home_score'),
                    'away_score': g.get('away_score'),
                    'league': team_league,
                    'age_group': age_group,
                    'conference': team_conference,
                    'location': None,
                    'game_status': 'completed' if g.get('home_score') is not None else 'scheduled',
                    'source_url': url,
                    'gender': team_gender
                }
                games.append(game)
            
            # Print summary
            if games:
                with_opponent = sum(1 for g in games if g.get('away_team') != 'Unknown')
                with_score = sum(1 for g in games if g.get('home_score') is not None)
                print(f"✓ {len(games)} games ({with_opponent} with opponent, {with_score} with scores)")
            
        except Exception as e:
            print(f"Page error: {e}")
            self.errors += 1
        
        return games

    async def scrape_team_roster(self, page, team: Dict) -> List[Dict]:
        """Scrape player roster from team page"""
        players = []
        
        try:
            roster_data = await page.evaluate("""
                () => {
                    const players = [];
                    const seen = new Set();
                    const bodyText = document.body.innerText;
                    
                    // Find players section
                    const playersIdx = bodyText.indexOf('Club Players');
                    if (playersIdx === -1) return players;
                    
                    const playerSection = bodyText.substring(playersIdx);
                    const chunks = playerSection.split('View Profile');
                    
                    chunks.forEach(chunk => {
                        const nameMatches = chunk.matchAll(/([A-Z][a-z]+),\\s*([A-Z][a-z]+)/g);
                        
                        for (const nameMatch of nameMatches) {
                            const lastName = nameMatch[1];
                            const firstName = nameMatch[2];
                            const fullName = firstName + ' ' + lastName;
                            
                            if (seen.has(fullName)) continue;
                            seen.add(fullName);
                            
                            const afterName = chunk.substring(chunk.indexOf(nameMatch[0]) + nameMatch[0].length);
                            const numberMatch = afterName.match(/#(\\d{1,2})\\b/);
                            const yearMatch = afterName.match(/\\b(202[5-9]|203[0-2])\\b/);
                            
                            let position = null;
                            const posMatch = afterName.match(/\\b(Goal\\s*Keeper|Goalkeeper|GK|Defender|Midfielder|Forward|Fwd|Mid|Def)\\b/i);
                            if (posMatch) position = posMatch[1];
                            
                            if (fullName && (position || yearMatch)) {
                                players.push({
                                    name: fullName,
                                    first_name: firstName,
                                    last_name: lastName,
                                    number: numberMatch ? numberMatch[1] : null,
                                    position: position,
                                    grad_year: yearMatch ? yearMatch[1] : null
                                });
                            }
                        }
                    });
                    
                    return players;
                }
            """)
            
            players = roster_data
            
        except Exception as e:
            if self.debug:
                print(f"    Roster error: {e}")
        
        return players

    async def scrape_teams(self, teams: List[Dict]) -> Tuple[int, int]:
        """Scrape games for a list of teams"""
        total_new, total_upd = 0, 0
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            print(f"\n📥 Scraping {len(teams)} teams...")
            print(f"🖥️  Browser: {'Hidden' if self.headless else 'Visible'}")
            
            for i, team in enumerate(teams, 1):
                team_name = team.get('team_name', 'Unknown')
                league = team.get('league', 'ECNL')
                age = team.get('age_group', '')
                
                print(f"[{i}/{len(teams)}] {team_name} ({league} {age}) ", end="", flush=True)
                
                try:
                    games = await self.scrape_team_schedule(page, team)
                    
                    if games:
                        n, u = save_games(self.db_path, games, self.days_filter)
                        total_new += n
                        total_upd += u
                        self.all_games.extend(games)
                        update_status(self.db_path, team.get('url'), 'completed')
                        
                        # Save team details
                        team_details = await self.scrape_team_details(page, team)
                        team_data = {
                            'team_url': team.get('url'),
                            'club_name': team.get('club_name'),
                            'team_name': team_name,
                            'age_group': age,
                            'gender': team.get('gender', 'Girls'),
                            'league': league,
                            'conference': team.get('conference', ''),
                            'event_id': team.get('event_id'),
                            'state': team_details.get('state'),
                            'city': team_details.get('city'),
                            'street_address': team_details.get('street_address'),
                            'zip_code': team_details.get('zip_code'),
                            'official_website': team_details.get('official_website'),
                        }
                        save_team(self.db_path, team_data)
                        
                        # Scrape players if requested
                        if self.include_players:
                            players = await self.scrape_team_roster(page, team)
                            if players:
                                saved = save_players(self.db_path, players, team.get('url', ''), team_name)
                                if self.debug:
                                    print(f"    💼 {saved} players")
                    else:
                        print("- No games")
                        update_status(self.db_path, team.get('url'), 'no_games')
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"❌ {e}")
                    self.errors += 1
                    update_status(self.db_path, team.get('url'), 'error')
            
            await browser.close()
        
        return total_new, total_upd

    def show_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        print("\n" + "="*60)
        print("📊 ECNL DATABASE STATISTICS")
        print("="*60)
        
        cur.execute("SELECT COUNT(*) FROM games WHERE league IN ('ECNL', 'ECNL RL')")
        total_games = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM games WHERE league IN ('ECNL', 'ECNL RL') AND home_score IS NOT NULL")
        completed = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT url) FROM discovered_urls WHERE league IN ('ECNL', 'ECNL RL')")
        total_teams = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM discovered_urls WHERE league IN ('ECNL', 'ECNL RL') AND scrape_status = 'completed'")
        scraped_teams = cur.fetchone()[0]
        
        print(f"Total ECNL Games: {total_games}")
        print(f"Completed Games: {completed}")
        print(f"Teams Discovered: {total_teams}")
        print(f"Teams Scraped: {scraped_teams}")
        print("="*60)
        
        conn.close()

    def cleanup_data(self):
        """Clean up corrupted data"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM games WHERE home_team IS NULL OR away_team IS NULL")
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        print(f"🧹 Cleaned up {deleted} invalid games")


async def main_async():
    parser = argparse.ArgumentParser(description='ECNL Scraper v72')
    parser.add_argument('--db', help='Database path')
    parser.add_argument('--discover', action='store_true', help='Discover team URLs')
    parser.add_argument('--scrape', action='store_true', help='Scrape pending teams')
    parser.add_argument('--scrape-all', action='store_true', help='Scrape all teams')
    parser.add_argument('--league', choices=['ECNL', 'ECNL RL', 'ecnl', 'ecnl-rl', 'both'], 
                       help='Specific league (default: both)')
    parser.add_argument('--age', help='Age group filter')
    parser.add_argument('--limit', type=int, help='Limit teams')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--cleanup', action='store_true', help='Clean corrupted data')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--headless', action='store_true', help='Hide browser (default: visible)')
    parser.add_argument('--gender', choices=['girls', 'boys', 'both'], default='both')
    parser.add_argument('--ages', help='Comma-separated age groups')
    parser.add_argument('--days', type=int, help='Only games from last N days')
    parser.add_argument('--players', action='store_true', help='Include player scraping')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--no-confirm', action='store_true', help='Skip prompts')
    parser.add_argument('--reset-status', action='store_true', help='Reset teams to pending')
    
    args = parser.parse_args()
    
    db_path = args.db or DATABASE_PATH
    
    print("=" * 60)
    print("🏃 ECNL COMPREHENSIVE SCRAPER v72")
    print("=" * 60)
    print(f"📂 Database: {db_path}")
    
    # Determine league filter
    league_filter = args.league
    if league_filter:
        if league_filter.lower() == 'ecnl-rl':
            league_filter = 'ECNL RL'
        elif league_filter.lower() == 'ecnl':
            league_filter = 'ECNL'
        elif league_filter.lower() == 'both':
            league_filter = 'both'
    else:
        league_filter = 'both'
    
    league_display = 'ECNL + ECNL RL (both)' if league_filter == 'both' else league_filter
    print(f"🏆 League: {league_display}")
    print(f"👤 Gender: {args.gender}")
    print(f"📅 Age groups: {args.ages or 'all'}")
    print(f"👥 Including players: {'Yes' if args.players else 'No'}")
    print(f"🖥️  Browser: {'Hidden' if args.headless else 'Visible'}")
    
    # Create scraper - V72: Default to visible browser
    scraper = ECNLScraper(
        db_path, 
        headless=args.headless,  # False by default now
        debug=args.debug or args.verbose,
        include_players=args.players,
        days_filter=args.days
    )
    
    if args.stats:
        scraper.show_stats()
        return
    
    if args.cleanup:
        scraper.cleanup_data()
        return
    
    # Parse ages
    age_list = []
    if args.ages:
        age_list = parse_age_filter(args.ages)
    
    # Handle reset-status
    if args.reset_status:
        reset_count = reset_scrape_status(
            db_path, 
            league=league_filter,
            gender=args.gender if args.gender != 'both' else None,
            age_list=age_list if age_list else None
        )
        print(f"🔄 Reset {reset_count} teams to pending status")
    
    # Scrape teams
    if args.scrape or args.scrape_all or args.reset_status:
        status = None if args.scrape_all else 'pending'
        mode = "All teams" if args.scrape_all else "Pending teams only"
        print(f"🔄 Mode: {mode}")
        
        teams = get_teams_from_db(
            db_path, 
            league=league_filter,
            age=args.ages,
            gender=args.gender if args.gender != 'both' else None,
            status=status,
            limit=args.limit
        )
        
        print(f"📋 {len(teams)} teams to scrape")
        
        if teams:
            if not args.no_confirm:
                input("\nPress Enter to start scraping...")
            
            new_cnt, upd_cnt = await scraper.scrape_teams(teams)
            
            print(f"\n✅ Complete: {new_cnt} new games, {upd_cnt} updated")
            
            if scraper.all_games:
                csv_file = export_csv(scraper.all_games, OUTPUT_DIR, 'ECNL')
                if csv_file:
                    print(f"📄 CSV exported: {csv_file}")
            
            scraper.show_stats()
    else:
        print("\nNo action specified. Use --scrape, --stats, or --help")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
