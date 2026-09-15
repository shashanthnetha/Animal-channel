"""
YouTube OAuth2 Refresh Token Generator.

Run this script locally to obtain your YOUTUBE_REFRESH_TOKEN and automatically
save it to your GitHub Repository Secrets!

Usage:
  .venv/bin/python scripts/get_youtube_token.py --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET>
"""

import argparse
import http.server
import json
import os
import subprocess
import sys
import urllib.parse
import webbrowser

import requests


OAUTH_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
REDIRECT_URI = "http://localhost:8090/"


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube OAuth2 Refresh Token")
    parser.add_argument("--client-id", default=os.getenv("YOUTUBE_CLIENT_ID", ""), help="Google OAuth Client ID")
    parser.add_argument("--client-secret", default=os.getenv("YOUTUBE_CLIENT_SECRET", ""), help="Google OAuth Client Secret")
    parser.add_argument("--repo", default="shashanthnetha/Animal-channel", help="GitHub repository (owner/repo)")

    args = parser.parse_args()

    client_id = (args.client_id or "").strip()
    client_secret = (args.client_secret or "").strip()

    print("=" * 65)
    print("       YouTube OAuth2 Refresh Token Generator & Auto-Uploader")
    print("=" * 65)

    if not client_id:
        client_id = input("Enter your Google Client ID: ").strip()
    if not client_secret:
        client_secret = input("Enter your Google Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        return

    print(f"Client ID: {client_id[:20]}...")
    print(f"Target GitHub Repo: {args.repo}")
    print()

    auth_code_holder = {"code": None}

    class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                auth_code_holder["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body style='font-family:sans-serif;text-align:center;padding:50px;'>"
                    b"<h1 style='color:#10b981;'>&#10004; Authorization Successful!</h1>"
                    b"<p>You can close this tab and return to your terminal.</p>"
                    b"</body></html>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed to obtain authorization code.")

        def log_message(self, format, *args):
            return

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote(OAUTH_SCOPE)}&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    print("Opening your browser to authorize your YouTube channel...")
    print("If your browser does not open automatically, visit this link:")
    print(f"\n{auth_url}\n")

    webbrowser.open(auth_url)

    try:
        server = http.server.HTTPServer(("localhost", 8090), OAuthCallbackHandler)
        server.timeout = 180
        print("Waiting for Google authorization callback on http://localhost:8090/ ...")
        while auth_code_holder["code"] is None:
            server.handle_request()
    except Exception as exc:
        print(f"Local server notice: {exc}")
        code = input("Paste the authorization code or redirected URL here: ").strip()
        if "code=" in code:
            code = code.split("code=")[1].split("&")[0]
        auth_code_holder["code"] = code

    code = auth_code_holder["code"]
    if not code:
        print("Error: No authorization code received.")
        return

    print("Exchanging authorization code for refresh token...")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    res = requests.post(token_url, data=payload, timeout=30)
    if res.status_code != 200:
        print(f"\nError exchanging token (HTTP {res.status_code}): {res.text}")
        print("\nNote: Make sure 'http://localhost:8090/' is added to 'Authorized redirect URIs'")
        print("in your Google Cloud Console OAuth 2.0 Client ID settings.")
        return

    data = res.json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        print("\nWarning: No refresh_token was returned in response.")
        print("Full response:", data)
        return

    print("\n" + "=" * 65)
    print("SUCCESS! YOUTUBE_REFRESH_TOKEN OBTAINED:")
    print("=" * 65)
    print(refresh_token)
    print("=" * 65)

    # Automatically set in GitHub Secrets
    try:
        print(f"\nSetting YOUTUBE_REFRESH_TOKEN in GitHub repository {args.repo}...")
        cmd = ["gh", "secret", "set", "YOUTUBE_REFRESH_TOKEN", "-R", args.repo, "--body", refresh_token]
        sub_res = subprocess.run(cmd, capture_output=True, text=True)
        if sub_res.returncode == 0:
            print(f"✅ Successfully set YOUTUBE_REFRESH_TOKEN in GitHub secrets for {args.repo}!")
        else:
            print(f"Could not auto-set secret via gh CLI: {sub_res.stderr}")
    except Exception as exc:
        print(f"Could not run gh CLI: {exc}")


if __name__ == "__main__":
    main()
