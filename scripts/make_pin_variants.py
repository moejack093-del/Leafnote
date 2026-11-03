#!/usr/bin/env python3
"""Generate four extra Pinterest pins per species, one per search intent.

Why four designs rather than four crops of the same card:

Pinterest is a search engine, and it suppresses near-duplicate images. Posting
the same card teaser again with a different caption gets the second one
buried. Each pin here answers a DIFFERENT question people actually type into
Pinterest -- "why is my monstera yellowing", "how often to water a monstera",
"is monstera toxic to cats", "monstera light requirements" -- so each one
competes in its own search, with its own title, description and artwork.

    python scripts/make_pin_variants.py

Output:
    designs/pins/pinterest/<slug>-{problem,water,toxic,light}.png
    designs/pins/pin_copy_variants.csv

Each pin gives away exactly one fact. That is the hook. The product is the
complete reference card with the troubleshooting table, which none of these
reproduce -- same reasoning as the 62% crop in make_pins.py.
"""

import csv
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_cards import PALETTE, font, wrap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
STATE = ROOT / "data" / "listings.json"
OUT = ROOT / "designs" / "pins"
PINS = OUT / "pinterest"

SHOP = "https://www.etsy.com/shop/LeafnoteStudio"
BLOG = "https://leafnotestudio.github.io/plants"

# Troubleshooting pins go to the blog article, not the listing.
#
# Two reasons. First, intent: someone who searched "why is my monstera
# yellowing" wants that question answered, and dropping them on a $4
# product page is the wrong answer -- it is a plausible part of why 86
# views produced 0 favourites. The article answers it and then offers the
# card. Second, links: the blog was live, correct and completely orphaned,
# with all 203 pins pointing at Etsy. Google finds pages through links, so
# nothing pointing at it meant nothing indexing it.
#
# The water/toxic/light pins still go straight to Etsy. Those are product
# questions, and the extra hop would only cost conversions.
LINK_TO_BLOG = {"problem"}

W, H = 1000, 1500
M = 70

# Fixed y for the quick-facts strip so all four designs line up as a set.
FACTS_Y = 880


def fit(d, text, kind, hi, lo, max_w, max_lines):
    """Largest size in [lo, hi] where text wraps into <= max_lines lines.

    Plant names run from "ZZ Plant" to "Pink Princess Philodendron", and a
    fixed size that suits one overflows the other. Measuring beats guessing.
    """
    for size in range(hi, lo - 1, -2):
        f = font(kind, size)
        lines = wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = font(kind, lo)
    return f, wrap(d, text, f, max_w)[:max_lines]


def panel(d, box, fill):
    d.rounded_rectangle(list(box), radius=14, fill=fill)


def footer(d, right_label):
    fy = H - 118
    d.line([(M, fy - 26), (W - M, fy - 26)], fill=PALETTE["rule"], width=2)
    d.text((M, fy), "leafnote", font=font("sans_bold", 32),
           fill=PALETTE["accent"])
    f = font("sans", 29)
    d.text((W - M - d.textlength(right_label, font=f), fy + 3),
           right_label, font=f, fill=PALETTE["muted"])


def head(d, eyebrow, question):
    """Shared top block: eyebrow label, then the question in serif."""
    d.text((M, 72), eyebrow, font=font("sans_bold", 28),
           fill=PALETTE["accent"])
    f, lines = fit(d, question, "serif_bold", 72, 46, W - 2 * M, 3)
    y = 122
    for line in lines:
        d.text((M, y), line, font=f, fill=PALETTE["ink"])
        y += f.size + 10
    return y + 14


def body(d, y, text, max_y):
    """Detail paragraph, trimmed to whole lines that fit above max_y."""
    f = font("sans", 31)
    for line in wrap(d, text, f, W - 2 * M):
        if y + f.size > max_y:
            break
        d.text((M, y), line, font=f, fill=PALETTE["muted"])
        y += 44
    return y


def facts(d, y, sp, skip):
    """Scannable quick-facts rows filling the middle of the pin.

    Without this the layout ran out of content around 40% height and the
    bottom half sat empty -- the same dead-space defect the cards had. An
    empty lower half also wastes the tall format Pinterest rewards.

    `skip` drops the fact this particular pin is already about, so the
    water pin does not repeat the watering line back at itself.
    """
    rows = [("LIGHT", sp["light_short"]), ("WATER", sp["water_short"]),
            ("HUMIDITY", sp["humidity"].split(".")[0]),
            ("TEMP", f"{sp['temp_f']} F"),
            ("PETS", "Non-toxic to cats and dogs"
             if sp["toxic_pets"] == "non-toxic" else "Toxic to cats and dogs")]
    rows = [r for r in rows if r[0] != skip][:3]

    f_lab, f_val = font("sans_bold", 24), font("sans", 31)
    for label, value in rows:
        d.line([(M, y), (W - M, y)], fill=PALETTE["rule"], width=1)
        d.text((M, y + 20), label, font=f_lab, fill=PALETTE["accent"])
        vx = M + 190
        for line in wrap(d, value, f_val, W - M - vx)[:2]:
            d.text((vx, y + 16), line, font=f_val, fill=PALETTE["ink"])
            y += 38
        y += 30
    return y


