#!/usr/bin/env python3
"""Post the pin batch to Pinterest via the API.

    python scripts/post_pins.py                 # dry run
    python scripts/post_pins.py --check         # post ONE pin, to verify tier
    python scripts/post_pins.py --live          # post everything not yet posted
    python scripts/post_pins.py --live --limit 3

Reads pinterest_bulk.csv (image URL, title, description, link, board) and
records posted pin ids in data/pins_posted.json so re-running never duplicates.

Pacing: Pinterest throttles accounts that publish in bursts, and a new account
doing it looks like spam. DELAY_SECONDS spaces the calls out.

The Trial-tier trap: on Trial access, POST /pins returns 201 with a real id
and the pin is visible only to you. Nothing in the response says so. Run
--check first, open the returned URL in a private window, and only continue
if you can actually see it.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pinterest_client import Pinterest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "pinterest_bulk.csv"
STATE = ROOT / "data" / "pins_posted.json"

DELAY_SECONDS = 20


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="post a single pin so you can verify visibility")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true",
                    help="skip the one-pin visibility gate")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    state = load_state()
    todo = [r for r in rows if r["Media URL"] not in state]
    if args.limit:
        todo = todo[:args.limit]

    if not (args.live or args.check):
        print(f"DRY RUN. {len(rows)} pins in file, {len(todo)} not yet posted.\n")
        for r in todo[:5]:
            print(f"  {r['Pinterest board']:22} {r['Title'][:52]}")
            print(f"    img  {r['Media URL']}")
            print(f"    link {r['Link'][:76]}")
        if len(todo) > 5:
            print(f"  ... and {len(todo) - 5} more")
        print("\n--check posts one pin. --live posts the rest.")
        return 0

    p = Pinterest()
    boards = p.boards()
    if not boards:
        sys.exit("No boards found. Create them on pinterest.com first.")

    needed = {r["Pinterest board"] for r in todo}
    missing = needed - set(boards)
    if missing:
        print(f"Missing boards: {sorted(missing)}")
        print("Board names must match exactly. Create them, then rerun.")
        return 1

    # Gate: do not blast 43 pins before confirming they are actually public.
    if args.live and not args.force and not state:
        print("Nothing has been posted yet, so the access tier is unproven.")
        print("Run this first:\n    python scripts/post_pins.py --check")
        print("Then open the pin URL it prints in a PRIVATE browser window.")
        print("If you can see it there, rerun with --live.")
        print("If you cannot, the app is on Trial access and every pin would")
        print("be invisible. Pass --force only to override this deliberately.")
        return 1

    batch = todo[:1] if args.check else todo
    posted = 0
    for i, r in enumerate(batch):
        res = p.create_pin(
            board_id=boards[r["Pinterest board"]],
            image_url=r["Media URL"],
            title=r["Title"],
            description=r["Description"],
            link=r["Link"],
        )
        if res.status_code in (200, 201):
            pin = res.json()
            pid = pin.get("id")
            state[r["Media URL"]] = {"pin_id": pid, "title": r["Title"]}
            save_state(state)
            posted += 1
            print(f"  [{posted}] {r['Title'][:54]}")
            print(f"      https://www.pinterest.com/pin/{pid}/")
        else:
            print(f"  FAILED {res.status_code}: {res.text[:300]}")
            print("  Stopping so the problem gets fixed rather than repeated.")
            break
        if i < len(batch) - 1:
            time.sleep(DELAY_SECONDS)

    print(f"\nposted {posted}")
    if args.check and posted:
        print("\nNow open that pin URL in a PRIVATE/incognito window.")
        print("  Visible    -> Standard access. Run --live for the rest.")
        print("  Not found  -> Trial access. The pins would be invisible;")
        print("                apply for Standard before doing a full run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
