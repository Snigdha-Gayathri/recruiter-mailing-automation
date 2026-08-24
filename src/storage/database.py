from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_STATE = {
    "contacted_emails": [],
    "contacted_linkedin_urls": [],
    "seen_recruiters": [],
    "templates_used": {},
    "runs": 0,
    "emails_sent": 0,
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
        return dict(DEFAULT_STATE)

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
        return dict(DEFAULT_STATE)

    if not isinstance(data, dict):
        return dict(DEFAULT_STATE)

    state = dict(DEFAULT_STATE)
    state.update(data)

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
        state.get("runs", 0)
    ) + 1


def mark_recruiter_seen(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> None:
    url = (
        recruiter.get("linkedinUrl")
        or recruiter.get("publicIdentifier")
        or recruiter.get("id")
    )

    if not url:
        return

    seen = state.setdefault(
        "seen_recruiters",
        [],
    )

    if url not in seen:
        seen.append(url)


def recruiter_has_been_contacted(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> bool:
    email = (
        recruiter.get("_match", {}).get("email")
        or recruiter.get("email")
        or ""
    )

    linkedin_url = (
        recruiter.get("linkedinUrl")
        or ""
    )

    contacted_emails = {
        str(value).lower()
        for value in state.get(
            "contacted_emails",
            [],
        )
    }

    contacted_linkedin = {
        str(value).lower()
        for value in state.get(
            "contacted_linkedin_urls",
            [],
        )
    }

    if email and str(email).lower() in contacted_emails:
        return True

    if (
        linkedin_url
        and str(linkedin_url).lower()
        in contacted_linkedin
    ):
        return True

    return False


def mark_contacted(
    state: dict[str, Any],
    recruiter: dict[str, Any],
) -> None:
    email = (
        recruiter.get("_match", {}).get("email")
        or recruiter.get("email")
    )

    linkedin_url = recruiter.get(
        "linkedinUrl"
    )

    if email:
        state.setdefault(
            "contacted_emails",
            [],
        ).append(email)

    if linkedin_url:
        state.setdefault(
            "contacted_linkedin_urls",
            [],
        ).append(linkedin_url)

    state["emails_sent"] = int(
        state.get("emails_sent", 0)
    ) + 1


def record_template_usage(
    state: dict[str, Any],
    template_name: str,
) -> None:
    templates = state.setdefault(
        "templates_used",
        {},
    )

    templates[template_name] = (
        int(templates.get(template_name, 0))
        + 1
    )
