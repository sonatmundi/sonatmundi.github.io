#!/usr/bin/env python3
"""
report_monthly.py — Sonat Mundi monthly analytics report.

Covers: previous calendar month (if run on the 1st) or current month to date.
Scheduled: 1st of each month at 09:00

Fetches:
  - Full month views, watch time, likes, comments, shares
  - Revenue estimate (requires yt-analytics-monetary scope)
  - Subscriber growth
  - Best performing series
  - Per-video full ranking
  - Traffic sources
  - Content recommendations for next month

Output: D:\\Yedekler\\UCS\\analytics\\reports\\monthly_<date>.txt
"""

import os
import sys
import calendar
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

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def get_report_period():
    """Determine date range: previous full month if run on the 1st, else current month."""
    today = date.today()
    if today.day == 1:
        if today.month == 1:
            y, m = today.year - 1, 12
        else:
            y, m = today.year, today.month - 1
        last_day   = calendar.monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date   = date(y, m, last_day)
        label      = f"{MONTH_NAMES[m]} {y}"
    else:
        start_date = date(today.year, today.month, 1)
        end_date   = today - timedelta(days=1)
        label      = f"{MONTH_NAMES[today.month]} {today.year} (partial)"
    return start_date, end_date, label


def generate_recommendations(series_sorted, traffic_rows, video_rows, title_map):
    """Generate data-driven content recommendations for next month."""
    recs = []

    if series_sorted:
        best   = series_sorted[0]
        recs.append(
            f"→ Double down on '{best[0]}' — highest engagement this month "
            f"({best[1]['views']:,} views, {best[1]['count']} videos)."
        )
        if len(series_sorted) > 1:
            worst = series_sorted[-1]
            if worst[1]["views"] < best[1]["views"] * 0.2 and worst[1]["count"] > 0:
                recs.append(
                    f"→ Revamp '{worst[0]}' series — significantly underperforming "
                    f"({worst[1]['views']:,} views). Consider new sub-themes or thumbnails."
                )

        # Series with no uploads this month
        all_series = {
            "Sounds of World", "Sounds of Emotions",
            "Sounds of Concepts", "Sounds of Frequencies"
        }
        active_series = {s for s, _ in series_sorted if s != "Other"}
        missing = all_series - active_series
        for ms in missing:
            recs.append(f"→ No '{ms}' content this month — plan at least 1 upload next month.")

    if traffic_rows:
        top_traffic = traffic_rows[0].get("insightTrafficSourceType", "")
        if "BROWSE" in top_traffic:
            recs.append("→ Browse is your top traffic source — optimize thumbnails for click-through rate.")
        elif "SEARCH" in top_traffic:
            recs.append("→ YouTube Search is your top source — add more long-tail keywords in descriptions.")
        elif "SUGGESTED" in top_traffic:
            recs.append("→ Suggested Videos is your top source — use end screens and cards to chain videos.")

    recs.append("→ Maintain 2–3 uploads per week for consistent algorithm visibility.")
    recs.append("→ Ensure all videos have chapters (timestamps) for better retention metrics.")
    recs.append("→ Respond to all comments within 48 hours to boost engagement signals.")

    return recs


