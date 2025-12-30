# Seedline Project

## About
Seedline.ai is a youth soccer analytics platform featuring:
- Web scrapers for multiple leagues (ECNL, Girls Academy, ASPIRE, NPL, MLS NEXT, State Cups)
- Team ranking algorithms using PageRank-based approach
- React frontend for displaying rankings, team profiles, player badges
- SQLite database storing games, teams, and players
- Firebase hosting at seedline.ai
- Daily automated scraping and ranking updates

## Current Database Stats
- **228,000+ games** scraped
- **55,000+ teams** tracked
- **99,000+ players** with profiles
- **5,142 clubs** with geocoded addresses
- **16,154 teams** with specific addresses

## Steve's Working Style
- **Vibe coder** - Understands programming logic and system architecture, prefers Claude to handle implementation details
- Scripts now use "final" naming convention (e.g., `team_ranker_final.py`)
- Test changes before finalizing
- Prefers practical, working solutions over complex theoretical approaches
- Maintains detailed version control across development projects

## Key File Locations

### Scrapers and Data
```
C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\
```
- `seedlinedata.db` - Main SQLite database
- `Run Rankings\team_ranker_final.py` - **CURRENT** ranking algorithm
- `scheduled_scraper.py` - Automated daily scraper
- `run_daily_scrape.bat` - Daily scheduled task runner
- `database_cleanup_safe.py` - Non-destructive database cleanup

### React Frontend
```
C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\
```
- Rankings display with filters (league, age group, state, gender)
- Team profiles with game history and rankings charts
- Club profiles with aggregated team rankings
- Player badge systems
- Rankings map with geocoded team locations
- Conference simulation tool
- Mobile-responsive design

### Key Data Files
- `public/rankings_for_react.json` - Full rankings data (~120MB with teams, players, games)
- `public/rankings_light.json` - Teams only (~25MB, for fast initial load)
- `public/club_addresses.json` - 5,142 clubs + 16,154 teams with geocoded addresses
- `public/rankings_history.json` - Historical ranking data for charts
- `public/tournaments_data.json` - Tournament game data

### Backend Server Files
- `admin_server.py` - Python HTTP server with API endpoints
- `activity_logger.py` - Activity tracking and VPN detection
- `auth_middleware.py` - Firebase JWT token verification
- `seedline_activity.db` - Activity logging database (separate from main data)

## Scrapers

### Current Scrapers
| Scraper | Filename | Platform |
|---------|----------|----------|
| ECNL/ECNL-RL | `ecnl_scraper_final.py` | TotalGlobalSports |
| Girls Academy | `GA_league_scraper_final.py` | Custom |
| NPL | `us_club_npl_league_scraper_final.py` | GotSport |
| ASPIRE | `ASPIRE_league_scraper_final.py` | Custom |
| MLS NEXT | `mls_next_scraper_final.py` | Custom |
| Tournament | `gotsport_game_scraper_final.py` | GotSport |

### Scraper Platforms
| Platform | URL Pattern | Leagues |
|----------|-------------|---------|
| TotalGlobalSports | public.totalglobalsports.com | ECNL, ECNL-RL |
| GotSport | system.gotsport.com | NPL leagues, tournaments |
| SincSports | soccer.sincsports.com | Some tournaments |

## Ranker Configuration

### Use team_ranker_final.py
**IMPORTANT:** Always use `team_ranker_final.py` - it has critical features:
- Club addresses fallback from `club_addresses.json`
- Address validation (rejects invalid "None" values)
- Full address data in JSON output
- GA (Georgia) vs GA (Girls Academy) state confusion fix

### League Factors
```python
LEAGUE_FACTORS = {
    'ECNL': 2.0,       # Top tier
    'GA': 1.55,        # High tier
    'MLS NEXT': 1.2,   # MLS academies
    'ECNL-RL': 1.05,   # Strong regional
    'ASPIRE': 0.90,    # Competitive
    'NPL': 0.90,       # Regional NPL (all consolidated)
}
DEFAULT_LEAGUE_FACTOR = 0.75  # Unknown leagues
```

### Key Features
- Team name alias system (170+ patterns)
- Self-play filter (removes teams playing themselves)
- Cross-league deduplication
- GA ceiling compression (ratings above 1700 compressed)
- Minimum wins rule (< 5 wins cannot be top 10)
- Offensive/Defensive power scores
- Recency weighting
- **Club addresses fallback** - Uses `club_addresses.json` when DB lacks address

### Ranker Output
- `rankings_for_react.json` - JSON for React app (auto-copied to public folder)
- `rankings_history.json` - Appends daily ranking snapshot for history charts
- Excel export with detailed stats

## Data Architecture & Flow

### Data Pipeline
```
Scrapers (ECNL, GA, NPL, etc.)
    ↓
seedlinedata.db (main database: games, teams, players)
    ↓
team_ranker_final.py
    ↓
├── rankings_for_react.json (full data: ~120MB)
├── rankings_light.json (teams only: ~25MB, auto-generated)
└── rankings_history.json (daily snapshots)
    ↓
React Frontend (loads light JSON first, full in background)
```

