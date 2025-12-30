"""
Fix MLS NEXT game dates from MM/DD/YY format to YYYY-MM-DD format

MLS NEXT scraper saved dates as "01/11/26" but the ranker expects "2026-01-11"
Uses batch SQL update for efficiency.
"""

import sqlite3

db_path = r'C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current state
cursor.execute("""
    SELECT COUNT(*) FROM games
    WHERE league = 'MLS NEXT' AND game_date LIKE '%/%'
""")
count_mm_dd = cursor.fetchone()[0]
print(f"MLS NEXT games with MM/DD/YY format: {count_mm_dd:,}")

# SQLite can convert MM/DD/YY to YYYY-MM-DD using substr and concatenation
# "01/11/26" -> "2026-01-11"
# substr(game_date, 7, 2) = "26" (year)
# substr(game_date, 1, 2) = "01" (month)
# substr(game_date, 4, 2) = "11" (day)

cursor.execute("""
    UPDATE games
    SET game_date = '20' || substr(game_date, 7, 2) || '-' ||
                    substr(game_date, 1, 2) || '-' ||
                    substr(game_date, 4, 2)
    WHERE league = 'MLS NEXT'
    AND game_date LIKE '__/__/__'
""")

updated = cursor.rowcount
conn.commit()
print(f"Updated {updated:,} games")

# Verify
cursor.execute("""
    SELECT game_date, COUNT(*) as cnt
    FROM games
    WHERE league = 'MLS NEXT'
    GROUP BY game_date
    ORDER BY game_date DESC
    LIMIT 10
""")
print("\nSample dates after fix:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]} games")

# Check remaining issues
cursor.execute("""
    SELECT COUNT(*) FROM games
    WHERE league = 'MLS NEXT' AND game_date NOT LIKE '____-__-__'
""")
remaining = cursor.fetchone()[0]
print(f"\nGames with non-standard dates remaining: {remaining}")

conn.close()
print("\nDone!")
