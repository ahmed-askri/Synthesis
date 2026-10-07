"""MCP server with the two search tools.
The trusted-domain list lives HERE, so a client cannot widen it.
Only ids and titles are returned: the source text stays in the database."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from mcp.server.fastmcp import FastMCP

import evidence_db as db
from tools.arxiv_search import search_arxiv as _arxiv
from tools.web_search import TRUSTED_DOMAINS, search_web as _web

DB = os.environ.get("SYNTHESIS_DB", db.DB_PATH)
MAX_RESULTS = 10

mcp = FastMCP("synthesis-search")


def _brief(found):
    return json.dumps([{"source_id": p["source_id"], "title": p["title"]} for p in found])


def _clamp(n):
    return max(1, min(int(n), MAX_RESULTS))


@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> str:
    """Search arXiv papers. Stores them as sources and returns a JSON list of {source_id, title}."""
    return _brief(_arxiv(query, max_results=_clamp(max_results), db_path=DB))


@mcp.tool()
def search_web(query: str, max_results: int = 3) -> str:
    """Search trusted web domains only. Stores results as sources and returns a JSON list of {source_id, title}."""
    return _brief(_web(query, max_results=_clamp(max_results), db_path=DB,
                       include_domains=TRUSTED_DOMAINS))


if __name__ == "__main__":
    mcp.run()