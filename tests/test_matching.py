from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
CONFIG_DIR = ROOT_DIR / "config"
ASSETS_DIR = ROOT_DIR / "assets"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    qualify_recruiters,
    score_recruiter,
)
from matching.scorer import (
    match_recruiters_to_jobs,
    score_recruiter_job,
)


PASS_COUNT = 0
FAIL_COUNT = 0


def assert_true(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


def run_test(
    name: str,
    function,
) -> None:
    global PASS_COUNT
    global FAIL_COUNT

    try:
        function()

        PASS_COUNT += 1

        print(
            f"PASS: {name}"
        )

    except Exception as exc:
        FAIL_COUNT += 1

        print(
            f"FAIL: {name}"
        )

        print(
            f"      {type(exc).__name__}: {exc}"
        )


def load_profile_directly() -> dict:
    profile_path = (
        CONFIG_DIR
        / "profile.json"
    )

    assert_true(
        profile_path.exists(),
        "config/profile.json does not exist.",
    )

    with profile_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        profile = json.load(file)

    assert_true(
        isinstance(profile, dict),
        "profile.json must contain a JSON object.",
    )

    return profile


def is_valid_email(
    value: str,
) -> bool:
    if not isinstance(
        value,
        str,
    ):
        return False

    value = value.strip()

    if not value:
        return False

    pattern = (
        r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@"
        r"[A-Za-z0-9]"
        r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        r"(?:\.[A-Za-z0-9]"
        r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
    )

    return bool(
        re.match(
            pattern,
            value,
        )
    )


RELEVANT_RECRUITER = {
    "id": "recruiter-001",
    "publicIdentifier": "ai-recruiter",
    "firstName": "Priya",
    "lastName": "Sharma",
    "headline": (
        "Technical Recruiter | AI & Machine Learning | "
        "Generative AI Hiring"
    ),
    "about": (
        "Technical recruiter hiring AI engineers, "
        "machine learning engineers, LLM engineers, "
        "RAG engineers and software engineers."
    ),
    "linkedinUrl": (
        "https://www.linkedin.com/in/ai-recruiter/"
    ),
    "emails": [
        "priya@example.com",
    ],
    "location": {
        "linkedinText": (
            "Bengaluru, Karnataka, India"
        ),
        "parsed": {
            "text": (
                "Bengaluru, Karnataka, India"
            ),
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India",
        },
    },
    "topSkills": [
        "Technical Recruiting",
        "AI Recruiting",
        "Talent Acquisition",
    ],
    "currentPosition": [
        {
            "position": "Technical Recruiter",
            "companyName": "AI Company",
            "description": (
                "Hiring AI engineers, machine learning "
                "engineers, Generative AI engineers, "
                "LLM engineers and software engineers."
            ),
            "company": {
                "name": "AI Company",
                "description": (
                    "Enterprise artificial intelligence "
                    "and machine learning company."
                ),
                "industries": [
                    {
                        "name": "Software Development",
                    }
                ],
            },
        }
    ],
}


HYDERABAD_RECRUITER = {
    "id": "recruiter-002",
    "publicIdentifier": "hyderabad-ai-recruiter",
    "firstName": "Ananya",
    "lastName": "Reddy",
    "headline": (
        "Machine Learning Recruiter | "
        "AI/ML Talent Acquisition"
    ),
    "about": (
        "Recruiter specializing in machine learning, "
        "artificial intelligence, NLP and Generative AI hiring."
    ),
    "linkedinUrl": (
        "https://www.linkedin.com/in/hyderabad-ai-recruiter/"
    ),
    "emails": [
        "ananya@example.com",
    ],
    "location": {
        "linkedinText": (
            "Hyderabad, Telangana, India"
        ),
        "parsed": {
            "text": (
                "Hyderabad, Telangana, India"
            ),
            "city": "Hyderabad",
            "state": "Telangana",
            "country": "India",
        },
    },
    "topSkills": [
        "Machine Learning",
        "Artificial Intelligence",
        "Talent Acquisition",
    ],
    "currentPosition": [
        {
            "position": (
                "Machine Learning Recruiter"
            ),
            "companyName": "AI Company",
            "description": (
                "Hiring machine learning engineers, "
                "AI engineers, LLM engineers and "
                "Generative AI engineers."
            ),
            "company": {
                "name": "AI Company",
                "description": (
                    "Artificial intelligence and "
                    "machine learning software company."
                ),
                "industries": [
                    {
                        "name": "Software Development",
                    }
                ],
            },
        }
    ],
}


IRRELEVANT_RECRUITER = {
    "id": "recruiter-003",
    "publicIdentifier": "construction-recruiter",
    "firstName": "Anees",
    "lastName": "Shaikh",
    "headline": (
        "Headhunter Specialized in Architecture, "
        "Engineering, Construction"
    ),
    "about": (
        "Recruitment professional specializing in "
        "construction, architecture, healthcare and "
        "building materials."
    ),
    "linkedinUrl": (
        "https://www.linkedin.com/in/construction-recruiter/"
    ),
    "emails": [
        "anees@example.com",
    ],
    "location": {
        "linkedinText": (
            "Mumbai, Maharashtra, India"
        ),
        "parsed": {
            "text": (
                "Mumbai, Maharashtra, India"
            ),
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
        },
    },
    "topSkills": [
        "Recruiting",
        "Construction Recruitment",
        "Architecture",
    ],
    "currentPosition": [
        {
            "position": (
                "Senior Talent Acquisition Specialist"
            ),
            "companyName": (
                "Construction Company"
            ),
            "description": (
                "Recruitment for construction "
                "professionals, civil engineers, architects, "
                "site engineers and building specialists."
            ),
            "company": {
                "name": "Construction Company",
                "description": (
                    "Construction and architecture company."
                ),
                "industries": [
                    {
                        "name": "Construction",
                    }
                ],
            },
        }
    ],
}


NO_EMAIL_RECRUITER = {
    **RELEVANT_RECRUITER,
    "id": "recruiter-004",
    "publicIdentifier": "no-email-recruiter",
    "emails": [],
}


AI_ENGINEER_JOB = {
    "id": "job-001",
    "title": "AI Engineer",
    "companyName": "AI Company",
    "location": (
        "Bengaluru, Karnataka, India"
    ),
    "description": (
        "Build production AI systems using Python, "
        "PyTorch, LLMs, RAG, LangGraph, LangChain "
        "and FastAPI."
    ),
    "url": (
        "https://example.com/jobs/ai-engineer"
    ),
}


GENAI_JOB = {
    "id": "job-002",
    "title": "Generative AI Engineer",
    "companyName": "AI Company",
    "location": (
        "Hyderabad, Telangana, India"
    ),
    "description": (
        "Develop LLM applications, RAG pipelines, "
        "agentic AI systems and retrieval infrastructure "
        "using Python, LangChain and vector databases."
    ),
    "url": (
        "https://example.com/jobs/generative-ai"
    ),
}


UNRELATED_JOB = {
    "id": "job-003",
    "title": "Senior Civil Engineer",
    "companyName": "Construction Company",
    "location": (
        "Mumbai, Maharashtra, India"
    ),
    "description": (
        "Design commercial buildings and infrastructure "
        "projects. Civil engineering, structural engineering, "
        "construction management and AutoCAD experience required."
    ),
    "url": (
        "https://example.com/jobs/civil-engineer"
    ),
}


def test_profile_loads() -> None:
    profile = load_profile_directly()

    candidate = profile.get(
        "candidate"
    )

    targeting = profile.get(
        "targeting"
    )

    assert_true(
        isinstance(candidate, dict),
        "candidate section is missing.",
    )

    assert_true(
        isinstance(targeting, dict),
        "targeting section is missing.",
    )

    assert_true(
        candidate.get("name")
        == "Snigdha Gayathri Mandapati",
        "Candidate name is incorrect.",
    )

    assert_true(
        candidate.get("email")
        == "snigdhaisme@gmail.com",
        "Candidate email is incorrect.",
    )

    assert_true(
        candidate.get("linkedin"),
        "LinkedIn URL is missing.",
    )

    assert_true(
        candidate.get("github"),
        "GitHub URL is missing.",
    )

    assert_true(
        candidate.get("portfolio"),
        "Portfolio URL is missing.",
    )

    resume_path = (
        ROOT_DIR
        / candidate.get(
            "resume_path",
            "",
        )
    )

    assert_true(
        resume_path.exists(),
        f"Resume does not exist: {resume_path}",
    )

    locations = targeting.get(
        "locations",
        [],
    )

    assert_true(
        "Remote" in locations,
        "Remote target is missing.",
    )

    assert_true(
        "Bangalore" in locations,
        "Bangalore target is missing.",
    )

    assert_true(
        "Bengaluru" in locations,
        "Bengaluru target is missing.",
    )

    assert_true(
        "Mumbai" in locations,
        "Mumbai target is missing.",
    )

    assert_true(
        "Hyderabad" in locations,
        "Hyderabad target is missing.",
    )

    roles = targeting.get(
        "roles",
        [],
    )

    assert_true(
        "AI Engineer" in roles,
        "AI Engineer role is missing.",
    )

    assert_true(
        "Machine Learning Engineer" in roles,
        "Machine Learning Engineer role is missing.",
    )

    assert_true(
        "LLM Engineer" in roles,
        "LLM Engineer role is missing.",
    )


def test_recruiter_normalization() -> None:
    recruiter = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    assert_true(
        recruiter["name"]
        == "Priya Sharma",
        "Recruiter name normalization failed.",
    )

    assert_true(
        recruiter["title"]
        == "Technical Recruiter",
        "Recruiter title normalization failed.",
    )

    assert_true(
        recruiter["company"]
        == "AI Company",
        "Recruiter company normalization failed.",
    )

    assert_true(
        recruiter["location"]
        == "Bengaluru, Karnataka, India",
        "Recruiter location normalization failed.",
    )

    assert_true(
        recruiter["email"]
        == "priya@example.com",
        "Recruiter email extraction failed.",
    )

    assert_true(
        recruiter["linkedinUrl"]
        == (
            "https://www.linkedin.com/in/"
            "ai-recruiter/"
        ),
        "LinkedIn URL normalization failed.",
    )


def test_recruiter_scoring() -> None:
    result = score_recruiter(
        RELEVANT_RECRUITER
    )

    assert_true(
        isinstance(result, dict),
        "Recruiter score must be a dictionary.",
    )

    assert_true(
        0 <= result["score"] <= 100,
        "Recruiter score must be between 0 and 100.",
    )

    assert_true(
        result["score"] >= 50,
        (
            "Strong AI/ML recruiter should score "
            "at least 50."
        ),
    )

    assert_true(
        result["email"]
        == "priya@example.com",
        "Recruiter score lost email.",
    )

    assert_true(
        result["company"]
        == "AI Company",
        "Recruiter score lost company.",
    )

    assert_true(
        result["title"]
        == "Technical Recruiter",
        "Recruiter score lost title.",
    )


def test_hyderabad_recruiter_scoring() -> None:
    result = score_recruiter(
        HYDERABAD_RECRUITER
    )

    assert_true(
        result["score"] >= 50,
        (
            "Hyderabad AI/ML recruiter should "
            "receive a strong score."
        ),
    )

    assert_true(
        "Hyderabad"
        in result["location"],
        "Hyderabad location was not preserved.",
    )


def test_irrelevant_recruiter_rejected() -> None:
    result = score_recruiter(
        IRRELEVANT_RECRUITER
    )

    assert_true(
        result["score"] < 50,
        (
            "Construction recruiter should "
            "not receive a strong AI/ML score."
        ),
    )

    qualified = qualify_recruiters(
        [
            IRRELEVANT_RECRUITER
        ]
    )

    assert_true(
        len(qualified) == 0,
        "Construction recruiter should be rejected.",
    )


def test_missing_email_rejected() -> None:
    qualified = qualify_recruiters(
        [
            NO_EMAIL_RECRUITER
        ]
    )

    assert_true(
        len(qualified) == 0,
        "Recruiter without email must not qualify.",
    )


def test_email_validation() -> None:
    valid_addresses = [
        "snigdhaisme@gmail.com",
        "recruiter@example.com",
        "technical.recruiter@example.co.in",
    ]

    invalid_addresses = [
        "",
        "not-an-email",
        "missing-at-symbol.com",
        "@example.com",
        "person@",
        "person@example",
    ]

    for email in valid_addresses:
        assert_true(
            is_valid_email(email),
            f"Expected valid email: {email}",
        )

    for email in invalid_addresses:
        assert_true(
            not is_valid_email(email),
            f"Expected invalid email: {email}",
        )


def test_recruiter_deduplication() -> None:
    first = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    duplicate = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    second = normalize_recruiter(
        HYDERABAD_RECRUITER
    )

    result = deduplicate_recruiters(
        [
            first,
            duplicate,
            second,
        ]
    )

    assert_true(
        len(result) == 2,
        (
            "Duplicate LinkedIn profiles "
            "should collapse to one recruiter."
        ),
    )


def test_relevant_job_score() -> None:
    recruiter = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    recruiter["_match"] = score_recruiter(
        RELEVANT_RECRUITER
    )

    ai_score = score_recruiter_job(
        recruiter,
        AI_ENGINEER_JOB,
    )

    genai_score = score_recruiter_job(
        recruiter,
        GENAI_JOB,
    )

    unrelated_score = score_recruiter_job(
        recruiter,
        UNRELATED_JOB,
    )

    assert_true(
        ai_score > 0,
        "AI Engineer job should produce a positive match.",
    )

    assert_true(
        genai_score > 0,
        (
            "Generative AI Engineer job should "
            "produce a positive match."
        ),
    )

    assert_true(
        ai_score > unrelated_score,
        (
            "Relevant AI job must score higher "
            "than unrelated civil engineering job."
        ),
    )

    assert_true(
        genai_score > unrelated_score,
        (
            "Relevant GenAI job must score higher "
            "than unrelated civil engineering job."
        ),
    )


def test_recruiter_to_company_to_job_matching() -> None:
    recruiter = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    recruiter["_match"] = score_recruiter(
        RELEVANT_RECRUITER
    )

    jobs = [
        AI_ENGINEER_JOB,
        GENAI_JOB,
    ]

    matches = match_recruiters_to_jobs(
        [
            recruiter
        ],
        jobs,
        minimum_score=50.0,
    )

    assert_true(
        len(matches) == 1,
        (
            "Relevant recruiter should produce "
            "one best recruiter-job match."
        ),
    )

    match = matches[0]

    assert_true(
        match["recruiter"]["company"]
        == "AI Company",
        "Matched recruiter company is incorrect.",
    )

    assert_true(
        match["job"]["companyName"]
        == "AI Company",
        "Matched job company is incorrect.",
    )

    assert_true(
        match["score"] >= 50.0,
        (
            "Relevant recruiter-job match "
            "did not meet minimum score."
        ),
    )

    print(
        f"      score={match['score']:.2f}"
    )

    print(
        "      jobs=2"
    )


def test_hyderabad_ml_recruiter_matching() -> None:
    recruiter = normalize_recruiter(
        HYDERABAD_RECRUITER
    )

    recruiter["_match"] = score_recruiter(
        HYDERABAD_RECRUITER
    )

    matches = match_recruiters_to_jobs(
        [
            recruiter
        ],
        [
            AI_ENGINEER_JOB,
            GENAI_JOB,
        ],
        minimum_score=50.0,
    )

    assert_true(
        len(matches) >= 1,
        (
            "Hyderabad ML recruiter should "
            "match at least one AI job."
        ),
    )

    best_match = matches[0]

    assert_true(
        best_match["score"] >= 50.0,
        (
            "Hyderabad ML recruiter match "
            "should meet minimum score."
        ),
    )

    print(
        f"      score={best_match['score']:.2f}"
    )


def test_unrelated_job_rejected() -> None:
    recruiter = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    recruiter["_match"] = score_recruiter(
        RELEVANT_RECRUITER
    )

    matches = match_recruiters_to_jobs(
        [
            recruiter
        ],
        [
            UNRELATED_JOB
        ],
        minimum_score=50.0,
    )

    assert_true(
        len(matches) == 0,
        (
            "AI recruiter must not match "
            "an unrelated civil engineering job."
        ),
    )


def test_import_contract() -> None:
    """
    Verify that main.py can actually import the functions
    it declares as dependencies.

    This deliberately happens after all lower-level tests.
    Therefore a broken application integration is reported
    without making the earlier tests consume Apify or Gmail.
    """

    import main

    assert_true(
        callable(main.load_profile),
        "main.load_profile is not callable.",
    )

    assert_true(
        callable(
            main.discover_recruiters
        ),
        "main.discover_recruiters is not callable.",
    )

    assert_true(
        callable(
            main.qualify_against_jobs
        ),
        "main.qualify_against_jobs is not callable.",
    )


def main() -> None:
    print(
        "=" * 70
    )

    print(
        "LOCAL MATCHING TEST SUITE"
    )

    print(
        "Apify calls: 0"
    )

    print(
        "Emails sent: 0"
    )

    print(
        "=" * 70
    )

    tests = [
        (
            "profile loads correctly",
            test_profile_loads,
        ),
        (
            "recruiter normalization",
            test_recruiter_normalization,
        ),
        (
            "recruiter scoring",
            test_recruiter_scoring,
        ),
        (
            "Hyderabad recruiter scoring",
            test_hyderabad_recruiter_scoring,
        ),
        (
            "recruiter qualification",
            test_recruiter_qualification,
        ),
        (
            "irrelevant recruiter rejected",
            test_irrelevant_recruiter_rejected,
        ),
        (
            "missing recruiter email rejected",
            test_missing_email_rejected,
        ),
        (
            "email validation",
            test_email_validation,
        ),
        (
            "recruiter deduplication",
            test_recruiter_deduplication,
        ),
        (
            "relevant recruiter-job scoring",
            test_relevant_job_score,
        ),
        (
            "recruiter-to-company-to-job matching",
            test_recruiter_to_company_to_job_matching,
        ),
        (
            "Hyderabad ML recruiter matching",
            test_hyderabad_ml_recruiter_matching,
        ),
        (
            "unrelated job rejected",
            test_unrelated_job_rejected,
        ),
        (
            "application import contract",
            test_import_contract,
        ),
    ]

    for name, function in tests:
        run_test(
            name,
            function,
        )

    print()
    print(
        "=" * 70
    )

    if FAIL_COUNT:
        print(
            "TEST SUITE FAILED"
        )

        print(
            f"Passed: {PASS_COUNT}"
        )

        print(
            f"Failed: {FAIL_COUNT}"
        )

        print(
            "Apify calls used: 0"
        )

        print(
            "Emails sent: 0"
        )

        print(
            "=" * 70
        )

        raise SystemExit(1)

    print(
        "ALL LOCAL TESTS PASSED"
    )

    print(
        f"Passed: {PASS_COUNT}"
    )

    print(
        "Failed: 0"
    )

    print(
        "Apify calls used: 0"
    )

    print(
        "Emails sent: 0"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()
