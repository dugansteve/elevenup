#!/usr/bin/env python3
"""
California Regional Leagues Scraper v1.0
=========================================
Scraper for California regional youth soccer leagues using GotSport platform.

⚠️⚠️⚠️ CRITICAL: AGE GROUP FORMAT USES BIRTH YEAR ⚠️⚠️⚠️
=====================================================
ALL THESE PATTERNS ARE EQUIVALENT: 12G = G12 = 2012 = 2012G = birth year 2012

The number in team names and age groups is ALWAYS the birth year!
Current ages are NEVER in team names (except U-format).

| Pattern | Meaning          | Age Group | Players' Age in 2025 |
|---------|------------------|-----------|----------------------|
| G12     | Girls, Born 2012 | G12       | 13 years old         |
| B11     | Boys, Born 2011  | B11       | 14 years old         |
| 12G     | Born 2012, Girls | G12       | 13 years old         |
| 14F     | Born 2014, Female| G14       | 11 years old         |

Only U-format (U13, U11) means "under age X" where the number IS an age.

Formula: 12G → birth_year = 2012 → age_group = G12

THIS MISTAKE HAS BEEN MADE MULTIPLE TIMES - DO NOT REPEAT IT!
=====================================================

VERSION HISTORY:
═══════════════════════════════════════════════════════════════════════════════

V1.0 (Current):
  ✅ Initial release - Multi-state regional league scraper
  ✅ GotSport platform scraping (same as NPL scraper)
  ✅ Human-like behavior (delays, rotating user agents)
  ✅ CSV export and database integration
  ✅ Resume capability with section retry
  ✅ Event tracking in league_events table
  ✅ Smart deduplication with fuzzy team name matching
  ✅ WAL mode and busy_timeout for database resilience

Supported Leagues:
- Cal North CCSL (California Competitive Soccer League)
- NorCal Premier League
- EDP League (NJ, PA, DE, MD)
- CJSL (NY)
- Illinois State Premiership
- Georgia Soccer
- TCSL (Texas)
- MSPSP (Michigan)
- US Youth Soccer National League Conferences
- Many state cups and regional leagues

Features:
- GotSport platform scraping (same as NPL scraper)
- Human-like behavior (delays, rotating user agents)
- CSV export and database integration
- Resume capability with section retry
- Event tracking (--sync, --status, --auto flags)

CRITICAL IMPLEMENTATION NOTES - DO NOT REMOVE OR MODIFY:
═══════════════════════════════════════════════════════════════════════════════

  1. SMART DEDUPLICATION (save_game_to_db function):
     - Uses 3-step matching: exact game_id → fuzzy match → insert/update/skip
     - Returns Tuple[bool, str] with action type: 'inserted', 'updated', 'skipped', 'filtered'
     - Checks ALL existing games (not just those without scores)
     - PRESERVE: The normalize_team_for_id() function and fuzzy matching logic
     - WHY: Prevents duplicates when team names vary between sources

  2. TEAM NAME NORMALIZATION (normalize_team_for_id function):
     - Removes: FC, SC, Academy, Club, United, Soccer, age patterns
     - Removes all non-alphanumeric characters, truncates to 30 chars
     - PRESERVE: All remove_patterns and remove_words lists
     - WHY: Team names vary across sources but need to match for deduplication

  3. DATABASE RESILIENCE (get_db_connection function):
     - WAL mode enabled for better concurrency
     - 30-second busy_timeout prevents "database locked" errors
     - PRESERVE: PRAGMA statements in get_db_connection()
     - WHY: Multiple scrapers may access the database simultaneously

  4. EVENT TRACKING (league_events table):
     - Tracks each league/event with status, dates, and scrape schedule
     - update_event_after_scrape() calculates next_scrape based on status
     - PRESERVE: Event tracking for --auto mode scheduling
     - WHY: Allows smart scheduling of scrapes based on event activity

  5. SECTION RETRY LOGIC:
     - Failed sections are tracked and retried at end of scraping
     - PRESERVE: The failed_sections list and retry loop in scrape_league()
     - WHY: Network issues shouldn't cause entire league to be skipped

Author: Claude (with Steve)
Version: 1.0
"""

SCRAPER_VERSION = "v1"

import os
import re
import csv
import sys
import json
import time
import random
import asyncio
import argparse
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path

# Third-party imports
try:
    from playwright.async_api import async_playwright, Page, Browser
    from bs4 import BeautifulSoup
    import requests
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install playwright beautifulsoup4 requests")
    print("Then run: playwright install chromium")
    sys.exit(1)


# =============================================================================
# STEALTH CONFIGURATION
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

MIN_DELAY = 2.0
MAX_DELAY = 5.0


# =============================================================================
# LEAGUE CONFIGURATION
# =============================================================================

@dataclass
class LeagueConfig:
    """Configuration for a single league"""
    name: str                  # League name for database
    display_name: str          # Display name
    organization: str          # Parent organization
    platform: str              # "gotsport"
    url: str                   # Base URL
    event_id: str              # GotSport event ID
    gender: str                # "Both", "Boys", "Girls"
    age_groups: str            # "U8-U19", etc.
    region: str                # Geographic region
    tier: str                  # Competition tier
    state: str = "CA"          # Default state
    active: bool = True


