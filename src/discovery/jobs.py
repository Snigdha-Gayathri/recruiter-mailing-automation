from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests


APIFY_BASE_URL = "https://api.apify.com/v2"
DEFAULT_JOB_ACTOR = "bebity/linkedin-jobs-scraper"

TARGET_LOCATIONS = [
    "Bengaluru",
    "Bangalore",
    "Mumbai",
    "Hyderabad",
    "Remote",
]

TARGET_JOB_TERMS = [
    "AI Engineer",
    "Machine Learning Engineer",
    "ML Engineer",
    "Generative AI",
    "GenAI",
    "LLM Engineer",
    "AI Agent Engineer",
    "RAG Engineer",
    "Applied AI Engineer",
    "NLP Engineer",
    "AI/ML Engineer",
]


def _normalise(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.lower().strip()

    return str(value).lower().strip()


def _job_text(job: dict[str, Any]) -> str:
    fields = [
        job.get("title"),
        job.get("description"),
        job.get("location"),
        job.get("companyName"),
        job.get("company"),
        job.get("workplaceType"),
    ]

    return " ".join(
        _normalise(field)
        for field in fields
        if field
    )


def _job_title(job: dict[str, Any]) -> str:
    return str(
        job.get("title")
        or job.get("jobTitle")
        or job.get("name")
        or ""
    ).strip()


def _job_company(job: dict[str, Any]) -> str:
    company = job.get("company")

    if isinstance(company, dict):
        return str(
            company.get("name")
            or company.get("companyName")
            or ""
        ).strip()

    return str(
        job.get("companyName")
        or company
        or ""
    ).strip()


def _job_location(job: dict[str, Any]) -> str:
    location = job.get("location")

    if isinstance(location, dict):
        return str(
            location.get("name")
            or location.get("city")
            or location.get("text")
            or ""
        ).strip()

    return str(location or "").strip()


def score_job(job: dict[str, Any]) -> float:
    text = _job_text(job)
    title = _normalise(_job_title(job))
    location = _normalise(_job_location(job))

    score = 0.0

    title_hits = sum(
        term.lower() in title
        for term in TARGET_JOB_TERMS
    )

    text_hits = sum(
        term.lower() in text
        for term in TARGET_JOB_TERMS
    )

    score += min(60, title_hits * 25)
    score += min(25, text_hits * 5)

    if any(
        city.lower() in location
        for city in TARGET_LOCATIONS
    ):
        score += 15

    return round(
        min(100.0, score),
        2,
    )


def is_relevant_job(
    job: dict[str, Any],
    minimum_score: float = 30.0,
) -> bool:
    return score_job(job) >= minimum_score


def _run_apify_job_actor(
    actor_id: str,
    actor_input: dict[str, Any],
    timeout_seconds: int = 120,
) -> list[dict[str, Any]]:
    token = os.getenv("APIFY_API_TOKEN")

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN is not configured."
        )

    encoded_actor_id = actor_id.replace("/", "~")

    url = (
        f"{APIFY_BASE_URL}/acts/"
        f"{encoded_actor_id}/runs"
    )

    response = requests.post(
        url,
        params={
            "token": token,
            "waitForFinish": timeout_seconds,
        },
        json=actor_input,
        timeout=timeout_seconds + 30,
    )

    response.raise_for_status()

    run_data = response.json().get("data") or {}

    dataset_id = run_data.get("defaultDatasetId")

    if not dataset_id:
        return []

    print(f"Apify job dataset: {dataset_id}")

    dataset_url = (
        f"{APIFY_BASE_URL}/datasets/"
        f"{dataset_id}/items"
    )

    dataset_response = requests.get(
        dataset_url,
        params={
            "token": token,
            "format": "json",
            "clean": "true",
        },
        timeout=60,
    )

    dataset_response.raise_for_status()

    data = dataset_response.json()

    if not isinstance(data, list):
        return []

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def search_jobs(
    max_results: int = 100,
) -> list[dict[str, Any]]:
    actor_id = os.getenv(
        "APIFY_JOB_ACTOR",
        DEFAULT_JOB_ACTOR,
    )

    query = (
        "AI Engineer OR Machine Learning Engineer OR "
        "Generative AI OR GenAI OR LLM Engineer OR "
        "AI Agent Engineer OR RAG Engineer OR "
        "Applied AI Engineer"
    )

    print("JOB DISCOVERY")
    print(f"Using Apify job actor: {actor_id}")
    print(f"Job query: {query}")

    actor_input = {
        "searchQuery": query,
        "locations": TARGET_LOCATIONS,
        "maxItems": max_results,
        "startPage": 1,
        "takePages": 1,
    }

    print("Apify job input:")
    print(actor_input)

    jobs = _run_apify_job_actor(
        actor_id=actor_id,
        actor_input=actor_input,
    )

    relevant = [
        job
        for job in jobs
        if is_relevant_job(job)
    ]

    relevant.sort(
        key=score_job,
        reverse=True,
    )

    print(f"Raw jobs: {len(jobs)}")
    print(f"Relevant jobs: {len(relevant)}")

    return relevant


def load_job_cache(
    cache_path: str,
    ttl_seconds: int,
) -> list[dict[str, Any]]:
    path = Path(cache_path)

    if not path.exists():
        return []

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return []

    if not isinstance(data, dict):
        return []

    timestamp = data.get("timestamp")

    if not isinstance(timestamp, (int, float)):
        return []

    age = time.time() - timestamp

    if age >= ttl_seconds:
        return []

    jobs = data.get("jobs")

    if not isinstance(jobs, list):
        return []

    return [
        job
        for job in jobs
        if isinstance(job, dict)
    ]


def save_job_cache(
    cache_path: str,
    jobs: list[dict[str, Any]],
) -> None:
    path = Path(cache_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "timestamp": time.time(),
        "jobs": jobs,
    }

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def get_jobs_with_cache(
    cache_path: str = "data/job_cache.json",
    ttl_seconds: int = 21600,
    max_results: int = 100,
) -> list[dict[str, Any]]:
    cached_jobs = load_job_cache(
        cache_path=cache_path,
        ttl_seconds=ttl_seconds,
    )

    if cached_jobs:
        print("JOB DISCOVERY")
        print(
            f"Using cached jobs: {len(cached_jobs)}"
        )
        print(
            f"Job cache TTL: {ttl_seconds // 3600} hours"
        )
        return cached_jobs

    print("JOB DISCOVERY")
    print("Job cache expired or empty.")
    print("Refreshing global AI job cache...")

    jobs = search_jobs(
        max_results=max_results,
    )

    save_job_cache(
        cache_path=cache_path,
        jobs=jobs,
    )

    return jobs


def jobs_for_company(
    jobs: list[dict[str, Any]],
    company_name: str,
) -> list[dict[str, Any]]:
    target = _normalise(company_name)

    if not target:
        return []

    return [
        job
        for job in jobs
        if target in _normalise(_job_company(job))
    ]


def search_company_jobs(
    company_name: str,
    jobs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if jobs is None:
        jobs = get_jobs_with_cache()

    return jobs_for_company(
        jobs,
        company_name,
    )
