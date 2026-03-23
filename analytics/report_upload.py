#!/usr/bin/env python3
"""
report_upload.py — Sonat Mundi post-upload performance report.

Fetches video performance since publish date:
  - Views, likes, comments, shares, subscribers gained
  - Average view duration & view percentage
  - Daily breakdown
  - Traffic sources

Usage:
    python report_upload.py <video_id>
    python report_upload.py              # auto-detects most recent upload

Output: D:\\Yedekler\\UCS\\analytics\\reports\\upload_<title>_<date>.txt

NOTE: YouTube Analytics has a 48–72 h processing delay. Data for videos
      uploaded within the last 3 days may be incomplete or show zeros.
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from _auth import (
    get_services, CHANNEL_ID, REPORTS_DIR, ensure_reports_dir,
    parse_analytics, safe_int, safe_float,
    format_duration, format_minutes, ascii_bar,
    sanitize_filename, get_video_titles_and_tags,
)

SEP   = "─" * 68
THICK = "═" * 68


# ─── Data fetching ─────────────────────────────────────────────────────────────

def get_video_details(youtube, video_id):
    resp = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=video_id
    ).execute()
    if not resp.get("items"):
        return None
    item = resp["items"][0]
    snip = item["snippet"]
    stat = item["statistics"]
    return {
        "id":        video_id,
        "title":     snip["title"],
        "published": snip["publishedAt"][:10],
        "tags":      snip.get("tags", []),
        "views":     safe_int(stat.get("viewCount")),
        "likes":     safe_int(stat.get("likeCount")),
        "comments":  safe_int(stat.get("commentCount")),
    }


def get_most_recent_video(youtube, channel_id):
    resp = youtube.search().list(
        part="id",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=1
    ).execute()
    items = resp.get("items", [])
    return items[0]["id"]["videoId"] if items else None


# ─── Report builder ────────────────────────────────────────────────────────────

def run_upload_report(video_id=None):
    youtube, analytics = get_services()
    ensure_reports_dir()

    # Resolve video ID
    if not video_id:
        print("No video ID provided — detecting most recent upload...")
        video_id = get_most_recent_video(youtube, CHANNEL_ID)
        if not video_id:
            print("ERROR: No videos found on channel.")
            sys.exit(1)
        print(f"Most recent video: {video_id}")

    info = get_video_details(youtube, video_id)
    if not info:
        print(f"ERROR: Video '{video_id}' not found.")
        sys.exit(1)

    today      = date.today()
    pub_date   = info["published"]
    start_str  = pub_date
    end_str    = today.isoformat()
    days_live  = (today - date.fromisoformat(pub_date)).days

    print(f"Fetching analytics for: {info['title']}")
    print(f"Period: {start_str} → {end_str} ({days_live} days)")

    # Core daily metrics
    core_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics=(
            "views,estimatedMinutesWatched,averageViewDuration,"
            "averageViewPercentage,likes,comments,shares,subscribersGained"
        ),
        dimensions="day",
        filters=f"video=={video_id}",
        sort="day"
    ).execute()
    core_rows = parse_analytics(core_resp)

    # Traffic sources
    traffic_resp = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start_str,
        endDate=end_str,
        metrics="views",
        dimensions="insightTrafficSourceType",
        filters=f"video=={video_id}",
        sort="-views"
    ).execute()
    traffic_rows = parse_analytics(traffic_resp)

    # Aggregate totals
    total_views    = sum(safe_int(r.get("views"))                    for r in core_rows)
    total_minutes  = sum(safe_float(r.get("estimatedMinutesWatched")) for r in core_rows)
    total_likes    = sum(safe_int(r.get("likes"))                    for r in core_rows)
    total_comments = sum(safe_int(r.get("comments"))                 for r in core_rows)
    total_shares   = sum(safe_int(r.get("shares"))                   for r in core_rows)
    total_subs     = sum(safe_int(r.get("subscribersGained"))        for r in core_rows)

    dur_vals = [safe_float(r.get("averageViewDuration")) for r in core_rows
                if r.get("averageViewDuration")]
    avg_dur  = sum(dur_vals) / len(dur_vals) if dur_vals else 0

    pct_vals = [safe_float(r.get("averageViewPercentage")) for r in core_rows
                if r.get("averageViewPercentage")]
    avg_pct  = sum(pct_vals) / len(pct_vals) if pct_vals else 0

    # ─── Build report text ────────────────────────────────────────────────────
    lines = []
    def w(s=""): lines.append(s)

    w(THICK)
    w("  SONAT MUNDI — UPLOAD PERFORMANCE REPORT")
    w(THICK)
    w(f"  Video   : {info['title']}")
    w(f"  ID      : {video_id}")
    w(f"  Published: {pub_date}  │  Days Live: {days_live}")
    w(f"  Report   : {today}")
    w(THICK)
    w()

    if days_live < 3:
        w("  ⚠  NOTICE: YouTube Analytics has a 48–72 h processing delay.")
        w("     Data for the most recent days may be incomplete or show zeros.")
        w()

    w("PERFORMANCE SUMMARY")
    w(SEP)
    w(f"  Views                  {total_views:>12,}")
    w(f"  Watch Time             {total_minutes:>12,.0f} min  ({format_minutes(total_minutes)})")
    w(f"  Avg View Duration      {format_duration(avg_dur):>12}")
    w(f"  Avg View Percentage    {avg_pct:>11.1f}%")
    w(f"  Likes                  {total_likes:>12,}")
    w(f"  Comments               {total_comments:>12,}")
    w(f"  Shares                 {total_shares:>12,}")
    w(f"  Subscribers Gained     {total_subs:>12,}")
    w()

    # Daily breakdown
    w("DAILY BREAKDOWN")
    w(SEP)
    if core_rows:
        w(f"  {'Date':<12}  {'Views':>8}  {'Watch (min)':>11}  {'Avg Dur':>8}  {'Avg %':>6}  {'Likes':>5}")
        w(f"  {'─'*12}  {'─'*8}  {'─'*11}  {'─'*8}  {'─'*6}  {'─'*5}")
        for r in core_rows:
            d   = r.get("day", "")
            v   = safe_int(r.get("views"))
            m   = safe_float(r.get("estimatedMinutesWatched"))
            dur = format_duration(safe_float(r.get("averageViewDuration")))
            pct = safe_float(r.get("averageViewPercentage"))
            lk  = safe_int(r.get("likes"))
            w(f"  {d:<12}  {v:>8,}  {m:>11,.0f}  {dur:>8}  {pct:>5.1f}%  {lk:>5,}")
    else:
        w("  No daily data available yet (analytics processing delay).")
    w()

    # Traffic sources
    w("TRAFFIC SOURCES")
    w(SEP)
    if traffic_rows:
        max_t = max((safe_int(r.get("views")) for r in traffic_rows), default=1)
        total_t = sum(safe_int(r.get("views")) for r in traffic_rows) or 1
        for r in traffic_rows:
            src   = r.get("insightTrafficSourceType", "UNKNOWN")
            v     = safe_int(r.get("views"))
            pct   = v / total_t * 100
            bar   = ascii_bar(v, max_t, 25)
            w(f"  {src:<35}  {bar}  {v:>7,}  ({pct:>5.1f}%)")
    else:
        w("  No traffic source data available yet.")
    w()

    # Video tags
    w("VIDEO TAGS")
    w(SEP)
    tags = info["tags"]
    if tags:
        for i in range(0, len(tags), 4):
            chunk = tags[i:i+4]
            w("  " + "  │  ".join(f"{t}" for t in chunk))
    else:
        w("  No tags found.")
    w()

    w(THICK)
    w(f"  Report generated: {today}  │  Sonat Mundi — United Colours of Sound")
    w(THICK)

    report_text = "\n".join(lines)

    # Save
    safe_title = sanitize_filename(info["title"])
    filename   = f"upload_{safe_title}_{today}.txt"
    filepath   = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    print(report_text)
    print(f"\n✓ Report saved: {filepath}")
    return filepath


if __name__ == "__main__":
    vid = sys.argv[1] if len(sys.argv) > 1 else None
    run_upload_report(vid)
