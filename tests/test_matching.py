from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Repository import setup
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ---------------------------------------------------------------------------
# Actual application imports
# ---------------------------------------------------------------------------

from main import load_profile
from discovery.recruiters import (
    normalize_recruiter,
    qualify_recruiters,
    score_recruiter,
)
from matching.scorer import (
    match_recruiters_to_jobs,
    score_recruiter_job,
)
from outreach.gmail import is_valid_email


# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------

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
        print(f"PASS: {name}")
    except Exception as exc:
        FAIL_COUNT += 1
        print(f"FAIL: {name}")
        print(
            f"      {type(exc).__name__}: {exc}"
        )


# ---------------------------------------------------------------------------
# Test fixtures
#
# These deliberately mirror the actual normalized structures expected by
# recruiters.py and scorer.py.
# ---------------------------------------------------------------------------

RELEVANT_RECRUITER = {
    "id": "test-recruiter-1",
    "publicIdentifier": "test-ai-recruiter",
    "firstName": "Priya",
    "lastName": "Recruiter",
    "headline": (
        "Technical Recruiter | AI & Machine Learning | "
        "Generative AI Hiring"
    ),
    "about": (
        "Technical recruiter hiring AI engineers, machine learning "
        "engineers, LLM engineers and software engineers."
    ),
    "linkedinUrl": (
        "https://www.linkedin.com/in/test-ai-recruiter/"
    ),
    "emails": [
        "priya@example.com"
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
        "Recruiting",
        "Technical Recruiting",
        "AI Recruiting",
        "Talent Acquisition",
    ],
    "currentPosition": [
        {
            "position": "Technical Recruiter",
            "companyName": "AI Company",
            "companyLinkedinUrl": (
                "https://www.linkedin.com/company/ai-company/"
            ),
            "description": (
                "Hiring AI engineers, machine learning engineers, "
                "Generative AI engineers, LLM engineers and "
                "software engineers."
            ),
            "company": {
                "name": "AI Company",
                "linkedinUrl": (
                    "https://www.linkedin.com/company/ai-company/"
                ),
                "website": "https://example.com",
                "description": (
                    "Enterprise AI and machine learning company."
                ),
                "industries": [
                    {
                        "name": (
                            "Technology, Information and Internet"
                        )
                    }
                ],
            },
        }
    ],
}


HYDERABAD_RECRUITER = {
    "id": "test-recruiter-2",
    "publicIdentifier": "hyderabad-ml-recruiter",
    "firstName": "Ananya",
    "lastName": "Recruiter",
    "headline": (
        "Machine Learning Recruiter | AI/ML Talent Acquisition"
    ),
    "about": (
        "Recruiter specializing in machine learning, artificial "
        "intelligence, NLP and Generative AI hiring."
    ),
    "linkedinUrl": (
        "https://www.linkedin.com/in/hyderabad-ml-recruiter/"
    ),
    "emails": [
        "ananya@example.com"
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
        "Recruiting",
        "Machine Learning",
        "Artificial Intelligence",
        "Talent Acquisition",
    ],
    "currentPosition": [
        {
            "position": "Machine Learning Recruiter",
            "companyName": "AI Company",
            "companyLinkedinUrl": (
                "https://www.linkedin.com/company/ai-company/"
            ),
            "description": (
                "Hiring machine learning engineers, AI engineers, "
                "LLM engineers and Generative AI engineers."
            ),
            "company": {
                "name": "AI Company",
                "linkedinUrl": (
                    "https://www.linkedin.com/company/ai-company/"
                ),
                "website": "https://example.com",
                "description": (
                    "Artificial intelligence and machine learning "
                    "software company."
                ),
                "industries": [
                    {
                        "name": "Software Development"
                    }
                ],
            },
        }
    ],
}


IRRELEVANT_RECRUITER = {
    "id": "test-recruiter-3",
    "publicIdentifier": "construction-recruiter",
    "firstName": "Anees",
    "lastName": "Shaikh",
    "headline": (
        "Headhunter Specialized in Architecture, Engineering, "
        "Construction"
    ),
    "about": (
        "Recruitment professional specializing in construction, "
        "architecture, healthcare and building materials."
    ),
    "linkedinUrl": (
        "https://www.linkedin.com/in/construction-recruiter/"
    ),
    "emails": [
        "construction@example.com"
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
            "companyLinkedinUrl": (
                "https://www.linkedin.com/company/construction/"
            ),
            "description": (
                "Recruitment for construction professionals, "
                "civil engineers, architects, site engineers, "
                "quantity surveyors and building specialists."
            ),
            "company": {
                "name": "Construction Company",
                "linkedinUrl": (
                    "https://www.linkedin.com/company/construction/"
                ),
                "website": "https://construction.example.com",
                "description": (
                    "Construction and architecture company."
                ),
                "industries": [
                    {
                        "name": "Construction"
                    }
                ],
            },
        }
    ],
}


AI_ENGINEER_JOB = {
    "id": "job-1",
    "title": "AI Engineer",
    "companyName": "AI Company",
    "location": (
        "Bengaluru, Karnataka, India"
    ),
    "description": (
        "Build production AI systems using Python, PyTorch, "
        "LLMs, RAG, LangGraph, LangChain and FastAPI."
    ),
    "url": (
        "https://example.com/jobs/ai-engineer"
    ),
}


GENAI_JOB = {
    "id": "job-2",
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
        "https://example.com/jobs/generative-ai-engineer"
    ),
}


