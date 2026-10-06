import os

from dotenv import load_dotenv
from tavily import TavilyClient

import evidence_db as db
from guardrails.sanitize import clean_web_text

load_dotenv()

# Edit freely. These suit AI agent engineering: papers, labs, frameworks, security bodies, a few expert blogs.
TRUSTED_DOMAINS = [
    "arxiv.org", "openreview.net", "aclanthology.org", "proceedings.mlr.press", "neurips.cc",
    "semanticscholar.org", "acm.org", "ieee.org",
    "anthropic.com", "openai.com", "deepmind.google", "research.google", "microsoft.com", "ai.meta.com",
    "huggingface.co", "github.com", "langchain.com", "langchain-ai.github.io", "modelcontextprotocol.io",
    "owasp.org", "nist.gov",
    "lilianweng.github.io", "simonwillison.net", "eugeneyan.com",
]


def search_web(query: str, max_results: int = 5, db_path=db.DB_PATH, client=None,
               include_domains=None) -> list[dict]:
    """Search the web, save every result into the evidence store,
    and return a short summary list that includes each source_id."""
    if client is None:
        key = os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")
        client = TavilyClient(api_key=key)

    options = {"query": query, "max_results": max_results, "search_depth": "basic"}
    if include_domains:
        options["include_domains"] = include_domains
    response = client.search(**options)

    results = []
    for item in response.get("results", []):
        text = clean_web_text(f"{item['title']}\n\n{item['content']}")
        source_id = db.add_source(item["url"], item["title"], text, "web", db_path)
        results.append({
            "source_id": source_id,
            "title": item["title"],
            "url": item["url"],
        })
    return results