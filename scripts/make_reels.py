#!/usr/bin/env python3
"""Build vertical 9:16 videos for Instagram Reels and TikTok.

    python scripts/make_reels.py --limit 3        # proof, 3 plants
    python scripts/make_reels.py --all

Output:
    designs/reels/<slug>.mp4      1080x1920, ~12s, H.264, no audio

Structure is the troubleshooting content, because that is what stops a
scroll: a symptom someone recognises, then the cause, then the fix. The
card only appears at the end, as the payoff.

Honest limitation, worth knowing before building anything on this:
these videos are SILENT. Both platforms heavily favour clips using
trending audio, and trending audio can only be attached from inside the
app -- it is not available through either API, and I cannot supply
licensed music. So an API-posted Reel starts at a reach disadvantage no
amount of editing fixes. Posting manually and adding a trending sound in
the app will materially outperform anything posted automatically.

ffmpeg comes from the imageio-ffmpeg wheel, so there is nothing to
install by hand and nothing to pay for.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_cards import PALETTE, font, wrap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
CARDS = ROOT / "designs" / "cards"
OUT = ROOT / "designs" / "reels"

W, H = 1080, 1920
M = 90
FPS = 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def centered(d, lines, f, y, fill, gap=14):
    for line in lines:
        d.text(((W - d.textlength(line, font=f)) / 2, y), line, font=f,
               fill=fill)
        y += f.size + gap
    return y


def fit(d, text, kind, hi, lo, max_w, max_lines):
    for size in range(hi, lo - 1, -4):
        f = font(kind, size)
        lines = wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = font(kind, lo)
    return f, wrap(d, text, f, max_w)[:max_lines]


def slide(bg=None):
    img = Image.new("RGB", (W, H), bg or PALETTE["bg"])
    return img, ImageDraw.Draw(img)


def hook_slide(sp):
    img, d = slide()
    f, lines = fit(d, sp["common"], "serif_bold", 130, 70, W - 2 * M, 2)
    y = centered(d, lines, f, 430, PALETTE["ink"])
    fs = font("sans", 46)
    centered(d, wrap(d, "what goes wrong, and what to do", fs, W - 2 * M),
             fs, y + 30, PALETTE["muted"])
    fm = font("sans_bold", 40)
    centered(d, ["leafnote"], fm, H - 240, PALETTE["accent"])
    return img


def problem_slide(sp, p, i, n):
    img, d = slide()
    d.text((M, 300), f"{i} / {n}", font=font("sans_bold", 38),
           fill=PALETTE["accent"])

    f, lines = fit(d, p["sign"], "serif_bold", 104, 56, W - 2 * M, 3)
    y = 380
    for line in lines:
        d.text((M, y), line, font=f, fill=PALETTE["ink"])
        y += f.size + 14

    y += 50
    d.rounded_rectangle([M, y, W - M, y + 230], radius=18,
                        fill=PALETTE["safe_bg"])
    d.text((M + 34, y + 30), "THE FIX", font=font("sans_bold", 34),
           fill=PALETTE["accent"])
    fy = y + 86
    ff = font("sans", 42)
    for line in wrap(d, p["fix"], ff, W - 2 * M - 68)[:3]:
        d.text((M + 34, fy), line, font=ff, fill=PALETTE["ink"])
        fy += 54
    return img


def payoff_slide(sp, card):
    img, d = slide()
    f, lines = fit(d, f"{sp['common']} care card", "serif_bold", 84, 50,
                   W - 2 * M, 2)
    y = centered(d, lines, f, 230, PALETTE["ink"])

    # Card small and angled: legible as an object, not as a free copy.
    th_h = 900
    th = card.convert("RGBA")
    th = th.resize((int(th_h * th.width / th.height), th_h), Image.LANCZOS)
    rot = th.rotate(-4, resample=Image.BICUBIC, expand=True)
    img.paste(rot, ((W - rot.width) // 2, y + 60), rot)

    fs = font("sans_bold", 46)
    centered(d, ["Printable . Instant download"], fs, H - 330,
             PALETTE["accent"])
    centered(d, ["link in bio"], font("sans", 40), H - 250, PALETTE["muted"])
    return img


def encode(slides, dest, per=3.0):
    """One clip per slide with a slow push-in, then concatenated.

    zoompan needs an explicit output size or it falls back to the input
    dimensions and the result is letterboxed.
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clips = []
        for i, img in enumerate(slides):
            png = td / f"s{i}.png"
            img.save(png)
            clip = td / f"c{i}.mp4"
            frames = int(per * FPS)
            subprocess.run(
                [FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-i",
                 str(png), "-t", f"{per}",
                 "-vf", (f"zoompan=z='min(zoom+0.00035,1.06)':d={frames}"
                         f":s={W}x{H}:fps={FPS},format=yuv420p"),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 str(clip)], check=True)
            clips.append(clip)

        lst = td / "list.txt"
        lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips),
                       encoding="utf-8")
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(lst), "-c", "copy", str(dest)], check=True)


def build(sp):
    card = Image.open(CARDS / f"{sp['slug']}.png")
    probs = sp["problems"][:3]
    slides = [hook_slide(sp)]
    slides += [problem_slide(sp, p, i, len(probs))
               for i, p in enumerate(probs, 1)]
    slides.append(payoff_slide(sp, card))
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{sp['slug']}.mp4"
    encode(slides, dest)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", metavar="SLUG")
    args = ap.parse_args()

    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    if args.only:
        species = [s for s in species if s["slug"] == args.only]
    elif args.limit:
        species = species[:args.limit]
    elif not args.all:
        print(f"{len(species)} species available. "
              f"Use --limit N, --only SLUG, or --all.")
        return 0

    for sp in species:
        if not (CARDS / f"{sp['slug']}.png").exists():
            print(f"  missing card: {sp['slug']}")
            continue
        dest = build(sp)
        mb = dest.stat().st_size / 1e6
        print(f"  {sp['slug']:32} {mb:5.1f} MB")
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
