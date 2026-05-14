"""
One-time OAuth bootstrap for Strava and Withings.

Usage:
    python3 setup/auth.py strava
    python3 setup/auth.py withings
    python3 setup/auth.py all

Stdlib only — no pip installs required.
Writes refresh tokens directly to .env in the project root.
"""
import http.server
import json
import os
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"

REDIRECT_PORT = 8888
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"

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
    env: dict = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _save_token(key: str, value: str) -> None:
    text = ENV_FILE.read_text()
    lines = text.splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"  Saved {key} to .env")


def _post_form(url: str, data: dict) -> dict:
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _reset_callback() -> None:
    global _auth_code, _server_done
    _auth_code = None
    _server_done = threading.Event()


def auth_strava() -> None:
    _reset_callback()
    env = _load_env()
    client_id = env.get("STRAVA_CLIENT_ID") or os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = env.get("STRAVA_CLIENT_SECRET") or os.getenv("STRAVA_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        sys.exit("Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env first.")

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read,activity:read_all",
    })
    auth_url = f"https://www.strava.com/oauth/authorize?{params}"

    print("Opening browser for Strava authorization...")
    print(f"If browser doesn't open, visit:\n  {auth_url}\n")

    threading.Thread(target=_run_local_server, daemon=True).start()
    webbrowser.open(auth_url)
    _server_done.wait(timeout=120)

    if not _auth_code:
        sys.exit("No auth code received.")

    data = _post_form("https://www.strava.com/oauth/token", {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": _auth_code,
        "grant_type": "authorization_code",
    })
    _save_token("STRAVA_REFRESH_TOKEN", data["refresh_token"])
    print("Strava auth complete.")


def auth_withings() -> None:
    _reset_callback()
    env = _load_env()
    client_id = env.get("WITHINGS_CLIENT_ID") or os.getenv("WITHINGS_CLIENT_ID", "")
    client_secret = env.get("WITHINGS_CLIENT_SECRET") or os.getenv("WITHINGS_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        sys.exit("Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET in .env first.")

    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "user.metrics,user.activity",
        "state": state,
    })
    auth_url = f"https://account.withings.com/oauth2_user/authorize2?{params}"

    print("Opening browser for Withings authorization...")
    print(f"If browser doesn't open, visit:\n  {auth_url}\n")

    threading.Thread(target=_run_local_server, daemon=True).start()
    webbrowser.open(auth_url)
    _server_done.wait(timeout=120)

    if not _auth_code:
        sys.exit("No auth code received.")

    body = _post_form("https://wbsapi.withings.net/v2/oauth2", {
        "action": "requesttoken",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": _auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
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
