from __future__ import annotations

import os
import random
import time
from typing import Any

import requests


APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

APIFY_ACTOR = os.getenv(
    "APIFY_RECRUITER_ACTOR",
    "harvestapi/linkedin-profile-search",
)

APIFY_BASE_URL = (
    "https://api.apify.com/v2"
)


def _actor_id() -> str:
    """
    Convert the actor identifier into the format
    expected by the Apify REST API.

    Apify accepts:
        harvestapi/linkedin-profile-search

    The API URL uses:
        harvestapi~linkedin-profile-search
    """

    return APIFY_ACTOR.replace(
        "/",
        "~",
    )


def _require_token() -> None:

    if not APIFY_API_TOKEN:
        raise RuntimeError(
            "APIFY_API_TOKEN is not configured."
        )


def _run_actor(
    actor_input: dict[str, Any],
) -> list[dict[str, Any]]:

    _require_token()

    actor_id = _actor_id()

    url = (
        f"{APIFY_BASE_URL}/acts/"
        f"{actor_id}/runs"
    )

    params = {
        "token": APIFY_API_TOKEN,
        "waitForFinish": 120,
    }

    response = requests.post(
        url,
        params=params,
        json=actor_input,
        timeout=180,
    )

    response.raise_for_status()

    payload = response.json()

    run = payload.get(
        "data",
        {},
    )

    dataset_id = run.get(
        "defaultDatasetId"
    )

    if not dataset_id:
        return []

    dataset_url = (
        f"{APIFY_BASE_URL}/datasets/"
        f"{dataset_id}/items"
    )

    dataset_response = requests.get(
        dataset_url,
        params={
            "token": APIFY_API_TOKEN,
            "clean": "true",
        },
        timeout=120,
    )

    dataset_response.raise_for_status()

    records = dataset_response.json()

    if not isinstance(
        records,
        list,
    ):
        return []

    return records


def _first(
    record: dict[str, Any],
    *keys: str,
) -> Any:

    for key in keys:

        value = record.get(
            key
        )

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


def _string(
    value: Any,
) -> str:

    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    return str(value).strip()


def _normalise_recruiter(
    record: dict[str, Any],
) -> dict[str, Any]:

    name = _first(
        record,
        "name",
        "fullName",
        "full_name",
    )

    if not name:

        first_name = _string(
            _first(
                record,
                "firstName",
                "first_name",
            )
        )

        last_name = _string(
            _first(
                record,
                "lastName",
                "last_name",
            )
        )

        name = (
            f"{first_name} {last_name}"
        ).strip()

    email = _first(
        record,
        "email",
        "emailAddress",
        "email_address",
        "workEmail",
    )

    title = _first(
        record,
        "headline",
        "title",
        "jobTitle",
        "job_title",
        "position",
    )

    company = _first(
        record,
        "company",
        "companyName",
        "company_name",
        "currentCompany",
    )

    location = _first(
        record,
        "location",
        "geoLocation",
        "geo_location",
        "city",
    )

    linkedin_url = _first(
        record,
        "linkedinUrl",
        "linkedin_url",
        "profileUrl",
        "profile_url",
        "url",
    )

    about = _first(
        record,
        "about",
        "summary",
        "description",
    )

    email = _string(
        email
    )

    return {
        "name": _string(name),
        "email": email.lower(),
        "email_valid": bool(email),
        "corporate_email": bool(email),
        "title": _string(title),
        "company": _string(company),
        "location": _string(location),
        "linkedin_url": _string(
            linkedin_url
        ),
        "about": _string(about),
        "raw": record,
    }


def _deduplicate(
    recruiters: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    seen: set[str] = set()

    result: list[
        dict[str, Any]
    ] = []

    for recruiter in recruiters:

        email = recruiter.get(
            "email",
            "",
        ).strip().lower()

        linkedin = recruiter.get(
            "linkedin_url",
            "",
        ).strip().lower()

        name = recruiter.get(
            "name",
            "",
        ).strip().lower()

        key = (
            email
            or linkedin
            or name
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        result.append(
            recruiter
        )

    return result


def search_recruiters(
    profile: dict[str, Any],
    max_results: int = 25,
) -> list[dict[str, Any]]:

    roles = profile.get(
        "targeting",
        {},
    ).get(
        "roles",
        [],
    )

    locations = profile.get(
        "targeting",
        {},
    ).get(
        "locations",
        [],
    )

    if not roles:
        roles = [
            "AI Engineer",
            "Machine Learning Engineer",
            "Generative AI Engineer",
            "LLM Engineer",
            "RAG Engineer",
        ]

    if not locations:
        locations = [
            "Remote",
            "Bengaluru",
            "Mumbai",
            "Hyderabad",
        ]

    role_terms = [
        "Technical Recruiter",
        "Technical Sourcer",
        "Engineering Recruiter",
        "Talent Acquisition",
    ]

    search_query = (
        " ".join(
            role_terms
        )
    )

    search_query += " "

    search_query += " ".join(
        roles[:8]
    )

    actor_input = {
        "profileScraperMode": (
            "Full + email search"
        ),
        "searchQuery": search_query,
        "locations": locations[:5],
        "maxItems": max_results,
        "startPage": 1,
        "takePages": 1,
    }

    print(
        "Using Apify actor: "
        f"{APIFY_ACTOR}"
    )

    print(
        "Apify input:"
    )

    print(
        actor_input
    )

    raw_records = _run_actor(
        actor_input
    )

    recruiters = [
        _normalise_recruiter(
            record
        )
        for record in raw_records
    ]

    recruiters = _deduplicate(
        recruiters
    )

    return recruiters
