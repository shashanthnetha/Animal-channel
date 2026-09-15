"""
YouTube OAuth2 Refresh Token Generator.

Run this script locally to obtain your YOUTUBE_REFRESH_TOKEN for GitHub Actions.

Prerequisites:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a project and enable 'YouTube Data API v3'.
3. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID'.
4. Select Application type: 'Web application' (or 'Desktop app').
   Add Authorized redirect URI: 'http://localhost:8090/'
5. Copy Client ID and Client Secret, then run this script:
   python scripts/get_youtube_token.py
"""

import http.server
import json
import urllib.parse
import webbrowser

import requests


OAUTH_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
REDIRECT_URI = "http://localhost:8090/"


def main():
    print("=" * 60)
    print("       YouTube OAuth2 Refresh Token Generator")
    print("=" * 60)
    print()
    client_id = input("Enter your Google Client ID: ").strip()
    client_secret = input("Enter your Google Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        return

    auth_code_holder = {"code": None}

    class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                auth_code_holder["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h1>Authorization successful!</h1><p>You can close this tab and return to the terminal.</p>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed to obtain code.")

        def log_message(self, format, *args):
            return  # silence log

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote(OAUTH_SCOPE)}&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    print()
    print("Opening browser for authorization...")
    print(f"If the browser doesn't open, visit this link manually:\n{auth_url}")
    print()
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", 8090), OAuthCallbackHandler)
    server.timeout = 120
    while auth_code_holder["code"] is None:
        server.handle_request()

    code = auth_code_holder["code"]
    print("Authorization code received! Exchanging for refresh token...")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    res = requests.post(token_url, data=payload)
    if res.status_code != 200:
        print(f"Error exchanging token (HTTP {res.status_code}): {res.text}")
        return

    data = res.json()
    refresh_token = data.get("refresh_token")

    print("\n" + "=" * 60)
    print("SUCCESS! Add these 3 secrets to your GitHub Repository Settings:")
    print("(Settings -> Secrets and variables -> Actions -> New repository secret)")
    print("=" * 60)
    print(f"YOUTUBE_CLIENT_ID     = {client_id}")
    print(f"YOUTUBE_CLIENT_SECRET = {client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN = {refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
