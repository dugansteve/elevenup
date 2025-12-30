#!/usr/bin/env python3
"""
Scrape Recent GotSport Tournaments - Version 2

⚠️⚠️⚠️ CRITICAL: AGE GROUP FORMAT USES BIRTH YEAR ⚠️⚠️⚠️
=====================================================
ALL THESE PATTERNS ARE EQUIVALENT: 12G = G12 = 2012 = 2012G = birth year 2012

The number in team names and age groups is ALWAYS the birth year!
Current ages are NEVER in team names (except U-format).

| Pattern | Meaning          | Age Group | Players' Age in 2025 |
|---------|------------------|-----------|----------------------|
| G12     | Girls, Born 2012 | G12       | 13 years old         |
| B11     | Boys, Born 2011  | B11       | 14 years old         |
| 12G     | Born 2012, Girls | G12       | 13 years old         |
| 14F     | Born 2014, Female| G14       | 11 years old         |

Only U-format (U13, U11) means "under age X" where the number IS an age.

Formula: 12G → birth_year = 2012 → age_group = G12

THIS MISTAKE HAS BEEN MADE MULTIPLE TIMES - DO NOT REPEAT IT!
=====================================================

Improved age group extraction:
1. Extract from team names (birth years like 2013, short codes like 11B/G13)
2. Extract from division headers as validation/fallback
3. For teams without age: use earliest birth year from other teams in division
4. Validate: U13 in 2025 = max birth year 2012 (under 13 = born 2012 or later)

Usage:
    python scrape_recent_tournaments_final.py                  # Full run
    python scrape_recent_tournaments_final.py --filter-only    # Just filter, don't scrape
    python scrape_recent_tournaments_final.py --resume         # Resume from last position
"""

import json
import re
import time
import os
import sys
import sqlite3
import requests
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Configuration
TOURNAMENTS_FILE = "tournaments_data.json"
FILTERED_FILE = "tournaments_to_scrape.json"
PROGRESS_FILE = "scrape_recent_progress_v2.json"
DB_PATH = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"

START_DATE = datetime(2025, 5, 25)
END_DATE = datetime.now()
CURRENT_YEAR = 2025  # For birth year to age conversion

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Month name to number mapping
MONTHS = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}


def birth_year_to_age_group(birth_year, gender=None):
    """
    Convert birth year to age group using birth year suffix.

    CRITICAL: Age groups use BIRTH YEAR, not calculated age!
    - 2012 = G12 or B12 (NOT G13)
    - 2013 = G13 or B13 (NOT G12)

    The number in age_group IS the birth year suffix.
    G12 = Girls born in 2012
    B11 = Boys born in 2011
    """
    if not birth_year:
        return None
    try:
        birth_year = int(birth_year)
        year_suffix = birth_year % 100  # 2012 -> 12, 2013 -> 13
        if year_suffix < 5 or year_suffix > 20:  # Valid range 2005-2020
            return None
        if gender:
            return f"{gender.upper()}{year_suffix}"
        # Without gender, we can't determine G or B, so leave blank
        return None
    except:
        return None


def u_age_to_birth_year(u_age):
    """
    Convert U-age to birth year.
    U13 in 2025 = max birth year 2012 (kids turning 13 in 2025 were born in 2012)
    Actually U13 means "under 13" so players are 12 or younger = born 2013 or later
    But typically U13 division has mostly 12-year-olds = born 2013
    """
    try:
        age = int(u_age)
        return CURRENT_YEAR - age
    except:
        return None


