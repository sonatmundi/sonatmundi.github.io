#!/usr/bin/env python3
"""
Upload Optimizer — Determines the best upload times and day-of-week.

Analyzes YouTube Analytics data to find when the audience is most active,
then updates config.json with optimal upload windows.

Usage:
    python -m growth.upload_optimizer           # analyze and show results
    python -m growth.upload_optimizer --update  # update config.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from growth import config, auth

CHANNEL_ID = config.channel_id()
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def fetch_hourly_data(analytics, days_back=90):
    """Fetch view data broken down by day to find patterns."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Get daily views and watch time
    resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start,
        endDate=end,
        metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained",
        dimensions="day",
        sort="-day",
    ).execute()

    rows = resp.get("rows", [])
    return [
        {
            "date": row[0],
            "views": row[1],
            "watch_minutes": row[2],
            "avg_duration": row[3],
            "subs_gained": row[4],
        }
        for row in rows
    ]


def analyze_patterns(daily_data):
    """Find best days of week and estimate optimal hours."""
    from collections import defaultdict

    day_stats = defaultdict(lambda: {"views": 0, "watch_min": 0, "subs": 0, "count": 0})

    for row in daily_data:
        dt = datetime.strptime(row["date"], "%Y-%m-%d")
        day_name = dt.strftime("%A")
        day_stats[day_name]["views"] += row["views"]
        day_stats[day_name]["watch_min"] += row["watch_minutes"]
        day_stats[day_name]["subs"] += row["subs_gained"]
        day_stats[day_name]["count"] += 1

    # Average per day of week
    results = {}
    for day, stats in day_stats.items():
        n = stats["count"] or 1
        results[day] = {
            "avg_views": round(stats["views"] / n, 1),
            "avg_watch_min": round(stats["watch_min"] / n, 1),
            "avg_subs": round(stats["subs"] / n, 2),
            "sample_days": n,
        }

    return dict(sorted(results.items(), key=lambda x: x[1]["avg_views"], reverse=True))


def recommend_schedule(day_patterns):
    """Generate upload schedule recommendation."""
    sorted_days = sorted(
        day_patterns.items(), key=lambda x: x[1]["avg_views"], reverse=True
    )

    best_days = [d[0] for d in sorted_days[:3]]

    # Meditation/ambient music typically performs best when uploaded
    # before peak listening hours (morning routines, evening wind-down)
    recommended_hours = ["07:00", "08:00", "09:00", "17:00", "18:00"]

    return {
        "best_days": best_days,
        "recommended_hours": recommended_hours,
        "primary_slot": f"{best_days[0]} at 09:00 UTC",
        "secondary_slot": f"{best_days[1]} at 17:00 UTC",
        "reasoning": (
            f"Based on {sum(d['sample_days'] for d in day_patterns.values())} days of data. "
            f"{best_days[0]} has the highest average views "
            f"({day_patterns[best_days[0]]['avg_views']:.0f}/day). "
            "Morning uploads (07-09) catch meditation/yoga routines; "
            "evening uploads (17-18) catch wind-down listeners."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi Upload Optimizer")
    parser.add_argument("--update", action="store_true", help="Update config.json")
    parser.add_argument("--days", type=int, default=90, help="Days to analyze")
    args = parser.parse_args()

    _, analytics = auth.youtube_and_analytics()

    print(f"Analyzing {args.days} days of data...")
    daily = fetch_hourly_data(analytics, args.days)

    if not daily:
        print("No analytics data available yet. Need more viewing history.")
        return

    patterns = analyze_patterns(daily)
    schedule = recommend_schedule(patterns)

    # Print results
    print(f"\n{'='*50}")
    print("  UPLOAD OPTIMIZATION RESULTS")
    print(f"{'='*50}\n")

    print("  Day-of-Week Performance:")
    for day, stats in patterns.items():
        print(f"    {day:<12} {stats['avg_views']:>8.0f} views/day  "
              f"{stats['avg_watch_min']:>8.0f} min  "
              f"+{stats['avg_subs']:.1f} subs")

    print(f"\n  Recommendation:")
    print(f"    Primary:   {schedule['primary_slot']}")
    print(f"    Secondary: {schedule['secondary_slot']}")
    print(f"    Best days: {', '.join(schedule['best_days'])}")
    print(f"\n  {schedule['reasoning']}")

    # Save report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    report = {"patterns": patterns, "schedule": schedule}
    path = os.path.join(REPORTS_DIR, f"upload_optimizer_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Report: {path}")

    if args.update:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["best_upload_hours"] = schedule["recommended_hours"]
        cfg["best_upload_days"] = schedule["best_days"]
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("  config.json updated with optimal schedule.")


if __name__ == "__main__":
    main()
