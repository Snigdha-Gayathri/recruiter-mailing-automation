from __future__ import annotations

import json
import os
from pathlib import Path

from discovery.enrichment import (from __future__ import annotations

import os
from pathlib import Path

from discovery.enrichment import (
    enrich_recruiter,
)

from discovery.jobs import (
    jobs_for_company,
    search_jobs,
)

from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    search_recruiters,
)

from matching.scorer import (
    calculate_recruiter_match,
)

from outreach.gmail import (
    send_email,
)

from outreach.personalization import (
    generate_personalization,
)

from outreach.templates import (
    choose_template,
    render_template,
)

from storage.database import (
    get_cached_jobs,
    has_been_contacted,
    increment_stat,
    job_cache_is_fresh,
    load_state,
    record_contact,
    save_state,
    set_job_cache,
)


ROOT = Path(
    __file__
).resolve().parents[1]

PROFILE_PATH = (
    ROOT
    / "config"
    / "profile.json"
)


MAX_APIFY_CALLS = int(
    os.getenv(
        "MAX_APIFY_CALLS_PER_RUN",
        "2",
    )
)

JOB_CACHE_TTL_HOURS = int(
    os.getenv(
        "JOB_CACHE_TTL_HOURS",
        "6",
    )
)


def load_profile() -> dict:
    import json

    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def ensure_apify_budget(
    calls_used: int,
) -> None:
    if calls_used >= MAX_APIFY_CALLS:
        raise RuntimeError(
            "Apify per-run safety limit reached. "
            f"Maximum allowed: "
            f"{MAX_APIFY_CALLS}"
        )


def discover_recruiters(
    profile: dict,
    state: dict,
) -> tuple[list[dict], int]:

    ensure_apify_budget(0)

    raw = search_recruiters(
        profile
    )

    increment_stat(
        state,
        "apify_calls",
    )

    recruiters = [
        normalize_recruiter(
            item
        )
        for item in raw
    ]

    recruiters = [
        enrich_recruiter(
            recruiter
        )
        for recruiter in recruiters
    ]

    recruiters = deduplicate_recruiters(
        recruiters
    )

    return recruiters, 1


def get_jobs(
    state: dict,
) -> tuple[list[dict], int]:

    if job_cache_is_fresh(
        state,
        JOB_CACHE_TTL_HOURS,
    ):
        print(
            "Using cached job data."
        )

        jobs = get_cached_jobs(
            state
        )

        print(
            f"Cached relevant jobs: "
            f"{len(jobs)}"
        )

        return jobs, 0

    ensure_apify_budget(1)

    jobs = search_jobs()

    increment_stat(
        state,
        "apify_calls",
    )

    set_job_cache(
        state,
        jobs,
    )

    print(
        f"Fresh relevant jobs: "
        f"{len(jobs)}"
    )

    return jobs, 1


def qualify_recruiters(
    recruiters: list[dict],
    jobs: list[dict],
    profile: dict,
    state: dict,
) -> list[tuple[dict, object]]:

    candidates = []

    for recruiter in recruiters:

        if has_been_contacted(
            state,
            recruiter,
        ):
            continue

        if not recruiter.get(
            "email_valid",
            False,
        ):
            continue

        company = recruiter.get(
            "company",
            "",
        )

        if not company:
            continue

        company_jobs = jobs_for_company(
            jobs,
            company,
        )

        if not company_jobs:
            continue

        match = calculate_recruiter_match(
            recruiter,
            company_jobs,
            profile,
        )

        if (
            match.recommendation
            != "OUTREACH"
        ):
            continue

        candidates.append(
            (
                recruiter,
                match,
            )
        )

    candidates.sort(
        key=lambda item: (
            item[1].score
        ),
        reverse=True,
    )

    return candidates


def print_candidate(
    recruiter: dict,
    match,
) -> None:

    print(
        "-" * 70
    )

    print(
        f"Recruiter: "
        f"{recruiter.get('name')}"
    )

    print(
        f"Title: "
        f"{recruiter.get('title')}"
    )

    print(
        f"Company: "
        f"{recruiter.get('company')}"
    )

    print(
        f"Location: "
        f"{recruiter.get('location')}"
    )

    print(
        f"Email: "
        f"{recruiter.get('email')}"
    )

    print(
        f"Score: "
        f"{match.score}"
    )

    print(
        "Matching jobs:"
    )

    for job in match.matching_jobs[:3]:

        print(
            f"  - "
            f"{job.get('title')} | "
            f"{job.get('location')} | "
            f"fit="
            f"{job.get('fit_score')}"
        )

        if job.get("url"):
            print(
                f"    {job.get('url')}"
            )

    if match.project_matches:
        print(
            "Relevant projects: "
            + ", ".join(
                match.project_matches[:5]
            )
        )

    if match.skill_matches:
        print(
            "Relevant skills: "
            + ", ".join(
                match.skill_matches[:8]
            )
        )


