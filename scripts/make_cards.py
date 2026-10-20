#!/usr/bin/env python3
"""Generate printable plant care cards from data/species.json.

One design system, N cards. Change the care data and every card regenerates
consistently -- which is the point of doing this programmatically instead of
generating each card as a separate image.

Output: designs/cards/<slug>.png (300 DPI) and <slug>.pdf (print-ready).

Runs on Windows locally and on Linux CI; fonts fall back accordingly.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "species.json"
OUT = ROOT / "designs" / "cards"
PREVIEW = ROOT / "designs" / "previews"

# 4x6in at 300dpi -- a standard photo print size, so buyers can print at home
# or at any drugstore kiosk without resizing.
DPI = 300
W, H = 4 * DPI, 6 * DPI
MARGIN = 90

PALETTE = {
    "bg": (251, 249, 244),
    "ink": (31, 42, 36),
    "muted": (107, 122, 112),
    "accent": (47, 93, 69),
    "rule": (216, 211, 199),
    "toxic_bg": (247, 235, 231),
    "toxic_ink": (154, 59, 40),
    "safe_bg": (234, 243, 237),
    "safe_ink": (47, 93, 69),
}

# Windows first, then the DejaVu set that ships on GitHub Actions runners.
FONT_CANDIDATES = {
    "serif": ["georgia.ttf", "Georgia.ttf", "DejaVuSerif.ttf"],
    "serif_bold": ["georgiab.ttf", "Georgia-Bold.ttf", "DejaVuSerif-Bold.ttf"],
    "serif_italic": ["georgiai.ttf", "Georgia-Italic.ttf", "DejaVuSerif-Italic.ttf"],
    "sans": ["segoeui.ttf", "SegoeUI.ttf", "DejaVuSans.ttf"],
    "sans_bold": ["segoeuib.ttf", "SegoeUI-Bold.ttf", "DejaVuSans-Bold.ttf"],
}

FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype"),
    Path("/Library/Fonts"),
]

_font_cache: dict = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    for name in FONT_CANDIDATES[kind]:
        for d in FONT_DIRS:
            p = d / name
            if p.exists():
                f = ImageFont.truetype(str(p), size)
                _font_cache[key] = f
                return f
    # Last resort: bitmap default. Ugly but never crashes the build.
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


def wrap(draw, text: str, fnt, max_w: int) -> list:
    """Greedy word wrap measured against the actual rendered width."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, xy, text, fnt, fill, max_w, leading=1.35) -> int:
    """Draw wrapped text; return the y position just past the last line."""
    x, y = xy
    lh = int(fnt.size * leading)
    for line in wrap(draw, text, fnt, max_w):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += lh
    return y


