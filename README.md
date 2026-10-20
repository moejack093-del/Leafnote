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
| Project scaffolding | Done |
| Setup checklist for Leo | Done — see `SETUP.md` (incl. Metricool) |
| Species data + care content | **24 of 40 done** — `data/species.json`, validated |
| Card designs | **Done for all 24** — `scripts/make_cards.py` → PNG + print PDF |
| Etsy API push script | Not started |
| SEO blog + GitHub Actions cron | Not started |
| Pinterest batch generator | Not started |
| Weekly `REPORT.md` job | Not started |

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
   | Now | Activate 24 | $4.80 | $4.80 | $15.20 |
   | Month 4 | Auto-renew | $4.80 | $9.60 | $10.40 |
   | Month 8 | Auto-renew | $4.80 | $14.40 | $5.60 |
   | Month 12 | Auto-renew | $4.80 | $19.20 | $0.80 |

   So $20 funds roughly **16 months of 24 listings if nothing ever sells**.

   **Decision point at month 4.** If there are zero sales and no meaningful traffic by then, turn
   off auto-renew and let the listings lapse. Total spend stops at $4.80. If there is traction,
   renewing is obviously worth it.

   Selling costs are separate and come out of revenue, not Leo's pocket: roughly 6.5% transaction
   plus ~3% + $0.25 payment processing. On a $4.00 card that is about $0.65, netting ~$3.35.
   **About 2 sales per 4-month cycle makes the whole thing self-funding.**

## What is automated vs. manual — honest version

**Fully automated, no ongoing work:**
- Order fulfillment. Etsy delivers the digital files itself the moment payment clears. Genuinely zero-touch.
- SEO blog. GitHub Actions cron generates and publishes species pages on a schedule. Free tier, no approval gate.
- Weekly `REPORT.md`. Generated from Etsy's stats API.

**Automated once set up, by API:**
- Etsy listing creation. `createDraftListing` + activate, so no manual listing forms.

**NOT automatable — these are your 15 min/week:**
- **Pinterest.** Pinterest's API puts approved apps in Trial tier, where pins are visible only to you.
  Standard access needs a separate review with a demo video of the OAuth flow, and it is not guaranteed.
  So: I generate a batch of pin images + titles + descriptions, you upload them.
- **TikTok.** Direct posting needs audited Content Posting API access. Same deal — batch upload.

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
