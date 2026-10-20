#!/usr/bin/env python3
"""One-time Etsy OAuth handshake. Run locally; needs a browser on this machine.

Etsy v3 uses OAuth 2.0 with PKCE. This script:
  1. starts a local listener on the redirect URI registered with the app,
  2. opens the Etsy consent page,
  3. exchanges the returned code for tokens,
  4. resolves the shop id from the shop name,
  5. writes ETSY_REFRESH_TOKEN and ETSY_SHOP_ID back into .env.

Access tokens last 1 hour; the refresh token lasts 90 days and is what every other
script uses. If the refresh token expires, just run this again.

    python scripts/etsy_auth.py
"""

import base64
import hashlib
import http.server
import os
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

PORT = 3003
REDIRECT_URI = f"http://localhost:{PORT}/oauth/callback"
SCOPES = [
    "listings_r", "listings_w",   # read and create/update listings
    "shops_r", "shops_w",         # shops_w is required for shop sections
    "transactions_r",             # sales figures for the weekly report
]

CONNECT_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
API = "https://openapi.etsy.com/v3/application"

_result: dict = {}


def read_env() -> dict:
    if not ENV.exists():
        sys.exit(f"No .env found at {ENV}\nCopy .env.example to .env and fill it in first.")
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def write_env(updates: dict) -> None:
    """Update keys in place, preserving comments and ordering.

    newline="" on both read and write is load-bearing on Windows: without it
    Python translates \\n to \\r\\n on write, which appends a carriage return to
    every value in the file. A key with a trailing \\r fails authentication with
    an error that gives no hint about why.
    """
    with open(ENV, "r", encoding="utf-8", newline="") as fh:
        text = fh.read().replace("\r\n", "\n").replace("\r", "\n")
    for key, val in updates.items():
        pattern = rf"(?m)^{re.escape(key)}=.*$"
        if re.search(pattern, text):
            text = re.sub(pattern, f"{key}={val}", text)
        else:
            text = text.rstrip() + f"\n{key}={val}\n"
    with open(ENV, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/oauth/callback":
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        _result["code"] = qs.get("code", [None])[0]
        _result["state"] = qs.get("state", [None])[0]
        _result["error"] = qs.get("error_description", qs.get("error", [None]))[0]

        ok = _result["code"] is not None
        body = (
            "<h2>Connected.</h2><p>You can close this tab and go back to the terminal.</p>"
            if ok else
            f"<h2>Authorization failed</h2><p>{_result['error']}</p>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<html><body style='font-family:system-ui;padding:3rem'>{body}</body></html>"
            .encode("utf-8")
        )
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):  # silence the default request logging
        pass


def main() -> int:
    env = read_env()
    api_key = env.get("ETSY_API_KEY")
    shop_name = env.get("ETSY_SHOP_NAME")
    if not api_key:
        sys.exit("ETSY_API_KEY is empty in .env. Paste your app's Keystring first.")
    if not shop_name:
        sys.exit("ETSY_SHOP_NAME is empty in .env.")

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    state = secrets.token_urlsafe(16)

    auth_url = f"{CONNECT_URL}?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })

    print(f"Listening on {REDIRECT_URI}")
    print("Opening Etsy in your browser. Approve the request there.\n")
    print(f"If it doesn't open, paste this in manually:\n{auth_url}\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        webbrowser.open(auth_url)
        httpd.serve_forever()

    if _result.get("error") or not _result.get("code"):
        sys.exit(f"Authorization failed: {_result.get('error')}")
    if _result.get("state") != state:
        sys.exit("State mismatch - aborting rather than trusting this response.")

    print("Exchanging code for tokens...")
    r = requests.post(TOKEN_URL, json={
        "grant_type": "authorization_code",
        "client_id": api_key,
        "redirect_uri": REDIRECT_URI,
        "code": _result["code"],
        "code_verifier": verifier,
    }, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Token exchange failed ({r.status_code}): {r.text}")
    tokens = r.json()
    access, refresh = tokens["access_token"], tokens["refresh_token"]

    print(f"Resolving shop id for '{shop_name}'...")
    headers = {"x-api-key": api_key, "Authorization": f"Bearer {access}"}
    r = requests.get(f"{API}/shops", params={"shop_name": shop_name},
                     headers=headers, timeout=30)
    shop_id = ""
    if r.status_code == 200:
        results = r.json().get("results", [])
        exact = [s for s in results
                 if s.get("shop_name", "").lower() == shop_name.lower()]
        if exact:
            shop_id = str(exact[0]["shop_id"])
            print(f"  shop_id = {shop_id}")
        else:
            print(f"  No exact match for '{shop_name}'. Found: "
                  f"{[s.get('shop_name') for s in results] or 'nothing'}")
    else:
        print(f"  Lookup failed ({r.status_code}). You can set ETSY_SHOP_ID by hand.")

    updates = {"ETSY_REFRESH_TOKEN": refresh}
    if shop_id:
        updates["ETSY_SHOP_ID"] = shop_id
    write_env(updates)

    print("\nDone. .env updated.")
    print("The refresh token is valid for 90 days; rerun this script if it lapses.")
    if not shop_id:
        print("\nETSY_SHOP_ID is still blank - tell me and I'll sort it out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
