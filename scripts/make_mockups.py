#!/usr/bin/env python3
"""Styled square mockups for the Etsy listing thumbnail.

Why this exists, from the data: 86 views produced 0 favourites. A favourite
costs the buyer nothing, so that is not a price objection -- nothing in the
grid was worth saving. Rendering the old previews at Etsy's ~230px grid size
showed why:

  - the plant name is legible, but everything under it is a grey mass of
    unreadable 6px text, so ~80% of the tile is noise;
  - it reads as a worksheet, not as something you would put on a wall;
  - all 40 share one layout, so the shop grid is a wall of identical greys;
  - they are 4:6 portrait in a square grid slot, so they do not fill the tile.

So this does not just enlarge the card. It shows the card as a physical
object on a tinted ground, square, with the tint varying per species so the
grid reads as a collection rather than 40 copies of one thing.

    python scripts/make_mockups.py

Output:
    designs/mockups/<slug>.jpg      2000x2000, listing image rank 1

The card is deliberately rendered small enough that its body text is not
readable -- same rule as the watermarked preview and the 62% pin crop. The
mockup is the advert; the preview (which stays as listing image 2) is the
sample.
"""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_cards import PALETTE, font, wrap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
CARDS = ROOT / "designs" / "cards"
OUT = ROOT / "designs" / "mockups"

S = 2000  # Etsy displays listing images square; fill the tile.

# On-brand grounds. Varying these is what stops the shop grid reading as one
# repeated object -- the single biggest difference at browse size.
# These started much closer in tone and the variety did not survive the
# 230px grid -- five of six tiles read as the same cream. Pushed apart in
# hue and depth until they separate at thumbnail size, which is the only
# size that matters for this decision.
GROUNDS = [
    ((225, 234, 226), (186, 208, 189)),   # sage
    ((240, 229, 216), (219, 196, 172)),   # clay
    ((226, 232, 238), (190, 205, 218)),   # slate
    ((242, 235, 220), (222, 206, 174)),   # sand
    ((238, 228, 228), (214, 190, 190)),   # blush
    ((228, 234, 222), (193, 208, 183)),   # moss
]


def ground_for(slug):
    """Stable per-slug choice, so regenerating never reshuffles the grid."""
    h = int(hashlib.sha1(slug.encode()).hexdigest()[:8], 16)
    return GROUNDS[h % len(GROUNDS)]


def backdrop(base, light, dark):
    """Soft vertical wash plus a low-contrast arc, so the ground has depth
    instead of reading as a flat colour swatch."""
    d = ImageDraw.Draw(base)
    for y in range(S):
        t = y / S
        d.line([(0, y), (S, y)],
               fill=tuple(int(light[i] + (dark[i] - light[i]) * t * 0.55)
                          for i in range(3)))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([-S * 0.25, -S * 0.55, S * 1.25, S * 0.72],
                                 fill=(255, 255, 255, 60))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))


def place_card(base, card, cx, cy, target_h, angle=-4.5):
    """Paste the card rotated, with a real blurred drop shadow under it."""
    w = int(target_h * card.width / card.height)
    thumb = card.convert("RGBA").resize((w, target_h), Image.LANCZOS)

    # Thin paper edge so the card separates from a close-toned ground.
    edged = Image.new("RGBA", (w + 6, target_h + 6), (255, 255, 255, 255))
    edged.paste(thumb, (3, 3))
    rot = edged.rotate(angle, resample=Image.BICUBIC, expand=True)

    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh = Image.new("RGBA", rot.size, (0, 0, 0, 0))
    sh.paste((60, 66, 60, 110), (0, 0), rot.split()[3])
    shadow.paste(sh, (cx - rot.width // 2 + 14, cy - rot.height // 2 + 22), sh)
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))
    base.alpha_composite(rot, (cx - rot.width // 2, cy - rot.height // 2))


def pill(d, cx, y, text, fnt, fg, bg):
    tw = d.textlength(text, font=fnt)
    pad_x, h = 34, fnt.size + 30
    d.rounded_rectangle([cx - tw / 2 - pad_x, y, cx + tw / 2 + pad_x, y + h],
                        radius=h // 2, fill=bg)
    d.text((cx - tw / 2, y + 14), text, font=fnt, fill=fg)
    return h


def mockup(sp, card):
    light, dark = ground_for(sp["slug"])
    base = Image.new("RGBA", (S, S), light + (255,))
    backdrop(base, light, dark)
    d = ImageDraw.Draw(base)

    # -- name ---------------------------------------------------------
    for size in range(150, 74, -4):
        f = font("serif_bold", size)
        lines = wrap(d, sp["common"], f, S - 300)
        if len(lines) <= 2:
            break
    y = 120 if len(lines) == 1 else 86
    for line in lines:
        d.text(((S - d.textlength(line, font=f)) / 2, y), line, font=f,
               fill=PALETTE["ink"])
        y += f.size + 12

    fb = font("serif", 46)
    d.text(((S - d.textlength(sp["botanical"], font=fb)) / 2, y + 6),
           sp["botanical"], font=fb, fill=PALETTE["muted"])

    # -- the card as an object ----------------------------------------
    # Raised and enlarged: at the first pass there was ~360px of dead
    # ground between the botanical name and the top of the card.
    place_card(base, card, S // 2, 1030, 1140)

    # -- tags ---------------------------------------------------------
    d = ImageDraw.Draw(base)
    # Shorter string at a larger size: "PRINTABLE . INSTANT DOWNLOAD" at 40px
    # was an unreadable smudge in the grid. Fewer characters buys height.
    pill(d, S // 2, 1692, "PRINTABLE DOWNLOAD", font("sans_bold", 58),
         (255, 255, 255), PALETTE["accent"] + (255,))

    if sp["toxic_pets"] == "non-toxic":
        pill(d, S // 2, 1800, "PET SAFE", font("sans_bold", 46),
             PALETTE["safe_ink"], PALETTE["safe_bg"] + (255,))

    f_mark = font("sans_bold", 38)
    d.text(((S - d.textlength("leafnote", font=f_mark)) / 2, 1900),
           "leafnote", font=f_mark, fill=PALETTE["accent"])
    return base.convert("RGB")


def main() -> int:
    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for sp in species:
        src = CARDS / f"{sp['slug']}.png"
        if not src.exists():
            print(f"  missing card: {sp['slug']}")
            continue
        mockup(sp, Image.open(src)).save(OUT / f"{sp['slug']}.jpg", "JPEG",
                                         quality=92, optimize=True)
        n += 1
    print(f"mockups: {n} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
