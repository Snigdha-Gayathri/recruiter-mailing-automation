from __future__ import annotations

import os
import time
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"


def get_apify_token() -> str:
    token = os.getenv("APIFY_API_TOKEN")

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN environment variable is not configured."
        )

    return token


def build_search_queries(profile: dict[str, Any]) -> list[str]:
    roles = profile.get("targeting", {}).get("roles", [])

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

    queries = []

    selected_roles = [
        role
        for role in role_groups
        if role in roles
    ]

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

    url = (
        f"{APIFY_API_BASE}/acts/"
        f"{actor_id.replace("/", "~")}/runs"
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

    response.raise_for_status()

    payload = response.json()

    run_data = payload.get("data", {})

    dataset_id = run_data.get("defaultDatasetId")

    if not dataset_id:
        raise RuntimeError(
            "Apify run completed without a dataset ID."
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

    dataset_response.raise_for_status()

    items = dataset_response.json()

    if not isinstance(items, list):
        return []

    return items


def search_recruiters(
    profile: dict[str, Any]
) -> list[dict[str, Any]]:
    actor_id = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        "harvestapi~linkedin-profile-search"
    )

    queries = build_search_queries(profile)

    # Keep one discovery request per workflow run.
    # This avoids the API explosion that occurred in the previous
    # recruiter automation.
    query_string = " OR ".join(
        f"({query})"
        for query in queries[:12]
    )

    run_input = {
        "searchQueries": [
            query_string
        ],
        "maxItems": 100,
        "searchMode": "people",
        "includeEmails": True
    }

    try:
        return run_apify_actor(
            actor_id=actor_id,
            run_input=run_input
        )

    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Apify recruiter discovery failed: {exc}"
        ) from exc

    except Exception:
        raise


def normalize_recruiter(raw: dict[str, Any]) -> dict[str, Any]:
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
        email = recruiter.get("email", "").lower()
        linkedin = recruiter.get("linkedin_url", "").lower()
        name = recruiter.get("name", "").lower()

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
        result.append(recruiter)

    return result