def cta(d):
    """Advert block above the footer. The pin gives away one fact; this is
    what says there is a complete card behind it."""
    top = H - 336
    panel(d, (M, top, W - M, top + 148), PALETTE["safe_bg"])
    d.text((M + 32, top + 26), "The full printable care card",
           font=font("serif_bold", 42), fill=PALETTE["accent"])
    f = font("sans", 28)
    y = top + 82
    for line in wrap(d, "Light, water, humidity, feeding and a "
                        "troubleshooting table. 4x6in, instant download.",
                     f, W - 2 * M - 64)[:2]:
        d.text((M + 32, y), line, font=f, fill=PALETTE["muted"])
        y += 34


def sun(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=PALETTE["accent"],
              width=5)
    for i in range(8):
        a = math.radians(i * 45)
        d.line([(cx + math.cos(a) * (r + 12), cy + math.sin(a) * (r + 12)),
                (cx + math.cos(a) * (r + 26), cy + math.sin(a) * (r + 26))],
               fill=PALETTE["accent"], width=5)


def drop(d, cx, cy, r):
    d.ellipse([cx - r, cy - r * 0.75, cx + r, cy + r], fill=PALETTE["accent"])
    d.polygon([(cx, cy - r * 1.9), (cx - r * 0.72, cy + r * 0.1),
               (cx + r * 0.72, cy + r * 0.1)], fill=PALETTE["accent"])


# -- the four templates ------------------------------------------------

def pin_problem(sp):
    """'Why is my X <symptom>?' -- the highest-intent search there is."""
    p = sp["problems"][0]
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    # The symptom is the headline, not "why is my X ...?". The signs in
    # species.json are a mix of noun phrases ("Brown leaf tips") and full
    # clauses ("Leaves stay whole with no splits"), so no single question
    # wrapper stays grammatical across all 40. Leading with the symptom is
    # also what a searcher is actually scanning the thumbnail for.
    y = head(d, f"{sp['common'].upper()}  /  TROUBLESHOOTING", p["sign"])

    # Accent bar beside the cause: makes this pin read differently from the
    # others at thumbnail size, which is the whole point of four designs.
    top = y + 10
    f, lines = fit(d, p["cause"], "serif_bold", 56, 34, W - 2 * M - 34, 4)
    bar_h = len(lines) * (f.size + 12) + 18
    d.rectangle([M, top, M + 10, top + bar_h], fill=PALETTE["accent"])
    yy = top + 8
    for line in lines:
        d.text((M + 34, yy), line, font=f, fill=PALETTE["ink"])
        yy += f.size + 12

    yy = top + bar_h + 34
    d.text((M, yy), "THE FIX", font=font("sans_bold", 26),
           fill=PALETTE["accent"])
    body(d, yy + 40, p["fix"], FACTS_Y - 20)
    facts(d, FACTS_Y, sp, "")
    cta(d)
    footer(d, "printable care card")
    return img


