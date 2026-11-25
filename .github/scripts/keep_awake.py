"""Visit the app on Streamlit Community Cloud so it does not go to sleep, and wake it if it already has.

Community Cloud puts an app to sleep after 12 hours with no visitors. A plain HTTP request (curl, an uptime
monitor) does not count as a visit, so this opens the app in a real headless browser, clicks
"Yes, get this app back up!" if the sleep page is showing, and waits until the app has drawn its sidebar.

Run by .github/workflows/keep-awake.yml. Exits 1 if the app does not load, so the workflow run fails and
GitHub sends an email.
"""
from __future__ import annotations

import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "https://kouroshie-texas-uic-tracker-app-1zchb4.streamlit.app/")
WAKE_BUTTON = re.compile(r"get this app back up", re.I)
# Text from the app's own sidebar disclaimer. It appears only once the app has loaded its data and run.
APP_READY_TEXT = "Not affiliated with or endorsed"
WAIT_SECONDS = int(os.environ.get("WAIT_SECONDS", "480"))  # a cold start downloads about 100 MB of data
SCREENSHOT = "keep-awake.png"


def app_is_ready(page) -> bool:
    # The app runs inside an iframe on *.streamlit.app, so look in every frame, not just the top page.
    for frame in page.frames:
        try:
            if frame.get_by_text(APP_READY_TEXT).count():
                return True
        except Exception:
            pass  # a frame can detach while we look
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)

        woke = False
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline:
            if app_is_ready(page):
                print(f"App is up{' (it was asleep and has been woken)' if woke else ''}: {URL}")
                page.wait_for_timeout(15_000)  # stay connected a little longer so the visit registers
                browser.close()
                return 0
            button = page.get_by_role("button", name=WAKE_BUTTON)
            if not woke and button.count():
                print("App was asleep. Clicking the wake button.")
                button.first.click()
                woke = True
            page.wait_for_timeout(5_000)

        page.screenshot(path=SCREENSHOT, full_page=True)
        browser.close()
        print(f"App did not load within {WAIT_SECONDS} s. Screenshot saved to {SCREENSHOT}.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