def extract_age_from_team_name(team_name):
    """
    Extract age information from team name.
    Returns dict with birth_year, gender, and normalized age_group.

    PRIORITY ORDER (not all numbers are birth years - e.g., "1974 Newark"):
    1. Numbers attached to G/B/F/M (MOST RELIABLE) - G13, 12B, 14F, M11, G2014, 2014G
    2. Full 4-digit years in valid range (2005-2020) with "Boys"/"Girls" nearby
    3. Standalone full 4-digit years in valid range (2005-2020)
    4. U-format (U13, U-11) - these ARE ages, convert to birth year

    If ambiguous, use opponent's birth year as reference (handled in determine_best_age_group)
    """
    if not team_name:
        return {'birth_year': None, 'gender': None, 'age_group': None}

    result = {'birth_year': None, 'gender': None, 'age_group': None}

    # PRIORITY 1: Numbers attached to G/B/F/M (most reliable)
    # These patterns are ALWAYS birth years, never club founding years

    # Pattern 1a: Short code - letter then 2-digit year (G13, B12, F18, M14)
    short_match = re.search(r'\b([BGFM])(0[5-9]|1[0-9]|20)\b', team_name, re.IGNORECASE)
    if short_match:
        g = short_match.group(1).upper()
        result['gender'] = 'G' if g in ('G', 'F') else 'B'  # F=Female=G, M=Male=B
        result['birth_year'] = 2000 + int(short_match.group(2))

    # Pattern 1b: Short code - 2-digit year then letter (11B, 13G, 18F, 14M)
    if not result['birth_year']:
        short_match = re.search(r'\b(0[5-9]|1[0-9]|20)([BGFM])\b', team_name, re.IGNORECASE)
        if short_match:
            result['birth_year'] = 2000 + int(short_match.group(1))
            g = short_match.group(2).upper()
            result['gender'] = 'G' if g in ('G', 'F') else 'B'

    # Pattern 1c: Full year with gender attached (2014G, 2014B, G2014, B2015)
    if not result['birth_year']:
        birth_match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))([BGF])\b', team_name, re.IGNORECASE)
        if birth_match:
            result['birth_year'] = int(birth_match.group(1))
            g = birth_match.group(2).upper()
            result['gender'] = 'G' if g == 'F' else g

    if not result['birth_year']:
        birth_match = re.search(r'\b([BGF])(20(?:0[5-9]|1[0-9]|20))\b', team_name, re.IGNORECASE)
        if birth_match:
            g = birth_match.group(1).upper()
            result['gender'] = 'G' if g == 'F' else g
            result['birth_year'] = int(birth_match.group(2))

    # PRIORITY 2: Full 4-digit year with "Boys"/"Girls" nearby
    if not result['birth_year']:
        gender_match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))\s*(Boys?|Girls?|Male|Female)\b', team_name, re.IGNORECASE)
        if gender_match:
            result['birth_year'] = int(gender_match.group(1))
            g = gender_match.group(2).lower()
            result['gender'] = 'B' if g.startswith('boy') or g.startswith('male') else 'G'

    # PRIORITY 3: Standalone full 4-digit year (2005-2020) - less reliable
    # Could be club founding year, so only use if no other pattern found
    if not result['birth_year']:
        birth_match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))\b', team_name)
        if birth_match:
            result['birth_year'] = int(birth_match.group(1))

    # Pattern 3: U-format like "U11", "U-13", "U9" (these ARE ages, used for birth year calculation)
    u_match = re.search(r'\bU-?(\d{1,2})\b', team_name, re.IGNORECASE)
    if u_match:
        u_age = int(u_match.group(1))
        # U-age can help determine birth year if not already found
        if not result['birth_year']:
            result['birth_year'] = u_age_to_birth_year(u_age)

    # Normalize to age_group (always calculated from birth_year)
    if result['birth_year']:
        result['age_group'] = birth_year_to_age_group(result['birth_year'], result['gender'])

    return result


