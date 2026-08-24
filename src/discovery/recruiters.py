from __future__ import annotations

import osfrom __future__ import annotations

import os
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"

DEFAULT_ACTOR_ID = "harvestapi~linkedin-profile-search"

RECRUITER_TITLES = [
    "Technical Recruiter",
    "Engineering Recruiter",
    "Technical Sourcer",
    "Talent Sourcer",
    "Talent Acquisition Partner",
    "Talent Acquisition Specialist",
    "Technical Talent Acquisition",
    "Engineering Talent Acquisition",
    "IT Recruiter",
    "Technology Recruiter",
    "Recruiter",
]

DEFAULT_LOCATIONS = [
    "Bengaluru",
    "Mumbai",
    "Hyderabad",
]


def get_apify_token() -> str:
    token = os.getenv("APIFY_API_TOKEN", "").strip()

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN is not configured."
        )

    return token


def get_actor_id() -> str:
    return os.getenv(
        "APIFY_RECRUITER_ACTOR",
        DEFAULT_ACTOR_ID,
    ).strip() or DEFAULT_ACTOR_ID


def get_search_location(
    profile: dict[str, Any],
) -> str:
    configured = (
        profile
        .get("targeting", {})
        .get("locations", [])
    )

    locations = []

    for location in configured:
        value = str(location).strip()

        if not value:
            continue

        if value.lower() == "remote":
            continue

        if value not in locations:
            locations.append(value)

    if not locations:
        locations = DEFAULT_LOCATIONS

    # The workflow runs hourly.
    # Rotate locations without making additional Apify calls.
    hour = __import__("datetime").datetime.utcnow().hour

    return locations[hour % len(locations)]


def get_recruiter_titles(
    profile: dict[str, Any],
) -> list[str]:
    configured = (
        profile
        .get("recruiter_targets", {})
        .get("preferred_titles", [])
    )

    configured_clean = []

    for title in configured:
        value = str(title).strip()

        if value and value not in configured_clean:
            configured_clean.append(value)

    if not configured_clean:
        return RECRUITER_TITLES

    preferred = []

    for title in RECRUITER_TITLES:
        if title in configured_clean:
            preferred.append(title)

    for title in configured_clean:
        if title not in preferred:
            preferred.append(title)

    return preferred[:20]


def build_run_input(
    profile: dict[str, Any],
) -> dict[str, Any]:
    max_items_raw = os.getenv(
        "RECRUITER_MAX_ITEMS",
        "25",
    ).strip()

    try:
        max_items = int(max_items_raw)
    except ValueError:
        max_items = 25

    max_items = max(
        1,
        min(
            max_items,
            25,
        ),
    )

    return {
        "profileScraperMode": "Full + email search",
        "currentJobTitles": get_recruiter_titles(
            profile
        ),
        "locations": [
            get_search_location(profile)
        ],
        "maxItems": max_items,
        "startPage": 1,
        "takePages": 1,
    }


def run_apify_actor(
    actor_id: str,
    run_input: dict[str, Any],
) -> list[dict[str, Any]]:
    token = get_apify_token()

    encoded_actor_id = actor_id.replace(
        "/",
        "~",
    )

    url = (
        f"{APIFY_API_BASE}/acts/"
        f"{encoded_actor_id}/runs"
    )

    response = requests.post(
        url,
        params={
            "token": token,
            "waitForFinish": 120,
        },
        json=run_input,
        timeout=300,
    )

    if not response.ok:
        raise RuntimeError(
            "Apify recruiter discovery failed: "
            f"HTTP {response.status_code}: "
            f"{response.text[:2000]}"
        )

    payload = response.json()

    run_data = payload.get("data", {})

    dataset_id = run_data.get(
        "defaultDatasetId"
    )

    if not dataset_id:
        raise RuntimeError(
            "Apify recruiter run returned no dataset ID."
        )

    dataset_url = (
        f"{APIFY_API_BASE}/datasets/"
        f"{dataset_id}/items"
    )

    dataset_response = requests.get(
        dataset_url,
        params={
            "token": token,
            "clean": "true",
        },
        timeout=300,
    )

    if not dataset_response.ok:
        raise RuntimeError(
            "Failed to read recruiter dataset: "
            f"HTTP {dataset_response.status_code}: "
            f"{dataset_response.text[:2000]}"
        )

    items = dataset_response.json()

    if not isinstance(items, list):
        raise RuntimeError(
            "Recruiter dataset was not a list."
        )

    print(
        f"Apify dataset: {dataset_id}"
    )

    print(
        f"Results: {len(items)}"
    )

    return items


