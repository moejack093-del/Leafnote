#!/usr/bin/env python3
"""Build Etsy listings from species data and push them to the shop.

Safety model, because activation costs real money:

    python scripts/push_listings.py              # dry run, prints, spends nothing
    python scripts/push_listings.py --create     # creates DRAFTS (free)
    python scripts/push_listings.py --create --limit 1   # one draft, to eyeball
    python scripts/push_listings.py --activate   # publishes, $0.20 EACH

Created listing ids are recorded in data/listings.json so re-running never
duplicates a listing. Delete an entry there to force a rebuild.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_client import Etsy  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
STATE = ROOT / "data" / "listings.json"
CARDS = ROOT / "designs" / "cards"
PREVIEWS = ROOT / "designs" / "previews"

TAXONOMY_DIGITAL_PRINTS = 2078  # Art & Collectibles > Prints > Digital Prints

PRICE_SINGLE = 4.00
PRICE_BUNDLE = 12.00

MAX_TITLE = 140
MAX_TAGS = 13
MAX_TAG_LEN = 20


# --------------------------------------------------------------------------
# listing content
# --------------------------------------------------------------------------

_QUOTES = {"'": "", '"': "", "‘": "", "’": "",
           "“": "", "”": ""}


def clean(s: str) -> str:
    """Strip quote characters from anything bound for Etsy.

    Etsy HTML-escapes them on store (don't -> don&#39;t) and renders the raw
    entity back. The species data is full of them -- cultivar names like
    'Brasil', possessives like Bird's Nest Fern -- so sanitising only the
    template prose is not enough. Applied to every interpolated value.
    """
    for bad, good in _QUOTES.items():
        s = s.replace(bad, good)
    return s


def build_title(sp: dict) -> str:
    t = (f"{clean(sp['common'])} Care Card Printable | {clean(sp['botanical'])} "
         f"Plant Care Guide | Instant Download | Houseplant Gift | 4x6 PDF")
    if len(t) <= MAX_TITLE:
        return t
    # Drop the trailing segments rather than hard-truncating mid-word, which
    # looks broken and wastes the keywords Etsy indexes.
    parts = t.split(" | ")
    while len(parts) > 2 and len(" | ".join(parts)) > MAX_TITLE:
        parts.pop()
    t = " | ".join(parts)
    return t[:MAX_TITLE].rsplit(" ", 1)[0] if len(t) > MAX_TITLE else t


def build_tags(sp: dict) -> list:
    common = sp["common"].lower()
    # The species-specific tag is the most valuable one on the listing -- it is
    # the long-tail query people actually search. If "<name> care" busts the
    # 20-char cap, fall back to the bare name rather than losing the tag.
    specific = f"{common} care"
    if len(specific) > MAX_TAG_LEN:
        specific = common if len(common) <= MAX_TAG_LEN else ""
    candidates = [
        specific,
        "plant care card",
        "plant care guide",
        "printable plant care",
        "houseplant care",
        "instant download",
        "plant lover gift",
        "plant parent gift",
        "houseplant decor",
        "botanical print",
        "plant care sign",
        "digital download",
    ]
    if sp.get("toxic_pets") == "non-toxic":
        candidates.insert(2, "pet safe plants")
        candidates.insert(3, "cat safe plant")

    out, seen = [], set()
    for t in candidates:
        t = t.strip()
        # Etsy rejects the whole request if any single tag is over 20 chars,
        # so drop offenders rather than truncating into nonsense.
        if len(t) > MAX_TAG_LEN or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) == MAX_TAGS:
            break
    return out


def build_description(sp: dict) -> str:
    sp = {k: (clean(v) if isinstance(v, str) else v) for k, v in sp.items()}
    toxic = sp.get("toxic_pets") == "toxic"
    pet_line = (
        f"PET SAFETY: Toxic to cats and dogs. {sp.get('toxic_note','')}"
        if toxic else
        f"PET SAFETY: Not known to be toxic to cats or dogs. "
        f"{sp.get('toxic_note','')}"
    )
    problems = "\n".join(
        f"  - {clean(p['sign'])}\n    {clean(p['fix'])}"
        for p in sp.get("problems", [])
    )
    # No apostrophes or double quotes anywhere in this text: Etsy stores them
    # HTML-escaped (don't -> don&#39;t) and they render as literal entities.
    return f"""{sp['common']} ({sp['botanical']}) care card - printable, instant download.

A clean 4x6 reference card with everything you actually need to keep this plant
alive, and nothing you do not. Print it, tuck it next to the pot, or keep a set
in a drawer.

WHAT YOU GET
  - 1 print-ready PDF (4x6 inches, 300 DPI)
  - 1 high-resolution PNG, same design
  - Instant download. Nothing is shipped to you.

ON THIS CARD
  LIGHT     {sp['light']}
  WATER     {sp['water']}
  HUMIDITY  {sp['humidity']}
  SOIL      {sp['soil']}
  TEMP      {sp['temp_f']} F
  FEEDING   {sp['feeding']}

{pet_line}

TROUBLESHOOTING INCLUDED
{problems}

GOOD TO KNOW
{sp.get('note','')}

PRINTING
Print at 4x6 on photo paper or cardstock at 100 percent scale. Do not use the
fit-to-page option. Any home printer or drugstore photo kiosk handles this size.

A NOTE ON THE CARE NUMBERS
Watering guidance is given as a condition to check, not a fixed schedule. A
flat every-7-days rule is wrong for most homes, because pot size, light and
season all change it. The card tells you what to look for instead.

This is a digital download. No physical item will be shipped.
Personal use and gifts are fine. Please do not resell or redistribute the files.
""".strip()


def build_listing(sp: dict) -> dict:
    return {
        "slug": sp["slug"],
        "title": build_title(sp),
        "description": build_description(sp),
        "tags": build_tags(sp),
        "price": PRICE_SINGLE,
        "quantity": 999,
        "taxonomy_id": TAXONOMY_DIGITAL_PRINTS,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "is_supply": False,
        "type": "download",
    }


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------

def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# api
# --------------------------------------------------------------------------

def create_draft(e: Etsy, shop_id: str, listing: dict) -> dict:
    payload = {
        "quantity": listing["quantity"],
        "title": listing["title"],
        "description": listing["description"],
        "price": listing["price"],
        "who_made": listing["who_made"],
        "when_made": listing["when_made"],
        "taxonomy_id": listing["taxonomy_id"],
        "is_supply": "true" if listing["is_supply"] else "false",
        "type": listing["type"],
    }
    # Tags must be ONE comma-separated string. Sending repeated "tags" keys
    # returns 201 and silently keeps only the last value -- verified by reading
    # a created listing back and finding 1 tag of 13. Always read back after
    # changing this.
    payload["tags"] = ",".join(listing["tags"])
    r = e.post(f"/shops/{shop_id}/listings", data=payload)
    return {"status": r.status_code, "body": r.text}


def upload_image(e: Etsy, shop_id: str, listing_id: str, path: Path, rank=1):
    with open(path, "rb") as fh:
        r = e.post(
            f"/shops/{shop_id}/listings/{listing_id}/images",
            files={"image": (path.name, fh, "image/jpeg")},
            data={"rank": rank},
        )
    return r


def upload_file(e: Etsy, shop_id: str, listing_id: str, path: Path, rank=1):
    mime = "application/pdf" if path.suffix == ".pdf" else "image/png"
    with open(path, "rb") as fh:
        r = e.post(
            f"/shops/{shop_id}/listings/{listing_id}/files",
            files={"file": (path.name, fh, mime)},
            data={"name": path.name, "rank": rank},
        )
    return r


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true", help="create drafts (free)")
    ap.add_argument("--activate", action="store_true",
                    help="publish drafts - COSTS $0.20 EACH")
    ap.add_argument("--limit", type=int, default=0, help="only process N species")
    args = ap.parse_args()

    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    if args.limit:
        species = species[:args.limit]
    state = load_state()

    if not (args.create or args.activate):
        print("DRY RUN - nothing is sent to Etsy, nothing is spent.\n")
        for sp in species:
            L = build_listing(sp)
            print(f"--- {L['slug']}")
            print(f"  title ({len(L['title'])}/140): {L['title']}")
            print(f"  tags  ({len(L['tags'])}/13): {', '.join(L['tags'])}")
            over = [t for t in L['tags'] if len(t) > MAX_TAG_LEN]
            if over:
                print(f"  !! TAGS OVER {MAX_TAG_LEN} CHARS: {over}")
            print(f"  price: ${L['price']:.2f}   desc: {len(L['description'])} chars")
            for p in (CARDS / f"{sp['slug']}.pdf", PREVIEWS / f"{sp['slug']}.jpg"):
                if not p.exists():
                    print(f"  !! MISSING ASSET: {p.name}")
            print()
        print(f"{len(species)} listings would be created.")
        print(f"Activation cost if published: ${0.20 * len(species):.2f}")
        return 0

    e = Etsy()
    shop_id = e.shop_id()
    if not shop_id:
        sys.exit("No shop id. Run: python scripts/etsy_client.py")

    if args.create:
        for sp in species:
            slug = sp["slug"]
            if state.get(slug, {}).get("listing_id"):
                print(f"  {slug}: already exists, skipping")
                continue
            L = build_listing(sp)
            res = create_draft(e, shop_id, L)
            if res["status"] not in (200, 201):
                print(f"  {slug}: FAILED {res['status']}")
                print(f"    {res['body'][:400]}")
                print("\nStopping on first failure so the problem gets fixed "
                      "rather than repeated 24 times.")
                save_state(state)
                return 1
            listing_id = str(json.loads(res["body"])["listing_id"])
            state[slug] = {"listing_id": listing_id, "state": "draft"}
            print(f"  {slug}: draft {listing_id}")

            ri = upload_image(e, shop_id, listing_id,
                              PREVIEWS / f"{slug}.jpg")
            print(f"    image  {ri.status_code}"
                  f"{'' if ri.status_code in (200,201) else ' ' + ri.text[:200]}")
            for rank, asset in enumerate(
                    [CARDS / f"{slug}.pdf", CARDS / f"{slug}.png"], start=1):
                rf = upload_file(e, shop_id, listing_id, asset, rank)
                print(f"    file {asset.suffix} {rf.status_code}"
                      f"{'' if rf.status_code in (200,201) else ' ' + rf.text[:200]}")
            save_state(state)

    if args.activate:
        todo = [s for s in species
                if state.get(s["slug"], {}).get("state") == "draft"]
        cost = 0.20 * len(todo)
        print(f"About to activate {len(todo)} listings. Cost: ${cost:.2f}")
        if input("Type the cost to confirm (e.g. 4.80): ").strip() != f"{cost:.2f}":
            print("Mismatch - nothing activated.")
            return 1
        for sp in todo:
            slug = sp["slug"]
            lid = state[slug]["listing_id"]
            # PATCH, not PUT: PUT returns 404 on this route.
            r = e.request("PATCH", f"/shops/{shop_id}/listings/{lid}",
                          data={"state": "active"})
            ok = r.status_code in (200, 201)
            print(f"  {slug}: {'active' if ok else 'FAILED ' + r.text[:200]}")
            if ok:
                state[slug]["state"] = "active"
            save_state(state)

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