def extract_age_from_division_header(html):
    """
    Extract age from division header in HTML.
    Looks for patterns like:
    - <h5>Female U13 - 13G Stripes</h5>
    - <h4>Male U9 - u9 Boys SAND 2016'</h4>
    - "Female U11 - Under 11 Girls Green"

    Returns dict with division_age, division_gender, division_birth_year
    """
    result = {'division_age': None, 'division_gender': None, 'division_birth_year': None}

    # Look for h4/h5 headers with age info
    header_match = re.search(r'<h[45][^>]*>([^<]+)</h[45]>', html, re.IGNORECASE)
    if header_match:
        header_text = header_match.group(1)

        # Extract gender from "Female" or "Male"
        if 'female' in header_text.lower() or 'girl' in header_text.lower():
            result['division_gender'] = 'G'
        elif 'male' in header_text.lower() or 'boy' in header_text.lower():
            result['division_gender'] = 'B'

        # Extract U-age
        u_match = re.search(r'\bU-?(\d{1,2})\b', header_text, re.IGNORECASE)
        if u_match:
            result['division_age'] = int(u_match.group(1))
            result['division_birth_year'] = u_age_to_birth_year(result['division_age'])

        # Extract birth year from header
        birth_match = re.search(r'\b(20(?:0[5-9]|1[0-9]|20))\b', header_text)
        if birth_match:
            result['division_birth_year'] = int(birth_match.group(1))
            if not result['division_age']:
                age = CURRENT_YEAR - result['division_birth_year']
                result['division_age'] = age

    return result


def determine_best_age_group(home_age_info, away_age_info, division_info, all_team_ages):
    """
    Determine the best age group for a game.

    Priority:
    1. Team name birth year (most reliable) - patterns like 2013, G13, 11B are birth years
    2. Division header (U-age or birth year)
    3. Most common/earliest birth year from other teams in division

    For teams without age: use earliest birth year (oldest players) from division
    """
    # Try to get from home team first
    if home_age_info.get('age_group'):
        return home_age_info['age_group']

    # Try away team
    if away_age_info.get('age_group'):
        return away_age_info['age_group']

    # Fall back to division header
    if division_info.get('division_age'):
        gender = division_info.get('division_gender', '')
        if gender:
            return f"{gender}{division_info['division_age']}"
        return f"U{division_info['division_age']}"

    # Fall back to earliest birth year from other teams in division
    if all_team_ages:
        birth_years = [a['birth_year'] for a in all_team_ages if a.get('birth_year')]
        if birth_years:
            earliest = min(birth_years)  # Oldest players
            # Try to get gender from any team
            genders = [a['gender'] for a in all_team_ages if a.get('gender')]
            gender = genders[0] if genders else None
            return birth_year_to_age_group(earliest, gender)

    return ""


