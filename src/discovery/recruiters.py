from __future__ import annotations

import os
from typing import Any

import requests


APIFY_BASE_URL = "https://api.apify.com/v2"

DEFAULT_ACTOR_ID = "harvestapi/linkedin-profile-search"


RECRUITER_SEARCH_QUERIES = [
    "Recruiter",
    "Technical Recruiter",
    "Engineering Recruiter",
    "IT Recruiter",
    "Talent Acquisition",
    "Talent Acquisition Partner",
    "Talent Acquisition Specialist",
    "Technology Recruiter",
    "Technical Sourcer",
    "Talent Sourcer",
]


TARGET_LOCATIONS = [
    "Bengaluru",
    "Hyderabad",
    "Mumbai",
    "Bangalore",
    "Remote",
]


RECRUITER_SEARCH_SEGMENTS = [
    ("Recruiter", "Bengaluru"),
    ("Recruiter", "Hyderabad"),
    ("Recruiter", "Mumbai"),
    ("Recruiter", "Bangalore"),
    ("Recruiter", "Remote"),
    ("Technical Recruiter", "Bengaluru"),
    ("Technical Recruiter", "Hyderabad"),
    ("Technical Recruiter", "Mumbai"),
    ("Engineering Recruiter", "Bengaluru"),
    ("Engineering Recruiter", "Hyderabad"),
    ("Engineering Recruiter", "Mumbai"),
    ("IT Recruiter", "Bengaluru"),
    ("IT Recruiter", "Hyderabad"),
    ("IT Recruiter", "Mumbai"),
    ("Talent Acquisition", "Bengaluru"),
    ("Talent Acquisition", "Hyderabad"),
    ("Talent Acquisition", "Mumbai"),
    ("Talent Acquisition Partner", "Bengaluru"),
    ("Talent Acquisition Partner", "Hyderabad"),
    ("Talent Acquisition Partner", "Mumbai"),
    ("Technology Recruiter", "Bengaluru"),
    ("Technology Recruiter", "Hyderabad"),
    ("Technology Recruiter", "Mumbai"),
    ("Technical Sourcer", "Bengaluru"),
    ("Technical Sourcer", "Hyderabad"),
    ("Technical Sourcer", "Mumbai"),
    ("Talent Sourcer", "Bengaluru"),
    ("Talent Sourcer", "Hyderabad"),
    ("Talent Sourcer", "Mumbai"),
]


RECRUITER_TITLE_KEYWORDS = {
    "recruiter",
    "recruiting",
    "talent acquisition",
    "talent partner",
    "talent sourcer",
    "sourcer",
    "headhunter",
    "recruitment",
}


TECHNICAL_KEYWORDS = {
    "software",
    "technology",
    "technical",
    "engineering",
    "engineer",
    "developer",
    "machine learning",
    "artificial intelligence",
    " ai ",
    " ml ",
    "data science",
    "data scientist",
    "generative ai",
    "genai",
    "llm",
    "rag",
    "nlp",
    "cloud",
    "devops",
    "backend",
    "frontend",
    "full stack",
    "platform",
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
    "mlops",
    "llm",
    "rag",
    "langchain",
    "langgraph",
}


IRRELEVANT_KEYWORDS = {
    "construction",
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
    "building materials",
}


