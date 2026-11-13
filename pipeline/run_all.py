"""The monthly update: fetch -> clean -> build -> models -> validate -> save.

    python pipeline/run_all.py            pull fresh data from the CBN, then rebuild
    python pipeline/run_all.py --offline  rebuild from the raw files already in data/raw/

data/processed/ is only replaced if every validation check passes. If anything fails,
the old data stays as it was and the script exits with an error (a red run on GitHub).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import clean  # noqa: E402
import fetch  # noqa: E402
import validate  # noqa: E402

PROCESSED = HERE.parent / "data" / "processed"
META_PATH = PROCESSED / "meta.json"
PANEL_PATH = PROCESSED / "panel.csv"


def fail(message):
    print(f"\nFAILED: {message}\nThe data in data/processed/ was NOT changed.", file=sys.stderr)
    sys.exit(1)


def write_atomically(path, text):
    """Write to a temporary file first, then swap it in, so a crash never leaves half a file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def main(offline=False):
    print("1. Fetch")
    if offline:
        print("  --offline: using the raw files already in data/raw/")
    else:
        try:
            fetch.fetch_all()
        except Exception as error:  # network, blocked, broken JSON: all mean "keep the old data"
            fail(f"could not download the CBN feeds ({error}).")

    print("2. Clean and build")
    try:
        raw = {name: fetch.load_raw(name) for name in fetch.FEEDS}
        panel, log, latest = build.build_panel(raw)
        parsed = build.parse_all(raw)
    except Exception as error:
        fail(f"could not build the panel ({type(error).__name__}: {error}).")
    for line in log:
        print(f"  {line}")
    print(f"  Panel: {len(panel)} months, {panel['month'].min():%b %Y} to {latest:%b %Y}")

    print("3. Models")
    print("  (inflation forecast and naira outlook are added in Phase 2)")

    print("4. Validate")
    previous_meta = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
    errors, vlog = validate.validate(panel, parsed, latest, previous_meta)
    for line in vlog:
        print(f"  {line}")
    if errors:
        for e in errors:
            print(f"  ERROR {e}", file=sys.stderr)
        fail(f"{len(errors)} validation check(s) failed.")
    print("  All checks passed.")

    print("5. Save")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest = fetch.load_manifest()
    meta = {
        "latest_month": f"{latest:%Y-%m-%d}",
        "latest_month_label": f"{latest:%B %Y}",
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pulled_at_utc": {name: m["pulled_at_utc"] for name, m in manifest.items()},
        "rows": {"panel": len(panel)},
        "panel_start": f"{panel['month'].min():%Y-%m-%d}",
        "run_log": log + vlog,
        "trap_notes": clean.TRAP_NOTES,
    }
    old_panel = PANEL_PATH.read_text(encoding="utf-8") if PANEL_PATH.exists() else None
    new_panel = build.to_float_rounded(panel).to_csv(index=False, date_format="%Y-%m-%d", lineterminator="\n")
    write_atomically(PANEL_PATH, new_panel)
    # Keep meta.json unchanged when the data is unchanged, so a quiet month makes no commit.
    if old_panel != new_panel or not META_PATH.exists():
        write_atomically(META_PATH, json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        print(f"  Saved {PANEL_PATH.name} and {META_PATH.name}: data up to {meta['latest_month_label']}.")
    else:
        print("  No change in the data since the last run.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="rebuild from data/raw/ without downloading")
    main(parser.parse_args().offline)