### Progressive Loading (Frontend)
1. **Initial load:** Fetch `rankings_light.json` (~25MB, teams + metadata only)
2. **Page renders immediately** with all 33k teams
3. **Background load:** Fetch `rankings_for_react.json` for players/games data
4. Players and games become available for team profiles

### API Endpoints (admin_server.py)

#### Rankings API
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/rankings` | Get rankings with filters (gender, age_group, league, state) |
| `GET /api/v1/rankings/team/{id}` | Get single team profile |
| `GET /api/v1/rankings/club/{name}` | Get all teams for a club |
| `GET /api/v1/rankings/search` | Search teams, clubs, players |

#### Activity Tracking API
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/activity/session` | Create tracking session (returns session_id) |
| `POST /api/v1/activity/pageview` | Log page view |
| `POST /api/v1/activity/heartbeat` | Update time on page |
| `GET /api/v1/activity/stats` | Admin: view activity stats |
| `GET /api/v1/activity/suspicious` | Admin: view suspicious activity |

### Activity Tracking System

#### Database: seedline_activity.db
Separate from main data for performance. Tables:
- **sessions** - Browser sessions with device fingerprint, IP, VPN detection
- **page_views** - Every page visit with timing and navigation context
- **api_calls** - API request logging with response times
- **suspicious_activity** - Flagged suspicious behavior
- **daily_session_stats** - Aggregated daily metrics
- **blocklist** - Blocked IPs/fingerprints

#### VPN Detection
Uses ip-api.com to detect:
- VPN/proxy usage
- Datacenter/hosting provider IPs
- Mobile networks
- Geographic location

#### Suspicious Behavior Detection
| Rule | Threshold | Severity |
|------|-----------|----------|
| Team pages per day | >100 | Medium |
| Sequential team IDs | 20+ consecutive | High |
| API requests per minute | >60 | High |
| Rapid navigation | >5 pages/second | Medium |

#### Rate Limits by Account Type
| Account | Requests/min |
|---------|--------------|
| Guest | 30 |
| Free | 60 |
| Paid/Admin | 120 |

### Frontend Services

#### src/services/api.js
- Singleton API client for all backend calls
- Manages auth tokens and session tracking
- Automatic page view logging
- Rate limit handling

#### src/services/fingerprint.js
- Collects device fingerprint (screen, timezone, language, hardware)
- Generates SHA-256 hash for cross-session tracking

### Configuration Flags
In `useRankingsData.js`:
- `ENABLE_PROGRESSIVE_LOADING` - Use API for initial load (currently disabled)

In `UserContext.jsx`:
- `ACTIVITY_TRACKING` - Enable/disable activity logging

## Daily Automation

### Scheduled Task
The `run_daily_scrape.bat` runs daily and:
1. Runs `scheduled_scraper.py` to scrape all leagues
2. Runs `database_cleanup_safe.py` for data quality fixes
3. Runs `team_ranker_final.py --no-cleanup` to update rankings

### To Run Manually
```bash
cd "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data"
python scheduled_scraper.py
python database_cleanup_safe.py
python "Run Rankings\team_ranker_final.py" --no-cleanup
```

## Database Schema

### games table
- game_id, game_date, game_date_iso, game_time
- home_team, away_team, home_score, away_score
- league, age_group, gender, conference
- location, game_status, source_url, scraped_at

### teams table
- team_url, club_name, team_name, age_group, gender
- league, conference, city, state, zip_code
- street_address, lat, lng

### players table
- Player data exported to JSON for React app

## Leagues Being Scraped

### Tier 1 (Primary)
- **ECNL** - Elite Clubs National League (2.0x factor)
- **ECNL-RL** - ECNL Regional League (1.05x factor)
- **Girls Academy (GA)** - Girls Academy league (1.55x factor)
- **MLS NEXT** - MLS youth development (1.2x factor)

### Tier 2
- **ASPIRE** - ASPIRE league (0.90x factor)
- **NPL** - All NPL regional leagues consolidated (0.90x factor)
  - Great Lakes Alliance NPL, FCL NPL, CPSL NPL
  - Central States NPL, Frontier Premier League
  - Mid-Atlantic Premier League, MDL NPL
  - Minnesota NPL, Mountain West NPL, NorCal NPL, SOCAL NPL

### State/Regional
- State Cups (various states)
- Southeastern CCL
- Florida regional leagues (WFPL, NFPL, SEFPL, CFPL)
- SLYSA, ICSL, and other regional leagues

## Recent Fixes (December 2025)

### State Data Pipeline (FIXED)
- **Problem:** Teams missing state in rankings table
- **Solution:** v46 ranker now uses `club_addresses.json` as fallback
- **Result:** 99.7% of teams now have state (31,024 of 31,117)

