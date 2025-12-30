"""Analyze how game team names match with teams table"""
import sqlite3

db_path = 'seedlinedata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all unique team names from games
cursor.execute("""
    SELECT DISTINCT home_team FROM games WHERE home_team IS NOT NULL AND home_team != ''
    UNION
    SELECT DISTINCT away_team FROM games WHERE away_team IS NOT NULL AND away_team != ''
""")
game_teams = set(row[0] for row in cursor.fetchall())
print(f"Unique team names in games: {len(game_teams):,}")

# Get all team names from teams table
cursor.execute("SELECT DISTINCT team_name FROM teams WHERE team_name IS NOT NULL")
db_teams = set(row[0] for row in cursor.fetchall())
print(f"Unique team names in teams table: {len(db_teams):,}")

# Check exact matches
exact_matches = game_teams & db_teams
print(f"Exact matches: {len(exact_matches):,} ({100*len(exact_matches)/len(game_teams):.1f}%)")

# Non-matching game teams
no_match = game_teams - db_teams
print(f"Game teams NOT in teams table: {len(no_match):,}")

# Sample non-matching teams
print("\n=== Sample game teams NOT in teams table (first 30): ===")
for team in sorted(no_match)[:30]:
    print(f"  {team}")

# Check if teams table has addresses for the exact matches
cursor.execute("""
    SELECT team_name, city, state, street_address
    FROM teams
    WHERE team_name IN ({})
""".format(','.join(['?' for _ in list(exact_matches)[:500]])), list(exact_matches)[:500])
matches_with_city = sum(1 for row in cursor.fetchall() if row[1] and row[1] != '')

print(f"\n=== Of exact matches, how many have city data? ===")
# Recalculate properly
cursor.execute("SELECT team_name, city FROM teams WHERE city IS NOT NULL AND city != ''")
teams_with_city = set(row[0] for row in cursor.fetchall())
matches_with_city = game_teams & teams_with_city
print(f"Game teams that match AND have city: {len(matches_with_city):,}")
print(f"Game teams that match but NO city: {len(exact_matches - matches_with_city):,}")

# What are the teams from games with no match in teams table?
# Check by league
print("\n=== No-match teams breakdown by checking games table: ===")
no_match_list = list(no_match)[:500]  # Sample
cursor.execute("""
    SELECT DISTINCT league, COUNT(*) as cnt
    FROM games
    WHERE home_team IN ({})
    GROUP BY league
    ORDER BY cnt DESC
""".format(','.join(['?' for _ in no_match_list])), no_match_list)
for row in cursor.fetchall():
    print(f"  {str(row[0])[:30]:30} | {row[1]} unmatched teams")

conn.close()
