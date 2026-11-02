# Where things stand

Last updated 1 November 2026.

## Live and running

| | |
|---|---|
| Etsy shop | [LeafnoteStudio](https://www.etsy.com/shop/LeafnoteStudio) |
| Listings | **40 active**, sorted into Pet-Safe (18) / Easy Care (14) / Statement (8) |
| Storefront | Icon, banner, about, announcement, policies, post-purchase message |
| Spend | **$8.00 of the $20 ceiling.** Nothing due until mid-February 2027. |
| Pinterest | **51 pins live**, 152 more queued and posting automatically |
| Pin assets | 203 pins built and hosted, all URLs verified resolving |
| Sites | moejack093-del.github.io/Leafnote (pin hosting) + leafnotestudio.github.io (blog) |

## Scheduled jobs

Both registered in Windows Task Scheduler on 1 November 2026.

| Task | When | Does |
|---|---|---|
| `Leafnote Pins` | Daily 10:00 | Posts 8 pins, logs to `data/pin_drip.log` |
| `Leafnote Report` | Mondays 09:00 | Rewrites `REPORT.md`, logs to `data/report.log` |

Correction to the previous version of this file: it claimed the weekly report
was already scheduled. It was not — no task existed. Both are registered now
and verified `Ready` with a next run time.

**These only run while this PC is on and signed in.** A missed day costs
nothing: `post_pins.py` tracks what it has already published in
`data/pins_posted.json`, so it never duplicates and simply resumes.

At 8/day the queue of 152 finishes around **20 November 2026**.

## The numbers, as of 1 November

| | |
|---|---|
| Views | 86 (first external traffic, all from Pinterest) |
| Favourites | 0 |
| Orders | 0 |
| Revenue | $0.00 |
| Net | −$8.00 |

86 views in five days with 43 pins live is the traffic engine working.
**0 favourites from 86 views is the problem.** A favourite is free, so this
is not a price objection — it says the listings are not landing. The leading
suspect is the listing thumbnails: they are flat text cards that, at Etsy's
grid size, read as grey documents rather than as a product.

## Needs Leo

**One thing, and it is optional.** Everything above runs without you.

### Instagram — if you want a second traffic channel

Read the honest version first: Pinterest is a better fit for this product
than Instagram or TikTok, because every pin carries a clickable link straight
to the listing and keeps pulling for months. Instagram is link-in-bio only.
It is worth doing as a second channel, not as a replacement.

What only you can do:

1. Create an Instagram account for Leafnote (and the email it needs).
2. Switch it to a **Professional → Business** account in settings.
3. Create a Facebook Page and link it to that Instagram account.
   Meta's publishing API will not work without the linked Page.
4. At `developers.facebook.com/apps`, create an app, add the
   **Instagram** product, and put the App ID and App secret in `.env` as
   `IG_APP_ID` and `IG_APP_SECRET`.

Then tell me, and I handle the OAuth, the video generation and the posting.

**The risk, stated up front:** Meta's own docs list Advanced Access as
required for content publishing and do *not* confirm that an app's own
owner can publish with Standard Access alone. That is the same shape as the
Pinterest Trial-tier wall we already hit once. I will test with a single
post and verify it is publicly visible before building anything on top of
it, exactly as with the pins.

### TikTok — not automatable, and I checked properly

TikTok's Content Posting API restricts **all content from unaudited apps to
private viewing**. Lifting that needs approval for the `video.publish` scope,
a separate Terms-of-Service audit, and a verified domain. There is no
Standard-access button like Pinterest had.

So TikTok is manual uploads or nothing. I can generate the videos; posting
them would be on you. Worth it only if you actually want to.
