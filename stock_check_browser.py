#!/usr/bin/env python3
"""Same as stock_check.py, but fetches through a real browser (Playwright).

Apple rejects plain HTTP clients (HTTP 541), so this loads the product page
first and calls the endpoint from inside the page, with the page's cookies.

Setup:
  pip install requests playwright && playwright install chromium

Env vars: same as stock_check.py, plus optional
  PAGE_URL   product page to load (default: iPhone Duo 256GB Night Sky)
  HEADLESS   set to 0 to watch the browser window (debugging)
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

from stock_check import INTERVAL, ONCE, PART, build_url, parse_stores, send_telegram

PAGE_URL = os.environ.get(
    "PAGE_URL",
    "https://www.apple.com/shop/buy-iphone/iphone-duo/7.6-inch-display-256gb-night-sky-unlocked",
)
HEADLESS = os.environ.get("HEADLESS", "1") != "0"

FETCH_JS = """async (url) => {
  const r = await fetch(url, {credentials: 'include', headers: {Accept: 'application/json'}});
  return {status: r.status, text: await r.text()};
}"""


def check(page):
    res = page.evaluate(FETCH_JS, build_url())
    if res["status"] != 200:
        raise RuntimeError(f"Apple returned HTTP {res['status']}")
    return parse_stores(json.loads(res["text"]))


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS)
        page = browser.new_context().new_page()
        page.goto(PAGE_URL, wait_until="domcontentloaded")
        was_available = False
        if not ONCE:
            send_telegram(f"Browser stock monitor started for {PART}")
        while True:
            try:
                stores = check(page)
                now = bool(stores)
                if now and not was_available:
                    send_telegram(f"IN STOCK: {PART}\nStores: {', '.join(stores)}")
                was_available = now
                print(time.strftime("%H:%M:%S"), "available" if now else "unavailable", flush=True)
            except Exception as e:
                print("error:", e, file=sys.stderr, flush=True)
                if ONCE:
                    sys.exit(1)
                page.goto(PAGE_URL, wait_until="domcontentloaded")
            if ONCE:
                break
            time.sleep(INTERVAL)
        browser.close()


if __name__ == "__main__":
    main()
