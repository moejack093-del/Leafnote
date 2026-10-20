# Pinterest Standard access — the application

This is the only thing standing between here and me posting your pins for you.
Two minutes of your time, once. After that `post_pins.py` posts everything
automatically, forever.

---

## Step 1 — create the app (3 min)

Go to **developers.pinterest.com/apps** → **Create app**.

**App name**
```
Leafnote Pin Manager
```

**What are you building / description** — paste this:
```
A personal tool that publishes product pins for my own Pinterest business
account. It reads a local list of plant care card images that I created,
along with their titles, descriptions and destination links, and creates the
corresponding pins on my own boards on a schedule. It only ever acts on my
own account and does not read or write any other user's data.
```

**Redirect URI** — exactly this, it must match what the script listens on:
```
http://localhost:3004/oauth/callback
```

Then copy the **App ID** and **App secret** into `.env`:
```
PINTEREST_APP_ID=
PINTEREST_APP_SECRET=
```

Those two lines are already waiting in the file, blank.

---

## Step 2 — record the video (2 min)

Pinterest requires a screen recording of the OAuth flow working. Solo
developers are not exempt. It does not need to be polished -- no narration,
no editing. Press record and run the command.

**Use Windows' built-in recorder: `Win + Alt + R`.**

What the recording has to show, in one unbroken take:

1. The terminal, with the command typed:
   ```
   python scripts/pinterest_client.py --auth
   ```
2. You press enter, the browser opens Pinterest's authorization page
3. The Pinterest consent screen, clearly showing it is asking to connect
4. You click **Grant access** / **Continue**
5. The "Connected." page
6. Back to the terminal showing "Done. .env updated."

Then run this and let it capture the output:
```
python scripts/pinterest_client.py
```
It prints your account and boards, which demonstrates a live API call.

Stop recording. The file lands in Videos\Captures.

**That is the whole video.** About 45 seconds.

---

## Step 3 — submit (1 min)

On the app card in **My apps**, click **Upgrade**. Attach the video.

If there is a free-text field about intended use, paste the description from
Step 1 again.

---

## Then what

Approval takes anywhere from a few days to a few weeks. Pinterest emails you.
One developer reported 26 days with no response, so do not expect it quickly.

**When the email arrives, tell me.** I run:
```
python scripts/post_pins.py --check     # one pin, verify it is public
python scripts/post_pins.py --live      # the other 42
```
and your pins are live.

Until then nothing is lost. The pins are built, hosted and verified. They are
just waiting.

---

## If you cannot do even this

Say so plainly and we will stop pretending otherwise. The honest position is
that an Etsy shop with no external traffic and nobody posting will sit at zero
indefinitely -- not because the work is bad, but because nothing is pointing
at it. That is worth knowing now rather than in three months.
