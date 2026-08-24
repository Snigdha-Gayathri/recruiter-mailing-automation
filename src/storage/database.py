from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_PATH = Path(
    os.getenv(
        "STATE_PATH",
        "data/state.json",
    )
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "version": 2,
        "created_at": utc_now(),
        "updated_at": utc_now(),

        "contacts": {},

        "outreach": [],

        "job_cache": {
            "updated_at": None,
            "jobs": [],
        },

        "statistics": {
            "discovered": 0,
            "qualified": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "apify_calls": 0,
        },
    }


def load_state() -> dict[str, Any]:
    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not STATE_PATH.exists():
        return default_state()

    try:
        with STATE_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            state = json.load(file)

        if not isinstance(
            state,
            dict,
        ):
            return default_state()

        state.setdefault(
            "contacts",
            {},
        )

        state.setdefault(
            "outreach",
            [],
        )

        state.setdefault(
            "statistics",
            {},
        )

        state.setdefault(
            "job_cache",
            {
                "updated_at": None,
                "jobs": [],
            },
        )

        return state

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return default_state()


def save_state(
    state: dict[str, Any],
) -> None:
    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    state["updated_at"] = utc_now()

    temporary_path = (
        STATE_PATH.with_suffix(
            ".tmp"
        )
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_path.replace(
        STATE_PATH
    )


def contact_key(
    recruiter: dict[str, Any],
) -> str:
    email = str(
        recruiter.get(
            "email",
            "",
        )
    ).strip().lower()

    if email:
        return f"email:{email}"

    linkedin = str(
        recruiter.get(
            "linkedin_url",
            "",
        )
    ).strip().lower()

    if linkedin:
        return (
            f"linkedin:{linkedin}"
        )

    name = str(
        recruiter.get(
            "name",
            "",
        )
    ).strip().lower()

    company = str(
        recruiter.get(
            "company",
            "",
        )
    ).strip().lower()

    return (
        f"name:{name}|company:{company}"
    )


def has_been_contacted(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> bool:
    key = contact_key(
        recruiter
    )

    contact = (
        state
        .get(
            "contacts",
            {},
        )
        .get(key)
    )

    if not contact:
        return False

    return contact.get(
        "status"
    ) == "sent"


def record_contact(
    state: dict[str, Any],
    recruiter: dict[str, Any],
    template: str,
    subject: str,
    message_id: str | None,
    status: str,
) -> None:
    key = contact_key(
        recruiter
    )

    state.setdefault(
        "contacts",
        {},
    )

    state["contacts"][key] = {
        "name": recruiter.get(
            "name"
        ),
        "email": recruiter.get(
            "email"
        ),
        "company": recruiter.get(
            "company"
        ),
        "linkedin_url": recruiter.get(
            "linkedin_url"
        ),
        "template": template,
        "subject": subject,
        "message_id": message_id,
        "status": status,
        "updated_at": utc_now(),
    }

    state.setdefault(
        "outreach",
        [],
    )

    state["outreach"].append(
        {
            "timestamp": utc_now(),
            "contact_key": key,
            "email": recruiter.get(
                "email"
            ),
            "company": recruiter.get(
                "company"
            ),
            "template": template,
            "subject": subject,
            "message_id": message_id,
            "status": status,
        }
    )


def increment_stat(
    state: dict[str, Any],
    key: str,
    amount: int = 1,
) -> None:
    statistics = state.setdefault(
        "statistics",
        {},
    )

    statistics[key] = (
        statistics.get(
            key,
            0,
        )
        + amount
    )


def job_cache_is_fresh(
    state: dict[str, Any],
    ttl_hours: int,
) -> bool:
    updated_at = (
        state
        .get(
            "job_cache",
            {},
        )
        .get(
            "updated_at"
        )
    )

    jobs = (
        state
        .get(
            "job_cache",
            {},
        )
        .get(
            "jobs",
            []
        )
    )

    if not updated_at or not jobs:
        return False

    try:
        updated = datetime.fromisoformat(
            updated_at
        )

        age = (
            datetime.now(
                timezone.utc
            )
            - updated
        )

        return (
            age.total_seconds()
            < ttl_hours * 3600
        )

    except ValueError:
        return False


def get_cached_jobs(
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    return (
        state
        .get(
            "job_cache",
            {},
        )
        .get(
            "jobs",
            []
        )
    )


def set_job_cache(
    state: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> None:
    state["job_cache"] = {
        "updated_at": utc_now(),
        "jobs": jobs,
    }
