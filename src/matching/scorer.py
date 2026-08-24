from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatchResult:
    score: float
    recommendation: str

    role_matches: list[str] = field(
        default_factory=list
    )

    skill_matches: list[str] = field(
        default_factory=list
    )

    project_matches: list[str] = field(
        default_factory=list
    )

    evidence: list[str] = field(
        default_factory=list
    )

    location_match: bool = False
    hiring_signal: bool = False

    recruiter_signal_matches: list[str] = field(
        default_factory=list
    )

    company_signal_matches: list[str] = field(
        default_factory=list
    )


def normalize(text: str) -> str:
    text = str(text or "").lower()

    text = re.sub(
        r"[^a-z0-9+#./& -]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_term(
    text: str,
    term: str
) -> bool:
    normalized_text = normalize(text)
    normalized_term = normalize(term)

    if not normalized_term:
        return False

    return normalized_term in normalized_text


def flatten_skills(
    profile: dict[str, Any]
) -> list[str]:
    skills = profile.get(
        "skills",
        {}
    )

    flattened = []

    for category_values in skills.values():

        if not isinstance(
            category_values,
            list
        ):
            continue

        flattened.extend(
            str(value)
            for value in category_values
        )

    return flattened


def build_recruiter_text(
    recruiter: dict[str, Any]
) -> str:
    raw = recruiter.get(
        "raw",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    fields = [
        recruiter.get(
            "name",
            ""
        ),

        recruiter.get(
            "title",
            ""
        ),

        recruiter.get(
            "company",
            ""
        ),

        recruiter.get(
            "location",
            ""
        ),

        recruiter.get(
            "about",
            ""
        ),

        recruiter.get(
            "job_title",
            ""
        ),

        recruiter.get(
            "job_description",
            ""
        ),

        raw.get(
            "headline",
            ""
        ),

        raw.get(
            "summary",
            ""
        ),

        raw.get(
            "about",
            ""
        ),

        raw.get(
            "occupation",
            ""
        ),

        raw.get(
            "currentJob",
            ""
        ),

        raw.get(
            "currentPosition",
            ""
        ),

        raw.get(
            "industry",
            ""
        )
    ]

    experiences = raw.get(
        "experiences",
        []
    )

    if isinstance(
        experiences,
        list
    ):
        for experience in experiences:

            if not isinstance(
                experience,
                dict
            ):
                continue

            fields.extend(
                [
                    experience.get(
                        "title",
                        ""
                    ),

                    experience.get(
                        "companyName",
                        ""
                    ),

                    experience.get(
                        "description",
                        ""
                    )
                ]
            )

    return " ".join(
        str(field)
        for field in fields
        if field
    )


def get_recruiter_role_signals(
    recruiter_text: str,
    profile: dict[str, Any]
) -> list[str]:
    recruiter_targets = profile.get(
        "recruiter_targets",
        {}
    )

    preferred_titles = recruiter_targets.get(
        "preferred_titles",
        []
    )

    matches = []

    for title in preferred_titles:

        if contains_term(
            recruiter_text,
            title
        ):
            matches.append(
                title
            )

    return matches


def get_target_role_signals(
    recruiter_text: str,
    profile: dict[str, Any]
) -> list[str]:
    targeting = profile.get(
        "targeting",
        {}
    )

    target_roles = targeting.get(
        "roles",
        []
    )

    matches = []

    for role in target_roles:

        if contains_term(
            recruiter_text,
            role
        ):
            matches.append(
                role
            )

    return matches


def get_skill_matches(
    recruiter_text: str,
    profile: dict[str, Any]
) -> list[str]:
    skills = flatten_skills(
        profile
    )

    matches = []

    for skill in skills:

        if contains_term(
            recruiter_text,
            skill
        ):
            matches.append(
                skill
            )

    return matches


def get_project_matches(
    recruiter_text: str,
    profile: dict[str, Any]
) -> tuple[
    list[str],
    list[str]
]:
    projects = profile.get(
        "projects",
        []
    )

    matched_projects = []
    evidence = []

    for project in projects:

        keywords = project.get(
            "keywords",
            []
        )

        matched_keywords = []

        for keyword in keywords:

            if contains_term(
                recruiter_text,
                keyword
            ):
                matched_keywords.append(
                    keyword
                )

        if not matched_keywords:
            continue

        project_name = project.get(
            "name",
            "Unknown Project"
        )

        matched_projects.append(
            project_name
        )

        for item in project.get(
            "evidence",
            []
        ):
            evidence.append(
                f"{project_name}: {item}"
            )

    return (
        matched_projects,
        evidence
    )


def location_matches(
    recruiter_location: str,
    recruiter_text: str,
    profile: dict[str, Any]
) -> bool:
    targeting = profile.get(
        "targeting",
        {}
    )

    target_locations = targeting.get(
        "locations",
        []
    )

    combined_location = " ".join(
        [
            recruiter_location,
            recruiter_text
        ]
    )

    normalized_location = normalize(
        combined_location
    )

    for location in target_locations:

        if contains_term(
            normalized_location,
            location
        ):
            return True

    return False


def get_company_signals(
    recruiter: dict[str, Any],
    recruiter_text: str,
    profile: dict[str, Any]
) -> list[str]:
    recruiter_targets = profile.get(
        "recruiter_targets",
        {}
    )

    company_signals = recruiter_targets.get(
        "preferred_company_signals",
        []
    )

    company = recruiter.get(
        "company",
        ""
    )

    matches = []

    for signal in company_signals:

        if contains_term(
            company,
            signal
        ):
            matches.append(
                signal
            )
            continue

        if contains_term(
            recruiter_text,
            signal
        ):
            matches.append(
                signal
            )

    return matches


def detect_hiring_signal(
    recruiter: dict[str, Any],
    recruiter_text: str
) -> bool:
    explicit_fields = [
        recruiter.get(
            "job_title",
            ""
        ),

        recruiter.get(
            "job_description",
            ""
        ),

        recruiter.get(
            "job_url",
            ""
        )
    ]

    explicit_text = " ".join(
        str(value)
        for value in explicit_fields
        if value
    )

    if explicit_text.strip():
        return True

    hiring_phrases = [
        "hiring",
        "we are hiring",
        "currently hiring",
        "looking for",
        "open roles",
        "open positions",
        "vacancies",
        "talent acquisition",
        "recruiting",
        "recruitment",
        "hiring for",
        "building the team",
        "join our team",
        "careers"
    ]

    for phrase in hiring_phrases:

        if contains_term(
            recruiter_text,
            phrase
        ):
            return True

    return False


def calculate_recruiter_match(
    recruiter: dict[str, Any],
    profile: dict[str, Any]
) -> MatchResult:
    recruiter_text = build_recruiter_text(
        recruiter
    )

    recruiter_role_matches = (
        get_recruiter_role_signals(
            recruiter_text,
            profile
        )
    )

    target_role_matches = (
        get_target_role_signals(
            recruiter_text,
            profile
        )
    )

    skill_matches = get_skill_matches(
        recruiter_text,
        profile
    )

    project_matches, evidence = (
        get_project_matches(
            recruiter_text,
            profile
        )
    )

    location_match = location_matches(
        recruiter.get(
            "location",
            ""
        ),
        recruiter_text,
        profile
    )

    company_signal_matches = (
        get_company_signals(
            recruiter,
            recruiter_text,
            profile
        )
    )

    hiring_signal = detect_hiring_signal(
        recruiter,
        recruiter_text
    )

    score = 0.0

    # --------------------------------------------------------
    # Recruiter identity
    # --------------------------------------------------------

    if recruiter_role_matches:

        score += min(
            25.0,
            15.0
            + (
                len(
                    recruiter_role_matches
                )
                - 1
            )
            * 5.0
        )

    # --------------------------------------------------------
    # Evidence that they recruit for Snigdha's target roles
    # --------------------------------------------------------

    if target_role_matches:

        score += min(
            25.0,
            12.0
            + (
                len(
                    target_role_matches
                )
                * 4.0
            )
        )

    # --------------------------------------------------------
    # Technical overlap
    # --------------------------------------------------------

    score += min(
        20.0,
        len(skill_matches)
        * 1.5
    )

    # --------------------------------------------------------
    # Project/domain overlap
    # --------------------------------------------------------

    project_score = 0.0

    for project in profile.get(
        "projects",
        []
    ):

        project_name = project.get(
            "name"
        )

        if project_name in project_matches:

            priority = float(
                project.get(
                    "priority",
                    5
                )
            )

            project_score += (
                priority * 0.75
            )

    score += min(
        15.0,
        project_score
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    if location_match:
        score += 10.0

    # --------------------------------------------------------
    # Hiring language
    # --------------------------------------------------------

    if hiring_signal:
        score += 5.0

    # --------------------------------------------------------
    # Company relevance
    # --------------------------------------------------------

    score += min(
        10.0,
        len(
            company_signal_matches
        )
        * 3.0
    )

    # --------------------------------------------------------
    # Corporate email bonus
    # --------------------------------------------------------

    if recruiter.get(
        "corporate_email",
        False
    ):
        score += 5.0

    score = min(
        100.0,
        score
    )

    # --------------------------------------------------------
    # Qualification policy
    # --------------------------------------------------------

    matching_config = profile.get(
        "matching",
        {}
    )

    minimum_score = float(
        matching_config.get(
            "minimum_score",
            55
        )
    )

    minimum_recruiter_signal = int(
        matching_config.get(
            "minimum_recruiter_signal",
            1
        )
    )

    require_location = bool(
        matching_config.get(
            "require_location_match",
            True
        )
    )

    require_email = bool(
        matching_config.get(
            "require_email",
            True
        )
    )

    recruiter_has_email = bool(
        recruiter.get(
            "email_valid",
            False
        )
    )

    recruiter_signal_count = (
        len(recruiter_role_matches)
        + len(target_role_matches)
    )

    qualifies = (
        score >= minimum_score
        and recruiter_signal_count
        >= minimum_recruiter_signal
        and (
            location_match
            or not require_location
        )
        and (
            recruiter_has_email
            or not require_email
        )
    )

    recommendation = (
        "OUTREACH"
        if qualifies
        else "REJECT"
    )

    return MatchResult(
        score=round(
            score,
            2
        ),

        recommendation=recommendation,

        role_matches=(
            recruiter_role_matches
            + target_role_matches
        ),

        skill_matches=skill_matches,

        project_matches=project_matches,

        evidence=evidence,

        location_match=location_match,

        hiring_signal=hiring_signal,

        recruiter_signal_matches=(
            recruiter_role_matches
        ),

        company_signal_matches=(
            company_signal_matches
        )
    )


def calculate_match(
    job: dict[str, Any],
    profile: dict[str, Any]
) -> MatchResult:
    """
    Backwards-compatible wrapper.

    The system is recruiter-first, so if the supplied
    object looks like a recruiter, use recruiter matching.
    """

    recruiter = {
        "name": job.get(
            "name",
            ""
        ),

        "email": job.get(
            "email",
            ""
        ),

        "title": job.get(
            "title",
            ""
        ),

        "company": job.get(
            "company",
            ""
        ),

        "location": job.get(
            "location",
            ""
        ),

        "about": job.get(
            "description",
            ""
        ),

        "linkedin_url": job.get(
            "url",
            ""
        ),

        "email_valid": job.get(
            "email_valid",
            False
        ),

        "corporate_email": job.get(
            "corporate_email",
            False
        ),

        "raw": job.get(
            "raw",
            {}
        )
    }

    return calculate_recruiter_match(
        recruiter,
        profile
    )
