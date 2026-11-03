#!/usr/bin/env python3
"""Generate the Leafnote care-guide site from species.json.

    python scripts/build_site.py            # build into site_build/
    python scripts/build_site.py --deploy   # build and push to the live repo

Design notes, since the SEO here is the whole point:

ONE STRONG PAGE PER PLANT, not many thin ones. It is tempting to generate a
page per question ("why is my monstera not splitting") because it multiplies
the URL count, but near-duplicate pages generated from one template are
exactly what Google demotes as thin content. A single substantial page can
rank for all of that plant's long-tail queries at once, and it survives
scrutiny.

Each page carries FAQPage structured data built from the troubleshooting
entries, which is genuine Q&A rather than marked-up filler, and internal
links to related plants so the site is crawlable as a graph rather than a
flat list.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
LISTINGS = ROOT / "data" / "listings.json"
PRIVACY = ROOT / "docs" / "privacy.html"
OUT = ROOT / "site_build"

SITE = "https://leafnotestudio.github.io"
GSC_VERIFY_FILE = "googleed03b0ca10e3d81e.html"
SHOP = "https://www.etsy.com/shop/LeafnoteStudio"
REPO = "https://github.com/leafnotestudio/leafnotestudio.github.io.git"
TODAY = date.today().isoformat()


def esc(s):
    return html.escape(str(s), quote=True)


STYLE = """
:root {
  color-scheme: light dark;
  --bg: #fbf9f4; --surface: #ffffff; --ink: #1f2a24; --muted: #6b7a70;
  --accent: #2f5d45; --accent-soft: #e8f0ea; --rule: #ddd8cc;
  --warn-bg: #f7ebe7; --warn-ink: #9a3b28;
  --safe-bg: #eaf3ed; --safe-ink: #2f5d45;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #141916; --surface: #1c231e; --ink: #e8e9e4; --muted: #9aa89f;
    --accent: #8fc2a5; --accent-soft: #233029; --rule: #2e3832;
    --warn-bg: #33211d; --warn-ink: #e0a090;
    --safe-bg: #1e2b23; --safe-ink: #8fc2a5;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.68 "Segoe UI", system-ui, -apple-system, sans-serif;
}
.wrap { max-width: 44rem; margin: 0 auto; padding: 0 1.1rem; }
header.site {
  border-bottom: 1px solid var(--rule); padding: 1.1rem 0; margin-bottom: 2.4rem;
}
header.site .wrap { display: flex; gap: 1.2rem; align-items: baseline; flex-wrap: wrap; }
.brand {
  font-family: Georgia, serif; font-weight: 700; font-size: 1.3rem;
  color: var(--ink); text-decoration: none; letter-spacing: -.01em;
}
header.site nav { display: flex; gap: 1rem; font-size: .93rem; }
header.site nav a { color: var(--muted); text-decoration: none; }
header.site nav a:hover { color: var(--accent); }
h1 {
  font-family: Georgia, serif; font-size: clamp(2rem, 5.5vw, 2.7rem);
  line-height: 1.15; margin: 0 0 .3rem; letter-spacing: -.015em;
  text-wrap: balance;
}
.botanical { font-style: italic; color: var(--muted); margin: 0 0 .4rem; font-size: 1.08rem; }
.chips { display: flex; gap: .4rem; flex-wrap: wrap; margin: .9rem 0 1.8rem; }
.chip {
  font-size: .78rem; font-weight: 600; letter-spacing: .04em;
  text-transform: uppercase; padding: .25rem .6rem; border-radius: 4px;
  background: var(--accent-soft); color: var(--accent); text-decoration: none;
}
.chip.warn { background: var(--warn-bg); color: var(--warn-ink); }
.chip.safe { background: var(--safe-bg); color: var(--safe-ink); }
h2 {
  font-family: Georgia, serif; font-size: 1.42rem; margin: 2.4rem 0 .7rem;
  padding-top: 1.6rem; border-top: 1px solid var(--rule); letter-spacing: -.01em;
}
h3 { font-size: 1.07rem; margin: 1.5rem 0 .3rem; }
p { margin: 0 0 1rem; }
a { color: var(--accent); }
dl.facts {
  display: grid; grid-template-columns: 7.5rem 1fr; gap: .55rem 1rem;
  margin: 1.4rem 0; padding: 1.2rem; background: var(--surface);
  border: 1px solid var(--rule); border-radius: 9px;
}
dl.facts dt {
  font-size: .76rem; font-weight: 700; letter-spacing: .05em;
  text-transform: uppercase; color: var(--accent); padding-top: .18rem;
}
dl.facts dd { margin: 0; }
.callout {
  padding: 1rem 1.2rem; border-radius: 9px; margin: 1.6rem 0;
  background: var(--warn-bg); color: var(--warn-ink);
}
.callout.safe { background: var(--safe-bg); color: var(--safe-ink); }
.callout strong { display: block; margin-bottom: .25rem;
  text-transform: uppercase; letter-spacing: .05em; font-size: .8rem; }
