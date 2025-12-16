# Seedline Project

## About
Seedline.ai is a youth soccer analytics platform featuring:
- Web scrapers for multiple leagues (ECNL, Girls Academy, ASPIRE, NPL)
- Team ranking algorithms using PageRank-based approach
- React frontend for displaying rankings, team profiles, player badges
- SQLite database storing games, teams, and players

## Steve's Working Style
- **Vibe coder** - Understands programming logic and system architecture, prefers Claude to handle implementation details
- Increment version numbers when updating scripts (v42 → v43)
- Test changes before finalizing
- Prefers practical, working solutions over complex theoretical approaches
- Maintains detailed version control across development projects

## Key File Locations

### Scrapers and Data
```
C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\
```
- `seedlinedata.db` - Main SQLite database
- `team_ranker_v43.py` - Latest ranking algorithm (NPL consolidation)
- `us_club_npl_league_scraper_v21.py` - NPL league scraper
- `fix_npl_age_groups.py` - Database cleanup for NPL age formats

### React Frontend
```
C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\
```
- Rankings display with filters (league, age group, state, gender)
- Team profiles and player badge systems
- Mobile-responsive design

## Database Schema

### games table
- game_id, game_date, game_date_iso, game_time
- home_team, away_team, home_score, away_score
- league, age_group, gender, conference
- location, game_status, source_url, scraped_at

### teams table
- team_url, club_name, team_name, age_group, gender
- league, conference, city, state, zip_code

### players table
- Player data exported to JSON for React app

## Current Issues / Recent Work

### 1. NPL Age Group Format (NEEDS FIX)
- ~4,700 NPL games have wrong age format stored as graduation year
- G30 should be G13 (grad 2030 → born 2012 → age 13)
- G28 should be G15, G31 should be G12, etc.
- **Fix:** Run `fix_npl_age_groups.py` against the database
- Newer scrapes (v21) save correctly; old data needs migration

### 2. NPL League Consolidation (FIXED in v43)
- Regional NPL leagues (Great Lakes Alliance NPL, FCL NPL, etc.) were showing as separate leagues in dropdown
- **Fixed in team_ranker_v43.py:** All NPL regional leagues now consolidate to just "NPL" in output
- League factors still apply correctly during ranking calculation

## Leagues Being Scraped

### Tier 1 (Primary)
- **ECNL** - Elite Clubs National League (TotalGlobalSports platform)
- **ECNL-RL** - ECNL Regional League
- **Girls Academy (GA)** - Girls Academy league

### Tier 2
- **ASPIRE** - ASPIRE league (0.90 multiplier)
- **NPL** - US Club Soccer National Premier Leagues (GotSport platform)
  - Great Lakes Alliance NPL
  - FCL NPL (Florida)
  - CPSL NPL (Chesapeake)
  - Central States NPL
  - Frontier Premier League
  - Mid-Atlantic Premier League
  - MDL NPL (Midwest Developmental)
  - Minnesota NPL, Mountain West NPL, NorCal NPL, SOCAL NPL
  - And more regional leagues

## Ranker Configuration (v43)

### League Factors
```python
LEAGUE_FACTORS = {
    'ECNL': 2.0,       # Top tier
    'GA': 1.55,        # High tier
    'ECNL-RL': 1.05,   # Strong regional
    'ASPIRE': 0.90,    # Competitive
    'NPL': 0.90,       # Regional NPL (all consolidated)
}
DEFAULT_LEAGUE_FACTOR = 0.75  # Unknown leagues
```

### Key Features
- Team name alias system (178 patterns)
- Self-play filter
- Cross-league deduplication
- GA ceiling compression (ratings above 1700 compressed)
- Minimum wins rule (< 5 wins cannot be top 10)
- Offensive/Defensive power scores
- Recency weighting

## Ranker Output
- `rankings_for_react.json` - JSON for React app
- Auto-copies to React app public folder
- Excel export with detailed stats

## Scraper Platforms

| Platform | URL Pattern | Leagues |
|----------|-------------|---------|
| GotSport | system.gotsport.com | NPL leagues |
| TotalGlobalSports | public.totalglobalsports.com | ECNL, ECNL-RL |
| SincSports | soccer.sincsports.com | Some tournaments |

## Version History

### team_ranker
- v42c → v43: Added NPL league consolidation (all regional NPL → "NPL")

### us_club_npl_league_scraper
- v20 → v21: Fixed CSV age group output (birth year → G12/B13 format)

## Common Commands

```bash
# Run the ranker
python team_ranker_v43.py --no-cleanup

# Fix NPL age groups
python fix_npl_age_groups.py --db seedlinedata.db

# Run NPL scraper
python us_club_npl_league_scraper_v21.py --league "Great Lakes"
```

## Notes
- Age groups: G13 = Girls 13U, B12 = Boys 12U
- Birth year 2012 = age 13 in 2025 = G13 or B13
- Graduation year 2030 = birth year 2012 (grad year - 18)