### Age Group Ordering (FIXED)
- G06/B06 (birth year 2006) are oldest, G19/B19 are youngest
- All age groups G06-G19 and B06-B19 now included in rankings

### League Dropdown Grouping (ADDED)
- Rankings and Clubs pages now group leagues into National vs Regional

### Mobile Optimization (IMPROVED)
- Tap-to-expand for truncated text on mobile
- Optimized column widths for Club Rankings
- Better responsive layout

## Common Commands

```bash
# Run the ranker
cd "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data"
python "Run Rankings\team_ranker_final.py" --no-cleanup
# This auto-generates both rankings_for_react.json AND rankings_light.json

# Run full daily process
run_daily_scrape.bat

# Deploy to Firebase
cd "App FrontEnd\Seedline_App"
npm run build && firebase deploy

# Start local dev server (frontend + backend)
cd "App FrontEnd\Seedline_App"
npm run dev                    # Terminal 1: Vite dev server (port 5173)
python admin_server.py         # Terminal 2: Backend API (port 5050)
# Vite proxy forwards /api/* requests to backend automatically

# View activity logs
cd "App FrontEnd\Seedline_App"
sqlite3 seedline_activity.db "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 10;"
```

## Version History

### Naming Convention Change (December 2025)
All scrapers and the ranker now use "final" naming instead of version numbers:
- `team_ranker_final.py` (was v46)
- `ecnl_scraper_final.py` (was v76)
- `GA_league_scraper_final.py` (was v16)
- `us_club_npl_league_scraper_final.py` (was v21)
- `ASPIRE_league_scraper_final.py` (was v8)
- Old versions moved to `old data and files` subfolders

### Frontend (useRankingsData.js)
- v52: Cache-busting with timestamp
- v51: Progressive loading (light JSON first, full in background)

### Backend (admin_server.py)
- Added API v1 endpoints for rankings and activity tracking
- Firebase JWT verification (auth_middleware.py)
- Activity logging with VPN detection (activity_logger.py)

## CRITICAL: Age Group Format Uses BIRTH YEAR

**⚠️ NEVER CONFUSE THESE - THIS MISTAKE HAS BEEN MADE MULTIPLE TIMES ⚠️**

### Birth Year Extraction Priority

**Not all numbers in team names are birth years!** Example: "1974 Newark" (club founded in 1974)

**Priority order for determining birth year:**
1. **Numbers attached to G, B, F, or M** (most reliable) - `G12`, `12B`, `14F`, `M11`
2. **Full 4-digit years in valid range** (2005-2020) - `2012`, `2013`
3. **If ambiguous, use opponent's birth year** as reference (closest match wins)

### All These Patterns Are Equivalent Birth Year Representations:

```
12G = G12 = 2012 = 2012G = 12F = F12 = 2012F = birth year 2012
```

**The number attached to G/B/F/M is ALWAYS the birth year, NEVER the current age!**

| Pattern | Meaning | Age Group | Players' Age in 2025 |
|---------|---------|-----------|---------------------|
| `G12`, `12G`, `2012G` | Girls, Born 2012 | G12 | 13 years old |
| `B11`, `11B`, `2011B` | Boys, Born 2011 | B11 | 14 years old |
| `G13`, `13G`, `2013G` | Girls, Born 2013 | G13 | 12 years old |
| `14F`, `F14`, `2014F` | Girls, Born 2014 | G14 | 11 years old |

### Examples

```
Team Name: "Sting 12G Soutar"
  12G = G12 = birth year 2012 = age_group G12

Team Name: "FC Dallas 10B North"
  10B = B10 = birth year 2010 = age_group B10

Team Name: "ALBION G14 Pre GA"
  G14 = birth year 2014 = age_group G14

Team Name: "1974 Newark FC 2013"
  1974 = club founding year (IGNORE)
  2013 = birth year = age_group G13 or B13
```

### The ONLY Exception: U-Format

`U13`, `U-11`, `U9` are the ONLY patterns where the number is an age:
- `U13` = Under 13 = kids who are 12 or younger
- Use U-format to calculate birth year: `birth_year = 2025 - u_age`

### Formula

```
# From team name pattern to age_group:
12G → birth_year = 2012 → age_group = G12

# The number in age_group IS the birth year suffix!
G12 = Girls born in 2012 (who are 13 years old in 2025)
B10 = Boys born in 2010 (who are 15 years old in 2025)

# When ambiguous (no G/B/F/M attached):
# Use opponent's birth year to pick the closest valid year
```

## Notes
- Age groups use BIRTH YEAR: G12 = Girls born 2012, B11 = Boys born 2011
- G12 players are 13 years old in 2025, B11 players are 14 years old in 2025
- Graduation year 2030 = birth year 2012 (grad year - 18)
- Always clear browser cache after deploying updates
- The ranker trusts database league values (don't try to detect from team names)
