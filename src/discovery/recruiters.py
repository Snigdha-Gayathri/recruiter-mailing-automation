from __future__ import annotations

import os
import re
from typing import Any

import requests


APIFY_API_TOKEN = os.getenv(
    "APIFY_API_TOKEN",
    "",
)

APIFY_ACTOR = os.getenv(
    "APIFY_RECRUITER_ACTOR",
    "harvestapi/linkedin-profile-search",
)

APIFY_BASE_URL = "https://api.apify.com/v2"


def _actor_id() -> str:
    return APIFY_ACTOR.replace("/", "~")


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

    response = requests.post(
        url,
        params={
            "token": APIFY_API_TOKEN,
            "waitForFinish": 120,
        },
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

    if not isinstance(records, list):
        return []

    return records


def _first(
    record: dict[str, Any],
    *keys: str,
) -> Any:
    for key in keys:
        value = record.get(key)

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

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _normalise_text(
    value: Any,
) -> str:
    text = _string(value)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _extract_email(
    record: dict[str, Any],
) -> str:
    direct_email = _first(
        record,
        "email",
        "emailAddress",
        "email_address",
        "workEmail",
    )

    if isinstance(
        direct_email,
        str,
    ):
        return direct_email.strip().lower()

    emails = record.get(
        "emails",
        [],
    )

    if isinstance(
        emails,
        list,
    ):
        for item in emails:
            if isinstance(
                item,
                str,
            ):
                value = item.strip().lower()

                if value:
                    return value

            elif isinstance(
                item,
                dict,
            ):
                value = _first(
                    item,
                    "email",
                    "address",
                    "value",
                )

                value = _string(
                    value
                ).lower()

                if value:
                    return value

    return ""


def _extract_location(
    record: dict[str, Any],
) -> str:
    location = record.get(
        "location"
    )

    if isinstance(
        location,
        str,
    ):
        return location.strip()

    if isinstance(
        location,
        dict,
    ):
        parsed = location.get(
            "parsed",
            {},
        )

        if isinstance(
            parsed,
            dict,
        ):
            parsed_text = _first(
                parsed,
                "text",
            )

            if parsed_text:
                return _string(
                    parsed_text
                )

            city = _string(
                parsed.get(
                    "city"
                )
            )

            state = _string(
                parsed.get(
                    "state"
                )
            )

            country = _string(
                parsed.get(
                    "country"
                )
            )

            return ", ".join(
                value
                for value in (
                    city,
                    state,
                    country,
                )
                if value
            )

        linkedin_text = _first(
            location,
            "linkedinText",
            "text",
        )

        if linkedin_text:
            return _string(
                linkedin_text
            )

    return _string(
        _first(
            record,
            "city",
            "locationText",
        )
    )


def _extract_current_position(
    record: dict[str, Any],
) -> dict[str, Any]:
    positions = record.get(
        "currentPosition",
        []
    )

    if isinstance(
        positions,
        dict,
    ):
        return positions

    if isinstance(
        positions,
        list,
    ):
        for position in positions:
            if isinstance(
                position,
                dict,
            ):
                return position

    return {}


def _extract_company(
    record: dict[str, Any],
) -> str:
    current_position = _extract_current_position(
        record
    )

    company = current_position.get(
        "company"
    )

    if isinstance(
        company,
        dict,
    ):
        name = _first(
            company,
            "name",
            "companyName",
        )

        if name:
            return _string(
                name
            )

    company_name = _first(
        current_position,
        "companyName",
        "company_name",
    )

    if company_name:
        return _string(
            company_name
        )

    direct_company = _first(
        record,
        "company",
        "companyName",
        "company_name",
        "currentCompany",
    )

    if isinstance(
        direct_company,
        dict,
    ):
        return _string(
            _first(
                direct_company,
                "name",
                "companyName",
            )
        )

    return _string(
        direct_company
    )


def _extract_title(
    record: dict[str, Any],
) -> str:
    current_position = _extract_current_position(
        record
    )

    position = _first(
        current_position,
        "position",
        "title",
        "jobTitle",
    )

    if position:
        return _string(
            position
        )

    return _string(
        _first(
            record,
            "headline",
            "title",
            "jobTitle",
            "job_title",
            "occupation",
        )
    )


def _extract_current_description(
    record: dict[str, Any],
) -> str:
    current_position = _extract_current_position(
        record
    )

    return _string(
        _first(
            current_position,
            "description",
        )
    )


def _extract_company_metadata(
    record: dict[str, Any],
) -> dict[str, Any]:
    current_position = _extract_current_position(
        record
    )

    company = current_position.get(
        "company"
    )

    if not isinstance(
        company,
        dict,
    ):
        return {}

    return company


def _extract_recruiter_text(
    record: dict[str, Any],
) -> str:
    current_position = _extract_current_position(
        record
    )

    company = _extract_company_metadata(
        record
    )

    fields = [
        record.get(
            "headline"
        ),
        record.get(
            "about"
        ),
        record.get(
            "topSkills"
        ),
        current_position.get(
            "position"
        ),
        current_position.get(
            "description"
        ),
        current_position.get(
            "location"
        ),
        company.get(
            "name"
        ),
        company.get(
            "tagline"
        ),
        company.get(
            "description"
        ),
        company.get(
            "industries"
        ),
        company.get(
            "specialities"
        ),
    ]

    flattened: list[str] = []

    for field in fields:
        if isinstance(
            field,
            list,
        ):
            flattened.extend(
                _string(item)
                for item in field
                if item
            )
        elif isinstance(
            field,
            dict,
        ):
            flattened.extend(
                _string(value)
                for value in field.values()
                if value
            )
        elif field:
            flattened.append(
                _string(field)
            )

    return _normalise_text(
        " ".join(
            flattened
        )
    )


def _is_valid_email(
    email: str,
) -> bool:
    if not email:
        return False

    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email,
        )
    )


