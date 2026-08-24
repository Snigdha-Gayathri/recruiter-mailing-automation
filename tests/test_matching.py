import os
import sys
from pathlib import Path

# Make the repository's src/ directory importable when this file is
# executed directly with:
#
#     python tests/test_matching.py
#
# This keeps the test command simple and avoids requiring PYTHONPATH
# configuration in GitHub Actions.
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config_loader import load_profile
from discovery.recruiters import qualify_recruiters
from matching.scorer import score_recruiter_against_jobs
from outreach.gmail import is_valid_email


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    print("=" * 70)
    print("LOCAL MATCHING TEST SUITE")
    print("Apify calls: 0")
    print("Emails sent: 0")
    print("=" * 70)

    profile = load_profile()

    assert_true(
        profile["name"] == "Snigdha Gayathri Mandapati",
        "Candidate profile did not load correctly.",
    )

    assert_true(
        "Bengaluru" in profile["target_locations"],
        "Bengaluru is missing from target locations.",
    )

    assert_true(
        "Hyderabad" in profile["target_locations"],
        "Hyderabad is missing from target locations.",
    )

    print("PASS: profile loads correctly")

    recruiter = {
        "id": "test-recruiter-1",
        "firstName": "Test",
        "lastName": "Recruiter",
        "name": "Test Recruiter",
        "headline": "Technical Recruiter | AI/ML Hiring",
        "linkedinUrl": "https://www.linkedin.com/in/test-recruiter",
        "email": "recruiter@example.com",
        "location": {
            "linkedinText": "Bengaluru, Karnataka, India",
            "parsed": {
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India",
            },
        },
        "currentPosition": [
            {
                "position": "Technical Recruiter",
                "companyName": "AI Company",
                "companyLinkedinUrl": "https://www.linkedin.com/company/ai-company/",
                "company": {
                    "name": "AI Company",
                    "linkedinUrl": "https://www.linkedin.com/company/ai-company/",
                    "website": "https://example.com",
                },
            }
        ],
    }

    jobs = [
        {
            "id": "job-1",
            "title": "AI Engineer",
            "companyName": "AI Company",
            "location": "Bengaluru, Karnataka, India",
            "description": (
                "Build production AI systems using Python, LLMs, RAG, "
                "LangGraph and FastAPI."
            ),
            "url": "https://example.com/jobs/ai-engineer",
        },
        {
            "id": "job-2",
            "title": "Generative AI Engineer",
            "companyName": "AI Company",
            "location": "Hyderabad, Telangana, India",
            "description": (
                "Develop LLM applications, RAG pipelines, agents and "
                "retrieval systems."
            ),
            "url": "https://example.com/jobs/genai-engineer",
        },
    ]

    score, matched_jobs = score_recruiter_against_jobs(
        recruiter,
        jobs,
        profile,
    )

    assert_true(
        score > 0,
        "Relevant recruiter should receive a positive score.",
    )

    assert_true(
        len(matched_jobs) == 2,
        f"Expected 2 matched jobs, got {len(matched_jobs)}.",
    )

    print("PASS: recruiter-to-company-to-job matching")
    print(f"      score={score:.2f}")
    print(f"      jobs={len(matched_jobs)}")

    hyderabad_recruiter = {
        "id": "test-recruiter-2",
        "firstName": "Hyderabad",
        "lastName": "Recruiter",
        "name": "Hyderabad Recruiter",
        "headline": "Machine Learning Recruiter",
        "linkedinUrl": "https://www.linkedin.com/in/hyderabad-recruiter",
        "email": "hyderabad@example.com",
        "location": {
            "linkedinText": "Hyderabad, Telangana, India",
            "parsed": {
                "city": "Hyderabad",
                "state": "Telangana",
                "country": "India",
            },
        },
        "currentPosition": [
            {
                "position": "Machine Learning Recruiter",
                "companyName": "AI Company",
                "companyLinkedinUrl": "https://www.linkedin.com/company/ai-company/",
                "company": {
                    "name": "AI Company",
                    "linkedinUrl": "https://www.linkedin.com/company/ai-company/",
                    "website": "https://example.com",
                },
            }
        ],
    }

    hyderabad_score, hyderabad_jobs = score_recruiter_against_jobs(
        hyderabad_recruiter,
        jobs,
        profile,
    )

    assert_true(
        hyderabad_score > 0,
        "Hyderabad AI/ML recruiter should receive a positive score.",
    )

    assert_true(
        len(hyderabad_jobs) >= 1,
        "Hyderabad AI/ML recruiter should match at least one job.",
    )

    print("PASS: Hyderabad ML recruiter matching")
    print(f"      score={hyderabad_score:.2f}")

    irrelevant_recruiter = {
        "id": "test-recruiter-3",
        "firstName": "Construction",
        "lastName": "Recruiter",
        "name": "Construction Recruiter",
        "headline": "Construction and Architecture Recruiter",
        "linkedinUrl": "https://www.linkedin.com/in/construction-recruiter",
        "email": "construction@example.com",
        "location": {
            "linkedinText": "Mumbai, Maharashtra, India",
            "parsed": {
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
            },
        },
        "currentPosition": [
            {
                "position": "Construction Recruiter",
                "companyName": "Construction Company",
                "companyLinkedinUrl": "https://www.linkedin.com/company/construction/",
                "company": {
                    "name": "Construction Company",
                    "linkedinUrl": "https://www.linkedin.com/company/construction/",
                    "website": "https://example.com",
                },
            }
        ],
    }

    irrelevant_score, irrelevant_jobs = score_recruiter_against_jobs(
        irrelevant_recruiter,
        jobs,
        profile,
    )

    assert_true(
        irrelevant_score <= 0 or len(irrelevant_jobs) == 0,
        "Irrelevant recruiter should be rejected.",
    )

    print("PASS: irrelevant recruiter rejected")

    assert_true(
        not is_valid_email("not-an-email"),
        "Invalid email was incorrectly accepted.",
    )

    assert_true(
        not is_valid_email("recruiter@"),
        "Malformed email was incorrectly accepted.",
    )

    print("PASS: invalid email rejected")

    unrelated_job = {
        "id": "job-unrelated",
        "title": "Senior Civil Engineer",
        "companyName": "Construction Company",
        "location": "Mumbai, Maharashtra, India",
        "description": (
            "Civil engineering, construction management, structural "
            "engineering and site operations."
        ),
        "url": "https://example.com/jobs/civil-engineer",
    }

    unrelated_score, unrelated_jobs = score_recruiter_against_jobs(
        recruiter,
        [unrelated_job],
        profile,
    )

    assert_true(
        unrelated_score <= 0 or len(unrelated_jobs) == 0,
        "Unrelated job was incorrectly matched.",
    )

    print("PASS: unrelated job rejected")

    print("=" * 70)
    print("ALL LOCAL TESTS PASSED")
    print("Apify calls used: 0")
    print("Emails sent: 0")
    print("=" * 70)


if __name__ == "__main__":
    main()
