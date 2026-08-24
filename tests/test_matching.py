from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT / "src"),
)


from matching.scorer import (
    calculate_recruiter_match,
)


PROFILE_PATH = (
    ROOT
    / "config"
    / "profile.json"
)

RECRUITERS_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "mock_recruiters.json"
)

JOBS_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "mock_jobs.json"
)


def load_json(
    path: Path,
):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def assert_true(
    condition: bool,
    message: str,
):
    if not condition:
        raise AssertionError(
            message
        )


def test_profile_loads():

    profile = load_json(
        PROFILE_PATH
    )

    assert_true(
        profile["candidate"]["name"]
        == "Snigdha Gayathri Mandapati",
        "Candidate profile is incorrect.",
    )

    assert_true(
        len(
            profile["targeting"]["roles"]
        )
        > 5,
        "Expected multiple target roles.",
    )

    assert_true(
        len(
            profile["skills"]["llm"]
        )
        > 0,
        "LLM skills are missing.",
    )

    assert_true(
        len(
            profile["projects"]
        )
        >= 5,
        "Project history is unexpectedly incomplete.",
    )

    print(
        "PASS: profile loads correctly"
    )


def test_recruiter_company_job_match():

    profile = load_json(
        PROFILE_PATH
    )

    recruiters = load_json(
        RECRUITERS_PATH
    )

    jobs = load_json(
        JOBS_PATH
    )

    ananya = next(
        recruiter
        for recruiter in recruiters
        if recruiter["name"]
        == "Ananya Rao"
    )

    ai_labs_jobs = [
        job
        for job in jobs
        if job["company"]
        == "Example AI Labs"
    ]

    result = (
        calculate_recruiter_match(
            ananya,
            ai_labs_jobs,
            profile,
        )
    )

    assert_true(
        result.recommendation
        == "OUTREACH",
        "Ananya should qualify for outreach.",
    )

    assert_true(
        result.score >= 55,
        f"Expected score >= 55, got {result.score}.",
    )

    assert_true(
        len(result.matching_jobs)
        > 0,
        "Expected matching AI jobs.",
    )

    assert_true(
        any(
            "Generative AI"
            in role
            or "AI Engineer"
            in role
            or "LLM"
            in role
            or "RAG"
            in role
            for role in result.role_matches
        ),
        "Expected AI role matches.",
    )

    print(
        "PASS: recruiter-to-company-to-job matching"
    )

    print(
        f"      score={result.score}"
    )

    print(
        f"      jobs={len(result.matching_jobs)}"
    )


def test_hyderabad_ml_recruiter():

    profile = load_json(
        PROFILE_PATH
    )

    recruiters = load_json(
        RECRUITERS_PATH
    )

    jobs = load_json(
        JOBS_PATH
    )

    rahul = next(
        recruiter
        for recruiter in recruiters
        if recruiter["name"]
        == "Rahul Mehta"
    )

    ml_jobs = [
        job
        for job in jobs
        if job["company"]
        == "Example ML Systems"
    ]

    result = (
        calculate_recruiter_match(
            rahul,
            ml_jobs,
            profile,
        )
    )

    assert_true(
        result.recommendation
        == "OUTREACH",
        "Rahul should qualify for outreach.",
    )

    assert_true(
        result.location_match,
        "Hyderabad job should match target location.",
    )

    print(
        "PASS: Hyderabad ML recruiter matching"
    )

    print(
        f"      score={result.score}"
    )


def test_irrelevant_recruiter_is_rejected():

    profile = load_json(
        PROFILE_PATH
    )

    recruiters = load_json(
        RECRUITERS_PATH
    )

    jobs = load_json(
        JOBS_PATH
    )

    david = next(
        recruiter
        for recruiter in recruiters
        if recruiter["name"]
        == "David Wilson"
    )

    retail_jobs = [
        job
        for job in jobs
        if job["company"]
        == "Example Retail"
    ]

    result = (
        calculate_recruiter_match(
            david,
            retail_jobs,
            profile,
        )
    )

    assert_true(
        result.recommendation
        != "OUTREACH",
        "Irrelevant recruiter should not qualify.",
    )

    print(
        "PASS: irrelevant recruiter rejected"
    )


def test_invalid_email_is_not_outreach_candidate():

    profile = load_json(
        PROFILE_PATH
    )

    recruiters = load_json(
        RECRUITERS_PATH
    )

    jobs = load_json(
        JOBS_PATH
    )

    meera = next(
        recruiter
        for recruiter in recruiters
        if recruiter["name"]
        == "Meera Iyer"
    )

    ai_labs_jobs = [
        job
        for job in jobs
        if job["company"]
        == "Example AI Labs"
    ]

    result = (
        calculate_recruiter_match(
            meera,
            ai_labs_jobs,
            profile,
        )
    )

    assert_true(
        not meera["email_valid"],
        "Fixture should represent an invalid email.",
    )

    assert_true(
        result.recommendation
        != "OUTREACH",
        "Invalid-email recruiter must not qualify.",
    )

    print(
        "PASS: invalid email rejected"
    )


def test_unrelated_job_is_not_a_good_fit():

    profile = load_json(
        PROFILE_PATH
    )

    recruiters = load_json(
        RECRUITERS_PATH
    )

    jobs = load_json(
        JOBS_PATH
    )

    ananya = next(
        recruiter
        for recruiter in recruiters
        if recruiter["name"]
        == "Ananya Rao"
    )

    unrelated_jobs = [
        job
        for job in jobs
        if job["company"]
        == "Unrelated Company"
    ]

    result = (
        calculate_recruiter_match(
            ananya,
            unrelated_jobs,
            profile,
        )
    )

    assert_true(
        result.recommendation
        != "OUTREACH",
        "Unrelated job must not produce outreach.",
    )

    print(
        "PASS: unrelated job rejected"
    )


def main():

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
        test_profile_loads,
        test_recruiter_company_job_match,
        test_hyderabad_ml_recruiter,
        test_irrelevant_recruiter_is_rejected,
        test_invalid_email_is_not_outreach_candidate,
        test_unrelated_job_is_not_a_good_fit,
    ]

    failures = 0

    for test in tests:

        try:
            test()

        except Exception as exc:

            failures += 1

            print(
                f"FAIL: {test.__name__}"
            )

            print(
                f"      {exc}"
            )

    print()
    print(
        "=" * 70
    )

    if failures:

        print(
            f"FAILED: {failures} test(s)"
        )

        raise SystemExit(1)

    print(
        "ALL LOCAL TESTS PASSED"
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
