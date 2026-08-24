from __future__ import annotations

import os
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"

DEFAULT_ACTOR_ID = "harvestapi~linkedin-profile-search"


def get_apify_token() -> str:
    token = os.getenv("APIFY_API_TOKEN", "").strip()

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN environment variable is not configured."
        )

    return token


def get_actor_id() -> str:
    actor_id = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        DEFAULT_ACTOR_ID
    ).strip()

    return actor_id or DEFAULT_ACTOR_ID


def build_recruiter_titles() -> list[str]:
    return [
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
        "Engineering Manager"
    ]


def build_locations(
    profile: dict[str, Any]
) -> list[str]:
    configured_locations = (
        profile
        .get("targeting", {})
        .get("locations", [])
    )

    location_map = {
        "Bangalore": "Bengaluru",
        "Bengaluru": "Bengaluru",
        "Mumbai": "Mumbai",
        "Hyderabad": "Hyderabad"
    }

    locations = []

    for location in configured_locations:
        mapped = location_map.get(
            location,
            location
        )

        if mapped == "Remote":
            continue

        if mapped not in locations:
            locations.append(mapped)

    return locations


def build_search_queries(
    profile: dict[str, Any]
) -> list[str]:
    recruiter_titles = build_recruiter_titles()

    locations = build_locations(
        profile
    )

    queries = []

    for title in recruiter_titles:
        for location in locations:
            queries.append(
                {
                    "searchQuery": title,
                    "location": location
                }
            )

    return queries


def run_apify_actor(
    actor_id: str,
    run_input: dict[str, Any],
    timeout_seconds: int = 300
) -> list[dict[str, Any]]:
    token = get_apify_token()

    encoded_actor_id = actor_id.replace(
        "/",
        "~"
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

    safe_input = {
        key: value
        for key, value in run_input.items()
    }

    print(
        safe_input
    )

    response = requests.post(
        url,
        params={
            "token": token,
            "waitForFinish": 120
        },
        json=run_input,
        timeout=timeout_seconds
    )

    if not response.ok:
        raise RuntimeError(
            "Apify actor request failed.\n"
            f"HTTP status: {response.status_code}\n"
            f"Actor: {actor_id}\n"
            f"Response: {response.text[:3000]}"
        )

    payload = response.json()

    run_data = payload.get(
        "data",
        {}
    )

    dataset_id = run_data.get(
        "defaultDatasetId"
    )

    if not dataset_id:
        raise RuntimeError(
            "Apify run completed without a dataset ID.\n"
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
            "clean": "true"
        },
        timeout=timeout_seconds
    )

    if not dataset_response.ok:
        raise RuntimeError(
            "Failed to retrieve Apify dataset.\n"
            f"HTTP status: "
            f"{dataset_response.status_code}\n"
            f"Response: "
            f"{dataset_response.text[:3000]}"
        )

    items = dataset_response.json()

    if not isinstance(items, list):
        raise RuntimeError(
            "Apify dataset response was not a list."
        )

    return items


def search_one_recruiter_segment(
    search_query: str,
    location: str
) -> list[dict[str, Any]]:
    actor_id = get_actor_id()

    run_input = {
        "profileScraperMode": "Full + email search",
        "searchQuery": search_query,
        "locations": [
            location
        ],
        "maxItems": 25,
        "startPage": 1,
        "takePages": 1
    }

    return run_apify_actor(
        actor_id=actor_id,
        run_input=run_input
    )


