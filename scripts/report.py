#!/usr/bin/env python3
"""Write REPORT.md: what sold, what got looked at, and what to change.

    python scripts/report.py

Designed to be honest rather than encouraging. A report that dresses up zero
sales as "building momentum" is worse than useless, because the whole point is
to decide at month 4 whether to keep paying renewal fees.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_client import Etsy  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ROOT / "data" / "species.json"
STATE = ROOT / "data" / "listings.json"
OUT = ROOT / "REPORT.md"
HISTORY = ROOT / "data" / "report_history.json"

LISTING_FEE = 0.20


def money(x):
    return f"${x:,.2f}"


def main() -> int:
    e = Etsy()
    sid = e.shop_id()
    shop = e.get(f"/shops/{sid}").json()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    species = {s["slug"]: s for s in
               json.loads(SPECIES.read_text(encoding="utf-8"))["species"]}

    rows = []
    for slug, rec in state.items():
        d = e.get(f"/listings/{rec['listing_id']}").json()
        if d.get("state") != "active":
            continue
        rows.append({
            "slug": slug,
            "common": species.get(slug, {}).get("common", slug),
            "views": d.get("views") or 0,
            "faves": d.get("num_favorers") or 0,
            "id": rec["listing_id"],
            "safe": species.get(slug, {}).get("toxic_pets") == "non-toxic",
        })

    total_views = sum(r["views"] for r in rows)
    total_faves = sum(r["faves"] for r in rows)

    # Sales
    receipts, sales_total, items_sold = [], 0.0, Counter()
    r = e.get(f"/shops/{sid}/receipts", params={"limit": 100})
    if r.status_code == 200:
        receipts = r.json().get("results", [])
        for rc in receipts:
            tot = rc.get("grandtotal") or {}
            if tot.get("amount") is not None:
                sales_total += tot["amount"] / (tot.get("divisor") or 100)
            for t in rc.get("transactions", []) or []:
                items_sold[t.get("title", "?")[:50]] += t.get("quantity", 1)

    prev = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    last = prev[-1] if prev else None
    dv = total_views - last["views"] if last else None
    ds = len(receipts) - last["orders"] if last else None

    spent = LISTING_FEE * len(rows)
    rows.sort(key=lambda x: (-x["views"], -x["faves"]))
    now = datetime.now(timezone.utc)

    L = []
    L.append("# Leafnote weekly report")
    L.append("")
    L.append(f"Generated {now:%Y-%m-%d %H:%M} UTC")
    L.append("")
    L.append("## Numbers")
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append(f"| Active listings | {len(rows)} |")
    L.append(f"| Total views | {total_views}"
             + (f" ({dv:+d} since last report)" if dv is not None else "") + " |")
    L.append(f"| Favourites | {total_faves} |")
    L.append(f"| Orders | {len(receipts)}"
             + (f" ({ds:+d})" if ds is not None else "") + " |")
    L.append(f"| Revenue | {money(sales_total)} |")
    L.append(f"| Spent on listing fees | {money(spent)} |")
    L.append(f"| Net | {money(sales_total - spent)} |")
    L.append("")

    # -- the honest verdict -------------------------------------------
    L.append("## What this means")
    L.append("")
    if len(receipts) == 0 and total_views == 0:
        L.append("**No views and no sales.** Nothing is reaching anyone yet.")
        L.append("")
        L.append("If the shop has been live less than about three weeks, this is "
                 "normal and expected -- Etsy indexes new listings slowly and "
                 "ranks new shops poorly until they have sales history.")
        L.append("")
        L.append("If it has been live longer than three weeks, the titles and "
                 "tags are not matching what people actually search. That is a "
                 "fixable problem, but it needs changing rather than waiting.")
    elif len(receipts) == 0:
        L.append(f"**{total_views} views, no sales.** People are finding the "
                 "listings and not buying.")
        L.append("")
        L.append("This is a different problem from no views, and it has different "
                 "fixes: price, the preview image, or the listing description. "
                 "Below roughly 200 views total it is too early to read anything "
                 "into it -- conversion rates on a new shop with no reviews are "
                 "low by default.")
    else:
        L.append(f"**{len(receipts)} orders, {money(sales_total)}.** "
                 "Something is working.")
        L.append("")
        breakeven = spent / max(sales_total, 0.01)
        if sales_total >= spent:
            L.append("Revenue has covered the listing fees. The shop is now "
                     "self-funding.")
        else:
            L.append(f"Still {money(spent - sales_total)} behind on fees. "
                     f"About {breakeven:.1f}x current revenue covers it.")
    L.append("")

    if items_sold:
        L.append("### What sold")
        L.append("")
        for title, n in items_sold.most_common(10):
            L.append(f"- {n} x {title}")
        L.append("")

    # -- per-listing ---------------------------------------------------
    L.append("## Listings by views")
    L.append("")
    L.append("| Plant | Views | Faves | Pet-safe |")
    L.append("|---|---:|---:|:---:|")
    for r_ in rows[:15]:
        L.append(f"| {r_['common']} | {r_['views']} | {r_['faves']} | "
                 f"{'yes' if r_['safe'] else ''} |")
    L.append("")

    dead = [r_ for r_ in rows if r_["views"] == 0]
    if dead and total_views > 0:
        L.append(f"**{len(dead)} listings have zero views.** "
                 "Their titles and tags are the first thing to rewrite, using "
                 "the wording from the listings that are getting traffic.")
        L.append("")

    # -- recommendation ------------------------------------------------
    L.append("## Recommended next action")
    L.append("")
    if total_views == 0:
        L.append("- Wait, if the shop is under three weeks old. Otherwise "
                 "rewrite titles around more specific searches.")
        L.append("- Get the Pinterest batch scheduled. Etsy search alone is a "
                 "slow start for a shop with no sales history.")
    elif len(receipts) == 0:
        top = rows[0]["common"] if rows else "the top listing"
        L.append(f"- {top} is getting the most attention. Look at why, and "
                 "apply the same title and tag pattern to the dead listings.")
        L.append("- Leave the price alone until there are 200+ views. Changing "
                 "two variables at once means learning nothing from either.")
    else:
        L.append("- Add more species in whatever category is selling.")
        L.append("- Ask buyers for reviews. Reviews are the single biggest "
                 "ranking factor working against a new shop.")
    L.append("")
    L.append("---")
    L.append("")
    L.append(f"Shop: {shop.get('url')}")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")

    prev.append({"date": now.isoformat(), "views": total_views,
                 "faves": total_faves, "orders": len(receipts),
                 "revenue": round(sales_total, 2)})
    HISTORY.write_text(json.dumps(prev, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"  views {total_views} | faves {total_faves} | "
          f"orders {len(receipts)} | revenue {money(sales_total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