def send_to_recruiter(
    recruiter: dict,
    match,
    index: int,
    profile: dict,
    state: dict,
) -> bool:

    candidate = profile[
        "candidate"
    ]

    template_name = choose_template(
        recruiter,
        match,
        index,
    )

    personalization = (
        generate_personalization(
            recruiter,
            match,
            candidate,
        )
    )

    subject, body = render_template(
        template_name=template_name,
        recruiter=recruiter,
        match=match,
        candidate=candidate,
        personalization=personalization,
    )

    resume_path = (
        ROOT
        / candidate[
            "resume_path"
        ]
    )

    try:

        message_id = send_email(
            recipient=recruiter[
                "email"
            ],
            subject=subject,
            body=body,
            attachment_path=str(
                resume_path
            ),
        )

        record_contact(
            state=state,
            recruiter=recruiter,
            template=template_name,
            subject=subject,
            message_id=message_id,
            status="sent",
        )

        increment_stat(
            state,
            "emails_sent",
        )

        print(
            f"EMAIL SENT: "
            f"{recruiter.get('email')}"
        )

        return True

    except Exception as exc:

        print(
            f"EMAIL FAILED: "
            f"{recruiter.get('email')}"
        )

        print(exc)

        record_contact(
            state=state,
            recruiter=recruiter,
            template=template_name,
            subject=subject,
            message_id=None,
            status="failed",
        )

        increment_stat(
            state,
            "emails_failed",
        )

        return False


def main():

    print("=" * 70)

    print(
        "AI RECRUITER HUNTER"
    )

    print("=" * 70)

    print(
        f"Apify safety limit: "
        f"{MAX_APIFY_CALLS} calls/run"
    )

    print(
        f"Job cache TTL: "
        f"{JOB_CACHE_TTL_HOURS} hours"
    )

    profile = load_profile()
    state = load_state()

    print()

    print(
        f"Candidate: "
        f"{profile['candidate']['name']}"
    )

    print(
        "Target locations: "
        + ", ".join(
            profile[
                "targeting"
            ][
                "locations"
            ]
        )
    )

    print()
    print(
        "RECRUITER DISCOVERY"
    )

    recruiters, recruiter_calls = (
        discover_recruiters(
            profile,
            state,
        )
    )

    print(
        f"Unique recruiters: "
        f"{len(recruiters)}"
    )

    increment_stat(
        state,
        "discovered",
        len(recruiters),
    )

    print()
    print(
        "JOB DISCOVERY"
    )

    jobs, job_calls = get_jobs(
        state
    )

    total_calls = (
        recruiter_calls
        + job_calls
    )

    print(
        f"Apify calls this run: "
        f"{total_calls}/"
        f"{MAX_APIFY_CALLS}"
    )

    if total_calls > MAX_APIFY_CALLS:
        raise RuntimeError(
            "Internal API budget violation."
        )

    print()
    print(
        "RECRUITER + JOB MATCHING"
    )

    candidates = qualify_recruiters(
        recruiters,
        jobs,
        profile,
        state,
    )

    print(
        f"Qualified recruiters: "
        f"{len(candidates)}"
    )

    increment_stat(
        state,
        "qualified",
        len(candidates),
    )

    if not candidates:
        print()
        print(
            "No qualified new recruiters "
            "with matching current jobs."
        )

        save_state(
            state
        )

        return

    print()
    print(
        "TOP RECRUITERS"
    )

    for recruiter, match in candidates[
        :10
    ]:
        print_candidate(
            recruiter,
            match,
        )

    max_emails = int(
        os.getenv(
            "MAX_EMAILS_PER_RUN",
            "5",
        )
    )

    selected = candidates[
        :max_emails
    ]

    print()
    print(
        f"SELECTED FOR OUTREACH: "
        f"{len(selected)}"
    )

    for index, (
        recruiter,
        match,
    ) in enumerate(selected):

        print()
        print(
            f"OUTREACH "
            f"{index + 1}/"
            f"{len(selected)}"
        )

        send_to_recruiter(
            recruiter,
            match,
            index,
            profile,
            state,
        )

        save_state(
            state
        )

    print()
    print("=" * 70)
    print(
        "RUN COMPLETE"
    )
    print("=" * 70)

    print(
        f"Apify calls this run: "
        f"{total_calls}"
    )

    print(
        f"Emails sent: "
        f"{state['statistics'].get('emails_sent', 0)}"
    )

    print(
        f"Emails failed: "
        f"{state['statistics'].get('emails_failed', 0)}"
    )


