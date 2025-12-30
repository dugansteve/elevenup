#!/usr/bin/env python3
"""Quick data quality check for tournament games"""
import sqlite3

DB = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
conn = sqlite3.connect(DB)
c = conn.cursor()

# Check age groups that ARE captured
print("=== AGE GROUPS CAPTURED ===")
c.execute("""
    SELECT age_group, COUNT(*) as cnt
    FROM games
    WHERE league = 'Tournament' AND age_group IS NOT NULL AND age_group <> ''
    GROUP BY age_group
    ORDER BY cnt DESC
    LIMIT 20
""")
for row in c.fetchall():
    print(f"  {row[0]:10} {row[1]:,} games")

# Sample high-score games
print("\n=== HIGH SCORE GAMES (>15) ===")
c.execute("""
    SELECT home_team, away_team, home_score, away_score, game_date
    FROM games
    WHERE league = 'Tournament' AND (home_score > 15 OR away_score > 15)
    LIMIT 10
""")
for row in c.fetchall():
    print(f"  {row[0][:35]} vs {row[1][:35]} | {row[2]}-{row[3]}")

# Check self-play
print("\n=== SELF-PLAY GAMES ===")
c.execute("""
    SELECT COUNT(*) FROM games
    WHERE league = 'Tournament' AND LOWER(home_team) = LOWER(away_team)
""")
print(f"  Self-play games: {c.fetchone()[0]}")

# Sample team names
print("\n=== SAMPLE TEAM NAMES ===")
c.execute("""
    SELECT DISTINCT home_team
    FROM games
    WHERE league = 'Tournament'
    ORDER BY RANDOM()
    LIMIT 15
""")
for row in c.fetchall():
    print(f"  {row[0]}")

# Date formats
print("\n=== DATE FORMAT SAMPLES ===")
c.execute("""
    SELECT game_date, COUNT(*) as cnt
    FROM games
    WHERE league = 'Tournament' AND game_date IS NOT NULL AND game_date <> ''
    GROUP BY game_date
    ORDER BY cnt DESC
    LIMIT 15
""")
for row in c.fetchall():
    print(f"  {row[0]:25} - {row[1]:,} games")

conn.close()
