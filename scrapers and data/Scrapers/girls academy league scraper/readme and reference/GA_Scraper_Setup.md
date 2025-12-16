# GA Scraper Setup Instructions

## Installation

1. **Install required packages** in your virtual environment:
   ```bash
   pip install requests beautifulsoup4 lxml
   ```

2. **Place your teams file** in the same directory as the scraper:
   - `ga_teams_all_ages_complete.json` (recommended) OR
   - `ga_teams_all_ages_complete.csv`
   
   The scraper will automatically find and use these files.

## Age Group Handling

Your teams file uses **ECNL-style age groups** (U13, U14, U15, etc.), but the scraper menu uses **GA-style** (13G, 12G, 11G, etc.) for user-friendliness.

### Conversion Table:
| You Select (Menu) | Matches in Data File |
|-------------------|---------------------|
| 13G               | U13                 |
| 12G               | U14                 |
| 11G               | U15                 |
| 10G               | U16                 |
| 09G               | U17                 |
| 08/07G            | U18 + U19           |

**The scraper handles this conversion automatically!** 

When you select "13G" from the menu, it will find all U13 teams in your data file. The output will keep the age group format from your source file (U13), which matches the ECNL format for easy merging.

## Running the Scraper

```bash
python ga_simple_scraper_v4.py
```

You'll be prompted to:
1. **Select age group** (13G, 12G, 11G, 10G, 09G, 08/07G, or All)
2. **Select game filter** (All games, Upcoming only, Past only, or Last 7 days)

## Output Files

### Database (Updated Each Run):
- `GA_Game_Data.db` - Single database file with all games

### CSV (New File Each Run):
- `GA_Game_Data_20241113_143022.csv` - Timestamped snapshot

Both outputs use ECNL-compatible format for easy merging with your ECNL data!

## Troubleshooting

### "No GA teams found"
- Make sure `ga_teams_all_ages_complete.json` or `ga_teams_all_ages_complete.csv` is in the same directory as the scraper
- Or place it in a `data/` subdirectory

### "ModuleNotFoundError: No module named 'requests'"
- Run: `pip install requests beautifulsoup4 lxml`

### No teams returned after age group selection
- This is normal if the data file doesn't have that age group
- Try selecting "All age groups" to see what's available
