from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


DEFAULT_STATE: dict[str, Any] = {
    "contacted_emails": [],
    "contacted_linkedin_urls": [],
    "seen_recruiters": [],
    "templates_used": {},

    "runs": 0,

    "emails_sent": 0,
    "emails_failed": 0,

    "linkedin_packages_sent": 0,

    "apify_calls": 0,
    "discovered": 0,
    "qualified": 0,

    "job_cache": [],
    "job_cache_timestamp": 0,

    "statistics": {},

    "contacts": [],
}


def _state_path() -> Path:
    return Path(
        os.getenv(
            "STATE_PATH",
            "data/state.json",
        )
    )


def load_state() -> dict[str, Any]:
    path = _state_path()

    if not path.exists():
        return dict(
            DEFAULT_STATE
        )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return dict(
            DEFAULT_STATE
        )

    if not isinstance(
        data,
        dict,
    ):
        return dict(
            DEFAULT_STATE
        )

    state = dict(
        DEFAULT_STATE
    )

    state.update(
        data
    )

    if not isinstance(
        state.get(
            "contacts"
        ),
        list,
    ):
        state["contacts"] = []

    if not isinstance(
        state.get(
            "contacted_emails"
        ),
        list,
    ):
        state["contacted_emails"] = []

    if not isinstance(
        state.get(
            "contacted_linkedin_urls"
        ),
        list,
    ):
        state["contacted_linkedin_urls"] = []

    if not isinstance(
        state.get(
            "seen_recruiters"
        ),
        list,
    ):
        state["seen_recruiters"] = []

    if not isinstance(
        state.get(
            "statistics"
        ),
        dict,
    ):
        state["statistics"] = {}

    if not isinstance(
        state.get(
            "templates_used"
        ),
        dict,
    ):
        state["templates_used"] = {}

    return state


def save_state(
    state: dict[str, Any],
) -> None:
    path = _state_path()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def increment_run(
    state: dict[str, Any],
) -> None:
    state["runs"] = int(
        state.get(
            "runs",
            0,
        )
    ) + 1


def increment_stat(
    state: dict[str, Any],
    name: str,
    amount: int = 1,
) -> None:
    statistics = state.setdefault(
        "statistics",
        {},
    )

    statistics[name] = (
        int(
            statistics.get(
                name,
                0,
            )
        )
        + amount
    )

    state[name] = (
        int(
            state.get(
                name,
                0,
            )
        )
        + amount
    )


def mark_recruiter_seen(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> None:
    identifier = (
        recruiter.get("linkedinUrl")
        or recruiter.get("publicIdentifier")
        or recruiter.get("id")
    )

    if not identifier:
        return

    seen = state.setdefault(
        "seen_recruiters",
        [],
    )

    if not isinstance(
        seen,
        list,
    ):
        seen = []
        state["seen_recruiters"] = seen

    identifier = str(
        identifier
    ).strip()

    if (
        identifier
        and identifier not in seen
    ):
        seen.append(
            identifier
        )


def has_been_contacted(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> bool:
    email = str(
        recruiter.get(
            "email",
            "",
        )
        or ""
    ).strip().lower()

    linkedin_url = str(
        recruiter.get(
            "linkedinUrl",
            "",
        )
        or ""
    ).strip().lower()

    contacted_emails = {
        str(value).strip().lower()
        for value in state.get(
            "contacted_emails",
            [],
        )
        if value
    }

    contacted_linkedin = {
        str(value).strip().lower()
        for value in state.get(
            "contacted_linkedin_urls",
            [],
        )
        if value
    }

    # If an email is now available, an old LinkedIn-only package
    # should NOT permanently prevent email outreach.
    #
    # Email route:
    if email:
        return email in contacted_emails

    # No email:
    # use LinkedIn URL to avoid sending the same package repeatedly.
    if linkedin_url:
        return (
            linkedin_url
            in contacted_linkedin
        )

    return False


def recruiter_has_been_contacted(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> bool:
    return has_been_contacted(
        state,
        recruiter,
    )


def record_contact(
    state: dict[str, Any],
    recruiter: dict[str, Any],
    template: str,
    subject: str,
    message_id: str | None,
    status: str,
    outreach_channel: str = "email",
) -> None:
    email = str(
        recruiter.get(
            "email",
            "",
        )
        or ""
    ).strip().lower()

    linkedin_url = str(
        recruiter.get(
            "linkedinUrl",
            "",
        )
        or ""
    ).strip()

    if status in {
        "sent",
        "linkedin_package_sent",
    }:
        if (
            outreach_channel == "email"
            and email
        ):
            emails = state.setdefault(
                "contacted_emails",
                [],
            )

            if email not in emails:
                emails.append(
                    email
                )

        if (
            outreach_channel
            == "linkedin"
            and linkedin_url
        ):
            urls = state.setdefault(
                "contacted_linkedin_urls",
                [],
            )

            if linkedin_url not in urls:
                urls.append(
                    linkedin_url
                )

    contacts = state.setdefault(
        "contacts",
        [],
    )

    if not isinstance(
        contacts,
        list,
    ):
        contacts = []
        state["contacts"] = contacts

    contacts.append(
        {
            "name": recruiter.get(
                "name",
                "",
            ),

            "email": email,

            "linkedin_url": linkedin_url,

            "company": recruiter.get(
                "company",
                "",
            ),

            "title": recruiter.get(
                "title",
                "",
            ),

            "template": template,

            "subject": subject,

            "message_id": message_id,

            "status": status,

            "outreach_channel": (
                outreach_channel
            ),
        }
    )


def record_template_usage(
    state: dict[str, Any],
    template_name: str,
) -> None:
    templates = state.setdefault(
        "templates_used",
        {},
    )

    templates[template_name] = (
        int(
            templates.get(
                template_name,
                0,
            )
        )
        + 1
    )


def get_cached_jobs(
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    jobs = state.get(
        "job_cache",
        [],
    )

    # Handle the old state format:
    # {"updated_at": ..., "jobs": [...]}
    if isinstance(
        jobs,
        dict,
    ):
        jobs = jobs.get(
            "jobs",
            [],
        )

    if not isinstance(
        jobs,
        list,
    ):
        return []

    return [
        job
        for job in jobs
        if isinstance(
            job,
            dict,
        )
    ]


def set_job_cache(
    state: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> None:
    state["job_cache"] = [
        job
        for job in jobs
        if isinstance(
            job,
            dict,
        )
    ]

    state["job_cache_timestamp"] = (
        time.time()
    )
