#!/usr/bin/env python3
"""Add SincSports tournaments to tracking CSV"""

import csv
import os
from datetime import datetime

TOURNAMENT_FILE = "tournament_urls_v2.csv"

# SincSports tournaments found from web search
SINCSPORTS_TOURNAMENTS = [
    # December 2025
    {"name": "Winter Cup 2025", "dates": "December 20, 2025", "state": "CA", "event_id": "TT4577", "status": "found"},
    {"name": "Winter Futsal Challenge", "dates": "December 20, 2025", "state": "AL", "event_id": "SWISG2", "status": "found"},
    {"name": "3v3 Holiday Cup", "dates": "December 29, 2025", "state": "IL", "event_id": "3V3HOLCUP2", "status": "found"},

    # January 2026
    {"name": "Beat The Freeze", "dates": "January 2, 2026", "state": "LA", "event_id": "BEATTHEFR", "status": "found"},
    {"name": "5v5 Raptors Indoor Cup", "dates": "January 3, 2026", "state": "Unknown", "event_id": "5V5RAPTORS", "status": "found"},
    {"name": "Rush Union Winter 7v7 League", "dates": "January 7, 2026", "state": "Unknown", "event_id": "RUSHUWL7", "status": "found"},
    {"name": "Kirkwood Cobra 5v5 Challenge", "dates": "January 9, 2026", "state": "TN", "event_id": "KIRKCO", "status": "found"},
    {"name": "Showcase Tennessee", "dates": "January 9, 2026", "state": "TN", "event_id": "SHOWTN", "status": "found"},
    {"name": "New Years Cup", "dates": "January 10, 2026", "state": "Unknown", "event_id": "NEWYC", "status": "found"},
    {"name": "Valor FC Champions Classic", "dates": "January 16, 2026", "state": "Unknown", "event_id": "WINCHCL", "status": "found"},
    {"name": "JASA Hammerheads Indoor Tournament", "dates": "January 17, 2026", "state": "Unknown", "event_id": "JASAHHI", "status": "found"},
    {"name": "Southeast College Showcase Boys", "dates": "January 17, 2026", "state": "TN", "event_id": "FCACSM", "status": "found"},
    {"name": "Strikers Invitational", "dates": "January 17, 2026", "state": "NC", "event_id": "INNAUG", "status": "found"},
    {"name": "Chris Martin Memorial 4v4", "dates": "January 18, 2026", "state": "NC", "event_id": "CMARTIN", "status": "found"},
    {"name": "TSC College Showcase", "dates": "January 23, 2026", "state": "TN", "event_id": "TSCCS", "status": "found"},
    {"name": "All-In Play Sports 4v4 Championships", "dates": "January 24, 2026", "state": "Unknown", "event_id": "AIP1", "status": "found"},
    {"name": "Bojangles Beast of the East", "dates": "January 24, 2026", "state": "Unknown", "event_id": "TRN159", "status": "found"},
    {"name": "Kick 4 A Cause", "dates": "January 24, 2026", "state": "NC", "event_id": "NCFCK4AC", "status": "found"},
    {"name": "Puma Kings Cup - Girls", "dates": "January 24, 2026", "state": "NC", "event_id": "CSAADIG", "status": "found"},
    {"name": "Riverside Spring Kickoff", "dates": "January 24, 2026", "state": "NC", "event_id": "ABYSA1", "status": "found"},
    {"name": "FC Charleston Pre-Season Invitational", "dates": "January 30, 2026", "state": "SC", "event_id": "FCCPSI", "status": "found"},
    {"name": "Gray Massey Memorial Open Cup", "dates": "January 30, 2026", "state": "MS", "event_id": "AFCOPC", "status": "found"},
    {"name": "Lexington Soccer Academy Cup", "dates": "January 30, 2026", "state": "SC", "event_id": "TZ1482", "status": "found"},
    {"name": "Turf Cup II", "dates": "January 30, 2026", "state": "TN", "event_id": "TURF2", "status": "found"},
    {"name": "2026 Commanders Cup SincSports", "dates": "January 31, 2026", "state": "NC", "event_id": "COMCUP", "status": "found"},
    {"name": "AFC Lightning Winter 5V5 Festival", "dates": "January 31, 2026", "state": "NC", "event_id": "WIN3V3F", "status": "found"},
    {"name": "Puma Kings Cup - Boys", "dates": "January 31, 2026", "state": "NC", "event_id": "CSAADI", "status": "found"},
    {"name": "Rising Stars Winter Elite 5v5", "dates": "January 31, 2026", "state": "GA", "event_id": "RISING52", "status": "found"},
    {"name": "Savannah United Elite Cup", "dates": "January 31, 2026", "state": "GA", "event_id": "SUNELITC", "status": "found"},

    # More from common SincSports tournaments
    {"name": "Battleground Tournament of Champions", "dates": "TBD 2026", "state": "GA", "event_id": "TZ0885", "status": "found"},
    {"name": "Alabama Soccer Showdown", "dates": "TBD 2026", "state": "AL", "event_id": "FARSS", "status": "found"},
    {"name": "NC FC Youth Recreation Cup", "dates": "May 17-18, 2025", "state": "NC", "event_id": "NCFCRC", "status": "found"},
]


def load_existing_tournaments():
    """Load existing tournaments and get existing event IDs"""
    existing = []
    existing_ids = set()
    existing_names = set()

    if os.path.exists(TOURNAMENT_FILE):
        with open(TOURNAMENT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.append(row)
                if row.get('event_id'):
                    existing_ids.add(row['event_id'])
                if row.get('name'):
                    existing_names.add(row['name'].lower())

    return existing, existing_ids, existing_names


def add_tournaments():
    """Add new tournaments to the tracking file"""
    existing, existing_ids, existing_names = load_existing_tournaments()

    print(f"Loaded {len(existing)} existing tournaments")
    print(f"Checking {len(SINCSPORTS_TOURNAMENTS)} SincSports tournaments...")

    added = 0
    for t in SINCSPORTS_TOURNAMENTS:
        # Skip if event ID exists
        if t['event_id'] in existing_ids:
            continue
        # Skip if similar name exists
        if t['name'].lower() in existing_names:
            continue

        new_row = {
            'name': t['name'],
            'dates': t['dates'],
            'state': t['state'],
            'club': '',
            'age_groups': '',
            'website_url': '',
            'schedule_url': f"https://soccer.sincsports.com/ttschedule.aspx?tid={t['event_id']}",
            'schedule_platform': 'sincsports',
            'event_id': t['event_id'],
            'status': t['status'],
            'notes': f"SincSports - Added {datetime.now().strftime('%Y-%m-%d')}"
        }
        existing.append(new_row)
        existing_ids.add(t['event_id'])
        added += 1
        print(f"  + {t['name']} ({t['state']})")

    if added > 0:
        fieldnames = ['name', 'dates', 'state', 'club', 'age_groups',
                      'website_url', 'schedule_url', 'schedule_platform',
                      'event_id', 'status', 'notes']

        with open(TOURNAMENT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing)

        print(f"\nAdded {added} new tournaments")
        print(f"Total tournaments: {len(existing)}")
    else:
        print("\nNo new tournaments to add")


if __name__ == "__main__":
    add_tournaments()