def search_recruiters(
    profile: dict[str, Any]
) -> list[dict[str, Any]]:
    segments = build_search_queries(
        profile
    )

    if not segments:
        raise RuntimeError(
            "No recruiter search segments "
            "could be generated."
        )

    print(
        f"Generated {len(segments)} "
        "recruiter search segments."
    )

    # IMPORTANT:
    #
    # We intentionally do not execute all 42 segments
    # in one hourly run. That would create unnecessary
    # Apify usage.
    #
    # We rotate through segments based on the current
    # GitHub Actions hour.
    #
    # Five segments per run gives us:
    #
    # 5 searches/hour
    # 120 searches/day maximum
    #
    # The caller can later reduce this if needed.

    from datetime import datetime, timezone

    current_hour = datetime.now(
        timezone.utc
    ).hour

    segment_count = len(segments)

    start_index = (
        current_hour * 5
    ) % segment_count

    selected_segments = []

    for offset in range(
        min(5, segment_count)
    ):
        index = (
            start_index + offset
        ) % segment_count

        selected_segments.append(
            segments[index]
        )

    print(
        "Selected segments:"
    )

    for segment in selected_segments:
        print(
            f"  - {segment['searchQuery']} "
            f"| {segment['location']}"
        )

    all_results = []

    for segment in selected_segments:
        print()
        print(
            f"Searching: "
            f"{segment['searchQuery']} "
            f"in {segment['location']}"
        )

        results = search_one_recruiter_segment(
            search_query=segment["searchQuery"],
            location=segment["location"]
        )

        print(
            f"Results: {len(results)}"
        )

        all_results.extend(
            results
        )

    return all_results


def extract_email(
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "email",
        "emailAddress",
        "contactEmail",
        "personalEmail",
        "workEmail",
        "professionalEmail"
    ]

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip().lower()

            if value:
                return value

    return ""


def extract_name(
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "name",
        "fullName",
        "full_name"
    ]

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

    first_name = (
        raw.get("firstName")
        or raw.get("first_name")
        or ""
    )

    last_name = (
        raw.get("lastName")
        or raw.get("last_name")
        or ""
    )

    return (
        f"{first_name} {last_name}"
    ).strip()


def extract_company(
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "company",
        "companyName",
        "currentCompany"
    ]

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

    experiences = raw.get(
        "experiences",
        []
    )

    if isinstance(
        experiences,
        list
    ):
        for experience in experiences:
            if not isinstance(
                experience,
                dict
            ):
                continue

            company = (
                experience.get("companyName")
                or experience.get("company")
                or ""
            )

            if company:
                return str(
                    company
                ).strip()

    return ""


def extract_title(
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "headline",
        "title",
        "position",
        "jobTitle"
    ]

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

    experiences = raw.get(
        "experiences",
        []
    )

    if isinstance(
        experiences,
        list
    ):
        for experience in experiences:
            if not isinstance(
                experience,
                dict
            ):
                continue

            title = (
                experience.get("title")
                or experience.get("position")
                or ""
            )

            if title:
                return str(
                    title
                ).strip()

    return ""


def extract_location(
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "location",
        "geoLocation",
        "city",
        "locationName"
    ]

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

        if isinstance(value, dict):
            city = (
                value.get("city")
                or ""
            )

            country = (
                value.get("country")
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
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "linkedinUrl",
        "linkedin_url",
        "profileUrl",
        "url"
    ]

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if "linkedin.com" in value:
                return value

    return ""


def extract_about(
    raw: dict[str, Any]
) -> str:
    possible_fields = [
        "about",
        "summary",
        "headline"
    ]

    values = []

    for field in possible_fields:
        value = raw.get(field)

        if isinstance(value, str):
            value = value.strip()

            if value:
                values.append(
                    value
                )

    return " ".join(
        values
    )


def normalize_recruiter(
    raw: dict[str, Any]
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

        "raw": raw
    }


def deduplicate_recruiters(
    recruiters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    seen = set()

    result = []

    for recruiter in recruiters:
        email = (
            recruiter.get("email", "")
            .strip()
            .lower()
        )

        linkedin = (
            recruiter.get("linkedin_url", "")
            .strip()
            .lower()
        )

        name = (
            recruiter.get("name", "")
            .strip()
            .lower()
        )

        company = (
            recruiter.get("company", "")
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

        seen.add(key)

        result.append(
            recruiter
        )

    return result
