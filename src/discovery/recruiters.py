from __future__ import annotations

import os
import random
import time
from typing import Any

import requests


APIFY_BASE_URL = "https://api.apify.com/v2"
DEFAULT_ACTOR_ID = "harvestapi/linkedin-profile-search"

RECRUITER_SEARCH_SEGMENTS = [
    "Recruiter",
    "Technical Recruiter",
    "Talent Acquisition",
    "Talent Acquisition Partner",
    "Technical Talent Acquisition",
    "Talent Sourcer",
    "Technical Sourcer",
    "IT Recruiter",
    "Engineering Recruiter",
    "AI Recruiter",
    "Machine Learning Recruiter",
    "Talent Acquisition Specialist",
]

TARGET_LOCATIONS = [
    "Bengaluru",
    "Bangalore",
    "Mumbai",
    "Hyderabad",
]

RECRUITER_TITLE_KEYWORDS = {
    "recruiter",
    "recruiting",
    "talent acquisition",
    "talent partner",
    "talent sourcer",
    "sourcer",
    "headhunter",
    "technical recruiter",
    "engineering recruiter",
    "recruitment",
}

TECHNICAL_RECRUITING_KEYWORDS = {
    "software",
    "technology",
    "technical",
    "engineering",
    "engineer",
    "developer",
    "machine learning",
    "artificial intelligence",
    "artificial intelligence",
    "ai",
    "ml",
    "data science",
    "data scientist",
    "generative ai",
    "genai",
    "llm",
    "rag",
    "nlp",
    "cloud",
    "devops",
    "platform",
    "backend",
    "frontend",
    "full stack",
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
    "nlp engineer",
    "data scientist",
    "mlops",
    "llm",
    "rag",
    "langchain",
    "langgraph",
    "generative artificial intelligence",
}

IRRELEVANT_INDUSTRIES = {
    "construction",
    "real estate",
    "architecture",
    "hospitality",
    "nursing",
    "healthcare",
    "clinical",
    "medical",
    "pharmaceutical",
    "legal",
    "automotive sales",
    "retail",
    "fashion",
}

IRRELEVANT_RECRUITING_KEYWORDS = {
    "construction",
    "architect",
    "architecture",
    "civil engineer",
    "nurse",
    "nursing",
    "clinical",
    "healthcare",
    "hospitality",
    "hotel",
    "real estate",
    "sales recruitment",
    "blue collar",
}


def _normalise(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.lower().strip()

    return str(value).lower().strip()


def _flatten_profile(profile: dict[str, Any]) -> str:
    parts: list[str] = []

    parts.append(_normalise(profile.get("headline")))
    parts.append(_normalise(profile.get("about")))

    location = profile.get("location") or {}

    if isinstance(location, dict):
        parts.append(_normalise(location.get("linkedinText")))
        parts.append(_normalise(location.get("parsed", {}).get("text")))
        parts.append(_normalise(location.get("parsed", {}).get("city")))
        parts.append(_normalise(location.get("parsed", {}).get("state")))

    current_positions = profile.get("currentPosition") or []

    if isinstance(current_positions, list):
        for position in current_positions:
            if not isinstance(position, dict):
                continue

            parts.append(_normalise(position.get("position")))
            parts.append(_normalise(position.get("description")))
            parts.append(_normalise(position.get("companyName")))

            company = position.get("company") or {}

            if isinstance(company, dict):
                parts.append(_normalise(company.get("name")))
                parts.append(_normalise(company.get("description")))
                parts.append(_normalise(company.get("tagline")))

                industries = company.get("industries") or []

                if isinstance(industries, list):
                    for industry in industries:
                        if isinstance(industry, dict):
                            parts.append(_normalise(industry.get("name")))

    top_skills = profile.get("topSkills") or []

    if isinstance(top_skills, list):
        parts.extend(_normalise(skill) for skill in top_skills)

    return " ".join(part for part in parts if part)


def _get_location(profile: dict[str, Any]) -> str:
    location = profile.get("location") or {}

    if isinstance(location, dict):
        parsed = location.get("parsed") or {}

        if isinstance(parsed, dict):
            city = _normalise(parsed.get("city"))

            if city:
                return city

            text = _normalise(parsed.get("text"))

            if text:
                return text

        text = _normalise(location.get("linkedinText"))

        if text:
            return text

    return ""


def _get_current_company(profile: dict[str, Any]) -> str:
    positions = profile.get("currentPosition") or []

    if not isinstance(positions, list):
        return ""

    for position in positions:
        if not isinstance(position, dict):
            continue

        company_name = position.get("companyName")

        if company_name:
            return str(company_name).strip()

    return ""


def _get_email(profile: dict[str, Any]) -> str:
    emails = profile.get("emails") or []

    if not isinstance(emails, list):
        return ""

    for email in emails:
        if isinstance(email, str) and "@" in email:
            return email.strip()

        if isinstance(email, dict):
            value = (
                email.get("email")
                or email.get("value")
                or email.get("address")
            )

            if isinstance(value, str) and "@" in value:
                return value.strip()

    return ""


def _get_recruiter_title(profile: dict[str, Any]) -> str:
    positions = profile.get("currentPosition") or []

    if isinstance(positions, list):
        for position in positions:
            if not isinstance(position, dict):
                continue

            title = position.get("position")

            if title:
                return str(title).strip()

    headline = profile.get("headline")

    if headline:
        return str(headline).strip()

    return ""


def _contains_any(text: str, keywords: set[str]) -> list[str]:
    return [
        keyword
        for keyword in keywords
        if keyword in text
    ]


def score_recruiter(profile: dict[str, Any]) -> dict[str, Any]:
    text = _flatten_profile(profile)
    title = _normalise(_get_recruiter_title(profile))
    location = _normalise(_get_location(profile))

    score = 0.0
    reasons: list[str] = []

    recruiter_matches = _contains_any(
        title,
        RECRUITER_TITLE_KEYWORDS,
    )

    if recruiter_matches:
        score += 25
        reasons.append(
            f"Recruiting title: {', '.join(recruiter_matches[:3])}"
        )

    technical_matches = _contains_any(
        text,
        TECHNICAL_RECRUITING_KEYWORDS,
    )

    if technical_matches:
        score += min(25, len(technical_matches) * 5)
        reasons.append(
            f"Technical signals: {', '.join(technical_matches[:5])}"
        )

    target_matches = _contains_any(
        text,
        TARGET_ROLE_KEYWORDS,
    )

    if target_matches:
        score += min(30, len(target_matches) * 7)
        reasons.append(
            f"Target-role signals: {', '.join(target_matches[:5])}"
        )

    location_matches = [
        city
        for city in TARGET_LOCATIONS
        if city.lower() in location
    ]

    if location_matches:
        score += 10
        reasons.append(
            f"Target location: {', '.join(location_matches)}"
        )

    email = _get_email(profile)

    if email:
        score += 10
        reasons.append("Public email available")

    irrelevant_matches = _contains_any(
        text,
        IRRELEVANT_RECRUITING_KEYWORDS,
    )

    if irrelevant_matches:
        score -= min(40, len(irrelevant_matches) * 10)
        reasons.append(
            f"Irrelevant-domain signals: {', '.join(irrelevant_matches[:5])}"
        )

    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "reasons": reasons,
        "email": email,
        "location": _get_location(profile),
        "company": _get_current_company(profile),
        "title": _get_recruiter_title(profile),
    }


