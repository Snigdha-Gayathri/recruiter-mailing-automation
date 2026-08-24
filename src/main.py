from __future__ import annotations

import json
import os
from pathlib import Path

from discovery.enrichment import enrich_recruiter
from discovery.recruiters import (
    deduplicate_recruiters,
    normalize_recruiter,
    search_recruiters
)
from matching.scorer import (
    calculate_recruiter_match
)
from outreach.gmail import send_email
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


ROOT = Path(__file__).resolve().parents[1]

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


def qualify_recruiter(
    recruiter: dict,
    profile: dict
):
    return calculate_recruiter_match(
        recruiter,
        profile
    )


def select_top_recruiters(
    recruiters: list[dict],
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

        match = qualify_recruiter(
            recruiter,
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
        key=lambda item: (
            item[1].score,

            item[0].get(
                "email_quality_score",
                0
            )
        ),
        reverse=True
    )

    return candidates


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
            f"{recruiter.get('email')} "
            f"-> {exc}"
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


def print_recruiter_match(
    recruiter: dict,
    match
) -> None:

    print("-" * 70)

    print(
        f"Recruiter: "
        f"{recruiter.get('name')}"
    )

    print(
        f"Email: "
        f"{recruiter.get('email')}"
    )

    print(
        f"Company: "
        f"{recruiter.get('company')}"
    )

    print(
        f"Title: "
        f"{recruiter.get('title')}"
    )

    print(
        f"Location: "
        f"{recruiter.get('location')}"
    )

    print(
        f"Match score: "
        f"{match.score}"
    )

    print(
        f"Recruiter signals: "
        f"{', '.join(match.recruiter_signal_matches)}"
    )

    print(
        f"Target role signals: "
        f"{', '.join(match.role_matches)}"
    )

    print(
        f"Skill matches: "
        f"{', '.join(match.skill_matches[:10])}"
    )

    print(
        f"Project matches: "
        f"{', '.join(match.project_matches)}"
    )

    print(
        f"Company signals: "
        f"{', '.join(match.company_signal_matches)}"
    )

    print(
        f"Location match: "
        f"{match.location_match}"
    )

    print(
        f"Hiring signal: "
        f"{match.hiring_signal}"
    )


def main():

    print("=" * 70)
    print("AI RECRUITER HUNTER")
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
            item
        )
        for item in recruiters
    ]

    recruiters = deduplicate_recruiters(
        recruiters
    )

    increment_stat(
        state,
        "discovered",
        len(recruiters)
    )

    print(
        f"Unique recruiters: "
        f"{len(recruiters)}"
    )

    print()

    print(
        "RECRUITER QUALIFICATION"
    )

    candidates = select_top_recruiters(
        recruiters,
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

        print(
            "No qualified new recruiters found."
        )

        save_state(
            state
        )

        return

    print()

    print(
        "TOP RECRUITERS"
    )

    preview_limit = min(
        10,
        len(candidates)
    )

    for recruiter, match in candidates[
        :preview_limit
    ]:

        print_recruiter_match(
            recruiter,
            match
        )

    max_per_run = int(
        os.getenv(
            "MAX_EMAILS_PER_RUN",
            "5"
        )
    )

    selected = candidates[
        :max_per_run
    ]

    print()

    print(
        f"Selected for outreach: "
        f"{len(selected)}"
    )

    print()

    for index, (
        recruiter,
        match
    ) in enumerate(
        selected
    ):

        print("=" * 70)

        print(
            f"SENDING {index + 1}/"
            f"{len(selected)}"
        )

        print(
            f"To: "
            f"{recruiter.get('email')}"
        )

        print(
            f"Recruiter: "
            f"{recruiter.get('name')}"
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
            recruiter=recruiter,

            match=match,

            template_index=index,

            profile=profile,

            state=state
        )

        save_state(
            state
        )

    print()

    print("=" * 70)
    print("RUN COMPLETE")
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
