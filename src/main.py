from __future__ import annotations

import json
import os
from pathlib import Path

from discovery.enrichment import enrich_recruiter
from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    search_recruiters,
)
from matching.scorer import (
    calculate_recruiter_match,
)
from outreach.gmail import send_email
from outreach.personalization import (
    generate_personalization,
)
from outreach.templates import (
    choose_template,
    render_template,
)
from storage.database import (
    has_been_contacted,
    increment_stat,
    load_state,
    record_contact,
    save_state,
)


ROOT = Path(
    __file__
).resolve().parents[1]

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

MAX_APIFY_CALLS_PER_RUN = 1


def load_profile() -> dict:

    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(
            file
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

    state[
        "_run_apify_calls"
    ] = (
        state.get(
            "_run_apify_calls",
            0,
        )
        + 1
    )

    increment_stat(
        state,
        "apify_calls",
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

    if not email:
        return False

    if not recruiter.get(
        "email_valid",
        True,
    ):
        return False

    return True


def qualify_recruiters(
    recruiters: list[dict],
    profile: dict,
    state: dict,
) -> list[tuple]:

    print()
    print(
        "RECRUITER QUALIFICATION"
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

        match = (
            calculate_recruiter_match(
                recruiter,
                [],
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
            f"{recruiter.get('email')}"
        )

        return True

    except Exception as exc:

        print(
            "EMAIL FAILED: "
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
        "Candidate: "
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
        "Apify limit this run: 1"
    )

    recruiters = (
        discover_recruiters(
            profile,
            state,
        )
    )

    run_calls = state[
        "_run_apify_calls"
    ]

    if (
        run_calls
        > MAX_APIFY_CALLS_PER_RUN
    ):

        raise RuntimeError(
            "Apify API budget exceeded: "
            f"{run_calls} > "
            f"{MAX_APIFY_CALLS_PER_RUN}"
        )

    candidates = (
        qualify_recruiters(
            recruiters,
            profile,
            state,
        )
    )

    print()
    print(
        f"Apify calls this run: "
        f"{run_calls}/"
        f"{MAX_APIFY_CALLS_PER_RUN}"
    )

    if not candidates:

        print()

        print(
            "No qualified new recruiters "
            "found."
        )

        state.pop(
            "_run_apify_calls",
            None,
        )

        save_state(
            state
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

    print(
        f"Apify calls this run: "
        f"{run_calls}"
    )

    print(
        f"Emails sent this run: "
        f"{len(selected)}"
    )


if __name__ == "__main__":
    main()
