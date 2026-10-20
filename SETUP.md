# Setup — one session, ~90 minutes

Everything here is something I'm legally or technically barred from doing: creating accounts,
verifying your identity, connecting your bank, and accepting terms. Do it in this order —
steps 1 and 2 can sit in a review queue, so starting them first means the wait overlaps
with the rest.

Have ready before you sit down: **photo ID, bank account + routing number, SSN (or EIN),
and a debit/credit card.**

---

## 1. Etsy seller account  (~30 min, plus verification wait)

1. Go to **etsy.com/sell** → **Get started**.
2. Sign up with your email. Verify the email before continuing.
3. Shop preferences: language **English (US)**, country **United States**, currency **USD**.
4. Shop name. Must be 4–20 characters, letters and numbers only, no spaces or punctuation, and unique.
   Try in this order and take the first available:
   - `Leafnote`
   - `LeafnoteStudio`
   - `LeafnoteCo`
   - `TheLeafnote`
   **Write down which one you got** — I need the exact string.
5. Etsy will push you to add a listing. **Skip it** if it lets you; I'll add listings by API.
   If it forces one, make any placeholder and set it to draft.
6. **How you'll get paid** → connect your bank account. Needs routing + account number.
7. Identity verification → SSN (or EIN if you got one) and photo ID upload.
8. **How you'll pay Etsy fees** → add your debit/credit card.
9. Open your shop.

> This step may leave you "pending verification" for a few hours to a couple of days. That's normal.
> Keep going with the rest.

## 2. Etsy developer app → API keys  (~10 min, plus approval wait)

1. Go to **etsy.com/developers** → sign in with the same account.
2. You'll see two cards. Pick the **second one — "Create a seller app" → Get started.**

   > **Not "Create a personal app."** That one is for tools other buyers and sellers use, and
   > Etsy puts it through a deeper review. A seller app is scoped to your own shop and Etsy
   > describes its approval as light and straightforward. We only ever touch your own shop,
   > so the seller app is both correct and faster.

3. Fill in:
   - **Name:** Leafnote Listing Manager
   - **Description:** Creates and updates digital download listings for my own shop.
4. Set the **callback/redirect URI** to exactly:
   ```
   http://localhost:3003/oauth/callback
   ```
   If the form won't accept a localhost URI, tell me and I'll switch the auth script to a
   different flow — don't invent a different URL, it has to match what the script listens on.
5. Submit. Seller-app approval is the light path, but it can still take a day or two.
6. Once approved, copy the **Keystring** (API key) and **Shared Secret**. Paste both into `.env`
   (step 5 of this checklist).

## 3. GitHub account + repo  (~10 min)

1. **github.com** → sign up (skip if you already have one).
2. **New repository** → name it `leafnote` → **Public** (required for free GitHub Pages) → Create.
3. On the repo: **Settings → Pages → Source: GitHub Actions**.
4. **Settings → Actions → General** → scroll to *Workflow permissions* → select
   **Read and write permissions** → Save. The cron job can't publish without this.
5. Copy the repo URL.

## 4. Pinterest + TikTok + Metricool  (~20 min)

**4a. Pinterest business account**

1. **pinterest.com/business/create** → sign up.
2. Name the account `Leafnote`, category **Home Decor** or **Gardening**.
3. **Claim your website** once the blog is live — I'll tell you the URL when it is.

**4b. TikTok account**

1. **tiktok.com** → sign up → **Settings → Account → Switch to Business Account**.
2. Category: **Home & Garden**. Business account is required for scheduling tools to connect.

**4c. Metricool** — this is what replaces the API approval I can't get

1. **metricool.com** → sign up for the **free** plan. Do not enter a card; the free tier
   needs no payment method.
2. **Connect brand** → connect **Pinterest** and **TikTok** using the accounts from 4a and 4b.
3. That's it. Nothing else to configure.

> Why Metricool: Pinterest's own API puts new apps in Trial tier, where pins are visible only
> to the creator, and Standard access needs a review I can't guarantee passing. Metricool already
> holds approved access, so it can actually publish. Free tier covers **1 brand, 20 scheduled
> posts/month**, which matches our publishing rate, plus 30 days of analytics that feed the
> weekly report. Buffer's free tier (3 channels, 10 queued posts) is the fallback if Metricool
> changes terms.
>
> **Your ongoing job becomes: one bulk upload per month, ~15 minutes.** I drop pin images and
> copy into `designs/pins/`; you upload and schedule the batch in Metricool.

## 5. Paste the keys  (~5 min)

Create a file called `.env` in `C:\Users\Leo\ventures\leafnote\` containing exactly this,
with your real values filled in:

```
ETSY_API_KEY=
ETSY_SHARED_SECRET=
ETSY_SHOP_NAME=
GITHUB_REPO_URL=
```

> `.env` is gitignored. Never paste these keys into a chat message, a commit, or a
> screenshot — an Etsy API key plus secret can act on your shop.

Then run this once and follow the browser prompt — it does the OAuth handshake and writes
your refresh token into `.env` automatically:

```bash
python scripts/etsy_auth.py
```

(I'll have that script written before you get here. It uses the Python 3.12 already on your
machine — nothing to install.)

---

## Then tell me

- The exact shop name you got
- That `.env` is filled in
- **Yes or no on $8.00 of Etsy listing fees** for the first 40 listings

That's everything. After this you're at ~15 min/week uploading a pin batch I'll have waiting for you.