.callout p { margin: 0; }
.problem { margin-bottom: 1.4rem; }
.problem h3 { margin-top: 0; }
.problem .cause { color: var(--muted); font-size: .93rem; margin-bottom: .25rem; }
.cta {
  background: var(--surface); border: 1px solid var(--rule); border-radius: 9px;
  padding: 1.3rem 1.4rem; margin: 2.4rem 0;
}
.cta h2 { border: 0; padding: 0; margin: 0 0 .4rem; font-size: 1.2rem; }
.cta p { margin-bottom: .9rem; color: var(--muted); font-size: .96rem; }
.btn {
  display: inline-block; background: var(--accent); color: var(--bg);
  text-decoration: none; font-weight: 600; padding: .6rem 1.1rem;
  border-radius: 7px;
}
ul.plants { list-style: none; padding: 0; display: grid;
  grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); gap: .55rem; }
ul.plants a {
  display: block; padding: .7rem .9rem; background: var(--surface);
  border: 1px solid var(--rule); border-radius: 7px; text-decoration: none;
  color: var(--ink);
}
ul.plants a:hover { border-color: var(--accent); }
ul.plants .sci { display: block; font-style: italic; color: var(--muted);
  font-size: .85rem; }
footer.site {
  margin-top: 4rem; border-top: 1px solid var(--rule); padding: 1.6rem 0 3rem;
  color: var(--muted); font-size: .9rem;
}
footer.site a { color: var(--muted); }
@media (max-width: 460px) {
  dl.facts { grid-template-columns: 1fr; gap: .15rem; padding: 1rem; }
  dl.facts dd { margin-bottom: .6rem; }
}
"""


def page(title, desc, canonical, body, extra_head=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{esc(canonical)}">
<link rel="stylesheet" href="{SITE}/style.css">
{extra_head}
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="{SITE}/">leafnote</a>
  <nav>
    <a href="{SITE}/pet-safe-houseplants/">Pet-safe plants</a>
    <a href="{SITE}/easy-houseplants/">Easy plants</a>
    <a href="{SITE}/difficult-houseplants/">Difficult plants</a>
  </nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
  <p>Care guides written for the houseplants people actually own.
     Printable versions of every card are in the
     <a href="{SHOP}">Leafnote shop</a>.</p>
  <p><a href="{SITE}/">All plants</a> &middot;
     <a href="{SITE}/privacy.html">Privacy</a></p>
</div></footer>
</body>
</html>
"""


OPENERS = {
    "easy": [
        "{name} ({bot}) is hard to kill, which is how most of them die: it "
        "tolerates neglect well enough that people stop looking at it.",
        "{name} ({bot}) asks for very little. The trouble is that very little "
        "gets read as nothing, and then it gets watered on a schedule it never "
        "wanted.",
        "If you have killed houseplants before, {name} ({bot}) is a reasonable "
        "place to start again. It recovers from most mistakes.",
        "{name} ({bot}) is forgiving about almost everything except one thing, "
        "and knowing which thing is most of the job.",
    ],
    "moderate": [
        "{name} ({bot}) is not difficult, but it is particular. Get its "
        "conditions roughly right and it mostly looks after itself.",
        "{name} ({bot}) sits between easy and demanding: it notices when "
        "something is wrong, and it shows you reasonably quickly.",
        "{name} ({bot}) rewards a bit of attention. It is not fussy enough to "
        "be frustrating, but it will not thrive on autopilot either.",
    ],
    "tricky": [
        "{name} ({bot}) has a reputation for being difficult and it is earned. "
        "It does not tolerate guesswork.",
        "{name} ({bot}) is the kind of plant that looks fine for three weeks "
        "and then all at once does not. Problems start well before they show.",
        "{name} ({bot}) is demanding, and worth it to the people who find it "
        "worth it. It will not accept a watering schedule.",
    ],
}


