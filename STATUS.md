# Where things stand

Last updated 20 October 2026.

## Live and running

| | |
|---|---|
| Etsy shop | [LeafnoteStudio](https://www.etsy.com/shop/LeafnoteStudio) |
| Listings | **40 active**, sorted into Pet-Safe (18) / Easy Care (14) / Statement (8) |
| Storefront | Icon, banner, about, announcement, policies, post-purchase message |
| Spend | **$8.00 of the $20 ceiling.** Nothing due until mid-February 2027. |
| Weekly report | Windows Task Scheduler, Mondays 9am, writes `REPORT.md` |
| Pin assets | 43 pins built, hosted, all URLs verified |
| Sites | moejack093-del.github.io/Leafnote (pin hosting) + leafnotestudio.github.io (company site) |

## Waiting on Pinterest

App **Leafnote Pin Manager**, App ID `1627370`, submitted 20 Oct.
Trial approval takes 1-3 business days; Pinterest emails you.

**When the approval email arrives:**

1. Copy the App secret from developers.pinterest.com into `.env` as
   `PINTEREST_APP_SECRET`
2. Run `python scripts/pinterest_client.py --auth`
3. Run `python scripts/post_pins.py --check` - posts ONE pin
4. Open that pin's URL in a private browser window

If you can see it, the app has Standard access and `--live` posts the other 42.
If you cannot, it is on Trial, where pins are visible only to you, and the
Standard upgrade needs a 45-second screen recording of step 2. See
`PINTEREST_ACCESS.md`.

## Not started

- SEO blog (slowest channel, 2-4 months to rank, needs nothing from Leo)
- Species 41+ if any listing shows traction

## The honest read

Zero views on day one is normal. Etsy takes 2-3 weeks to index a new shop and
ranks it poorly until it has sales history. **Watch views, not sales** - views
appearing means the titles and tags work; views without sales is a different
problem with a different fix. Do not change anything before 200 views.

External traffic is what breaks the cold start, which makes the pins the one
variable that is built but not running.
