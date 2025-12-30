#!/usr/bin/env python3
"""Add featured GotSport tournaments to tracking CSV"""

import csv
import os
from datetime import datetime

TOURNAMENT_FILE = "tournament_urls_v2.csv"

# Featured tournaments from GotSoccer - use actual system IDs where known
FEATURED_TOURNAMENTS = [
    # Known system.gotsport.com event IDs
    {"name": "Weston Cup & Showcase 2026", "dates": "February 13-16, 2026", "state": "FL", "event_id": "45745", "schedule_platform": "gotsport", "status": "found"},

    # December 2025
    {"name": "Miami 2026 The Youth World Cup", "dates": "December 30, 2025 - June 2, 2026", "state": "FL", "event_id": "5478_featured", "schedule_platform": "gotsport", "status": "pending"},

    # January 2026
    {"name": "ZICO Cup 2026", "dates": "January 16-18, 2026", "state": "FL", "event_id": "5519_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Disney Girls Soccer Showcase", "dates": "January 16-19, 2026", "state": "FL", "event_id": "5423_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "23rd Annual Dimitri Cup (U8-U12)", "dates": "January 17-19, 2026", "state": "FL", "event_id": "5409_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Kick the Rust Off 2026", "dates": "January 18-19, 2026", "state": "IN", "event_id": "5523_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "23rd Annual Dimitri Cup (U13-U14)", "dates": "January 24-25, 2026", "state": "FL", "event_id": "5410_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "12th Annual Soccer Elite College Showcase", "dates": "January 30 - February 1, 2026", "state": "TN", "event_id": "5434_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Nevada Jr. Cup 2026", "dates": "January 30 - February 1, 2026", "state": "NV", "event_id": "5471_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "23rd Annual Dimitri Cup (U15-U19)", "dates": "January 31 - February 1, 2026", "state": "FL", "event_id": "5411_featured", "schedule_platform": "gotsport", "status": "pending"},

    # February 2026
    {"name": "2026 Gulf Coast Invitational", "dates": "February 6-8, 2026", "state": "FL", "event_id": "5530_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Bazooka Soccer Presidents Day Tournament", "dates": "February 14-15, 2026", "state": "FL", "event_id": "5497_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Jacksonville FC 2026 Girls Invitational", "dates": "February 14-15, 2026", "state": "FL", "event_id": "5533_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Disney Presidents Day Soccer Tournament", "dates": "February 14-16, 2026", "state": "FL", "event_id": "5424_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "City of Las Vegas Mayor's Cup (Boys)", "dates": "February 14-16, 2026", "state": "NV", "event_id": "5509_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "City of Las Vegas Mayor's Cup (Girls)", "dates": "February 20-22, 2026", "state": "NV", "event_id": "5510_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Midwest Club Championships (Boys)", "dates": "February 20-22, 2026", "state": "IN", "event_id": "5515_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Winter Rose Classic", "dates": "February 20-22, 2026", "state": "CA", "event_id": "5520_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Spring Kickoff Classic 2026", "dates": "February 21-22, 2026", "state": "CA", "event_id": "5532_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "21st Annual Bazooka Soccer College Showcase International", "dates": "February 21-22, 2026", "state": "FL", "event_id": "5458_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "25th Annual Blues City Blowout", "dates": "February 27 - March 1, 2026", "state": "TN", "event_id": "5435_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "AZFC Select Invitational 2026", "dates": "February 27 - March 1, 2026", "state": "AZ", "event_id": "5417_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Circle City Showcase", "dates": "February 27 - March 1, 2026", "state": "IN", "event_id": "5528_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Midwest Club Championships (Girls)", "dates": "February 27 - March 1, 2026", "state": "IN", "event_id": "5516_featured", "schedule_platform": "gotsport", "status": "pending"},

    # March 2026
    {"name": "Players College Showcase (Boys)", "dates": "March 6-8, 2026", "state": "NV", "event_id": "5507_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Jefferson Cup Boys Weekend", "dates": "March 7-8, 2026", "state": "VA", "event_id": "5460_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Union County Spring Kick Off 2026", "dates": "March 7-8, 2026", "state": "NJ", "event_id": "5512_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Players College Showcase (Girls)", "dates": "March 13-15, 2026", "state": "NV", "event_id": "5508_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "8th Annual Bazooka Soccer 7v7, 9v9, 11v11", "dates": "March 14-15, 2026", "state": "FL", "event_id": "5498_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Doral Cup", "dates": "March 14-15, 2026", "state": "FL", "event_id": "5452_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Jefferson Cup Girls Weekend", "dates": "March 14-15, 2026", "state": "VA", "event_id": "5461_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Jefferson Cup Girls Showcase", "dates": "March 20-22, 2026", "state": "VA", "event_id": "5465_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Florida Spring Copa", "dates": "March 20-22, 2026", "state": "FL", "event_id": "5524_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Jefferson Cup Boys Showcase", "dates": "March 27-29, 2026", "state": "VA", "event_id": "5464_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Tuzos Challenge Spring Invitational", "dates": "March 27-29, 2026", "state": "AZ", "event_id": "5506_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "CVFA Spring Invitational", "dates": "March 28-29, 2026", "state": "CA", "event_id": "5517_featured", "schedule_platform": "gotsport", "status": "pending"},

    # April 2026
    {"name": "CDO Challenge Cup 2026", "dates": "April 9-12, 2026", "state": "AZ", "event_id": "5511_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Reno Spring Cup 2026", "dates": "April 11-12, 2026", "state": "NV", "event_id": "5503_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "20th Annual Carvana Soccer Elite Spring Championships", "dates": "April 17-19, 2026", "state": "TN", "event_id": "5436_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Coastal Shootout", "dates": "April 18-19, 2026", "state": "DE", "event_id": "5445_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "AZFC Select Challenge 2026", "dates": "April 24-26, 2026", "state": "AZ", "event_id": "5469_featured", "schedule_platform": "gotsport", "status": "pending"},

    # May 2026
    {"name": "11th Annual Premier Invitational", "dates": "May 1-3, 2026", "state": "TN", "event_id": "5437_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "May Day Classic 2026", "dates": "May 1-3, 2026", "state": "NY", "event_id": "5534_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Dynamo MVP 2026", "dates": "May 8-10, 2026", "state": "IN", "event_id": "5522_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Jeff Bush Memorial Cup 2026", "dates": "May 15-17, 2026", "state": "NV", "event_id": "5504_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "ASG Capital Cup 2026", "dates": "May 15-17, 2026", "state": "FL", "event_id": "5536_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Real CO Cup/Colorado Showcase", "dates": "May 21-25, 2026", "state": "CO", "event_id": "5513_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Jr Irish Memorial Day Invitational", "dates": "May 22-24, 2026", "state": "IN", "event_id": "5529_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Mother's Day Classic 2026", "dates": "May 23-24, 2026", "state": "IN", "event_id": "5526_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "2026 Disney Memorial Day Soccer Tournament", "dates": "May 23-25, 2026", "state": "FL", "event_id": "5425_featured", "schedule_platform": "gotsport", "status": "pending"},

    # June 2026
    {"name": "2026 Lancaster Summer Classic", "dates": "June 6-7, 2026", "state": "PA", "event_id": "5531_featured", "schedule_platform": "gotsport", "status": "pending"},
    {"name": "Chicago International College Showcase 2026", "dates": "June 12-14, 2026", "state": "IL", "event_id": "5505_featured", "schedule_platform": "gotsport", "status": "pending"},

    # August 2026
    {"name": "RUSH to the Shore Cup", "dates": "August 29-30, 2026", "state": "DE", "event_id": "5535_featured", "schedule_platform": "gotsport", "status": "pending"},
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
    print(f"Checking {len(FEATURED_TOURNAMENTS)} featured tournaments...")

    added = 0
    for t in FEATURED_TOURNAMENTS:
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
            'schedule_url': f"https://system.gotsport.com/org_event/events/{t['event_id'].replace('_featured', '')}" if '_featured' not in t['event_id'] else '',
            'schedule_platform': t['schedule_platform'],
            'event_id': t['event_id'],
            'status': t['status'],
            'notes': f"Featured tournament - Added {datetime.now().strftime('%Y-%m-%d')}"
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
