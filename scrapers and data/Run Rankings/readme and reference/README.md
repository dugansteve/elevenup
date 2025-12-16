# Youth Soccer Team Ranking System 🏆⚽

## What This Program Does

This program analyzes game data from multiple youth soccer leagues (ECNL, GA, etc.) and creates comprehensive team rankings based on performance. 

**Key Features:**
- ⚡ Calculates **Power Scores** where 100 = average team
- 🏅 Uses ELO rating system (like chess rankings) for accuracy
- 📊 Gives ECNL teams a 15% bonus since they face tougher competition
- 📈 Tracks wins, losses, goals, and more
- 📁 Outputs both database (.db) and Excel (.xlsx) files
- 🕐 Includes timestamp in filenames so you can track changes over time

## Quick Start - How to Run

### Method 1: Run the Python script directly
```bash
python3 rank_teams.py
```

### Method 2: Use the simple runner script
```bash
./run_ranking.sh
```

That's it! The program will:
1. Load all your game data
2. Calculate rankings
3. Create output files with today's date and time
4. Show you a summary of the top teams

## Output Files

The program creates two files with timestamps like:
- `Girls Soccer Rankings 2025-11-13 18-43.db` - SQLite database
- `Girls Soccer Rankings 2025-11-13 18-43.xlsx` - Excel file with multiple sheets

### Excel Sheets Include:
- **All Teams** - Complete rankings of all teams
- **ECNL Teams** - Only ECNL teams ranked
- **GA Teams** - Only GA teams ranked  
- **G12, G13, U13-U19** - Rankings by age group
- **Top 100** - The best 100 teams overall

## Understanding Power Scores

**Power Score = 100** means the team is exactly average

- **120+** = Elite team, top 1%
- **110-120** = Excellent team, top 10%
- **100-110** = Above average
- **90-100** = Below average
- **<90** = Struggling team

### Example Top Teams:
```
Rank  Team Name                    League  Age   Power Score
1     MVLA ECNL G12               ECNL    G12   124.50
2     San Diego Surf ECNL G12     ECNL    G12   123.08
3     Tennessee SC ECNL G12       ECNL    G12   122.04
```

## How Rankings Work

1. **Initial Rating**: Every team starts at 1500 ELO points
2. **Game Results**: Teams gain/lose points based on:
   - Win/Loss/Draw
   - Opponent strength (beating good teams = more points)
   - Margin of victory affects future expectations
3. **League Bonus**: ECNL teams get a 15% boost (they're generally stronger)
4. **Power Score**: Ratings are converted so average = 100

### Why ECNL Gets a Bonus
Since ECNL and GA teams rarely play each other, it's hard to compare directly. Based on national trends, ECNL teams are generally stronger, so we give them a 15% boost. This ensures that out of the top 100 teams, about 70-80 are ECNL (reflecting reality).

## Adding New Data Sources

To add a new league (like NPL, DPL, etc.):

1. Get the game data in one of these formats:
   - SQLite database (like ECNL)
   - JSON file (like GA)
   - CSV file

2. Add a new loading function to `rank_teams.py`:
```python
def load_npl_data(self, file_path):
    # Load your data
    # Process games
    # Update team records
```

3. Update the league bonus if needed:
```python
self.league_bonuses = {
    'ECNL': 1.15,
    'GA': 1.0,
    'NPL': 1.05,  # New league
}
```

4. Call your new function in `main()`:
```python
ranker.load_npl_data("path/to/npl_data.db")
```

## Updating Rankings Weekly

Just run the program again! It will:
- Read the latest game data
- Recalculate all rankings
- Create new files with the current timestamp
- Keep old files so you can track changes over time

**Pro tip**: You can compare this week's file to last week's to see which teams are improving!

## Customization Options

### Change the League Bonus
Edit this in `rank_teams.py`:
```python
self.league_bonuses = {
    'ECNL': 1.15,  # Change this number (1.0-1.3 recommended)
    'GA': 1.0,
}
```

### Change How Much Ratings Move Per Game
Edit the K-factor:
```python
self.k_factor = 32  # Higher = ratings change faster (16-64 recommended)
```

### Change Power Score Average
The default is 100 = average. This is set in the `calculate_power_scores()` function.

## Troubleshooting

**Problem**: "No module named 'pandas'"
**Solution**: Install dependencies:
```bash
pip install pandas openpyxl --break-system-packages
```

**Problem**: "File not found"
**Solution**: Update the file paths in `main()` to match where your data is stored

**Problem**: "No teams ranked"
**Solution**: Make sure your game data has completed games with scores

## Technical Details (For the Curious)

**ELO Rating System**: 
- Used in chess, sports, and competitive gaming
- Based on expected vs actual performance
- Naturally accounts for strength of schedule
- Self-correcting over time

**Why 1500 starting rating?**
- Standard in many ELO systems
- Gives room to go up or down
- Math works nicely with 400-point differences

**Why K-factor of 32?**
- Balance between stability and responsiveness
- Higher = rankings change faster
- Lower = more stable, but slower to adapt

## File Structure

```
rank_teams.py          # Main program (you run this)
README.md              # This file
run_ranking.sh         # Quick runner script (optional)

Input files:
- ECNL_Game_Data.db    # ECNL games database
- ga_teams_all_ages_complete.json  # GA teams list

Output directory:
- Girls Soccer Rankings [date] [time].db    # Database output
- Girls Soccer Rankings [date] [time].xlsx  # Excel output
```

## Questions?

The program is designed for "vibe coding" - you don't need to be a programmer! If something doesn't make sense:
1. Check this README
2. Look at the comments in rank_teams.py
3. The code is organized in logical sections with clear names

## Future Improvements (Ideas)

- [ ] Add game importance weighting (tournament games worth more?)
- [ ] Include head-to-head records
- [ ] Add trend indicators (↑↓) for teams moving up/down
- [ ] Export to website/HTML format
- [ ] Add prediction feature (who would win Team A vs Team B?)
- [ ] Include regional rankings (Southeast, West Coast, etc.)

---

**Created**: November 2025  
**Version**: 1.0  
**Purpose**: Help youth soccer teams, parents, and coaches understand team rankings across multiple leagues
