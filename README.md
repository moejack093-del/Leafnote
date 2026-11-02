# Leafnote

Automated digital-product business. Botanical plant-care cards sold as Etsy digital downloads,
with an SEO blog as the automated traffic layer.

**Owner:** Leo (Los Angeles, US)
**Budget:** $0–50 total. Only planned spend is Etsy listing fees at $0.20/listing.
**Owner time budget:** one ~2h setup session, then ~15 min/week.

---

## Status

| Piece | State |
|---|---|
| Niche + product line chosen | Done |
| Species data + care content | **40 of 40** — `data/species.json`, validated |
| Card designs | **40** — `scripts/make_cards.py` → PNG + print PDF |
| Etsy listings | **40 active**, pushed by API, storefront fully set up |
| Pinterest | **Automated.** 51 pins live, 152 queued, 8/day via Task Scheduler |
| Weekly `REPORT.md` job | Scheduled, Mondays 09:00 |
| SEO blog | 45 pages built by `scripts/build_site.py`; **published manually** |
| Instagram / TikTok | Not started — see `STATUS.md` |

Current numbers and what needs you live in **`STATUS.md`**.

**Runtime:** Python 3.12 (already installed at
`C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe`) plus Pillow, installed.
No Node needed. Same runtime as GitHub Actions, so scripts run identically locally and in CI.

Regenerate every card after editing care data:

```bash
python scripts/make_cards.py
```

## Needs Leo

1. **Work through `SETUP.md`** — accounts, identity, bank, API keys. Nothing else can go live until this is done.
2. **Hard budget ceiling: $20 total, set by Leo.** Etsy listings cost $0.20 each to activate and
   **auto-renew every 4 months at $0.20 each**. That renewal is the only recurring cost and the
   only thing that can creep toward the ceiling.

   | When | Event | Cost | Spent | Left of $20 |
   |---|---|---|---|---|
   | Done (Oct 2026) | Activate 40 | $8.00 | $8.00 | $12.00 |
   | Feb 2027 | Auto-renew | $8.00 | $16.00 | $4.00 |
   | Jun 2027 | Auto-renew | $8.00 | $24.00 | **over** |

   So $20 funds **40 listings until roughly June 2027 if nothing ever sells** —
   one renewal, then a decision.

   **Decision point at month 4.** If there are zero sales and no meaningful traffic by then, turn
   off auto-renew and let the listings lapse. Total spend stops at $4.80. If there is traction,
   renewing is obviously worth it.

   Selling costs are separate and come out of revenue, not Leo's pocket: roughly 6.5% transaction
   plus ~3% + $0.25 payment processing. On a $4.00 card that is about $0.65, netting ~$3.35.
   **About 2 sales per 4-month cycle makes the whole thing self-funding.**

## What is automated vs. manual — honest version

**Fully automated, no ongoing work:**
- Order fulfillment. Etsy delivers the digital files itself the moment payment clears. Genuinely zero-touch.
- **Pinterest.** Standard API access came through, so `post_pins.py` publishes directly.
  A daily task posts 8/day from the queue. This was previously listed here as
  *not* automatable — that is now wrong, and it is the single biggest change
  to the project.
- Weekly `REPORT.md`. Generated from Etsy's stats API, Mondays 09:00.
- Etsy listing creation. `createDraftListing` + activate, so no manual listing forms.

Both scheduled tasks run on this PC only, and only while it is on.

**Built but still manual:**
- **SEO blog.** `scripts/build_site.py` generates 45 pages, but there is no
  cron publishing them — `.github/workflows/` is empty. An earlier version of
  this file claimed a GitHub Actions cron existed. It never did.

**NOT automatable, confirmed from the platform's own docs:**
- **TikTok.** The Content Posting API restricts *all* content from unaudited
  apps to private viewing. Lifting it needs `video.publish` approval, a
  Terms-of-Service audit, and a verified domain. Batch upload or nothing.
- **Instagram** is probably automatable for our own account, but Meta's docs
  do not confirm it without Advanced Access. Untested. See `STATUS.md`.

## Rules this project runs under

- No trademarked or copyrighted names, characters, or designs. Species names only.
- No spam, fake accounts, fake reviews, or bot engagement.
- Care information must be accurate. It is the only real moat in a category full of AI slop,
  and wrong advice kills people's plants.
- Reports tell the truth. If nothing sells, the report says nothing sold.

## Layout

```
data/       species list, care data, listing metadata
designs/    generated card artwork + Pinterest pin images
scripts/    Etsy API push, OAuth helper, report generator
site/       SEO blog (GitHub Pages)
.github/    Actions cron workflows
```

## Honest expectation

No ad budget and a saturated category means this is slow and uncertain. Realistic outcome: $0 for the
first couple of months, then plausibly tens-to-low-hundreds per month *if* a design line and the SEO
long tail land. Downside is capped at the ~$8–20 of listing fees and one Saturday. It is a cheap
lottery ticket with reasonable odds of a small win, not a salary.
