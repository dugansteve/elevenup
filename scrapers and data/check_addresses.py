"""Check address coverage in the database"""
import sqlite3

db_path = 'seedlinedata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count teams and address coverage
cursor.execute('SELECT COUNT(*) FROM teams')
total = cursor.fetchone()[0]
print(f'Total teams in DB: {total:,}')

cursor.execute("SELECT COUNT(*) FROM teams WHERE city IS NOT NULL AND city != ''")
has_city = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM teams WHERE state IS NOT NULL AND state != ''")
has_state = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM teams WHERE street_address IS NOT NULL AND street_address != ''")
has_street = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM teams WHERE zip_code IS NOT NULL AND zip_code != ''")
has_zip = cursor.fetchone()[0]

print(f'Has city: {has_city:,} ({100*has_city/total:.1f}%)')
print(f'Has state: {has_state:,} ({100*has_state/total:.1f}%)')
print(f'Has street: {has_street:,} ({100*has_street/total:.1f}%)')
print(f'Has zip: {has_zip:,} ({100*has_zip/total:.1f}%)')

# By league
print('\n=== Address coverage by league: ===')
cursor.execute("""
    SELECT league,
           COUNT(*) as total,
           SUM(CASE WHEN city IS NOT NULL AND city != '' THEN 1 ELSE 0 END) as has_city,
           SUM(CASE WHEN street_address IS NOT NULL AND street_address != '' THEN 1 ELSE 0 END) as has_street
    FROM teams
    GROUP BY league
    ORDER BY COUNT(*) DESC
    LIMIT 20
""")
for row in cursor.fetchall():
    league, total, has_city, has_street = row
    city_pct = 100*has_city/total if total > 0 else 0
    street_pct = 100*has_street/total if total > 0 else 0
    print(f'  {str(league)[:25]:25} | {total:5} teams | City: {city_pct:5.1f}% | Street: {street_pct:5.1f}%')

# Sample teams without city
print('\n=== Sample teams without city (first 15): ===')
cursor.execute("""
    SELECT DISTINCT team_name, club_name, league, city, state
    FROM teams
    WHERE city IS NULL OR city = ''
    LIMIT 15
""")
for row in cursor.fetchall():
    team_name = row[0][:45] if row[0] else 'N/A'
    club_name = row[1][:20] if row[1] else 'N/A'
    league = row[2] if row[2] else 'N/A'
    print(f'  {team_name:45} | Club: {club_name:20} | League: {league}')

conn.close()
