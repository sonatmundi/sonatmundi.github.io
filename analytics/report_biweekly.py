#!/usr/bin/env python3
"""
report_biweekly.py — Sonat Mundi biweekly analytics report.

Covers: last 15 days (yesterday-14 → yesterday)
Scheduled: 1st and 15th of each month at 09:00

Fetches:
  - 15-day channel performance
  - Series comparison (detailed)
  - Audience demographics (age / gender)
  - Watch time trends (daily chart)
  - Top performing tags

Output: D:\\Yedekler\\UCS\\analytics\\reports\\biweekly_<date>.txt
"""

import os
import sys
from datetime import date, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def run_biweekly_report():
    youtube, analytics = get_services()
    ensure_reports_dir()

    today      = date.today()
    end_date   = today - timedelta(days=1)
    start_date = end_date - timedelta(days=14)
    start_str  = start_date.isoformat()
    end_str    = end_date.isoformat()

    print(f"[Biweekly] Fetching analytics: {start_str} → {end_str}")

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

    # 3. Video titles + tags
    video_ids          = [r["video"] for r in video_rows if r.get("video")]
    title_map, tags_map = get_video_titles_and_tags(youtube, video_ids)

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

    # 5. Demographics — viewerPercentage by age + gender
    try:
        demo_resp = analytics.reports().query(
            ids=f"channel=={CHANNEL_ID}",
            startDate=start_str,
            endDate=end_str,
            metrics="viewerPercentage",
            dimensions="ageGroup,gender",
            sort="-viewerPercentage"
        ).execute()
        demo_rows = parse_analytics(demo_resp)
    except Exception as e:
        print(f"[Biweekly] Demographics query failed: {e}")
        demo_rows = []

    # ─── Aggregate totals ─────────────────────────────────────────────────────
    ch_views    = sum(safe_int(r.get("views"))                    for r in totals)
    ch_minutes  = sum(safe_float(r.get("estimatedMinutesWatched")) for r in totals)
    ch_likes    = sum(safe_int(r.get("likes"))                    for r in totals)
    ch_comments = sum(safe_int(r.get("comments"))                 for r in totals)
    ch_shares   = sum(safe_int(r.get("shares"))                   for r in totals)
    ch_subs_g   = sum(safe_int(r.get("subscribersGained"))        for r in totals)
    ch_subs_l   = sum(safe_int(r.get("subscribersLost"))          for r in totals)

    dur_vals = [safe_float(r.get("averageViewDuration")) for r in totals
                if r.get("averageViewDuration")]
    avg_dur  = sum(dur_vals) / len(dur_vals) if dur_vals else 0

    # ─── Series analysis ──────────────────────────────────────────────────────
    series_stats = defaultdict(lambda: {"views": 0, "minutes": 0, "likes": 0,
                                         "comments": 0, "count": 0, "avg_dur": []})
    for r in video_rows:
        vid   = r.get("video", "")
        title = title_map.get(vid, vid)
        s     = detect_series(title)
        series_stats[s]["views"]    += safe_int(r.get("views"))
        series_stats[s]["minutes"]  += safe_float(r.get("estimatedMinutesWatched"))
        series_stats[s]["likes"]    += safe_int(r.get("likes"))
        series_stats[s]["comments"] += safe_int(r.get("comments"))
        series_stats[s]["count"]    += 1
        d = safe_float(r.get("averageViewDuration"))
        if d:
            series_stats[s]["avg_dur"].append(d)

    series_sorted = sorted(series_stats.items(), key=lambda x: x[1]["views"], reverse=True)

    # ─── Top performing tags ──────────────────────────────────────────────────
    tag_views   = defaultdict(int)
    tag_count   = defaultdict(int)
    for r in video_rows:
        vid   = r.get("video", "")
        views = safe_int(r.get("views"))
        for tag in tags_map.get(vid, []):
            tag_views[tag] += views
            tag_count[tag] += 1
    top_tags = sorted(tag_views.items(), key=lambda x: x[1], reverse=True)[:20]

    # ─── Build report ─────────────────────────────────────────────────────────
    lines = []
    def w(s=""): lines.append(s)

    w(THICK)
    w("  SONAT MUNDI — BIWEEKLY ANALYTICS REPORT")
    w(THICK)
    w(f"  Period   : {start_str} → {end_str}  (15 days)")
    w(f"  Generated: {today}")
    w(THICK)
    w()

    # Channel overview
    w("CHANNEL OVERVIEW — 15 DAYS")
    w(SEP)
    w(f"  Total Views            {ch_views:>12,}")
    w(f"  Total Watch Time       {ch_minutes:>12,.0f} min  ({format_minutes(ch_minutes)})")
    w(f"  Avg View Duration      {format_duration(avg_dur):>12}")
    w(f"  Likes                  {ch_likes:>12,}")
    w(f"  Comments               {ch_comments:>12,}")
    w(f"  Shares                 {ch_shares:>12,}")
    w(f"  New Subscribers        {ch_subs_g:>+12,}")
    w(f"  Lost Subscribers       {ch_subs_l:>+12,}")
    w(f"  Net Subscriber Change  {ch_subs_g - ch_subs_l:>+12,}")
    w()

    # Series comparison
    w("SERIES COMPARISON")
    w(SEP)
    if series_sorted:
        total_sv = sum(s["views"] for _, s in series_sorted) or 1
        max_sv   = series_sorted[0][1]["views"] or 1
        w(f"  {'Series':<26}  {'Videos':>6}  {'Views':>8}  {'Share':>6}  {'Watch Time':>12}  {'Avg Dur':>8}")
        w(f"  {'─'*26}  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*12}  {'─'*8}")
        for sname, stats in series_sorted:
            pct    = stats["views"] / total_sv * 100
            d_list = stats["avg_dur"]
            s_dur  = format_duration(sum(d_list) / len(d_list)) if d_list else "—"
            w(f"  {sname:<26}  {stats['count']:>6}  {stats['views']:>8,}  {pct:>5.1f}%  "
              f"{format_minutes(stats['minutes']):>12}  {s_dur:>8}")
        w()
        w("  Visual comparison (by views):")
        for sname, stats in series_sorted:
            bar = ascii_bar(stats["views"], max_sv, 35)
            w(f"  {sname:<26}  {bar}  {stats['views']:,}")
        w()
    else:
        w("  No series data available.")
        w()

    # Audience demographics
    w("AUDIENCE DEMOGRAPHICS")
    w(SEP)
    if demo_rows:
        # Aggregate by gender
        gender_totals = defaultdict(float)
        age_totals    = defaultdict(float)
        for r in demo_rows:
            g   = r.get("gender", "unknown")
            ag  = r.get("ageGroup", "unknown")
            pct = safe_float(r.get("viewerPercentage"))
            gender_totals[g]  += pct
            age_totals[ag]    += pct

        w("  Gender Distribution")
        w(f"  {'─'*40}")
        total_g = sum(gender_totals.values()) or 1
        for g, pct in sorted(gender_totals.items(), key=lambda x: x[1], reverse=True):
            bar = ascii_bar(pct, 100, 30)
            w(f"  {g:<10}  {bar}  {pct:>6.1f}%")
        w()

        w("  Age Group Distribution")
        w(f"  {'─'*40}")
        max_ap = max(age_totals.values(), default=1)
        for ag, pct in sorted(age_totals.items(), key=lambda x: x[1], reverse=True):
            bar = ascii_bar(pct, max_ap, 30)
            w(f"  {ag:<12}  {bar}  {pct:>6.1f}%")
        w()

        w("  Age × Gender Breakdown")
        w(f"  {'─'*40}")
        w(f"  {'Age Group':<12}  {'Gender':<10}  {'%':>6}")
        w(f"  {'─'*12}  {'─'*10}  {'─'*6}")
        for r in sorted(demo_rows, key=lambda x: safe_float(x.get("viewerPercentage")), reverse=True):
            ag  = r.get("ageGroup", "?")
            g   = r.get("gender", "?")
            pct = safe_float(r.get("viewerPercentage"))
            if pct > 0.5:
                w(f"  {ag:<12}  {g:<10}  {pct:>5.1f}%")
        w()
    else:
        w("  Demographics data not available.")
        w("  (Requires sufficient view volume or yt-analytics scope)")
        w()

    # Watch time trends (daily chart)
    w("WATCH TIME TRENDS — DAILY")
    w(SEP)
    if totals:
        max_v = max((safe_int(r.get("views")) for r in totals), default=1)
        max_m = max((safe_float(r.get("estimatedMinutesWatched")) for r in totals), default=1)
        w(f"  {'Date':<12}  {'Views':>8}  {'Watch (min)':>11}  Views chart")
        w(f"  {'─'*12}  {'─'*8}  {'─'*11}  {'─'*25}")
        for r in totals:
            d   = r.get("day", "")
            v   = safe_int(r.get("views"))
            m   = safe_float(r.get("estimatedMinutesWatched"))
            bar = ascii_bar(v, max_v, 22)
            w(f"  {d:<12}  {v:>8,}  {m:>11,.0f}  {bar}")
        w()
    else:
        w("  No daily data available.")
        w()

    # Top performing tags
    w("TOP PERFORMING TAGS (by combined video views)")
    w(SEP)
    if top_tags:
        max_tv = top_tags[0][1] or 1
        w(f"  {'#':>3}  {'Tag':<40}  {'Videos':>6}  {'Views':>8}")
        w(f"  {'─'*3}  {'─'*40}  {'─'*6}  {'─'*8}")
        for i, (tag, tv) in enumerate(top_tags, 1):
            cnt = tag_count[tag]
            w(f"  {i:>3}  {tag:<40}  {cnt:>6}  {tv:>8,}")
        w()
    else:
        w("  No tag data available.")
        w()

    # Traffic sources
    w("TRAFFIC SOURCES")
    w(SEP)
    if traffic_rows:
        total_t = sum(safe_int(r.get("views")) for r in traffic_rows) or 1
        max_t   = max(safe_int(r.get("views")) for r in traffic_rows) or 1
        for r in traffic_rows:
            src = r.get("insightTrafficSourceType", "UNKNOWN")
            v   = safe_int(r.get("views"))
            pct = v / total_t * 100
            bar = ascii_bar(v, max_t, 25)
            w(f"  {src:<38}  {bar}  {v:>7,}  ({pct:>5.1f}%)")
        w()
    else:
        w("  No traffic source data available.")
        w()

    w(THICK)
    w(f"  Report generated: {today}  │  Sonat Mundi — United Colours of Sound")
    w(THICK)

    report_text = "\n".join(lines)

    filename = f"biweekly_{today}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    print(report_text)
    print(f"\n✓ Report saved: {filepath}")
    return filepath


if __name__ == "__main__":
    run_biweekly_report()
