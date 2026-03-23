#!/usr/bin/env python3
"""
report_weekly.py — Sonat Mundi weekly analytics report.

Covers: last 7 days (yesterday-6 → yesterday)
Scheduled: every Monday at 09:00 via Windows Task Scheduler

Fetches:
  - Channel totals & daily trend
  - Per-video performance & series grouping
  - Top 3 videos
  - Subscriber growth
  - Traffic sources

Output: D:\\Yedekler\\UCS\\analytics\\reports\\weekly_<date>.txt
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 output so box-drawing / arrow chars print correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from _auth import (
    get_services, CHANNEL_ID, REPORTS_DIR, ensure_reports_dir,
    parse_analytics, safe_int, safe_float,
    format_duration, format_minutes, ascii_bar,
    detect_series, get_video_titles_and_tags,
)

SEP   = "─" * 70
THICK = "═" * 70


def run_weekly_report():
    youtube, analytics = get_services()
    ensure_reports_dir()

    today      = date.today()
    end_date   = today - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    start_str  = start_date.isoformat()
    end_str    = end_date.isoformat()

    print(f"[Weekly] Fetching analytics: {start_str} → {end_str}")

    # 1. Channel totals by day
    totals_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics=(
            "views,estimatedMinutesWatched,averageViewDuration,"
            "likes,comments,shares,subscribersGained,subscribersLost"
        ),
        dimensions="day",
        sort="day"
    ).execute()
    totals = parse_analytics(totals_resp)

    # 2. Per-video breakdown
    video_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments",
        dimensions="video",
        sort="-views",
        maxResults=50
    ).execute()
    video_rows = parse_analytics(video_resp)

    # 3. Titles for video IDs
    video_ids         = [r["video"] for r in video_rows if r.get("video")]
    title_map, _      = get_video_titles_and_tags(youtube, video_ids)

    # 4. Traffic sources
    traffic_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics="views",
        dimensions="insightTrafficSourceType",
        sort="-views"
    ).execute()
    traffic_rows = parse_analytics(traffic_resp)

    # ─── Aggregate channel totals ─────────────────────────────────────────────
    ch_views    = sum(safe_int(r.get("views"))                    for r in totals)
    ch_minutes  = sum(safe_float(r.get("estimatedMinutesWatched")) for r in totals)
    ch_likes    = sum(safe_int(r.get("likes"))                    for r in totals)
    ch_comments = sum(safe_int(r.get("comments"))                 for r in totals)
    ch_shares   = sum(safe_int(r.get("shares"))                   for r in totals)
    ch_subs_g   = sum(safe_int(r.get("subscribersGained"))        for r in totals)
    ch_subs_l   = sum(safe_int(r.get("subscribersLost"))          for r in totals)
    ch_net_subs = ch_subs_g - ch_subs_l

    dur_vals = [safe_float(r.get("averageViewDuration")) for r in totals
                if r.get("averageViewDuration")]
    avg_dur  = sum(dur_vals) / len(dur_vals) if dur_vals else 0

    # ─── Series grouping ──────────────────────────────────────────────────────
    series_stats = {}
    for r in video_rows:
        title = title_map.get(r.get("video", ""), r.get("video", "Unknown"))
        s     = detect_series(title)
        if s not in series_stats:
            series_stats[s] = {"views": 0, "minutes": 0, "count": 0}
        series_stats[s]["views"]   += safe_int(r.get("views"))
        series_stats[s]["minutes"] += safe_float(r.get("estimatedMinutesWatched"))
        series_stats[s]["count"]   += 1

    series_sorted  = sorted(series_stats.items(), key=lambda x: x[1]["views"], reverse=True)
    top3_videos    = video_rows[:3]

    # ─── Build report ─────────────────────────────────────────────────────────
    lines = []
    def w(s=""): lines.append(s)

    w(THICK)
    w("  SONAT MUNDI — WEEKLY ANALYTICS REPORT")
    w(THICK)
    w(f"  Period   : {start_str} → {end_str}  (7 days)")
    w(f"  Generated: {today}")
    w(THICK)
    w()

    # Channel overview
    w("CHANNEL OVERVIEW")
    w(SEP)
    w(f"  Total Views            {ch_views:>12,}")
    w(f"  Total Watch Time       {ch_minutes:>12,.0f} min  ({format_minutes(ch_minutes)})")
    w(f"  Avg View Duration      {format_duration(avg_dur):>12}")
    w(f"  Likes                  {ch_likes:>12,}")
    w(f"  Comments               {ch_comments:>12,}")
    w(f"  Shares                 {ch_shares:>12,}")
    w(f"  New Subscribers        {ch_subs_g:>+12,}")
    w(f"  Lost Subscribers       {ch_subs_l:>+12,}")
    w(f"  Net Subscriber Change  {ch_net_subs:>+12,}")
    w()

    # Top 3 videos
    w("TOP 3 VIDEOS THIS WEEK")
    w(SEP)
    if top3_videos:
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(top3_videos):
            vid   = r.get("video", "")
            title = title_map.get(vid, vid)
            views = safe_int(r.get("views"))
            mins  = safe_float(r.get("estimatedMinutesWatched"))
            dur   = format_duration(safe_float(r.get("averageViewDuration")))
            likes = safe_int(r.get("likes"))
            medal = medals[i] if i < 3 else f"  {i+1}."
            w(f"  {medal} {title[:62]}")
            w(f"       Views: {views:,}  │  Watch Time: {format_minutes(mins)}"
              f"  │  Avg Duration: {dur}  │  Likes: {likes:,}")
            w()
    else:
        w("  No video data available for this period.")
        w()

    # Series performance
    w("SERIES PERFORMANCE")
    w(SEP)
    if series_sorted:
        max_views = series_sorted[0][1]["views"] or 1
        for sname, stats in series_sorted:
            pct = stats["views"] / max_views * 100
            bar = ascii_bar(stats["views"], max_views, 28)
            w(f"  {sname:<26}  {bar}  {stats['views']:>8,} views")
            w(f"  {'':26}  {stats['count']:>2} videos  │  {format_minutes(stats['minutes'])} watch time")
            w()
    else:
        w("  No series data available.")
        w()

    # All videos table
    w("ALL VIDEOS THIS WEEK")
    w(SEP)
    if video_rows:
        w(f"  {'#':>3}  {'Title':<52}  {'Views':>7}  {'Watch':>8}  {'Avg Dur':>7}  {'Likes':>5}")
        w(f"  {'─'*3}  {'─'*52}  {'─'*7}  {'─'*8}  {'─'*7}  {'─'*5}")
        for i, r in enumerate(video_rows, 1):
            vid   = r.get("video", "")
            title = title_map.get(vid, vid)[:52]
            views = safe_int(r.get("views"))
            mins  = safe_float(r.get("estimatedMinutesWatched"))
            dur   = format_duration(safe_float(r.get("averageViewDuration")))
            likes = safe_int(r.get("likes"))
            w(f"  {i:>3}  {title:<52}  {views:>7,}  {mins:>8,.0f}  {dur:>7}  {likes:>5,}")
        w()
    else:
        w("  No video data available for this period.")
        w()

    # Traffic sources
    w("TRAFFIC SOURCES")
    w(SEP)
    if traffic_rows:
        total_t = sum(safe_int(r.get("views")) for r in traffic_rows) or 1
        max_t   = max(safe_int(r.get("views")) for r in traffic_rows) or 1
        for r in traffic_rows:
            src   = r.get("insightTrafficSourceType", "UNKNOWN")
            v     = safe_int(r.get("views"))
            pct   = v / total_t * 100
            bar   = ascii_bar(v, max_t, 25)
            w(f"  {src:<38}  {bar}  {v:>7,}  ({pct:>5.1f}%)")
        w()
    else:
        w("  No traffic source data available.")
        w()

    # Daily trend
    w("DAILY TREND")
    w(SEP)
    if totals:
        max_v = max((safe_int(r.get("views")) for r in totals), default=1)
        w(f"  {'Date':<12}  {'Views':>8}  {'Watch (min)':>11}  {'Net Subs':>9}  Chart")
        w(f"  {'─'*12}  {'─'*8}  {'─'*11}  {'─'*9}  {'─'*25}")
        for r in totals:
            d    = r.get("day", "")
            v    = safe_int(r.get("views"))
            m    = safe_float(r.get("estimatedMinutesWatched"))
            subs = safe_int(r.get("subscribersGained")) - safe_int(r.get("subscribersLost"))
            bar  = ascii_bar(v, max_v, 20)
            w(f"  {d:<12}  {v:>8,}  {m:>11,.0f}  {subs:>+9,}  {bar}")
        w()
    else:
        w("  No daily data available.")
        w()

    w(THICK)
    w(f"  Report generated: {today}  │  Sonat Mundi — United Colours of Sound")
    w(THICK)

    report_text = "\n".join(lines)

    filename = f"weekly_{today}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    print(report_text)
    print(f"\n✓ Report saved: {filepath}")
    return filepath


if __name__ == "__main__":
    run_weekly_report()
