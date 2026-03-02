import os
import json
import re
import time
from openai import OpenAI, RateLimitError, APIStatusError
from dotenv import load_dotenv

load_dotenv()

# OpenRouter is OpenAI-compatible — just swap the base URL.
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL = "qwen/qwen-2.5-7b-instruct"  # free-tier model on OpenRouter

SYSTEM_PROMPT = """You are an AI news editor for a technology publication focused on Artificial Intelligence.

Your job is to analyze an AI-related news article and return a structured JSON response.

INSTRUCTIONS:
1. Write a concise summary of 1–2 sentences (max 50 words) that captures the core news value.
   - Be factual and neutral. No hype or filler phrases like "In a groundbreaking move...".
   - Write in present tense where possible.
2. Assign exactly ONE category from this fixed list:
   - "AI Tools"       → new AI products, apps, APIs, models, or developer tooling
   - "Industry News"  → company news, funding, partnerships, acquisitions, regulation
   - "Ethics"         → bias, safety, misuse, policy debates, societal impact of AI
   - "Research"       → academic papers, benchmarks, new techniques, scientific findings

OUTPUT FORMAT (strict JSON):
Return ONLY a single JSON object. No explanations, no markdown, no backticks.

{
  "summary": "<1-2 sentence summary>",
  "category": "<one of: AI Tools | Industry News | Ethics | Research>"
}
Do NOT include any additional keys or text.
Never return empty output."""

USER_PROMPT_TEMPLATE = """Analyze the following news article and return the JSON response.

Title: {title}
Description: {description}

Remember: respond with the JSON object only, no extra text."""


VALID_CATEGORIES = {"AI Tools", "Industry News", "Ethics", "Research"}
_SKIP_SENTINEL = "__skip__"
_MAX_RETRIES   = 3
_RETRY_DELAY   = 2.0   # seconds between non-rate-limit retries
_MAX_RL_WAIT   = 65.0  # cap 429 back-off so we don't hang too long


def _parse_retry_after(error_str: str) -> float:
    """
    Extract the wait time from an OpenRouter 429 error message.
    Falls back to _MAX_RL_WAIT if nothing parseable is found.
    """
    match = re.search(r"(\d+(?:\.\d+)?)\s*s(?:econds?)?", str(error_str), re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 1.0, _MAX_RL_WAIT)
    return _MAX_RL_WAIT


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` fences that some models add despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def process_article(title: str, description: str) -> dict:
    """
    Send a single article to the model and return {"summary": ..., "category": ...}.

    Retry strategy:
      - 429 RateLimitError: parse Retry-After, sleep, retry
      - ValueError / JSONDecodeError: short sleep, retry
      - Other API errors: short sleep, retry
      - Unexpected errors: skip immediately

    Returns {"summary": "", "category": "__skip__"} once all retries are exhausted,
    so the caller can silently drop the article.
    """
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": USER_PROMPT_TEMPLATE.format(
                            title=title,
                            description=description or "(no description provided)",
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=256,
                response_format={"type": "json_object"},
            )

            if not response.choices:
                raise ValueError("OpenRouter returned no choices")

            finish_reason = response.choices[0].finish_reason
            if finish_reason not in (None, "stop"):
                raise ValueError(f"Unexpected finish_reason={finish_reason!r} for '{title}'")

            raw_text = (response.choices[0].message.content or "").strip()
            if not raw_text:
                raise ValueError(f"Empty response from model (attempt {attempt})")

            result   = json.loads(_strip_markdown_fences(raw_text))
            summary  = result.get("summary", "").strip()
            category = result.get("category", "").strip()

            print(f"[ai_service] Summary for '{title}': {summary}")

            if len(summary) <= 5:
                print(f"[ai_service] Very short summary for '{title}' — skipping")
                return {"summary": "", "category": _SKIP_SENTINEL}

            if category not in VALID_CATEGORIES:
                category = "Industry News"

            return {"summary": summary, "category": category}

        except RateLimitError as e:
            last_error = e
            wait = _parse_retry_after(str(e))
            print(
                f"[ai_service] Rate-limited (attempt {attempt}/{_MAX_RETRIES}) for '{title}'. "
                f"Waiting {wait:.0f}s..."
            )
            time.sleep(wait)

        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            print(f"[ai_service] Attempt {attempt}/{_MAX_RETRIES} failed for '{title}': {e}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

        except APIStatusError as e:
            last_error = e
            print(f"[ai_service] API error (attempt {attempt}/{_MAX_RETRIES}) for '{title}': {e}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

        except Exception as e:
            print(f"[ai_service] Unexpected error for '{title}': {e}")
            return {"summary": "", "category": _SKIP_SENTINEL}

    print(f"[ai_service] Skipping '{title}' after {_MAX_RETRIES} failed attempts: {last_error}")
    return {"summary": "", "category": _SKIP_SENTINEL}


def process_articles(articles: list[dict]) -> list[dict]:
    """Enrich a list of articles with summary + category, dropping any that are skipped."""
    enriched = []
    for article in articles:
        result = process_article(
            title=article.get("title", ""),
            description=article.get("description", ""),
        )
        if result["category"] == _SKIP_SENTINEL:
            continue
        enriched.append({**article, **result})
    return enriched
