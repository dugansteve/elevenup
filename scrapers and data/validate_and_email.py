"""
Data Quality Validation Script with Email Reporting
Runs validation checks and emails results to configured recipient.

Usage:
    python validate_and_email.py
    python validate_and_email.py --test  # Send test email only
"""

import sqlite3
import re
import argparse
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from pathlib import Path
from datetime import datetime

# Configuration
DB_PATH = Path(__file__).parent / "seedlinedata.db"
RECIPIENT_EMAIL = "dugansteve@gmail.com"
SENDER_EMAIL = os.environ.get("SEEDLINE_EMAIL", "dugansteve@gmail.com")
SENDER_PASSWORD = os.environ.get("SEEDLINE_EMAIL_PASSWORD", "")

# Gmail SMTP settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def get_connection():
    """Get database connection."""
    return sqlite3.connect(str(DB_PATH))


def check_trailing_dashes(conn):
    """Check for team names with trailing dashes, grouped by league."""
    cursor = conn.cursor()
    issues = []

    # Get trailing dash issues with league attribution
    cursor.execute("""
        SELECT DISTINCT home_team, league FROM games
        WHERE home_team LIKE '% -' OR home_team LIKE '%-'
        UNION
        SELECT DISTINCT away_team, league FROM games
        WHERE away_team LIKE '% -' OR away_team LIKE '%-'
    """)
    results = cursor.fetchall()

    if results:
        # Group by league
        by_league = defaultdict(list)
        for team, league in results:
            by_league[league or 'Unknown'].append(team)

        league_summary = ", ".join(f"{league}: {len(teams)}" for league, teams in sorted(by_league.items(), key=lambda x: -len(x[1])))
        examples = [f"{row[0]} ({row[1]})" for row in results[:5]]

        issues.append({
            'type': 'trailing_dash',
            'count': len(results),
            'examples': examples,
            'by_league': dict(by_league),
            'league_summary': league_summary,
            'severity': 'HIGH'
        })

    return issues


def check_known_typos(conn):
    """Check for known typos in team names, grouped by league."""
    cursor = conn.cursor()
    issues = []

    typos = [
        ('Socccer', 'Soccer'),
        ('Acadamy', 'Academy'),
        ('Untied', 'United'),
        ('Fcotball', 'Football'),
    ]

    for typo, correct in typos:
        cursor.execute(f"""
            SELECT home_team, league FROM games WHERE home_team LIKE '%{typo}%'
            UNION
            SELECT away_team, league FROM games WHERE away_team LIKE '%{typo}%'
        """)
        results = cursor.fetchall()

        if results:
            # Group by league
            by_league = defaultdict(list)
            for team, league in results:
                by_league[league or 'Unknown'].append(team)

            league_summary = ", ".join(f"{league}: {len(teams)}" for league, teams in sorted(by_league.items(), key=lambda x: -len(x[1])))
            examples = [f"{row[0]} ({row[1]})" for row in results[:3]]

            issues.append({
                'type': 'typo',
                'typo': typo,
                'correct': correct,
                'count': len(results),
                'examples': examples,
                'by_league': dict(by_league),
                'league_summary': league_summary,
                'severity': 'HIGH'
            })

    return issues


def check_duplicate_games(conn):
    """Check for potential duplicate games, grouped by league."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT game_date, home_team, away_team, home_score, away_score, league, age_group,
               COUNT(*) as dup_count
        FROM games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        GROUP BY game_date, home_team, away_team, home_score, away_score, league, age_group
        HAVING COUNT(*) > 1
        ORDER BY dup_count DESC
        LIMIT 50
    """)
    duplicates = cursor.fetchall()

    if duplicates:
        # Group by league
        by_league = defaultdict(int)
        for row in duplicates:
            league = row[5] or 'Unknown'
            by_league[league] += row[7] - 1  # Count extra copies

        league_summary = ", ".join(f"{league}: {count}" for league, count in sorted(by_league.items(), key=lambda x: -x[1]))
        examples = [
            f"{row[0]}: {row[1]} vs {row[2]} ({row[3]}-{row[4]}) [{row[5]}]"
            for row in duplicates[:5]
        ]
        total_dups = sum(row[7] - 1 for row in duplicates)

        return [{
            'type': 'duplicate_games',
            'count': total_dups,
            'examples': examples,
            'by_league': dict(by_league),
            'league_summary': league_summary,
            'severity': 'HIGH'
        }]

    return []


