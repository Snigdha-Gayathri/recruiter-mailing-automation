from __future__ import annotations

import os
import re
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"

DEFAULT_JOB_ACTOR = os.getenv(
    "APIFY_JOB_ACTOR",
    "bebity~linkedin-jobs-scraper"
)


TARGET_ROLE_KEYWORDS = [
    "ai engineer",
    "ai/ml engineer",
    "machine learning engineer",
    "machine learning",
    "ml engineer",
    "artificial intelligence engineer",
    "artificial intelligence",
    "generative ai",
    "genai",
    "generative ai engineer",
    "genai engineer",
    "llm engineer",
    "large language model",
    "agent engineer",
    "ai agent",
    "ai agents",
    "applied ai",
    "applied ai engineer",
    "rag engineer",
    "retrieval augmented generation",
    "nlp engineer",
    "natural language processing",
    "deep learning engineer",
    "deep learning",
    "mlops",
    "llmops",
    "ai research engineer",
    "machine learning intern",
    "ai intern",
    "generative ai intern",
    "software engineer ai",
    "software engineer ml"
]


TARGET_LOCATION_KEYWORDS = [
    "remote",
    "bengaluru",
    "bangalore",
    "mumbai",
    "hyderabad"
]


def normalize(text: Any) -> str:
    value = str(text or "").lower()

    value = re.sub(
        r"[^a-z0-9+#./& -]",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def get_apify_token() -> str:
    token = os.getenv(
        "APIFY_API_TOKEN",
        ""
    ).strip()

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN is not configured."
        )

    return token


def get_actor_id() -> str:
    actor_id = os.getenv(
        "APIFY_JOB_ACTOR",
        DEFAULT_JOB_ACTOR
    ).strip()

    if not actor_id:
        raise RuntimeError(
            "APIFY_JOB_ACTOR is empty."
        )

    return actor_id


def actor_url(
    actor_id: str
) -> str:
    return (
        f"{APIFY_API_BASE}/acts/"
        f"{actor_id.replace('/', '~')}/runs"
    )


def dataset_url(
    dataset_id: str
) -> str:
    return (
        f"{APIFY_API_BASE}/datasets/"
        f"{dataset_id}/items"
    )


def extract_value(
    record: dict[str, Any],
    fields: list[str]
) -> str:
    for field in fields:
        value = record.get(field)

        if isinstance(
            value,
            str
        ):
            value = value.strip()

            if value:
                return value

    return ""


def extract_job_title(
    record: dict[str, Any]
) -> str:
    return extract_value(
        record,
        [
            "title",
            "jobTitle",
            "position",
            "name"
        ]
    )


def extract_company(
    record: dict[str, Any]
) -> str:
    return extract_value(
        record,
        [
            "companyName",
            "company",
            "company_name",
            "organizationName"
        ]
    )


def extract_location(
    record: dict[str, Any]
) -> str:
    value = extract_value(
        record,
        [
            "location",
            "jobLocation",
            "formattedLocation",
            "locationName"
        ]
    )

    if value:
        return value

    city = extract_value(
        record,
        [
            "city",
            "jobCity"
        ]
    )

    return city


def extract_description(
    record: dict[str, Any]
) -> str:
    return extract_value(
        record,
        [
            "description",
            "jobDescription",
            "descriptionText"
        ]
    )


def extract_url(
    record: dict[str, Any]
) -> str:
    return extract_value(
        record,
        [
            "url",
            "jobUrl",
            "linkedinUrl",
            "link"
        ]
    )


def extract_company_url(
    record: dict[str, Any]
) -> str:
    return extract_value(
        record,
        [
            "companyUrl",
            "companyLinkedinUrl",
            "companyLinkedInUrl"
        ]
    )


def job_matches_target_roles(
    job: dict[str, Any]
) -> list[str]:
    text = normalize(
        " ".join(
            [
                job.get("title", ""),
                job.get("description", "")
            ]
        )
    )

    matches = []

    for keyword in TARGET_ROLE_KEYWORDS:
        if keyword in text:
            matches.append(
                keyword
            )

    return list(
        dict.fromkeys(matches)
    )


def job_matches_target_location(
    job: dict[str, Any]
) -> bool:
    location = normalize(
        job.get(
            "location",
            ""
        )
    )

    return any(
        keyword in location
        for keyword in TARGET_LOCATION_KEYWORDS
    )


def normalize_job(
    record: dict[str, Any]
) -> dict[str, Any]:
    job = {
        "title": extract_job_title(
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

        "company_url": extract_company_url(
            record
        ),

        "raw": record
    }

    job[
        "role_matches"
    ] = job_matches_target_roles(
        job
    )

    job[
        "location_match"
    ] = job_matches_target_location(
        job
    )

    return job


def search_company_jobs(
    company: str
) -> list[dict[str, Any]]:
    if not company:
        return []

    token = get_apify_token()
    actor_id = get_actor_id()

    payload = {
        "searchQuery": company,
        "maxItems": 25,
        "startPage": 1,
        "takePages": 1
    }

    print(
        f"Searching current jobs for: {company}"
    )

    response = requests.post(
        actor_url(actor_id),
        params={
            "token": token,
            "waitForFinish": 120
        },
        json=payload,
        timeout=300
    )

    if not response.ok:
        raise RuntimeError(
            "Apify job discovery failed.\n"
            f"HTTP: {response.status_code}\n"
            f"Company: {company}\n"
            f"Response: "
            f"{response.text[:2000]}"
        )

    run_data = response.json().get(
        "data",
        {}
    )

    dataset_id = run_data.get(
        "defaultDatasetId"
    )

    if not dataset_id:
        return []

    dataset_response = requests.get(
        dataset_url(dataset_id),
        params={
            "token": token,
            "clean": "true"
        },
        timeout=300
    )

    if not dataset_response.ok:
        raise RuntimeError(
            "Failed to retrieve job dataset.\n"
            f"HTTP: "
            f"{dataset_response.status_code}\n"
            f"Response: "
            f"{dataset_response.text[:2000]}"
        )

    records = dataset_response.json()

    if not isinstance(
        records,
        list
    ):
        return []

    jobs = [
        normalize_job(record)
        for record in records
        if isinstance(
            record,
            dict
        )
    ]

    relevant_jobs = [
        job
        for job in jobs
        if job["role_matches"]
        and job["location_match"]
    ]

    print(
        f"  Jobs discovered: {len(jobs)}"
    )

    print(
        f"  Relevant AI jobs: "
        f"{len(relevant_jobs)}"
    )

    return relevant_jobs


def deduplicate_jobs(
    jobs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    seen = set()
    result = []

    for job in jobs:
        key = (
            normalize(
                job.get(
                    "title",
                    ""
                )
            ),
            normalize(
                job.get(
                    "company",
                    ""
                )
            ),
            normalize(
                job.get(
                    "location",
                    ""
                )
            )
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(job)

    return result
