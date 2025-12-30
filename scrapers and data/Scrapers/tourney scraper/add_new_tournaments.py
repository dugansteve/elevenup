#!/usr/bin/env python3
"""
Add newly discovered tournaments to tracking CSV
"""

import csv
import os
from datetime import datetime

TOURNAMENT_FILE = "tournament_urls_v2.csv"

# New tournaments discovered from GotSport - December 2025 / January 2026
NEW_TOURNAMENTS = [
    # California tournaments
    {"name": "Copa Toque 2025", "dates": "December 19-21, 2025", "state": "CA", "event_id": "48292", "schedule_platform": "gotsport", "status": "found"},
    {"name": "GOAT Soccer Cup 2nd Edition", "dates": "December 19-21, 2025", "state": "CA", "event_id": "46442", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Christmas Youth Super Cup 2025", "dates": "December 20-21, 2025", "state": "CA", "event_id": "42706", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Corona Winter Cup", "dates": "December 20-21, 2025", "state": "CA", "event_id": "49550", "schedule_platform": "gotsport", "status": "found"},
    {"name": "San Jose 5v5 Showdown", "dates": "December 20-21, 2025", "state": "CA", "event_id": "49724", "schedule_platform": "gotsport", "status": "found"},
    {"name": "San Jose Cup 5v5", "dates": "December 20-21, 2025", "state": "CA", "event_id": "49931", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Scripps Ranch Recreational All Star 2025", "dates": "December 20-21, 2025", "state": "CA", "event_id": "43218", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Spartans FC Holiday Tournament", "dates": "December 20-21, 2025", "state": "CA", "event_id": "49719", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Winter 2025 CA Community Shield 7v7", "dates": "December 27-28, 2025", "state": "CA", "event_id": "49681", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Hawks Invitational", "dates": "December 29-31, 2025", "state": "CA", "event_id": "44366", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Cal South Winter Classic", "dates": "January 3-4, 2026", "state": "CA", "event_id": "48936", "schedule_platform": "gotsport", "status": "found"},

    # Texas tournaments
    {"name": "22nd Annual Winter Storm 5v5 Cup", "dates": "December 20-21, 2025", "state": "TX", "event_id": "49513", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Austin Lights Futsal Festival", "dates": "December 28-30, 2025", "state": "TX", "event_id": "50143", "schedule_platform": "gotsport", "status": "found"},
    {"name": "9th Annual Winter Junior Champions Cup 2026", "dates": "January 2-4, 2026", "state": "TX", "event_id": "49487", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Copa De Austin", "dates": "January 10-11, 2026", "state": "TX", "event_id": "50377", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Solar Winter Cup 2026", "dates": "January 10-11, 2026", "state": "TX", "event_id": "49863", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Outlaw Cup", "dates": "January 16-18, 2026", "state": "TX", "event_id": "41719", "schedule_platform": "gotsport", "status": "found"},
    {"name": "U90C Winter Classic Showcase 2026", "dates": "January 16-18, 2026", "state": "TX", "event_id": "46057", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Bobby Rhine Invitational 2026", "dates": "January 17-19, 2026", "state": "TX", "event_id": "49375", "schedule_platform": "gotsport", "status": "found"},

    # Florida tournaments
    {"name": "IMG Cup Boys Invitational 2025", "dates": "December 19-21, 2025", "state": "FL", "event_id": "45941", "schedule_platform": "gotsport", "status": "found"},
    {"name": "8TH ANNUAL BAZOOKA SOCCER HOLIDAY CUP", "dates": "December 20-21, 2025", "state": "FL", "event_id": "45874", "schedule_platform": "gotsport", "status": "found"},
    {"name": "The 2025 Cape Coral Cup", "dates": "December 20-21, 2025", "state": "FL", "event_id": "46492", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2025 Florida Sun Classic", "dates": "December 26-28, 2025", "state": "FL", "event_id": "46185", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2025 Disney Young Legends Soccer Tournament", "dates": "December 28-30, 2025", "state": "FL", "event_id": "44507", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Orlando Cup 2026", "dates": "January 9-11, 2026", "state": "FL", "event_id": "46351", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Paradise Cup", "dates": "January 9-11, 2026", "state": "FL", "event_id": "46472", "schedule_platform": "gotsport", "status": "found"},

    # Arizona tournaments
    {"name": "2026 ODP Far West Championships", "dates": "January 2-5, 2026", "state": "AZ", "event_id": "45141", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Inside Classic Winter 2026", "dates": "January 2-4, 2026", "state": "AZ", "event_id": "44162", "schedule_platform": "gotsport", "status": "found"},
    {"name": "CCV Stars Champions Cup 2026", "dates": "January 9-11, 2026", "state": "AZ", "event_id": "41699", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Rated Cup", "dates": "January 16-18, 2026", "state": "AZ", "event_id": "45222", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Fort Lowell Shootout 2026", "dates": "January 16-18, 2026", "state": "AZ", "event_id": "46091", "schedule_platform": "gotsport", "status": "found"},
    {"name": "North Scottsdale Sandsharks Invitational 2026", "dates": "January 16-18, 2026", "state": "AZ", "event_id": "46006", "schedule_platform": "gotsport", "status": "found"},

    # Other states
    {"name": "The Open 2025 Scottsdale", "dates": "December 5-7, 2025", "state": "AZ", "event_id": "8d8956d5d8", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2025 Bluegrass Futsal Cup", "dates": "December 19-21, 2025", "state": "KY", "event_id": "49204", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Copa Talento Futsal 2025", "dates": "December 19-21, 2025", "state": "VA", "event_id": "49187", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Philadelphia Union Futsal Cup", "dates": "December 20-21, 2025", "state": "PA", "event_id": "46216", "schedule_platform": "gotsport", "status": "found"},
]


def load_existing_tournaments():
    """Load existing tournaments and get existing event IDs"""
    existing = []
    existing_ids = set()

    if os.path.exists(TOURNAMENT_FILE):
        with open(TOURNAMENT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.append(row)
                if row.get('event_id'):
                    existing_ids.add(row['event_id'])

    return existing, existing_ids


def add_tournaments():
    """Add new tournaments to the tracking file"""
    existing, existing_ids = load_existing_tournaments()

    print(f"Loaded {len(existing)} existing tournaments")
    print(f"Checking {len(NEW_TOURNAMENTS)} new tournaments...")

    added = 0
    for t in NEW_TOURNAMENTS:
        if t['event_id'] not in existing_ids:
            # Format for CSV
            new_row = {
                'name': t['name'],
                'dates': t['dates'],
                'state': t['state'],
                'club': '',
                'age_groups': '',
                'website_url': '',
                'schedule_url': f"https://system.gotsport.com/org_event/events/{t['event_id']}",
                'schedule_platform': t['schedule_platform'],
                'event_id': t['event_id'],
                'status': t['status'],
                'notes': f"Added {datetime.now().strftime('%Y-%m-%d')}"
            }
            existing.append(new_row)
            existing_ids.add(t['event_id'])
            added += 1
            print(f"  + {t['name']} ({t['state']})")

    # Save updated file
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
        print("\nNo new tournaments to add (all already tracked)")


if __name__ == "__main__":
    add_tournaments()
