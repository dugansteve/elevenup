#!/usr/bin/env python3
"""Find tournament URLs where age group is missing"""
import sqlite3

DB = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db"
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== SAMPLE URLS WITH MISSING AGE GROUP ===")
print()

c.execute("""
    SELECT DISTINCT source_url, home_team, away_team, home_score, away_score
    FROM games
    WHERE league = 'Tournament'
    AND (age_group IS NULL OR age_group = '')
    AND source_url IS NOT NULL AND source_url <> ''
    ORDER BY RANDOM()
    LIMIT 15
""")

for row in c.fetchall():
    url, home, away, hs, as_ = row
    print(f"{home[:45]} vs {away[:45]}")
    print(f"  Score: {hs}-{as_}")
    print(f"  URL: {url}")
    print()

conn.close()
