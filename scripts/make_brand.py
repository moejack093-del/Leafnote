#!/usr/bin/env python3
"""Generate the shop icon and banner for manual upload.

Etsy's v3 API cannot set either, so these are produced as files and uploaded
by hand in Shop Manager. Shares the card palette and fonts so the storefront
and the product read as one thing.

    python scripts/make_brand.py

Output: designs/brand/icon.png (500x500), designs/brand/banner.png (1600x400)
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_cards import PALETTE, font  # noqa: E402  (one design system)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "designs" / "brand"


def leaf_polygon(cx, cy, w, h, lean=0.0):
    """A lens-shaped leaf. sin(pi*t)**0.75 gives a fuller belly and a sharper
    tip than a plain ellipse, which reads as a generic blob at small sizes."""
    pts = []
    steps = 60
    for i in range(steps + 1):          # right edge, tip -> base
        t = i / steps
        pts.append((cx + (w / 2) * math.sin(math.pi * t) ** 0.75 + lean * t * w,
                    cy - h / 2 + t * h))
    for i in range(steps, -1, -1):      # left edge, base -> tip
        t = i / steps
        pts.append((cx - (w / 2) * math.sin(math.pi * t) ** 0.75 + lean * t * w,
                    cy - h / 2 + t * h))
    return pts


def draw_leaf(d, cx, cy, w, h, fill, rib=None):
    d.polygon(leaf_polygon(cx, cy, w, h), fill=fill)
    if rib:
        d.line([(cx, cy - h / 2 + h * 0.06), (cx, cy + h / 2 - h * 0.04)],
               fill=rib, width=max(2, int(w * 0.035)))
        # Veins angle toward the tip (upward, since the tip is at the top).
        # Angling them away reads as a conifer rather than a leaf.
        for k in range(1, 5):
            t = 0.22 + k * 0.16
            y = cy - h / 2 + t * h
            spread = (w / 2) * math.sin(math.pi * t) ** 0.75 * 0.62
            for direction in (-1, 1):
                d.line([(cx, y), (cx + direction * spread, y - h * 0.075)],
                       fill=rib, width=max(1, int(w * 0.022)))


def make_icon(size=500) -> Image.Image:
    img = Image.new("RGB", (size, size), PALETTE["accent"])
    d = ImageDraw.Draw(img)
    draw_leaf(d, size / 2, size * 0.47, size * 0.46, size * 0.62,
              fill=PALETTE["bg"], rib=PALETTE["accent"])
    return img


def make_banner(w=1600, h=400) -> Image.Image:
    img = Image.new("RGB", (w, h), PALETTE["bg"])
    d = ImageDraw.Draw(img)

    # A trio of pale leaves at the right, each fully inside the frame. An
    # earlier version bled one huge leaf off the edge, which just read as a
    # stray pale circle rather than foliage.
    for cx, scale, tone in ((w * 0.78, 0.74, (231, 238, 232)),
                            (w * 0.87, 1.00, (223, 233, 225)),
                            (w * 0.955, 0.80, (231, 238, 232))):
        draw_leaf(d, cx, h * 0.5, 120 * scale, h * 0.78 * scale, fill=tone)

    draw_leaf(d, 150, h * 0.5, 86, 150, fill=PALETTE["accent"],
              rib=PALETTE["bg"])

    f_name = font("serif_bold", 96)
    f_tag = font("sans", 34)
    name_x, name_y = 232, h * 0.5 - 86
    d.text((name_x, name_y), "leafnote", font=f_name, fill=PALETTE["ink"])
    d.text((name_x + 6, h * 0.5 + 24),
           "Printable care cards for the houseplants you actually own",
           font=f_tag, fill=PALETTE["muted"])
    # Rule matches the wordmark width instead of a guessed constant.
    rule_w = d.textlength("leafnote", font=f_name)
    d.line([(name_x + 6, h * 0.5 + 10), (name_x + rule_w, h * 0.5 + 10)],
           fill=PALETTE["accent"], width=3)
    return img


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    make_icon().save(OUT / "icon.png", "PNG")
    make_banner().save(OUT / "banner.png", "PNG")
    print(f"icon.png   500x500   -> {OUT}")
    print(f"banner.png 1600x400  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
