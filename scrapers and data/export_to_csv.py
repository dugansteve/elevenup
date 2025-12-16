#!/usr/bin/env python3
"""
DATABASE TO CSV EXPORT SCRIPT
=============================

Exports seedlinedata.db tables to CSV files.

Usage:
    python export_to_csv.py seedlinedata.db                    # Export all tables
    python export_to_csv.py seedlinedata.db --tables games     # Export only games
    python export_to_csv.py seedlinedata.db --tables games teams  # Export games and teams
    python export_to_csv.py seedlinedata.db --output ./exports    # Custom output directory

Output files:
    - games.csv
    - teams.csv
    - players.csv
    - discovered_urls.csv
"""

import sqlite3
import csv
import os
import sys
import argparse
from datetime import datetime


def export_table_to_csv(conn, table_name, output_path):
    """Export a single table to CSV"""
    cursor = conn.cursor()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Get all data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)  # Header
        writer.writerows(rows)
    
    return len(rows)


def get_table_stats(conn, table_name):
    """Get basic stats for a table"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    return count


def main():
    parser = argparse.ArgumentParser(description='Export database tables to CSV')
    parser.add_argument('database', help='Path to SQLite database file')
    parser.add_argument('--tables', nargs='+', 
                        choices=['games', 'teams', 'players', 'discovered_urls', 'all'],
                        default=['all'],
                        help='Tables to export (default: all)')
    parser.add_argument('--output', '-o', default='.',
                        help='Output directory (default: current directory)')
    
    args = parser.parse_args()
    
    # Validate database exists
    if not os.path.exists(args.database):
        print(f"❌ Database not found: {args.database}")
        sys.exit(1)
    
    # Create output directory if needed
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"📁 Created output directory: {args.output}")
    
    # Connect to database
    conn = sqlite3.connect(args.database)
    
    print("=" * 60)
    print("DATABASE TO CSV EXPORT")
    print("=" * 60)
    print(f"\nDatabase: {args.database}")
    print(f"Output: {args.output}")
    
    # Determine which tables to export
    all_tables = ['games', 'teams', 'players', 'discovered_urls']
    
    if 'all' in args.tables:
        tables_to_export = all_tables
    else:
        tables_to_export = args.tables
    
    print(f"Tables: {', '.join(tables_to_export)}")
    print("\n" + "-" * 60)
    
    # Export each table
    total_rows = 0
    for table in tables_to_export:
        output_path = os.path.join(args.output, f"{table}.csv")
        
        try:
            row_count = export_table_to_csv(conn, table, output_path)
            file_size = os.path.getsize(output_path)
            
            # Format file size
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024*1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} bytes"
            
            print(f"✅ {table}.csv: {row_count:,} rows ({size_str})")
            total_rows += row_count
            
        except Exception as e:
            print(f"❌ {table}: Error - {e}")
    
    conn.close()
    
    print("-" * 60)
    print(f"\n✅ Export complete: {total_rows:,} total rows")
    print(f"📁 Files saved to: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