def check_database_stats(conn):
    """Get overall database statistics including per-league breakdown."""
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) FROM games")
    stats['total_games'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teams")
    stats['total_teams'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT league) FROM games")
    stats['leagues'] = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(game_date), MAX(game_date) FROM games WHERE game_date IS NOT NULL")
    row = cursor.fetchone()
    stats['date_range'] = f"{row[0]} to {row[1]}"

    cursor.execute("""
        SELECT COUNT(*) FROM games
        WHERE scraped_at > datetime('now', '-7 days')
    """)
    stats['games_added_last_week'] = cursor.fetchone()[0]

    # Get games added per league in last 7 days (shows which scrapers ran)
    cursor.execute("""
        SELECT league, COUNT(*) as count
        FROM games
        WHERE scraped_at > datetime('now', '-7 days')
        GROUP BY league
        ORDER BY count DESC
    """)
    stats['games_by_league'] = {row[0] or 'Unknown': row[1] for row in cursor.fetchall()}

    # Get recent scrape activity (last scrape per league)
    cursor.execute("""
        SELECT league, MAX(scraped_at) as last_scrape
        FROM games
        GROUP BY league
        ORDER BY last_scrape DESC
    """)
    stats['last_scrape_by_league'] = {row[0] or 'Unknown': row[1] for row in cursor.fetchall()}

    return stats


def run_validation(conn):
    """Run all validation checks and return results."""
    all_issues = []

    checks = [
        ("Trailing Dashes", check_trailing_dashes),
        ("Known Typos", check_known_typos),
        ("Duplicate Games", check_duplicate_games),
    ]

    for name, check_func in checks:
        issues = check_func(conn)
        all_issues.extend(issues)

    stats = check_database_stats(conn)

    return all_issues, stats


def format_email_body(issues, stats):
    """Format the validation results as an email body."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Format games by league for display
    games_by_league_html = ""
    games_by_league_text = ""
    if stats.get('games_by_league'):
        games_by_league_html = "<table style='margin-left: 20px; font-size: 14px;'>"
        for league, count in stats['games_by_league'].items():
            games_by_league_html += f"<tr><td style='padding-right: 15px;'>{league}</td><td style='text-align: right;'>{count:,}</td></tr>"
        games_by_league_html += "</table>"

        for league, count in stats['games_by_league'].items():
            games_by_league_text += f"    {league}: {count:,}\n"

    # Build HTML email
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c5282; }}
            h2 {{ color: #4a5568; margin-top: 20px; }}
            h3 {{ color: #718096; margin-top: 15px; font-size: 14px; }}
            .stats {{ background: #f7fafc; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            .stat-item {{ margin: 5px 0; }}
            .stat-label {{ font-weight: bold; color: #4a5568; }}
            .issue {{ background: #fff5f5; border-left: 4px solid #fc8181; padding: 10px; margin: 10px 0; }}
            .issue-high {{ border-left-color: #fc8181; background: #fff5f5; }}
            .issue-medium {{ border-left-color: #f6ad55; background: #fffaf0; }}
            .no-issues {{ background: #f0fff4; border-left: 4px solid #68d391; padding: 15px; }}
            .examples {{ font-size: 12px; color: #718096; margin-top: 5px; }}
            .league-breakdown {{ font-size: 12px; color: #4a5568; margin-top: 5px; background: #edf2f7; padding: 5px 10px; border-radius: 4px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #a0aec0; }}
        </style>
    </head>
    <body>
        <h1>Seedline Data Quality Report</h1>
        <p>Weekly validation run: {now}</p>

        <div class="stats">
            <h2>Database Statistics</h2>
            <div class="stat-item"><span class="stat-label">Total Games:</span> {stats['total_games']:,}</div>
            <div class="stat-item"><span class="stat-label">Total Teams:</span> {stats['total_teams']:,}</div>
            <div class="stat-item"><span class="stat-label">Leagues:</span> {stats['leagues']}</div>
            <div class="stat-item"><span class="stat-label">Date Range:</span> {stats['date_range']}</div>
            <div class="stat-item"><span class="stat-label">Games Added (Last 7 Days):</span> {stats['games_added_last_week']:,}</div>

            <h3>Games Added by League/Scraper (Last 7 Days):</h3>
            {games_by_league_html if games_by_league_html else "<p style='color: #a0aec0;'>No games added in the last 7 days</p>"}
        </div>

        <h2>Data Quality Issues</h2>
    """

    if not issues:
        html += '<div class="no-issues">No data quality issues found!</div>'
    else:
        high = [i for i in issues if i.get('severity') == 'HIGH']
        medium = [i for i in issues if i.get('severity') == 'MEDIUM']

        for issue in high + medium:
            severity_class = 'issue-high' if issue.get('severity') == 'HIGH' else 'issue-medium'
            html += f"""
            <div class="issue {severity_class}">
                <strong>{issue['type'].upper()}</strong> - {issue['count']} found
            """
            if 'typo' in issue:
                html += f"<br>Typo: '{issue['typo']}' should be '{issue['correct']}'"
            if 'league_summary' in issue:
                html += f'<div class="league-breakdown"><strong>By Scraper/League:</strong> {issue["league_summary"]}</div>'
            if 'examples' in issue and issue['examples']:
                html += f'<div class="examples">Examples: {", ".join(str(e)[:60] for e in issue["examples"][:3])}</div>'
            html += "</div>"

    html += f"""
        <div class="footer">
            <p>This is an automated report from Seedline Data Quality Validation.</p>
            <p>To run manually: python validate_data_quality.py</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text = f"""
SEEDLINE DATA QUALITY REPORT
Weekly validation run: {now}

DATABASE STATISTICS
-------------------
Total Games: {stats['total_games']:,}
Total Teams: {stats['total_teams']:,}
Leagues: {stats['leagues']}
Date Range: {stats['date_range']}
Games Added (Last 7 Days): {stats['games_added_last_week']:,}

Games Added by League/Scraper:
{games_by_league_text if games_by_league_text else "    No games added in the last 7 days"}

DATA QUALITY ISSUES
-------------------
"""
    if not issues:
        text += "No data quality issues found!\n"
    else:
        for issue in issues:
            text += f"\n[{issue.get('severity', 'UNKNOWN')}] {issue['type'].upper()}: {issue['count']} found\n"
            if 'league_summary' in issue:
                text += f"  By Scraper/League: {issue['league_summary']}\n"
            if 'examples' in issue:
                for ex in issue['examples'][:3]:
                    text += f"  - {str(ex)[:70]}\n"

    text += "\n---\nAutomated report from Seedline Data Quality Validation\n"

    return html, text


def send_email(subject, html_body, text_body):
    """Send email with the validation results."""
    if not SENDER_PASSWORD:
        print("ERROR: SEEDLINE_EMAIL_PASSWORD environment variable not set!")
        print("Please set it with your Gmail App Password.")
        print("See: https://support.google.com/accounts/answer/185833")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL

    # Attach both plain text and HTML versions
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')
    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Validate Seedline database and email results')
    parser.add_argument('--test', action='store_true', help='Send test email only')
    parser.add_argument('--no-email', action='store_true', help='Run validation without sending email')
    args = parser.parse_args()

    if args.test:
        # Send test email
        subject = "Seedline Data Quality Report - TEST"
        html = "<html><body><h1>Test Email</h1><p>This is a test email from Seedline validation.</p></body></html>"
        text = "Test Email\n\nThis is a test email from Seedline validation."
        send_email(subject, html, text)
        return

    print("Running Seedline data quality validation...")

    conn = get_connection()
    issues, stats = run_validation(conn)
    conn.close()

    # Print summary
    print(f"\nDatabase: {stats['total_games']:,} games, {stats['total_teams']:,} teams")
    print(f"Games added last week: {stats['games_added_last_week']:,}")
    print(f"Issues found: {len(issues)}")

    if not args.no_email:
        # Format and send email
        now = datetime.now().strftime("%Y-%m-%d")
        issue_count = len(issues)

        if issue_count == 0:
            subject = f"Seedline Data Quality Report ({now}) - All Clear"
        else:
            subject = f"Seedline Data Quality Report ({now}) - {issue_count} Issues Found"

        html_body, text_body = format_email_body(issues, stats)
        send_email(subject, html_body, text_body)
    else:
        print("\nSkipping email (--no-email flag set)")
        html_body, text_body = format_email_body(issues, stats)
        print(text_body)


if __name__ == "__main__":
    main()