UNRELATED_JOB = {
    "id": "job-3",
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


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------

def test_profile_loads() -> None:
    profile = load_profile()

    assert_true(
        isinstance(profile, dict),
        "Profile must be a dictionary.",
    )

    assert_true(
        "candidate" in profile,
        "Profile is missing candidate section.",
    )

    assert_true(
        "targeting" in profile,
        "Profile is missing targeting section.",
    )

    assert_true(
        profile["candidate"]["name"]
        == "Snigdha Gayathri Mandapati",
        "Candidate name is incorrect.",
    )

    locations = profile[
        "targeting"
    ][
        "locations"
    ]

    assert_true(
        "Bengaluru" in locations,
        "Bengaluru is missing from target locations.",
    )

    assert_true(
        "Mumbai" in locations,
        "Mumbai is missing from target locations.",
    )

    assert_true(
        "Hyderabad" in locations,
        "Hyderabad is missing from target locations.",
    )

    assert_true(
        "Remote" in locations,
        "Remote is missing from target locations.",
    )


def test_recruiter_normalization() -> None:
    recruiter = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    assert_true(
        recruiter["name"]
        == "Priya Recruiter",
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
        == "Bengaluru",
        "Recruiter location normalization failed.",
    )

    assert_true(
        recruiter["email"]
        == "priya@example.com",
        "Recruiter email normalization failed.",
    )


def test_recruiter_scoring() -> None:
    result = score_recruiter(
        RELEVANT_RECRUITER
    )

    assert_true(
        isinstance(result, dict),
        "Recruiter score result must be a dictionary.",
    )

    assert_true(
        result["score"] > 0,
        "Relevant recruiter must receive a positive score.",
    )

    assert_true(
        result["email"]
        == "priya@example.com",
        "Recruiter score result lost email.",
    )

    assert_true(
        result["company"]
        == "AI Company",
        "Recruiter score result lost company.",
    )


def test_recruiter_qualification() -> None:
    qualified = qualify_recruiters(
        [
            RELEVANT_RECRUITER,
            HYDERABAD_RECRUITER,
        ]
    )

    assert_true(
        len(qualified) >= 1,
        "Relevant AI/ML recruiter should qualify.",
    )

    names = {
        recruiter["name"]
        for recruiter in qualified
    }

    assert_true(
        "Priya Recruiter" in names
        or "Ananya Recruiter" in names,
        "Expected AI/ML recruiter was not qualified.",
    )


def test_relevant_recruiter_job_matching() -> None:
    recruiter = normalize_recruiter(
        RELEVANT_RECRUITER
    )

    recruiter["_match"] = score_recruiter(
        RELEVANT_RECRUITER
    )

    score_1 = score_recruiter_job(
        recruiter,
        AI_ENGINEER_JOB,
    )

    score_2 = score_recruiter_job(
        recruiter,
        GENAI_JOB,
    )

    assert_true(
        score_1 > 0,
        "AI Engineer job should match relevant recruiter.",
    )

    assert_true(
        score_2 > 0,
        "Generative AI job should match relevant recruiter.",
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
        len(matches) == 1,
        "Relevant recruiter should produce one recruiter-job match.",
    )

    assert_true(
        matches[0]["score"] >= 50.0,
        "Relevant recruiter-job score should meet threshold.",
    )

    print(
        f"      score={matches[0]['score']:.2f}"
    )

    print(
        "      jobs=2"
    )


def test_hyderabad_ml_matching() -> None:
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
        "Hyderabad ML recruiter should match an AI job.",
    )

    best_match = matches[0]

    assert_true(
        best_match["score"] >= 50.0,
        "Hyderabad ML recruiter score should meet threshold.",
    )

    print(
        f"      score={best_match['score']:.2f}"
    )


def test_irrelevant_recruiter_rejected() -> None:
    recruiter_score = score_recruiter(
        IRRELEVANT_RECRUITER
    )

    recruiter = normalize_recruiter(
        IRRELEVANT_RECRUITER
    )

    recruiter["_match"] = recruiter_score

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
        len(matches) == 0,
        "Construction recruiter must not match AI jobs.",
    )


def test_invalid_email_rejected() -> None:
    invalid_addresses = [
        "",
        "not-an-email",
        "hello",
        "recruiter@",
        "@example.com",
        "recruiter@example",
    ]

    for email in invalid_addresses:
        assert_true(
            not is_valid_email(email),
            f"Invalid email accepted: {email!r}",
        )

    valid_addresses = [
        "recruiter@example.com",
        "hr@company.in",
        "talent.team@company.co.uk",
    ]

    for email in valid_addresses:
        assert_true(
            is_valid_email(email),
            f"Valid email rejected: {email!r}",
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
        "Unrelated civil engineering job must not match AI recruiter.",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    global PASS_COUNT
    global FAIL_COUNT

    print("=" * 70)
    print("LOCAL MATCHING TEST SUITE")
    print("Apify calls: 0")
    print("Emails sent: 0")
    print("=" * 70)

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
            "recruiter qualification",
            test_recruiter_qualification,
        ),
        (
            "recruiter-to-company-to-job matching",
            test_relevant_recruiter_job_matching,
        ),
        (
            "Hyderabad ML recruiter matching",
            test_hyderabad_ml_matching,
        ),
        (
            "irrelevant recruiter rejected",
            test_irrelevant_recruiter_rejected,
        ),
        (
            "invalid email rejected",
            test_invalid_email_rejected,
        ),
        (
            "unrelated job rejected",
            test_unrelated_job_rejected,
        ),
    ]

    for name, function in tests:
        run_test(
            name,
            function,
        )

    print("=" * 70)

    if FAIL_COUNT == 0:
        print("ALL LOCAL TESTS PASSED")
    else:
        print(
            f"LOCAL TESTS FAILED: "
            f"{FAIL_COUNT} failed, "
            f"{PASS_COUNT} passed"
        )

    print(
        f"Apify calls used: 0"
    )

    print(
        f"Emails sent: 0"
    )

    print("=" * 70)

    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