def parse_date_from_text(text, year_hint=2025):
    """Extract and parse date from text. Returns datetime or None."""
    if not text:
        return None

    # Pattern 1: "January 15-17, 2025" or "Jan 15-17, 2025"
    match = re.search(r'(\w+)\s+(\d{1,2})[-–]?\d*,?\s*(202[4-6])', text, re.IGNORECASE)
    if match:
        month_name, day, year = match.groups()
        month = MONTHS.get(month_name.lower()[:3])
        if month:
            try:
                return datetime(int(year), month, int(day))
            except:
                pass

    # Pattern 2: ISO format "2025-05-25"
    match = re.search(r'(202[4-6])-(\d{2})-(\d{2})', text)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except:
            pass

    # Pattern 3: US format "05/25/2025"
    match = re.search(r'(\d{1,2})/(\d{1,2})/(202[4-6])', text)
    if match:
        try:
            return datetime(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except:
            pass

    return None


def check_event_date(event_id):
    """Fetch event page and extract start date"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return None, None

        html = response.text

        # Skip invalid pages
        if len(html) < 5000:
            return None, None

        # Extract event name
        name = ""
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            name = title_match.group(1).replace(" | GotSport", "").strip()

        # Look for date in multiple places
        date_patterns = [
            r'(\w+)\s+(\d{1,2})[-–]\d*,?\s*(202[4-6])',  # January 15-17, 2025
            r'(202[4-6])-(\d{2})-(\d{2})',  # ISO format
            r'(\d{1,2})/(\d{1,2})/(202[4-6])',  # US format
        ]

        for pattern in date_patterns:
            match = re.search(pattern, html)
            if match:
                date = parse_date_from_text(match.group(0))
                if date:
                    return date, name

        # Fallback: Look in meta tags
        meta_match = re.search(r'content="[^"]*(\w+ \d{1,2}[-–]\d*,? 202[4-6])', html)
        if meta_match:
            date = parse_date_from_text(meta_match.group(1))
            if date:
                return date, name

        return None, name

    except Exception as e:
        return None, None


def filter_tournaments_by_date():
    """Filter tournaments to those in the date range"""
    print("=" * 70)
    print("STEP 1: Filtering tournaments by date")
    print(f"Date range: {START_DATE.strftime('%B %d, %Y')} - {END_DATE.strftime('%B %d, %Y')}")
    print("=" * 70)
    print()

    # Load tournaments
    with open(TOURNAMENTS_FILE, 'r') as f:
        data = json.load(f)

    tournaments = data.get('tournaments', [])

    # Filter to 2025 GotSport events
    candidates = [t for t in tournaments
                  if t.get('platform') == 'gotsport'
                  and str(t.get('year', '')) in ['2025', '2026']]

    print(f"Candidate events to check: {len(candidates)}")
    print()

    # Check already filtered
    filtered = []
    if os.path.exists(FILTERED_FILE):
        with open(FILTERED_FILE, 'r') as f:
            filtered = json.load(f)
        print(f"Already filtered: {len(filtered)} events")

    already_checked = set(str(t['event_id']) for t in filtered)

    # Check remaining events
    to_check = [t for t in candidates if str(t['event_id']) not in already_checked]
    print(f"Remaining to check: {len(to_check)}")
    print()

    in_range = [t for t in filtered if t.get('in_range')]
    print(f"Already found in range: {len(in_range)}")

    batch_size = 10
    checked = 0

    for i in range(0, len(to_check), batch_size):
        batch = to_check[i:i+batch_size]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check_event_date, int(t['event_id'])): t for t in batch}

            for future in as_completed(futures):
                t = futures[future]
                event_date, name = future.result()
                checked += 1

                t['checked'] = True
                if name:
                    t['name'] = name

                if event_date:
                    t['start_date'] = event_date.strftime('%Y-%m-%d')
                    if START_DATE <= event_date <= END_DATE:
                        t['in_range'] = True
                        in_range.append(t)
                        name_safe = t.get('name', '')[:45].encode('ascii', 'replace').decode('ascii')
                        print(f"  + {t['event_id']}: {name_safe} ({event_date.strftime('%b %d')})")
                    else:
                        t['in_range'] = False
                else:
                    t['start_date'] = None
                    t['in_range'] = False

                filtered.append(t)

        # Progress update
        if checked % 50 == 0:
            print(f"  [Checked {checked}/{len(to_check)} | In range: {len(in_range)}]")
            # Save progress
            with open(FILTERED_FILE, 'w') as f:
                json.dump(filtered, f, indent=2)

        time.sleep(0.5)

    # Final save
    with open(FILTERED_FILE, 'w') as f:
        json.dump(filtered, f, indent=2)

    in_range = [t for t in filtered if t.get('in_range')]
    print()
    print(f"Total events in date range: {len(in_range)}")

    return in_range


def get_schedule_groups(event_id):
    """Get schedule group IDs from event page"""
    url = f"https://system.gotsport.com/org_event/events/{event_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        groups = list(set(re.findall(r'group=(\d+)', response.text)))
        return groups
    except:
        return []


def scrape_group_games(event_id, group_id, event_name):
    """
    Scrape games from a schedule group with improved age extraction.

    Returns list of games with age_group, age_from_home, age_from_away, age_from_division
    """
    url = f"https://system.gotsport.com/org_event/events/{event_id}/schedules?group={group_id}"
    games = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        html = response.text

        # Extract division age from header
        division_info = extract_age_from_division_header(html)

        # First pass: collect all team names and their ages
        all_team_ages = []
        team_links = re.findall(r'<a[^>]*href="[^"]*team[^"]*"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
        for team_name in team_links:
            age_info = extract_age_from_team_name(team_name.strip())
            if age_info.get('birth_year') or age_info.get('age_code'):
                all_team_ages.append(age_info)

        # Look for game rows - find table rows with score patterns
        game_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(game_pattern, html, re.DOTALL | re.IGNORECASE)

        for row in rows:
            # Look for score pattern
            score_match = re.search(r'>(\d+)\s*[-–]\s*(\d+)<', row)
            if not score_match:
                continue

            home_score = int(score_match.group(1))
            away_score = int(score_match.group(2))

            # Extract team names from links
            row_team_links = re.findall(r'<a[^>]*href="[^"]*team[^"]*"[^>]*>([^<]+)</a>', row, re.IGNORECASE)

            # Also try non-link team cells
            if len(row_team_links) < 2:
                team_cells = re.findall(r'<td[^>]*>([^<]{3,50})</td>', row)
                row_team_links = [t.strip() for t in team_cells if t.strip() and not re.match(r'^[\d\-:]+$', t.strip())]

            if len(row_team_links) >= 2:
                home_team = row_team_links[0].strip()
                away_team = row_team_links[1].strip()

                # Skip byes and placeholders
                if 'bye' in home_team.lower() or 'bye' in away_team.lower():
                    continue
                if len(home_team) < 3 or len(away_team) < 3:
                    continue

                # Extract date
                date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4})', row, re.IGNORECASE)
                game_date = date_match.group(1) if date_match else ""

                # Extract age from team names
                home_age_info = extract_age_from_team_name(home_team)
                away_age_info = extract_age_from_team_name(away_team)

                # Determine best age group
                age_group = determine_best_age_group(home_age_info, away_age_info, division_info, all_team_ages)

                # Build age detail string for debugging/review
                age_details = []
                if home_age_info.get('birth_year'):
                    age_details.append(f"home:{home_age_info['birth_year']}")
                if away_age_info.get('birth_year'):
                    age_details.append(f"away:{away_age_info['birth_year']}")
                if division_info.get('division_birth_year'):
                    age_details.append(f"div:{division_info['division_birth_year']}")

                games.append({
                    'tournament_id': event_id,
                    'tournament_name': event_name,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'game_date': game_date,
                    'age_group': age_group,
                    'age_from_home': home_age_info.get('age_group', ''),
                    'age_from_away': away_age_info.get('age_group', ''),
                    'age_from_division': f"{division_info.get('division_gender', '')}{division_info.get('division_age', '')}" if division_info.get('division_age') else '',
                    'home_birth_year': home_age_info.get('birth_year'),
                    'away_birth_year': away_age_info.get('birth_year'),
                    'division_birth_year': division_info.get('division_birth_year'),
                    'group_id': group_id,
                    'source_url': url,
                    'scraped_at': datetime.now().isoformat()
                })

    except Exception as e:
        pass

    return games


def import_games_to_db(games):
    """Import games to SQLite database"""
    if not games:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    imported = 0
    for game in games:
        try:
            # Check if game exists
            cursor.execute('''
                SELECT 1 FROM games
                WHERE home_team = ? AND away_team = ?
                AND home_score = ? AND away_score = ?
                LIMIT 1
            ''', (game['home_team'], game['away_team'],
                  game['home_score'], game['away_score']))

            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO games (home_team, away_team, home_score, away_score,
                                      game_date, age_group, league, source_url, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (game['home_team'], game['away_team'],
                      game['home_score'], game['away_score'],
                      game.get('game_date', ''),
                      game.get('age_group', ''),
                      'Tournament',
                      game.get('source_url', ''),
                      game.get('scraped_at', datetime.now().isoformat())))
                imported += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    return imported


def load_progress():
    """Load scraping progress"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'scraped': [], 'total_games': 0}


def save_progress(progress):
    """Save scraping progress"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def scrape_tournaments(in_range):
    """Scrape games from tournaments in date range"""
    print()
    print("=" * 70)
    print("STEP 2: Scraping games from tournaments (v2 - improved age extraction)")
    print("=" * 70)
    print()

    progress = load_progress()
    already_scraped = set(progress.get('scraped', []))
    total_games = progress.get('total_games', 0)

    to_scrape = [t for t in in_range if str(t['event_id']) not in already_scraped]
    print(f"Tournaments to scrape: {len(to_scrape)}")
    print(f"Already scraped: {len(already_scraped)}")
    print(f"Games imported so far: {total_games}")
    print()

    for i, t in enumerate(to_scrape, 1):
        event_id = int(t['event_id'])
        name = t.get('name', f'Event {event_id}')[:50]
        name_safe = name.encode('ascii', 'replace').decode('ascii')

        print(f"[{i}/{len(to_scrape)}] {name_safe}")

        groups = get_schedule_groups(event_id)
        if not groups:
            print(f"  -> No schedule groups found")
            already_scraped.add(str(event_id))
            progress['scraped'] = list(already_scraped)
            save_progress(progress)
            continue

        print(f"  -> Found {len(groups)} divisions")

        tournament_games = []
        for group in groups:
            games = scrape_group_games(event_id, group, name)
            tournament_games.extend(games)
            time.sleep(0.3 + random.uniform(0, 0.5))

        if tournament_games:
            # Count how many have age groups
            with_age = sum(1 for g in tournament_games if g.get('age_group'))
            imported = import_games_to_db(tournament_games)
            total_games += imported
            print(f"  -> Scraped {len(tournament_games)} games ({with_age} with age), imported {imported} new")
        else:
            print(f"  -> No games found")

        already_scraped.add(str(event_id))
        progress['scraped'] = list(already_scraped)
        progress['total_games'] = total_games
        save_progress(progress)

        # Be nice to server
        time.sleep(1 + random.uniform(0, 2))

    print()
    print("=" * 70)
    print(f"COMPLETE: Scraped {len(to_scrape)} tournaments, imported {total_games} total games")
    print("=" * 70)

    return total_games


def test_age_extraction():
    """
    Test the age extraction functions.

    CRITICAL: Patterns like B11, G13, 14F, 12G are SHORT BIRTH YEARS, not ages!
    - G13 = Born 2013, age_group = G13
    - B11 = Born 2011, age_group = B11
    - 14F = Born 2014, Female, age_group = G14
    - 12G = Born 2012, Girls, age_group = G12

    The number in the age_group IS the birth year suffix!
    G12 = Girls born in 2012 (who are 13 years old in 2025)
    B11 = Boys born in 2011 (who are 14 years old in 2025)
    """
    print("Testing age extraction...")
    print()
    print("REMEMBER: G13, B11, 14F, 12G etc. are BIRTH YEARS, not ages!")
    print("  G13 = 13G = 2013 = 2013G = Born 2013 = age_group G13")
    print("  B11 = 11B = 2011 = 2011B = Born 2011 = age_group B11")
    print("  12G = G12 = 2012 = 2012G = Born 2012 = age_group G12")
    print()
    print("The number in the age_group IS the birth year, NOT the calculated age!")
    print()

    test_teams = [
        # Full birth year patterns - age_group uses birth year suffix, NOT calculated age
        ("Rebels Futbol Club Rebels FC - 2013 Girls", 2013, "G", "G13"),  # 2013 Girls = G13
        ("South Parkland Youth SP Leopards 2013", 2013, None, None),  # No gender = no age_group
        ("SJEB FC SJEB 2014G Colonial", 2014, "G", "G14"),  # 2014G = G14
        ("NJ Premier FC NJ Premier G2014", 2014, "G", "G14"),  # G2014 = G14
        ("Real Colorado 2016 Girls Pierson", 2016, "G", "G16"),  # 2016 Girls = G16

        # Short birth year patterns (G13, B11, 12G = born 2013, 2011, 2012)
        # The number IS the birth year, NOT the age!
        ("Tonka Fusion Elite 13G Pre-GA", 2013, "G", "G13"),  # 13G = born 2013 = G13
        ("FC Dallas Youth 10B North White", 2010, "B", "B10"),  # 10B = born 2010 = B10
        ("Sting 12G Soutar", 2012, "G", "G12"),  # 12G = born 2012 = G12
        ("Renegades 11G Blanton", 2011, "G", "G11"),  # 11G = born 2011 = G11
        ("ALBION SC San Diego G14 Pre GA Aspire", 2014, "G", "G14"),  # G14 = born 2014 = G14
        ("PA Classics Academy Lancaster 18F", 2018, "G", "G18"),  # 18F = born 2018 = G18

        # Club founding years should be IGNORED (not in valid range 2005-2020)
        ("1974 Newark FC G13", 2013, "G", "G13"),  # 1974 = founding year, G13 = birth year
        ("FC 1904 San Diego 2012 Boys", 2012, "B", "B12"),  # 1904 = founding year, 2012 = birth year
        ("Inter Miami CF 1926 B11", 2011, "B", "B11"),  # 1926 ignored, B11 = birth year

        # No age
        ("Warminster SC Freedom", None, None, None),
        ("Sand SCORchers", None, None, None),
        ("United Soccer Athletes Capybara FC", None, None, None),
    ]

    print(f"{'Team Name':<50} | Expected          | Got")
    print("-" * 100)

    all_passed = True
    for team, exp_year, exp_gender, exp_age_group in test_teams:
        info = extract_age_from_team_name(team)
        passed = (info['birth_year'] == exp_year and
                  info['gender'] == exp_gender and
                  info['age_group'] == exp_age_group)
        status = "OK" if passed else "FAIL"
        if not passed:
            all_passed = False
        exp_ag_str = exp_age_group if exp_age_group else "None"
        got_ag_str = info['age_group'] if info['age_group'] else "None"
        print(f"{team[:50]:<50} | {exp_year}, {exp_gender}, {exp_ag_str:<6} | {info['birth_year']}, {info['gender']}, {got_ag_str} [{status}]")

    print()
    print("Birth year to age group conversion:")
    print("  (age_group uses birth year suffix, NOT calculated age)")
    for year in [2010, 2011, 2012, 2013, 2014, 2015, 2016]:
        suffix = year % 100
        age = 2025 - year
        print(f"  {year} -> G{suffix}/B{suffix} (players are {age} years old in 2025)")

    print()
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")


def main():
    print()
    print("GotSport Tournament Scraper v2 - Improved Age Extraction")
    print(f"Date range: May 25, 2025 - {END_DATE.strftime('%B %d, %Y')}")
    print()

    if '--test' in sys.argv:
        test_age_extraction()
        return

    filter_only = '--filter-only' in sys.argv
    resume = '--resume' in sys.argv

    # Step 1: Filter by date
    if resume and os.path.exists(FILTERED_FILE):
        with open(FILTERED_FILE, 'r') as f:
            filtered = json.load(f)
        in_range = [t for t in filtered if t.get('in_range')]
        print(f"Resuming with {len(in_range)} events in date range")
    else:
        in_range = filter_tournaments_by_date()

    if filter_only:
        print("\nFilter-only mode. Run without --filter-only to scrape games.")
        return

    if not in_range:
        print("\nNo events found in date range.")
        return

    # Step 2: Scrape games
    scrape_tournaments(in_range)


if __name__ == "__main__":
    main()
