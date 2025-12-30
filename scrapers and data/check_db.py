import sqlite3
conn = sqlite3.connect(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db")
cur = conn.cursor()

print("Current age_group distribution:")
cur.execute("SELECT age_group, COUNT(*) FROM games GROUP BY age_group ORDER BY COUNT(*) DESC LIMIT 20")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\nGender/age_group mismatches remaining:")
cur.execute("SELECT COUNT(*) FROM games WHERE gender = 'Boys' AND age_group LIKE 'G%'")
print(f"  Boys with G prefix: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM games WHERE gender = 'Girls' AND age_group LIKE 'B%'")
print(f"  Girls with B prefix: {cur.fetchone()[0]}")

print("\nSample teams with 2009 in name:")
cur.execute("SELECT home_team, age_group, gender FROM games WHERE home_team LIKE '%2009%' LIMIT 10")
for row in cur.fetchall():
    print(f"  {row[1]} | {row[2]} | {row[0][:50]}")

conn.close()