def run_monthly_report():
    youtube, analytics = get_services()
    ensure_reports_dir()

    today                        = date.today()
    start_date, end_date, label  = get_report_period()
    start_str                    = start_date.isoformat()
    end_str                      = end_date.isoformat()

    print(f"[Monthly] Fetching analytics: {start_str} → {end_str}  ({label})")

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

    # 2. Revenue estimate (requires yt-analytics-monetary scope)
    revenue = None
    try:
        rev_resp = analytics.reports().query(
            ids=f"channel=={CHANNEL_ID}",
            startDate=start_str,
            endDate=end_str,
            metrics="estimatedRevenue,estimatedAdRevenue,cpm,playbackBasedCpm"
        ).execute()
        rev_rows = parse_analytics(rev_resp)
        if rev_rows:
            revenue = {
                "total":  safe_float(rev_rows[0].get("estimatedRevenue")),
                "ads":    safe_float(rev_rows[0].get("estimatedAdRevenue")),
                "cpm":    safe_float(rev_rows[0].get("cpm")),
                "pb_cpm": safe_float(rev_rows[0].get("playbackBasedCpm")),
            }
    except Exception as e:
        print(f"[Monthly] Revenue query skipped: {e}")

    # 3. Per-video breakdown
    video_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares",
        dimensions="video",
        sort="-views",
        maxResults=50
    ).execute()
    video_rows = parse_analytics(video_resp)

    # 4. Video titles + tags
    video_ids           = [r["video"] for r in video_rows if r.get("video")]
    title_map, tags_map = get_video_titles_and_tags(youtube, video_ids)

    # 5. Traffic sources
    traffic_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics="views",
        dimensions="insightTrafficSourceType",
        sort="-views"
    ).execute()
    traffic_rows = parse_analytics(traffic_resp)

    # 6. Demographics
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
    except Exception:
        demo_rows = []

    # ─── Aggregate channel totals ─────────────────────────────────────────────
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
                                         "comments": 0, "shares": 0, "count": 0,
                                         "avg_dur": []})
    for r in video_rows:
        vid   = r.get("video", "")
        title = title_map.get(vid, vid)
        s     = detect_series(title)
        series_stats[s]["views"]    += safe_int(r.get("views"))
        series_stats[s]["minutes"]  += safe_float(r.get("estimatedMinutesWatched"))
        series_stats[s]["likes"]    += safe_int(r.get("likes"))
        series_stats[s]["comments"] += safe_int(r.get("comments"))
        series_stats[s]["shares"]   += safe_int(r.get("shares"))
        series_stats[s]["count"]    += 1
        d = safe_float(r.get("averageViewDuration"))
        if d:
            series_stats[s]["avg_dur"].append(d)

    series_sorted = sorted(series_stats.items(), key=lambda x: x[1]["views"], reverse=True)

    # ─── Content recommendations ──────────────────────────────────────────────
    recommendations = generate_recommendations(series_sorted, traffic_rows, video_rows, title_map)

    # ─── Build report ─────────────────────────────────────────────────────────
    lines = []
    def w(s=""): lines.append(s)

    w(THICK)
    w("  SONAT MUNDI — MONTHLY ANALYTICS REPORT")
    w(THICK)
    w(f"  Period   : {label}  ({start_str} → {end_str})")
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
    w(f"  Net Subscriber Change  {ch_subs_g - ch_subs_l:>+12,}")
    w()

    # Revenue
    w("REVENUE ESTIMATE")
    w(SEP)
    if revenue:
        w(f"  Estimated Revenue      ${revenue['total']:>11.2f}  USD")
        w(f"  Ad Revenue             ${revenue['ads']:>11.2f}  USD")
        w(f"  CPM                    ${revenue['cpm']:>11.2f}  USD per 1K impressions")
        w(f"  Playback-based CPM     ${revenue['pb_cpm']:>11.2f}  USD")
    else:
        w("  Revenue data not available.")
        w("  Requires yt-analytics-monetary.readonly scope and channel monetization.")
    w()

    # Series performance
    w("SERIES PERFORMANCE")
    w(SEP)
    if series_sorted:
        total_sv = sum(s["views"] for _, s in series_sorted) or 1
        max_sv   = series_sorted[0][1]["views"] or 1
        w(f"  {'Series':<26}  {'Videos':>6}  {'Views':>8}  {'Share':>6}  {'Watch Time':>12}  {'Likes':>6}")
        w(f"  {'─'*26}  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*12}  {'─'*6}")
        for sname, stats in series_sorted:
            pct   = stats["views"] / total_sv * 100
            d_lst = stats["avg_dur"]
            s_dur = format_duration(sum(d_lst) / len(d_lst)) if d_lst else "—"
            w(f"  {sname:<26}  {stats['count']:>6}  {stats['views']:>8,}  {pct:>5.1f}%  "
              f"{format_minutes(stats['minutes']):>12}  {stats['likes']:>6,}")
        w()
        w("  Visual comparison (by views):")
        for sname, stats in series_sorted:
            bar = ascii_bar(stats["views"], max_sv, 35)
            w(f"  {sname:<26}  {bar}  {stats['views']:,}")
        w()
    else:
        w("  No series data available.")
        w()

    # Full video ranking
    w("ALL VIDEOS THIS MONTH — FULL RANKING")
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

    # Audience demographics
    w("AUDIENCE DEMOGRAPHICS")
    w(SEP)
    if demo_rows:
        gender_totals = defaultdict(float)
        age_totals    = defaultdict(float)
        for r in demo_rows:
            gender_totals[r.get("gender", "unknown")] += safe_float(r.get("viewerPercentage"))
            age_totals[r.get("ageGroup", "unknown")]  += safe_float(r.get("viewerPercentage"))
        w("  Gender")
        for g, pct in sorted(gender_totals.items(), key=lambda x: x[1], reverse=True):
            bar = ascii_bar(pct, 100, 30)
            w(f"  {g:<10}  {bar}  {pct:>5.1f}%")
        w()
        w("  Age Groups")
        max_ap = max(age_totals.values(), default=1)
        for ag, pct in sorted(age_totals.items(), key=lambda x: x[1], reverse=True):
            bar = ascii_bar(pct, max_ap, 30)
            w(f"  {ag:<12}  {bar}  {pct:>5.1f}%")
        w()
    else:
        w("  Demographics data not available.")
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

    # Watch time trend (monthly)
    w("MONTHLY WATCH TIME TREND")
    w(SEP)
    if totals:
        max_v = max((safe_int(r.get("views")) for r in totals), default=1)
        w(f"  {'Date':<12}  {'Views':>8}  {'Watch (min)':>11}  Chart")
        w(f"  {'─'*12}  {'─'*8}  {'─'*11}  {'─'*22}")
        for r in totals:
            d   = r.get("day", "")
            v   = safe_int(r.get("views"))
            m   = safe_float(r.get("estimatedMinutesWatched"))
            bar = ascii_bar(v, max_v, 20)
            w(f"  {d:<12}  {v:>8,}  {m:>11,.0f}  {bar}")
        w()
    else:
        w("  No daily data available.")
        w()

    # Content recommendations
    w("CONTENT RECOMMENDATIONS FOR NEXT MONTH")
    w(SEP)
    for rec in recommendations:
        w(f"  {rec}")
    w()

    w(THICK)
    w(f"  Report generated: {today}  │  Sonat Mundi — United Colours of Sound")
    w(THICK)

    report_text = "\n".join(lines)

    filename = f"monthly_{today}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    print(report_text)
    print(f"\n✓ Report saved: {filepath}")
    return filepath


if __name__ == "__main__":
    run_monthly_report()