def intro(sp):
    """A first paragraph built from this plant's own specifics.

    An earlier version keyed only off difficulty, which gave all 25 easy
    plants an identical opening sentence -- the clearest possible signal of
    generated content. This varies the opener and then grounds it in facts
    unique to the plant: its actual light need and its actual first failure
    mode.
    """
    name, bot = sp["common"], sp["botanical"]
    diff = sp.get("difficulty", "moderate")
    toxic = sp["toxic_pets"] == "toxic"

    pool = OPENERS.get(diff, OPENERS["moderate"])
    # Stable per-slug choice, so a rebuild does not reshuffle every page.
    lead = pool[sum(ord(c) for c in sp["slug"]) % len(pool)].format(
        name=name, bot=bot)

    problems = sp.get("problems") or []
    if problems:
        p = problems[0]
        sign = p["sign"][0].lower() + p["sign"][1:]
        cause = p["cause"].rstrip(".")
        cause = cause[0].lower() + cause[1:]
        lead += f" The first thing that usually goes wrong is {sign} — {cause}."

    light = sp["light_short"].lower()
    lead += f" It wants {light} light"
    hum = sp.get("humidity", "")
    if "60" in hum or "70" in hum:
        lead += ", and genuinely high humidity rather than whatever your "\
                "living room happens to have"
    lead += "."

    tail = (" It is toxic to cats and dogs, which is worth knowing before you "
            "bring one home." if toxic else
            " It is not toxic to cats or dogs.")
    return lead + tail


