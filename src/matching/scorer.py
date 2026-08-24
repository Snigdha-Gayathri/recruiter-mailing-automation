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

    recruiter_signal_matches: list[str] = field(
        default_factory=list
    )

    company_signal_matches: list[str] = field(
        default_factory=list
    )

    matching_jobs: list[dict[str, Any]] = field(
        default_factory=list
    )

    evidence: list[str] = field(
        default_factory=list
    )

    location_match: bool = False
    hiring_signal: bool = False


def normalize(
    text: Any
) -> str:
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


def contains(
    text: str,
    term: str
) -> bool:
    return normalize(term) in normalize(text)


def recruiter_text(
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
        recruiter.get("name"),
        recruiter.get("title"),
        recruiter.get("company"),
        recruiter.get("location"),
        recruiter.get("about"),
        raw.get("headline"),
        raw.get("summary"),
        raw.get("about"),
        raw.get("occupation"),
        raw.get("industry")
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
                        "title"
                    ),
                    experience.get(
                        "companyName"
                    ),
                    experience.get(
                        "description"
                    )
                ]
            )

    return " ".join(
        str(value)
        for value in fields
        if value
    )


def recruiter_signals(
    recruiter: dict[str, Any],
    profile: dict[str, Any]
) -> list[str]:
    text = recruiter_text(
        recruiter
    )

    targets = profile.get(
        "recruiter_targets",
        {}
    )

    titles = targets.get(
        "preferred_titles",
        []
    )

    matches = []

    for title in titles:
        if contains(
            text,
            title
        ):
            matches.append(
                title
            )

    return matches


def company_signals(
    recruiter: dict[str, Any],
    profile: dict[str, Any]
) -> list[str]:
    targets = profile.get(
        "recruiter_targets",
        {}
    )

    signals = targets.get(
        "preferred_company_signals",
        []
    )

    company = recruiter.get(
        "company",
        ""
    )

    matches = []

    for signal in signals:
        if contains(
            company,
            signal
        ):
            matches.append(
                signal
            )

    return matches


def skill_list(
    profile: dict[str, Any]
) -> list[str]:
    skills = profile.get(
        "skills",
        {}
    )

    result = []

    for values in skills.values():

        if not isinstance(
            values,
            list
        ):
            continue

        result.extend(
            str(value)
            for value in values
        )

    return list(
        dict.fromkeys(result)
    )


def match_job_to_profile(
    job: dict[str, Any],
    profile: dict[str, Any]
) -> tuple[
    list[str],
    list[str],
    list[str]
]:
    job_text = " ".join(
        [
            job.get(
                "title",
                ""
            ),
            job.get(
                "description",
                ""
            )
        ]
    )

    role_matches = []

    for role in profile.get(
        "targeting",
        {}
    ).get(
        "roles",
        []
    ):
        if contains(
            job_text,
            role
        ):
            role_matches.append(
                role
            )

    skill_matches = []

    for skill in skill_list(
        profile
    ):
        if contains(
            job_text,
            skill
        ):
            skill_matches.append(
                skill
            )

    project_matches = []

    for project in profile.get(
        "projects",
        []
    ):
        project_name = project.get(
            "name",
            ""
        )

        keywords = project.get(
            "keywords",
            []
        )

        if any(
            contains(
                job_text,
                keyword
            )
            for keyword in keywords
        ):
            project_matches.append(
                project_name
            )

    return (
        role_matches,
        skill_matches,
        project_matches
    )


def score_job(
    job: dict[str, Any],
    profile: dict[str, Any]
) -> tuple[
    float,
    list[str],
    list[str],
    list[str]
]:
    (
        role_matches,
        skill_matches,
        project_matches
    ) = match_job_to_profile(
        job,
        profile
    )

    score = 0.0

    score += min(
        40.0,
        len(role_matches) * 10.0
    )

    score += min(
        25.0,
        len(skill_matches) * 2.5
    )

    score += min(
        20.0,
        len(project_matches) * 5.0
    )

    if job.get(
        "location_match",
        False
    ):
        score += 15.0

    return (
        min(
            100.0,
            score
        ),
        role_matches,
        skill_matches,
        project_matches
    )


def calculate_recruiter_match(
    recruiter: dict[str, Any],
    jobs: list[dict[str, Any]],
    profile: dict[str, Any]
) -> MatchResult:

    recruiter_matches = recruiter_signals(
        recruiter,
        profile
    )

    company_matches = company_signals(
        recruiter,
        profile
    )

    best_jobs = []

    all_roles = []
    all_skills = []
    all_projects = []
    evidence = []

    for job in jobs:

        (
            job_score,
            role_matches,
            skill_matches,
            project_matches
        ) = score_job(
            job,
            profile
        )

        enriched_job = dict(
            job
        )

        enriched_job[
            "fit_score"
        ] = round(
            job_score,
            2
        )

        enriched_job[
            "role_matches"
        ] = role_matches

        enriched_job[
            "skill_matches"
        ] = skill_matches

        enriched_job[
            "project_matches"
        ] = project_matches

        best_jobs.append(
            enriched_job
        )

        all_roles.extend(
            role_matches
        )

        all_skills.extend(
            skill_matches
        )

        all_projects.extend(
            project_matches
        )

        if role_matches:
            evidence.append(
                f"{job.get('title', '')} "
                f"in {job.get('location', '')}"
            )

    best_jobs.sort(
        key=lambda job: job.get(
            "fit_score",
            0
        ),
        reverse=True
    )

    best_jobs = best_jobs[:5]

    if not best_jobs:
        return MatchResult(
            score=0,
            recommendation="REJECT"
        )

    best_job_score = best_jobs[0][
        "fit_score"
    ]

    score = 0.0

    # Recruiter quality
    score += min(
        15.0,
        len(recruiter_matches) * 5.0
    )

    # Company quality
    score += min(
        10.0,
        len(company_matches) * 5.0
    )

    # Actual job fit
    score += (
        best_job_score * 0.65
    )

    # Email quality
    if recruiter.get(
        "email_valid",
        False
    ):
        score += 5.0

    if recruiter.get(
        "corporate_email",
        False
    ):
        score += 5.0

    # Current hiring activity
    score += 10.0

    score = min(
        100.0,
        score
    )

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

    qualifies = (
        score >= minimum_score
        and bool(
            best_jobs
        )
        and recruiter.get(
            "email_valid",
            False
        )
    )

    return MatchResult(
        score=round(
            score,
            2
        ),

        recommendation=(
            "OUTREACH"
            if qualifies
            else "REJECT"
        ),

        role_matches=list(
            dict.fromkeys(
                all_roles
            )
        ),

        skill_matches=list(
            dict.fromkeys(
                all_skills
            )
        ),

        project_matches=list(
            dict.fromkeys(
                all_projects
            )
        ),

        recruiter_signal_matches=(
            recruiter_matches
        ),

        company_signal_matches=(
            company_matches
        ),

        matching_jobs=best_jobs,

        evidence=evidence,

        location_match=any(
            job.get(
                "location_match",
                False
            )
            for job in best_jobs
        ),

        hiring_signal=True
    )
