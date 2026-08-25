from __future__ import annotations

from typing import Any


TEMPLATES = {
    "hiring_signal": {
        "name": "Hiring Signal",
    },
    "technical_proof": {
        "name": "Technical Proof",
    },
    "direct": {
        "name": "Direct",
    },
    "company_specific": {
        "name": "Company Specific",
    },
    "short_form": {
        "name": "Short Form",
    },
}


def choose_template(
    recruiter: dict[str, Any],
    match: Any,
    index: int,
) -> str:
    available = list(
        TEMPLATES.keys()
    )

    return available[
        index % len(available)
    ]


def render_template(
    template_name: str,
    recruiter: dict[str, Any],
    match: Any,
    candidate: dict[str, Any],
    personalization: str,
) -> tuple[str, str]:
    company = recruiter.get(
        "company",
        "your company",
    )

    recruiter_name = recruiter.get(
        "name",
        "",
    ).split(" ")[0]

    candidate_name = candidate[
        "name"
    ]

    greeting = (
        f"Hi {recruiter_name},"
        if recruiter_name
        else "Hi,"
    )

    links = (
        f"LinkedIn: {candidate['linkedin']}\n"
        f"GitHub: {candidate['github']}\n"
        f"Portfolio: {candidate['portfolio']}"
    )

    project = (
        match.project_matches[0]
        if match.project_matches
        else "my recent AI engineering work"
    )

    if template_name == "hiring_signal":
        subject = (
            f"AI/ML opportunity at {company}"
        )

        body = f"""
{greeting}

{personalization}

I'm an AI Engineer focused on production LLM systems, RAG pipelines and multi-agent orchestration. A relevant example is {project}.

I'd be grateful if you could consider my profile for relevant AI/ML, GenAI, LLM or agent engineering opportunities you are handling.

{links}

I've attached my resume.

Best,
{candidate_name}
""".strip()

    elif template_name == "technical_proof":
        subject = (
            "AI Engineer with production RAG + agent experience"
        )

        body = f"""
{greeting}

{personalization}

My recent work includes:

- Production-oriented Agentic RAG systems
- LangGraph multi-agent orchestration
- Hybrid BM25 + semantic retrieval
- Cross-encoder reranking
- Grounded evaluation
- FastAPI production backends
- LLM inference and latency optimization

One relevant project is {project}.

If you are recruiting for AI/ML, GenAI, LLM or agent engineering roles, I'd appreciate being considered.

{links}

Resume attached.

Best,
{candidate_name}
""".strip()

    elif template_name == "direct":
        subject = (
            "Would my profile fit your AI/ML hiring?"
        )

        body = f"""
{greeting}

{personalization}

I'm currently targeting early-career AI Engineer, ML Engineer, GenAI and LLM/Agent Engineer opportunities in Bengaluru, Mumbai, Hyderabad or remotely.

My strongest area is production-oriented LLM systems, particularly RAG, agent orchestration, evaluation and retrieval.

Would my profile be relevant for any AI/ML roles you are currently recruiting for?

{links}

Resume attached.

Best,
{candidate_name}
""".strip()

    elif template_name == "company_specific":
        subject = (
            f"Potential AI/ML fit for {company}"
        )

        body = f"""
{greeting}

{personalization}

I'm particularly interested in the AI engineering work being done at {company}. My background combines ML engineering with production LLM systems, RAG, multi-agent orchestration and performance optimization.

One relevant example is {project}.

If there is an appropriate AI/ML, GenAI, LLM or Agent Engineer opening, I'd love to be considered.

{links}

I've attached my resume.

Best,
{candidate_name}
""".strip()

    else:
        subject = (
            f"AI Engineer | {candidate_name}"
        )

        body = f"""
{greeting}

{personalization}

I'm an AI Engineer specializing in LLM systems, RAG and multi-agent applications, with production ML experience as well.

I'm currently looking for AI/ML, GenAI, LLM or Agent Engineer opportunities in Bengaluru, Mumbai, Hyderabad or remotely.

{links}

Resume attached.

Would you be open to considering my profile for relevant openings?

Best,
{candidate_name}
""".strip()

    return subject, body


def render_linkedin_package(
    recruiter: dict[str, Any],
    match: Any,
    candidate: dict[str, Any],
    connection_note: str,
    dm_message: str,
) -> tuple[str, str]:
    recruiter_name = recruiter.get(
        "name",
        "Recruiter",
    )

    company = recruiter.get(
        "company",
        "",
    )

    subject = (
        f"LinkedIn outreach package: "
        f"{recruiter_name}"
        f"{' | ' + company if company else ''}"
    )

    matching_jobs = []

    for job in match.matching_jobs[:5]:
        if not isinstance(job, dict):
            continue

        title = (
            job.get("title")
            or job.get("jobTitle")
            or job.get("name")
            or ""
        )

        if title:
            matching_jobs.append(
                str(title)
            )

    jobs_text = (
        "\n".join(
            f"- {title}"
            for title in matching_jobs
        )
        if matching_jobs
        else "- No cached company job available"
    )

    reasons_text = "\n".join(
        f"- {reason}"
        for reason in match.reasons[:8]
    )

    body = f"""
RECRUITER OUTREACH PACKAGE

Recruiter
---------
Name: {recruiter_name}
Title: {recruiter.get('title', '')}
Company: {company}
Location: {recruiter.get('location', '')}

LinkedIn
--------
{recruiter.get('linkedinUrl', '')}

Match score
-----------
{match.score}

Outreach route
--------------
LinkedIn connection + post-acceptance DM

Why this recruiter matched
--------------------------
{reasons_text}

Matching company jobs
---------------------
{jobs_text}

CONNECTION NOTE
===============

{connection_note}

POST-ACCEPTANCE DM
==================

{dm_message}

Candidate links
---------------
LinkedIn: {candidate.get('linkedin', '')}
GitHub: {candidate.get('github', '')}
Portfolio: {candidate.get('portfolio', '')}

Resume
------
Attached to this email.

IMPORTANT
---------
No public recruiter email was discovered by the Apify profile search.
Do not send this package to the recruiter by email.
Use the LinkedIn profile above.
""".strip()

    return subject, body