def faq_schema(sp, url):
    qs = []
    for p in sp.get("problems", []):
        qs.append({
            "@type": "Question",
            "name": f"{sp['common']}: {p['sign'].lower()}",
            "acceptedAnswer": {"@type": "Answer",
                               "text": f"{p['cause']}. {p['fix']}"},
        })
    qs.append({
        "@type": "Question",
        "name": f"Is {sp['common']} toxic to cats and dogs?",
        "acceptedAnswer": {"@type": "Answer", "text": sp["toxic_note"]},
    })
    qs.append({
        "@type": "Question",
        "name": f"How often should I water a {sp['common']}?",
        "acceptedAnswer": {"@type": "Answer", "text": sp["water"]},
    })
    data = {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": qs}
    return ('<script type="application/ld+json">'
            + json.dumps(data) + "</script>")


def species_page(sp, listing, related):
    slug = sp["slug"]
    url = f"{SITE}/plants/{slug}/"
    toxic = sp["toxic_pets"] == "toxic"
    name = sp["common"]

    title = (f"{name} Care Guide: Light, Water and Pet Safety")[:62]
    desc = (f"How to keep a {name} ({sp['botanical']}) alive: "
            f"{sp['light_short'].lower()}, {sp['water_short'].lower()}, "
            + ("toxic to cats and dogs" if toxic else "safe for cats and dogs")
            + ". Plus what to do when the leaves go wrong.")[:158]

    chips = [f'<span class="chip">{esc(sp["difficulty"].title())}</span>']
    chips.append(f'<span class="chip {"warn" if toxic else "safe"}">'
                 f'{"Toxic to pets" if toxic else "Pet safe"}</span>')

    problems = ""
    for p in sp.get("problems", []):
        problems += f"""
<div class="problem">
  <h3>{esc(p['sign'])}</h3>
  <p class="cause">Usually: {esc(p['cause'])}</p>
  <p>{esc(p['fix'])}</p>
</div>"""

    rel = "".join(
        f'<li><a href="{SITE}/plants/{r["slug"]}/">{esc(r["common"])}'
        f'<span class="sci">{esc(r["botanical"])}</span></a></li>'
        for r in related)

    shop_url = (listing or {}).get("url") or SHOP

    body = f"""
<h1>{esc(name)} Care Guide</h1>
<p class="botanical">{esc(sp['botanical'])}</p>
<div class="chips">{''.join(chips)}</div>

<p>{esc(intro(sp))}</p>

<dl class="facts">
  <dt>Light</dt><dd>{esc(sp['light'])}</dd>
  <dt>Water</dt><dd>{esc(sp['water'])}</dd>
  <dt>Humidity</dt><dd>{esc(sp['humidity'])}</dd>
  <dt>Soil</dt><dd>{esc(sp['soil'])}</dd>
  <dt>Temperature</dt><dd>{esc(sp['temp_f'])} &deg;F</dd>
  <dt>Feeding</dt><dd>{esc(sp['feeding'])}</dd>
</dl>

<div class="callout {'warn' if toxic else 'safe'}">
  <strong>{'Toxic to cats and dogs' if toxic else 'Safe for cats and dogs'}</strong>
  <p>{esc(sp['toxic_note'])}</p>
</div>

<h2>Why &ldquo;water every week&rdquo; is the wrong advice</h2>
<p>How fast a {esc(name)} dries out depends on its pot size, how much light it
gets, the airflow in the room and the time of year. The same plant can want
water twice a week in July and once a month in January. A fixed schedule
ignores all of that, which is why it is the most common way people drown a
houseplant.</p>
<p>What to check instead: {esc(sp['water'][0].lower() + sp['water'][1:])}</p>

<h2>When something looks wrong</h2>
{problems}

<h2>Worth knowing</h2>
<p>{esc(sp['note'])}</p>

<div class="cta">
  <h2>Printable {esc(name)} care card</h2>
  <p>Everything on this page as a 4&times;6 card you can print and keep next to
     the pot. Instant download, PDF and PNG.</p>
  <a class="btn" href="{esc(shop_url)}">See the card</a>
</div>

<h2>Other plants</h2>
<ul class="plants">{rel}</ul>
"""
    return page(title, desc, url, body, faq_schema(sp, url))


def list_page(slug, h1, title, desc, lead, items, extra=""):
    url = f"{SITE}/{slug}/"
    li = "".join(
        f'<li><a href="{SITE}/plants/{s["slug"]}/">{esc(s["common"])}'
        f'<span class="sci">{esc(s["botanical"])}</span></a></li>'
        for s in items)
    body = f"""
<h1>{esc(h1)}</h1>
<p>{lead}</p>
{extra}
<h2>The list</h2>
<ul class="plants">{li}</ul>
<div class="cta">
  <h2>Printable care cards</h2>
  <p>Every plant here has a 4&times;6 card with its light, water, soil and
     troubleshooting, plus its pet-safety status.</p>
  <a class="btn" href="{SHOP}">Browse the shop</a>
</div>
"""
    return url, page(title, desc, url, body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    species = json.loads(SPECIES.read_text(encoding="utf-8"))["species"]
    listings = json.loads(LISTINGS.read_text(encoding="utf-8"))
    by_slug = {s["slug"]: s for s in species}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "style.css").write_text(STYLE.strip() + "\n", encoding="utf-8")

    urls = [f"{SITE}/"]

    # --- species pages ---------------------------------------------------
    for i, sp in enumerate(species):
        # Related = neighbours in the list, wrapping. Cheap, but it makes the
        # site a connected graph instead of 40 orphan pages hanging off index.
        related = [species[(i + k) % len(species)] for k in (1, 2, 3, 4)]
        d = OUT / "plants" / sp["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            species_page(sp, listings.get(sp["slug"]), related),
            encoding="utf-8")
        urls.append(f"{SITE}/plants/{sp['slug']}/")

    # --- category pages --------------------------------------------------
    safe = [s for s in species if s["toxic_pets"] == "non-toxic"]
    easy = [s for s in species if s["difficulty"] == "easy"]
    hard = [s for s in species if s["difficulty"] in ("tricky", "moderate")]

    cats = [
        list_page(
            "pet-safe-houseplants",
            f"{len(safe)} houseplants that are safe for cats and dogs",
            "Pet-Safe Houseplants: The Full List for Cats and Dogs",
            f"{len(safe)} houseplants that are not toxic to cats or dogs, with "
            f"care notes for each. Checked against standard toxicity listings.",
            "Every plant on this list is non-toxic to cats and dogs. Worth "
            "saying plainly: most &ldquo;toxic&rdquo; houseplants cause mouth "
            "irritation and an upset stomach rather than anything worse. But if "
            "you have an animal that chews, or you would simply rather not think "
            "about it, these are the ones to start with.",
            safe,
            "<h2>A note on what toxic actually means</h2><p>The majority of "
            "common houseplant toxicity comes from insoluble calcium oxalates. "
            "Chewing a leaf causes immediate burning, drooling and sometimes "
            "vomiting, which in practice stops most animals from eating more. "
            "It is genuinely unpleasant and occasionally serious, but it is not "
            "usually life-threatening. A few plants are worse than that, and "
            "those are flagged individually. If an animal has actually eaten "
            "part of a plant, call a vet rather than relying on any web "
            "page.</p>"),
        list_page(
            "easy-houseplants",
            f"{len(easy)} houseplants that are genuinely hard to kill",
            "Easy Houseplants That Survive Neglect",
            f"{len(easy)} houseplants that tolerate low light, irregular "
            f"watering and general neglect, with honest care notes for each.",
            "These tolerate low light, forgotten waterings and the general "
            "chaos of a normal house. One thing unites nearly all of them: the "
            "way people kill them is too much water, not too little. If you are "
            "coming back from a few dead plants, start here.",
            easy),
        list_page(
            "difficult-houseplants",
            f"{len(hard)} houseplants that will test your patience",
            "Difficult Houseplants and What They Actually Need",
            f"{len(hard)} houseplants that punish guesswork, and the specific "
            f"conditions each one needs to do well indoors.",
            "These are the ones that crisp at the edges, drop leaves without "
            "warning, or quietly decline for weeks before anything looks wrong. "
            "They are not impossible, but humidity and water quality matter far "
            "more for them than for the easy plants, and they do not forgive a "
            "guessed watering schedule.",
            hard),
    ]
    for url, html_doc in cats:
        d = OUT / url.replace(SITE + "/", "").rstrip("/")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html_doc, encoding="utf-8")
        urls.append(url)

    # --- index -----------------------------------------------------------
    all_li = "".join(
        f'<li><a href="{SITE}/plants/{s["slug"]}/">{esc(s["common"])}'
        f'<span class="sci">{esc(s["botanical"])}</span></a></li>'
        for s in sorted(species, key=lambda x: x["common"]))
    index_body = f"""
<h1>Houseplant care guides</h1>
<p>Care notes for {len(species)} houseplants, written for people who want to
know what to check rather than what day to water. Every guide says plainly
whether the plant is toxic to cats and dogs, and what to do when the leaves
start going wrong.</p>

<div class="chips">
  <a class="chip safe" href="{SITE}/pet-safe-houseplants/">{len(safe)} pet-safe plants</a>
  <a class="chip" href="{SITE}/easy-houseplants/">{len(easy)} easy plants</a>
  <a class="chip" href="{SITE}/difficult-houseplants/">{len(hard)} difficult plants</a>
</div>

<h2>Every plant</h2>
<ul class="plants">{all_li}</ul>

<div class="cta">
  <h2>Printable care cards</h2>
  <p>Each guide is also a 4&times;6 printable card &mdash; light, water, soil,
     feeding, pet safety and troubleshooting on one page you can keep beside
     the pot.</p>
  <a class="btn" href="{SHOP}">Browse the shop</a>
</div>
"""
    (OUT / "index.html").write_text(page(
        "Leafnote — Houseplant Care Guides",
        f"Honest care guides for {len(species)} houseplants: light, water, "
        f"soil, pet safety and troubleshooting. No vague watering schedules.",
        f"{SITE}/", index_body), encoding="utf-8")

    # --- privacy, sitemap, robots ---------------------------------------
    if PRIVACY.exists():
        shutil.copy2(PRIVACY, OUT / "privacy.html")
        urls.append(f"{SITE}/privacy.html")

    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n"
                         for u in urls)
               + "</urlset>\n")
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n",
        encoding="utf-8")

    # Google Search Console ownership token.
    #
    # This has to be emitted by the build rather than committed once to the
    # site repo, because deploy() deletes everything in that repo before
    # copying this directory over it. A file added by hand there would
    # survive exactly until the next deploy and then silently un-verify the
    # site -- Search Console drops you without warning when the token goes.
    (OUT / GSC_VERIFY_FILE).write_text(
        f"google-site-verification: {GSC_VERIFY_FILE}\n", encoding="utf-8")

    print(f"pages : {len(urls)}")
    print(f"output: {OUT}")

    if args.deploy:
        deploy()
    return 0


def deploy():
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["git", "clone", "--depth", "1", REPO, str(tmp)],
                   check=True, capture_output=True)
    for item in tmp.iterdir():
        if item.name == ".git":
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    for item in OUT.iterdir():
        dest = tmp / item.name
        shutil.copytree(item, dest) if item.is_dir() else shutil.copy2(item, dest)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=tmp,
                            capture_output=True, text=True).stdout.strip()
    if not status:
        print("deploy: no changes")
        return
    subprocess.run(["git", "-c", "user.name=Leo",
                    "-c", "user.email=moejack093@gmail.com",
                    "commit", "-q", "-m",
                    f"Rebuild care guides ({TODAY})"], cwd=tmp, check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD"], cwd=tmp, check=True)
    print("deploy: pushed")


if __name__ == "__main__":
    sys.exit(main())
