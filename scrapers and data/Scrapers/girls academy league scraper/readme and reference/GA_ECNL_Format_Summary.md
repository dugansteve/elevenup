# GA Scraper - ECNL-Compatible Format

## Summary of Changes

Your GA scraper has been updated to match the ECNL data format so you can eventually merge the datasets.

---

## File Naming

### Database
- **Filename**: `GA_Game_Data.db`
- **Behavior**: Single file that gets updated with each run
- **Table**: `ga_games` (matches ECNL's `ecnl_games` table)

### CSV Files
- **Filename Pattern**: `GA_Game_Data_YYYYMMDD_HHMMSS.csv`
- **Example**: `GA_Game_Data_20241113_143022.csv`
- **Behavior**: New timestamped file created with each run (archive of snapshots)

---

## Database Schema (ECNL-Compatible)

Both ECNL and GA now use the same structure:

| Column       | Type      | Description                              |
|--------------|-----------|------------------------------------------|
| id           | INTEGER   | Auto-increment primary key               |
| game_id      | TEXT      | Unique identifier (e.g., `ga_2025-12-13_Team1_Team2`) |
| age_group    | TEXT      | Age group (G13, G12, G11, etc.)         |
| game_date    | TEXT      | Date in YYYY-MM-DD format               |
| game_time    | TEXT      | Time or "TBD"                           |
| home_team    | TEXT      | Home team name                          |
| away_team    | TEXT      | Away team name                          |
| home_score   | INTEGER   | Home team score (NULL if not played)    |
| away_score   | INTEGER   | Away team score (NULL if not played)    |
| conference   | TEXT      | Conference name                         |
| location     | TEXT      | Game location/venue                     |
| scraped_at   | TIMESTAMP | When the data was scraped               |
| source_url   | TEXT      | URL where data was scraped from         |
| game_status  | TEXT      | "scheduled" or "completed"              |

---

## Key Format Changes

### Old Format → New Format

1. **Team Naming**
   - OLD: `team1_name`, `team2_name`, `team1_score`, `team2_score`
   - NEW: `home_team`, `away_team`, `home_score`, `away_score`

2. **Game Identification**
   - OLD: `external_game_id` (generic)
   - NEW: `game_id` (standardized format)

3. **Date/Time**
   - OLD: Single `game_date` field containing both
   - NEW: Separate `game_date` and `game_time` fields

4. **New Fields Added**
   - `game_status`: Indicates if game is "scheduled" or "completed"
   - `scraped_at`: ISO timestamp of when data was collected
   - `source_url`: Direct link to the source page

5. **Removed Fields**
   - Removed GA-specific internal fields like `team1_external_id`, `team2_external_id`, `event_id`, `league`

---

## Home/Away Team Detection

The scraper now intelligently determines home vs. away teams:

1. **Looks for (H) or (A) markers** in team names
2. **First team listed** is assumed to be home if no markers found
3. Ensures proper home/away assignment for score tracking

---

## Age Group Note

**Important**: GA uses different age group naming than ECNL:
- **GA**: G13 (2013 birth year)
- **ECNL**: U13 (Under 13)

The scraper preserves GA's naming (G13, G12, G11, etc.) but you may want to standardize this when merging datasets:
- G13 = U13
- G12 = U14
- G11 = U15
- G10 = U16
- G09 = U17
- G08/07 = U18/U19

---

## CSV Output Format

The CSV now matches the database structure with these columns:

```
game_id, age_group, game_date, game_time, home_team, away_team, 
home_score, away_score, conference, location, scraped_at, 
source_url, game_status
```

---

## Usage

The scraper works exactly the same way:

```bash
python ga_simple_scraper_v4.py
```

You'll be prompted to select:
1. Age group (13G, 12G, 11G, etc.)
2. Game filter (All, Upcoming, Past, Last 7 days)

**Output**:
- ✅ Updates `GA_Game_Data.db` (persistent database)
- ✅ Creates new `GA_Game_Data_YYYYMMDD_HHMMSS.csv` (timestamped snapshot)

---

## Merging GA and ECNL Data

Since both datasets now use the same structure, you can merge them by:

1. **Combining databases**:
   ```sql
   -- Copy GA games to ECNL database
   INSERT INTO ecnl_games SELECT * FROM ga_games WHERE game_id NOT IN (SELECT game_id FROM ecnl_games);
   ```

2. **Combining CSV files**:
   ```python
   import pandas as pd
   ga_df = pd.read_csv('GA_Game_Data_20241113_143022.csv')
   ecnl_df = pd.read_csv('ECNL_Game_Data_20241113_143022.csv')
   combined = pd.concat([ga_df, ecnl_df]).drop_duplicates(subset='game_id')
   ```

3. **Don't forget** to standardize age group naming if needed!

---

## Next Steps

✅ Both scrapers now produce the same format  
✅ Ready to merge datasets whenever you want  
✅ Easy to create combined reports/analysis  
✅ Can track both leagues side-by-side