def search_recruiters(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    actor_id = get_actor_id()

    run_input = build_run_input(
        profile
    )

    print(
        "Recruiter search strategy: "
        "ONE Apify call"
    )

    print(
        "Recruiter actor: "
        f"{actor_id}"
    )

    print(
        "Recruiter location: "
        f"{run_input['locations'][0]}"
    )

    print(
        "Recruiter title filters:"
    )

    for title in run_input[
        "currentJobTitles"
    ]:
        print(
            f"  - {title}"
        )

    print(
        "Apify input:"
    )

    print(run_input)

    return run_apify_actor(
        actor_id,
        run_input,
    )


def _first_string(
    raw: dict[str, Any],
    fields: list[str],
) -> str:
    for field in fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

    return ""


def extract_email(
    raw: dict[str, Any],
) -> str:
    return _first_string(
        raw,
        [
            "email",
            "emailAddress",
            "contactEmail",
            "professionalEmail",
            "workEmail",
            "personalEmail",
        ],
    ).lower()


def extract_name(
    raw: dict[str, Any],
) -> str:
    name = _first_string(
        raw,
        [
            "fullName",
            "full_name",
            "name",
        ],
    )

    if name:
        return name

    first = _first_string(
        raw,
        [
            "firstName",
            "first_name",
        ],
    )

    last = _first_string(
        raw,
        [
            "lastName",
            "last_name",
        ],
    )

    return f"{first} {last}".strip()


def extract_title(
    raw: dict[str, Any],
) -> str:
    return _first_string(
        raw,
        [
            "headline",
            "jobTitle",
            "title",
            "position",
        ],
    )


def extract_company(
    raw: dict[str, Any],
) -> str:
    return _first_string(
        raw,
        [
            "companyName",
            "currentCompany",
            "company",
        ],
    )


def extract_location(
    raw: dict[str, Any],
) -> str:
    value = raw.get("location")

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        city = str(
            value.get("city", "")
        ).strip()

        country = str(
            value.get("country", "")
        ).strip()

        return ", ".join(
            part
            for part in [
                city,
                country,
            ]
            if part
        )

    return _first_string(
        raw,
        [
            "locationName",
            "city",
        ],
    )


def extract_linkedin_url(
    raw: dict[str, Any],
) -> str:
    value = _first_string(
        raw,
        [
            "linkedinUrl",
            "linkedin_url",
            "profileUrl",
            "url",
        ],
    )

    if "linkedin.com" in value:
        return value

    return ""


def normalize_recruiter(
    raw: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": extract_name(raw),
        "email": extract_email(raw),
        "title": extract_title(raw),
        "company": extract_company(raw),
        "location": extract_location(raw),
        "linkedin_url": extract_linkedin_url(raw),
        "about": _first_string(
            raw,
            [
                "about",
                "summary",
            ],
        ),
        "source": "apify",
        "raw": raw,
    }


def deduplicate_recruiters(
    recruiters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = set()
    result = []

    for recruiter in recruiters:
        email = recruiter.get(
            "email",
            "",
        ).lower()

        linkedin = recruiter.get(
            "linkedin_url",
            "",
        ).lower()

        name = recruiter.get(
            "name",
            "",
        ).lower()

        company = recruiter.get(
            "company",
            "",
        ).lower()

        key = (
            email
            or linkedin
            or f"{name}|{company}"
        )

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(recruiter)

    return result
from datetime import datetime, timezone
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"

DEFAULT_ACTOR_ID = "harvestapi~linkedin-profile-search"

DEFAULT_MAX_ITEMS = 25

SEARCH_FOCUSES = [
    "Technical Recruiter",
    "Technical Talent Acquisition",
    "Talent Acquisition Partner",
    "Talent Acquisition Specialist",
    "Technical Sourcer",
    "Talent Sourcer",
    "Engineering Recruiter",
    "IT Recruiter",
    "Technology Recruiter",
    "Senior Recruiter",
    "Recruiter",
    "Hiring Manager",
    "Engineering Manager",
]

DEFAULT_LOCATIONS = [
    "Bangalore",
    "Bengaluru",
    "Mumbai",
    "Hyderabad",
]


def get_apify_token() -> str:
    token = os.getenv(
        "APIFY_API_TOKEN",
        "",
    ).strip()

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN environment variable is not configured."
        )

    return token


def get_actor_id() -> str:
    actor_id = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        DEFAULT_ACTOR_ID,
    ).strip()

    if not actor_id:
        return DEFAULT_ACTOR_ID

    return actor_id


