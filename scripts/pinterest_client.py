#!/usr/bin/env python3
"""Pinterest API v5 client: OAuth handshake, token refresh, board lookup.

    python scripts/pinterest_client.py          # connectivity check
    python scripts/pinterest_client.py --auth   # one-time OAuth

IMPORTANT -- the Trial tier trap:
Pinterest grants newly approved apps Trial access. On Trial, POST /pins
returns 201 with a real pin id, and the pin is visible ONLY to the account
that created it. Logged in as yourself everything looks perfect; logged out,
the pin does not exist. Pinterest documents this as "visible only to creator".

So a green run here does NOT mean your pins are public. check_visibility()
below reports which tier the app is on, and post_pins.py refuses to do a full
run on Trial unless you pass --force.
"""

import base64
import hashlib
import http.server
import re
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"

PORT = 3004
REDIRECT_URI = f"http://localhost:{PORT}/oauth/callback"
SCOPES = ["boards:read", "boards:write", "pins:read", "pins:write",
          "user_accounts:read"]

AUTH_URL = "https://www.pinterest.com/oauth/"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
API = "https://api.pinterest.com/v5"

_result: dict = {}


def read_env() -> dict:
    env = {}
    if not ENV.exists():
        return env
    with open(ENV, "r", encoding="utf-8", newline="") as fh:
        for line in fh.read().replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def write_env(updates: dict) -> None:
    # newline="" on both sides: Windows otherwise appends \r to every value,
    # and a token with a trailing \r fails auth with a useless error.
    with open(ENV, "r", encoding="utf-8", newline="") as fh:
        text = fh.read().replace("\r\n", "\n").replace("\r", "\n")
    for key, val in updates.items():
        pat = rf"(?m)^{re.escape(key)}=.*$"
        text = (re.sub(pat, f"{key}={val}", text) if re.search(pat, text)
                else text.rstrip() + f"\n{key}={val}\n")
    with open(ENV, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        p = urllib.parse.urlparse(self.path)
        if p.path != "/oauth/callback":
            self.send_response(404); self.end_headers(); return
        q = urllib.parse.parse_qs(p.query)
        _result["code"] = q.get("code", [None])[0]
        _result["state"] = q.get("state", [None])[0]
        _result["error"] = q.get("error_description", q.get("error", [None]))[0]
        ok = _result["code"] is not None
        body = ("<h2>Connected.</h2><p>Close this tab and go back to the terminal.</p>"
                if ok else f"<h2>Failed</h2><p>{_result['error']}</p>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<html><body style='font-family:system-ui;padding:3rem'>{body}</body></html>"
            .encode())
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *a):
        pass


def do_auth() -> int:
    env = read_env()
    cid = env.get("PINTEREST_APP_ID", "")
    secret = env.get("PINTEREST_APP_SECRET", "")
    if not cid or not secret:
        sys.exit("Set PINTEREST_APP_ID and PINTEREST_APP_SECRET in .env first.")

    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "state": state,
    })
    print(f"Listening on {REDIRECT_URI}")
    print("Approve the request in your browser.\n")
    print(f"If it does not open:\n{url}\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        webbrowser.open(url)
        httpd.serve_forever()

    if not _result.get("code"):
        sys.exit(f"Authorization failed: {_result.get('error')}")
    if _result.get("state") != state:
        sys.exit("State mismatch - aborting.")

    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(TOKEN_URL,
                      headers={"Authorization": f"Basic {basic}",
                               "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "authorization_code",
                            "code": _result["code"],
                            "redirect_uri": REDIRECT_URI},
                      timeout=30)
    if r.status_code != 200:
        sys.exit(f"Token exchange failed ({r.status_code}): {r.text}")
    tok = r.json()
    write_env({"PINTEREST_ACCESS_TOKEN": tok["access_token"],
               "PINTEREST_REFRESH_TOKEN": tok.get("refresh_token", "")})
    print("\nDone. .env updated.")
    return 0


class Pinterest:
    def __init__(self):
        env = read_env()
        self.cid = env.get("PINTEREST_APP_ID", "")
        self.secret = env.get("PINTEREST_APP_SECRET", "")
        self.token = env.get("PINTEREST_ACCESS_TOKEN", "")
        self.refresh_token = env.get("PINTEREST_REFRESH_TOKEN", "")
        if not self.token:
            sys.exit("No PINTEREST_ACCESS_TOKEN. Run:\n"
                     "    python scripts/pinterest_client.py --auth")

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def refresh(self):
        if not self.refresh_token:
            return False
        basic = base64.b64encode(f"{self.cid}:{self.secret}".encode()).decode()
        r = requests.post(TOKEN_URL,
                          headers={"Authorization": f"Basic {basic}"},
                          data={"grant_type": "refresh_token",
                                "refresh_token": self.refresh_token},
                          timeout=30)
        if r.status_code != 200:
            return False
        tok = r.json()
        self.token = tok["access_token"]
        write_env({"PINTEREST_ACCESS_TOKEN": self.token})
        return True

    def request(self, method, path, **kw):
        url = path if path.startswith("http") else f"{API}{path}"
        r = requests.request(method, url, headers=self.headers(), timeout=40, **kw)
        if r.status_code == 401 and self.refresh():
            r = requests.request(method, url, headers=self.headers(),
                                 timeout=40, **kw)
        return r

    def get(self, p, **kw):
        return self.request("GET", p, **kw)

    def post(self, p, **kw):
        return self.request("POST", p, **kw)

    def boards(self) -> dict:
        """Map board name -> id. Board names in the CSV must match exactly."""
        out, bookmark = {}, None
        while True:
            params = {"page_size": 100}
            if bookmark:
                params["bookmark"] = bookmark
            r = self.get("/boards", params=params)
            if r.status_code != 200:
                print(f"  boards {r.status_code}: {r.text[:200]}")
                return out
            body = r.json()
            for b in body.get("items", []):
                out[b["name"]] = b["id"]
            bookmark = body.get("bookmark")
            if not bookmark:
                return out

    def create_board(self, name, description=""):
        return self.post("/boards", json={"name": name,
                                          "description": description[:500]})

    def create_pin(self, board_id, image_url, title, description, link):
        """Pinterest fetches image_url itself, so it must be publicly reachable."""
        return self.post("/pins", json={
            "board_id": board_id,
            "media_source": {"source_type": "image_url", "url": image_url},
            "title": title[:100],
            "description": description[:800],
            "link": link,
        })

    def access_tier(self) -> str:
        """Best-effort read of whether this app is Trial or Standard.

        Pinterest exposes no tier endpoint, so this is inferred and should be
        treated as a hint, not proof. The only reliable check is opening a
        created pin in a logged-out browser.
        """
        r = self.get("/user_account")
        if r.status_code != 200:
            return f"unknown (user_account {r.status_code})"
        return "connected"


def main() -> int:
    if "--auth" in sys.argv:
        return do_auth()
    p = Pinterest()
    r = p.get("/user_account")
    print("GET /user_account ->", r.status_code)
    if r.status_code == 200:
        d = r.json()
        print("  username :", d.get("username"))
        print("  type     :", d.get("account_type"))
    else:
        print(" ", r.text[:300])
        return 1
    bs = p.boards()
    print(f"\nboards ({len(bs)}):")
    for n, i in bs.items():
        print(f"  {n}  ->  {i}")
    print("\nNOTE: a successful pin create on Trial access is still invisible")
    print("to everyone but you. Verify one pin in a logged-out browser before")
    print("trusting a full run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
