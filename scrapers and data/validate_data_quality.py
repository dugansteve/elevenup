"""
Data Quality Validation Script for Seedline Database
Checks for common data quality issues and reports findings.

Usage:
    python validate_data_quality.py
    python validate_data_quality.py --fix  # Apply automatic fixes
"""

import sqlite3
import re
import argparse
from collections import defaultdict
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "seedlinedata.db"


def get_connection():
    """Get database connection."""
    return sqlite3.connect(str(DB_PATH))


def check_trailing_dashes(conn):
    """Check for team names with trailing dashes."""
    cursor = conn.cursor()
    issues = []

    # Check games table
    cursor.execute("""
        SELECT DISTINCT home_team FROM games
        WHERE home_team LIKE '% -' OR home_team LIKE '%-'
    """)
    home_teams = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT away_team FROM games
        WHERE away_team LIKE '% -' OR away_team LIKE '%-'
    """)
    away_teams = [row[0] for row in cursor.fetchall()]

    # Check teams table
    cursor.execute("""
        SELECT DISTINCT team_name FROM teams
        WHERE team_name LIKE '% -' OR team_name LIKE '%-'
    """)
    team_names = [row[0] for row in cursor.fetchall()]

    all_issues = set(home_teams + away_teams + team_names)
    if all_issues:
        issues.append({
            'type': 'trailing_dash',
            'count': len(all_issues),
            'examples': list(all_issues)[:10],
            'severity': 'HIGH'
        })

    return issues


def check_known_typos(conn):
    """Check for known typos in team names."""
    cursor = conn.cursor()
    issues = []

    typos = [
        # Use specific patterns to avoid false positives
        # ('Ethesda', 'Bethesda') - already fixed, skip to avoid false positive on 'Bethesda'
        ('Socccer', 'Soccer'),
        ('Acadamy', 'Academy'),
        ('Athletico', 'Atletico'),
    ]

    for typo, correct in typos:
        cursor.execute(f"""
            SELECT COUNT(*) FROM games
            WHERE home_team LIKE '%{typo}%' OR away_team LIKE '%{typo}%'
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute(f"""
                SELECT DISTINCT home_team FROM games WHERE home_team LIKE '%{typo}%'
                UNION
                SELECT DISTINCT away_team FROM games WHERE away_team LIKE '%{typo}%'
            """)
            examples = [row[0] for row in cursor.fetchall()]
            issues.append({
                'type': 'typo',
                'typo': typo,
                'correct': correct,
                'count': count,
                'examples': examples[:5],
                'severity': 'HIGH'
            })

    return issues


def check_age_groups_in_team_names(conn):
    """Check for age group patterns embedded in team names."""
    cursor = conn.cursor()
    issues = []

    # Pattern: team name ending with B13, G12, etc.
    # SQLite doesn't have REGEXP by default, use LIKE approximation
    cursor.execute("""
        SELECT DISTINCT home_team FROM games
        WHERE home_team LIKE '% B__' OR home_team LIKE '% G__'
        OR home_team LIKE '% B__ %' OR home_team LIKE '% G__ %'
    """)
    teams_with_age = [row[0] for row in cursor.fetchall()]

    # Filter to only those with actual age patterns
    age_pattern = re.compile(r'\s[BG]\d{2}(\s|$)', re.I)
    filtered = [t for t in teams_with_age if age_pattern.search(t)]

    if filtered:
        issues.append({
            'type': 'age_in_team_name',
            'count': len(filtered),
            'examples': filtered[:10],
            'severity': 'MEDIUM'
        })

    return issues


