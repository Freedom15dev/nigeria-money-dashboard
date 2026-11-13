"""Forecast vintages: a frozen copy of each month's forecasts, so they can be checked later.

data/forecasts/<model>_<YYYY-MM>.csv, where YYYY-MM is the last month of data the forecast was made with.
Rules:
- A vintage is written once and never overwritten or edited. If the file exists, it is left alone.
- data/forecasts/manifest.json records every vintage's SHA-256 fingerprint. validate.py checks that every
  file still matches its fingerprint and that no unexpected file has appeared, before any run saves anything.
- Files are written with Unix line endings, and fingerprints ignore line-ending style, so a vintage has the
  same fingerprint on Windows and on GitHub's Linux machines.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

FORECASTS = Path(__file__).resolve().parents[1] / "data" / "forecasts"
MANIFEST = FORECASTS / "manifest.json"
MODELS = ("inflation", "naira")
CRLF, LF = bytes([13, 10]), bytes([10])


def vintage_path(model, vintage):
    return FORECASTS / f"{model}_{vintage}.csv"


def _sha(path):
    """Fingerprint of the file's content, with Windows line endings (CR LF) read as Unix ones (LF)."""
    return hashlib.sha256(path.read_bytes().replace(CRLF, LF)).hexdigest()


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_vintage(model, vintage, table, source, note=""):
    """Write a new vintage if, and only if, none exists for this model and month. Returns a log line."""
    path = vintage_path(model, vintage)
    manifest = load_manifest()
    if path.exists():
        kept = manifest.get(path.name, {}).get("source", "unknown")
        return f"Vintage {path.name} already saved ({kept}); left unchanged."
    FORECASTS.mkdir(parents=True, exist_ok=True)
    out = table.copy()
    out.insert(0, "source", source)
    out.insert(0, "vintage", vintage)
    out.insert(0, "model", model)
    text = out.to_csv(index=False, date_format="%Y-%m-%d", lineterminator="\n")
    path.write_text(text, encoding="utf-8", newline="\n")  # Unix line endings on every machine, as stored in git
    manifest[path.name] = {"source": source, "note": note, "sha256": _sha(path),
                           "saved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return f"Vintage {path.name} saved ({source})."


def check_unchanged():
    """Errors if any saved vintage changed, disappeared, or a vintage file appeared outside save_vintage."""
    errors = []
    manifest = load_manifest()
    for name, info in manifest.items():
        path = FORECASTS / name
        if not path.exists():
            errors.append(f"Forecast vintage {name} has been deleted.")
        elif _sha(path) != info["sha256"]:
            errors.append(f"Forecast vintage {name} has been changed since it was saved.")
    for path in FORECASTS.glob("*.csv"):
        if path.name not in manifest:
            errors.append(f"Forecast vintage {path.name} is not in the manifest (saved by hand?).")
    return errors


def load_vintages(model):
    files = sorted(FORECASTS.glob(f"{model}_*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f, parse_dates=["month"], dtype={"vintage": str}) for f in files],
                     ignore_index=True)
