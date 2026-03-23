#!/usr/bin/env python3
"""
run_now.py — Master script: runs ALL Sonat Mundi analytics reports immediately.

Use this for first-time setup, testing, or on-demand full reporting.

Usage:
    python run_now.py                  # run all 4 reports
    python run_now.py --skip-upload    # skip upload report (no recent video needed)
    python run_now.py --only weekly    # run a single report
    python run_now.py <video_id>       # use specific video ID for upload report
"""

import os
import sys
import time
import traceback
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

THICK = "═" * 70
SEP   = "─" * 70


def section(title):
    print()
    print(THICK)
    print(f"  {title}")
    print(THICK)
    print()


def run_report(label, func, *args, **kwargs):
    section(label)
    t0 = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - t0
        print(f"\n  ✓ Completed in {elapsed:.1f}s")
        return True, result
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\n  ✗ FAILED after {elapsed:.1f}s")
        print(f"  Error: {e}")
        traceback.print_exc()
        return False, None


def main():
    args         = sys.argv[1:]
    skip_upload  = "--skip-upload" in args
    only_mode    = "--only" in args
    only_target  = args[args.index("--only") + 1].lower() if only_mode and "--only" in args else None
    video_id     = next((a for a in args if not a.startswith("--")), None)

    print(THICK)
    print("  SONAT MUNDI — FULL ANALYTICS SUITE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(THICK)
    print()
    print("  Reports to run:")
    print("    1. Weekly Report    (last 7 days)")
    print("    2. Biweekly Report  (last 15 days)")
    print("    3. Monthly Report   (current / previous month)")
    if not skip_upload:
        print(f"    4. Upload Report    (most recent video{f': {video_id}' if video_id else ''})")
    print()

    # Import all report functions
    from report_weekly    import run_weekly_report
    from report_biweekly  import run_biweekly_report
    from report_monthly   import run_monthly_report
    from report_upload    import run_upload_report

    reports = []
    if not only_mode or only_target == "weekly":
        reports.append(("WEEKLY REPORT — Last 7 Days",    run_weekly_report,   []))
    if not only_mode or only_target == "biweekly":
        reports.append(("BIWEEKLY REPORT — Last 15 Days", run_biweekly_report, []))
    if not only_mode or only_target == "monthly":
        reports.append(("MONTHLY REPORT — Full Month",    run_monthly_report,  []))
    if (not skip_upload) and (not only_mode or only_target == "upload"):
        reports.append(("UPLOAD REPORT — Most Recent Video",
                        run_upload_report, [video_id]))

    results = {}
    start_all = time.time()

    for label, func, func_args in reports:
        ok, path = run_report(label, func, *func_args)
        results[label] = {"ok": ok, "path": path}

    total_elapsed = time.time() - start_all

    # Summary
    print()
    print(THICK)
    print("  SUMMARY")
    print(SEP)
    ok_count = sum(1 for v in results.values() if v["ok"])
    for label, res in results.items():
        status = "✓" if res["ok"] else "✗ FAILED"
        path   = res["path"] or "—"
        short  = label.split("—")[0].strip()
        print(f"  {status}  {short:<20}  {path}")
    print(SEP)
    print(f"  {ok_count}/{len(results)} reports completed  │  Total: {total_elapsed:.1f}s")
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    print(f"  Reports folder: {reports_dir}")
    print(THICK)

    if ok_count < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