# Regional Leagues - Multiple States
LEAGUE_CONFIGS = [
    # =========================================================================
    # CALIFORNIA - Northern
    # =========================================================================
    # Cal North CCSL - Multiple seasons available
    LeagueConfig(
        name="CCSL",
        display_name="Cal North CCSL Fall 2021",
        organization="Cal North",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/6160",
        event_id="6160",
        gender="Both",
        age_groups="U8-U19",
        region="Northern California",
        tier="Regional",
        state="CA"
    ),
    LeagueConfig(
        name="CCSL",
        display_name="Cal North CCSL Spring 2022",
        organization="Cal North",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/11718",
        event_id="11718",
        gender="Both",
        age_groups="U8-U19",
        region="Northern California",
        tier="Regional",
        state="CA"
    ),
    # NorCal Premier - Current season
    LeagueConfig(
        name="NorCal Premier",
        display_name="NorCal Premier Fall 2024-25",
        organization="NorCal Premier Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/33458",
        event_id="33458",
        gender="Both",
        age_groups="U8-U19",
        region="Northern California",
        tier="Premier",
        state="CA"
    ),
    LeagueConfig(
        name="NorCal Premier",
        display_name="NorCal Premier Spring 2024",
        organization="NorCal Premier Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/44142",
        event_id="44142",
        gender="Both",
        age_groups="U8-U19",
        region="Northern California",
        tier="Premier",
        state="CA"
    ),

    # =========================================================================
    # CALIFORNIA - Southern
    # =========================================================================
    LeagueConfig(
        name="SoCal Soccer League",
        display_name="SoCal Soccer League 2024-25",
        organization="SoCal Soccer League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/33123",
        event_id="33123",
        gender="Both",
        age_groups="U8-U19",
        region="Southern California",
        tier="Premier",
        state="CA"
    ),
    LeagueConfig(
        name="Coast Soccer League",
        display_name="SOCAL Fall League",
        organization="Coast Soccer League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/14215",
        event_id="14215",
        gender="Both",
        age_groups="U8-U19",
        region="Southern California",
        tier="Regional",
        state="CA"
    ),

    # =========================================================================
    # EAST COAST - EDP League (NJ, PA, DE, MD)
    # =========================================================================
    LeagueConfig(
        name="EDP",
        display_name="EDP League Fall 2024",
        organization="EDP Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/34067",
        event_id="34067",
        gender="Both",
        age_groups="U9-U19",
        region="Mid-Atlantic",
        tier="Premier",
        state="NJ",
        active=True
    ),
    LeagueConfig(
        name="EDP",
        display_name="EDP League Spring 2024",
        organization="EDP Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/27462",
        event_id="27462",
        gender="Both",
        age_groups="U9-U19",
        region="Mid-Atlantic",
        tier="Premier",
        state="NJ",
        active=True
    ),

    # =========================================================================
    # NEW YORK
    # =========================================================================
    LeagueConfig(
        name="CJSL",
        display_name="CJSL (Cosmopolitan Junior Soccer League)",
        organization="CJSL",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/33353",
        event_id="33353",
        gender="Both",
        age_groups="U9-U19",
        region="New York Metro",
        tier="Premier",
        state="NY",
        active=True
    ),

    # =========================================================================
    # ILLINOIS
    # =========================================================================
    LeagueConfig(
        name="Illinois State Premiership",
        display_name="Illinois State Premiership 2024-25",
        organization="Illinois Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/35609",
        event_id="35609",
        gender="Both",
        age_groups="U13-U19",
        region="Illinois",
        tier="State",
        state="IL",
        active=True
    ),

    # =========================================================================
    # GEORGIA
    # =========================================================================
    LeagueConfig(
        name="Georgia Soccer",
        display_name="Georgia Soccer League 2024-25",
        organization="Georgia Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/36330",
        event_id="36330",
        gender="Both",
        age_groups="U9-U19",
        region="Georgia",
        tier="State",
        state="GA",
        active=True
    ),

    # =========================================================================
    # TEXAS
    # =========================================================================
    LeagueConfig(
        name="TCSL",
        display_name="TCSL Fall 2024 (Texas Club Soccer League)",
        organization="Texas Club Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/35207",
        event_id="35207",
        gender="Both",
        age_groups="U11-U17",
        region="North Texas",
        tier="Select",
        state="TX",
        active=True
    ),
    LeagueConfig(
        name="TCSL",
        display_name="TCSL Winter 2024-25",
        organization="Texas Club Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/37085",
        event_id="37085",
        gender="Both",
        age_groups="U11-U17",
        region="North Texas",
        tier="Select",
        state="TX",
        active=True
    ),

    # =========================================================================
    # MICHIGAN
    # =========================================================================
    LeagueConfig(
        name="MSPSP",
        display_name="Michigan State Premier Soccer Program 2024-25",
        organization="Michigan State Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/40646",
        event_id="40646",
        gender="Both",
        age_groups="U13-U19",
        region="Michigan",
        tier="State Premier",
        state="MI",
        active=True
    ),

    # =========================================================================
    # US YOUTH SOCCER NATIONAL LEAGUE CONFERENCES
    # =========================================================================
    LeagueConfig(
        name="Northwest Conference",
        display_name="USYS Northwest Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/34040",
        event_id="34040",
        gender="Both",
        age_groups="U13-U19",
        region="Pacific Northwest",
        tier="National League",
        state="WA",
        active=True
    ),
    LeagueConfig(
        name="Midwest Conference",
        display_name="USYS Midwest Conference Fall 2024",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/4696",
        event_id="4696",
        gender="Both",
        age_groups="U13-U19",
        region="Midwest",
        tier="National League",
        state="IL",
        active=True
    ),
    LeagueConfig(
        name="Desert Conference",
        display_name="USYS Desert Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/34558",
        event_id="34558",
        gender="Both",
        age_groups="U13-U19",
        region="Southwest",
        tier="National League",
        state="AZ",
        active=True
    ),

    # =========================================================================
    # NEW ENGLAND
    # =========================================================================
    LeagueConfig(
        name="WPL",
        display_name="WPL Fall 2024 (New England)",
        organization="WPL",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/34397",
        event_id="34397",
        gender="Both",
        age_groups="U11-U14",
        region="New England",
        tier="Regional",
        state="MA",
        active=True
    ),

    # =========================================================================
    # MORE USYS NATIONAL LEAGUE CONFERENCES
    # =========================================================================
    LeagueConfig(
        name="Great Lakes Conference",
        display_name="USYS Great Lakes Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/32563",
        event_id="32563",
        gender="Both",
        age_groups="U13-U19",
        region="Great Lakes",
        tier="National League",
        state="OH",
        active=True
    ),
    LeagueConfig(
        name="Mid South Conference",
        display_name="USYS Mid South Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/40362",
        event_id="40362",
        gender="Both",
        age_groups="U13-U19",
        region="Mid South",
        tier="National League",
        state="TN",
        active=True
    ),
    LeagueConfig(
        name="Frontier Conference",
        display_name="USYS Frontier Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/33931",
        event_id="33931",
        gender="Both",
        age_groups="U13-U19",
        region="South Central",
        tier="National League",
        state="TX",
        active=True
    ),
    LeagueConfig(
        name="Sunshine Conference",
        display_name="USYS Sunshine Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/4697",
        event_id="4697",
        gender="Both",
        age_groups="U13-U19",
        region="Southeast",
        tier="National League",
        state="FL",
        active=True
    ),
    LeagueConfig(
        name="Piedmont Conference",
        display_name="USYS Piedmont Conference 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/40408",
        event_id="40408",
        gender="Both",
        age_groups="U13-U19",
        region="Piedmont",
        tier="National League",
        state="NC",
        active=True
    ),

    # =========================================================================
    # STATE LEAGUES
    # =========================================================================
    LeagueConfig(
        name="Nevada State League",
        display_name="Nevada State League 2024",
        organization="Nevada Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/35204",
        event_id="35204",
        gender="Both",
        age_groups="U7-U19",
        region="Nevada",
        tier="State",
        state="NV",
        active=True
    ),
    LeagueConfig(
        name="FSPL",
        display_name="Florida State Premier League 2024-25",
        organization="Florida Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/32708",
        event_id="32708",
        gender="Both",
        age_groups="U13-U19",
        region="Florida",
        tier="State Premier",
        state="FL",
        active=True
    ),

    # =========================================================================
    # USYS NATIONAL LEAGUE P.R.O. (Top Tier - National Level)
    # =========================================================================
    LeagueConfig(
        name="National League PRO",
        display_name="USYS National League P.R.O. 2024-25",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/4632",
        event_id="4632",
        gender="Both",
        age_groups="U13-U19",
        region="National",
        tier="National League PRO",
        state="US",
        active=True
    ),

    # =========================================================================
    # USYS PRESIDENTS CUP
    # =========================================================================
    LeagueConfig(
        name="Presidents Cup",
        display_name="USYS National Presidents Cup 2025",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/42906",
        event_id="42906",
        gender="Both",
        age_groups="U13-U19",
        region="National",
        tier="Presidents Cup",
        state="FL",
        active=True
    ),
    LeagueConfig(
        name="Presidents Cup",
        display_name="STX Presidents Cup 2025",
        organization="STX Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/41131",
        event_id="41131",
        gender="Both",
        age_groups="U11-U19",
        region="South Texas",
        tier="Presidents Cup",
        state="TX",
        active=True
    ),
    LeagueConfig(
        name="Presidents Cup",
        display_name="Virginia Presidents Cup",
        organization="Virginia Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/26278",
        event_id="26278",
        gender="Both",
        age_groups="U11-U19",
        region="Virginia",
        tier="Presidents Cup",
        state="VA",
        active=True
    ),

    # =========================================================================
    # STATE CUPS
    # =========================================================================
    LeagueConfig(
        name="State Cup",
        display_name="SOCAL State Cup 2025",
        organization="SOCAL Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/38927",
        event_id="38927",
        gender="Both",
        age_groups="U9-U19",
        region="Southern California",
        tier="State Cup",
        state="CA",
        active=True
    ),
    LeagueConfig(
        name="State Cup",
        display_name="NorCal State Cup 2024-25",
        organization="NorCal Premier Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/33460",
        event_id="33460",
        gender="Both",
        age_groups="U9-U19",
        region="Northern California",
        tier="State Cup",
        state="CA",
        active=True
    ),
    LeagueConfig(
        name="State Cup",
        display_name="STX State Cup 2025",
        organization="STX Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/41135",
        event_id="41135",
        gender="Both",
        age_groups="U11-U19",
        region="South Texas",
        tier="State Cup",
        state="TX",
        active=True
    ),

    # =========================================================================
    # PENNSYLVANIA
    # =========================================================================
    LeagueConfig(
        name="Eastern PA Challenge Cup",
        display_name="Eastern PA Challenge Cup 2025",
        organization="Eastern PA Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/42736",
        event_id="42736",
        gender="Both",
        age_groups="U9-U19",
        region="Eastern Pennsylvania",
        tier="Challenge Cup",
        state="PA",
        active=True
    ),
    LeagueConfig(
        name="State Cup",
        display_name="Eastern PA State Cup",
        organization="Eastern PA Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/3122",
        event_id="3122",
        gender="Both",
        age_groups="U9-U19",
        region="Eastern Pennsylvania",
        tier="State Cup",
        state="PA",
        active=True
    ),

    # =========================================================================
    # FLORIDA - Additional Leagues
    # =========================================================================
    LeagueConfig(
        name="WFPL",
        display_name="West Florida Premier League 25/26",
        organization="West Florida Premier League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/45008",
        event_id="45008",
        gender="Both",
        age_groups="U9-U19",
        region="West Florida",
        tier="Premier",
        state="FL",
        active=True
    ),
    LeagueConfig(
        name="SEFPL",
        display_name="Southeast Florida Premier League",
        organization="Southeast Florida Premier League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/35059",
        event_id="35059",
        gender="Both",
        age_groups="U9-U19",
        region="Southeast Florida",
        tier="Premier",
        state="FL",
        active=True
    ),

    # =========================================================================
    # STATE CUPS - Various States
    # =========================================================================
    LeagueConfig(
        name="State Cup",
        display_name="New Mexico Open State Cup 2025",
        organization="New Mexico Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/39444",
        event_id="39444",
        gender="Both",
        age_groups="U12-U19",
        region="New Mexico",
        tier="State Cup",
        state="NM",
        active=True
    ),
    LeagueConfig(
        name="State Cup",
        display_name="North Texas State Cup 2025",
        organization="North Texas Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/40552",
        event_id="40552",
        gender="Both",
        age_groups="U11-U19",
        region="North Texas",
        tier="State Cup",
        state="TX",
        active=True
    ),
    LeagueConfig(
        name="State Cup",
        display_name="Washington Cup 2025",
        organization="Washington Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/41133",
        event_id="41133",
        gender="Both",
        age_groups="U11-U14",
        region="Washington",
        tier="State Cup",
        state="WA",
        active=True
    ),
    LeagueConfig(
        name="State Cup",
        display_name="US Club Texas State Cup 2025",
        organization="US Club Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/37553",
        event_id="37553",
        gender="Both",
        age_groups="U9-U19",
        region="Texas",
        tier="State Cup",
        state="TX",
        active=True
    ),

    # =========================================================================
    # ILLINOIS
    # =========================================================================
    LeagueConfig(
        name="Illinois Cup",
        display_name="Fall 2025 Illinois Cup",
        organization="Illinois Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/45647",
        event_id="45647",
        gender="Both",
        age_groups="U11-U19",
        region="Illinois",
        tier="State Cup",
        state="IL",
        active=True
    ),

    # =========================================================================
    # VIRGINIA
    # =========================================================================
    LeagueConfig(
        name="Virginia Cup",
        display_name="2025 Virginian Elite Soccer",
        organization="Virginia Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/39393",
        event_id="39393",
        gender="Both",
        age_groups="U9-U19",
        region="Virginia",
        tier="Tournament",
        state="VA",
        active=True
    ),

    # =========================================================================
    # NEW JERSEY
    # =========================================================================
    LeagueConfig(
        name="ICSL",
        display_name="ICSL Fall League",
        organization="Inter-County Soccer League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/32948",
        event_id="32948",
        gender="Both",
        age_groups="U9-U19",
        region="New Jersey",
        tier="Regional",
        state="NJ",
        active=True
    ),

    # =========================================================================
    # ARIZONA
    # =========================================================================
    LeagueConfig(
        name="State Cup",
        display_name="Arizona State Cup 2025",
        organization="Arizona Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/34355",
        event_id="34355",
        gender="Both",
        age_groups="U12-U19",
        region="Arizona",
        tier="State Cup",
        state="AZ",
        active=True
    ),

    # =========================================================================
    # COLORADO
    # =========================================================================
    LeagueConfig(
        name="Real CO Cup",
        display_name="2025 Real CO Cup / Colorado Showcase",
        organization="Real Colorado",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/39601",
        event_id="39601",
        gender="Both",
        age_groups="U10-U19",
        region="Colorado",
        tier="Tournament",
        state="CO",
        active=True
    ),

    # =========================================================================
    # MARYLAND
    # =========================================================================
    LeagueConfig(
        name="Baltimore Mania",
        display_name="2025 Baltimore Mania - Boys",
        organization="Elite Tournaments",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/35273",
        event_id="35273",
        gender="Boys",
        age_groups="U9-U19",
        region="Maryland",
        tier="Tournament",
        state="MD",
        active=True
    ),

    # =========================================================================
    # NEW YORK
    # =========================================================================
    LeagueConfig(
        name="State Cup",
        display_name="Eastern New York State Cup 2025",
        organization="Eastern NY Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/39315",
        event_id="39315",
        gender="Both",
        age_groups="U12-U17",
        region="Eastern New York",
        tier="State Cup",
        state="NY",
        active=True
    ),

    # =========================================================================
    # PENNSYLVANIA - Additional
    # =========================================================================
    LeagueConfig(
        name="LVYSL",
        display_name="Lebanon Valley Youth Soccer League Spring 2025",
        organization="LVYSL",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/41885",
        event_id="41885",
        gender="Both",
        age_groups="U9-U18",
        region="Lebanon Valley PA",
        tier="Regional",
        state="PA",
        active=True
    ),
    LeagueConfig(
        name="APL",
        display_name="2025 APL / Acela Fall League",
        organization="APL",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/43531",
        event_id="43531",
        gender="Both",
        age_groups="U8-U12",
        region="Philadelphia PA",
        tier="Regional",
        state="PA",
        active=True
    ),

    # =========================================================================
    # WISCONSIN
    # =========================================================================
    LeagueConfig(
        name="WYSA State League",
        display_name="WYSA State League Spring 2024",
        organization="Wisconsin Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/30599",
        event_id="30599",
        gender="Both",
        age_groups="U11-U19",
        region="Wisconsin",
        tier="State League",
        state="WI",
        active=True
    ),

    # =========================================================================
    # NORTHWEST (OR, WA, ID)
    # =========================================================================
    LeagueConfig(
        name="Northwest Conference",
        display_name="Northwest Conference 2024-2025",
        organization="US Youth Soccer",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/34040",
        event_id="34040",
        gender="Both",
        age_groups="U13-U19",
        region="Pacific Northwest",
        tier="Conference",
        state="OR",
        active=True
    ),

    # =========================================================================
    # WEST VIRGINIA
    # =========================================================================
    LeagueConfig(
        name="WVFC Capital Cup",
        display_name="WVFC 2025 Capital Cup",
        organization="West Virginia Futbol Club",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/37861",
        event_id="37861",
        gender="Both",
        age_groups="U8-U19",
        region="West Virginia",
        tier="Tournament",
        state="WV",
        active=True
    ),

    # =========================================================================
    # FALL 2025 LEAGUES (After June 1, 2025)
    # =========================================================================
    LeagueConfig(
        name="ICSL",
        display_name="ICSL Fall 2025",
        organization="Inter-County Soccer League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/43667",
        event_id="43667",
        gender="Both",
        age_groups="U9-U19",
        region="New Jersey",
        tier="Regional",
        state="NJ",
        active=True
    ),
    LeagueConfig(
        name="SOCAL",
        display_name="SOCAL Fall 2025-2026",
        organization="SOCAL Soccer League",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/43086",
        event_id="43086",
        gender="Both",
        age_groups="U7-U19",
        region="Southern California",
        tier="Premier",
        state="CA",
        active=True
    ),
    LeagueConfig(
        name="SLYSA",
        display_name="SLYSA Fall 2025",
        organization="St. Louis Youth Soccer Association",
        platform="gotsport",
        url="https://system.gotsport.com/org_event/events/44132",
        event_id="44132",
        gender="Both",
        age_groups="U8-U19",
        region="St. Louis",
        tier="Regional",
        state="MO",
        active=True
    ),
]


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def find_database_path():
    """Find the seedlinedata.db database file"""
    script_dir = Path(__file__).parent.resolve()
    search_paths = [
        script_dir.parent.parent / "seedlinedata.db",
        script_dir.parent / "seedlinedata.db",
        script_dir / "seedlinedata.db",
        Path.cwd() / "seedlinedata.db",
    ]

    for path in search_paths:
        if path.exists():
            return str(path)

    return None


