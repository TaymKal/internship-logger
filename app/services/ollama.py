import ast
import json
import os
import re
from typing import Tuple

import requests


from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL_NAME


class OllamaError(Exception):
    """Raised when the Ollama summarization fails."""



SUMMARIZE_PROMPT_TEMPLATE = """
You are an expert AI assistant. Your task is to rewrite and summarize the given transcript.

CRITICAL INSTRUCTION:
1. Detect the dominant language of the transcript.
2. Generate the "title", "formal_text", and "summary" in that EXACT SAME LANGUAGE.
3. Do NOT translate the content into English or any other language.
4. The "formal_text" MUST be a polished rewrite, not a copy. Improve grammar, remove fillers, and make it professional. Do NOT just repeat the input.

Example:
- If transcript is Spanish -> Title, Formal Text, and Summary must be in Spanish.
- If transcript is English -> Title, Formal Text, and Summary must be in English.

Return a JSON object with:
- "language": The detected language (e.g., "English", "Spanish").
- "title": A short descriptive title in the detected language.
- "formal_text": The rewritten formal text in the detected language.
- "summary": A bulleted summary in the detected language (as a single string with newlines).

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
                "format": "json",
                "stream": False,
                "options": {
                    "num_ctx": 4096,
                    "num_predict": -1, # Generate until done
                },
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
            
    json_str = json_str.strip()
    
    # Pre-processing to fix common LLM mistakes
    # Fix 1: Replace escaped single quotes \', which are valid in Py/JS but not JSON
    json_str = json_str.replace(r"\'", "'")
    
    # Fix 2: Replace invalid unicode escapes (like \u00bu caused by typos)
    # This prevents the "truncated \uXXXX escape" error in ast.literal_eval
    def escape_invalid_unicode(match):
        return "\\\\u"
    
    # Find \u NOT followed by 4 hex digits
    json_str = re.sub(r'\\u(?![0-9a-fA-F]{4})', escape_invalid_unicode, json_str)
    
    try:
        payload = json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Fallback: Try ast.literal_eval (handles Python dicts, single quotes, slightly different escapes)
            payload = ast.literal_eval(json_str)
            if not isinstance(payload, dict):
                raise ValueError("Parsed output is not a dictionary.")
        except (ValueError, SyntaxError, TypeError) as exc:
             raise OllamaError(f"Could not parse Ollama response as JSON or Python dict: {exc}\nResponse: {full_response}") from exc

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

