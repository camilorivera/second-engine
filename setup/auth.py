"""
One-time OAuth bootstrap for Strava and Withings.

Usage:
    python setup/auth.py strava
    python setup/auth.py withings
    python setup/auth.py all

Writes refresh tokens to .env in the project root.
Requires STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET (or WITHINGS equivalents)
to already be present in .env before running.
"""
import http.server
import os
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"

REDIRECT_PORT = 8888
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

_auth_code: str | None = None
_server_done = threading.Event()


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]

        if error:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Auth error: {error}".encode())
            _auth_code = None
        else:
            _auth_code = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Auth complete. You can close this tab.")

        _server_done.set()

    def log_message(self, *args):
        pass


def _run_local_server() -> None:
    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    server.handle_request()


def _load_env() -> dict:
    if not ENV_FILE.exists():
        sys.exit(f".env not found at {ENV_FILE}. Run: cp .env.example .env")
    return dotenv_values(ENV_FILE)


def _save_token(key: str, value: str) -> None:
    set_key(str(ENV_FILE), key, value)
    print(f"  Saved {key} to .env")


def auth_strava() -> None:
    env = _load_env()
    client_id = env.get("STRAVA_CLIENT_ID") or os.getenv("STRAVA_CLIENT_ID")
    client_secret = env.get("STRAVA_CLIENT_SECRET") or os.getenv("STRAVA_CLIENT_SECRET")

    if not client_id or not client_secret:
        sys.exit("STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set in .env first.")

    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
    )

    print("Opening browser for Strava authorization...")
    print(f"If browser doesn't open, visit:\n  {auth_url}\n")

    thread = threading.Thread(target=_run_local_server, daemon=True)
    thread.start()
    webbrowser.open(auth_url)
    _server_done.wait(timeout=120)

    if not _auth_code:
        sys.exit("No auth code received. Check the browser for errors.")

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _auth_code,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    _save_token("STRAVA_REFRESH_TOKEN", data["refresh_token"])
    print("Strava auth complete.")


def auth_withings() -> None:
    global _auth_code, _server_done
    _auth_code = None
    _server_done = threading.Event()

    env = _load_env()
    client_id = env.get("WITHINGS_CLIENT_ID") or os.getenv("WITHINGS_CLIENT_ID")
    client_secret = env.get("WITHINGS_CLIENT_SECRET") or os.getenv("WITHINGS_CLIENT_SECRET")

    if not client_id or not client_secret:
        sys.exit("WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET must be set in .env first.")

    auth_url = (
        f"https://account.withings.com/oauth2_user/authorize2"
        f"?client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope=user.metrics,user.activity"
    )

    print("Opening browser for Withings authorization...")
    print(f"If browser doesn't open, visit:\n  {auth_url}\n")

    thread = threading.Thread(target=_run_local_server, daemon=True)
    thread.start()
    webbrowser.open(auth_url)
    _server_done.wait(timeout=120)

    if not _auth_code:
        sys.exit("No auth code received. Check the browser for errors.")

    resp = requests.post(
        "https://wbsapi.withings.net/v2/oauth2",
        data={
            "action": "requesttoken",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 0:
        sys.exit(f"Withings token exchange failed: {body}")

    _save_token("WITHINGS_REFRESH_TOKEN", body["body"]["refresh_token"])
    print("Withings auth complete.")


if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if target in ("strava", "all"):
        auth_strava()
    if target in ("withings", "all"):
        auth_withings()
