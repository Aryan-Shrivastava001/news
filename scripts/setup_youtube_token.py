"""
Helper script to authenticate and obtain YouTube OAuth2 Refresh Token for GitHub Secrets.

Instructions:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a project, enable 'YouTube Data API v3'
3. Configure OAuth Consent Screen (External, add your personal email as Test User)
4. Create Credentials -> OAuth Client ID (Type: Desktop Application)
5. Download client_secrets.json or copy Client ID and Client Secret
6. Run: python scripts/setup_youtube_token.py
"""

import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    print("=== YouTube Shorts Bot: OAuth2 Token Generator ===\n")
    client_secret_file = Path("client_secrets.json")

    if not client_secret_file.exists():
        print("client_secrets.json not found.")
        client_id = input("Enter your OAuth Client ID: ").strip()
        client_secret = input("Enter your OAuth Client Secret: ").strip()

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"]
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), scopes=SCOPES)

    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    print("\n" + "="*50)
    print("SUCCESS! Here are your credentials for .env or GitHub Secrets:")
    print("="*50)
    print(f"YOUTUBE_CLIENT_ID={flow.client_config['client_id']}")
    print(f"YOUTUBE_CLIENT_SECRET={flow.client_config['client_secret']}")
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print("="*50)
    print("\nCopy these 3 values into your repository's Settings -> Secrets and variables -> Actions!")

if __name__ == "__main__":
    main()
