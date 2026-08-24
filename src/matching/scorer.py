
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatchResult:
    score: float
    recommendation: str
    role_matches: list[str] = field(default_factory=list)
    skill_matches: list[str] = field(default_factory=list)
    project_matches: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    location_match: bool = False
    hiring_signal: bool = False


def normalize(text: str) -> str:
    text = text or ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./ -]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_term(text: str, term: str) -> bool:
    text = normalize(text)
    term = normalize(term)

    if not term:
        return False

    if term in text:
        return True

    return False


def flatten_skills(profile: dict[str, Any]) -> list[str]:
    skills = profile.get("skills", {})

    flattened = []

    for category_values in skills.values():
        if isinstance(category_values, list):
            flattened.extend(category_values)

    return flattened


def get_project_matches(
    job_text: str,
    profile: dict[str, Any]
) -> tuple[list[str], list[str]]:
    normalized_job = normalize(job_text)

    matched_projects = []
    evidence = []

    projects = profile.get("projects", [])

    for project in projects:
        keywords = project.get("keywords", [])

        matched_keywords = [
            keyword
            for keyword in keywords
            if contains_term(normalized_job, keyword)
        ]

        if matched_keywords:
            matched_projects.append(project["name"])

            for item in project.get("evidence", []):
                evidence.append(
                    f'{project["name"]}: {item}'
                )

    return matched_projects, evidence


def get_role_matches(
    job_title: str,
    profile: dict[str, Any]
) -> list[str]:
    title = normalize(job_title)

    target_roles = profile.get("targeting", {}).get("roles", [])

    matches = []

    for role in target_roles:
        if contains_term(title, role):
            matches.append(role)

    return matches


def get_skill_matches(
    job_text: str,
    profile: dict[str, Any]
) -> list[str]:
    normalized_job = normalize(job_text)

    skills = flatten_skills(profile)

    matches = []

    for skill in skills:
        if contains_term(normalized_job, skill):
            matches.append(skill)

    return matches


def location_matches(
    job_location: str,
    profile: dict[str, Any]
) -> bool:
    normalized_location = normalize(job_location)

    target_locations = (
        profile
        .get("targeting", {})
        .get("locations", [])
    )

    return any(
        contains_term(normalized_location, location)
        for location in target_locations
    )


def calculate_match(
    job: dict[str, Any],
    profile: dict[str, Any]
) -> MatchResult:
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    description = job.get("description", "")

    combined_text = " ".join(
        [
            title,
            company,
            location,
            description
        ]
    )

    role_matches = get_role_matches(title, profile)
    skill_matches = get_skill_matches(combined_text, profile)

    project_matches, evidence = get_project_matches(
        combined_text,
        profile
    )

    location_match = location_matches(
        location,
        profile
    )

    hiring_signal = bool(
        job.get("hiring_signal", False)
        or job.get("url")
        or job.get("description")
    )

    score = 0.0

    # Role relevance: maximum 25 points.
    if role_matches:
        score += min(
            25.0,
            15.0 + (len(role_matches) - 1) * 5.0
        )

    # Technical skill relevance: maximum 20 points.
    score += min(
        20.0,
        len(skill_matches) * 2.0
    )

    # Project evidence: maximum 20 points.
    score += min(
        20.0,
        len(project_matches) * 7.0
    )

    # Location: 15 points.
    if location_match:
        score += 15.0

    # Hiring signal: 10 points.
    if hiring_signal:
        score += 10.0

    # Company relevance: 10 points.
    company_signals = (
        profile
        .get("recruiter_targets", {})
        .get("preferred_company_signals", [])
    )

    company_text = normalize(company)

    if any(
        contains_term(company_text, signal)
        for signal in company_signals
    ):
        score += 10.0

    score = min(100.0, score)

    minimum_score = (
        profile
        .get("matching", {})
        .get("minimum_score", 70)
    )

    minimum_role_match = (
        profile
        .get("matching", {})
        .get("minimum_role_match", 1)
    )

    minimum_skill_match = (
        profile
        .get("matching", {})
        .get("minimum_skill_match", 2)
    )

    require_location = (
        profile
        .get("matching", {})
        .get("require_location_match", True)
    )

    require_hiring_signal = (
        profile
        .get("matching", {})
        .get("require_hiring_signal", True)
    )

    qualifies = (
        score >= minimum_score
        and len(role_matches) >= minimum_role_match
        and len(skill_matches) >= minimum_skill_match
        and (location_match or not require_location)
        and (hiring_signal or not require_hiring_signal)
    )

    recommendation = (
        "OUTREACH"
        if qualifies
        else "REJECT"
    )

    return MatchResult(
        score=round(score, 2),
        recommendation=recommendation,
        role_matches=role_matches,
        skill_matches=skill_matches,
        project_matches=project_matches,
        evidence=evidence,
        location_match=location_match,
        hiring_signal=hiring_signal
    )
