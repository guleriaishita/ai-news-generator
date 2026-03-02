import os
import httpx
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("news_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Focused query so NewsAPI does most of the heavy lifting before our pre-filter runs.
AI_QUERY = (
    '"artificial intelligence" OR "machine learning" OR "large language model" OR '
    '"generative AI" OR "AI model" OR "AI tool" OR "AI agent" OR '
    'ChatGPT OR Gemini OR Claude OR Copilot OR Llama OR Mistral OR Grok OR '
    '"OpenAI" OR "Anthropic" OR "Google DeepMind" OR "Hugging Face" OR '
    '"AI assistant" OR "foundation model" OR "diffusion model" OR "transformer model"'
)

# Keyword set for the cheap local pre-filter — prevents off-topic articles from
# reaching the model at all.
_AI_KEYWORDS = {
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "llm", "generative ai",
    "chatgpt", "gpt-4", "gpt-3", "gemini", "claude", "openai", "anthropic",
    "mistral", "llama", "copilot", "hugging face", "diffusion model",
    "transformer", "ai model", "ai tool", "ai agent", "ai assistant",
    "deepmind", "nvidia ai", "foundation model", "stable diffusion",
    "midjourney", "dall-e", "dall·e", "grok", "perplexity", "cohere",
    "rag", "retrieval augmented", "fine-tuning", "finetuning",
    "language model", "ai startup", "ai company", "ai chip", "ai safety",
    "ai regulation", "ai ethics", "ai research", "ai benchmark",
    "ai system", "ai platform", "ai software", "ai hardware",
}


def is_ai_relevant(title: str, description: str) -> bool:
    """Return True if the article contains at least one AI keyword. No external calls."""
    text = (title + " " + (description or "")).lower()
    return any(kw in text for kw in _AI_KEYWORDS)


async def fetch_ai_news(page_size: int = 8) -> list[dict]:
    """
    Fetch raw articles from NewsAPI. Capped at 8 to stay within free-tier Gemini limits.
    searchIn=title,description keeps results focused on visible fields rather than body text.
    """
    params = {
        "q": AI_QUERY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "searchIn": "title,description",
        "apiKey": NEWS_API_KEY,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(NEWS_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

    return data.get("articles", [])