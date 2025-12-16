"""
FILENAME: ga_complete_all_ages_scraper.py

Girls Academy Complete All-Ages Team Scraper

This script:
1. Uses the division URLs extracted by ga_division_url_finder.py
2. Scrapes ALL teams from ALL divisions for ALL age groups
3. Creates a complete team list ready for game scraping

USAGE:
    Step 1: Extract division URLs
        python ga_division_url_finder.py
    
    Step 2: Scrape all teams
        python ga_complete_all_ages_scraper.py
        
OUTPUT:
    ga_teams_all_ages_complete.json - ALL teams with IDs (~840 teams)
"""

import json
import time
import re
from typing import List, Dict, Set
import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

DIVISION_URLS_FILE = "ga_division_urls.json"
OUTPUT_FILE = "ga_teams_all_ages_complete.json"
EVENT_ID = "42137"
RATE_LIMIT = 1.0

# ============================================================================


class CompleteAllAgesScraper:
    """Scrape all teams from all divisions for all age groups."""
    
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        
        self.all_teams: Dict[str, Dict] = {}
        self.teams_by_age: Dict[str, List[Dict]] = {}
        self.division_urls: Dict[str, List[Dict]] = {}
    
    def _sleep(self):
        time.sleep(self.rate_limit)
    
    def load_division_urls(self, urls_file: str):
        """Load division URLs from JSON file."""
        try:
            with open(urls_file, 'r', encoding='utf-8') as f:
                self.division_urls = json.load(f)
            
            total = sum(len(divs) for divs in self.division_urls.values())
            print(f"Loaded {total} division URLs across {len(self.division_urls)} age groups")
        except FileNotFoundError:
            print(f"[ERROR] {urls_file} not found!")
            print("Run ga_division_url_finder.py first to generate this file.")
            raise
    
    def extract_club_name(self, team_name: str) -> str:
        """Extract core club name from full team name."""
        club = re.sub(
            r'\s*(2013|2012|2011|2010|2009|2008|2007|U1[3-9]|1[0-3]G|0[7-9]G)\s*',
            ' ',
            team_name,
            flags=re.IGNORECASE
        )
        club = re.sub(r'\s*(GA|Girls Academy)\s*$', '', club, flags=re.IGNORECASE)
        club = re.sub(r'\s+', ' ', club).strip()
        return club
    
    def scrape_division(self, division_info: Dict) -> List[Dict]:
        """Scrape all teams from a single division."""
        url = division_info["url"]
        age_group = division_info["age_group"]
        division = division_info["division"]
        
        self._sleep()
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"      [ERROR] Failed: {e}")
            return []
        
        soup = BeautifulSoup(resp.content, "html.parser")
        
        teams = {}
        team_links = soup.find_all('a', href=re.compile(r'schedules\?team=\d+'))
        
        for link in team_links:
            href = link.get('href', '')
            team_text = link.get_text(strip=True)
            
            match = re.search(r'team=(\d+)', href)
            if not match:
                continue
            
            team_id = match.group(1)
            team_name = re.sub(r'\s*\([HAhVvAa]\)\s*$', '', team_text).strip()
            
            if not team_name:
                continue
            
            # Validate GA team
            name_upper = team_name.upper()
            has_ga = "GA" in name_upper or "GIRLS ACADEMY" in name_upper
            
            # Check for age match (flexible to catch variations)
            age_patterns = {
                "U13": ["2013", "13G", "U13"],
                "U14": ["2012", "12G", "U14"],
                "U15": ["2011", "11G", "U15"],
                "U16": ["2010", "10G", "U16"],
                "U17": ["2009", "09G", "U17"],
                "U18": ["2008", "08G", "U18"],
                "U19": ["2007", "07G", "U19"],
            }
            
            has_age = False
            if age_group in age_patterns:
                has_age = any(pattern in name_upper for pattern in age_patterns[age_group])
            
            if not (has_ga and has_age):
                continue
            
            club_name = self.extract_club_name(team_name)
            
            teams[team_id] = {
                "event_id": EVENT_ID,
                "team_id": team_id,
                "team_name": team_name,
                "club_name": club_name,
                "conference": division,
                "age_group": age_group,
                "group_id": division_info.get("group_id", "")
            }
        
        return list(teams.values())
    
    def scrape_all_divisions(self):
        """Scrape teams from all divisions across all age groups."""
        print("\n" + "="*70)
        print("SCRAPING ALL DIVISIONS - ALL AGE GROUPS")
        print("="*70)
        
        total_divisions = sum(len(divs) for divs in self.division_urls.values())
        current = 0
        
        for age_group in sorted(self.division_urls.keys()):
            divisions = self.division_urls[age_group]
            
            print(f"\n{'='*70}")
            print(f"{age_group} ({len(divisions)} divisions)")
            print(f"{'='*70}")
            
            age_teams = []
            
            for i, division_info in enumerate(divisions, 1):
                current += 1
                division_name = division_info["division"]
                
                print(f"  [{current}/{total_divisions}] {division_name}... ", end="", flush=True)
                
                teams = self.scrape_division(division_info)
                print(f"found {len(teams)} teams")
                
                age_teams.extend(teams)
                
                # Add to global teams (deduplicate)
                for team in teams:
                    team_key = f"{team['team_id']}_{age_group}"
                    if team_key not in self.all_teams:
                        self.all_teams[team_key] = team
            
            # Deduplicate by team_id within age group
            unique_teams = {}
            for team in age_teams:
                unique_teams[team['team_id']] = team
            
            self.teams_by_age[age_group] = list(unique_teams.values())
            
            print(f"  ✓ {age_group}: {len(unique_teams)} unique teams")
        
        print("\n" + "="*70)
        print("SCRAPING COMPLETE!")
        print("="*70)
        print(f"Total unique teams: {len(self.all_teams)}")
        print()
        print("Teams by age group:")
        for age in sorted(self.teams_by_age.keys()):
            print(f"  {age}: {len(self.teams_by_age[age])} teams")
        print("="*70)
    
    def save_results(self, output_file: str):
        """Save all teams to JSON."""
        teams_list = sorted(
            self.all_teams.values(),
            key=lambda x: (x["age_group"], x.get("conference", ""), x["team_name"])
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(teams_list, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(teams_list)} teams to {output_file}")
        
        # Save summary
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Girls Academy Teams - All Ages Complete\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total teams: {len(teams_list)}\n\n")
            
            for age in sorted(self.teams_by_age.keys()):
                teams = self.teams_by_age[age]
                f.write(f"\n{age} ({len(teams)} teams)\n")
                f.write("-"*70 + "\n")
                
                # Group by conference
                by_conf = {}
                for team in teams:
                    conf = team.get("conference", "Unknown")
                    if conf not in by_conf:
                        by_conf[conf] = []
                    by_conf[conf].append(team)
                
                for conf in sorted(by_conf.keys()):
                    conf_teams = sorted(by_conf[conf], key=lambda x: x['team_name'])
                    f.write(f"\n  {conf} ({len(conf_teams)} teams):\n")
                    for i, team in enumerate(conf_teams, 1):
                        f.write(f"    {i:2d}. {team['team_name']:<45} (ID: {team['team_id']})\n")
        
        print(f"✓ Saved summary to {summary_file}")
        
        # Save CSV
        csv_file = output_file.replace('.json', '.csv')
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            import csv
            writer = csv.DictWriter(f, fieldnames=[
                'age_group', 'conference', 'club_name', 'team_name', 
                'team_id', 'event_id', 'group_id'
            ])
            writer.writeheader()
            writer.writerows(teams_list)
        
        print(f"✓ Saved CSV to {csv_file}")


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("GIRLS ACADEMY COMPLETE ALL-AGES SCRAPER")
    print("="*70)
    print()
    print("This will scrape ALL teams from ALL divisions for ALL age groups")
    print("using the division URLs you provided.")
    print()
    
    scraper = CompleteAllAgesScraper(rate_limit=RATE_LIMIT)
    
    try:
        scraper.load_division_urls(DIVISION_URLS_FILE)
    except Exception:
        return
    
    print()
    input("Press Enter to start scraping... ")
    
    try:
        scraper.scrape_all_divisions()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED]")
    except Exception as e:
        print(f"\n\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
    
    if scraper.all_teams:
        scraper.save_results(OUTPUT_FILE)
        
        print("\n" + "="*70)
        print("SUCCESS! ALL TEAMS DISCOVERED")
        print("="*70)
        print()
        print("Next step: Scrape all games")
        print(f"  python run_ga_simple_scraper.py --teams-json {OUTPUT_FILE}")
        print()
        print("This will scrape games for ALL ~840 GA teams!")
        print("Estimated time: 15-20 minutes")
        print("="*70)


if __name__ == "__main__":
    main()