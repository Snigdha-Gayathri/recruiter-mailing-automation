from __future__ import annotations

import json
import os
from typing import Any

import requests


GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)


def _groq(
    prompt: str,
) -> str | None:
    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:
        return None

    model = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    response = requests.post(
        GROQ_URL,

        headers={
            "Authorization": (
                f"Bearer {api_key}"
            ),
            "Content-Type": (
                "application/json"
            ),
        },

        json={
            "model": model,
            "temperature": 0.35,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        },

        timeout=45,
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["choices"][0]["message"]["content"]
        .strip()
    )


def build_fallback_personalization(
    recruiter: dict[str, Any],
    match: Any,
) -> str:
    recruiter_name = recruiter.get(
        "name",
        "",
    )

    company = recruiter.get(
        "company",
        "",
    )

    title = recruiter.get(
        "title",
        "",
    )

    if recruiter_name:
        opening = (
            f"I came across your profile while researching "
            f"AI/ML recruiting and noticed your work as "
            f"{title or 'a recruiter'}"
            f"{' at ' + company if company else ''}."
        )
    else:
        opening = (
            "I came across your profile while researching "
            "current AI/ML recruiting activity."
        )

    if match.role_matches:
        opening += (
            f" Your profile shows a connection with "
            f"{match.role_matches[0]} hiring."
        )

    return opening


def generate_personalization(
    recruiter: dict[str, Any],
    match: Any,
    candidate: dict[str, Any],
) -> str:
    prompt = f"""
Write one deeply personalized opening paragraph for a
job-seeking email.

Candidate:
{candidate.get("name", "")}

Candidate headline:
{candidate.get("headline", "")}

Candidate projects:
{", ".join(match.project_matches[:5])}

Recruiter:
{recruiter.get("name", "")}

Recruiter title:
{recruiter.get("title", "")}

Company:
{recruiter.get("company", "")}

Recruiter location:
{recruiter.get("location", "")}

Recruiter LinkedIn profile:
{recruiter.get("linkedinUrl", "")}

Recruiter's profile/about:
{recruiter.get("about", "")}

Recruiter's current role description:
{recruiter.get("job_description", "")}

Relevant target roles:
{", ".join(match.role_matches[:10])}

Relevant technical signals:
{", ".join(match.skill_matches[:12])}

Matching reasons:
{"; ".join(match.reasons[:8])}

Rules:
- Write 2 to 4 sentences.
- Use concrete evidence from the supplied recruiter profile.
- Connect the recruiter's actual work to the candidate's background.
- Do not invent jobs.
- Do not claim the recruiter is hiring for a role unless the supplied evidence supports it.
- Do not say "I hope this email finds you well".
- Do not say "I am passionate".
- Do not use generic flattery.
- Do not use em dashes.
- Do not include greeting or sign-off.
"""

    try:
        result = _groq(prompt)

        if result:
            return result

    except Exception as exc:
        print(
            "Groq personalization failed: "
            f"{exc}"
        )

    return build_fallback_personalization(
        recruiter,
        match,
    )


def generate_linkedin_messages(
    recruiter: dict[str, Any],
    match: Any,
    candidate: dict[str, Any],
) -> dict[str, str]:
    prompt = f"""
Create two highly personalized LinkedIn outreach messages
for a job-seeking AI Engineer.

Return ONLY valid JSON with exactly these keys:
connection_note
dm_message

Candidate:
Name: {candidate.get("name", "")}
Headline: {candidate.get("headline", "")}
LinkedIn: {candidate.get("linkedin", "")}

Candidate projects:
{", ".join(match.project_matches[:5])}

Candidate skills:
{", ".join(match.skill_matches[:15])}

Recruiter:
Name: {recruiter.get("name", "")}
Title: {recruiter.get("title", "")}
Company: {recruiter.get("company", "")}
Location: {recruiter.get("location", "")}
LinkedIn: {recruiter.get("linkedinUrl", "")}

Recruiter about:
{recruiter.get("about", "")}

Current role description:
{recruiter.get("job_description", "")}

Matching signals:
{"; ".join(match.reasons[:10])}

Relevant roles:
{", ".join(match.role_matches[:10])}

Requirements:

connection_note:
- Maximum 280 characters.
- Natural and human.
- Mention one concrete recruiter/company signal.
- Explain the relevance in a compact way.
- Do not say "I hope you are well".
- Do not sound like a mass connection request.
- Do not ask for a job directly.

dm_message:
- 3 to 6 short paragraphs.
- Strongly personalized.
- Mention why their recruiting work is relevant to the candidate.
- Mention 1 or 2 specific candidate strengths or projects.
- Make a clear, low-friction request to be considered for relevant AI/ML roles.
- End with a natural question that makes replying easy.
- Do not fabricate a job opening.
- Do not use em dashes.
"""

    fallback_connection = (
        f"Hi {str(recruiter.get('name', '')).split()[0] "
        f"if recruiter.get('name') else ''}, "
        f"I came across your work in AI/ML recruiting"
        f"{' at ' + recruiter.get('company', '') if recruiter.get('company') else ''}. "
        f"I'm an AI Engineer focused on LLM, RAG and agent systems and would "
        f"love to connect."
    ).strip()

    fallback_connection = (
        fallback_connection[:280]
    )

    fallback_dm = (
        f"Hi {str(recruiter.get('name', '')).split()[0] "
        f"if recruiter.get('name') else 'there'},\n\n"
        f"I wanted to follow up because your recruiting work "
        f"{'at ' + recruiter.get('company', '') if recruiter.get('company') else ''} "
        f"looks closely aligned with the kind of AI/ML roles I'm targeting.\n\n"
        f"My strongest work is around production LLM systems, "
        f"RAG pipelines and multi-agent orchestration, including "
        f"{match.project_matches[0] if match.project_matches else 'recent AI engineering projects'}.\n\n"
        f"If you are handling relevant AI/ML, GenAI, LLM or agent "
        f"engineering hiring, would you be open to considering my profile?"
    )

    try:
        result = _groq(prompt)

        if result:
            cleaned = result.strip()

            if cleaned.startswith("```"):
                cleaned = (
                    cleaned
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            parsed = json.loads(
                cleaned
            )

            connection_note = str(
                parsed.get(
                    "connection_note",
                    "",
                )
            ).strip()

            dm_message = str(
                parsed.get(
                    "dm_message",
                    "",
                )
            ).strip()

            if connection_note and dm_message:
                return {
                    "connection_note": (
                        connection_note[:300]
                    ),
                    "dm_message": dm_message,
                }

    except Exception as exc:
        print(
            "Groq LinkedIn personalization failed: "
            f"{exc}"
        )

    return {
        "connection_note": fallback_connection,
        "dm_message": fallback_dm,
    }
