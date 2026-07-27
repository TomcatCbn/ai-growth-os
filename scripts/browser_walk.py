#!/usr/bin/env python3
"""Browser regression walk (Spec: cover the REAL player payload path).

Drives the actual player page through a full adventure and asserts the
server-side event log. Run:

    uv run uvicorn demo.web:app --port 8767 &
    uv run --with playwright python scripts/browser_walk.py
"""

from __future__ import annotations

import json
import sqlite3
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8767"
CHILD = "vc_curious"
DB = "demo/data/vc_curious.db"


def main() -> int:
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(f"{BASE}/player?child={CHILD}")
        page.wait_for_load_state("networkidle")
        page.click("#start-btn")
        page.wait_for_timeout(800)

        steps = 0
        while steps < 15:
            steps += 1
            if "明天再来找豆豆兔" in page.inner_text("#bubble"):
                break
            if page.locator("#choices .choice-btn").count() > 0:
                page.locator("#choices .choice-btn").first.click()
            elif page.locator("#voice-input").is_visible():
                page.fill("#voice-input", "红黄红黄，我摆的")
                page.press("#voice-input", "Enter")
            elif page.locator("#next-btn").is_visible():
                page.click("#next-btn")
            else:
                failures.append(f"stuck at: {page.inner_text('#bubble')[:40]}")
                break
            page.wait_for_timeout(400)

        if "明天再来找豆豆兔" not in page.inner_text("#bubble"):
            failures.append("adventure did not complete")
        if errors:
            failures.append(f"js errors: {errors}")
        browser.close()

    db = sqlite3.connect(DB)
    rows = db.execute(
        "SELECT event_type, payload FROM events WHERE child_id = ? "
        "AND event_type IN ('session.started','session.interaction',"
        "'partner.callback_offered','partner.callback_answered')",
        (CHILD,),
    ).fetchall()
    types = [r[0] for r in rows]
    for expected in ("session.started", "session.interaction",
                     "partner.callback_offered", "partner.callback_answered"):
        if expected not in types:
            failures.append(f"missing event: {expected}")
    answered = [json.loads(r[1]) for r in rows
                if r[0] == "partner.callback_answered"]
    if answered and answered[0].get("response") != "recognized":
        failures.append(f"expected first answer recognized, got {answered}")
    started = [json.loads(r[1]) for r in rows if r[0] == "session.started"]
    if started and started[-1].get("launch_source") != "child_mode":
        failures.append("player session not labelled child_mode")

    if failures:
        print("FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print(f"OK: full adventure walk, {len(rows)} relationship events recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