def get_search_focus() -> str:
    configured_index = os.getenv(
        "RECRUITER_SEARCH_INDEX",
        "",
    ).strip()

    if configured_index.isdigit():
        index = int(
            configured_index
        )
    else:
        current_hour = datetime.now(
            timezone.utc
        ).hour

        index = current_hour % len(
            SEARCH_FOCUSES
        )

    return SEARCH_FOCUSES[
        index % len(SEARCH_FOCUSES)
    ]


def get_search_location(
    profile: dict[str, Any],
) -> str:

    configured_locations = (
        profile
        .get(
            "targeting",
            {},
        )
        .get(
            "locations",
            [],
        )
    )

    locations: list[str] = []

    for location in configured_locations:

        value = str(
            location
        ).strip()

        if not value:
            continue

        if value.lower() == "remote":
            continue

        if value not in locations:
            locations.append(
                value
            )

    if not locations:
        locations = DEFAULT_LOCATIONS

    current_hour = datetime.now(
        timezone.utc
    ).hour

    return locations[
        current_hour % len(locations)
    ]


def build_search_query(
    profile: dict[str, Any],
) -> str:

    return get_search_focus()


def build_run_input(
    profile: dict[str, Any],
) -> dict[str, Any]:

    max_items_raw = os.getenv(
        "RECRUITER_MAX_ITEMS",
        str(DEFAULT_MAX_ITEMS),
    ).strip()

    try:
        max_items = int(
            max_items_raw
        )
    except ValueError:
        max_items = DEFAULT_MAX_ITEMS

    if max_items <= 0:
        max_items = DEFAULT_MAX_ITEMS

    if max_items > 25:
        max_items = 25

    return {
        "profileScraperMode": (
            "Full + email search"
        ),
        "searchQuery": build_search_query(
            profile
        ),
        "locations": [
            get_search_location(
                profile
            )
        ],
        "maxItems": max_items,
        "startPage": 1,
        "takePages": 1,
    }


def run_apify_actor(
    actor_id: str,
    run_input: dict[str, Any],
    timeout_seconds: int = 300,
) -> list[dict[str, Any]]:

    token = get_apify_token()

    encoded_actor_id = actor_id.replace(
        "/",
        "~",
    )

    url = (
        f"{APIFY_API_BASE}/acts/"
        f"{encoded_actor_id}/runs"
    )

    print(
        f"Using Apify actor: {actor_id}"
    )

    print(
        "Apify input:"
    )

    print(
        run_input
    )

    response = requests.post(
        url,
        params={
            "token": token,
            "waitForFinish": 120,
        },
        json=run_input,
        timeout=timeout_seconds,
    )

    if not response.ok:
        raise RuntimeError(
            "Apify actor request failed.\n"
            f"HTTP status: "
            f"{response.status_code}\n"
            f"Actor: {actor_id}\n"
            f"Response: "
            f"{response.text[:3000]}"
        )

    payload = response.json()

    run_data = payload.get(
        "data",
        {},
    )

    dataset_id = run_data.get(
        "defaultDatasetId"
    )

    if not dataset_id:
        raise RuntimeError(
            "Apify run completed without "
            "a dataset ID.\n"
            f"Response: {payload}"
        )

    print(
        f"Apify dataset: {dataset_id}"
    )

    dataset_url = (
        f"{APIFY_API_BASE}/datasets/"
        f"{dataset_id}/items"
    )

    dataset_response = requests.get(
        dataset_url,
        params={
            "token": token,
            "clean": "true",
        },
        timeout=timeout_seconds,
    )

    if not dataset_response.ok:
        raise RuntimeError(
            "Failed to retrieve "
            "Apify dataset.\n"
            f"HTTP status: "
            f"{dataset_response.status_code}\n"
            f"Response: "
            f"{dataset_response.text[:3000]}"
        )

    items = dataset_response.json()

    if not isinstance(
        items,
        list,
    ):
        raise RuntimeError(
            "Apify dataset response "
            "was not a list."
        )

    print(
        f"Results: {len(items)}"
    )

    return items