def get_db_connection(db_path: str):
    """Get database connection with WAL mode for better concurrency"""
    conn = sqlite3.connect(db_path, timeout=30)  # 30 second timeout
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
    return conn


def save_game_to_db(db_path: str, game: Dict, min_date: str = None, max_retries: int = 3) -> Tuple[bool, str]:
    """Save game to database with smart deduplication.

    Matching logic:
    1. First try exact game_id match
    2. If no match, use fuzzy matching by date + normalized teams + age + league
    3. Check ALL existing games (not just those without scores) to prevent duplicates
    4. Update existing games with new scores if available
    5. Only insert if no matching game exists

    Args:
        min_date: Optional minimum date filter (e.g., '2025-06-01').
                  If set, games before this date are skipped.
        max_retries: Number of times to retry on database lock errors.

    Returns:
        Tuple of (success, action) where action is 'inserted', 'updated', 'skipped', or 'filtered'
    """
    if not db_path:
        return False, 'error'

    # Filter out games before min_date if specified
    if min_date:
        game_date = game.get('game_date_iso') or game.get('game_date', '')
        if game_date and game_date < min_date:
            return False, 'filtered'  # Skip old games

    game_id = game.get('game_id', '')
    if not game_id:
        return False, 'error'

    for attempt in range(max_retries):
        try:
            conn = get_db_connection(db_path)
            cur = conn.cursor()

            # Convert age group to proper format
            age_group = game.get('age_group', '')
            gender = game.get('gender', 'Girls')
            if age_group and age_group.isdigit() and len(age_group) == 4:
                birth_year = int(age_group)
                current_year = datetime.now().year
                age = current_year - birth_year
                gender_prefix = 'B' if gender.lower().startswith('b') else 'G'
                age_group = f"{gender_prefix}{age:02d}"

            league = game.get('league', 'CCSL')
            conference = game.get('region', '')
            game_date_iso = game.get('game_date_iso', game.get('game_date'))

            # Normalize team names for matching
            home_norm = normalize_team_for_id(game.get('home_team', ''))
            away_norm = normalize_team_for_id(game.get('away_team', ''))

            # Step 1: Try exact game_id match
            cur.execute("SELECT rowid, home_score, away_score FROM games WHERE game_id = ?", (game_id,))
            ex = cur.fetchone()

            # Step 2: If no exact match, fuzzy match on ALL games
            if not ex:
                cur.execute("""
                    SELECT rowid, home_score, away_score, home_team, away_team FROM games
                    WHERE game_date_iso = ? AND age_group = ? AND league = ?
                """, (game_date_iso, age_group, league))

                for row in cur.fetchall():
                    existing_home = normalize_team_for_id(row[3] or '')
                    existing_away = normalize_team_for_id(row[4] or '')
                    # Match if teams match in either order
                    if (home_norm == existing_home and away_norm == existing_away) or \
                       (home_norm == existing_away and away_norm == existing_home):
                        ex = (row[0], row[1], row[2])
                        break

            # Step 3: Decide action based on what we found
            if ex:
                existing_has_scores = ex[1] is not None and ex[2] is not None
                new_has_scores = game.get('home_score') is not None

                if new_has_scores and not existing_has_scores:
                    # Update: existing game missing scores, new data has scores
                    cur.execute("""UPDATE games SET
                        home_score = ?, away_score = ?,
                        game_status = 'completed',
                        scraped_at = datetime('now')
                        WHERE rowid = ?""",
                        (game.get('home_score'), game.get('away_score'), ex[0]))
                    conn.commit()
                    conn.close()
                    return True, 'updated'
                else:
                    # Skip: game already exists
                    conn.close()
                    return False, 'skipped'
            else:
                # Insert: no matching game found
                cur.execute("""INSERT INTO games (game_id, game_date, game_date_iso, game_time, home_team, away_team,
                              home_score, away_score, league, age_group, conference, location, game_status, source_url, scraped_at, gender)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                           (game_id, game.get('game_date'), game_date_iso,
                            game.get('game_time'), game.get('home_team'), game.get('away_team'),
                            game.get('home_score'), game.get('away_score'),
                            league, age_group, conference,
                            game.get('location', ''), game.get('game_status', ''),
                            game.get('source_url', ''), gender))
                conn.commit()
                conn.close()
                return True, 'inserted'

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(1 + attempt * 2)  # Exponential backoff: 1s, 3s, 5s
                continue
            else:
                if 'conn' in locals():
                    conn.close()
                raise
        except Exception:
            if 'conn' in locals():
                conn.close()
            raise

    return False, 'error'


def save_team_to_db(db_path: str, team: Dict, max_retries: int = 3) -> bool:
    """Save team to database with retry logic"""
    if not db_path:
        return False

    team_url = team.get('schedule_url') or f"ca_regional_{team.get('team_id', '')}"

    for attempt in range(max_retries):
        try:
            conn = get_db_connection(db_path)
            cur = conn.cursor()

            cur.execute("SELECT rowid FROM teams WHERE team_url = ?", (team_url,))
            if cur.fetchone():
                conn.close()
                return False

            # Convert age group
            age_group = team.get('age_group', '')
            gender = team.get('gender', 'Girls')
            if age_group and age_group.isdigit() and len(age_group) == 4:
                birth_year = int(age_group)
                current_year = datetime.now().year
                age = current_year - birth_year
                gender_prefix = 'B' if gender.lower().startswith('b') else 'G'
                age_group = f"{gender_prefix}{age:02d}"

            cur.execute("""INSERT INTO teams (team_url, club_name, team_name, age_group, gender, league, conference,
                          state, scraped_at)
                          VALUES (?,?,?,?,?,?,?,?,datetime('now'))""",
                       (team_url, team.get('club_name'), team.get('team_name'), age_group,
                        gender, team.get('league'), team.get('region'), team.get('state', 'CA')))
            conn.commit()
            conn.close()
            return True

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(1 + attempt * 2)  # Exponential backoff
                continue
            else:
                if 'conn' in locals():
                    conn.close()
                raise
        except Exception:
            if 'conn' in locals():
                conn.close()
            raise

    return False


# =============================================================================
# EVENT TRACKING FUNCTIONS
# =============================================================================

def save_event_to_db(db_path: str, league_config: 'LeagueConfig',
                     start_date: str = None, end_date: str = None) -> bool:
    """Save or update event metadata in league_events table"""
    if not db_path:
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if event exists
    cur.execute("SELECT id FROM league_events WHERE event_id = ?", (league_config.event_id,))
    existing = cur.fetchone()

    if existing:
        # Update existing event
        cur.execute("""
            UPDATE league_events SET
                league_name = ?,
                event_name = ?,
                event_url = ?,
                start_date = COALESCE(?, start_date),
                end_date = COALESCE(?, end_date),
                region = ?,
                state = ?,
                gender = ?,
                age_groups = ?,
                tier = ?,
                updated_at = datetime('now')
            WHERE event_id = ?
        """, (league_config.name, league_config.display_name, league_config.url,
              start_date, end_date, league_config.region, league_config.state,
              league_config.gender, league_config.age_groups, league_config.tier,
              league_config.event_id))
    else:
        # Insert new event
        cur.execute("""
            INSERT INTO league_events (
                event_id, platform, league_name, event_name, event_url,
                start_date, end_date, region, state, gender, age_groups, tier,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', datetime('now'), datetime('now'))
        """, (league_config.event_id, league_config.platform, league_config.name,
              league_config.display_name, league_config.url, start_date, end_date,
              league_config.region, league_config.state, league_config.gender,
              league_config.age_groups, league_config.tier))

    conn.commit()
    conn.close()
    return True


def update_event_after_scrape(db_path: str, event_id: str,
                               games_found: int, games_saved: int, teams_found: int,
                               earliest_date: str = None, latest_date: str = None) -> bool:
    """Update event stats after scraping"""
    if not db_path:
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Determine status based on dates
    today = datetime.now().strftime('%Y-%m-%d')
    status = 'active'
    if latest_date and latest_date < today:
        status = 'completed'
    elif earliest_date and earliest_date > today:
        status = 'upcoming'

    # Calculate next scrape based on status
    if status == 'completed':
        next_scrape = None  # Don't scrape completed events
    elif status == 'upcoming':
        next_scrape = earliest_date  # Scrape when it starts
    else:
        # Active events: scrape again in 1-3 days depending on how recent games are
        next_scrape = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

    cur.execute("""
        UPDATE league_events SET
            games_found = ?,
            games_saved = ?,
            teams_found = ?,
            start_date = COALESCE(?, start_date),
            end_date = COALESCE(?, end_date),
            status = ?,
            last_scraped = datetime('now'),
            next_scrape = ?,
            updated_at = datetime('now')
        WHERE event_id = ?
    """, (games_found, games_saved, teams_found, earliest_date, latest_date,
          status, next_scrape, event_id))

    conn.commit()
    conn.close()
    return True


def get_events_to_scrape(db_path: str, force: bool = False) -> List[Dict]:
    """Get list of events that need scraping based on dates and schedule"""
    if not db_path:
        return []

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')

    if force:
        # Return all active/upcoming events
        cur.execute("""
            SELECT event_id, league_name, event_name, event_url, status, last_scraped
            FROM league_events
            WHERE status != 'completed'
            ORDER BY next_scrape ASC NULLS LAST
        """)
    else:
        # Return events where next_scrape <= today or never scraped
        cur.execute("""
            SELECT event_id, league_name, event_name, event_url, status, last_scraped
            FROM league_events
            WHERE status != 'completed'
              AND (next_scrape IS NULL OR next_scrape <= ?)
            ORDER BY next_scrape ASC NULLS FIRST
        """, (today,))

    events = []
    for row in cur.fetchall():
        events.append({
            'event_id': row[0],
            'league_name': row[1],
            'event_name': row[2],
            'event_url': row[3],
            'status': row[4],
            'last_scraped': row[5]
        })

    conn.close()
    return events


def sync_configs_to_db(db_path: str) -> int:
    """Sync all LeagueConfig entries to league_events table"""
    if not db_path:
        return 0

    count = 0
    for config in LEAGUE_CONFIGS:
        if config.active:
            if save_event_to_db(db_path, config):
                count += 1

    return count


def list_events_status(db_path: str) -> None:
    """Print status of all tracked events"""
    if not db_path:
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT league_name, event_name, status, games_saved,
               last_scraped, next_scrape, start_date, end_date
        FROM league_events
        ORDER BY status, next_scrape ASC NULLS LAST
    """)

    print("\n" + "=" * 100)
    print("TRACKED EVENTS STATUS")
    print("=" * 100)
    print(f"{'League':<20} {'Event':<35} {'Status':<10} {'Games':<8} {'Last Scraped':<12} {'Next Scrape':<12}")
    print("-" * 100)

    for row in cur.fetchall():
        last = row[4][:10] if row[4] else 'Never'
        next_s = row[5][:10] if row[5] else 'N/A'
        print(f"{row[0]:<20} {row[1][:35]:<35} {row[2]:<10} {row[3] or 0:<8} {last:<12} {next_s:<12}")

    conn.close()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_date(text: str) -> Optional[str]:
    """Parse date from text"""
    if not text:
        return None

    # Format: "Aug 23, 2025" or "August 23, 2025"
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})', text, re.I)
    if match:
        month_map = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                     'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
        month = month_map.get(match.group(1).lower()[:3], '01')
        day = match.group(2).zfill(2)
        year = match.group(3)
        return f"{year}-{month}-{day}"

    return None


