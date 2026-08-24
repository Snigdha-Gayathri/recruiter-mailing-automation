from __future__ import annotations

import json
import os
from pathlib import Path

from discovery.enrichment import enrich_recruiter
from discovery.jobs import search_jobs
from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    search_recruiters,
)
from matching.scorer import calculate_recruiter_match
from outreach.gmail import send_email
from outreach.personalization import generate_personalization
from outreach.templates import choose_template, render_template
from storage.database import (
    get_cached_jobs,
    has_been_contacted,
    increment_stat,
    load_state,
    record_contact,
    save_state,
    set_job_cache,
)


ROOT = Path(__file__).resolve().parents[1]

PROFILE_PATH = (
    ROOT
    / "config"
    / "profile.json"
)

MAX_EMAILS_PER_RUN = int(
    os.getenv(
        "MAX_EMAILS_PER_RUN",
        "5",
    )
)

MAX_APIFY_CALLS_PER_RUN = int(
    os.getenv(
        "MAX_APIFY_CALLS_PER_RUN",
        "1",
    )
)

RUN_MODE = os.getenv(
    "RUN_MODE",
    "recruiter",
).strip().lower()


def load_profile() -> dict:
    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def increment_apify_call(
    state: dict,
) -> None:

    state["_run_apify_calls"] = (
        state.get(
            "_run_apify_calls",
            0,
        )
        + 1
    )

    if (
        state["_run_apify_calls"]
        > MAX_APIFY_CALLS_PER_RUN
    ):
        raise RuntimeError(
            "Apify API budget exceeded: "
            f"{state['_run_apify_calls']} > "
            f"{MAX_APIFY_CALLS_PER_RUN}"
        )

    increment_stat(
        state,
        "apify_calls",
    )


def refresh_job_cache(
    profile: dict,
    state: dict,
) -> None:

    print()
    print(
        "JOB CACHE REFRESH"
    )

    print(
        "This run uses exactly one "
        "Apify call for job discovery."
    )

    jobs = search_jobs()

    increment_apify_call(
        state
    )

    existing_jobs = (
        get_cached_jobs(
            state
        )
    )

    combined = (
        existing_jobs
        + jobs
    )

    deduped = {}

    for job in combined:

        url = str(
            job.get(
                "url",
                "",
            )
        ).strip()

        key = (
            url
            or "|".join(
                [
                    str(
                        job.get(
                            "title",
                            "",
                        )
                    ).lower(),
                    str(
                        job.get(
                            "company",
                            "",
                        )
                    ).lower(),
                    str(
                        job.get(
                            "location",
                            "",
                        )
                    ).lower(),
                ]
            )
        )

        if key:
            deduped[key] = job

    set_job_cache(
        state,
        list(
            deduped.values()
        ),
    )

    increment_stat(
        state,
        "jobs_cached",
        len(jobs),
    )

    print(
        f"New relevant jobs: "
        f"{len(jobs)}"
    )

    print(
        f"Total cached jobs: "
        f"{len(deduped)}"
    )


def discover_recruiters(
    profile: dict,
    state: dict,
) -> list[dict]:

    print()
    print(
        "RECRUITER DISCOVERY"
    )

    raw_recruiters = (
        search_recruiters(
            profile
        )
    )

    increment_apify_call(
        state
    )

    recruiters = []

    for raw in raw_recruiters:

        recruiter = (
            normalize_recruiter(
                raw
            )
        )

        recruiter = (
            enrich_recruiter(
                recruiter
            )
        )

        recruiters.append(
            recruiter
        )

    recruiters = (
        deduplicate_recruiters(
            recruiters
        )
    )

    increment_stat(
        state,
        "discovered",
        len(recruiters),
    )

    print(
        f"Unique recruiters: "
        f"{len(recruiters)}"
    )

    return recruiters


def recruiter_has_valid_email(
    recruiter: dict,
) -> bool:

    email = str(
        recruiter.get(
            "email",
            "",
        )
    ).strip()

    return bool(
        email
        and recruiter.get(
            "email_valid",
            False,
        )
    )


