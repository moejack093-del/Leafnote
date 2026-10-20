#!/usr/bin/env python3
"""Publish pin images to GitHub Pages and build Pinterest's bulk-upload CSV.

Pinterest's bulk tool fetches each image from a public URL at publish time --
it will not read files off your computer. The repo is public, so Pages hosts
them for free.

    python scripts/make_bulk_csv.py

Output:
    docs/pins/*.png          copied, these become the public URLs
    pinterest_bulk.csv       upload this to Pinterest

A broken or login-protected image URL makes the pin fail silently, with no
error, so verify_urls() checks every link resolves before you upload.
"""

import csv
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
PINS = ROOT / "designs" / "pins" / "pinterest"
COPY = ROOT / "designs" / "pins" / "pin_copy.csv"
DOCS = ROOT / "docs" / "pins"
OUT = ROOT / "pinterest_bulk.csv"

PAGES_BASE = "https://moejack093-del.github.io/Leafnote/pins"

# Pinterest throttles accounts that dump everything at once, and a brand-new
# account doing it looks like spam. 3/day is a normal-looking ramp.
PINS_PER_DAY = 3
START_OFFSET_DAYS = 1


def main() -> int:
    if not COPY.exists():
        sys.exit("No pin_copy.csv. Run: python scripts/make_pins.py")

    DOCS.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(COPY, encoding="utf-8")))

    start = (datetime.now() + timedelta(days=START_OFFSET_DAYS)).replace(
        hour=10, minute=0, second=0, microsecond=0)

    # Lead with the list pins. They are useful standalone, which is what gets
    # saved, and saves are what Pinterest actually rewards.
    rows.sort(key=lambda r: (0 if "list-" in r["file"] else 1, r["file"]))

    out_rows = []
    for i, r in enumerate(rows):
        name = Path(r["file"]).name
        src = PINS / name
        if not src.exists():
            print(f"  missing image, skipping: {name}")
            continue
        shutil.copy2(src, DOCS / name)

        when = start + timedelta(days=i // PINS_PER_DAY,
                                 hours=(i % PINS_PER_DAY) * 3)
        out_rows.append({
            "Title": r["title"][:100],
            "Media URL": f"{PAGES_BASE}/{name}",
            "Pinterest board": r["board"],
            "Thumbnail": "",
            "Description": r["description"][:500],
            "Link": r["link"],
            "Publish date": when.strftime("%Y-%m-%d %H:%M"),
            "Keywords": "houseplants, plant care, printable, pet safe plants",
        })

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        wr.writeheader()
        wr.writerows(out_rows)

    last = out_rows[-1]["Publish date"] if out_rows else "-"
    print(f"images staged : {len(out_rows)} -> {DOCS}")
    print(f"csv           : {OUT}")
    print(f"schedule      : {out_rows[0]['Publish date']} .. {last}")
    print(f"boards needed : {sorted({r['Pinterest board'] for r in out_rows})}")
    return 0


def verify_urls() -> int:
    """Check every Media URL actually resolves. Run AFTER pushing to Pages."""
    rows = list(csv.DictReader(open(OUT, encoding="utf-8")))
    bad = []
    for r in rows:
        try:
            resp = requests.head(r["Media URL"], timeout=15,
                                 allow_redirects=True)
            if resp.status_code != 200:
                bad.append((r["Media URL"], resp.status_code))
        except Exception as exc:
            bad.append((r["Media URL"], str(exc)[:60]))
    print(f"checked {len(rows)} urls, {len(bad)} broken")
    for u, s in bad[:15]:
        print(f"  {s}  {u}")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(verify_urls())
    sys.exit(main())