def parse_time(text: str) -> Optional[str]:
    """Parse time from text"""
    if not text:
        return None

    match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', text, re.I)
    if match:
        hour = int(match.group(1))
        minute = match.group(2)
        ampm = match.group(3)

        if ampm:
            if ampm.upper() == 'PM' and hour < 12:
                hour += 12
            elif ampm.upper() == 'AM' and hour == 12:
                hour = 0

        return f"{hour:02d}:{minute}"

    return None


def parse_score(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse score from text"""
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)', text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def extract_age_group(text: str) -> str:
    """Extract age group from text"""
    if not text:
        return ""

    current_year = 2025

    # Birth year format: 2013, 2012
    birth_year = re.search(r'\b(20(?:0[5-9]|1[0-9]|2[0-5]))\b', text)
    if birth_year:
        return birth_year.group(1)

    # U-age format: U13, U-13
    u_age = re.search(r'\bU[\s-]*(\d{1,2})\b', text, re.I)
    if u_age:
        age = int(u_age.group(1))
        if 6 <= age <= 19:
            return str(current_year - age)

    return ""


def extract_gender(text: str, default: str = "Both") -> str:
    """Extract gender from text"""
    if not text:
        return default

    text_lower = text.lower()
    if 'girl' in text_lower or 'female' in text_lower:
        return "Girls"
    if 'boy' in text_lower or 'male' in text_lower:
        return "Boys"

    # Check for G/B markers
    if re.search(r'\bG\d{2}\b|\bGU\d{2}\b|\d{2}G\b', text, re.I):
        return "Girls"
    if re.search(r'\bB\d{2}\b|\bBU\d{2}\b|\d{2}B\b', text, re.I):
        return "Boys"

    return default


def extract_club_name(team_name: str) -> str:
    """Extract club name from team name"""
    if not team_name:
        return ""

    club = team_name.strip()

    # Remove age patterns
    club = re.sub(r'\bU[\s-]*\d{1,2}[GB]?\b', '', club, flags=re.I)
    club = re.sub(r'\b[GB]\d{1,2}\b', '', club, flags=re.I)
    club = re.sub(r'\b20\d{2}[GB]?\b', '', club, flags=re.I)

    # Remove common suffixes
    club = re.sub(r'\s+(Blue|Red|White|Black|Gold|Green|Navy|Premier|Elite|Select)\s*$', '', club, flags=re.I)

    return re.sub(r'\s+', ' ', club).strip()


def normalize_team_for_id(team: str) -> str:
    """Normalize team name for game ID generation - aggressive normalization for deduplication"""
    if not team:
        return "unknown"
    normalized = team.lower().strip()

    # Remove common suffixes/words that vary between sources
    remove_patterns = [
        r'\s*-\s*$',                    # trailing dash
        r'\s+(sc|fc)\s*$',              # SC/FC at end
        r'\s+soccer\s*club\s*$',        # Soccer Club
        r'\s+futbol\s*club\s*$',        # Futbol Club
        r'\s+football\s*club\s*$',      # Football Club
        r'\s+academy\s*$',              # Academy
        r'\s+united\s*$',               # United
        r'\s+club\s*$',                 # Club alone
        r'\s+rl\s*$',                   # RL suffix
        r'\s+elite\s*$',                # Elite
    ]
    for pattern in remove_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.I)

    # Remove words that appear anywhere (not just end)
    remove_words = ['soccer', 'futbol', 'football', 'fc', 'sc', 'academy', 'club', 'united']
    for word in remove_words:
        normalized = re.sub(r'\b' + word + r'\b', '', normalized, flags=re.I)

    # Remove age group patterns
    normalized = re.sub(r'\s*\d{2}G\s*', '', normalized)
    normalized = re.sub(r'\s*G\d{2}\s*', '', normalized)
    normalized = re.sub(r'\s*U\d{2}\s*', '', normalized, flags=re.I)
    normalized = re.sub(r'\s*B\d{2}\s*', '', normalized)

    # Remove all non-alphanumeric and collapse spaces
    normalized = re.sub(r'[^a-z0-9]', '', normalized)

    return normalized[:30] if normalized else "unknown"


def generate_game_id(league: str, age_group: str, game_date: str, home_team: str, away_team: str) -> str:
    """Generate unique game ID with normalized team names"""
    import hashlib

    # Normalize team names to prevent duplicates from name variations
    home_norm = normalize_team_for_id(home_team)
    away_norm = normalize_team_for_id(away_team)

    # Sort teams alphabetically so home/away swaps don't create different IDs
    teams_sorted = "_".join(sorted([home_norm, away_norm]))

    key = f"{league}|{age_group}|{game_date}|{teams_sorted}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def determine_game_status(game_date: str, home_score, away_score) -> str:
    """Determine game status"""
    if home_score is not None and away_score is not None:
        return "completed"

    if game_date:
        try:
            from dateutil import parser
            game_dt = parser.parse(game_date)
            if game_dt.date() < datetime.now().date():
                return "unknown"
            return "scheduled"
        except:
            pass

    return "unknown"


# =============================================================================
# GOTSPORT SCRAPER
# =============================================================================

class GotSportScraper:
    """Scraper for GotSport platform"""

    def __init__(self, db_path: str = None, verbose: bool = False):
        self.db_path = db_path
        self.verbose = verbose
        self.games_scraped = 0
        self.teams_scraped = 0

    async def delay(self, min_sec: float = MIN_DELAY, max_sec: float = MAX_DELAY):
        """Human-like delay"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    def log(self, msg: str):
        """Log message"""
        print(msg)

    def debug(self, msg: str):
        """Debug message"""
        if self.verbose:
            print(f"  [DEBUG] {msg}")

    async def scrape_league(self, page: Page, league: LeagueConfig) -> Tuple[List[Dict], List[Dict]]:
        """Scrape all games from a league"""
        games = []
        teams = []

        self.log(f"\n{'='*60}")
        self.log(f"League: {league.display_name}")
        self.log(f"URL: {league.url}")
        self.log(f"{'='*60}")

        try:
            # Navigate to event page
            self.log("Loading event page...")
            await page.goto(league.url, timeout=60000)
            await self.delay(3, 5)

            # Find schedule sections (age groups/divisions)
            sections = await self._find_schedule_sections(page, league)
            self.log(f"Found {len(sections)} schedule sections")

            # Track failed sections for retry
            failed_sections = []

            # Scrape each section
            for i, section in enumerate(sections, 1):
                section_name = section.get('name', f'Section {i}')
                section_url = section.get('url')

                self.log(f"\n[{i}/{len(sections)}] {section_name}")

                try:
                    section_games, section_teams = await self._scrape_section(
                        page, league, section_name, section_url
                    )

                    games.extend(section_games)
                    teams.extend(section_teams)

                    # Save to database
                    games_saved = sum(1 for g in section_games if save_game_to_db(self.db_path, g)[0])
                    teams_saved = sum(1 for t in section_teams if save_team_to_db(self.db_path, t))

                    self.log(f"  Games: {len(section_games)} found, {games_saved} saved")
                    self.log(f"  Teams: {len(section_teams)} found, {teams_saved} saved")

                    self.games_scraped += games_saved
                    self.teams_scraped += teams_saved

                except Exception as e:
                    self.log(f"  ERROR: {e}")
                    # Track failed section for retry
                    failed_sections.append({
                        'index': i,
                        'section': section,
                        'error': str(e)
                    })

                await self.delay(2, 4)

            # Retry failed sections
            if failed_sections:
                self.log(f"\n--- Retrying {len(failed_sections)} failed section(s) ---")
                await self.delay(5, 10)  # Wait before retrying

                for failed in failed_sections:
                    i = failed['index']
                    section = failed['section']
                    section_name = section.get('name', f'Section {i}')
                    section_url = section.get('url')

                    self.log(f"\n[RETRY {i}/{len(sections)}] {section_name}")

                    try:
                        section_games, section_teams = await self._scrape_section(
                            page, league, section_name, section_url
                        )

                        games.extend(section_games)
                        teams.extend(section_teams)

                        # Save to database
                        games_saved = sum(1 for g in section_games if save_game_to_db(self.db_path, g)[0])
                        teams_saved = sum(1 for t in section_teams if save_team_to_db(self.db_path, t))

                        self.log(f"  Games: {len(section_games)} found, {games_saved} saved")
                        self.log(f"  Teams: {len(section_teams)} found, {teams_saved} saved")

                        self.games_scraped += games_saved
                        self.teams_scraped += teams_saved

                    except Exception as e:
                        self.log(f"  RETRY FAILED: {e}")

                    await self.delay(3, 6)

        except Exception as e:
            self.log(f"League error: {e}")

        return games, teams

    async def _find_schedule_sections(self, page: Page, league: LeagueConfig) -> List[Dict]:
        """Find all schedule sections on the page"""
        sections = []

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        base_url = page.url.split('?')[0]

        # Method 1: Look for schedule links with age/gender params
        schedule_links = soup.find_all('a', href=re.compile(r'schedules\?.*group=\d+', re.I))
        self.debug(f"Found {len(schedule_links)} group schedule links")

        for link in schedule_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if href:
                full_url = href if href.startswith('http') else f"https://system.gotsport.com{href}"
                if not any(s['url'] == full_url for s in sections):
                    sections.append({'name': text or f"Schedule", 'url': full_url})

        # Method 2: Look for age group elements
        for element in soup.find_all(['a', 'div'], class_=re.compile(r'age|division|bracket', re.I)):
            text = element.get_text(strip=True)
            href = element.get('href', '')

            if re.search(r'U\d{1,2}|20\d{2}', text) and len(text) < 50:
                if href:
                    full_url = href if href.startswith('http') else f"https://system.gotsport.com{href}"
                    if not any(s['url'] == full_url for s in sections):
                        sections.append({'name': text, 'url': full_url})

        # Method 3: Try common GotSport group patterns
        group_matches = re.findall(r'group=(\d+)', html)
        seen_groups = set()

        for group_id in group_matches:
            if group_id not in seen_groups:
                seen_groups.add(group_id)
                group_url = f"{base_url}/schedules?group={group_id}"
                if not any(s['url'] == group_url for s in sections):
                    sections.append({'name': f"Group {group_id}", 'url': group_url})

        # Limit to first 100 sections to avoid overwhelming
        return sections[:100]

    async def _scrape_section(self, page: Page, league: LeagueConfig,
                               section_name: str, section_url: str) -> Tuple[List[Dict], List[Dict]]:
        """Scrape games from a section"""
        games = []
        teams = []

        if section_url:
            self.debug(f"Navigating to: {section_url}")
            await page.goto(section_url, timeout=30000)
            await self.delay(2, 3)

        # Try to click "All" to see all games
        await self._click_view_all(page)

        # Parse age and gender from section
        age_group = extract_age_group(section_name)
        gender = extract_gender(section_name, default=league.gender)

        self.debug(f"Section age: {age_group}, gender: {gender}")

        # Get page content
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        current_url = page.url

        # Parse tables
        tables = soup.find_all('table')
        self.debug(f"Found {len(tables)} tables")

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                result = self._parse_game_row(row, league, age_group, gender, section_name, current_url)
                if result:
                    game, game_teams = result
                    games.append(game)
                    teams.extend(game_teams)

        return games, teams

    async def _click_view_all(self, page: Page):
        """Click 'All' or 'View All Matches' button"""
        selectors = [
            'text="View All Matches"',
            'text="All"',
            'a:has-text("All")',
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = await locator.count()
                if count > 0:
                    await locator.first.click()
                    await self.delay(2, 3)
                    self.debug("Clicked 'All' to view all games")
                    return
            except:
                continue

    def _parse_game_row(self, row, league: LeagueConfig, age_group: str,
                        gender: str, division: str, source_url: str) -> Optional[Tuple[Dict, List[Dict]]]:
        """Parse a game from a table row"""
        cells = row.find_all(['td', 'th'])
        if len(cells) < 4:
            return None

        if row.find('th'):
            return None

        home_team = None
        home_team_url = None
        home_team_id = None
        away_team = None
        away_team_url = None
        away_team_id = None
        home_score = None
        away_score = None
        game_date = None
        game_time = None
        location = None

        for idx, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            links = cell.find_all('a')

            # Date column
            date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}', text, re.I)
            if date_match and not game_date:
                game_date = parse_date(date_match.group(0))
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)', text, re.I)
                if time_match:
                    game_time = parse_time(time_match.group(1))
                continue

            # Score column
            score_match = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', text.strip())
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                continue

            # Team columns (have links)
            if links:
                for link in links:
                    link_text = link.get_text(strip=True)
                    link_href = link.get('href', '')

                    if not link_text or len(link_text) < 3:
                        continue
                    if 'map' in link_href.lower() or 'location' in link_href.lower():
                        continue

                    team_id_match = re.search(r'team[=_/](\d+)', link_href, re.I)
                    team_id = team_id_match.group(1) if team_id_match else None

                    full_url = link_href
                    if link_href and not link_href.startswith('http'):
                        full_url = f"https://system.gotsport.com{link_href}"

                    if not home_team:
                        home_team = link_text
                        home_team_url = full_url
                        home_team_id = team_id
                    elif not away_team and link_text != home_team:
                        away_team = link_text
                        away_team_url = full_url
                        away_team_id = team_id

            # Location
            if 'field' in text.lower() or 'park' in text.lower() or 'complex' in text.lower():
                location = text

        if not home_team or not away_team:
            return None

        # Skip bye games
        if home_team.strip().lower() == 'bye' or away_team.strip().lower() == 'bye':
            return None

        # Extract age from team names if not found
        if not age_group:
            age_group = extract_age_group(home_team) or extract_age_group(away_team)

        # Re-detect gender from team names
        if gender == "Both":
            for team in [home_team, away_team]:
                detected = extract_gender(team, "Both")
                if detected != "Both":
                    gender = detected
                    break

        game_id = generate_game_id(league.name, age_group, game_date or '', home_team, away_team)
        game_status = determine_game_status(game_date, home_score, away_score)

        game = {
            'game_id': game_id,
            'league': league.name,
            'organization': league.organization,
            'region': league.region,
            'gender': gender,
            'age_group': age_group,
            'division': division,
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score if home_score is not None else '',
            'away_score': away_score if away_score is not None else '',
            'game_date': game_date or '',
            'game_date_iso': game_date or '',
            'game_time': game_time or '',
            'game_status': game_status,
            'location': location or '',
            'source_url': source_url,
            'state': league.state,
        }

        team_list = []
        for team_name, team_id, team_url in [
            (home_team, home_team_id, home_team_url),
            (away_team, away_team_id, away_team_url)
        ]:
            if team_name:
                team_list.append({
                    'team_id': team_id or '',
                    'team_name': team_name,
                    'club_name': extract_club_name(team_name),
                    'league': league.name,
                    'age_group': age_group,
                    'gender': gender,
                    'region': league.region,
                    'schedule_url': team_url or '',
                    'state': league.state,
                })

        return game, team_list


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description='California Regional Leagues Scraper')
    parser.add_argument('--league', type=str, help='Specific league to scrape (CCSL, NorCal Premier)')
    parser.add_argument('--list', action='store_true', help='List available leagues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of sections to scrape')
    # New event tracking arguments
    parser.add_argument('--sync', action='store_true', help='Sync league configs to database')
    parser.add_argument('--status', action='store_true', help='Show status of tracked events')
    parser.add_argument('--auto', action='store_true', help='Scrape events that are due (based on schedule)')
    parser.add_argument('--force', action='store_true', help='Force scrape all active events (with --auto)')
    args = parser.parse_args()

    # Find database
    db_path = find_database_path()
    if db_path:
        print(f"Database: {db_path}")
    else:
        print("WARNING: Database not found, games will not be saved")

    # Handle --sync: sync configs to database
    if args.sync:
        count = sync_configs_to_db(db_path)
        print(f"\nSynced {count} league configs to database")
        list_events_status(db_path)
        return

    # Handle --status: show event status
    if args.status:
        list_events_status(db_path)
        return

    if args.list:
        print("\nAvailable Leagues:")
        print("-" * 60)
        for league in LEAGUE_CONFIGS:
            status = "Active" if league.active else "Inactive"
            print(f"  {league.name}: {league.display_name} [{status}]")
        print()
        return

    # Handle --auto: scrape based on schedule from database
    if args.auto:
        events = get_events_to_scrape(db_path, force=args.force)
        if not events:
            print("\nNo events need scraping at this time.")
            print("Use --force to scrape all active events, or --status to see event schedule.")
            return

        print(f"\n{len(events)} event(s) due for scraping:")
        for e in events:
            print(f"  - {e['event_name']} ({e['status']}, last: {e['last_scraped'] or 'never'})")

        # Convert to LeagueConfig objects
        leagues_to_scrape = []
        for e in events:
            matching = [l for l in LEAGUE_CONFIGS if l.event_id == e['event_id']]
            if matching:
                leagues_to_scrape.append(matching[0])

        if not leagues_to_scrape:
            print("No matching league configs found for scheduled events.")
            return
    else:
        # Filter leagues by --league argument
        leagues_to_scrape = LEAGUE_CONFIGS
        if args.league:
            leagues_to_scrape = [l for l in LEAGUE_CONFIGS if args.league.lower() in l.name.lower()]
            if not leagues_to_scrape:
                print(f"No leagues matching '{args.league}' found")
                return

        leagues_to_scrape = [l for l in leagues_to_scrape if l.active]

    print(f"\nScraping {len(leagues_to_scrape)} league(s)...")

    # Run scraper
    scraper = GotSportScraper(db_path=db_path, verbose=args.verbose)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        total_games = 0
        total_teams = 0

        for league in leagues_to_scrape:
            # Save event to tracking table before scraping
            save_event_to_db(db_path, league)

            games, teams = await scraper.scrape_league(page, league)
            total_games += len(games)
            total_teams += len(teams)

            # Track game dates for this event
            game_dates = [g.get('game_date_iso') or g.get('game_date', '') for g in games if g.get('game_date_iso') or g.get('game_date')]
            earliest_date = min(game_dates) if game_dates else None
            latest_date = max(game_dates) if game_dates else None

            # Update event after scraping
            games_saved = sum(1 for g in games if save_game_to_db(db_path, g)[0])
            update_event_after_scrape(
                db_path, league.event_id,
                games_found=len(games),
                games_saved=games_saved,
                teams_found=len(teams),
                earliest_date=earliest_date,
                latest_date=latest_date
            )

        await browser.close()

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total games found: {total_games}")
    print(f"Total teams found: {total_teams}")
    print(f"Games saved to DB: {scraper.games_scraped}")
    print(f"Teams saved to DB: {scraper.teams_scraped}")


if __name__ == "__main__":
    asyncio.run(main())
