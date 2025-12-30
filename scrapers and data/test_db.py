import sqlite3
print("Connecting to database...")
conn = sqlite3.connect(r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\seedlinedata.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM games")
count = cur.fetchone()[0]
print(f"Total games: {count}")
conn.close()
print("Done!")
