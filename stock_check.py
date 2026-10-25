#!/usr/bin/env python3
"""Apple stock checker with Telegram alerts.

Env vars:
  PART_NUMBER   part number from the product page (e.g. MXXXXLL/A)
  LOCATION      ZIP / postal code
  TG_TOKEN      Telegram bot token (from @BotFather)
  TG_CHAT_ID    your chat id (from @userinfobot)
  APPLE_DOMAIN  optional, default www.apple.com (e.g. www.apple.com/ae for other countries)
  INTERVAL      optional, seconds between checks, default 600
  ONCE          set to 1 to check once and exit (for cron / GitHub Actions)
"""
import os
import sys
import time

import requests

PART = os.environ["PART_NUMBER"]
LOCATION = os.environ["LOCATION"]
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
DOMAIN = os.environ.get("APPLE_DOMAIN", "www.apple.com")
INTERVAL = int(os.environ.get("INTERVAL", "600"))
ONCE = os.environ.get("ONCE") == "1"

URL = f"https://{DOMAIN}/shop/fulfillment-messages"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT_ID, "text": text},
        timeout=15,
    ).raise_for_status()


def available_stores():
    params = {"pl": "true", "mts.0": "regular", "parts.0": PART, "location": LOCATION}
    r = requests.get(URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    stores = r.json()["body"]["content"]["pickupMessage"]["stores"]
    found = []
    for s in stores:
        info = s["partsAvailability"].get(PART, {})
        if info.get("pickupDisplay") == "available":
            found.append(s["storeName"])
    return found


def main():
    if ONCE:
        stores = available_stores()
        print("available" if stores else "unavailable", flush=True)
        if stores:
            send_telegram(f"IN STOCK: {PART}\nStores: {', '.join(stores)}")
        return
    was_available = False
    send_telegram(f"Stock monitor started for {PART} near {LOCATION}")
    while True:
        try:
            stores = available_stores()
            now_available = bool(stores)
            if now_available and not was_available:
                send_telegram(f"IN STOCK: {PART}\nStores: {', '.join(stores)}")
            was_available = now_available
            print(time.strftime("%H:%M:%S"), "available" if now_available else "unavailable", flush=True)
        except Exception as e:  # keep running on transient errors
            print("error:", e, file=sys.stderr, flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
