#!/usr/bin/env python3
"""Shared Etsy API client: token refresh, throttled requests, shop resolution.

Every other script imports this rather than re-implementing auth.

Run directly for a connectivity check:
    python scripts/etsy_client.py
"""

import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"

TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
API = "https://openapi.etsy.com/v3/application"

# App limit is 10 QPS / 10k per day. We stay well under it: nothing here is
# latency-sensitive, and a runaway retry loop burning the daily quota would
# take the whole pipeline down until midnight UTC.
MIN_INTERVAL = 0.25
_last_call = 0.0


def load_env() -> dict:
    """Read .env. newline='' so Windows CRLF never leaks \\r into a value."""
    if not ENV.exists():
        sys.exit(f"No .env at {ENV}")
    env = {}
    with open(ENV, "r", encoding="utf-8", newline="") as fh:
        for line in fh.read().replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(updates: dict) -> None:
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


class Etsy:
    def __init__(self):
        self.env = load_env()
        # Etsy uses the two credentials differently, and the docs do not say so:
        #   OAuth (connect + token) -> client_id is the Keystring alone.
        #   Every API request       -> x-api-key must be "keystring:shared_secret",
        #                              colon-joined.
        # Verified against /openapi-ping:
        #   keystring alone      -> 403 "Shared secret is required in x-api-key header."
        #   shared secret alone  -> 403 "API key not found or not active..."
        #   keystring:secret     -> 200
        # Do not "simplify" this to a single value; both forms fail.
        self.api_key = self.env.get("ETSY_API_KEY", "")
        self.shared_secret = self.env.get("ETSY_SHARED_SECRET", "")
        self.refresh_token = self.env.get("ETSY_REFRESH_TOKEN", "")
        if not self.api_key:
            sys.exit("ETSY_API_KEY (Keystring) missing from .env")
        if not self.shared_secret:
            sys.exit("ETSY_SHARED_SECRET missing from .env - needed for x-api-key")
        if not self.refresh_token:
            sys.exit("ETSY_REFRESH_TOKEN missing. Run: python scripts/etsy_auth.py")
        self.access_token = None

    # -- auth ----------------------------------------------------------
    def refresh(self) -> str:
        r = requests.post(TOKEN_URL, json={
            "grant_type": "refresh_token",
            "client_id": self.api_key,
            "refresh_token": self.refresh_token,
        }, timeout=30)
        if r.status_code != 200:
            sys.exit(
                f"Token refresh failed ({r.status_code}): {r.text}\n"
                "If this says the token is invalid or expired, rerun:\n"
                "    python scripts/etsy_auth.py"
            )
        data = r.json()
        self.access_token = data["access_token"]
        # Etsy rotates the refresh token on use; persist the new one or the
        # next run authenticates with a token Etsy has already retired.
        new_refresh = data.get("refresh_token")
        if new_refresh and new_refresh != self.refresh_token:
            self.refresh_token = new_refresh
            save_env({"ETSY_REFRESH_TOKEN": new_refresh})
        return self.access_token

    def headers(self) -> dict:
        if not self.access_token:
            self.refresh()
        return {
            "x-api-key": f"{self.api_key}:{self.shared_secret}",
            "Authorization": f"Bearer {self.access_token}",
        }

    # -- requests ------------------------------------------------------
    def _throttle(self):
        global _last_call
        gap = time.monotonic() - _last_call
        if gap < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - gap)
        _last_call = time.monotonic()

    def request(self, method: str, path: str, **kw) -> requests.Response:
        self._throttle()
        url = path if path.startswith("http") else f"{API}{path}"
        hdrs = self.headers()
        hdrs.update(kw.pop("headers", {}))
        r = requests.request(method, url, headers=hdrs, timeout=30, **kw)
        if r.status_code == 401:  # access token aged out mid-run
            self.refresh()
            hdrs = self.headers()
            hdrs.update(kw.pop("headers", {}))
            self._throttle()
            r = requests.request(method, url, headers=hdrs, timeout=30, **kw)
        return r

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    # -- shop ----------------------------------------------------------
    def shop_id(self) -> str:
        """Resolve and cache the shop id.

        Tries /users/me first: it is authoritative for the authenticated
        account. Falls back to name search, which can miss or return
        near-matches belonging to other sellers.
        """
        cached = self.env.get("ETSY_SHOP_ID", "")
        if cached:
            return cached

        r = self.get("/users/me")
        if r.status_code == 200:
            me = r.json()
            sid = me.get("shop_id")
            if sid:
                save_env({"ETSY_SHOP_ID": str(sid)})
                self.env["ETSY_SHOP_ID"] = str(sid)
                return str(sid)
            uid = me.get("user_id")
            if uid:
                r2 = self.get(f"/users/{uid}/shops")
                if r2.status_code == 200:
                    body = r2.json()
                    results = body.get("results", body if isinstance(body, list) else [])
                    if results:
                        sid = str(results[0]["shop_id"])
                        save_env({"ETSY_SHOP_ID": sid})
                        self.env["ETSY_SHOP_ID"] = sid
                        return sid
        return ""


def main() -> int:
    e = Etsy()
    print("Refreshing access token...")
    e.refresh()
    print("  ok\n")

    print("GET /users/me")
    r = e.get("/users/me")
    print(f"  {r.status_code}: {r.text[:400]}\n")

    sid = e.shop_id()
    if sid:
        print(f"shop_id = {sid}")
        r = e.get(f"/shops/{sid}")
        if r.status_code == 200:
            s = r.json()
            print(f"  shop_name   : {s.get('shop_name')}")
            print(f"  listing_act : {s.get('listing_active_count')}")
            print(f"  currency    : {s.get('currency_code')}")
            print(f"  is_vacation : {s.get('is_vacation')}")
        else:
            print(f"  shop fetch {r.status_code}: {r.text[:300]}")
    else:
        print("Could not resolve a shop id for this account.")
        print("Most likely the Etsy shop is not fully opened yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
