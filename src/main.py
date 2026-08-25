from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(
        0,
        str(SRC),
    )


from discovery.enrichment import (
    enrich_recruiter,
)

from discovery.recruiters import (
    RECRUITER_SEARCH_SEGMENTS,
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
    generate_linkedin_messages,
    generate_personalization,
)

from outreach.templates import (
    choose_template,
    render_linkedin_package,
    render_template,
)

from storage.database import (
    get_cached_jobs,
    has_been_contacted,
    increment_run,
    increment_stat,
    load_state,
    mark_recruiter_seen,
    record_contact,
    record_template_usage,
    save_state,
)


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


MAX_LINKEDIN_PACKAGES_PER_RUN = int(
    os.getenv(
        "MAX_LINKEDIN_PACKAGES_PER_RUN",
        "10",
    )
)


MAX_APIFY_CALLS_PER_RUN = int(
    os.getenv(
        "MAX_APIFY_CALLS_PER_RUN",
        "1",
    )
)


SEARCH_STATE_PATH = (
    ROOT
    / "data"
    / "recruiter_search_state.json"
)


def load_profile() -> dict:
    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_search_state() -> dict:
    if not SEARCH_STATE_PATH.exists():
        return {
            "segment_index": 0,
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
            "segment_index": 0,
            "runs": 0,
        }

    if not isinstance(
        data,
        dict,
    ):
        return {
            "segment_index": 0,
            "runs": 0,
        }

    return {
        "segment_index": int(
            data.get(
                "segment_index",
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


def consume_apify_call(
    state: dict,
) -> None:
    calls = int(
        state.get(
            "_run_apify_calls",
            0,
        )
    ) + 1

    if calls > MAX_APIFY_CALLS_PER_RUN:
        raise RuntimeError(
            "Apify API budget exceeded: "
            f"{calls} > "
            f"{MAX_APIFY_CALLS_PER_RUN}"
        )

    state[
        "_run_apify_calls"
    ] = calls

    increment_stat(
        state,
        "apify_calls",
    )


def discover_recruiters(
    profile: dict,
    state: dict,
    search_state: dict,
) -> list[dict]:
    segment_index = (
        search_state.get(
            "segment_index",
            0,
        )
        % len(
            RECRUITER_SEARCH_SEGMENTS
        )
    )

    search_query, search_location = (
        RECRUITER_SEARCH_SEGMENTS[
            segment_index
        ]
    )

    print()
    print(
        "RECRUITER DISCOVERY"
    )

    print(
        "Recruiter search strategy: "
        "ONE Apify call"
    )

    print(
        f"Search segment: "
        f"{segment_index + 1}/"
        f"{len(RECRUITER_SEARCH_SEGMENTS)}"
    )

    print(
        f"Search query: "
        f"{search_query}"
    )

    print(
        f"Search location: "
        f"{search_location}"
    )

    print(
        "Max recruiter records: 25"
    )

    raw = search_recruiters(
        profile,
        max_results=25,
        search_query=search_query,
        search_location=search_location,
    )

    consume_apify_call(
        state
    )

    recruiters = []

    for item in raw:
        recruiter = normalize_recruiter(
            item
        )

        recruiter = enrich_recruiter(
            recruiter
        )

        mark_recruiter_seen(
            state,
            recruiter,
        )

        recruiters.append(
            recruiter
        )

    recruiters = deduplicate_recruiters(
        recruiters
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


def qualify_recruiters(
    recruiters: list[dict],
    jobs: list[dict],
    profile: dict,
    state: dict,
) -> list[tuple[dict, object]]:
    print()
    print(
        "RECRUITER QUALIFICATION"
    )

    if jobs:
        print(
            f"Cached jobs available: "
            f"{len(jobs)}"
        )
    else:
        print(
            "No cached jobs available."
        )

        print(
            "Using recruiter-profile "
            "AI/ML hiring signals."
        )

    qualified = []

    minimum_score = float(
        profile.get(
            "matching",
            {},
        ).get(
            "minimum_score",
            55,
        )
    )

    for recruiter in recruiters:
        if has_been_contacted(
            state,
            recruiter,
        ):
            continue

        match = calculate_recruiter_match(
            recruiter,
            jobs,
            profile,
            minimum_score=minimum_score,
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

    email_count = sum(
        bool(
            recruiter.get(
                "email"
            )
        )
        for recruiter, _ in qualified
    )

    linkedin_count = (
        len(qualified)
        - email_count
    )

    print(
        f"Qualified recruiters: "
        f"{len(qualified)}"
    )

    print(
        f"  Email outreach: "
        f"{email_count}"
    )

    print(
        f"  LinkedIn packages: "
        f"{linkedin_count}"
    )

    return qualified


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
            "Resume not found: "
            f"{resume_path}"
        )

    print()
    print(
        f"EMAIL OUTREACH -> "
        f"{recruiter.get('name', 'Unknown')}"
    )

    print(
        f"Email: "
        f"{recruiter.get('email', '')}"
    )

    print(
        f"Company: "
        f"{recruiter.get('company', '')}"
    )

    print(
        f"Match score: "
        f"{match.score}"
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
            outreach_channel="email",
        )

        record_template_usage(
            state,
            template_name,
        )

        increment_stat(
            state,
            "emails_sent",
        )

        print(
            "EMAIL SENT"
        )

        print(
            f"Message ID: "
            f"{message_id}"
        )

        return True

    except Exception as exc:
        print(
            "EMAIL FAILED"
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
            outreach_channel="email",
        )

        increment_stat(
            state,
            "emails_failed",
        )

        return False


def send_linkedin_package(
    recruiter: dict,
    match,
    profile: dict,
    state: dict,
) -> bool:
    candidate = profile[
        "candidate"
    ]

    messages = generate_linkedin_messages(
        recruiter,
        match,
        candidate,
    )

    subject, body = render_linkedin_package(
        recruiter=recruiter,
        match=match,
        candidate=candidate,
        connection_note=messages[
            "connection_note"
        ],
        dm_message=messages[
            "dm_message"
        ],
    )

    resume_path = (
        ROOT
        / candidate[
            "resume_path"
        ]
    )

    print()
    print(
        f"LINKEDIN PACKAGE -> "
        f"{recruiter.get('name', 'Unknown')}"
    )

    print(
        f"LinkedIn: "
        f"{recruiter.get('linkedinUrl', '')}"
    )

    print(
        f"Company: "
        f"{recruiter.get('company', '')}"
    )

    print(
        f"Match score: "
        f"{match.score}"
    )

    owner_email = os.getenv(
        "SENDER_EMAIL"
    )

    if not owner_email:
        raise RuntimeError(
            "SENDER_EMAIL is required so "
            "LinkedIn outreach packages can "
            "be delivered to you."
        )

    try:
        message_id = send_email(
            recipient=owner_email,
            subject=subject,
            body=body,
            attachment_path=(
                str(resume_path)
                if resume_path.exists()
                else None
            ),
        )

        record_contact(
            state=state,
            recruiter=recruiter,
            template="linkedin_package",
            subject=subject,
            message_id=message_id,
            status="linkedin_package_sent",
            outreach_channel="linkedin",
        )

        increment_stat(
            state,
            "linkedin_packages_sent",
        )

        print(
            "LINKEDIN PACKAGE SENT TO CANDIDATE"
        )

        print(
            f"Message ID: "
            f"{message_id}"
        )

        return True

    except Exception as exc:
        print(
            "LINKEDIN PACKAGE FAILED"
        )

        print(
            f"Reason: {exc}"
        )

        record_contact(
            state=state,
            recruiter=recruiter,
            template="linkedin_package",
            subject=subject,
            message_id=None,
            status="failed",
            outreach_channel="linkedin",
        )

        return False


def main() -> None:
    print("=" * 70)
    print(
        "AI RECRUITER HUNTER"
    )
    print("=" * 70)

    profile = load_profile()

    state = load_state()

    state[
        "_run_apify_calls"
    ] = 0

    increment_run(
        state
    )

    search_state = load_search_state()

    candidate = profile[
        "candidate"
    ]

    print(
        f"Candidate: "
        f"{candidate['name']}"
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

    recruiters = discover_recruiters(
        profile,
        state,
        search_state,
    )

    qualified = qualify_recruiters(
        recruiters,
        jobs,
        profile,
        state,
    )

    if not qualified:
        print()
        print(
            "No qualified new recruiters found."
        )

    else:
        print()
        print(
            "TOP RECRUITER MATCHES"
        )

        for recruiter, match in qualified[:10]:
            print(
                "-" * 70
            )

            print(
                f"{recruiter.get('name', 'Unknown')} "
                f"| "
                f"{recruiter.get('title', '')}"
            )

            print(
                f"{recruiter.get('company', '')}"
            )

            print(
                f"Email: "
                f"{recruiter.get('email', '') or 'NOT PUBLICLY AVAILABLE'}"
            )

            print(
                f"LinkedIn: "
                f"{recruiter.get('linkedinUrl', '')}"
            )

            print(
                f"Score: "
                f"{match.score}"
            )

            print(
                f"Route: "
                f"{match.outreach_channel}"
            )

        email_selected = [
            item
            for item in qualified
            if item[0].get(
                "email"
            )
        ][
            :MAX_EMAILS_PER_RUN
        ]

        linkedin_selected = [
            item
            for item in qualified
            if not item[0].get(
                "email"
            )
        ][
            :MAX_LINKEDIN_PACKAGES_PER_RUN
        ]

        print()
        print(
            f"EMAILS SELECTED: "
            f"{len(email_selected)}"
        )

        print(
            f"LINKEDIN PACKAGES SELECTED: "
            f"{len(linkedin_selected)}"
        )

        for index, (
            recruiter,
            match,
        ) in enumerate(
            email_selected
        ):
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

        for (
            recruiter,
            match,
        ) in linkedin_selected:
            send_linkedin_package(
                recruiter,
                match,
                profile,
                state,
            )

            save_state(
                state
            )

    search_state[
        "segment_index"
    ] = (
        (
            search_state.get(
                "segment_index",
                0,
            )
            + 1
        )
        % len(
            RECRUITER_SEARCH_SEGMENTS
        )
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
    print("=" * 70)
    print(
        "RUN COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
