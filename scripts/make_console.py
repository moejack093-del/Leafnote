#!/usr/bin/env python3
"""Build pin_console.html -- a working checklist for posting pins by hand.

Pinterest has no organic bulk upload, so the pins go up one at a time. The
slow part of that is not clicking, it is hunting for the right title and
description for each image. This puts every field one click from the
clipboard and remembers which pins are done.

    python scripts/make_console.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "pinterest_bulk.csv"
OUT = ROOT / "pin_console.html"

TEMPLATE = """<title>Leafnote Pin Console</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  /* Working console: sticky progress bar over a single column of pin rows. */
  :root {
    --bg: #fbf9f4;
    --surface: #ffffff;
    --ink: #1f2a24;
    --muted: #6b7a70;
    --accent: #2f5d45;
    --accent-soft: #e8f0ea;
    --rule: #ddd8cc;
    --done: #8aa394;
    --display: "Newsreader", Georgia, serif;
    --body: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #141916;
      --surface: #1c231e;
      --ink: #e8e9e4;
      --muted: #9aa89f;
      --accent: #8fc2a5;
      --accent-soft: #233029;
      --rule: #2e3832;
      --done: #5c7466;
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --bg: #141916; --surface: #1c231e; --ink: #e8e9e4; --muted: #9aa89f;
    --accent: #8fc2a5; --accent-soft: #233029; --rule: #2e3832; --done: #5c7466;
    color-scheme: dark;
  }

  body { background: var(--bg); color: var(--ink); font-family: var(--body); }
  .wrap {
    max-width: 58rem; margin: 0 auto;
    padding-left: max(16px, env(safe-area-inset-left, 0px));
    padding-right: max(16px, env(safe-area-inset-right, 0px));
    padding-block: 2rem 4rem;
  }

  header { margin-bottom: 1.5rem; }
  h1 {
    font-family: var(--display); font-weight: 600; font-size: clamp(1.8rem, 5vw, 2.6rem);
    margin: 0 0 .35rem; text-wrap: balance; letter-spacing: -.01em;
  }
  .sub { color: var(--muted); margin: 0; max-width: 46ch; line-height: 1.55; }

  .bar {
    position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5;
    background: var(--bg); border-bottom: 1px solid var(--rule);
    padding-block: .8rem; margin-bottom: 1.25rem;
    display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;
  }
  .count { font-variant-numeric: tabular-nums; font-weight: 600; }
  .track { flex: 1 1 10rem; min-width: 0; height: 7px; border-radius: 99px; background: var(--rule); overflow: hidden; }
  .fill { height: 100%; width: 0; background: var(--accent); transition: width .25s ease; }
  .go {
    font: inherit; font-weight: 600; text-decoration: none;
    background: var(--accent); color: var(--bg);
    padding: .5rem .9rem; border-radius: 7px; white-space: nowrap;
  }
  .pin {
    display: grid; grid-template-columns: 92px 1fr; gap: 1rem;
    background: var(--surface); border: 1px solid var(--rule);
    border-radius: 10px; padding: 1rem; margin-bottom: .85rem;
  }
  .pin.done { opacity: .5; }
  .pin img { width: 92px; border-radius: 5px; display: block; border: 1px solid var(--rule); }
  .meta { min-width: 0; display: flex; flex-direction: column; gap: .6rem; }
  .top { display: flex; gap: .6rem; align-items: flex-start; justify-content: space-between; }
  .ttl { font-family: var(--display); font-size: 1.12rem; font-weight: 600; margin: 0; line-height: 1.3; }
  .when { color: var(--muted); font-size: .82rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .board {
    display: inline-block; background: var(--accent-soft); color: var(--accent);
    font-size: .74rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
    padding: .2rem .5rem; border-radius: 4px; align-self: flex-start;
  }
  .desc { color: var(--muted); font-size: .88rem; line-height: 1.5; margin: 0; }
  .row { display: flex; gap: .4rem; flex-wrap: wrap; }
  button.cp {
    font: inherit; font-size: .82rem; font-weight: 500; cursor: pointer;
    background: transparent; color: var(--ink);
    border: 1px solid var(--rule); border-radius: 6px; padding: .3rem .6rem;
  }
  button.cp:hover { border-color: var(--accent); color: var(--accent); }
  button.cp.ok { background: var(--accent); color: var(--bg); border-color: var(--accent); }
  label.chk { display: flex; gap: .4rem; align-items: center; font-size: .82rem; color: var(--muted); cursor: pointer; }
  :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
  @media (max-width: 460px) {
    .pin { grid-template-columns: 64px 1fr; }
    .pin img { width: 64px; }
  }
</style>

<div class="wrap">
  <header>
    <h1>Pin console</h1>
    <p class="sub">Pinterest has no organic bulk upload, so these go up one at a
      time. Everything you need to paste is one click away. Aim for two or three
      a day rather than all of them at once.</p>
  </header>

  <div class="bar">
    <span class="count"><span id="n">0</span> / __TOTAL__ posted</span>
    <span class="track"><span class="fill" id="fill"></span></span>
    <a class="go" href="https://pinterest.com/pin-creation-tool/" target="_blank" rel="noopener">Open Pinterest</a>
  </div>

  <div id="list"></div>
</div>

<script>
const PINS = __DATA__;
const KEY = "leafnote_pins_done";

function loadDone() {
  try { return new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); }
  catch (e) { return new Set(); }
}
function saveDone(s) {
  try { localStorage.setItem(KEY, JSON.stringify([...s])); } catch (e) {}
}