if __name__ == "__main__":
    main()
    enrich_recruiter
)

from discovery.jobs import (
    search_company_jobs
)

from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    search_recruiters
)

from matching.scorer import (
    calculate_recruiter_match
)

from outreach.gmail import (
    send_email
)

from outreach.personalization import (
    generate_personalization
)

from outreach.templates import (
    choose_template,
    render_template
)

from storage.database import (
    has_been_contacted,
    increment_stat,
    load_state,
    record_contact,
    save_state
)


ROOT = Path(
    __file__
).resolve().parents[1]

PROFILE_PATH = (
    ROOT
    / "config"
    / "profile.json"
)


def load_profile() -> dict:
    with PROFILE_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def discover_company_jobs(
    recruiters: list[dict]
) -> dict[str, list[dict]]:
    company_jobs = {}

    companies = []

    for recruiter in recruiters:

        company = recruiter.get(
            "company",
            ""
        ).strip()

        if not company:
            continue

        if company.lower() in {
            item.lower()
            for item in companies
        }:
            continue

        companies.append(
            company
        )

    print()
    print(
        f"Unique companies to investigate: "
        f"{len(companies)}"
    )

    max_companies = int(
        os.getenv(
            "MAX_COMPANIES_PER_RUN",
            "10"
        )
    )

    companies = companies[
        :max_companies
    ]

    for company in companies:

        try:

            jobs = search_company_jobs(
                company
            )

            company_jobs[
                company.lower()
            ] = jobs

        except Exception as exc:

            print(
                f"JOB SEARCH FAILED "
                f"for {company}: "
                f"{exc}"
            )

            company_jobs[
                company.lower()
            ] = []

    return company_jobs


def select_top_recruiters(
    recruiters: list[dict],
    company_jobs: dict[str, list[dict]],
    profile: dict,
    state: dict
) -> list[tuple[dict, object]]:

    candidates = []

    for recruiter in recruiters:

        if has_been_contacted(
            state,
            recruiter
        ):
            continue

        if not recruiter.get(
            "email_valid",
            False
        ):
            continue

        company = recruiter.get(
            "company",
            ""
        ).strip()

        jobs = company_jobs.get(
            company.lower(),
            []
        )

        if not jobs:
            continue

        match = calculate_recruiter_match(
            recruiter,
            jobs,
            profile
        )

        if match.recommendation != "OUTREACH":
            continue

        candidates.append(
            (
                recruiter,
                match
            )
        )

    candidates.sort(
        key=lambda item: item[1].score,
        reverse=True
    )

    return candidates


def print_match(
    recruiter: dict,
    match
) -> None:

    print("-" * 70)

    print(
        f"Recruiter: "
        f"{recruiter.get('name')}"
    )

    print(
        f"Title: "
        f"{recruiter.get('title')}"
    )

    print(
        f"Company: "
        f"{recruiter.get('company')}"
    )

    print(
        f"Location: "
        f"{recruiter.get('location')}"
    )

    print(
        f"Email: "
        f"{recruiter.get('email')}"
    )

    print(
        f"Recruiter signals: "
        f"{', '.join(match.recruiter_signal_matches)}"
    )

    print(
        f"Company signals: "
        f"{', '.join(match.company_signal_matches)}"
    )

    print(
        f"Overall score: "
        f"{match.score}"
    )

    print(
        f"Role matches: "
        f"{', '.join(match.role_matches[:10])}"
    )

    print(
        f"Skill matches: "
        f"{', '.join(match.skill_matches[:10])}"
    )

    print(
        f"Project matches: "
        f"{', '.join(match.project_matches[:10])}"
    )

    print(
        "Matching jobs:"
    )

    for job in match.matching_jobs[:3]:

        print(
            f"  - "
            f"{job.get('title')} | "
            f"{job.get('location')} | "
            f"fit={job.get('fit_score')}"
        )

        if job.get("url"):
            print(
                f"    {job.get('url')}"
            )


