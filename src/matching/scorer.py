from __future__ import annotations

from dataclasses import dataclass, field
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
    "llm",
    "rag",
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
    "bm25",
    "reranking",
    "cross-encoder",
}


RECRUITER_KEYWORDS = {
    "recruiter",
    "recruiting",
    "talent acquisition",
    "talent partner",
    "talent sourcer",
    "sourcer",
    "headhunter",
    "recruitment",
}


IRRELEVANT_KEYWORDS = {
    "construction",
    "architecture",
    "civil engineer",
    "nurse",
    "nursing",
    "clinical",
    "healthcare recruitment",
    "hospitality",
    "hotel",
    "real estate",
    "building materials",
}


@dataclass
class RecruiterMatch:
    score: float
    recommendation: str
    recruiter: dict[str, Any]

    matching_jobs: list[dict[str, Any]] = field(
        default_factory=list
    )

    role_matches: list[str] = field(
        default_factory=list
    )

    skill_matches: list[str] = field(
        default_factory=list
    )

    project_matches: list[str] = field(
        default_factory=list
    )

    reasons: list[str] = field(
        default_factory=list
    )

    outreach_channel: str = "linkedin"


def _normalise(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).lower().strip()


def _flatten(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.lower()

    if isinstance(
        value,
        dict,
    ):
        return " ".join(
            _flatten(item)
            for item in value.values()
        )

    if isinstance(
        value,
        list,
    ):
        return " ".join(
            _flatten(item)
            for item in value
        )

    return str(
        value
    ).lower()


def _contains(
    text: str,
    keywords: set[str],
) -> list[str]:
    return [
        keyword
        for keyword in keywords
        if keyword in text
    ]


def _job_company(
    job: dict[str, Any],
) -> str:
    company = job.get(
        "company"
    )

    if isinstance(
        company,
        dict,
    ):
        return _normalise(
            company.get("name")
            or company.get("companyName")
        )

    return _normalise(
        job.get("companyName")
        or company
    )


def _company_matches(
    recruiter: dict[str, Any],
    job: dict[str, Any],
) -> bool:
    recruiter_company = _normalise(
        recruiter.get("company")
    )

    job_company = _job_company(
        job
    )

    if not recruiter_company or not job_company:
        return False

    return (
        recruiter_company == job_company
        or recruiter_company in job_company
        or job_company in recruiter_company
    )


def _profile_role_hits(
    recruiter: dict[str, Any],
) -> list[str]:
    return _contains(
        _flatten(recruiter),
        TARGET_ROLE_KEYWORDS,
    )


def _job_role_hits(
    job: dict[str, Any],
) -> list[str]:
    return _contains(
        _flatten(job),
        TARGET_ROLE_KEYWORDS,
    )


def _job_skill_hits(
    job: dict[str, Any],
) -> list[str]:
    return _contains(
        _flatten(job),
        TECHNOLOGY_KEYWORDS,
    )


def _candidate_skill_hits(
    profile: dict[str, Any],
    text: str,
) -> list[str]:
    hits = _contains(
        text,
        TECHNOLOGY_KEYWORDS,
    )

    skills = profile.get(
        "skills",
        {},
    )

    if isinstance(
        skills,
        dict,
    ):
        hits.extend(
            _contains(
                _flatten(skills),
                TECHNOLOGY_KEYWORDS,
            )
        )

    return sorted(
        set(hits)
    )


def calculate_recruiter_match(
    recruiter: dict[str, Any],
    jobs: list[dict[str, Any]],
    profile: dict[str, Any],
    minimum_score: float | None = None,
) -> RecruiterMatch:
    recruiter_text = _flatten(
        recruiter
    )

    title = _normalise(
        recruiter.get("title")
    )

    email = _normalise(
        recruiter.get("email")
    )

    recruiter_roles = _profile_role_hits(
        recruiter
    )

    technical_hits = _contains(
        recruiter_text,
        TECHNOLOGY_KEYWORDS,
    )

    irrelevant_hits = _contains(
        recruiter_text,
        IRRELEVANT_KEYWORDS,
    )

    score = 0.0

    reasons: list[str] = []

    if any(
        keyword in title
        for keyword in RECRUITER_KEYWORDS
    ):
        score += 25

        reasons.append(
            "Direct recruiting or talent-acquisition title."
        )
    else:
        return RecruiterMatch(
            score=0.0,
            recommendation="REJECT",
            recruiter=recruiter,
            reasons=[
                "No direct recruiter or talent-acquisition signal."
            ],
        )

    if recruiter_roles:
        score += min(
            25,
            len(
                recruiter_roles
            ) * 5,
        )

        reasons.append(
            "AI/ML target-role signals found in recruiter profile."
        )

    if technical_hits:
        score += min(
            15,
            len(
                technical_hits
            ) * 2.5,
        )

        reasons.append(
            "Technical hiring signals found."
        )

    location = _normalise(
        recruiter.get("location")
    )

    if any(
        target in location
        for target in TARGET_LOCATIONS
    ):
        score += 10

        reasons.append(
            "Recruiter is in a target location."
        )

    if email:
        score += 15

        reasons.append(
            "Direct email is available."
        )
    else:
        reasons.append(
            "No public email. LinkedIn outreach package required."
        )

    if irrelevant_hits:
        penalty = min(
            50,
            len(
                irrelevant_hits
            ) * 15,
        )

        score -= penalty

        reasons.append(
            "Irrelevant-domain signals found."
        )

    matching_jobs = [
        job
        for job in jobs
        if _company_matches(
            recruiter,
            job,
        )
    ]

    if matching_jobs:
        score += 20

        reasons.append(
            "Recruiter's company has a matching cached job."
        )

        best_job = max(
            matching_jobs,
            key=lambda job: (
                len(
                    _job_role_hits(job)
                ),
                len(
                    _job_skill_hits(job)
                ),
            ),
        )

        job_roles = _job_role_hits(
            best_job
        )

        job_skills = _job_skill_hits(
            best_job
        )

        if job_roles:
            score += min(
                15,
                len(
                    job_roles
                ) * 4,
            )

            reasons.append(
                "Company job matches target AI/ML roles."
            )

        if job_skills:
            score += min(
                10,
                len(
                    job_skills
                ) * 1.5,
            )

            reasons.append(
                "Company job matches candidate technologies."
            )

    else:
        best_job = None
        job_roles = []
        job_skills = []

    score = round(
        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),
        2,
    )

    threshold = (
        minimum_score
        if minimum_score is not None
        else float(
            profile.get(
                "matching",
                {},
            ).get(
                "minimum_score",
                55,
            )
        )
    )

    # THIS IS THE IMPORTANT CHANGE:
    #
    # A recruiter can qualify without an email.
    # The outreach channel is selected afterwards.
    recommendation = (
        "OUTREACH"
        if score >= threshold
        else "REJECT"
    )

    outreach_channel = (
        "email"
        if email
        else "linkedin"
    )

    project_matches: list[str] = []

    projects = profile.get(
        "projects",
        [],
    )

    company_job_text = _flatten(
        best_job
    )

    for project in projects:
        if not isinstance(
            project,
            dict,
        ):
            continue

        keywords = project.get(
            "keywords",
            [],
        )

        if any(
            _normalise(keyword)
            in company_job_text
            for keyword in keywords
        ):
            project_matches.append(
                str(
                    project.get(
                        "name",
                        "",
                    )
                )
            )

    if not project_matches:
        ordered_projects = sorted(
            [
                project
                for project in projects
                if isinstance(
                    project,
                    dict,
                )
            ],
            key=lambda item: item.get(
                "priority",
                0,
            ),
            reverse=True,
        )

        project_matches = [
            str(
                project.get(
                    "name",
                    "",
                )
            )
            for project in ordered_projects[:3]
            if project.get("name")
        ]

    return RecruiterMatch(
        score=score,
        recommendation=recommendation,
        recruiter=recruiter,
        matching_jobs=matching_jobs,
        role_matches=sorted(
            set(
                recruiter_roles
                + job_roles
            )
        ),
        skill_matches=sorted(
            set(
                _candidate_skill_hits(
                    profile,
                    recruiter_text,
                )
                + job_skills
            )
        ),
        project_matches=project_matches[:3],
        reasons=reasons,
        outreach_channel=outreach_channel,
    )


def match_recruiters_to_jobs(
    recruiters: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    profile: dict[str, Any],
    minimum_score: float | None = None,
) -> list[RecruiterMatch]:
    matches = [
        calculate_recruiter_match(
            recruiter,
            jobs,
            profile,
            minimum_score,
        )
        for recruiter in recruiters
    ]

    matches = [
        match
        for match in matches
        if match.recommendation == "OUTREACH"
    ]

    matches.sort(
        key=lambda match: match.score,
        reverse=True,
    )

    return matches
