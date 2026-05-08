"""One-time OAuth setup for the Xero e2e test (and local dev).

Walks you through connecting to a Xero developer "Demo Company"
(developer.xero.com → My Apps → Try it → connect Demo Company),
captures the OAuth tokens, fetches your Xero tenant ID(s), and
prints a ready-to-paste block for ``.env``.

Why this script exists
----------------------
``ExternalTokenManager`` (mcp_servers/auth/token_store.py) is in-memory
only — tokens disappear when the Python process exits. For repeatable
e2e tests against real Xero we capture the tokens once here, paste
them into ``.env``, and the test fixture re-loads them into the
manager before each run.

Prerequisites
-------------
1. Sign up at https://developer.xero.com (free).
2. Create an app in "My Apps" — pick "Web app".
3. Add ``http://localhost:8765/callback`` as an OAuth 2.0 redirect URI.
4. Connect the "Demo Company (SG)" via the developer portal so the app
   has access to a sandbox org with a chart of accounts.
5. Copy the app's Client ID + Client Secret into ``.env``::

       XERO_CLIENT_ID=...
       XERO_CLIENT_SECRET=...

Usage
-----
::

    python scripts/xero_oauth_setup.py

Opens your browser to Xero's consent screen, then writes the captured
tokens to stdout. Copy them into ``.env`` under
``XERO_E2E_ACCESS_TOKEN`` / ``XERO_E2E_REFRESH_TOKEN`` /
``XERO_E2E_TENANT_ID`` for the e2e test to pick up.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REDIRECT_URI = "http://localhost:8765/callback"
LISTEN_PORT = 8765


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
    except ImportError:
        pass


class _CallbackHandler(BaseHTTPRequestHandler):
    """Single-shot HTTP handler that captures ?code=... and exits."""

    captured: dict[str, str] = {}

    def do_GET(self):  # noqa: N802 (HTTPServer convention)
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = dict(urllib.parse.parse_qsl(parsed.query))
        _CallbackHandler.captured.update(params)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        body = b"""<!DOCTYPE html>
        <html><body style="font-family:system-ui;max-width:480px;margin:80px auto;text-align:center">
        <h2 style="color:#0d6e4f">Xero authorization received.</h2>
        <p>You can close this tab and return to your terminal.</p>
        </body></html>"""
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):  # silence default access log
        return


def _capture_oauth_code(auth_url: str, expected_state: str) -> str:
    print(f"\nOpening Xero authorization URL in your browser…\n  {auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("127.0.0.1", LISTEN_PORT), _CallbackHandler)
    print(f"Listening for callback on {REDIRECT_URI} …")
    while "code" not in _CallbackHandler.captured:
        server.handle_request()

    captured = _CallbackHandler.captured
    if captured.get("state") != expected_state:
        raise RuntimeError(
            f"State mismatch: expected {expected_state}, got {captured.get('state')}. "
            "Aborting — possible CSRF."
        )
    code = captured.get("code")
    if not code:
        raise RuntimeError(f"No 'code' parameter in callback: {captured}")
    return code


async def main() -> None:
    _load_env()

    client_id = os.environ.get("XERO_CLIENT_ID", "").strip()
    client_secret = os.environ.get("XERO_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        logger.error(
            "XERO_CLIENT_ID and XERO_CLIENT_SECRET must be set in .env. "
            "See the docstring at the top of this script for setup steps."
        )
        sys.exit(2)

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from hr_advisory.mcp_servers.adapters.xero import (
        XERO_AUTHORIZE_URL,
        XERO_CONNECTIONS_URL,
        XERO_IDENTITY_URL,
    )

    import httpx

    # Use a dummy local tenant id — we only care about the access token + Xero
    # tenant id at the end. The local tenant id is just a key in the in-memory
    # store, which we won't use directly here.
    local_tenant = "xero-e2e-setup"
    state = secrets.token_urlsafe(16)
    scopes = [
        "openid",
        "profile",
        "email",
        "accounting.transactions",
        "accounting.reports.read",
        "accounting.settings.read",
        "offline_access",
    ]
    auth_params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(scopes),
            "state": state,
        }
    )
    auth_url = f"{XERO_AUTHORIZE_URL}?{auth_params}"

    code = _capture_oauth_code(auth_url, state)
    print("\nAuthorization code captured. Exchanging for tokens…")

    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            XERO_IDENTITY_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            logger.error(
                "Token exchange failed (HTTP %s): %s",
                token_resp.status_code,
                token_resp.text,
            )
            sys.exit(3)

        tokens = token_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token", "")

        # Fetch the connected Xero tenant(s) so the user knows what they
        # authorised. Most users have just one Demo Company.
        conn_resp = await client.get(
            XERO_CONNECTIONS_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if conn_resp.status_code != 200:
            logger.error(
                "Failed to list connections (HTTP %s): %s",
                conn_resp.status_code,
                conn_resp.text,
            )
            sys.exit(4)
        connections = conn_resp.json()

    if not connections:
        logger.error("No Xero connections found — connect a Demo Company first.")
        sys.exit(5)

    print("\n──────────────────────────────────────────────────────────────")
    print("Xero authorization successful.\n")
    for c in connections:
        print(
            f"  Tenant: {c.get('tenantName')}  "
            f"({c.get('tenantType')})  id={c.get('tenantId')}"
        )

    chosen = connections[0]
    chosen_id = chosen["tenantId"]

    print("\nAdd these lines to .env to enable the e2e test:\n")
    print(f"XERO_E2E_TENANT_ID={chosen_id}")
    print(f"XERO_E2E_ACCESS_TOKEN={access_token}")
    print(f"XERO_E2E_REFRESH_TOKEN={refresh_token}")
    print("\nAccess tokens expire after 30 minutes. The refresh token lets")
    print("the test refresh transparently. Re-run this script if both go stale.")
    print("──────────────────────────────────────────────────────────────")
    _ = local_tenant  # silence unused — kept for clarity in the docstring


if __name__ == "__main__":
    asyncio.run(main())