def qualify_recruiters(
    recruiters: list[dict],
    jobs: list[dict],
    profile: dict,
    state: dict,
) -> list[tuple]:

    print()
    print(
        "RECRUITER QUALIFICATION"
    )

    print(
        f"Cached relevant jobs: "
        f"{len(jobs)}"
    )

    qualified = []

    for recruiter in recruiters:

        if has_been_contacted(
            state,
            recruiter,
        ):
            continue

        if not recruiter_has_valid_email(
            recruiter
        ):
            continue

        company = recruiter.get(
            "company",
            "",
        )

        company_jobs = []

        recruiter_company = (
            str(
                company
            )
            .strip()
            .lower()
        )

        if not recruiter_company:
            continue

        for job in jobs:

            job_company = (
                str(
                    job.get(
                        "company",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            if not job_company:
                continue

            if (
                recruiter_company
                == job_company
            ):
                company_jobs.append(
                    job
                )
                continue

            if (
                recruiter_company
                in job_company
                or job_company
                in recruiter_company
            ):
                company_jobs.append(
                    job
                )

        if not company_jobs:
            continue

        for job in company_jobs:
            job[
                "location_match"
            ] = True

        match = (
            calculate_recruiter_match(
                recruiter,
                company_jobs,
                profile,
            )
        )

        if (
            match.recommendation
            != "OUTREACH"
        ):
            continue

        qualified.append(
            (
                recruiter,
                match,
            )
        )

    qualified.sort(
        key=lambda item: (
            item[1].score
        ),
        reverse=True,
    )

    increment_stat(
        state,
        "qualified",
        len(qualified),
    )

    print(
        f"Qualified recruiters: "
        f"{len(qualified)}"
    )

    return qualified


def print_recruiter(
    recruiter: dict,
    match,
) -> None:

    print(
        "-" * 70
    )

    print(
        f"Recruiter: "
        f"{recruiter.get('name', 'Unknown')}"
    )

    print(
        f"Title: "
        f"{recruiter.get('title', 'Unknown')}"
    )

    print(
        f"Company: "
        f"{recruiter.get('company', 'Unknown')}"
    )

    print(
        f"Location: "
        f"{recruiter.get('location', 'Unknown')}"
    )

    print(
        f"Email: "
        f"{recruiter.get('email', 'Unknown')}"
    )

    print(
        f"Match score: "
        f"{match.score}"
    )

    if match.matching_jobs:

        job = match.matching_jobs[0]

        print(
            f"Matching job: "
            f"{job.get('title', 'Unknown')}"
        )

        print(
            f"Job location: "
            f"{job.get('location', 'Unknown')}"
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

    template_name = (
        choose_template(
            recruiter,
            match,
            index,
        )
    )

    personalization = (
        generate_personalization(
            recruiter,
            match,
            candidate,
        )
    )

    subject, body = (
        render_template(
            template_name=template_name,
            recruiter=recruiter,
            match=match,
            candidate=candidate,
            personalization=personalization,
        )
    )

    resume_path = (
        ROOT
        / candidate[
            "resume_path"
        ]
    )

    if not resume_path.exists():

        raise FileNotFoundError(
            f"Resume not found at: "
            f"{resume_path}"
        )

    print(
        f"Sending using template: "
        f"{template_name}"
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

        print(
            f"Reason: {exc}"
        )

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


def run_recruiter_mode(
    profile: dict,
    state: dict,
) -> None:

    jobs = get_cached_jobs(
        state
    )

    if not jobs:

        print()
        print(
            "No cached jobs exist."
        )

        print(
            "Skipping recruiter "
            "discovery."
        )

        print(
            "Apify calls this run: 0"
        )

        return

    recruiters = (
        discover_recruiters(
            profile,
            state,
        )
    )

    candidates = (
        qualify_recruiters(
            recruiters,
            jobs,
            profile,
            state,
        )
    )

    if not candidates:

        print()
        print(
            "No qualified new "
            "recruiters found."
        )

        return

    print()
    print(
        "TOP RECRUITER MATCHES"
    )

    for recruiter, match in (
        candidates[:10]
    ):

        print_recruiter(
            recruiter,
            match,
        )

    selected = candidates[
        :MAX_EMAILS_PER_RUN
    ]

    print()
    print(
        f"SELECTED FOR OUTREACH: "
        f"{len(selected)}"
    )

    for index, (
        recruiter,
        match,
    ) in enumerate(
        selected
    ):

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


def main() -> None:

    print(
        "=" * 70
    )

    print(
        "AI RECRUITER HUNTER"
    )

    print(
        "=" * 70
    )

    profile = load_profile()

    state = load_state()

    state[
        "_run_apify_calls"
    ] = 0

    print(
        f"Mode: {RUN_MODE}"
    )

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

    print(
        f"Apify limit this run: "
        f"{MAX_APIFY_CALLS_PER_RUN}"
    )

    if RUN_MODE == "jobs":

        refresh_job_cache(
            profile,
            state,
        )

    elif RUN_MODE == "recruiter":

        run_recruiter_mode(
            profile,
            state,
        )

    else:

        raise RuntimeError(
            "RUN_MODE must be "
            "'recruiter' or 'jobs'."
        )

    calls = state.get(
        "_run_apify_calls",
        0,
    )

    print()
    print(
        f"Apify calls this run: "
        f"{calls}/"
        f"{MAX_APIFY_CALLS_PER_RUN}"
    )

    state.pop(
        "_run_apify_calls",
        None,
    )

    save_state(
        state
    )

    print()
    print(
        "=" * 70
    )

    print(
        "RUN COMPLETE"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()
