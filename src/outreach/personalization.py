from __future__ import annotations

import os
from typing import Any

import requests


def build_fallback_personalization(
    recruiter: dict[str, Any],
    match: Any
) -> str:
    recruiter_name = recruiter.get("name", "")
    company = recruiter.get("company", "")

    if recruiter_name:
        opening = (
            f"I came across your profile while looking at AI/ML "
            f"recruiting activity and noticed your work with "
            f"{company or 'technical hiring'}."
        )
    else:
        opening = (
            "I came across your profile while looking at "
            "current AI/ML hiring activity."
        )

    if match.role_matches:
        role_text = (
            match.role_matches[0]
        )

        opening += (
            f" I noticed a potential connection with "
            f"{role_text} hiring."
        )

    return opening


def generate_personalization(
    recruiter: dict[str, Any],
    match: Any,
    candidate: dict[str, Any]
) -> str:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return build_fallback_personalization(
            recruiter,
            match
        )

    model = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile"
    )

    recruiter_name = recruiter.get(
        "name",
        "the recruiter"
    )

    company = recruiter.get(
        "company",
        "the company"
    )

    recruiter_title = recruiter.get(
        "title",
        ""
    )

    job_description = recruiter.get(
        "job_description",
        ""
    )

    project_text = ", ".join(
        match.project_matches[:3]
    )

    prompt = f"""
Write ONE concise, natural opening paragraph for a job-seeking email.

Candidate:
{candidate["name"]}

Candidate headline:
{candidate["headline"]}

Recruiter:
{recruiter_name}

Recruiter title:
{recruiter_title}

Company:
{company}

Relevant roles:
{", ".join(match.role_matches)}

Relevant skills:
{", ".join(match.skill_matches[:12])}

Relevant projects:
{project_text}

Recruiter's hiring context:
{job_description}

Rules:
- 2 to 3 sentences maximum.
- Mention something specific about the recruiter's hiring activity when possible.
- Connect the hiring activity to the candidate.
- Do not use generic phrases like "I hope this email finds you well".
- Do not exaggerate.
- Do not claim the recruiter is hiring for something unless the supplied context supports it.
- Do not say "I am passionate".
- Do not use em dashes.
- Do not include a greeting or sign-off.
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "temperature": 0.4,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data["choices"][0]["message"]["content"]
        .strip()
    )

    if not content:
        return build_fallback_personalization(
            recruiter,
            match
        )

    return content
