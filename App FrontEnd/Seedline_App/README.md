# Seedline Soccer Analytics Platform v49

A comprehensive youth soccer analytics platform for tracking teams, games, players, and rankings across ECNL, Girls Academy, ECNL-RL, and ASPIRE leagues.

## V49 Changes

### Badges - Award to ANY Player
- Search all 109k+ players by name, team, jersey number, or age group
- No longer limited to "My Players" only
- Player info is stored with badges for display

### Rankings Table Improvements
- **Removed Club column** - cleaner table view
- **GD now shows average per game** - not total goal differential
- **Sortable columns**: Click Record, GD, Off Rank, or Def Rank to sort
- **Record sorting**: 3 pts/win, 1 pt/draw, tiebreaker = more games played
- **Uniform header font size** - all headers now same size
- **Narrower Off/Def columns** - headers wrap to 2 lines

### Previous Changes (V48)
- Favorites now survive JSON regeneration (uses name+ageGroup matching)
- Default team tab is Games
- Tab order: Games → Roster → Links → Overview

## File Structure

```
App_FrontEnd/
├── Seedline_Data/              ← PERSISTENT DATA (never overwrite on updates)
│   ├── seedline_users.json     ← User accounts & passwords
│   ├── admin_config.json       ← Settings + badges + saved players
│   └── ga_events_config.json   ← GA event discovery data & team mappings
│
└── Seedline_App/               ← APP CODE (safe to replace on updates)
    ├── admin_dashboard.html    ← Admin UI
    ├── admin_server.py         ← Backend API server
    ├── index.html              ← React app entry
    ├── package.json            ← Node dependencies
    ├── vite.config.js          ← Build config
    ├── launch_admin.bat        ← Start admin server
    ├── launch_app.bat          ← Start React dev server
    │
    ├── src/                    ← React source code
    │   ├── App.jsx
    │   ├── App.css
    │   ├── components/         ← React components
    │   ├── context/            ← React context (auth, etc.)
    │   └── data/               ← Data hooks
    │
    ├── public/                 ← Static files (can be regenerated)
    │   ├── seedline-logo.png
    │   ├── rankings_for_react.json  ← Generated from database
    │   └── players_for_react.json   ← Generated from database
    │
    ├── scrapers/               ← Web scraper code (in scrapers and data folder)
    │   ├── ecnl_scraper_final.py
    │   ├── GA_league_scraper_final.py
    │   ├── GA_events_scraper_final.py
    │   └── ASPIRE_league_scraper_final.py
    │
    └── server/                 ← URL validator service
        └── urlValidator.js
```

## Important: Updating the App

When you download a new version of Seedline_App:

1. **KEEP** the `Seedline_Data` folder - it contains your users, badges, and settings
2. **REPLACE** the entire `Seedline_App` folder with the new version
3. Your data will automatically be preserved

The app automatically migrates data files from the old location to `Seedline_Data` on first run.

## Quick Start

### 1. Start the Admin Server
```bash
# Windows: double-click launch_admin.bat
# Or run manually:
python admin_server.py
```
Opens at: http://localhost:5050

### 2. Start the React App (Development)
```bash
# Windows: double-click launch_app.bat
# Or run manually:
npm install
npm run dev
```
Opens at: http://localhost:5173

## Admin Dashboard Features

### Scrapers Page
Run data scrapers for different leagues:
- **ECNL + ECNL-RL Scraper** - League games and players
- **Girls Academy Scraper** - GA league games
- **GA Events Scraper** - Champions Cup, Playoffs, Showcases, Regionals
- **ASPIRE Scraper** - ASPIRE league games

Scrapers open in a **visible CMD window** so you can:
- See real-time progress
- Interact with the console
- Press Ctrl+C to stop early

### Other Pages
- **Dashboard** - Overview stats and recent games
- **Teams** - Browse/edit teams
- **Players** - Browse/edit players
- **Games** - Browse/edit games
- **Export** - Generate React data files
- **Users** - Manage user accounts
- **Files & Folders** - View system files and documentation
- **Settings** - Configure paths and options

## Database Location

The main database (`seedlinedata.db`) is located in your scrapers folder:
```
Dropbox/Seedline/Scrapers/seedlinedata.db
```

This is separate from the app to allow scrapers to run independently.

## Data Files

### Persistent Data (Seedline_Data/)
| File | Description |
|------|-------------|
| `seedline_users.json` | User accounts, passwords, roles |
| `admin_config.json` | App settings, scraper history, user badges & saved players |
| `ga_events_config.json` | Discovered GA events, team name mappings |

### Generated Data (public/)
| File | Description |
|------|-------------|
| `rankings_for_react.json` | Team rankings (regenerate via Export) |
| `players_for_react.json` | Player data (regenerate via Export) |

## User Roles

| Role | Permissions |
|------|-------------|
| Guest | View rankings only |
| Free | View rankings + team profiles |
| Paid | Full access including player data |
| Admin | Full access + admin dashboard |

## Scrapers

### Running from Admin UI
1. Go to Scrapers page
2. Click "Run Now" on any scraper
3. Configure settings (gender, age groups, date range)
4. Click "Run Scraper"
5. Watch progress in the CMD window that opens

### Running from Command Line
```bash
# ECNL + ECNL-RL
python ecnl_scraper_final.py --gender girls --ages 13 --days 30

# Girls Academy League
python GA_league_scraper_final.py --gender girls --ages 13 --days 30

# GA Events (Champions Cup, Playoffs, etc.)
python GA_events_scraper_final.py --scrape

# ASPIRE
python ASPIRE_league_scraper_final.py --gender girls --ages 13G --days 30
```

### GA Events Scraper Commands
```bash
--discover      # Find new events on GA website
--scrape        # Scrape active events (within 2 weeks)
--scrape-all    # Scrape all discovered events
--status        # Show event status
--add-event ID  # Add event by GotSport ID
```

## Troubleshooting

### "Server not connected"
Make sure admin_server.py is running:
```bash
python admin_server.py
```

### "Database not found"
1. Go to Settings in admin dashboard
2. Verify Database Path points to your seedlinedata.db
3. Click Save if you make changes

### Scraper doesn't run
- Check that Python is installed and in PATH
- Verify scraper file exists (shown in Settings)
- Try running manually from command line to see errors

## Version History

- **v3.9** - File structure reorganization, persistent Seedline_Data folder
- **v3.5** - CMD window for scrapers, GA Events scraper in admin UI
- **v3.4** - Scraper settings modal, Files & Folders page
- **v3.3** - User persistence, badge system
- **v3.9** - Fixed scraper path detection, bundled scrapers used as fallback
- **v3.9** - Fixed team ranker detection (v39b), fixed scraper status for CMD windows, fixed GA Events age group handling (uses team name birth year, calculates correct birth year from U-age based on event date)