def pin_water(sp):
    """'How often to water X' -- the question that kills the most plants."""
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    y = head(d, "WATERING", f"How often to water a {sp['common']}")

    top = y + 16
    f, lines = fit(d, sp["water_short"], "serif_bold", 92, 48,
                   W - 2 * M - 150, 2)
    ph = len(lines) * (f.size + 10) + 56
    panel(d, (M, top, W - M, top + ph), PALETTE["safe_bg"])
    drop(d, W - M - 76, top + ph // 2, 32)
    yy = top + 28
    for line in lines:
        d.text((M + 34, yy), line, font=f, fill=PALETTE["accent"])
        yy += f.size + 10

    body(d, top + ph + 34, sp["water"], FACTS_Y - 20)
    facts(d, FACTS_Y, sp, "WATER")
    cta(d)
    footer(d, "full card in the shop")
    return img


def pin_toxic(sp):
    """'Is X toxic to cats' -- enormous volume, and an honest answer builds
    more trust than a reassuring one."""
    safe = sp["toxic_pets"] == "non-toxic"
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    y = head(d, "PETS", f"Is a {sp['common']} toxic to cats and dogs?")

    verdict = "No." if safe else "Yes."
    tint = PALETTE["safe_bg"] if safe else PALETTE["toxic_bg"]
    ink = PALETTE["safe_ink"] if safe else PALETTE["toxic_ink"]

    top = y + 16
    f = font("serif_bold", 130)
    sub = "Safe around cats and dogs" if safe else "Keep it out of reach"
    fs = font("sans", 34)
    ph = f.size + 92
    panel(d, (M, top, W - M, top + ph), tint)
    d.text((M + 34, top + 18), verdict, font=f, fill=ink)
    d.text((M + 34 + d.textlength(verdict, font=f) + 26,
            top + 18 + f.size - 56), sub, font=fs, fill=ink)

    body(d, top + ph + 34, sp["toxic_note"], FACTS_Y - 20)
    facts(d, FACTS_Y, sp, "PETS")
    cta(d)
    footer(d, "printable care card")
    return img


def pin_light(sp):
    """'Where to put X' -- light is the thing people get wrong at purchase."""
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    y = head(d, "LIGHT", f"Where to put your {sp['common']}")

    top = y + 16
    f, lines = fit(d, sp["light_short"], "serif_bold", 92, 48,
                   W - 2 * M - 180, 2)
    ph = len(lines) * (f.size + 10) + 56
    panel(d, (M, top, W - M, top + ph), PALETTE["safe_bg"])
    sun(d, W - M - 84, top + ph // 2, 30)
    yy = top + 28
    for line in lines:
        d.text((M + 34, yy), line, font=f, fill=PALETTE["accent"])
        yy += f.size + 10

    body(d, top + ph + 34, sp["light"], FACTS_Y - 20)
    facts(d, FACTS_Y, sp, "LIGHT")
    cta(d)
    footer(d, "full card in the shop")
    return img


# -- copy --------------------------------------------------------------

TAGS = "#houseplants #plantcare #planttips"


def rows_for(sp):
    safe = sp["toxic_pets"] == "non-toxic"
    board = "Pet-Safe Houseplants" if safe else "Houseplant Care"
    p = sp["problems"][0]
    c, b = sp["common"], sp["botanical"]
    return [
        ("problem", "Houseplant Care",
         f"{c}: {p['sign']} - Cause and Fix",
         f"{c} ({b}) - {p['sign'].lower()}. The usual cause: "
         f"{p['cause'][0].lower()}{p['cause'][1:]} The fix: {p['fix']} "
         f"The printable card has the rest of the troubleshooting list. "
         f"{TAGS} #plantproblems"),
        ("water", board,
         f"How Often to Water a {c}",
         f"{c} ({b}) watering, without the guesswork: {sp['water']} "
         f"Overwatering kills more houseplants than neglect does. Full "
         f"printable care card with light, humidity and troubleshooting. "
         f"{TAGS} #wateringplants"),
        ("toxic", board,
         f"Is a {c} Toxic to Cats and Dogs?",
         (f"{c} ({b}) is non-toxic to cats and dogs. " if safe
          else f"{c} ({b}) is toxic to cats and dogs. ")
         + f"{sp['toxic_note']} The printable care card covers light, water "
           f"and what to do when it sulks. {TAGS} "
         + ("#petsafeplants #catsafeplants" if safe else "#petsafety")),
        ("light", board,
         f"{c} Light Requirements - Where to Put It",
         f"Where a {c} ({b}) actually wants to live: {sp['light']} "
         f"Getting light right fixes most problems before they start. "
         f"Printable 4x6 care card, instant download. {TAGS} #plantlight"),
    ]


BUILDERS = {"problem": pin_problem, "water": pin_water,
            "toxic": pin_toxic, "light": pin_light}


def main() -> int:
    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    listings = json.loads(STATE.read_text(encoding="utf-8")) \
        if STATE.exists() else {}
    PINS.mkdir(parents=True, exist_ok=True)

    out = []
    for sp in species:
        rec = listings.get(sp["slug"])
        link = SHOP
        if rec:
            link = rec.get("url") or \
                f"https://www.etsy.com/listing/{rec['listing_id']}"

        for kind, board, title, desc in rows_for(sp):
            name = f"{sp['slug']}-{kind}.png"
            BUILDERS[kind](sp).save(PINS / name, "PNG")
            dest = (f"{BLOG}/{sp['slug']}/" if kind in LINK_TO_BLOG
                    else link)
            out.append({"file": f"pinterest/{name}", "board": board,
                        "title": title[:100], "description": desc[:480],
                        "link": dest})

    with open(OUT / "pin_copy_variants.csv", "w", newline="",
              encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["file", "board", "title",
                                            "description", "link"])
        wr.writeheader()
        wr.writerows(out)

    print(f"variant pins : {len(out)}  -> {PINS}")
    print(f"copy         : {OUT / 'pin_copy_variants.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
