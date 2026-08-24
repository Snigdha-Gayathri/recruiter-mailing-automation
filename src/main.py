from __future__ import annotations

import json
import os
from pathlib import Path

from discovery.enrichment import enrich_recruiter
from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    qualify_recruiters,
    search_recruiters,
)
from matching.scorer import calculate_recruiter_match
from outreach.gmail import send_email
from outreach.personalization import generate_personalization
from outreach.templates import (
    choose_template,
    render_template,
)
from storage.database import (
    get_cached_jobs,
    has_been_contacted,
    increment_stat,
    load_state,
    record_contact,
    save_state,
)


ROOT = Path(__file__).resolve().parents[1]

PROFILE_PATH = (
    ROOT
    / "config"
    / "profile.json"
)

SEARCH_STATE_PATH = (
    ROOT
    / "data"
    / "recruiter_search_state.json"
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


RECRUITER_SEARCH_QUERIES = [
    "Recruiter",
    "Technical Recruiter",
    "Engineering Recruiter",
    "IT Recruiter",
    "Talent Acquisition",
    "Talent Acquisition Partner",
    "Talent Acquisition Specialist",
    "Technical Sourcer",
    "Talent Sourcer",
]


RECRUITER_SEARCH_LOCATIONS = [
    "Bengaluru",
    "Mumbai",
    "Hyderabad",
]


def load_profile() -> dict:
    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_search_state() -> dict:
    if not SEARCH_STATE_PATH.exists():
        return {
            "query_index": 0,
            "location_index": 0,
            "runs": 0,
        }

    try:
        data = json.loads(
            SEARCH_STATE_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {
            "query_index": 0,
            "location_index": 0,
            "runs": 0,
        }

    if not isinstance(
        data,
        dict,
    ):
        return {
            "query_index": 0,
            "location_index": 0,
            "runs": 0,
        }

    return {
        "query_index": int(
            data.get(
                "query_index",
                0,
            )
        ),
        "location_index": int(
            data.get(
                "location_index",
                0,
            )
        ),
        "runs": int(
            data.get(
                "runs",
                0,
            )
        ),
    }


def save_search_state(
    state: dict,
) -> None:
    SEARCH_STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    SEARCH_STATE_PATH.write_text(
        json.dumps(
            state,
            indent=2,
        ),
        encoding="utf-8",
    )


def increment_apify_call(
    state: dict,
) -> None:
    calls = (
        state.get(
            "_run_apify_calls",
            0,
        )
        + 1
    )

    state[
        "_run_apify_calls"
    ] = calls

    if calls > MAX_APIFY_CALLS_PER_RUN:
        raise RuntimeError(
            "Apify API budget exceeded: "
            f"{calls} > "
            f"{MAX_APIFY_CALLS_PER_RUN}"
        )

    increment_stat(
        state,
        "apify_calls",
    )


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


def _company_name(
    value,
) -> str:
    if isinstance(
        value,
        dict,
    ):
        return str(
            value.get(
                "name",
                "",
            )
        ).strip().lower()

    return str(
        value or ""
    ).strip().lower()


def find_company_jobs(
    recruiter: dict,
    jobs: list[dict],
) -> list[dict]:
    recruiter_company = _company_name(
        recruiter.get(
            "company",
            "",
        )
    )

    if not recruiter_company:
        return []

    matches = []

    for job in jobs:
        job_company = _company_name(
            job.get(
                "company"
            )
            or job.get(
                "companyName"
            )
        )

        if not job_company:
            continue

        if (
            recruiter_company
            == job_company
        ):
            matches.append(
                job
            )
            continue

        if (
            recruiter_company
            in job_company
            or job_company
            in recruiter_company
        ):
            matches.append(
                job
            )

    return matches


def discover_recruiters(
    profile: dict,
    state: dict,
    search_state: dict,
) -> list[dict]:
    query_index = (
        search_state[
            "query_index"
        ]
    )

    location_index = (
        search_state[
            "location_index"
        ]
    )

    query = RECRUITER_SEARCH_QUERIES[
        query_index
        % len(
            RECRUITER_SEARCH_QUERIES
        )
    ]

    location = RECRUITER_SEARCH_LOCATIONS[
        location_index
        % len(
            RECRUITER_SEARCH_LOCATIONS
        )
    ]

    print()
    print(
        "RECRUITER DISCOVERY"
    )

    print(
        f"Rotation: "
        f"query={query_index}, "
        f"location={location_index}"
    )

    print(
        f"Query: {query}"
    )

    print(
        f"Location: {location}"
    )

    raw_recruiters = (
        search_recruiters(
            profile,
            max_results=25,
            search_index=(
                query_index
            ),
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


def qualify_against_jobs(
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

        company_jobs = find_company_jobs(
            recruiter,
            jobs,
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
        key=lambda item: item[1].score,
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
        "Recruiter: "
        + str(
            recruiter.get(
                "name",
                "Unknown",
            )
        )
    )

    print(
        "Title: "
        + str(
            recruiter.get(
                "title",
                "Unknown",
            )
        )
    )

    print(
        "Company: "
        + str(
            recruiter.get(
                "company",
                "Unknown",
            )
        )
    )

    print(
        "Location: "
        + str(
            recruiter.get(
                "location",
                "Unknown",
            )
        )
    )

    print(
        "Email: "
        + str(
            recruiter.get(
                "email",
                "Unknown",
            )
        )
    )

    print(
        "Match score: "
        + str(
            match.score
        )
    )

    if match.matching_jobs:
        job = (
            match.matching_jobs[0]
        )

        print(
            "Matching job: "
            + str(
                job.get(
                    "title",
                    "Unknown",
                )
            )
        )

        print(
            "Job location: "
            + str(
                job.get(
                    "location",
                    "Unknown",
                )
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

    if not resume_path.exists():
        raise FileNotFoundError(
            "Resume not found at: "
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
            "EMAIL SENT: "
            + recruiter["email"]
        )

        return True

    except Exception as exc:
        print(
            "EMAIL FAILED: "
            + recruiter["email"]
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

    search_state = load_search_state()

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

    jobs = get_cached_jobs(
        state
    )

    if not jobs:
        print()
        print(
            "No cached jobs available."
        )

        print(
            "This run will perform "
            "recruiter discovery only."
        )

        print(
            "Recruiters will only be "
            "eligible for outreach when "
            "their company matches a "
            "cached target job."
        )

    recruiters = discover_recruiters(
        profile,
        state,
        search_state,
    )

    candidates = qualify_against_jobs(
        recruiters,
        jobs,
        profile,
        state,
    )

    if not candidates:
        print()
        print(
            "No qualified new "
            "recruiters found."
        )

    else:
        print()
        print(
            "TOP RECRUITER MATCHES"
        )

        for recruiter, match in candidates[:10]:
            print_recruiter(
                recruiter,
                match,
            )

        selected = candidates[
            :MAX_EMAILS_PER_RUN
        ]

        print()
        print(
            "SELECTED FOR OUTREACH: "
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

    search_state[
        "query_index"
    ] = (
        search_state[
            "query_index"
        ]
        + 1
    ) % len(
        RECRUITER_SEARCH_QUERIES
    )

    search_state[
        "location_index"
    ] = (
        search_state[
            "location_index"
        ]
        + 1
    ) % len(
        RECRUITER_SEARCH_LOCATIONS
    )

    search_state[
        "runs"
    ] = (
        search_state.get(
            "runs",
            0,
        )
        + 1
    )

    save_search_state(
        search_state
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
