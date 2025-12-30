#!/usr/bin/env python3
"""Add more discovered tournaments to tracking CSV"""

import csv
import os
from datetime import datetime

TOURNAMENT_FILE = "tournament_urls_v2.csv"

# More tournaments discovered from GotSport
MORE_TOURNAMENTS = [
    # North Carolina
    {"name": "Commanders Cup 2026", "dates": "January 31-February 1, 2026", "state": "NC", "event_id": "42320", "schedule_platform": "gotsport", "status": "found"},
    {"name": "GA Spring Showcase Bryan Park", "dates": "April 9-13, 2026", "state": "NC", "event_id": "47823", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 NC Rush Triad Beat the Heat", "dates": "April 11-12, 2026", "state": "NC", "event_id": "44183", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Aspire East Regional U13-19", "dates": "April 16-20, 2026", "state": "NC", "event_id": "47898", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Zoo City Summer Classic", "dates": "May 30-31, 2026", "state": "NC", "event_id": "50633", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 National Cup Southeast Regional", "dates": "June 20-23, 2026", "state": "NC", "event_id": "47493", "schedule_platform": "gotsport", "status": "found"},

    # Virginia
    {"name": "Elite Futsal Invitational 2025", "dates": "December 27-28, 2025", "state": "VA", "event_id": "49786", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Arlington Boys College Showcase", "dates": "January 24-25, 2026", "state": "VA", "event_id": "50174", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Arlington Girls College Showcase", "dates": "January 24-25, 2026", "state": "VA", "event_id": "50173", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Feature Weekend Showcase 2026", "dates": "January 31-February 1, 2026", "state": "VA", "event_id": "43452", "schedule_platform": "gotsport", "status": "found"},
    {"name": "VDA Girls College Showcase 2026", "dates": "February 7-8, 2026", "state": "VA", "event_id": "44863", "schedule_platform": "gotsport", "status": "found"},
    {"name": "The Adidas National Cup 2026", "dates": "February 13-15, 2026", "state": "VA", "event_id": "42679", "schedule_platform": "gotsport", "status": "found"},
    {"name": "2026 Presidents Day Cup Showcase", "dates": "February 14-15, 2026", "state": "VA", "event_id": "43076", "schedule_platform": "gotsport", "status": "found"},
    {"name": "VDA Boys College Showcase 2026", "dates": "February 14-15, 2026", "state": "VA", "event_id": "44877", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Arlington Spring Boys Tournament", "dates": "February 27-March 1, 2026", "state": "VA", "event_id": "46958", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Loudoun Soccer College Showcase 2026", "dates": "February 27-March 1, 2026", "state": "VA", "event_id": "46932", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Alexandria Soccer Kickoff 2026", "dates": "February 28-March 1, 2026", "state": "VA", "event_id": "43512", "schedule_platform": "gotsport", "status": "found"},

    # New Jersey
    {"name": "Winter 5v5 Kick-off Sat", "dates": "December 20, 2025", "state": "NJ", "event_id": "44679", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Winter 5v5 Kick-off Sun", "dates": "December 21, 2025", "state": "NJ", "event_id": "44680", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Winter Holiday 5v5 Blast Sat", "dates": "December 27, 2025", "state": "NJ", "event_id": "44681", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Winter Holiday 5v5 Blast Sun", "dates": "December 28, 2025", "state": "NJ", "event_id": "44684", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Winter Holiday 5v5 Blast Mon", "dates": "December 29, 2025", "state": "NJ", "event_id": "44685", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Gotham FC Youth Cup", "dates": "January 3, 2026", "state": "NJ", "event_id": "44824", "schedule_platform": "gotsport", "status": "found"},
    {"name": "Winter One-Day Sun Jan 4", "dates": "January 4, 2026", "state": "NJ", "event_id": "44825", "schedule_platform": "gotsport", "status": "found"},
    {"name": "January 26 Winter Futsal", "dates": "January 10, 2026", "state": "NJ", "event_id": "49611", "schedule_platform": "gotsport", "status": "found"},
    {"name": "The FA 7v7 MLK Cup 2026", "dates": "January 17-19, 2026", "state": "NJ", "event_id": "49587", "schedule_platform": "gotsport", "status": "found"},
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
    print(f"Checking {len(MORE_TOURNAMENTS)} new tournaments...")

    added = 0
    for t in MORE_TOURNAMENTS:
        if t['event_id'] not in existing_ids:
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
