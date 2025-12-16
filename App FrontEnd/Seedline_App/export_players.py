#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_players.py - Export players from database to React app JSON format

This script reads players from the SQLite database and exports them
to a JSON file that the React frontend can consume.

Usage:
    python export_players.py --db path/to/database.db --react path/to/react/app
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def export_players(db_path: Path, react_path: Path) -> dict:
    """
    Export all players from the database to a JSON file for the React app.
    
    Args:
        db_path: Path to the SQLite database
        react_path: Path to the React app root folder
        
    Returns:
        dict with success status and details
    """
    if not db_path.exists():
        return {"success": False, "error": f"Database not found: {db_path}"}
    
    # Output path
    output_path = react_path / "public" / "players_for_react.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if players table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
        if not cursor.fetchone():
            conn.close()
            # Write empty players file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"players": [], "exportedAt": None, "totalCount": 0}, f, indent=2)
            return {"success": True, "count": 0, "message": "No players table found, exported empty file"}
        
        # Get all players
        cursor.execute("""
            SELECT 
                rowid,
                player_name,
                team_name,
                team_url,
                club,
                position,
                number,
                grad_year,
                state,
                league,
                age_group
            FROM players
            ORDER BY player_name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to React-friendly format
        players = []
        for row in rows:
            player = {
                "id": row["rowid"],
                "name": row["player_name"] or "",
                "teamName": row["team_name"],
                "teamUrl": row["team_url"],
                "club": row["club"] or "",
                "position": row["position"],
                "number": row["number"],
                "gradYear": str(row["grad_year"]) if row["grad_year"] else None,
                "state": row["state"],
                "league": row["league"],
                "ageGroup": row["age_group"],
                "source": "database"
            }
            players.append(player)
        
        # Write to JSON file
        from datetime import datetime
        output_data = {
            "players": players,
            "exportedAt": datetime.now().isoformat(),
            "totalCount": len(players)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully exported {len(players)} players to {output_path}")
        return {"success": True, "count": len(players), "path": str(output_path)}
        
    except sqlite3.OperationalError as e:
        # Handle case where columns might be different
        error_msg = str(e)
        if "no such column" in error_msg:
            # Try with a more flexible query
            return export_players_flexible(db_path, react_path)
        return {"success": False, "error": f"Database error: {error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def export_players_flexible(db_path: Path, react_path: Path) -> dict:
    """
    Fallback export that dynamically reads whatever columns exist in the players table.
    """
    output_path = react_path / "public" / "players_for_react.json"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get column names
        cursor.execute("PRAGMA table_info(players)")
        columns_info = cursor.fetchall()
        db_columns = [col[1] for col in columns_info]
        
        # Get all players
        cursor.execute(f"SELECT rowid, * FROM players ORDER BY player_name" 
                      if "player_name" in db_columns 
                      else "SELECT rowid, * FROM players")
        
        rows = cursor.fetchall()
        result_columns = ["rowid"] + db_columns
        conn.close()
        
        # Column mapping from database names to React format
        column_map = {
            "player_name": "name",
            "team_name": "teamName", 
            "team_url": "teamUrl",
            "grad_year": "gradYear",
            "age_group": "ageGroup",
            # Direct mappings
            "club": "club",
            "position": "position",
            "number": "number",
            "state": "state",
            "league": "league",
            "id": "id"
        }
        
        players = []
        for row in rows:
            row_dict = dict(zip(result_columns, row))
            
            player = {"id": row_dict.get("rowid"), "source": "database"}
            
            for db_col, react_col in column_map.items():
                if db_col in row_dict:
                    value = row_dict[db_col]
                    # Convert grad_year to string if it exists
                    if db_col == "grad_year" and value is not None:
                        value = str(value)
                    player[react_col] = value
            
            # Ensure required fields exist (even as null)
            for field in ["name", "teamName", "teamUrl", "club", "position", 
                         "number", "gradYear", "state", "league", "ageGroup"]:
                if field not in player:
                    player[field] = None
                    
            players.append(player)
        
        # Write to JSON file
        from datetime import datetime
        output_data = {
            "players": players,
            "exportedAt": datetime.now().isoformat(),
            "totalCount": len(players)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully exported {len(players)} players to {output_path}")
        return {"success": True, "count": len(players), "path": str(output_path)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Export players to React app JSON")
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--react", required=True, help="Path to React app folder")
    
    args = parser.parse_args()
    
    db_path = Path(args.db)
    react_path = Path(args.react)
    
    result = export_players(db_path, react_path)
    
    if result["success"]:
        print(f"Export complete: {result.get('count', 0)} players")
        sys.exit(0)
    else:
        print(f"Export failed: {result.get('error', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
