#!/usr/bin/env python3
"""Put the styled mockup in front of the watermarked preview on each listing.

    python scripts/push_mockups.py                  # dry run
    python scripts/push_mockups.py --one monstera-deliciosa
    python scripts/push_mockups.py --all

This ADDS an image at rank 1 rather than deleting anything. The existing
watermarked preview stays on the listing as the second image, which is what
a buyer wants anyway: the mockup is the advert, the preview is the sample.

Etsy's rank semantics on insert are not documented clearly enough to trust,
so --one uploads to a single listing and prints the resulting image order
read back from the API. Do that first and look at it. Every significant bug
on this project returned 201 while doing something other than what was
intended, and all of them were found by reading the result back.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_client import Etsy  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MOCKUPS = ROOT / "designs" / "mockups"
STATE = ROOT / "data" / "listings.json"


def images_of(e, shop_id, listing_id):
    # NOT shop-scoped. Upload is POST /shops/{shop}/listings/{id}/images but
    # the read is GET /listings/{id}/images -- using the shop-scoped path
    # here returned a quiet failure that made the verification print None
    # and look like it had checked something.
    r = e.request("GET", f"/listings/{listing_id}/images")
    if r.status_code != 200:
        return f"GET failed {r.status_code}: {r.text[:120]}"
    return [(i.get("rank"), i.get("full_width"), i.get("full_height"))
            for i in r.json().get("results", [])]


def already_done(imgs):
    """The mockups are the only 2000x2000 images in the shop; the previews
    are 600x900. So a square first image means this listing is done, which
    makes a re-run safe to repeat.

    Note on verification: immediately after an upload the images endpoint
    can still report the pre-update ranks. Read it a beat later, and trust
    the dimensions over the rank field.
    """
    return isinstance(imgs, list) and imgs and imgs[0][1] == imgs[0][2] == 2000


def upload(e, shop_id, listing_id, path, rank=1):
    with open(path, "rb") as fh:
        return e.post(
            f"/shops/{shop_id}/listings/{listing_id}/images",
            files={"image": (path.name, fh, "image/jpeg")},
            data={"rank": rank},
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", metavar="SLUG")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    listings = json.loads(STATE.read_text(encoding="utf-8"))
    todo = [(s, r) for s, r in listings.items()
            if (MOCKUPS / f"{s}.jpg").exists()]

    if args.one:
        todo = [(s, r) for s, r in todo if s == args.one]
        if not todo:
            sys.exit(f"No listing or mockup for {args.one}")
    elif not args.all:
        print(f"DRY RUN. {len(todo)} listings have a mockup ready.")
        for s, r in todo[:5]:
            print(f"  {s:30} listing {r['listing_id']}")
        print(f"  ... and {max(0, len(todo) - 5)} more")
        print("\n--one <slug> uploads to a single listing and reads it back.")
        print("--all does the rest.")
        return 0

    e = Etsy()
    shop_id = e.shop_id()
    if not shop_id:
        sys.exit("No shop id.")

    ok, skipped = 0, 0
    for slug, rec in todo:
        lid = rec["listing_id"]
        before = images_of(e, shop_id, lid)
        if already_done(before):
            skipped += 1
            continue
        r = upload(e, shop_id, lid, MOCKUPS / f"{slug}.jpg", rank=1)
        if r.status_code not in (200, 201):
            print(f"  FAILED {slug}: {r.status_code} {r.text[:200]}")
            print("  Stopping so the problem gets fixed rather than repeated.")
            break
        ok += 1
        after = images_of(e, shop_id, lid)
        print(f"  [{ok}] {slug}")
        if args.one:
            print(f"      before: {before}")
            print(f"      after : {after}")
            print("\nCheck that rank 1 is now the mockup and the preview "
                  "survived at rank 2, then rerun with --all.")
        time.sleep(0.4)

    print(f"\nuploaded {ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
