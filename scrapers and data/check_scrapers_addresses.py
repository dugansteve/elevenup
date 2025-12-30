"""Check which scrapers populate address data properly"""
import sqlite3

db_path = 'seedlinedata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Full breakdown by league - all teams regardless of games
print("=== Complete address coverage by league (teams table): ===")
cursor.execute("""
    SELECT league,
           COUNT(*) as total,
           SUM(CASE WHEN city IS NOT NULL AND city != '' THEN 1 ELSE 0 END) as has_city,
           SUM(CASE WHEN street_address IS NOT NULL AND street_address != '' THEN 1 ELSE 0 END) as has_street,
           SUM(CASE WHEN state IS NOT NULL AND state != '' THEN 1 ELSE 0 END) as has_state,
           SUM(CASE WHEN zip_code IS NOT NULL AND zip_code != '' THEN 1 ELSE 0 END) as has_zip
    FROM teams
    GROUP BY league
    ORDER BY COUNT(*) DESC
""")

print(f"{'League':<30} | {'Total':>6} | {'City%':>6} | {'State%':>6} | {'Street%':>7} | {'Zip%':>6}")
print("-" * 85)
for row in cursor.fetchall():
    league, total, has_city, has_street, has_state, has_zip = row
    league_name = str(league)[:29] if league else 'None'
    city_pct = 100*has_city/total if total > 0 else 0
    state_pct = 100*has_state/total if total > 0 else 0
    street_pct = 100*has_street/total if total > 0 else 0
    zip_pct = 100*has_zip/total if total > 0 else 0
    print(f'{league_name:<30} | {total:>6} | {city_pct:>5.1f}% | {state_pct:>5.1f}% | {street_pct:>6.1f}% | {zip_pct:>5.1f}%')

# Sample teams from ECNL without city
print("\n=== Sample ECNL teams without city data: ===")
cursor.execute("""
    SELECT team_name, club_name, state
    FROM teams
    WHERE league = 'ECNL' AND (city IS NULL OR city = '')
    LIMIT 20
""")
for row in cursor.fetchall():
    print(f"  {row[0][:50]:50} | Club: {str(row[1])[:20]:20} | State: {row[2]}")

# Sample NPL teams without city
print("\n=== Sample NPL teams without city data: ===")
cursor.execute("""
    SELECT team_name, club_name, state
    FROM teams
    WHERE league = 'NPL' AND (city IS NULL OR city = '')
    LIMIT 15
""")
for row in cursor.fetchall():
    print(f"  {row[0][:50]:50} | Club: {str(row[1])[:20]:20} | State: {row[2]}")

conn.close()
