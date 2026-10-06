import os

from dotenv import load_dotenv
from tavily import TavilyClient

import evidence_db as db
from guardrails.sanitize import clean_web_text

load_dotenv()


def search_web(query: str, max_results: int = 5, db_path=db.DB_PATH, client=None) -> list[dict]:
    """Search the web, save every result into the evidence store,
    and return a short summary list that includes each source_id."""
    if client is None:
        key = os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")
        client = TavilyClient(api_key=key)

    response = client.search(query=query, max_results=max_results, search_depth="basic")

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