def is_qualified_recruiter(
    profile: dict[str, Any],
    minimum_score: float = 45.0,
) -> bool:
    result = score_recruiter(profile)

    if result["score"] < minimum_score:
        return False

    title = _normalise(result["title"])
    text = _flatten_profile(profile)

    has_recruiter_signal = bool(
        _contains_any(title, RECRUITER_TITLE_KEYWORDS)
    )

    has_target_signal = bool(
        _contains_any(text, TARGET_ROLE_KEYWORDS)
        or _contains_any(text, TECHNICAL_RECRUITING_KEYWORDS)
    )

    has_irrelevant_signal = bool(
        _contains_any(text, IRRELEVANT_INDUSTRIES)
    )

    if not has_recruiter_signal:
        return False

    if not has_target_signal:
        return False

    if has_irrelevant_signal and result["score"] < 60:
        return False

    return True


def _run_apify_actor(
    actor_id: str,
    actor_input: dict[str, Any],
    timeout_seconds: int = 120,
) -> list[dict[str, Any]]:
    token = os.getenv("APIFY_API_TOKEN")

    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN is not configured."
        )

    actor_id = actor_id.strip()

    if not actor_id:
        raise RuntimeError(
            "APIFY actor ID is empty."
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

    print(f"Apify dataset: {dataset_id}")

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


def _deduplicate_profiles(
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []

    for profile in profiles:
        identifier = (
            profile.get("linkedinUrl")
            or profile.get("publicIdentifier")
            or profile.get("id")
            or _get_email(profile)
        )

        if not identifier:
            continue

        key = str(identifier).strip().lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(profile)

    return unique


def search_recruiters(
    candidate_profile: dict[str, Any],
    max_results: int = 25,
) -> list[dict[str, Any]]:
    actor_id = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        DEFAULT_ACTOR_ID,
    )

    location = random.choice(TARGET_LOCATIONS)

    search_query = os.getenv(
        "RECRUITER_SEARCH_QUERY",
        "Recruiter Talent Acquisition Technical Recruiter "
        "Engineering Recruiter IT Recruiter AI ML GenAI LLM",
    )

    print("RECRUITER DISCOVERY")
    print("Recruiter search strategy: ONE Apify call")
    print(f"Search focus: {search_query}")
    print(f"Search location: {location}")
    print(f"Max recruiter records: {max_results}")
    print(f"Using Apify actor: {actor_id}")

    actor_input = {
        "profileScraperMode": "Full + email search",
        "searchQuery": search_query,
        "locations": [location],
        "maxItems": max_results,
        "startPage": 1,
        "takePages": 1,
    }

    print("Apify input:")
    print(actor_input)

    profiles = _run_apify_actor(
        actor_id=actor_id,
        actor_input=actor_input,
    )

    print(f"Results: {len(profiles)}")

    unique_profiles = _deduplicate_profiles(profiles)

    print(
        f"Unique recruiters: {len(unique_profiles)}"
    )

    return unique_profiles


def qualify_recruiters(
    profiles: list[dict[str, Any]],
    minimum_score: float = 45.0,
) -> list[dict[str, Any]]:
    qualified: list[dict[str, Any]] = []

    for profile in profiles:
        scoring = score_recruiter(profile)

        enriched = dict(profile)

        enriched["_match"] = scoring

        if is_qualified_recruiter(
            profile,
            minimum_score=minimum_score,
        ):
            qualified.append(enriched)

    qualified.sort(
        key=lambda item: item["_match"]["score"],
        reverse=True,
    )

    return qualified
