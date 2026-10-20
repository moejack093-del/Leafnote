#!/usr/bin/env python3
"""Generate Pinterest pins and TikTok carousel slides, plus the copy to go
with them.

Pinterest is the better channel for this product: it is a search engine with a
content half-life measured in months, where TikTok is a feed that forgets you
in days. So the species pins are Pinterest-first, and the TikTok output is
photo-carousel slides (no video, nothing to film).

    python scripts/make_pins.py

Output:
    designs/pins/pinterest/*.png   1000x1500
    designs/pins/tiktok/*.png      1080x1920
    designs/pins/pin_copy.csv      title / description / board / link per pin
"""

import csv
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_cards import PALETTE, font, wrap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
CARDS = ROOT / "designs" / "cards"
STATE = ROOT / "data" / "listings.json"
OUT = ROOT / "designs" / "pins"

SHOP = "https://www.etsy.com/shop/LeafnoteStudio"
PIN_W, PIN_H = 1000, 1500
TT_W, TT_H = 1080, 1920


def shadowed(base, card, box):
    """Paste the card with a soft offset shadow so it reads as a physical
    thing rather than a flat screenshot."""
    x, y, w, h = box
    thumb = card.resize((w, h), Image.LANCZOS)
    shadow = Image.new("RGB", (w, h), (214, 210, 199))
    base.paste(shadow, (x + 7, y + 9))
    base.paste(thumb, (x, y))
    d = ImageDraw.Draw(base)
    d.rectangle([x, y, x + w, y + h], outline=(222, 217, 206), width=2)


def species_pin(sp, card):
    img = Image.new("RGB", (PIN_W, PIN_H), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    m = 70

    d.text((m, 70), "PRINTABLE CARE CARD", font=font("sans_bold", 28),
           fill=PALETTE["accent"])

    y = 118
    for line in wrap(d, sp["common"], font("serif_bold", 76), PIN_W - 2 * m):
        d.text((m, y), line, font=font("serif_bold", 76), fill=PALETTE["ink"])
        y += 82

    hook = (f"Pet safe around cats and dogs"
            if sp["toxic_pets"] == "non-toxic" else
            f"Toxic to cats and dogs - know before you buy")
    d.text((m, y + 6), hook, font=font("sans", 30), fill=PALETTE["muted"])

    # Show only the top of the card. A full, legible card on a public pin is
    # a free substitute for the thing being sold -- the same mistake the
    # watermarked Etsy previews exist to avoid. Cropping at 62% keeps the
    # plant name and the first care rows visible and cuts off before the
    # troubleshooting section, which is most of the value.
    teaser = card.crop((0, 0, card.width, int(card.height * 0.62)))

    top = y + 74
    avail = (PIN_H - 150) - top
    card_h = avail
    card_w = int(card_h * teaser.width / teaser.height)
    if card_w > PIN_W - 2 * m:                 # width-bound on short crops
        card_w = PIN_W - 2 * m
        card_h = int(card_w * teaser.height / teaser.width)
    shadowed(img, teaser, ((PIN_W - card_w) // 2,
                           top + (avail - card_h) // 2, card_w, card_h))

    fy = PIN_H - 128
    d.line([(m, fy - 26), (PIN_W - m, fy - 26)], fill=PALETTE["rule"], width=2)
    d.text((m, fy), "leafnote", font=font("sans_bold", 32),
           fill=PALETTE["accent"])
    t = "instant download"
    d.text((PIN_W - m - d.textlength(t, font=font("sans", 30)), fy + 2),
           t, font=font("sans", 30), fill=PALETTE["muted"])
    return img


def list_pin(title, subtitle, items, size=(PIN_W, PIN_H), accent_count=None):
    w, h = size
    img = Image.new("RGB", (w, h), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    m = int(w * 0.08)

    if accent_count:
        d.text((m, int(h * 0.06)), accent_count, font=font("serif_bold", 150),
               fill=PALETTE["accent"])
        y = int(h * 0.06) + 165
    else:
        y = int(h * 0.07)

    for line in wrap(d, title, font("serif_bold", 68), w - 2 * m):
        d.text((m, y), line, font=font("serif_bold", 68), fill=PALETTE["ink"])
        y += 76
    y += 8
    for line in wrap(d, subtitle, font("sans", 30), w - 2 * m):
        d.text((m, y), line, font=font("sans", 30), fill=PALETTE["muted"])
        y += 40

    y += 26
    d.line([(m, y), (w - m, y)], fill=PALETTE["rule"], width=2)
    y += 30

    f_item = font("sans", 36)
    # Stop early enough that the "+N more" line clears the footer rule. At
    # h-190 the overflow line was drawn straight through it.
    cutoff = h - 215
    for i, item in enumerate(items, 1):
        if y > cutoff:
            d.text((m, y), f"+ {len(items) - i + 1} more", font=f_item,
                   fill=PALETTE["accent"])
            break
        d.text((m, y), f"{i}.", font=font("sans_bold", 34),
               fill=PALETTE["accent"])
        d.text((m + 58, y), item, font=f_item, fill=PALETTE["ink"])
        y += 52

    fy = h - 110
    d.line([(m, fy - 24), (w - m, fy - 24)], fill=PALETTE["rule"], width=2)
    d.text((m, fy), "leafnote", font=font("sans_bold", 32),
           fill=PALETTE["accent"])
    return img


def main() -> int:
    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    listings = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}

    pdir = OUT / "pinterest"
    tdir = OUT / "tiktok"
    pdir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)

    rows = []

    # -- one pin per species -------------------------------------------
    for sp in species:
        card_path = CARDS / f"{sp['slug']}.png"
        if not card_path.exists():
            print(f"  missing card: {sp['slug']}")
            continue
        card = Image.open(card_path)
        species_pin(sp, card).save(pdir / f"{sp['slug']}.png", "PNG")

        safe = sp["toxic_pets"] == "non-toxic"
        link = SHOP
        if sp["slug"] in listings:
            link = f"https://www.etsy.com/listing/{listings[sp['slug']]['listing_id']}"

        rows.append({
            "file": f"pinterest/{sp['slug']}.png",
            "board": "Pet-Safe Houseplants" if safe else "Houseplant Care",
            "title": f"{sp['common']} Care Guide - Printable Card"[:100],
            "description": (
                f"How to actually keep a {sp['common']} ({sp['botanical']}) alive. "
                f"Light: {sp['light_short'].lower()}. Water: {sp['water_short'].lower()}. "
                + ("Safe around cats and dogs. " if safe
                   else "Toxic to cats and dogs - worth knowing before you buy. ")
                + "Printable 4x6 card with troubleshooting on the back half. "
                  "#houseplants #planttips #plantcare"
            )[:480],
            "link": link,
        })

    # -- list pins ------------------------------------------------------
    safe_names = [s["common"] for s in species if s["toxic_pets"] == "non-toxic"]
    easy_names = [s["common"] for s in species if s["difficulty"] == "easy"]
    tricky = [s["common"] for s in species if s["difficulty"] == "tricky"]

    lists = [
        ("pet-safe", str(len(safe_names)), "Houseplants that are safe for cats and dogs",
         "No panic-googling in the shop. Every one of these is non-toxic.",
         safe_names, "Pet-Safe Houseplants",
         f"{len(safe_names)} houseplants that will not poison your cat or dog",
         "Every plant here is non-toxic to cats and dogs. Note that most toxic "
         "houseplants cause mouth irritation and an upset stomach rather than "
         "anything worse, but if you want to stop worrying entirely, start with "
         "this list. #petsafeplants #catsafeplants #houseplants"),
        ("easy-care", str(len(easy_names)), "Houseplants that are genuinely hard to kill",
         "Forgiving of neglect, bad light, and the occasional forgotten month.",
         easy_names, "Houseplant Care",
         f"{len(easy_names)} houseplants that survive almost anything",
         "If you have killed things before, start here. These tolerate low light, "
         "irregular watering and general neglect. The most common way people kill "
         "all of them is overwatering, not under. #houseplants #beginnerplants "
         "#plantcare"),
        ("tricky", str(len(tricky)), "Houseplants that will test your patience",
         "Worth it, but read the care notes before you buy.",
         tricky, "Houseplant Care",
         "The houseplants that are genuinely difficult - and what they need",
         "These are the ones that drop leaves, crisp at the edges and generally "
         "punish guesswork. Humidity and water quality matter far more than for "
         "the easy plants. #houseplants #plantcare #planttips"),
    ]

    for slug, count, title, sub, items, board, pin_title, pin_desc in lists:
        list_pin(title, sub, items, accent_count=count).save(
            pdir / f"list-{slug}.png", "PNG")
        rows.append({
            "file": f"pinterest/list-{slug}.png",
            "board": board,
            "title": pin_title[:100],
            "description": pin_desc[:480],
            "link": SHOP,
        })

        # TikTok carousel cover at 9:16 from the same content
        list_pin(title, sub, items, size=(TT_W, TT_H),
                 accent_count=count).save(tdir / f"list-{slug}.png", "PNG")

    with open(OUT / "pin_copy.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["file", "board", "title",
                                            "description", "link"])
        wr.writeheader()
        wr.writerows(rows)

    print(f"pinterest pins : {len(rows)}  -> {pdir}")
    print(f"tiktok slides  : {len(lists)}  -> {tdir}")
    print(f"copy           : {OUT / 'pin_copy.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
