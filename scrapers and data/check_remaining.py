import sqlite3
conn = sqlite3.connect(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db")
cur = conn.cursor()

print("Teams with '2009' in name but NOT G09/B09 age_group:")
cur.execute("""
    SELECT DISTINCT home_team, age_group, gender
    FROM games
    WHERE home_team LIKE '%2009%'
    AND age_group NOT LIKE '%09%'
    LIMIT 20
""")
for row in cur.fetchall():
    print(f"  {row[1]} | {row[2]} | {row[0][:55]}")

print("\nCount of remaining mismatches in database:")
cur.execute("""
    SELECT COUNT(*) FROM games
    WHERE (home_team LIKE '%2009%' AND age_group NOT LIKE '%09%')
       OR (home_team LIKE '%2010%' AND age_group NOT LIKE '%10%')
       OR (home_team LIKE '%2011%' AND age_group NOT LIKE '%11%')
       OR (home_team LIKE '%2012%' AND age_group NOT LIKE '%12%')
       OR (home_team LIKE '%2013%' AND age_group NOT LIKE '%13%')
""")
print(f"  {cur.fetchone()[0]} games still have mismatched age_group")

conn.close()
