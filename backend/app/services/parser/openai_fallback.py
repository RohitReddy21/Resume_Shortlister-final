import os
import json
from typing import Dict, Any

try:
    import openai
except Exception:
    openai = None


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")


def _ensure_client():
    if openai is None:
        raise RuntimeError("openai package not installed")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    openai.api_key = key


PROMPT = """
You are a structured resume parser. Given the raw resume text, extract the following fields as JSON exactly with these keys:
full_name, emails (list), phones (list), location, skills (list), experiences (list of objects with company, designation, start_date, end_date, summary), projects (list), education (list), certifications (list), languages (list), companies (list), current_company, current_ctc, expected_ctc, notice_period, linkedin, github, portfolio

Return only valid JSON. If a field is not present, set it to null or an empty list/object as appropriate.
"""


def openai_extract(raw_text: str, max_tokens: int = 1024) -> Dict[str, Any]:
    """Call OpenAI to extract structured JSON from raw_text.

    Returns parsed dict or empty dict on failure.
    """
    _ensure_client()
    system = {"role": "system", "content": "You extract resume fields into JSON."}
    user = {"role": "user", "content": PROMPT + "\n\nResume text:\n" + raw_text}

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[system, user],
            max_tokens=max_tokens,
            temperature=0.0,
        )
    except Exception as e:
        return {"error": str(e)}

    try:
        content = resp["choices"][0]["message"]["content"]
        # find first JSON object in content
        start = content.find("{")
        if start == -1:
            return {"error": "no json in response", "raw": content}
        json_text = content[start:]
        parsed = json.loads(json_text)
        return parsed
    except Exception as e:
        return {"error": "parse_failed", "detail": str(e), "raw": content}
