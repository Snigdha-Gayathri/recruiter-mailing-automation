from __future__ import annotations

import os
import re
from typing import Any

import requests


APIFY_API_BASE = "https://api.apify.com/v2"

DEFAULT_JOB_ACTOR = "bebity~linkedin-jobs-scraper"

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


def normalize(value: Any) -> str:
    text = str(value or "").lower()

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
    actor_id = os.getenv(
        "APIFY_JOB_ACTOR",
        DEFAULT_JOB_ACTOR,
    ).strip()

    if not actor_id:
        raise RuntimeError(
            "APIFY_JOB_ACTOR is not configured."
        )

    return actor_id


def build_actor_url(
    actor_id: str,
) -> str:
    encoded_actor_id = actor_id.replace(
        "/",
        "~",
    )

    return (
        f"{APIFY_API_BASE}/acts/"
        f"{encoded_actor_id}/runs"
    )


def extract_string(
    record: dict[str, Any],
    fields: list[str],
) -> str:

    for field in fields:

        value = record.get(
            field
        )

        if (
            isinstance(value, str)
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
        "title": extract_title(record),
        "company": extract_company(record),
        "location": extract_location(record),
        "description": extract_description(record),
        "url": extract_url(record),
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

    normalized_location = normalize(
        location
    )

    if not normalized_location:
        return False

    for target in TARGET_LOCATIONS:

        normalized_target = normalize(
            target
        )

        if normalized_target in normalized_location:
            return True

    return False


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

        url = normalize(
            job.get(
                "url",
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

        seen.add(key)
        result.append(job)

    return result


def search_jobs() -> list[dict[str, Any]]:

    token = get_apify_token()
    actor_id = get_actor_id()

    actor_url = build_actor_url(
        actor_id
    )

    actor_input = {
        "searchQuery": JOB_SEARCH_QUERY,
        "locations": TARGET_LOCATIONS,
        "maxItems": int(
            os.getenv(
                "JOB_MAX_ITEMS",
                "100",
            )
        ),
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

    print(actor_input)

    response = requests.post(
        actor_url,
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

    print(
        f"Apify job dataset: "
        f"{dataset_id}"
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
            jobs.append(job)

    jobs = deduplicate_jobs(
        jobs
    )

    print(
        f"Relevant unique jobs: "
        f"{len(jobs)}"
    )

    return jobs


def company_key(
    company: str,
) -> str:

    value = normalize(
        company
    )

    value = re.sub(
        r"\b(pvt|private|ltd|limited|inc|llc|corp|corporation)\b",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def companies_match(
    recruiter_company: str,
    job_company: str,
) -> bool:

    recruiter_key = company_key(
        recruiter_company
    )

    job_key = company_key(
        job_company
    )

    if not recruiter_key or not job_key:
        return False

    if recruiter_key == job_key:
        return True

    if (
        recruiter_key in job_key
        or job_key in recruiter_key
    ):
        return True

    recruiter_words = set(
        recruiter_key.split()
    )

    job_words = set(
        job_key.split()
    )

    if not recruiter_words or not job_words:
        return False

    overlap = (
        recruiter_words
        & job_words
    )

    return len(overlap) >= 2


def jobs_for_company(
    jobs: list[dict[str, Any]],
    company: str,
) -> list[dict[str, Any]]:

    if not company:
        return []

    matches = []

    for job in jobs:

        if companies_match(
            company,
            job.get(
                "company",
                "",
            ),
        ):
            matches.append(job)

    return matches
