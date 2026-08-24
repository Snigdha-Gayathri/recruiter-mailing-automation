from __future__ import annotations

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main() -> None:
    client_id = input("Google OAuth Client ID: ").strip()
    client_secret = input("Google OAuth Client Secret: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
    }

    config_path = Path("gmail_oauth_client.json")
    config_path.write_text(
        json.dumps(client_config, indent=2),
        encoding="utf-8",
    )

    flow = InstalledAppFlow.from_client_config(
        client_config,
        SCOPES,
    )

    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    print()
    print("=" * 70)
    print("GMAIL OAUTH SUCCESS")
    print("=" * 70)
    print()
    print("Refresh token:")
    print(credentials.refresh_token)
    print()
    print("Client ID:")
    print(client_id)
    print()
    print("Client secret:")
    print(client_secret)
    print()
    print("Save these as GitHub Actions secrets:")
    print()
    print("GMAIL_REFRESH_TOKEN")
    print("GMAIL_CLIENT_ID")
    print("GMAIL_CLIENT_SECRET")
    print("SENDER_EMAIL")
    print()
    print("=" * 70)

    config_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