def _normalise_recruiter(
    record: dict[str, Any],
) -> dict[str, Any]:
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

    name = _string(
        _first(
            record,
            "name",
            "fullName",
            "full_name",
        )
    )

    if not name:
        name = (
            f"{first_name} {last_name}"
        ).strip()

    email = _extract_email(
        record
    )

    location = _extract_location(
        record
    )

    title = _extract_title(
        record
    )

    company = _extract_company(
        record
    )

    linkedin_url = _string(
        _first(
            record,
            "linkedinUrl",
            "linkedin_url",
            "profileUrl",
            "profile_url",
            "url",
        )
    )

    about = _string(
        _first(
            record,
            "about",
            "summary",
            "description",
        )
    )

    current_position = _extract_current_position(
        record
    )

    company_metadata = _extract_company_metadata(
        record
    )

    recruiter_text = _extract_recruiter_text(
        record
    )

    return {
        "name": name,
        "email": email,
        "email_valid": _is_valid_email(
            email
        ),
        "corporate_email": _is_valid_email(
            email
        ),
        "title": title,
        "company": company,
        "location": location,
        "linkedin_url": linkedin_url,
        "about": about,
        "current_position": current_position,
        "company_metadata": company_metadata,
        "recruiter_text": recruiter_text,
        "hiring": bool(
            record.get(
                "hiring",
                False,
            )
        ),
        "open_to_work": bool(
            record.get(
                "openToWork",
                False,
            )
        ),
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
        email = _string(
            recruiter.get(
                "email"
            )
        ).lower()

        linkedin = _string(
            recruiter.get(
                "linkedin_url"
            )
        ).lower()

        name = _string(
            recruiter.get(
                "name"
            )
        ).lower()

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


def _recruiter_is_relevant(
    recruiter: dict[str, Any],
    profile: dict[str, Any],
) -> bool:
    text = _normalise_text(
        " ".join(
            [
                recruiter.get(
                    "title",
                    ""
                ),
                recruiter.get(
                    "company",
                    ""
                ),
                recruiter.get(
                    "location",
                    ""
                ),
                recruiter.get(
                    "about",
                    ""
                ),
                recruiter.get(
                    "recruiter_text",
                    ""
                ),
            ]
        )
    ).lower()

    target_roles = profile.get(
        "targeting",
        {},
    ).get(
        "roles",
        [],
    )

    role_terms = [
        "technical recruiter",
        "technical sourcer",
        "engineering recruiter",
        "technology recruiter",
        "it recruiter",
        "talent acquisition",
        "talent sourcer",
        "recruiter",
        "sourcer",
        "hiring manager",
        "talent partner",
    ]

    ai_terms = [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
        "generative ai",
        "genai",
        "llm",
        "rag",
        "data science",
        "software",
        "engineering",
        "technology",
    ]

    location_text = recruiter.get(
        "location",
        ""
    ).lower()

    target_locations = [
        str(location).lower()
        for location in profile.get(
            "targeting",
            {},
        ).get(
            "locations",
            [],
        )
    ]

    location_match = any(
        location in location_text
        or location_text in location
        for location in target_locations
        if location
    )

    recruiter_role_match = any(
        term in text
        for term in role_terms
    )

    ai_role_match = any(
        term.lower() in text
        for term in target_roles
    )

    ai_signal = any(
        term in text
        for term in ai_terms
    )

    remote_match = (
        "remote" in text
        or "remote" in location_text
    )

    return bool(
        recruiter_role_match
        and (
            location_match
            or remote_match
            or ai_role_match
            or ai_signal
        )
    )


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

    search_query = (
        "Technical Recruiter "
        "Technical Sourcer "
        "Engineering Recruiter "
        "Talent Acquisition"
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

    print(
        f"Raw recruiter records: "
        f"{len(raw_records)}"
    )

    recruiters = [
        _normalise_recruiter(
            record
        )
        for record in raw_records
        if isinstance(
            record,
            dict,
        )
    ]

    recruiters = _deduplicate(
        recruiters
    )

    print(
        f"Unique recruiters: "
        f"{len(recruiters)}"
    )

    qualified = [
        recruiter
        for recruiter in recruiters
        if _recruiter_is_relevant(
            recruiter,
            profile,
        )
    ]

    print(
        f"Relevant recruiter records: "
        f"{len(qualified)}"
    )

    return qualified
