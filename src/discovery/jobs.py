from __future__ import annotations

import os
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"

DEFAULT_ACTOR_ID = (
    "harvestapi~linkedin-profile-search"
)

RECRUITER_SEARCH_QUERY = (
    "recruiter"
)

SUPPORTED_RECRUITER_TERMS = [
    "recruiter",
    "talent acquisition",
    "talent sourcer",
    "technical sourcer",
    "technical recruiter",
    "engineering recruiter",
    "technology recruiter",
    "it recruiter",
    "technical talent acquisition",
    "talent acquisition partner",
    "talent acquisition specialist",
    "senior recruiter",
    "hiring manager",
    "engineering manager",
]


LOCATION_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "mumbai": "Mumbai",
    "hyderabad": "Hyderabad",
}


def get_apify_token() -> str:
    token = os.getenv(
        "APIFY_API_TOKEN",
        "",
    ).strip()

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN is not configured."
        )

    return token


def get_actor_id() -> str:
    actor_id = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        DEFAULT_ACTOR_ID,
    ).strip()

    return actor_id or DEFAULT_ACTOR_ID


def build_locations(
    profile: dict[str, Any],
) -> list[str]:
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

        key = value.lower()

        if key == "remote":
            continue

        mapped = LOCATION_ALIASES.get(
            key,
            value,
        )

        if mapped not in locations:
            locations.append(mapped)

    return locations


def build_search_input(
    profile: dict[str, Any],
) -> dict[str, Any]:
    locations = build_locations(profile)

    return {
        "profileScraperMode": (
            "Full + email search"
        ),
        "searchQuery": (
            RECRUITER_SEARCH_QUERY
        ),
        "locations": locations,
        "maxItems": int(
            os.getenv(
                "RECRUITER_MAX_ITEMS",
                "100",
            )
        ),
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

    print(
        f"Using Apify actor: {actor_id}"
    )

    print(
        "Apify recruiter input:"
    )

    print(run_input)

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
            "Apify recruiter discovery failed.\n"
            f"HTTP: {response.status_code}\n"
            f"Response: "
            f"{response.text[:3000]}"
        )

    payload = response.json()

    run_data = payload.get(
        "data",
        {},
    )

    dataset_id = run_data.get(
        "defaultDatasetId",
    )

    if not dataset_id:
        raise RuntimeError(
            "Apify run returned no dataset ID."
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
        timeout=300,
    )

    if not dataset_response.ok:
        raise RuntimeError(
            "Failed to retrieve Apify dataset.\n"
            f"HTTP: "
            f"{dataset_response.status_code}\n"
            f"Response: "
            f"{dataset_response.text[:3000]}"
        )

    items = dataset_response.json()

    if not isinstance(items, list):
        raise RuntimeError(
            "Apify dataset was not a list."
        )

    return [
        item
        for item in items
        if isinstance(item, dict)
    ]


def search_recruiters(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    locations = build_locations(
        profile
    )

    if not locations:
        raise RuntimeError(
            "No supported recruiter "
            "locations configured."
        )

    run_input = build_search_input(
        profile
    )

    print(
        "Generated ONE broad recruiter "
        "search request."
    )

    results = run_apify_actor(
        actor_id=get_actor_id(),
        run_input=run_input,
    )

    print(
        f"Raw recruiter records: "
        f"{len(results)}"
    )

    return results


def extract_email(
    raw: dict[str, Any],
) -> str:
    fields = [
        "email",
        "emailAddress",
        "contactEmail",
        "personalEmail",
        "workEmail",
        "professionalEmail",
    ]

    for field in fields:
        value = raw.get(field)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip().lower()

    return ""


def extract_name(
    raw: dict[str, Any],
) -> str:
    for field in [
        "name",
        "fullName",
        "full_name",
    ]:
        value = raw.get(field)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip()

    first = str(
        raw.get("firstName")
        or raw.get("first_name")
        or ""
    ).strip()

    last = str(
        raw.get("lastName")
        or raw.get("last_name")
        or ""
    ).strip()

    return f"{first} {last}".strip()


def extract_company(
    raw: dict[str, Any],
) -> str:
    for field in [
        "company",
        "companyName",
        "currentCompany",
    ]:
        value = raw.get(field)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip()

    experiences = raw.get(
        "experiences",
        [],
    )

    if isinstance(experiences, list):
        for experience in experiences:
            if not isinstance(
                experience,
                dict,
            ):
                continue

            value = (
                experience.get(
                    "companyName"
                )
                or experience.get(
                    "company"
                )
                or ""
            )

            if str(value).strip():
                return str(value).strip()

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
        value = raw.get(field)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip()

    experiences = raw.get(
        "experiences",
        [],
    )

    if isinstance(experiences, list):
        for experience in experiences:
            if not isinstance(
                experience,
                dict,
            ):
                continue

            value = (
                experience.get("title")
                or experience.get(
                    "position"
                )
                or ""
            )

            if str(value).strip():
                return str(value).strip()

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
        value = raw.get(field)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip()

        if isinstance(value, dict):
            city = str(
                value.get("city")
                or ""
            ).strip()

            country = str(
                value.get("country")
                or ""
            ).strip()

            combined = ", ".join(
                part
                for part in [
                    city,
                    country,
                ]
                if part
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
        value = raw.get(field)

        if (
            isinstance(value, str)
            and "linkedin.com" in value
        ):
            return value.strip()

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
        value = raw.get(field)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            values.append(
                value.strip()
            )

    return " ".join(values)


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
        "about": extract_about(raw),
        "source": "apify",
        "raw": raw,
    }


def is_recruiter(
    recruiter: dict[str, Any],
) -> bool:
    text = " ".join(
        [
            recruiter.get(
                "name",
                "",
            ),
            recruiter.get(
                "title",
                "",
            ),
            recruiter.get(
                "about",
                "",
            ),
        ]
    ).lower()

    return any(
        term in text
        for term in SUPPORTED_RECRUITER_TERMS
    )


def deduplicate_recruiters(
    recruiters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = set()
    result = []

    for recruiter in recruiters:
        if not is_recruiter(
            recruiter
        ):
            continue

        email = str(
            recruiter.get(
                "email",
                "",
            )
        ).strip().lower()

        linkedin = str(
            recruiter.get(
                "linkedin_url",
                "",
            )
        ).strip().lower()

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

        key = (
            email
            or linkedin
            or f"{name}|{company}"
        )

        if key == "|":
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(recruiter)

    return result
