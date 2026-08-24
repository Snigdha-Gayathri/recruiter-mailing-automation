from __future__ import annotations

import json
from pathlib import Path

from discovery.recruiters import (
    is_qualified_recruiter,
    qualify_recruiters,
    score_recruiter,
)
from matching.scorer import (
    match_recruiters_to_jobs,
)
from storage.database import (
    load_state,
)


BASE_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BASE_DIR / "fixtures"


def load_json(filename: str):
    path = FIXTURES_DIR / filename

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_profile_loads():
    recruiters = load_json(
        "recruiter_sample.json"
    )

    jobs = load_json(
        "job_sample.json"
    )

    assert len(recruiters) == 3
    assert len(jobs) == 3

    print("PASS: profile loads correctly")


def test_recruiter_qualification():
    recruiters = load_json(
        "recruiter_sample.json"
    )

    qualified = qualify_recruiters(
        recruiters
    )

    identifiers = {
        recruiter["publicIdentifier"]
        for recruiter in qualified
    }

    assert (
        "ai-recruiter-bengaluru"
        in identifiers
    )

    assert (
        "genai-recruiter-hyderabad"
        in identifiers
    )

    assert (
        "aneesshaikh14"
        not in identifiers
    )

    print(
        "PASS: recruiter qualification"
    )


def test_irrelevant_recruiter_rejected():
    recruiters = load_json(
        "recruiter_sample.json"
    )

    irrelevant = recruiters[0]

    score = score_recruiter(
        irrelevant
    )

    assert not is_qualified_recruiter(
        irrelevant
    )

    print(
        "PASS: irrelevant recruiter rejected"
    )

    print(
        f"      score={score['score']}"
    )


def test_recruiter_to_job_matching():
    recruiters = load_json(
        "recruiter_sample.json"
    )

    jobs = load_json(
        "job_sample.json"
    )

    qualified = qualify_recruiters(
        recruiters
    )

    matches = match_recruiters_to_jobs(
        qualified,
        jobs,
        minimum_score=30,
    )

    assert len(matches) >= 2

    companies = {
        match["job"]["companyName"]
        for match in matches
    }

    assert (
        "Example AI Labs"
        in companies
    )

    assert (
        "Example GenAI Systems"
        in companies
    )

    print(
        "PASS: recruiter-to-company-to-job matching"
    )

    for match in matches:
        print(
            f"      score={match['score']}"
        )
        print(
            f"      recruiter="
            f"{match['recruiter']['firstName']}"
        )
        print(
            f"      job="
            f"{match['job']['title']}"
        )


def test_hyderabad_ml_recruiter():
    recruiters = load_json(
        "recruiter_sample.json"
    )

    jobs = load_json(
        "job_sample.json"
    )

    hyderabad = [
        recruiter
        for recruiter in recruiters
        if recruiter["publicIdentifier"]
        == "genai-recruiter-hyderabad"
    ]

    qualified = qualify_recruiters(
        hyderabad
    )

    matches = match_recruiters_to_jobs(
        qualified,
        jobs,
        minimum_score=30,
    )

    assert len(matches) == 1

    assert (
        matches[0]["job"]["companyName"]
        == "Example GenAI Systems"
    )

    print(
        "PASS: Hyderabad ML recruiter matching"
    )

    print(
        f"      score={matches[0]['score']}"
    )


def test_invalid_email_rejected():
    recruiter = {
        "headline": "Technical Recruiter",
        "location": {
            "linkedinText": "Bengaluru, India"
        },
        "about": "Hiring AI and ML engineers.",
        "emails": [
            "not-an-email"
        ],
        "currentPosition": [
            {
                "position": "Technical Recruiter",
                "companyName": "AI Company",
                "description": "Hiring AI Engineers."
            }
        ]
    }

    result = score_recruiter(
        recruiter
    )

    assert result["email"] == ""

    print(
        "PASS: invalid email rejected"
    )


def test_unrelated_job_rejected():
    jobs = load_json(
        "job_sample.json"
    )

    unrelated = jobs[2]

    from discovery.jobs import (
        is_relevant_job,
        score_job,
    )

    assert not is_relevant_job(
        unrelated
    )

    print(
        "PASS: unrelated job rejected"
    )

    print(
        f"      score={score_job(unrelated)}"
    )


def main():
    print("=" * 70)
    print("LOCAL MATCHING TEST SUITE")
    print("=" * 70)
    print("Apify calls: 0")
    print("Emails sent: 0")
    print("=" * 70)

    test_profile_loads()
    test_recruiter_qualification()
    test_recruiter_to_job_matching()
    test_hyderabad_ml_recruiter()
    test_irrelevant_recruiter_rejected()
    test_invalid_email_rejected()
    test_unrelated_job_rejected()

    print("=" * 70)
    print("ALL LOCAL TESTS PASSED")
    print("=" * 70)
    print("Apify calls used: 0")
    print("Emails sent: 0")
    print("=" * 70)


if __name__ == "__main__":
    main()
