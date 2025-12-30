#!/usr/bin/env python3
"""Check address data in backup vs current database"""

import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BACKUP_DB = SCRIPT_DIR / 'seedlinedata_backup_20251217_144015.db'
CURRENT_DB = SCRIPT_DIR / 'seedlinedata.db'

def check_db(db_path, label):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print(f"\n{label}:")
    print("-" * 70)

    c.execute("""
        SELECT league,
            COUNT(*) as total,
            SUM(CASE WHEN city IS NOT NULL AND city <> '' THEN 1 ELSE 0 END) as has_city,
            SUM(CASE WHEN street_address IS NOT NULL AND street_address <> '' THEN 1 ELSE 0 END) as has_street,
            SUM(CASE WHEN state IS NOT NULL AND state <> '' THEN 1 ELSE 0 END) as has_state
        FROM teams
        WHERE league IN ('ECNL', 'ECNL RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT')
        GROUP BY league
        ORDER BY total DESC
    """)

    print(f"{'League':15} | {'Total':>6} | {'State':>6} | {'City':>6} | {'Street':>6}")
    print("-" * 70)
    for row in c.fetchall():
        league, total, city, street, state = row
        print(f"{league:15} | {total:6} | {state:6} | {city:6} | {street:6}")

    conn.close()

print("=" * 70)
print("ADDRESS DATA COMPARISON")
print("=" * 70)

check_db(BACKUP_DB, "Backup (Dec 17, 2025)")
check_db(CURRENT_DB, "Current Database")
