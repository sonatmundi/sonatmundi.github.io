#!/usr/bin/env python3
"""
scheduler.py — Register all Sonat Mundi analytics tasks in Windows Task Scheduler.

Creates the following scheduled tasks:
  SonatMundi_Weekly    — every Monday at 09:00
  SonatMundi_Biweekly  — 1st and 15th of each month at 09:00
  SonatMundi_Monthly   — 1st of each month at 09:00

Run once as Administrator (or confirm UAC prompt) to register the tasks.
Re-running is safe — /f flag overwrites existing tasks.

Usage:
    python scheduler.py              # register / update all tasks
    python scheduler.py --list       # show current task status
    python scheduler.py --delete     # remove all Sonat Mundi tasks
"""

import os
import sys
import subprocess

ANALYTICS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON        = sys.executable          # full path to python.exe

TASK_DEFS = [
    {
        "name":     "SonatMundi_Weekly",
        "script":   os.path.join(ANALYTICS_DIR, "report_weekly.py"),
        "schedule": "WEEKLY",
        "day":      "MON",
        "time":     "09:00",
        "desc":     "Weekly report — every Monday at 09:00",
    },
    {
        "name":     "SonatMundi_Biweekly_1st",
        "script":   os.path.join(ANALYTICS_DIR, "report_biweekly.py"),
        "schedule": "MONTHLY",
        "day":      "1",
        "time":     "09:00",
        "desc":     "Biweekly report — 1st of each month at 09:00",
    },
    {
        "name":     "SonatMundi_Biweekly_15th",
        "script":   os.path.join(ANALYTICS_DIR, "report_biweekly.py"),
        "schedule": "MONTHLY",
        "day":      "15",
        "time":     "09:00",
        "desc":     "Biweekly report — 15th of each month at 09:00",
    },
    {
        "name":     "SonatMundi_Monthly",
        "script":   os.path.join(ANALYTICS_DIR, "report_monthly.py"),
        "schedule": "MONTHLY",
        "day":      "1",
        "time":     "09:00",
        "desc":     "Monthly report — 1st of each month at 09:00",
    },
]


def run(cmd_list):
    return subprocess.run(cmd_list, capture_output=True, text=True)


def register_tasks():
    print("=" * 60)
    print("  SONAT MUNDI — TASK SCHEDULER SETUP")
    print("=" * 60)
    print(f"  Python: {PYTHON}")
    print(f"  Scripts: {ANALYTICS_DIR}")
    print()

    success = 0
    for t in TASK_DEFS:
        tr = f'"{PYTHON}" "{t["script"]}"'

        if t["schedule"] == "WEEKLY":
            cmd = [
                "schtasks", "/create",
                "/tn", t["name"],
                "/tr", tr,
                "/sc", "WEEKLY", "/d", t["day"], "/st", t["time"],
                "/f",
            ]
        else:  # MONTHLY
            cmd = [
                "schtasks", "/create",
                "/tn", t["name"],
                "/tr", tr,
                "/sc", "MONTHLY", "/d", t["day"], "/st", t["time"],
                "/f",
            ]

        result = run(cmd)
        ok = result.returncode == 0
        status = "✓" if ok else "✗"
        print(f"  {status} {t['desc']}")
        if ok:
            success += 1
        else:
            print(f"    Task name : {t['name']}")
            print(f"    Error     : {result.stderr.strip() or result.stdout.strip()}")
            print(f"    Cmd       : {cmd}")
        print()

    print("─" * 60)
    print(f"  Registered: {success}/{len(TASK_DEFS)} tasks")

    if success < len(TASK_DEFS):
        print()
        print("  TIP: If tasks failed, try running this script as Administrator:")
        print("       Right-click scheduler.py → Run as administrator")
        print("       Or open an elevated cmd.exe and run: python scheduler.py")

    print()
    list_tasks()


def list_tasks():
    print("=" * 60)
    print("  CURRENT SONAT MUNDI SCHEDULED TASKS")
    print("=" * 60)
    for t in TASK_DEFS:
        result = run(["schtasks", "/query", "/tn", t["name"], "/fo", "LIST"])
        if result.returncode == 0:
            # Extract key lines
            for line in result.stdout.splitlines():
                line = line.strip()
                if any(key in line for key in
                       ("TaskName", "Next Run Time", "Last Run Time",
                        "Status", "Schedule Type")):
                    print(f"  {line}")
            print()
        else:
            print(f"  {t['name']}: NOT FOUND")
            print()


def delete_tasks():
    print("Deleting all Sonat Mundi scheduled tasks...")
    for t in TASK_DEFS:
        result = run(["schtasks", "/delete", "/tn", t["name"], "/f"])
        status = "✓ Deleted" if result.returncode == 0 else "✗ Not found"
        print(f"  {status}: {t['name']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--list" in args:
        list_tasks()
    elif "--delete" in args:
        delete_tasks()
    else:
        register_tasks()