def send_to_recruiter(
    recruiter: dict,
    match,
    template_index: int,
    profile: dict,
    state: dict
) -> bool:

    candidate = profile[
        "candidate"
    ]

    template_name = choose_template(
        recruiter,
        match,
        template_index
    )

    personalization = (
        generate_personalization(
            recruiter,
            match,
            candidate
        )
    )

    subject, body = render_template(
        template_name=template_name,
        recruiter=recruiter,
        match=match,
        candidate=candidate,
        personalization=personalization
    )

    try:

        message_id = send_email(
            recipient=recruiter[
                "email"
            ],

            subject=subject,

            body=body,

            attachment_path=str(
                ROOT
                / candidate[
                    "resume_path"
                ]
            )
        )

        record_contact(
            state=state,
            recruiter=recruiter,
            template=template_name,
            subject=subject,
            message_id=message_id,
            status="sent"
        )

        increment_stat(
            state,
            "emails_sent"
        )

        return True

    except Exception as exc:

        print(
            f"EMAIL FAILED: "
            f"{recruiter.get('email')}: "
            f"{exc}"
        )

        record_contact(
            state=state,
            recruiter=recruiter,
            template=template_name,
            subject=subject,
            message_id=None,
            status="failed"
        )

        increment_stat(
            state,
            "emails_failed"
        )

        return False


def main():

    print("=" * 70)
    print(
        "AI RECRUITER HUNTER"
    )
    print("=" * 70)

    profile = load_profile()
    state = load_state()

    print(
        f"Candidate: "
        f"{profile['candidate']['name']}"
    )

    print(
        "Target locations: "
        + ", ".join(
            profile[
                "targeting"
            ][
                "locations"
            ]
        )
    )

    print()
    print(
        "RECRUITER DISCOVERY"
    )

    raw_recruiters = search_recruiters(
        profile
    )

    print(
        f"Raw recruiter records: "
        f"{len(raw_recruiters)}"
    )

    recruiters = [
        normalize_recruiter(
            item
        )
        for item in raw_recruiters
    ]

    recruiters = [
        enrich_recruiter(
            recruiter
        )
        for recruiter in recruiters
    ]

    recruiters = deduplicate_recruiters(
        recruiters
    )

    print(
        f"Unique recruiters: "
        f"{len(recruiters)}"
    )

    increment_stat(
        state,
        "discovered",
        len(recruiters)
    )

    print()
    print(
        "CURRENT COMPANY HIRING DISCOVERY"
    )

    company_jobs = discover_company_jobs(
        recruiters
    )

    total_relevant_jobs = sum(
        len(jobs)
        for jobs in company_jobs.values()
    )

    print()
    print(
        f"Relevant current jobs found: "
        f"{total_relevant_jobs}"
    )

    print()
    print(
        "RECRUITER + JOB QUALIFICATION"
    )

    candidates = select_top_recruiters(
        recruiters,
        company_jobs,
        profile,
        state
    )

    print(
        f"Qualified recruiters: "
        f"{len(candidates)}"
    )

    increment_stat(
        state,
        "qualified",
        len(candidates)
    )

    if not candidates:

        print()
        print(
            "No qualified recruiters found "
            "for current matching openings."
        )

        save_state(
            state
        )

        return

    print()
    print(
        "TOP RECRUITERS"
    )

    for recruiter, match in candidates[:10]:

        print_match(
            recruiter,
            match
        )

    max_emails = int(
        os.getenv(
            "MAX_EMAILS_PER_RUN",
            "5"
        )
    )

    selected = candidates[
        :max_emails
    ]

    print()
    print(
        f"SELECTED FOR OUTREACH: "
        f"{len(selected)}"
    )

    for index, (
        recruiter,
        match
    ) in enumerate(
        selected
    ):

        print()
        print("=" * 70)

        print(
            f"OUTREACH {index + 1}/"
            f"{len(selected)}"
        )

        print(
            f"To: "
            f"{recruiter.get('email')}"
        )

        print(
            f"Company: "
            f"{recruiter.get('company')}"
        )

        print(
            f"Score: "
            f"{match.score}"
        )

        send_to_recruiter(
            recruiter,
            match,
            index,
            profile,
            state
        )

        save_state(
            state
        )

    print()
    print("=" * 70)
    print(
        "RUN COMPLETE"
    )
    print("=" * 70)

    print(
        f"Emails sent: "
        f"{state['statistics'].get('emails_sent', 0)}"
    )

    print(
        f"Emails failed: "
        f"{state['statistics'].get('emails_failed', 0)}"
    )


if __name__ == "__main__":
    main()
