from __future__ import annotations

import re
from typing import Any


FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "protonmail.com"
}


def normalize_email(email: str) -> str:
    return (
        email
        or ""
    ).strip().lower()


def is_valid_email(email: str) -> bool:
    email = normalize_email(email)

    if not email:
        return False

    pattern = (
        r"^[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}$"
    )

    return bool(
        re.match(pattern, email)
    )


def get_domain(email: str) -> str:
    email = normalize_email(email)

    if "@" not in email:
        return ""

    return email.split("@", 1)[1]


def is_corporate_email(email: str) -> bool:
    domain = get_domain(email)

    if not domain:
        return False

    return domain not in FREE_EMAIL_DOMAINS


def email_quality_score(email: str) -> int:
    if not is_valid_email(email):
        return 0

    if is_corporate_email(email):
        return 100

    return 50


def enrich_recruiter(
    recruiter: dict[str, Any]
) -> dict[str, Any]:
    email = normalize_email(
        recruiter.get("email", "")
    )

    recruiter["email"] = email
    recruiter["email_valid"] = is_valid_email(email)
    recruiter["corporate_email"] = is_corporate_email(email)
    recruiter["email_quality_score"] = email_quality_score(email)

    return recruiter
