#!/usr/bin/env python3
"""
Dashboard Generator — Creates a beautiful HTML dashboard from live YouTube data.

Combines: Analytics, SEO Audit, Trending Analysis, Comment status
into a single HTML file and optionally emails it.

Usage:
    python -m growth.dashboard_generator                # generate only
    python -m growth.dashboard_generator --email        # generate + email
"""

import argparse
import json
import os
import sys
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from growth import config, auth

CHANNEL_ID = config.channel_id()
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def fetch_analytics(analytics, days=7):
    """Fetch channel analytics for the given period."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Overall stats
    overall = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start, endDate=end,
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,subscribersGained,subscribersLost",
    ).execute()

    # Daily breakdown
    daily = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start, endDate=end,
        metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost",
        dimensions="day", sort="day",
    ).execute()

    # Per-video stats
    per_video = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start, endDate=end,
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes",
        dimensions="video", sort="-views", maxResults=10,
    ).execute()

    # Traffic sources
    traffic = analytics.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate=start, endDate=end,
        metrics="views",
        dimensions="insightTrafficSourceType", sort="-views",
    ).execute()

    return {
        "period": {"start": start, "end": end},
        "overall": overall.get("rows", [[0]*8])[0],
        "daily": daily.get("rows", []),
        "per_video": per_video.get("rows", []),
        "traffic": traffic.get("rows", []),
    }


def fetch_video_titles(youtube, video_ids):
    """Get titles for video IDs."""
    if not video_ids:
        return {}
    resp = youtube.videos().list(part="snippet", id=",".join(video_ids)).execute()
    return {item["id"]: item["snippet"]["title"] for item in resp.get("items", [])}


def fetch_seo_audit(youtube):
    """Quick SEO audit via Claude AI."""
    ch = youtube.channels().list(part="contentDetails", id=CHANNEL_ID).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = youtube.playlistItems().list(part="contentDetails", playlistId=uploads_id, maxResults=50).execute()
    vids = [i["contentDetails"]["videoId"] for i in pl["items"]]

    details = youtube.videos().list(part="snippet,statistics", id=",".join(vids)).execute()

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    video_data = []
    for v in details.get("items", []):
        s, st = v["snippet"], v.get("statistics", {})
        video_data.append({
            "id": v["id"], "title": s["title"],
            "tags": s.get("tags", [])[:10],
            "views": st.get("viewCount", "0"),
        })

    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2048,
        messages=[{"role": "user", "content": f"""Rate each video's SEO 1-10 and give priority (high/medium/low).
Return JSON array: [{{"title":"...","score":N,"priority":"..."}}]
Videos: {json.dumps(video_data, ensure_ascii=False)}"""}],
    )
    text = msg.content[0].text
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return []


def fetch_trending_summary():
    """Quick trending summary via Claude AI."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1024,
        messages=[{"role": "user", "content": """What are the top 5 trending topics in meditation/healing/world music on YouTube right now (March 2026)?
Return JSON: {"topics": [{"title":"...","why":"..."}], "keywords": ["kw1","kw2",...]}"""}],
    )
    text = msg.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return {"topics": [], "keywords": []}


def fetch_comment_count(youtube):
    """Count unreplied comments."""
    ch = youtube.channels().list(part="contentDetails", id=CHANNEL_ID).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = youtube.playlistItems().list(part="contentDetails", playlistId=uploads_id, maxResults=20).execute()
    vids = [i["contentDetails"]["videoId"] for i in pl["items"]]

    unreplied = 0
    total = 0
    for vid in vids:
        try:
            threads = youtube.commentThreads().list(part="snippet", videoId=vid, maxResults=100).execute()
            for t in threads.get("items", []):
                total += 1
                if t["snippet"]["totalReplyCount"] == 0:
                    top = t["snippet"]["topLevelComment"]["snippet"]
                    if top["authorChannelId"]["value"] != CHANNEL_ID:
                        unreplied += 1
        except Exception:
            pass
    return total, unreplied