def check_orphan_teams(conn):
    """Check for teams that appear in games but not in teams table."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT g.home_team, g.league, g.age_group, COUNT(*) as game_count
        FROM games g
        LEFT JOIN teams t ON g.home_team = t.team_name
        WHERE t.team_name IS NULL
        GROUP BY g.home_team, g.league, g.age_group
        ORDER BY game_count DESC
        LIMIT 50
    """)
    orphan_home = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT g.away_team, g.league, g.age_group, COUNT(*) as game_count
        FROM games g
        LEFT JOIN teams t ON g.away_team = t.team_name
        WHERE t.team_name IS NULL
        GROUP BY g.away_team, g.league, g.age_group
        ORDER BY game_count DESC
        LIMIT 50
    """)
    orphan_away = cursor.fetchall()

    # Combine and dedupe
    orphans = {}
    for team, league, age, count in orphan_home + orphan_away:
        key = (team, league, age)
        orphans[key] = orphans.get(key, 0) + count

    if orphans:
        top_orphans = sorted(orphans.items(), key=lambda x: -x[1])[:20]
        return [{
            'type': 'orphan_teams',
            'count': len(orphans),
            'examples': [f"{t[0]} ({t[1]}/{t[2]}): {c} games" for t, c in top_orphans],
            'severity': 'MEDIUM'
        }]

    return []


def check_duplicate_games(conn):
    """Check for potential duplicate games."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT game_date, home_team, away_team, home_score, away_score, league, age_group,
               COUNT(*) as dup_count
        FROM games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        GROUP BY game_date, home_team, away_team, home_score, away_score, league, age_group
        HAVING COUNT(*) > 1
        ORDER BY dup_count DESC
        LIMIT 20
    """)
    duplicates = cursor.fetchall()

    if duplicates:
        examples = [
            f"{row[0]}: {row[1]} vs {row[2]} ({row[3]}-{row[4]}) [{row[5]}/{row[6]}] x{row[7]}"
            for row in duplicates
        ]
        total_dups = sum(row[7] - 1 for row in duplicates)  # Extra copies
        return [{
            'type': 'duplicate_games',
            'count': total_dups,
            'examples': examples,
            'severity': 'HIGH'
        }]

    return []


def check_teams_missing_club(conn):
    """Check for teams with missing club_name."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM teams WHERE club_name IS NULL OR club_name = ''
    """)
    missing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teams")
    total = cursor.fetchone()[0]

    if missing > 0:
        cursor.execute("""
            SELECT team_name, league FROM teams
            WHERE club_name IS NULL OR club_name = ''
            LIMIT 10
        """)
        examples = [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]
        return [{
            'type': 'missing_club_name',
            'count': missing,
            'total': total,
            'percentage': round(100 * missing / total, 1) if total > 0 else 0,
            'examples': examples,
            'severity': 'MEDIUM'
        }]

    return []


def check_team_name_variants(conn):
    """Check for team name variants that might be duplicates."""
    cursor = conn.cursor()

    # Get all unique team names
    cursor.execute("""
        SELECT DISTINCT team FROM (
            SELECT home_team as team FROM games
            UNION
            SELECT away_team as team FROM games
        )
    """)
    all_teams = [row[0] for row in cursor.fetchall()]

    # Normalize for comparison
    def normalize(name):
        n = name.lower()
        n = re.sub(r'\s*\([^)]*\)', '', n)  # Remove parentheticals
        n = re.sub(r'\s*-\s*$', '', n)  # Remove trailing dashes
        n = re.sub(r'[^a-z0-9]', '', n)  # Keep only alphanumeric
        return n

    # Group by normalized name
    groups = defaultdict(list)
    for team in all_teams:
        groups[normalize(team)].append(team)

    # Find groups with multiple variants
    variants = {k: v for k, v in groups.items() if len(v) > 1}

    if variants:
        examples = []
        for norm, names in sorted(variants.items(), key=lambda x: -len(x[1]))[:10]:
            examples.append(f"{names[0]}: {names}")

        return [{
            'type': 'team_name_variants',
            'count': len(variants),
            'examples': examples,
            'severity': 'HIGH'
        }]

    return []


def fix_trailing_dashes(conn):
    """Fix trailing dashes in team names."""
    cursor = conn.cursor()

    cursor.execute("UPDATE games SET home_team = RTRIM(home_team, ' -') WHERE home_team LIKE '% -'")
    home_fixed = cursor.rowcount

    cursor.execute("UPDATE games SET away_team = RTRIM(away_team, ' -') WHERE away_team LIKE '% -'")
    away_fixed = cursor.rowcount

    cursor.execute("UPDATE teams SET team_name = RTRIM(team_name, ' -') WHERE team_name LIKE '% -'")
    teams_fixed = cursor.rowcount

    conn.commit()
    return home_fixed, away_fixed, teams_fixed


def fix_typos(conn):
    """Fix known typos."""
    cursor = conn.cursor()

    typos = [
        ('Ethesda', 'Bethesda'),
    ]

    total_fixed = 0
    for typo, correct in typos:
        cursor.execute(f"UPDATE games SET home_team = REPLACE(home_team, '{typo}', '{correct}') WHERE home_team LIKE '%{typo}%'")
        total_fixed += cursor.rowcount
        cursor.execute(f"UPDATE games SET away_team = REPLACE(away_team, '{typo}', '{correct}') WHERE away_team LIKE '%{typo}%'")
        total_fixed += cursor.rowcount

    conn.commit()
    return total_fixed


def main():
    parser = argparse.ArgumentParser(description='Validate Seedline database data quality')
    parser.add_argument('--fix', action='store_true', help='Apply automatic fixes')
    args = parser.parse_args()

    print("=" * 60)
    print("SEEDLINE DATA QUALITY VALIDATION REPORT")
    print("=" * 60)
    print()

    conn = get_connection()

    all_issues = []

    # Run all checks
    checks = [
        ("Trailing Dashes", check_trailing_dashes),
        ("Known Typos", check_known_typos),
        ("Age Groups in Team Names", check_age_groups_in_team_names),
        ("Orphan Teams", check_orphan_teams),
        ("Duplicate Games", check_duplicate_games),
        ("Missing Club Names", check_teams_missing_club),
        ("Team Name Variants", check_team_name_variants),
    ]

    for name, check_func in checks:
        print(f"Checking: {name}...")
        issues = check_func(conn)
        all_issues.extend(issues)

    print()
    print("-" * 60)
    print("RESULTS")
    print("-" * 60)
    print()

    if not all_issues:
        print("No data quality issues found!")
    else:
        # Group by severity
        high = [i for i in all_issues if i.get('severity') == 'HIGH']
        medium = [i for i in all_issues if i.get('severity') == 'MEDIUM']
        low = [i for i in all_issues if i.get('severity') == 'LOW']

        for severity, issues in [('HIGH', high), ('MEDIUM', medium), ('LOW', low)]:
            if issues:
                print(f"\n[{severity} SEVERITY]")
                for issue in issues:
                    print(f"\n  {issue['type'].upper()}")
                    print(f"  Count: {issue['count']}")
                    if 'examples' in issue:
                        print("  Examples:")
                        for ex in issue['examples'][:5]:
                            print(f"    - {ex}")

    print()
    print("-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"Total issue types found: {len(all_issues)}")
    print(f"  HIGH severity: {len([i for i in all_issues if i.get('severity') == 'HIGH'])}")
    print(f"  MEDIUM severity: {len([i for i in all_issues if i.get('severity') == 'MEDIUM'])}")
    print(f"  LOW severity: {len([i for i in all_issues if i.get('severity') == 'LOW'])}")

    if args.fix:
        print()
        print("-" * 60)
        print("APPLYING FIXES")
        print("-" * 60)

        # Fix trailing dashes
        home, away, teams = fix_trailing_dashes(conn)
        print(f"Fixed trailing dashes: {home} home_team, {away} away_team, {teams} teams")

        # Fix typos
        typo_fixed = fix_typos(conn)
        print(f"Fixed typos: {typo_fixed} entries")

        print()
        print("Fixes applied successfully!")

    conn.close()
    print()


if __name__ == "__main__":
    main()
