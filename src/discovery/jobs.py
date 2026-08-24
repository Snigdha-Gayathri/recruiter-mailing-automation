from __future__ import annotations

import os
import re
from typing import Any

import requests


APIFY_API_BASE = (
    "https://api.apify.com/v2"
)

DEFAULT_JOB_ACTOR = (
    "bebity~linkedin-jobs-scraper"
)

JOB_SEARCH_QUERY = (
    "AI Engineer OR "
    "Machine Learning Engineer OR "
    "Generative AI OR "
    "GenAI OR "
    "LLM Engineer OR "
    "AI Agent Engineer OR "
    "RAG Engineer OR "
    "Applied AI Engineer"
)

TARGET_LOCATIONS = [
    "Bengaluru",
    "Bangalore",
    "Mumbai",
    "Hyderabad",
    "Remote",
]


def normalize(
    value: Any,
) -> str:

    text = str(
        value or ""
    ).lower()

    text = re.sub(
        r"[^a-z0-9+#./& -]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


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

    return os.getenv(
        "APIFY_JOB_ACTOR",
        DEFAULT_JOB_ACTOR,
    ).strip() or DEFAULT_JOB_ACTOR


def extract_string(
    record: dict[str, Any],
    fields: list[str],
) -> str:

    for field in fields:

        value = record.get(
            field
        )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):

            return value.strip()

    return ""


def extract_title(
    record: dict[str, Any],
) -> str:

    return extract_string(
        record,
        [
            "title",
            "jobTitle",
            "job_title",
            "position",
            "name",
        ],
    )


def extract_company(
    record: dict[str, Any],
) -> str:

    return extract_string(
        record,
        [
            "companyName",
            "company",
            "company_name",
            "organizationName",
            "organization",
        ],
    )


def extract_location(
    record: dict[str, Any],
) -> str:

    value = extract_string(
        record,
        [
            "location",
            "jobLocation",
            "formattedLocation",
            "locationName",
            "city",
        ],
    )

    if value:
        return value

    location = record.get(
        "location"
    )

    if isinstance(
        location,
        dict,
    ):

        city = str(
            location.get(
                "city",
                "",
            )
        ).strip()

        country = str(
            location.get(
                "country",
                "",
            )
        ).strip()

        return ", ".join(
            part
            for part in [
                city,
                country,
            ]
            if part
        )

    return ""


def extract_description(
    record: dict[str, Any],
) -> str:

    return extract_string(
        record,
        [
            "description",
            "jobDescription",
            "descriptionText",
            "job_description",
        ],
    )


def extract_url(
    record: dict[str, Any],
) -> str:

    return extract_string(
        record,
        [
            "url",
            "jobUrl",
            "job_url",
            "linkedinUrl",
            "link",
        ],
    )


def normalize_job(
    record: dict[str, Any],
) -> dict[str, Any]:

    return {
        "title": extract_title(
            record
        ),
        "company": extract_company(
            record
        ),
        "location": extract_location(
            record
        ),
        "description": extract_description(
            record
        ),
        "url": extract_url(
            record
        ),
        "raw": record,
    }


def role_matches(
    job: dict[str, Any],
) -> bool:

    text = normalize(
        " ".join(
            [
                job.get(
                    "title",
                    "",
                ),
                job.get(
                    "description",
                    "",
                ),
            ]
        )
    )

    keywords = [
        "ai engineer",
        "artificial intelligence",
        "machine learning",
        "ml engineer",
        "generative ai",
        "genai",
        "llm",
        "large language model",
        "agent engineer",
        "ai agent",
        "applied ai",
        "rag",
        "retrieval augmented generation",
        "nlp",
        "natural language processing",
        "deep learning",
        "mlops",
        "llmops",
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


def location_matches(
    location: str,
) -> bool:

    value = normalize(
        location
    )

    if not value:
        return False

    return any(
        normalize(target)
        in value
        for target in TARGET_LOCATIONS
    )


def relevant_job(
    job: dict[str, Any],
) -> bool:

    return (
        role_matches(job)
        and location_matches(
            job.get(
                "location",
                "",
            )
        )
    )


def deduplicate_jobs(
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    seen = set()
    result = []

    for job in jobs:

        url = normalize(
            job.get(
                "url",
                "",
            )
        )

        title = normalize(
            job.get(
                "title",
                "",
            )
        )

        company = normalize(
            job.get(
                "company",
                "",
            )
        )

        location = normalize(
            job.get(
                "location",
                "",
            )
        )

        key = (
            url
            or f"{title}|{company}|{location}"
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            job
        )

    return result


def search_jobs() -> list[dict[str, Any]]:

    token = get_apify_token()

    actor_id = get_actor_id()

    encoded_actor_id = (
        actor_id.replace(
            "/",
            "~",
        )
    )

    url = (
        f"{APIFY_API_BASE}/acts/"
        f"{encoded_actor_id}/runs"
    )

    max_items = int(
        os.getenv(
            "JOB_MAX_ITEMS",
            "100",
        )
    )

    max_items = max(
        1,
        min(
            max_items,
            100,
        ),
    )

    actor_input = {
        "searchQuery": JOB_SEARCH_QUERY,
        "locations": TARGET_LOCATIONS,
        "maxItems": max_items,
        "startPage": 1,
        "takePages": 1,
    }

    print(
        f"Using Apify job actor: "
        f"{actor_id}"
    )

    print(
        "Apify job input:"
    )

    print(
        actor_input
    )

    response = requests.post(
        url,
        params={
            "token": token,
            "waitForFinish": 120,
        },
        json=actor_input,
        timeout=300,
    )

    if not response.ok:

        raise RuntimeError(
            "Apify job discovery failed.\n"
            f"HTTP: "
            f"{response.status_code}\n"
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
            "Apify job run returned "
            "no dataset ID."
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
            "Failed to retrieve "
            "Apify job dataset.\n"
            f"HTTP: "
            f"{dataset_response.status_code}\n"
            f"Response: "
            f"{dataset_response.text[:3000]}"
        )

    records = dataset_response.json()

    if not isinstance(
        records,
        list,
    ):

        return []

    print(
        f"Raw job records: "
        f"{len(records)}"
    )

    jobs = []

    for record in records:

        if not isinstance(
            record,
            dict,
        ):
            continue

        job = normalize_job(
            record
        )

        if relevant_job(job):
            jobs.append(
                job
            )

    jobs = deduplicate_jobs(
        jobs
    )

    print(
        f"Relevant unique jobs: "
        f"{len(jobs)}"
    )

    return jobs