def generate_html(data, video_titles, seo_data, trending, comment_stats):
    """Generate the HTML dashboard."""
    o = data["overall"]
    views, watch_min, avg_dur, likes, comments, shares, subs_gained, subs_lost = o
    net_subs = subs_gained - subs_lost
    watch_h = int(watch_min) // 60
    watch_m = int(watch_min) % 60
    avg_m, avg_s = divmod(int(avg_dur), 60)
    period = data["period"]
    total_comments, unreplied = comment_stats

    # Daily data for chart
    daily_rows = data["daily"]
    max_views = max((r[1] for r in daily_rows), default=1)

    # Video rows
    video_rows = data["per_video"]

    # Traffic rows
    traffic_rows = data["traffic"]
    max_traffic = max((r[1] for r in traffic_rows), default=1)

    # Traffic source friendly names
    traffic_names = {
        "YT_CHANNEL": "Kanal Sayfasi",
        "SUBSCRIBER": "Aboneler",
        "EXT_URL": "Harici Link",
        "RELATED_VIDEO": "Ilgili Video",
        "NOTIFICATION": "Bildirim",
        "NO_LINK_OTHER": "Diger",
        "YT_SEARCH": "YT Arama",
        "PLAYLIST": "Playlist",
        "YT_OTHER_PAGE": "YT Diger Sayfa",
        "ADVERTISING": "Reklam",
    }

    # SEO score colors
    def score_class(s):
        if s >= 8: return "score-high"
        if s >= 6: return "score-mid"
        return "score-low"

    def badge_class(p):
        return {"high": "badge-high", "medium": "badge-medium", "low": "badge-low"}.get(p, "badge-medium")

    # Build daily bars
    daily_html = ""
    for row in daily_rows:
        day_label = row[0][5:]  # MM-DD
        v = int(row[1])
        pct = int(v / max_views * 100) if max_views > 0 else 0
        daily_html += f"""<div class="daily-bar">
          <div class="daily-value">{v}</div>
          <div class="daily-bar-fill" style="height: {max(pct, 5)}%"></div>
          <div class="daily-label">{day_label}</div>
        </div>\n"""

    # Build video table
    video_html = ""
    for i, row in enumerate(video_rows):
        vid_id = row[0]
        title = video_titles.get(vid_id, vid_id)[:55]
        v, wm, ad, lk = int(row[1]), int(row[2]), int(row[3]), int(row[4])
        am, asc = divmod(ad, 60)
        rank_cls = ["rank-1", "rank-2", "rank-3"][i] if i < 3 else ""
        video_html += f"""<tr>
          <td><span class="rank {rank_cls}">{i+1}</span></td>
          <td>{title}</td>
          <td style="font-family:'JetBrains Mono';font-weight:600">{v}</td>
          <td>{wm}d</td><td>{am}:{asc:02d}</td><td>{lk}</td></tr>\n"""

    # Traffic bars
    traffic_html = ""
    total_traffic = sum(r[1] for r in traffic_rows)
    for row in traffic_rows:
        name = traffic_names.get(row[0], row[0])
        v = int(row[1])
        pct = round(v / total_traffic * 100, 1) if total_traffic > 0 else 0
        bar_pct = int(v / max_traffic * 100) if max_traffic > 0 else 0
        color = "var(--gold)" if row[0] == "YT_SEARCH" else "var(--teal)"
        if row[0] == "YT_SEARCH" and pct < 5:
            color = "var(--red)"
        traffic_html += f"""<div class="bar-row">
          <div class="bar-label">{name}</div>
          <div class="bar-track"><div class="bar-fill" style="width:{max(bar_pct,3)}%;background:{color}">{pct}%</div></div>
          <div class="bar-value">{v}</div></div>\n"""

    # SEO table
    seo_html = ""
    for s in seo_data:
        sc = s.get("score", 5)
        pr = s.get("priority", "medium")
        seo_html += f"""<tr>
          <td>{s['title'][:50]}</td>
          <td><span class="score {score_class(sc)}">{sc}</span></td>
          <td><span class="badge {badge_class(pr)}">{pr.upper()}</span></td></tr>\n"""

    # Trending topics
    topics_html = ""
    for i, t in enumerate(trending.get("topics", [])[:5]):
        topics_html += f"""<div class="card opp-card">
          <div class="opp-number">{i+1}</div>
          <div class="opp-title">{t.get('title','')}</div>
          <div class="opp-why">{t.get('why','')}</div></div>\n"""

    # Keywords
    kw_html = "".join(f'<span class="keyword">{k}</span>' for k in trending.get("keywords", [])[:20])

    # YT Search warning
    yt_search_pct = 0
    for row in traffic_rows:
        if row[0] == "YT_SEARCH":
            yt_search_pct = round(int(row[1]) / total_traffic * 100, 1) if total_traffic > 0 else 0
    search_warning = ""
    if yt_search_pct < 10:
        search_warning = f'<div style="margin-top:16px;padding:12px;background:rgba(248,113,113,0.08);border-radius:8px;font-size:0.85rem;color:var(--red)">&#9888; YT Search %{yt_search_pct} — SEO iyilestirmesi kritik oncelik!</div>'

    now = datetime.now().strftime("%d %B %Y %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sonat Mundi Dashboard — {period['start']} / {period['end']}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root{{--bg:#0a0a0f;--card:#12121a;--border:#1e1e2e;--gold:#d4a853;--teal:#2dd4bf;--purple:#a78bfa;--red:#f87171;--green:#4ade80;--blue:#60a5fa;--pink:#f472b6;--text:#e2e8f0;--muted:#64748b}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}}
.container{{max-width:1400px;margin:0 auto;padding:24px}}
.header{{text-align:center;padding:48px 0 32px;border-bottom:1px solid var(--border);margin-bottom:32px}}
.header h1{{font-size:2.2rem;font-weight:700;background:linear-gradient(135deg,var(--gold),var(--teal));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}}
.header .subtitle{{color:var(--muted);font-size:.95rem;letter-spacing:2px;text-transform:uppercase}}
.header .date{{color:var(--gold);margin-top:12px;font-family:'JetBrains Mono',monospace;font-size:.85rem}}
.status-bar{{display:flex;gap:12px;justify-content:center;margin:24px 0;flex-wrap:wrap}}
.status-pill{{display:flex;align-items:center;gap:6px;padding:6px 16px;border-radius:20px;font-size:.8rem;font-weight:500;background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);color:var(--green)}}
.status-pill .dot{{width:8px;height:8px;border-radius:50%;background:var(--green)}}
.section{{margin-bottom:32px}}
.section-title{{font-size:1.1rem;font-weight:600;color:var(--gold);display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border)}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
.grid-2{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
@media(max-width:900px){{.grid-4,.grid-3{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:600px){{.grid-4,.grid-3,.grid-2{{grid-template-columns:1fr}}}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;transition:border-color .2s}}
.card:hover{{border-color:var(--gold)}}
.stat-card{{text-align:center}}
.stat-value{{font-size:2rem;font-weight:700;font-family:'JetBrains Mono',monospace}}
.stat-label{{font-size:.8rem;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
.stat-change{{font-size:.75rem;margin-top:4px}}
.up{{color:var(--green)}}.down{{color:var(--red)}}
.bar-row{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}
.bar-label{{width:160px;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bar-track{{flex:1;height:24px;background:var(--border);border-radius:4px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:4px;display:flex;align-items:center;padding-left:8px;font-size:.75rem;font-weight:600;color:#fff;min-width:32px}}
.bar-value{{font-size:.8rem;color:var(--muted);width:50px;text-align:right;font-family:'JetBrains Mono'}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;padding:10px 12px;font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border)}}
td{{padding:12px;border-bottom:1px solid var(--border);font-size:.85rem}}
tr:hover td{{background:rgba(212,168,83,.05)}}
.rank{{font-family:'JetBrains Mono';font-weight:700;font-size:1.1rem}}
.rank-1{{color:#fbbf24}}.rank-2{{color:#94a3b8}}.rank-3{{color:#b45309}}
.badge{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:.7rem;font-weight:600;text-transform:uppercase}}
.badge-high{{background:rgba(248,113,113,.15);color:var(--red)}}
.badge-medium{{background:rgba(251,191,36,.15);color:#fbbf24}}
.badge-low{{background:rgba(74,222,128,.15);color:var(--green)}}
.score{{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;font-weight:700;font-size:.85rem;font-family:'JetBrains Mono'}}
.score-high{{background:rgba(74,222,128,.15);color:var(--green);border:2px solid var(--green)}}
.score-mid{{background:rgba(251,191,36,.15);color:#fbbf24;border:2px solid #fbbf24}}
.score-low{{background:rgba(248,113,113,.15);color:var(--red);border:2px solid var(--red)}}
.opp-card{{position:relative;overflow:hidden}}
.opp-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--gold),var(--teal))}}
.opp-number{{font-size:3rem;font-weight:800;color:rgba(212,168,83,.1);position:absolute;right:12px;top:4px;font-family:'JetBrains Mono'}}
.opp-title{{font-weight:600;font-size:.95rem;margin-bottom:8px}}
.opp-why{{font-size:.8rem;color:var(--muted);line-height:1.5}}
.daily-chart{{display:flex;align-items:flex-end;gap:8px;height:120px;padding:16px 0}}
.daily-bar{{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px}}
.daily-bar-fill{{width:100%;border-radius:4px 4px 0 0;background:linear-gradient(180deg,var(--gold),rgba(212,168,83,.3))}}
.daily-label{{font-size:.7rem;color:var(--muted)}}.daily-value{{font-size:.7rem;color:var(--gold);font-weight:600;font-family:'JetBrains Mono'}}
.keyword-cloud{{display:flex;flex-wrap:wrap;gap:8px}}
.keyword{{padding:4px 12px;border-radius:16px;font-size:.8rem;font-weight:500;background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.3);color:var(--purple)}}
.footer{{text-align:center;padding:32px 0;margin-top:48px;border-top:1px solid var(--border);color:var(--muted);font-size:.8rem}}
.footer a{{color:var(--gold);text-decoration:none}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>SONAT MUNDI</h1>
    <div class="subtitle">Growth Automation Dashboard</div>
    <div class="date">{period['start']} — {period['end']} | Olusturulma: {now}</div>
    <div class="status-bar">
      <div class="status-pill"><span class="dot"></span> Analytics</div>
      <div class="status-pill"><span class="dot"></span> {unreplied} Yanitsiz Yorum</div>
      <div class="status-pill"><span class="dot"></span> SEO Audit</div>
      <div class="status-pill"><span class="dot"></span> Trend Analizi</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Haftalik Ozet</div>
    <div class="grid-4">
      <div class="card stat-card"><div class="stat-value" style="color:var(--gold)">{int(views)}</div><div class="stat-label">Goruntulenme</div></div>
      <div class="card stat-card"><div class="stat-value" style="color:var(--teal)">{watch_h}s {watch_m}d</div><div class="stat-label">Izlenme Suresi</div></div>
      <div class="card stat-card"><div class="stat-value" style="color:var(--purple)">{avg_m}:{avg_s:02d}</div><div class="stat-label">Ort. Izlenme</div></div>
      <div class="card stat-card"><div class="stat-value" style="color:var(--green)">+{int(net_subs)}</div><div class="stat-label">Net Abone</div><div class="stat-change up">+{int(subs_gained)} yeni / -{int(subs_lost)} kayip</div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Gunluk Trend</div>
    <div class="card"><div class="daily-chart">{daily_html}</div></div>
  </div>

  <div class="section">
    <div class="section-title">Video Performansi</div>
    <div class="card" style="overflow-x:auto">
      <table><thead><tr><th>#</th><th>Video</th><th>Izlenme</th><th>Sure</th><th>Ort.</th><th>Begeni</th></tr></thead>
      <tbody>{video_html}</tbody></table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Trafik Kaynaklari</div>
    <div class="card">{traffic_html}{search_warning}</div>
  </div>

  <div class="section">
    <div class="section-title">SEO Denetim</div>
    <div class="card" style="overflow-x:auto">
      <table><thead><tr><th>Video</th><th>Skor</th><th>Oncelik</th></tr></thead>
      <tbody>{seo_html}</tbody></table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Trend Firsatlari</div>
    <div class="grid-3">{topics_html}</div>
  </div>

  <div class="section">
    <div class="section-title">Hedef Anahtar Kelimeler</div>
    <div class="card"><div class="keyword-cloud">{kw_html}</div></div>
  </div>

  <div class="footer">
    <p><strong>Sonat Mundi</strong> — United Colours of Sound — Omnia Resonant</p>
    <p style="margin-top:8px">Otomatik rapor: GitHub Actions + Claude AI + YouTube Analytics</p>
    <p style="margin-top:4px"><a href="https://github.com/sonatmundi/sonatmundi.github.io/actions">Workflow'lari Gor</a></p>
  </div>
</div>
</body>
</html>"""
    return html


def send_email(html_content, html_file_path=None, subject=None):
    """Send the dashboard via Gmail SMTP — HTML body + .html file attachment."""
    from email.mime.base import MIMEBase
    from email import encoders

    gmail_user = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_email = "sjrkocaman@gmail.com"

    if not gmail_user or not gmail_pass:
        print("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set. Skipping email.")
        return False

    if not subject:
        subject = f"Sonat Mundi Dashboard — {datetime.now().strftime('%d %b %Y')}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"Sonat Mundi <{gmail_user}>"
    msg["To"] = to_email

    # HTML body (renders directly in email client)
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(html_part)

    # Attach the .html file for download
    if html_file_path and os.path.exists(html_file_path):
        filename = os.path.basename(html_file_path)
        attachment = MIMEBase("text", "html")
        with open(html_file_path, "r", encoding="utf-8") as f:
            attachment.set_payload(f.read().encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(attachment)
        print(f"Attached: {filename}")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_string())
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi Dashboard Generator")
    parser.add_argument("--email", action="store_true", help="Send dashboard via email")
    args = parser.parse_args()

    youtube, analytics = auth.youtube_and_analytics()

    print("Fetching analytics...")
    data = fetch_analytics(analytics)

    print("Fetching video titles...")
    video_ids = [row[0] for row in data["per_video"]]
    titles = fetch_video_titles(youtube, video_ids)

    print("Running SEO audit...")
    seo = fetch_seo_audit(youtube)

    print("Analyzing trends...")
    trending = fetch_trending_summary()

    print("Checking comments...")
    comment_stats = fetch_comment_count(youtube)

    print("Generating HTML dashboard...")
    html = generate_html(data, titles, seo, trending, comment_stats)

    # Save to file
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(REPORTS_DIR, f"dashboard_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard saved: {path}")

    if args.email:
        send_email(html, html_file_path=path)


if __name__ == "__main__":
    main()
