from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from openai import AzureOpenAI
from openai import NotFoundError


def _get_client() -> AzureOpenAI:
    # Ensure .env is loaded even if imported outside streamlit_app.py
    load_dotenv()

    api_key = os.getenv("EPAM_DIAL_API_KEY")
    if not api_key:
        raise RuntimeError("Missing EPAM_DIAL_API_KEY in environment.")

    return AzureOpenAI(
        api_version="2023-08-01-preview",
        azure_endpoint="https://ai-proxy.lab.epam.com",
        api_key=api_key,
        timeout=120.0,
        max_retries=2,
    )


def _get_deployment_candidates(explicit_model: str | None) -> list[str]:
    """
    For Azure OpenAI, `model=` is the *deployment name*.
    EPAM Dial may have different deployment ids; allow env override + fallbacks.
    """
    env_model = (
        os.getenv("EPAM_DIAL_DEPLOYMENT")
        or os.getenv("EPAM_DIAL_MODEL")
        or ""
    ).strip()
    candidates = []
    if explicit_model:
        candidates.append(explicit_model)
    if env_model and env_model not in candidates:
        candidates.append(env_model)

    # Common deployment names (guessing; will try until one works)
    fallbacks = [
        "gpt-35-turbo",
        "gpt-35-turbo-16k",
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4",
    ]
    for m in fallbacks:
        if m not in candidates:
            candidates.append(m)

    return candidates


def generate_ppt_narrative(
    *,
    question: str,
    answer: str,
    sources: list[dict] | None = None,
    model: str | None = None,
) -> str:
    """
    Generate detailed PPT-ready text from a single Q/A.
    Output is plain text with clear sections (Summary, Insights, Trends, etc.).
    """
    src_lines = []
    for s in (sources or []):
        url = (s.get("url") or "").strip()
        title = (s.get("title") or url).strip()
        if url:
            src_lines.append(f"- {title}")
            if title and url != title:
                src_lines.append(f"  {url}")

    sources_block = "\n".join(src_lines) if src_lines else "- (No sources provided)"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""You are an expert business analyst creating PPT slide content.
Create a detailed, PPT-ready narrative based on the Q/A below.

Requirements:
- Use concise, presentation-style bullet points where appropriate.
- Include these sections exactly (use headings):
  1) Executive Summary
  2) Key Insights
  3) Key Trends
  4) Risks / Watchouts
  5) Recommended Next Actions
  6) Sources (restate provided sources; do not invent)
- Do NOT fabricate facts. If information is missing or uncertain, state assumptions clearly.
- Keep it high-signal; no fluff.

Timestamp: {now}

Question:
{question}

Answer:
{answer}

Sources:
{sources_block}
"""

    client = _get_client()
    last_err: Exception | None = None
    tried = []
    for deployment in _get_deployment_candidates(model):
        tried.append(deployment)
        try:
            resp = client.chat.completions.create(
                model=deployment,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return (resp.choices[0].message.content or "").strip()
        except NotFoundError as e:
            # Unknown deployment name; try the next candidate
            last_err = e
            continue

    tried_list = ", ".join(tried)
    raise RuntimeError(
        "EPAM Dial deployment name not found. "
        "Set EPAM_DIAL_DEPLOYMENT in your .env to the correct Azure deployment id. "
        f"Tried: {tried_list}"
    ) from last_err