def search_recruiters(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:

    actor_id = get_actor_id()

    run_input = build_run_input(
        profile
    )

    print(
        "Recruiter search strategy: "
        "ONE Apify call"
    )

    print(
        f"Search focus: "
        f"{run_input['searchQuery']}"
    )

    print(
        f"Search location: "
        f"{run_input['locations'][0]}"
    )

    print(
        f"Max recruiter records: "
        f"{run_input['maxItems']}"
    )

    return run_apify_actor(
        actor_id=actor_id,
        run_input=run_input,
    )


def extract_email(
    raw: dict[str, Any],
) -> str:

    possible_fields = [
        "email",
        "emailAddress",
        "contactEmail",
        "personalEmail",
        "workEmail",
        "professionalEmail",
    ]

    for field in possible_fields:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip().lower()

            if value:
                return value

    return ""


def extract_name(
    raw: dict[str, Any],
) -> str:

    for field in [
        "name",
        "fullName",
        "full_name",
    ]:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                return value

    first_name = (
        raw.get(
            "firstName"
        )
        or raw.get(
            "first_name"
        )
        or ""
    )

    last_name = (
        raw.get(
            "lastName"
        )
        or raw.get(
            "last_name"
        )
        or ""
    )

    return (
        f"{first_name} {last_name}"
    ).strip()


def extract_company(
    raw: dict[str, Any],
) -> str:

    for field in [
        "company",
        "companyName",
        "currentCompany",
    ]:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                return value

    experiences = raw.get(
        "experiences",
        [],
    )

    if isinstance(
        experiences,
        list,
    ):

        for experience in experiences:

            if not isinstance(
                experience,
                dict,
            ):
                continue

            company = (
                experience.get(
                    "companyName"
                )
                or experience.get(
                    "company"
                )
                or ""
            )

            if company:
                return str(
                    company
                ).strip()

    return ""


def extract_title(
    raw: dict[str, Any],
) -> str:

    for field in [
        "headline",
        "title",
        "position",
        "jobTitle",
    ]:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                return value

    experiences = raw.get(
        "experiences",
        [],
    )

    if isinstance(
        experiences,
        list,
    ):

        for experience in experiences:

            if not isinstance(
                experience,
                dict,
            ):
                continue

            title = (
                experience.get(
                    "title"
                )
                or experience.get(
                    "position"
                )
                or ""
            )

            if title:
                return str(
                    title
                ).strip()

    return ""


def extract_location(
    raw: dict[str, Any],
) -> str:

    for field in [
        "location",
        "geoLocation",
        "city",
        "locationName",
    ]:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                return value

        if isinstance(
            value,
            dict,
        ):

            city = (
                value.get(
                    "city"
                )
                or ""
            )

            country = (
                value.get(
                    "country"
                )
                or ""
            )

            combined = (
                f"{city}, {country}"
            ).strip(
                ", "
            )

            if combined:
                return combined

    return ""


def extract_linkedin_url(
    raw: dict[str, Any],
) -> str:

    for field in [
        "linkedinUrl",
        "linkedin_url",
        "profileUrl",
        "url",
    ]:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if "linkedin.com" in value:
                return value

    return ""


def extract_about(
    raw: dict[str, Any],
) -> str:

    values = []

    for field in [
        "about",
        "summary",
        "headline",
    ]:

        value = raw.get(
            field
        )

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                values.append(
                    value
                )

    return " ".join(
        values
    )


def normalize_recruiter(
    raw: dict[str, Any],
) -> dict[str, Any]:

    return {
        "name": extract_name(
            raw
        ),
        "email": extract_email(
            raw
        ),
        "title": extract_title(
            raw
        ),
        "company": extract_company(
            raw
        ),
        "location": extract_location(
            raw
        ),
        "linkedin_url": (
            extract_linkedin_url(
                raw
            )
        ),
        "about": extract_about(
            raw
        ),
        "source": "apify",
        "raw": raw,
    }


def deduplicate_recruiters(
    recruiters: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:

    seen = set()

    result = []

    for recruiter in recruiters:

        email = (
            recruiter
            .get(
                "email",
                "",
            )
            .strip()
            .lower()
        )

        linkedin = (
            recruiter
            .get(
                "linkedin_url",
                "",
            )
            .strip()
            .lower()
        )

        name = (
            recruiter
            .get(
                "name",
                "",
            )
            .strip()
            .lower()
        )

        company = (
            recruiter
            .get(
                "company",
                "",
            )
            .strip()
            .lower()
        )

        key = (
            email
            or linkedin
            or (
                f"{name}|{company}"
                if name or company
                else ""
            )
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            recruiter
        )

    return result
