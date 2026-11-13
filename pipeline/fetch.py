"""Download every CBN feed the dashboard uses and save it, unedited, to data/raw/.

The CBN feeds are undocumented JSON endpoints, so they can change without notice.
Every value comes back as text, newest record first. This script saves the JSON
exactly as received; all cleaning happens in clean.py.

Each pull overwrites the previous file for that feed. data/raw/manifest.json records
when each feed was pulled, how many records it had, and a fingerprint (SHA-256) of
the file, so every month's run can be traced.

If a feed fails, the script stops with an error. It never falls back to made-up data.
US consumer prices come from FRED (series CPIAUCSL), saved as data/raw/us_cpi.csv.

Run from the project root:  python pipeline/fetch.py
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
MANIFEST = RAW_DIR / "manifest.json"

BASE_URL = "https://www.cbn.gov.ng/api/"
FEEDS = {
    "inflation": "GetAllInflationRates",
    "money_market": "GetAllMoneyMarketIndicators",
    "money_credit": "GetAllMoneyAndCreditStats",
    "exchange_rates": "GetAllExchangeRates",
    "crude": "GetAllDailyCrude",
}

# Some servers refuse requests that don't look like they come from a web browser.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
}


def fetch_feed(endpoint, attempts=3, wait_seconds=20):
    """Download one CBN feed and return the parsed JSON (a list of records).

    The CBN server sometimes answers with a passing server error (5xx) or times out, so a
    feed is tried up to 3 times. A refusal (4xx, e.g. 403 Forbidden) is not retried: that
    means we are blocked, and the run should stop and say so.
    """
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(BASE_URL + endpoint, headers=HEADERS, timeout=180)
            response.raise_for_status()
            records = response.json()
            if not isinstance(records, list) or not records:
                raise ValueError(f"{endpoint} returned no records")
            return records
        except requests.HTTPError as error:
            if error.response is not None and error.response.status_code < 500:
                raise
            if attempt == attempts:
                raise
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts:
                raise
        print(f"  {endpoint}: server error, trying again in {wait_seconds}s ({attempt}/{attempts})")
        time.sleep(wait_seconds)


def raw_path(name):
    return RAW_DIR / f"{name}.json"


# US consumer prices (FRED series CPIAUCSL), for the inflation gap behind the naira page's
# "policy reversal" scenario. FRED answers the plain requests client quickly; a custom
# User-Agent made it hang in testing, so none is sent.
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
FRED_RAW = RAW_DIR / "us_cpi.csv"


def fetch_us_cpi(attempts=3, wait_seconds=20):
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(FRED_URL, timeout=120)
            response.raise_for_status()
            text = response.text
            if not text.startswith("observation_date,CPIAUCSL"):
                raise ValueError("FRED CPIAUCSL file has an unexpected format")
            return text
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == attempts:
                raise
        print(f"  FRED: no answer, trying again in {wait_seconds}s ({attempt}/{attempts})")
        time.sleep(wait_seconds)


def load_us_cpi_text():
    if not FRED_RAW.exists():
        raise FileNotFoundError("No US CPI file. Run python pipeline/fetch.py first.")
    return FRED_RAW.read_text(encoding="utf-8")


def fetch_all():
    """Download every feed, save it to data/raw/<name>.json, and update the manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pulled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {}
    for name, endpoint in FEEDS.items():
        records = fetch_feed(endpoint)
        text = json.dumps(records, ensure_ascii=False)
        raw_path(name).write_text(text, encoding="utf-8")
        manifest[name] = {
            "url": BASE_URL + endpoint,
            "pulled_at_utc": pulled_at,
            "records": len(records),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        print(f"  {endpoint}: {len(records):,} records")
    text = fetch_us_cpi()
    FRED_RAW.write_text(text, encoding="utf-8", newline="\n")
    manifest["us_cpi"] = {
        "url": FRED_URL,
        "pulled_at_utc": pulled_at,
        "records": text.count("\n"),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    print(f"  FRED CPIAUCSL: {manifest['us_cpi']['records']:,} months")
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_raw(name):
    """The saved records for one feed (raises a clear error if it was never pulled)."""
    path = raw_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No raw data for '{name}'. Run python pipeline/fetch.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


if __name__ == "__main__":
    print("Fetching CBN feeds...")
    fetch_all()
