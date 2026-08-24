from __future__ import annotations

from typing import Any


TARGET_LOCATIONS = {
    "bengaluru",
    "bangalore",
    "mumbai",
    "hyderabad",
    "remote",
}

TARGET_ROLE_KEYWORDS = {
    "ai engineer",
    "machine learning engineer",
    "ml engineer",
    "generative ai",
    "genai",
    "llm engineer",
    "rag engineer",
    "ai agent",
    "agentic ai",
    "applied ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "nlp",
    "mlops",
}

TECHNOLOGY_KEYWORDS = {
    "python",
    "pytorch",
    "tensorflow",
    "transformers",
    "langchain",
    "langgraph",
    "llamaindex",
    "rag",
    "llm",
    "gemini",
    "qdrant",
    "neo4j",
    "fastapi",
    "docker",
}


def _normalise(value: Any) -> str:
    if value is None:
        return ""

    return str(value).lower().strip()


def _flatten(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.lower()

    if isinstance(value, dict):
        return " ".join(
            _flatten(item)
            for item in value.values()
        )

    if isinstance(value, list):
        return " ".join(
            _flatten(item)
            for item in value
        )

    return str(value).lower()


def _contains_any(
    text: str,
    keywords: set[str],
) -> int:
    return sum(
        keyword in text
        for keyword in keywords
    )


def _job_location(job: dict[str, Any]) -> str:
    location = job.get("location")

    if isinstance(location, dict):
        return _normalise(
            location.get("name")
            or location.get("city")
            or location.get("text")
        )

    return _normalise(location)


def _job_company(job: dict[str, Any]) -> str:
    company = job.get("company")

    if isinstance(company, dict):
        return _normalise(
            company.get("name")
            or company.get("companyName")
        )

    return _normalise(
        job.get("companyName")
        or company
    )


def score_recruiter_job(
    recruiter: dict[str, Any],
    job: dict[str, Any],
) -> float:
    recruiter_text = _flatten(recruiter)
    job_text = _flatten(job)

    score = 0.0

    recruiter_match = recruiter.get("_match") or {}

    if isinstance(recruiter_match, dict):
        score += min(
            35.0,
            float(
                recruiter_match.get("score", 0)
            ) * 0.35,
        )

    recruiter_role_hits = _contains_any(
        recruiter_text,
        TARGET_ROLE_KEYWORDS,
    )

    job_role_hits = _contains_any(
        job_text,
        TARGET_ROLE_KEYWORDS,
    )

    technology_hits = _contains_any(
        recruiter_text + " " + job_text,
        TECHNOLOGY_KEYWORDS,
    )

    score += min(
        20.0,
        recruiter_role_hits * 5,
    )

    score += min(
        25.0,
        job_role_hits * 5,
    )

    score += min(
        10.0,
        technology_hits * 1.5,
    )

    recruiter_company = _normalise(
        recruiter.get("_match", {}).get(
            "company",
            "",
        )
    )

    job_company = _job_company(job)

    if recruiter_company and job_company:
        if (
            recruiter_company in job_company
            or job_company in recruiter_company
        ):
            score += 20.0

    job_location = _job_location(job)

    if any(
        location in job_location
        for location in TARGET_LOCATIONS
    ):
        score += 5.0

    return round(
        min(100.0, score),
        2,
    )


def match_recruiters_to_jobs(
    recruiters: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    minimum_score: float = 50.0,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    for recruiter in recruiters:
        best_job = None
        best_score = 0.0

        for job in jobs:
            score = score_recruiter_job(
                recruiter,
                job,
            )

            if score > best_score:
                best_score = score
                best_job = job

        if best_job is None:
            continue

        if best_score < minimum_score:
            continue

        matches.append(
            {
                "recruiter": recruiter,
                "job": best_job,
                "score": best_score,
            }
        )

    matches.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches
