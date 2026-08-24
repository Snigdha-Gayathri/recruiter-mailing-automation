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
    configured_actor = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        ""
    ).strip()

    if configured_actor:
        return configured_actor

    return DEFAULT_ACTOR_ID


def build_search_queries(
    profile: dict[str, Any]
) -> list[str]:
    roles = (
        profile
        .get("targeting", {})
        .get("roles", [])
    )

    role_groups = [
        "AI Engineer",
        "Machine Learning Engineer",
        "Generative AI Engineer",
        "LLM Engineer",
        "AI Agent Engineer",
        "RAG Engineer",
        "AI/ML Engineer"
    ]

    recruiter_titles = [
        "Technical Recruiter",
        "Technical Talent Acquisition",
        "Talent Acquisition Partner",
        "Engineering Recruiter",
        "Technical Sourcer",
        "Hiring Manager"
    ]

    selected_roles = [
        role
        for role in role_groups
        if role in roles
    ]

    queries = []

    for recruiter_title in recruiter_titles:
        for role in selected_roles:
            queries.append(
                f'"{recruiter_title}" "{role}" '
                f'Bangalore OR Bengaluru OR Mumbai OR Hyderabad OR Remote'
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
        error_text = response.text[:2000]

        raise RuntimeError(
            "Apify actor request failed.\n"
            f"HTTP status: {response.status_code}\n"
            f"Actor: {actor_id}\n"
            f"Response: {error_text}"
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
            f"{dataset_response.text[:2000]}"
        )

    items = dataset_response.json()

    if not isinstance(items, list):
        raise RuntimeError(
            "Apify dataset response was not a list."
        )

    return items


def search_recruiters(
    profile: dict[str, Any]
) -> list[dict[str, Any]]:
    actor_id = get_actor_id()

    if not actor_id:
        raise RuntimeError(
            "No Apify recruiter actor configured."
        )

    queries = build_search_queries(
        profile
    )

    if not queries:
        raise RuntimeError(
            "No recruiter search queries could "
            "be generated from profile.json."
        )

    # We intentionally keep discovery to one Apify
    # actor execution per hourly workflow run.
    combined_query = " OR ".join(
        f"({query})"
        for query in queries[:12]
    )

    run_input = {
        "searchQueries": [
            combined_query
        ],
        "maxItems": 100,
        "searchMode": "people",
        "includeEmails": True
    }

    print(
        f"Generated {len(queries)} recruiter queries."
    )

    print(
        "Submitting one Apify discovery request..."
    )

    return run_apify_actor(
        actor_id=actor_id,
        run_input=run_input
    )


def normalize_recruiter(
    raw: dict[str, Any]
) -> dict[str, Any]:
    return {
        "name": (
            raw.get("name")
            or raw.get("fullName")
            or raw.get("full_name")
            or ""
        ).strip(),

        "email": (
            raw.get("email")
            or raw.get("emailAddress")
            or raw.get("contactEmail")
            or ""
        ).strip().lower(),

        "title": (
            raw.get("headline")
            or raw.get("title")
            or raw.get("position")
            or ""
        ).strip(),

        "company": (
            raw.get("company")
            or raw.get("companyName")
            or raw.get("currentCompany")
            or ""
        ).strip(),

        "location": (
            raw.get("location")
            or raw.get("geoLocation")
            or raw.get("city")
            or ""
        ).strip(),

        "linkedin_url": (
            raw.get("linkedinUrl")
            or raw.get("linkedin_url")
            or raw.get("profileUrl")
            or ""
        ).strip(),

        "about": (
            raw.get("about")
            or raw.get("summary")
            or ""
        ).strip(),

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
        result.append(recruiter)

    return result
