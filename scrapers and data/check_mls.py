import sqlite3
import pandas as pd

conn = sqlite3.connect(r'C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db')

# Load games like the ranker does
query = """
    SELECT game_id, game_date, home_team, away_team, home_score, away_score,
           age_group, gender, league, conference
    FROM games
    WHERE home_score IS NOT NULL AND away_score IS NOT NULL
      AND (age_group LIKE 'G%' OR age_group LIKE 'U%' OR age_group LIKE 'B%')
"""
games_df = pd.read_sql_query(query, conn)
print(f"Total games loaded: {len(games_df):,}")

# Check MLS NEXT games
mls_games = games_df[games_df['league'] == 'MLS NEXT']
print(f"\n=== MLS NEXT games after initial load ===")
print(f"MLS NEXT games: {len(mls_games):,}")

# Check league distribution
print(f"\n=== League distribution ===")
for league, count in games_df['league'].value_counts().head(20).items():
    print(f"  {league}: {count:,}")

# Clean up scores like the ranker does
games_df['home_score'] = pd.to_numeric(games_df['home_score'], errors='coerce').fillna(0).astype(int)
games_df['away_score'] = pd.to_numeric(games_df['away_score'], errors='coerce').fillna(0).astype(int)

# Create the same dedup key as the ranker
def make_game_key(row):
    teams = sorted([str(row['home_team']).lower().strip(), str(row['away_team']).lower().strip()])
    scores = sorted([int(row['home_score']), int(row['away_score'])])
    return f"{row['game_date']}_{teams[0]}_{teams[1]}_{scores[0]}_{scores[1]}"

games_df['game_key'] = games_df.apply(make_game_key, axis=1)

# Find MLS NEXT games that have duplicates in other leagues
mls_keys = set(games_df[games_df['league'] == 'MLS NEXT']['game_key'])
other_keys = set(games_df[games_df['league'] != 'MLS NEXT']['game_key'])
overlap = mls_keys & other_keys

print(f"\n=== Duplicate Key Analysis ===")
print(f"MLS NEXT unique game keys: {len(mls_keys):,}")
print(f"Other leagues unique keys: {len(other_keys):,}")
print(f"Overlapping keys (will lose MLS NEXT): {len(overlap):,}")

if overlap:
    print(f"\n=== Sample overlapping games ===")
    overlap_list = list(overlap)[:5]
    for key in overlap_list:
        matches = games_df[games_df['game_key'] == key][['home_team', 'away_team', 'game_date', 'home_score', 'away_score', 'league']]
        print(f"\nKey: {key}")
        for _, row in matches.iterrows():
            print(f"  {row['league']}: {row['home_team']} vs {row['away_team']} ({row['home_score']}-{row['away_score']}) on {row['game_date']}")

# After dedup, what remains?
games_df_dedup = games_df.drop_duplicates(subset='game_key', keep='first')
print(f"\n=== After deduplication ===")
print(f"Total games: {len(games_df_dedup):,}")
mls_after = games_df_dedup[games_df_dedup['league'] == 'MLS NEXT']
print(f"MLS NEXT games remaining: {len(mls_after):,}")

conn.close()
