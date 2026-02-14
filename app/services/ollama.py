import os
from typing import Tuple

import requests


from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL_NAME


class OllamaError(Exception):
    """Raised when the Ollama summarization fails."""


SUMMARIZE_PROMPT_TEMPLATE = """
You are a helpful assistant that turns voice transcripts into formal Notion notes.

**IMPORTANT: You must write the output in the SAME LANGUAGE as the transcript.**
If the transcript is in Spanish, write the notes in Spanish.
If the transcript is in Arabic, write the notes in Arabic.
If the transcript is mixed, use the dominant language.

Given the raw transcript below, do two things in order:

1. Rewrite it into clear, formal prose (correct grammar, full sentences, no filler). Put that in "formal_text".
2. Write a concise summary as bullet points. Each bullet should start with "- ". Put that in "summary".

Produce a JSON object with these keys:
- "title": a short descriptive title (max 80 characters).
- "formal_text": the transcript rewritten as formal, well-written text (paragraphs allowed).
- "summary": a concise bullet-point summary as a SINGLE STRING (not an array). Each bullet on its own line, starting with "- ".

Transcript:
\"\"\"{transcript}\"\"\"

Respond with ONLY valid JSON, no extra commentary.
"""


def summarize_transcript(transcript: str) -> Tuple[str, str]:
    """
    Call Ollama to summarize the transcript into (title, body).
    """
    if not transcript.strip():
        raise OllamaError("Empty transcript cannot be summarized.")

    url = f"{OLLAMA_BASE_URL}/api/generate"
    prompt = SUMMARIZE_PROMPT_TEMPLATE.format(transcript=transcript)

    try:
        resp = requests.post(
            url,
            json={
                "model": OLLAMA_MODEL_NAME,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise OllamaError(f"Failed to reach Ollama at {url}: {exc}") from exc

    if resp.status_code != 200:
        raise OllamaError(
            f"Ollama returned HTTP {resp.status_code}: {resp.text[:500]}"
        )

    data = resp.json()
    full_response = data.get("response") or ""
    if not full_response.strip():
        raise OllamaError("Ollama returned an empty response.")

    # Best-effort JSON extraction.
    import json

    json_str = full_response.strip()
    # In case the model wrapped JSON in markdown code fences.
    if json_str.startswith("```"):
        json_str = json_str.strip("`")
        if json_str.lower().startswith("json"):
            json_str = json_str[4:]
    try:
        payload = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Could not parse Ollama JSON: {exc}\n{full_response}") from exc

    title = str(payload.get("title", "Untitled Note")).strip() or "Untitled Note"
    formal_text = str(payload.get("formal_text", "")).strip()
    summary = payload.get("summary", "")
    # Handle summary returned as a list instead of a string
    if isinstance(summary, list):
        summary = "\n".join(str(item).strip() for item in summary)
    summary = str(summary).strip()
    if formal_text and summary:
        body = f"{formal_text}\n\n## Summary\n\n{summary}"
    elif formal_text:
        body = formal_text
    else:
        body = str(payload.get("body", transcript)).strip()
    return title, body