def _normalise(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_any(
    text: str,
    keywords: set[str],
) -> list[str]:
    lowered = text.lower()

    return [
        keyword
        for keyword in keywords
        if keyword in lowered
    ]


def _get_email(
    profile: dict[str, Any],
) -> str:
    emails = profile.get("emails") or []

    if not isinstance(emails, list):
        return ""

    for item in emails:
        if isinstance(item, str):
            value = item
        elif isinstance(item, dict):
            value = (
                item.get("email")
                or item.get("value")
                or item.get("address")
                or ""
            )
        else:
            value = ""

        if isinstance(value, str) and "@" in value:
            return value.strip().lower()

    return ""


def _get_current_position(
    profile: dict[str, Any],
) -> dict[str, Any]:
    positions = profile.get("currentPosition") or []

    if not isinstance(positions, list):
        return {}

    for position in positions:
        if isinstance(position, dict):
            return position

    return {}


def _get_location(
    profile: dict[str, Any],
) -> str:
    location = profile.get("location") or {}

    if isinstance(location, dict):
        parsed = location.get("parsed") or {}

        if isinstance(parsed, dict):
            return str(
                parsed.get("text")
                or parsed.get("city")
                or location.get("linkedinText")
                or ""
            ).strip()

        return str(
            location.get("linkedinText")
            or ""
        ).strip()

    return str(location or "").strip()


def _get_title(
    profile: dict[str, Any],
) -> str:
    position = _get_current_position(profile)

    return str(
        position.get("position")
        or profile.get("headline")
        or ""
    ).strip()


def _get_company(
    profile: dict[str, Any],
) -> str:
    position = _get_current_position(profile)

    company = position.get("company") or {}

    if not isinstance(company, dict):
        company = {}

    return str(
        position.get("companyName")
        or company.get("name")
        or ""
    ).strip()


def _flatten_profile(
    profile: dict[str, Any],
) -> str:
    position = _get_current_position(profile)

    company = position.get("company") or {}

    if not isinstance(company, dict):
        company = {}

    industries = company.get("industries") or []

    industry_text = ""

    if isinstance(industries, list):
        industry_text = " ".join(
            str(item.get("name", ""))
            for item in industries
            if isinstance(item, dict)
        )

    skills = profile.get("topSkills") or []

    skill_text = ""

    if isinstance(skills, list):
        skill_text = " ".join(
            str(skill)
            for skill in skills
        )

    values = [
        profile.get("headline"),
        profile.get("about"),
        position.get("position"),
        position.get("description"),
        position.get("companyName"),
        company.get("name"),
        company.get("description"),
        company.get("tagline"),
        industry_text,
        skill_text,
    ]

    return " ".join(
        str(value or "")
        for value in values
    ).lower()


def normalize_recruiter(
    profile: dict[str, Any],
) -> dict[str, Any]:
    first_name = str(
        profile.get("firstName")
        or ""
    ).strip()

    last_name = str(
        profile.get("lastName")
        or ""
    ).strip()

    name = " ".join(
        value
        for value in [
            first_name,
            last_name,
        ]
        if value
    ).strip()

    position = _get_current_position(profile)

    return {
        **profile,
        "name": (
            name
            or str(
                profile.get(
                    "publicIdentifier",
                    "",
                )
            ).strip()
        ),
        "title": _get_title(profile),
        "company": _get_company(profile),
        "location": _get_location(profile),
        "email": _get_email(profile),
        "linkedinUrl": str(
            profile.get(
                "linkedinUrl",
                "",
            )
        ).strip(),
        "job_description": str(
            position.get(
                "description",
                "",
            )
        ).strip(),
    }


def deduplicate_recruiters(
    recruiters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []

    for recruiter in recruiters:
        key = _normalise(
            recruiter.get("linkedinUrl")
            or recruiter.get("email")
            or recruiter.get("publicIdentifier")
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(recruiter)

    return result


def score_recruiter(
    profile: dict[str, Any],
) -> dict[str, Any]:
    recruiter = normalize_recruiter(profile)

    text = _flatten_profile(recruiter)
    title = _normalise(recruiter["title"])
    location = _normalise(recruiter["location"])

    score = 0.0
    reasons: list[str] = []

    title_hits = _contains_any(
        title,
        RECRUITER_TITLE_KEYWORDS,
    )

    if title_hits:
        score += 30

        reasons.append(
            "Recruiting title: "
            + ", ".join(title_hits[:3])
        )

    technical_hits = _contains_any(
        text,
        TECHNICAL_KEYWORDS,
    )

    score += min(
        25,
        len(technical_hits) * 5,
    )

    if technical_hits:
        reasons.append(
            "Technical hiring signals: "
            + ", ".join(technical_hits[:5])
        )

    target_hits = _contains_any(
        text,
        TARGET_ROLE_KEYWORDS,
    )

    score += min(
        25,
        len(target_hits) * 6,
    )

    if target_hits:
        reasons.append(
            "Target-role signals: "
            + ", ".join(target_hits[:5])
        )

    if any(
        city.lower() in location
        for city in TARGET_LOCATIONS
    ):
        score += 10
        reasons.append("Target location")

    email = recruiter["email"]

    if email:
        score += 10
        reasons.append("Email available")

    irrelevant_hits = _contains_any(
        text,
        IRRELEVANT_KEYWORDS,
    )

    if irrelevant_hits:
        score -= min(
            45,
            len(irrelevant_hits) * 12,
        )

        reasons.append(
            "Irrelevant-domain signals: "
            + ", ".join(irrelevant_hits[:4])
        )

    if profile.get("recentlyPostedOnLinkedIn"):
        score += 5
        reasons.append(
            "Recently active on LinkedIn"
        )

    return {
        "score": round(
            max(
                0.0,
                min(
                    100.0,
                    score,
                ),
            ),
            2,
        ),
        "reasons": reasons,
        "email": email,
        "location": recruiter["location"],
        "company": recruiter["company"],
        "title": recruiter["title"],
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
        _contains_any(
            title,
            RECRUITER_TITLE_KEYWORDS,
        )
    )

    if not has_recruiter_signal:
        return False

    has_technical_signal = bool(
        _contains_any(
            text,
            TARGET_ROLE_KEYWORDS,
        )
        or _contains_any(
            text,
            TECHNICAL_KEYWORDS,
        )
    )

    if not has_technical_signal:
        return False

    if not result["email"]:
        return False

    irrelevant_hits = _contains_any(
        text,
        IRRELEVANT_KEYWORDS,
    )

    if (
        irrelevant_hits
        and result["score"] < 60
    ):
        return False

    return True


def qualify_recruiters(
    profiles: list[dict[str, Any]],
    minimum_score: float = 45.0,
) -> list[dict[str, Any]]:
    qualified: list[dict[str, Any]] = []

    for profile in profiles:
        if not is_qualified_recruiter(
            profile,
            minimum_score,
        ):
            continue

        recruiter = normalize_recruiter(profile)

        recruiter["_match"] = score_recruiter(
            profile
        )

        qualified.append(recruiter)

    qualified.sort(
        key=lambda item: item["_match"]["score"],
        reverse=True,
    )

    return qualified


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

    encoded_actor_id = (
        actor_id
        .strip()
        .replace("/", "~")
    )

    response = requests.post(
        f"{APIFY_BASE_URL}/acts/"
        f"{encoded_actor_id}/runs",
        params={
            "token": token,
            "waitForFinish": timeout_seconds,
        },
        json=actor_input,
        timeout=timeout_seconds + 30,
    )

    response.raise_for_status()

    run_data = (
        response.json().get("data")
        or {}
    )

    dataset_id = run_data.get(
        "defaultDatasetId"
    )

    if not dataset_id:
        return []

    print(
        f"Apify dataset: {dataset_id}"
    )

    dataset_response = requests.get(
        f"{APIFY_BASE_URL}/datasets/"
        f"{dataset_id}/items",
        params={
            "token": token,
            "format": "json",
            "clean": "true",
        },
        timeout=60,
    )

    dataset_response.raise_for_status()

    items = dataset_response.json()

    if not isinstance(items, list):
        return []

    return [
        item
        for item in items
        if isinstance(item, dict)
    ]


def search_recruiters(
    candidate_profile: dict[str, Any],
    max_results: int = 25,
    search_index: int = 0,
    search_query: str | None = None,
    search_location: str | None = None,
) -> list[dict[str, Any]]:
    """
    Perform exactly one Apify recruiter search.

    search_query and search_location are explicit so the caller
    cannot accidentally select a query from one state index and
    a location from another.
    """

    actor_id = os.getenv(
        "APIFY_RECRUITER_ACTOR",
        DEFAULT_ACTOR_ID,
    )

    if search_query is None:
        search_query = (
            RECRUITER_SEARCH_QUERIES[
                search_index
                % len(RECRUITER_SEARCH_QUERIES)
            ]
        )

    if search_location is None:
        search_location = (
            TARGET_LOCATIONS[
                search_index
                % len(TARGET_LOCATIONS)
            ]
        )

    print(
        f"Using Apify actor: {actor_id}"
    )

    actor_input = {
        "profileScraperMode": (
            "Full + email search"
        ),
        "searchQuery": search_query,
        "locations": [search_location],
        "maxItems": max_results,
        "startPage": 1,
        "takePages": 1,
    }

    print("Apify input:")
    print(actor_input)

    results = _run_apify_actor(
        actor_id=actor_id,
        actor_input=actor_input,
    )

    print(
        f"Results: {len(results)}"
    )

    return results