const done = loadDone();

function copy(text, btn) {
  const mark = () => {
    const old = btn.textContent;
    btn.textContent = "Copied";
    btn.classList.add("ok");
    setTimeout(() => { btn.textContent = old; btn.classList.remove("ok"); }, 1100);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(mark).catch(() => fallback(text, mark));
  } else { fallback(text, mark); }
}
function fallback(text, mark) {
  const ta = document.createElement("textarea");
  ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.select();
  try { document.execCommand("copy"); mark(); } catch (e) {}
  document.body.removeChild(ta);
}

function tally() {
  document.getElementById("n").textContent = done.size;
  document.getElementById("fill").style.width =
    (PINS.length ? (done.size / PINS.length) * 100 : 0) + "%";
}

const list = document.getElementById("list");
PINS.forEach((p, i) => {
  const el = document.createElement("div");
  el.className = "pin" + (done.has(p.u) ? " done" : "");
  const img = document.createElement("img");
  img.src = p.u; img.alt = p.t; img.loading = "lazy";
  const meta = document.createElement("div");
  meta.className = "meta";

  const top = document.createElement("div");
  top.className = "top";
  const h = document.createElement("p");
  h.className = "ttl"; h.textContent = p.t;
  const when = document.createElement("span");
  when.className = "when"; when.textContent = p.w.split(" ")[0];
  top.append(h, when);

  const board = document.createElement("span");
  board.className = "board"; board.textContent = p.b;

  const desc = document.createElement("p");
  desc.className = "desc"; desc.textContent = p.d;

  const row = document.createElement("div");
  row.className = "row";
  [["Image URL", p.u], ["Title", p.t], ["Description", p.d],
   ["Link", p.l], ["Board", p.b]].forEach(([label, val]) => {
    const b = document.createElement("button");
    b.className = "cp"; b.type = "button"; b.textContent = label;
    b.addEventListener("click", () => copy(val, b));
    row.appendChild(b);
  });

  const lab = document.createElement("label");
  lab.className = "chk";
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.id = "p" + i; cb.checked = done.has(p.u);
  cb.addEventListener("change", () => {
    if (cb.checked) { done.add(p.u); el.classList.add("done"); }
    else { done.delete(p.u); el.classList.remove("done"); }
    saveDone(done); tally();
  });
  lab.append(cb, document.createTextNode("Posted"));

  meta.append(top, board, desc, row, lab);
  el.append(img, meta);
  list.appendChild(el);
});
tally();
</script>
"""


def main() -> int:
    if not CSV_PATH.exists():
        sys.exit("No pinterest_bulk.csv. Run: python scripts/make_bulk_csv.py")
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    data = [{"t": r["Title"], "u": r["Media URL"], "b": r["Pinterest board"],
             "d": r["Description"], "l": r["Link"], "w": r["Publish date"]}
            for r in rows]
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__TOTAL__", str(len(data))))
    OUT.write_text(html, encoding="utf-8")
    print(f"{len(data)} pins -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
