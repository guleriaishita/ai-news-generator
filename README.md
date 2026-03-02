# AI News Aggregator

Pulls the latest AI news from NewsAPI, runs each article through an LLM to get a short summary and category, and lets people subscribe to get that digest in their inbox. Built with FastAPI on the backend and React + Vite on the frontend.

---

## What's inside

```
ai-news-aggregator/
├── backend/
│   ├── .env                # your secrets — don't commit this
│   ├── .env.example        # copy this and fill it in
│   ├── main.py             # FastAPI routes + pipeline cache/lock
│   ├── news_service.py     # fetches from NewsAPI, keyword pre-filter
│   ├── ai_service.py       # sends articles to OpenRouter, handles retries
│   └── email_service.py    # builds the HTML email and sends it via Resend
└── frontend/
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── index.css
        └── components/
            ├── NewsFeed.jsx
            ├── SubscribeForm.jsx
            └── NewsletterAdmin.jsx
```

---

## Before you start

You'll need Python 3.11+, Node 18+, and accounts on three services:

- **[NewsAPI](https://newsapi.org/register)** — free tier is fine, 100 requests/day
- **[OpenRouter](https://openrouter.ai/keys)** — I used `qwen/qwen-2.5-7b-instruct` which is free
- **[Resend](https://resend.com/api-keys)** — free tier, but has a sandbox restriction (more on that below)

---

## Setting up API keys

Copy the example env file:

```bash
cp backend/.env.example backend/.env
```

Then open `backend/.env` and fill in your keys:

```
news_API_KEY=          # from newsapi.org
OPENROUTER_API_KEY=    # from openrouter.ai
RESEND_API_KEY=        # from resend.com
RESEND_FROM=           # sender name + email, e.g: AI News Digest <onboarding@resend.dev>
RESEND_VERIFIED_EMAIL= # the email you signed up to Resend with
```

**About `RESEND_VERIFIED_EMAIL`:** Resend's free sandbox only delivers to the email you used to register — not to random addresses. So if you try subscribing with a different email it'll give a clear error rather than silently failing. Once you verify a domain in Resend you can remove this variable entirely and it'll work for anyone.

Don't commit `backend/.env` — it's in `.gitignore`.

---

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate

pip install fastapi uvicorn httpx openai resend python-dotenv pydantic[email]

uvicorn main:app --reload --port 8000
```

API runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs` if you want to poke at endpoints manually.

### Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Start the backend first or the news feed won't load.

---

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| `GET` | `/news` | fetch + filter + summarise AI articles (cached 60s) |
| `POST` | `/subscribe` | takes `{ "email": "..." }`, sends a newsletter |
| `GET` | `/newsletter/preview` | returns the newsletter HTML so you can preview it |
| `GET` | `/docs` | Swagger UI |

---

## Why I made certain choices

**FastAPI over Flask/Django** — the pipeline needs to fetch from NewsAPI asynchronously and I wanted the lock + cache to work properly with async. FastAPI's async support felt like the right fit here. The auto-generated docs at `/docs` also saved me a bunch of manual testing time.

**OpenRouter instead of calling Gemini directly** — I went with OpenRouter because it's a drop-in OpenAI-compatible wrapper and the `qwen/qwen-2.5-7b-instruct` model on their free tier was good enough to produce clean structured JSON. Kept costs at zero during development.

**Two-stage filtering** — NewsAPI already narrows things down with a keyword query (`searchIn=title,description`), but some articles still sneak through that aren't really about AI. So I added a cheap Python keyword check (`is_ai_relevant()`) before anything hits the LLM. Cuts down on quota usage.

**Cache + async lock** — React StrictMode in dev fires every `useEffect` twice, so without a lock I'd get two simultaneous pipeline runs both hitting OpenRouter at the same time. The lock makes only one run at a time; the second request just waits and returns whatever the first one cached. Cache TTL is 60 seconds which also covers the LLM rate-limit retry window.

**Resend for email** — it has a proper Python SDK and the sandbox mode meant I could actually test emails without setting up a custom domain. The tradeoff is the sandbox restriction above, but that's easy to work around.

**React + Vite, no UI library** — kept it minimal on purpose. Just React 18 and plain CSS. No router, no component library — the project is small enough that adding dependencies felt like overkill.

---
