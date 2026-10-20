#!/usr/bin/env python3
"""Configure the storefront: shop text, sections, and listing assignment.

    python scripts/setup_shop.py           # dry run
    python scripts/setup_shop.py --apply   # write to Etsy (free, no fees)

Shop sections and shop text are free to set -- unlike listings, nothing here
costs money, so this is safe to re-run.

What this CANNOT do: the shop icon, banner, About page, and structured
policies are not writable through the v3 API. Those are generated as assets
and copy for manual upload; see assign_sections() output and shop_copy.md.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_client import Etsy  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
STATE = ROOT / "data" / "listings.json"

TITLE = "Printable plant care cards for every houseplant"

ANNOUNCEMENT = (
    "Printable care cards for the houseplants people actually own. Each one is "
    "a 4x6 PDF with light, water, soil and feeding, what to do when something "
    "looks wrong, and whether the plant is safe around cats and dogs.\n\n"
    "Every card is an instant download. Nothing ships.\n\n"
    "The watering guidance is a condition to check, not a schedule. A flat "
    "every-7-days rule is wrong for most homes, so the cards tell you what to "
    "look for instead."
)

# Shown to the buyer immediately after a digital purchase.
DIGITAL_SALE_MESSAGE = (
    "Thanks very much. Your files are ready to download from your Etsy "
    "purchases page.\n\n"
    "You get a print-ready PDF and a high-resolution PNG.\n\n"
    "PRINTING: choose 4x6, print at 100 percent scale, and turn off any "
    "fit-to-page option so the layout stays correct. Photo paper or cardstock "
    "both work, as does any drugstore photo kiosk.\n\n"
    "If a file will not open or print properly, message me and I will sort it "
    "out.\n\n"
    "A reminder that these cards are a starting point, not a diagnosis. If a "
    "plant is badly struggling, check the roots before changing anything else."
)


def section_for(sp: dict) -> str:
    """One section per listing -- Etsy allows only one, so pet-safe wins.

    Pet safety is the highest-intent filter a buyer applies: someone searching
    whether a plant will poison their cat is closer to buying than someone
    browsing by difficulty.
    """
    if sp.get("toxic_pets") == "non-toxic":
        return "Pet-Safe Plants"
    if sp.get("difficulty") == "easy":
        return "Easy Care Plants"
    return "Statement Plants"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write to Etsy")
    args = ap.parse_args()

    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}

    buckets = defaultdict(list)
    for sp in species:
        buckets[section_for(sp)].append(sp["slug"])

    print("SHOP TEXT")
    print(f"  title              : {TITLE} ({len(TITLE)} chars)")
    print(f"  announcement       : {len(ANNOUNCEMENT)} chars")
    print(f"  digital_sale_msg   : {len(DIGITAL_SALE_MESSAGE)} chars")
    print("\nSECTIONS")
    for name, slugs in buckets.items():
        print(f"  {name:20} {len(slugs):>2} listings")
    print()

    if not args.apply:
        print("Dry run. Re-run with --apply to write. Nothing here costs money.")
        return 0

    e = Etsy()
    shop_id = e.shop_id()

    # -- shop text ------------------------------------------------------
    # Probe each field separately: Etsy rejects the whole request if any one
    # field is not writable, and a combined call would hide which.
    # Shop update is PUT. Listings are PATCH. This is genuinely inconsistent
    # in Etsy's API, and PATCH here returns a bare 404 that looks like a wrong
    # path rather than a wrong verb. Verified both ways.
    for field, value in [
        ("title", TITLE),
        ("announcement", ANNOUNCEMENT),
        ("digital_sale_message", DIGITAL_SALE_MESSAGE),
        ("sale_message", DIGITAL_SALE_MESSAGE),
    ]:
        r = e.request("PUT", f"/shops/{shop_id}", data={field: value})
        ok = r.status_code == 200
        print(f"  {field:22} {r.status_code}"
              f"{'' if ok else '  ' + r.text[:160]}")

    # -- sections -------------------------------------------------------
    r = e.get(f"/shops/{shop_id}/sections")
    existing = {s["title"]: s["shop_section_id"]
                for s in (r.json().get("results") or [])} if r.status_code == 200 else {}

    ids = {}
    for name in buckets:
        if name in existing:
            ids[name] = existing[name]
            print(f"  section exists: {name} ({existing[name]})")
            continue
        r = e.post(f"/shops/{shop_id}/sections", data={"title": name})
        if r.status_code in (200, 201):
            ids[name] = r.json()["shop_section_id"]
            print(f"  section created: {name} ({ids[name]})")
        else:
            print(f"  section FAILED: {name} {r.status_code} {r.text[:160]}")

    # -- assign listings ------------------------------------------------
    assigned = 0
    for sp in species:
        slug = sp["slug"]
        rec = state.get(slug)
        if not rec:
            continue
        sec = ids.get(section_for(sp))
        if not sec:
            continue
        r = e.request("PATCH", f"/shops/{shop_id}/listings/{rec['listing_id']}",
                      data={"shop_section_id": sec})
        if r.status_code == 200:
            assigned += 1
        else:
            print(f"  assign FAILED {slug}: {r.status_code} {r.text[:140]}")
    print(f"\n  listings assigned to sections: {assigned}/{len(state)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
