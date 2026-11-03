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
**0 favourites from 86 views was the problem.** A favourite is free, so that
was not a price objection — the listings were not landing.

**Fixed 2 November:** all 40 listing thumbnails replaced with styled 2000x2000
mockups. The old previews read as grey worksheets at Etsy's grid size, all 40
shared one layout, and they did not fill the square tile. The watermarked
preview is retained as image 2. Verified on all 40 via the API.

**Price deliberately unchanged** at $4.00, so the next report measures one
variable. Do not change price until there are 200+ views.

## Needs Leo

**One thing, and it is optional.** Everything above runs without you.

### Instagram — in progress, 2 November

Done already, by me, verified:

- Account `leafnotestudio` converted to a **Professional / Business** account
  (confirmed: settings now show "Professional account - Business tools and
  controls", which only exists on a professional account)
- Category set to Shopping & retail
- **Declined** Instagram's offer to publish contact details on the public
  profile. It wanted email, phone and street address shown publicly. Nothing
  requires that, so it is off.

**Correction to the earlier version of this file:** it said a Facebook Page
was required and had you create one. That is wrong. The newer
"Instagram API with Instagram Login" path explicitly does not require a
Facebook Page linked to the Instagram account. Skip that step entirely.

**What is blocking, and it is only you:** creating the Meta developer app
needs a login at developers.facebook.com, and the only options are
"Continue with Facebook", "Create new account", or a managed Meta account.
That is a password field, so it is yours.

1. Sign in (or create an account) at developers.facebook.com
2. Tell me

Then I create the app, add the Instagram product, pull the App ID and
secret, run the OAuth, and test with a single post.

**The risk is unchanged:** Meta's docs list Advanced Access for content
publishing and do not confirm an app's own owner can publish without it.
Same shape as the Pinterest Trial-tier wall. I will verify one post is
publicly visible before building anything on top of it.

**And the ceiling, also unchanged:** generated videos are silent, and
trending audio can only be attached inside the app, not through the API.
Posting manually with a trending sound will outperform anything automated.

### TikTok — not automatable, and I checked properly

TikTok's Content Posting API restricts **all content from unaudited apps to
private viewing**. Lifting that needs approval for the `video.publish` scope,
a separate Terms-of-Service audit, and a verified domain. There is no
Standard-access button like Pinterest had.

So TikTok is manual uploads or nothing. I can generate the videos; posting
them would be on you. Worth it only if you actually want to.
