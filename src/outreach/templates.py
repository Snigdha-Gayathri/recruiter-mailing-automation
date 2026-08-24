from __future__ import annotations

from typing import Any


TEMPLATES = {
    "hiring_signal": {
        "name": "Hiring Signal",
        "subject": "AI/ML opportunity at {company}"
    },

    "technical_proof": {
        "name": "Technical Proof",
        "subject": "AI Engineer with production RAG + agent experience"
    },

    "direct": {
        "name": "Direct",
        "subject": "Would my profile fit your AI/ML hiring?"
    },

    "company_specific": {
        "name": "Company Specific",
        "subject": "Potential AI/ML fit for {company}"
    },

    "short_form": {
        "name": "Short Form",
        "subject": "AI Engineer | {candidate_name}"
    }
}


def choose_template(
    recruiter: dict[str, Any],
    match: Any,
    index: int
) -> str:
    available = list(TEMPLATES.keys())

    return available[
        index % len(available)
    ]


def render_template(
    template_name: str,
    recruiter: dict[str, Any],
    match: Any,
    candidate: dict[str, Any],
    personalization: str
) -> tuple[str, str]:
    company = recruiter.get(
        "company",
        "your company"
    )

    recruiter_name = recruiter.get(
        "name",
        ""
    ).split(" ")[0]

    candidate_name = candidate["name"]

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

        body = f"""\
{greeting}

{personalization}

I'm an AI Engineer focused on LLM systems, RAG pipelines and multi-agent orchestration. My recent work includes {project}, with hands-on experience across LangGraph, hybrid retrieval, reranking, evaluation and production FastAPI systems.

I'd be grateful if you could consider my profile for relevant AI/ML, GenAI or LLM opportunities you're hiring for.

{links}

I've attached my resume as well.

Best,
{candidate_name}
"""

    elif template_name == "technical_proof":
        subject = (
            "AI Engineer with production RAG + agent experience"
        )

        body = f"""\
{greeting}

{personalization}

A quick snapshot of the kind of work I build:

- Production-oriented Agentic RAG systems
- LangGraph multi-agent orchestration
- Hybrid BM25 + semantic retrieval
- Cross-encoder reranking and grounded evaluation
- FastAPI production backends
- ML inference and latency optimization

For example, {project} involved measurable improvements in retrieval, reliability and system performance.

If you're currently hiring for AI/ML, GenAI, LLM or agent engineering roles, I'd appreciate being considered.

{links}

Resume attached.

Best,
{candidate_name}
"""

    elif template_name == "direct":
        subject = (
            "Would my profile fit your AI/ML hiring?"
        )

        body = f"""\
{greeting}

{personalization}

I'm currently targeting early-career AI Engineer, ML Engineer, GenAI and LLM/Agent Engineer opportunities in Bengaluru, Mumbai, Hyderabad or remotely.

My strongest area is production-oriented LLM systems, particularly RAG, agent orchestration, evaluation and retrieval.

Would my profile be relevant for any roles you're currently recruiting for?

{links}

Resume attached.

Best,
{candidate_name}
"""

    elif template_name == "company_specific":
        subject = (
            f"Potential AI/ML fit for {company}"
        )

        body = f"""\
{greeting}

{personalization}

I'm particularly interested in the kind of AI engineering work being done at {company}. My background combines traditional ML engineering with production LLM systems, RAG, multi-agent orchestration and performance optimization.

One relevant example is {project}, where I worked on a production-oriented AI system with measurable retrieval and reliability improvements.

If there is an appropriate AI/ML, GenAI, LLM or Agent Engineer opening, I'd love to be considered.

{links}

I've attached my resume for context.

Best,
{candidate_name}
"""

    else:
        subject = (
            f"AI Engineer | {candidate_name}"
        )

        body = f"""\
{greeting}

{personalization}

I'm an AI Engineer specializing in LLM systems, RAG and multi-agent applications, with production ML experience as well.

I'm currently looking for AI/ML, GenAI, LLM or Agent Engineer opportunities in Bengaluru, Mumbai, Hyderabad or remotely.

{links}

Resume attached. Would you be open to considering my profile for relevant openings?

Best,
{candidate_name}
"""

    return subject, body