def render(sp: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    inner = W - 2 * MARGIN
    y = MARGIN

    # --- header: eyebrow + difficulty -----------------------------------
    f_eyebrow = font("sans_bold", 26)
    d.text((MARGIN, y), "PLANT CARE", font=f_eyebrow, fill=PALETTE["accent"])
    diff = sp.get("difficulty", "").upper()
    if diff:
        tw = d.textlength(diff, font=f_eyebrow)
        d.text((W - MARGIN - tw, y), diff, font=f_eyebrow, fill=PALETTE["muted"])
    y += 52

    # --- names -----------------------------------------------------------
    y = text_block(d, (MARGIN, y), sp["common"], font("serif_bold", 82),
                   PALETTE["ink"], inner, leading=1.1)
    y += 10
    y = text_block(d, (MARGIN, y), sp["botanical"], font("serif_italic", 38),
                   PALETTE["muted"], inner)
    y += 28
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=PALETTE["rule"], width=2)
    y += 34

    # --- care rows -------------------------------------------------------
    rows = [
        ("LIGHT", sp["light"]),
        ("WATER", sp["water"]),
        ("HUMIDITY", sp["humidity"]),
        ("SOIL", sp["soil"]),
        ("TEMP", f"{sp['temp_f']} \u00b0F"),
        ("FEEDING", sp["feeding"]),
    ]
    f_label = font("sans_bold", 24)
    f_value = font("sans", 31)
    label_w = 190
    for label, value in rows:
        d.text((MARGIN, y + 6), label, font=f_label, fill=PALETTE["accent"])
        y_end = text_block(d, (MARGIN + label_w, y), value, f_value,
                           PALETTE["ink"], inner - label_w, leading=1.3)
        y = y_end + 18

    y += 10

    # --- pet safety badge -------------------------------------------------
    is_toxic = sp.get("toxic_pets") == "toxic"
    badge_bg = PALETTE["toxic_bg"] if is_toxic else PALETTE["safe_bg"]
    badge_ink = PALETTE["toxic_ink"] if is_toxic else PALETTE["safe_ink"]
    headline = "TOXIC TO CATS & DOGS" if is_toxic else "PET SAFE"

    f_badge = font("sans_bold", 28)
    f_note = font("sans", 26)
    note_lines = wrap(d, sp.get("toxic_note", ""), f_note, inner - 56)
    badge_h = 34 + 38 + len(note_lines) * int(f_note.size * 1.3) + 26
    d.rounded_rectangle([(MARGIN, y), (W - MARGIN, y + badge_h)],
                        radius=18, fill=badge_bg)
    by = y + 26
    d.text((MARGIN + 28, by), headline, font=f_badge, fill=badge_ink)
    by += 44
    for line in note_lines:
        d.text((MARGIN + 28, by), line, font=f_note, fill=badge_ink)
        by += int(f_note.size * 1.3)
    y += badge_h + 36

    # --- troubleshooting, as many as fit ---------------------------------
    footer_reserve = 130
    f_sec = font("sans_bold", 24)
    f_sign = font("sans_bold", 28)
    f_fix = font("sans", 27)

    if y + 120 < H - footer_reserve:
        d.text((MARGIN, y), "IF SOMETHING LOOKS WRONG", font=f_sec,
               fill=PALETTE["accent"])
        y += 42
        for prob in sp.get("problems", []):
            sign_lines = wrap(d, prob["sign"], f_sign, inner)
            fix_lines = wrap(d, prob["fix"], f_fix, inner)
            need = (len(sign_lines) * int(f_sign.size * 1.25)
                    + len(fix_lines) * int(f_fix.size * 1.3) + 24)
            if y + need > H - footer_reserve:
                break
            y = text_block(d, (MARGIN, y), prob["sign"], f_sign,
                           PALETTE["ink"], inner, leading=1.25)
            y = text_block(d, (MARGIN, y + 2), prob["fix"], f_fix,
                           PALETTE["muted"], inner, leading=1.3)
            y += 22

    # --- good to know -----------------------------------------------------
    # Lives in the body, not the footer: the text is a full sentence or two and
    # was previously truncated to a single line. It also absorbs the slack on
    # cards whose troubleshooting list is short.
    tip = sp.get("note", "")
    if tip:
        f_tip = font("sans", 27)
        tip_lines = wrap(d, tip, f_tip, inner - 56)
        block_h = 30 + 38 + len(tip_lines) * int(f_tip.size * 1.3)
        ty = max(y + 10, H - footer_reserve - block_h - 24)
        if ty + block_h <= H - footer_reserve:
            d.rounded_rectangle([(MARGIN, ty), (W - MARGIN, ty + block_h)],
                                radius=18, fill=(244, 241, 233))
            iy = ty + 24
            d.text((MARGIN + 28, iy), "GOOD TO KNOW", font=f_sec,
                   fill=PALETTE["accent"])
            iy += 40
            for line in tip_lines:
                d.text((MARGIN + 28, iy), line, font=f_tip,
                       fill=PALETTE["ink"])
                iy += int(f_tip.size * 1.3)

    # --- footer ----------------------------------------------------------
    fy = H - MARGIN - 34
    d.line([(MARGIN, fy - 20), (W - MARGIN, fy - 20)],
           fill=PALETTE["rule"], width=2)
    d.text((MARGIN, fy), "leafnote", font=font("sans_bold", 24),
           fill=PALETTE["accent"])
    bot = sp["botanical"]
    f_foot = font("sans", 24)
    tw = d.textlength(bot, font=f_foot)
    d.text((W - MARGIN - tw, fy), bot, font=f_foot, fill=PALETTE["muted"])

    return img


def make_preview(card: Image.Image) -> Image.Image:
    """Downscaled, watermarked copy for the public Etsy listing image.

    The listing photo is visible to anyone browsing, so it must not be a
    usable substitute for the file people pay for. Half resolution plus a
    repeating diagonal mark keeps it readable as a sample while making it
    poor to print.
    """
    prev = card.resize((card.width // 2, card.height // 2), Image.LANCZOS)
    mark = Image.new("RGBA", prev.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(mark)
    f = font("sans_bold", 34)
    text = "leafnote  •  preview"
    step_x, step_y = 420, 240
    for row, y in enumerate(range(-60, prev.height + step_y, step_y)):
        offset = (row % 2) * (step_x // 2)
        for x in range(-260 + offset, prev.width + step_x, step_x):
            md.text((x, y), text, font=f, fill=(47, 93, 69, 46))
    rotated = mark.rotate(30, resample=Image.BICUBIC, center=(prev.width // 2,
                                                              prev.height // 2))
    return Image.alpha_composite(prev.convert("RGBA"), rotated).convert("RGB")


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    made = 0
    for sp in data["species"]:
        img = render(sp)
        img.save(OUT / f"{sp['slug']}.png", "PNG", dpi=(DPI, DPI))
        img.save(OUT / f"{sp['slug']}.pdf", "PDF", resolution=DPI)
        make_preview(img).save(PREVIEW / f"{sp['slug']}.jpg", "JPEG", quality=86)
        made += 1
        print(f"  {sp['slug']}")
    print(f"\n{made} cards -> {OUT}")
    print(f"{made} previews -> {PREVIEW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
