import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_server import search_server as s
from tools.web_search import TRUSTED_DOMAINS

SERVER = Path(__file__).resolve().parent.parent / "mcp_server" / "search_server.py"

async def _tool_names(db_path):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)],
                                   env={"SYNTHESIS_DB": str(db_path)})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return [t.name for t in (await session.list_tools()).tools]


def test_server_exposes_only_the_two_search_tools(tmp_path):
    names = asyncio.run(_tool_names(tmp_path / "t.db"))
    assert sorted(names) == ["search_arxiv", "search_web"]


def test_tool_returns_only_ids_and_titles(monkeypatch):
    monkeypatch.setattr(s, "_arxiv", lambda q, max_results, db_path: [
        {"source_id": 1, "title": "T", "text": "secret body"}])
    assert json.loads(s.search_arxiv("x")) == [{"source_id": 1, "title": "T"}]


def test_max_results_is_clamped(monkeypatch):
    seen = {}
    monkeypatch.setattr(s, "_arxiv", lambda q, max_results, db_path:
                        seen.update(n=max_results) or [])
    s.search_arxiv("x", max_results=999)
    assert seen["n"] == 10


def test_web_search_always_uses_trusted_domains(monkeypatch):
    seen = {}
    monkeypatch.setattr(s, "_web", lambda q, max_results, db_path, include_domains:
                        seen.update(d=include_domains) or [])
    s.search_web("x")
    assert seen["d"] == TRUSTED_DOMAINS