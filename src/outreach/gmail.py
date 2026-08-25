from __future__ import annotations

import base64
import os
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


def get_gmail_credentials() -> Credentials:
    refresh_token = os.getenv(
        "GMAIL_REFRESH_TOKEN"
    )

    client_id = os.getenv(
        "GMAIL_CLIENT_ID"
    )

    client_secret = os.getenv(
        "GMAIL_CLIENT_SECRET"
    )

    if not refresh_token:
        raise RuntimeError(
            "GMAIL_REFRESH_TOKEN is not configured."
        )

    if not client_id:
        raise RuntimeError(
            "GMAIL_CLIENT_ID is not configured."
        )

    if not client_secret:
        raise RuntimeError(
            "GMAIL_CLIENT_SECRET is not configured."
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=(
            "https://oauth2.googleapis.com/token"
        ),
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES,
    )

    credentials.refresh(
        Request()
    )

    return credentials


def create_gmail_service():
    credentials = get_gmail_credentials()

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def create_message(
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    attachment_path: str | None = None,
) -> dict:
    message = EmailMessage()

    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(
        body
    )

    if attachment_path:
        path = Path(
            attachment_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Attachment not found: {path}"
            )

        with path.open(
            "rb"
        ) as file:
            attachment_bytes = file.read()

        suffix = (
            path.suffix.lower()
        )

        if suffix == ".pdf":
            maintype = "application"
            subtype = "pdf"
        else:
            maintype = "application"
            subtype = "octet-stream"

        message.add_attachment(
            attachment_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )

    encoded = (
        base64.urlsafe_b64encode(
            message.as_bytes()
        )
        .decode()
    )

    return {
        "raw": encoded
    }


def send_email(
    recipient: str,
    subject: str,
    body: str,
    attachment_path: str | None = None,
) -> str:
    sender = os.getenv(
        "SENDER_EMAIL"
    )

    if not sender:
        raise RuntimeError(
            "SENDER_EMAIL is not configured."
        )

    service = create_gmail_service()

    message = create_message(
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=body,
        attachment_path=attachment_path,
    )

    result = (
        service
        .users()
        .messages()
        .send(
            userId="me",
            body=message,
        )
        .execute()
    )

    message_id = result.get(
        "id"
    )

    if not message_id:
        raise RuntimeError(
            "Gmail returned no message ID."
        )

    return message_id
