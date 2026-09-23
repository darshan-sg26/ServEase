"""
ServEase Gmail API Token Management & Diagnostic Utility
=========================================================
This script safely checks, tests, and updates Gmail API OAuth credentials for
email OTP delivery over HTTPS (port 443).

Usage:
  1. Check current token health:
     python refresh_gmail_token.py --check

  2. Print authorization URL to obtain a new code:
     python refresh_gmail_token.py --auth-url

  3. Exchange an authorization code (from Google OAuth) for a refresh token and update .env:
     python refresh_gmail_token.py --code "4/0A..."

  4. Set a new refresh token directly and update .env:
     python refresh_gmail_token.py --token "1//04..."

  5. Send a test OTP verification email to verify end-to-end delivery:
     python refresh_gmail_token.py --test-send servease.dev@gmail.com
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
from dotenv import dotenv_values, set_key
import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

ENV_PATH = Path(__file__).resolve().parent / ".env"
OAUTH_PLAYGROUND_REDIRECT = "https://developers.google.com/oauthplayground"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"

def load_env_config():
    if not ENV_PATH.exists():
        print(f"[ERROR] .env file not found at {ENV_PATH}")
        sys.exit(1)
    vals = dotenv_values(str(ENV_PATH))
    return {
        "client_id": vals.get("GMAIL_CLIENT_ID", "").strip(),
        "client_secret": vals.get("GMAIL_CLIENT_SECRET", "").strip(),
        "refresh_token": vals.get("GMAIL_REFRESH_TOKEN", "").strip(),
        "sender_email": vals.get("GMAIL_SENDER_EMAIL", "servease.dev@gmail.com").strip(),
    }

def print_diagnostics(cfg):
    print("=" * 65)
    print("ServEase Gmail API Configuration Diagnostics")
    print("=" * 65)
    print(f"GMAIL_CLIENT_ID configured:     {bool(cfg['client_id'])}")
    print(f"GMAIL_CLIENT_SECRET configured: {bool(cfg['client_secret'])}")
    print(f"GMAIL_REFRESH_TOKEN configured: {bool(cfg['refresh_token'])}")
    print(f"GMAIL_SENDER_EMAIL:             {cfg['sender_email']}")
    print("-" * 65)

def get_auth_url(client_id):
    import urllib.parse
    params = {
        "client_id": client_id,
        "redirect_uri": OAUTH_PLAYGROUND_REDIRECT,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent"
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

def check_token(cfg):
    print("\n[Testing Token Health] Calling Google OAuth2 token endpoint...")
    if not cfg["refresh_token"]:
        print("[FAIL] No refresh token currently configured in .env.")
        return False

    creds = Credentials(
        token=None,
        refresh_token=cfg["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=[GMAIL_SCOPE]
    )

    try:
        creds.refresh(Request())
        if creds.valid:
            print("[SUCCESS] Refresh token is ACTIVE and valid! Access token refreshed successfully.")
            return True
    except Exception as e:
        print(f"[FAIL] Refresh token validation error: {type(e).__name__}: {e}")
        return False

def exchange_code_for_tokens(code, cfg):
    print(f"\n[Exchanging Authorization Code] Contacting oauth2.googleapis.com...")
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code.strip(),
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": OAUTH_PLAYGROUND_REDIRECT,
            "grant_type": "authorization_code"
        },
        timeout=15.0
    )

    if resp.status_code != 200:
        print(f"[FAIL] Token exchange failed with status {resp.status_code}:")
        try:
            print(resp.json())
        except Exception:
            print(resp.text)
        return None

    data = resp.json()
    new_refresh = data.get("refresh_token")
    if not new_refresh:
        print("[WARNING] Google returned an access token but NO new refresh_token.")
        print("          Ensure 'prompt=consent' and 'access_type=offline' were included in auth.")
        print(f"          Payload received keys: {list(data.keys())}")
        return None

    print("[SUCCESS] Successfully obtained new Refresh Token from Google!")
    save_refresh_token(new_refresh)
    return new_refresh

def save_refresh_token(new_refresh):
    set_key(str(ENV_PATH), "GMAIL_REFRESH_TOKEN", new_refresh)
    print(f"[SAVED] Updated GMAIL_REFRESH_TOKEN in {ENV_PATH}")

async def send_test_email(to_email):
    backend_root = str(Path(__file__).resolve().parent)
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    from app.services.email_service import send_otp_email
    print(f"\n[Sending Test OTP Email] Dispatching test email to {to_email} via Gmail API...")
    try:
        await send_otp_email(to_email=to_email, otp="999888", recipient_name="ServEase Test")
        print(f"[SUCCESS] Test verification email successfully dispatched to {to_email}!")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to dispatch email: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="ServEase Gmail API Token Manager")
    parser.add_argument("--check", action="store_true", help="Check current token validity")
    parser.add_argument("--auth-url", action="store_true", help="Display the OAuth authorization URL")
    parser.add_argument("--code", type=str, help="Authorization code from Google to exchange")
    parser.add_argument("--token", type=str, help="Manually set a new refresh token in .env")
    parser.add_argument("--test-send", type=str, help="Send a test verification email to this address")
    args = parser.parse_args()

    cfg = load_env_config()
    print_diagnostics(cfg)

    if args.auth_url:
        print("\nAuthorize this app by opening the following URL in your browser:")
        print("-" * 65)
        print(get_auth_url(cfg["client_id"]))
        print("-" * 65)
        print("After allowing permissions, copy the 'code=...' from your browser's address bar")
        print("and run: python refresh_gmail_token.py --code \"<YOUR_CODE>\"")
        return

    if args.code:
        new_token = exchange_code_for_tokens(args.code, cfg)
        if new_token:
            cfg["refresh_token"] = new_token
            asyncio.run(send_test_email(cfg["sender_email"]))
        return

    if args.token:
        save_refresh_token(args.token)
        cfg["refresh_token"] = args.token
        asyncio.run(send_test_email(cfg["sender_email"]))
        return

    if args.test_send:
        asyncio.run(send_test_email(args.test_send))
        return

    is_valid = check_token(cfg)
    if not is_valid:
        print("\nAction Required:")
        print("Open the following authorization URL in your browser to re-authorize servease.dev@gmail.com:")
        print("-" * 65)
        print(get_auth_url(cfg["client_id"]))
        print("-" * 65)
        print("Or use Google OAuth Playground with scope 'https://www.googleapis.com/auth/gmail.send'")

if __name__ == "__main__":
    main()
