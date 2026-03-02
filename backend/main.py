import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from news_service import fetch_ai_news, is_ai_relevant
from ai_service import process_article, _SKIP_SENTINEL
from email_service import send_welcome_email, build_newsletter_html, SandboxRestrictionError

app = FastAPI(
    title="AI News Aggregator",
    description="Fetches, filters, and summarises AI-related news using Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cache + lock to prevent concurrent requests (e.g. React StrictMode double-calls)
# from each triggering an independent pipeline run and hitting Gemini rate limits.
_pipeline_lock = asyncio.Lock()
_news_cache: dict = {}  # {"articles": list, "ts": float}
CACHE_TTL = 60          # seconds


def _run_pipeline(raw_articles: list[dict]) -> list[dict]:
    """
    Filter and enrich a batch of raw NewsAPI articles:
      1. is_ai_relevant() — fast local pre-filter, no model call
      2. process_article() — model call with retry
      3. Collect results
    """
    results: list[dict] = []

    for article in raw_articles:
        title       = article.get("title", "") or ""
        description = article.get("description", "") or ""
        source      = (article.get("source") or {}).get("name", "")

        if not is_ai_relevant(title, description):
            print(f"[pipeline] skip (not AI-relevant): {title!r}")
            continue

        ai_result = process_article(title, description)

        if ai_result.get("category") == _SKIP_SENTINEL:
            print(f"[pipeline] skip (model failed): {title!r}")
            continue

        results.append({
            "title":       title,
            "description": description,
            "url":         article.get("url", ""),
            "publishedAt": article.get("publishedAt", ""),
            "source":      source,
            "urlToImage":  article.get("urlToImage", ""),
            "summary":     ai_result["summary"],
            "category":    ai_result["category"],
        })
        print(f"[pipeline] added [{ai_result['category']}]: {title!r}")

    print(f"[pipeline] done — {len(results)}/{len(raw_articles)} articles passed")
    return results


async def _get_articles() -> list[dict]:
    """
    Shared helper for all endpoints. Returns cached articles if still fresh;
    otherwise acquires the lock, runs the pipeline once, and caches the result.
    """
    if _news_cache and (time.monotonic() - _news_cache["ts"]) < CACHE_TTL:
        print("[pipeline] cache hit")
        return _news_cache["articles"]

    async with _pipeline_lock:
        # Re-check after acquiring the lock — another request may have just populated it.
        if _news_cache and (time.monotonic() - _news_cache["ts"]) < CACHE_TTL:
            print("[pipeline] cache hit (after lock)")
            return _news_cache["articles"]

        try:
            raw_articles = await fetch_ai_news()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"NewsAPI error: {exc}")

        loop = asyncio.get_event_loop()
        enriched = await loop.run_in_executor(None, _run_pipeline, raw_articles)

        _news_cache["articles"] = enriched
        _news_cache["ts"] = time.monotonic()
        return enriched


@app.get("/news", summary="Fetch and process AI news articles")
async def get_news():
    """
    Fetches articles from NewsAPI, pre-filters with is_ai_relevant(),
    then enriches each through the model. Results are cached for 60s.
    """
    articles = await _get_articles()
    return {"articles": articles, "count": len(articles)}


class SubscribeRequest(BaseModel):
    email: EmailStr


@app.post("/subscribe", summary="Subscribe and receive a welcome newsletter email")
async def subscribe(body: SubscribeRequest):
    """Fetch the latest AI news and email it as a newsletter to the subscriber."""
    articles = await _get_articles()

    if not articles:
        raise HTTPException(
            status_code=503,
            detail="No AI articles were available to send in the newsletter.",
        )

    try:
        send_welcome_email(to_email=body.email, articles=articles)
    except SandboxRestrictionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Email send failed: {exc}")

    return {"message": f"Newsletter sent to {body.email}", "articles_sent": len(articles)}


@app.get("/newsletter/preview", summary="Preview the newsletter HTML")
async def newsletter_preview():
    """Return the newsletter HTML — reuses the cache so no extra model calls are made."""
    articles = await _get_articles()
    return HTMLResponse(content=build_newsletter_html(articles))
