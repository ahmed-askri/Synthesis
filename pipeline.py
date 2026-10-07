import sys
from collections import Counter
from pathlib import Path

import evidence_db as db
import fact_checker
import researcher
import writer
from guardrails.approval import cli_approve, save_with_approval
from guardrails.sanitize import scan_sources
from query_planner import plan_groups, search_with_relaxation
from tools.arxiv_search import search_arxiv
from tools.registry import ToolRegistry
from tools.web_search import TRUSTED_DOMAINS, search_web


def make_registry(db_path, use_mcp=True):
    """All search tools live here. Roles can only call what they are allowed.
    With use_mcp the tools run inside the MCP search server."""
    reg = ToolRegistry()
    if use_mcp:
        from tools.mcp_client import SearchClient
        client = SearchClient(db_path)
        reg.register("search_arxiv", lambda query, max_results: client.call(
            "search_arxiv", query=query, max_results=max_results))
        # the server enforces the trusted domains, include_domains is ignored here
        reg.register("search_web", lambda query, max_results, include_domains=None: client.call(
            "search_web", query=query, max_results=max_results))
    else:
        reg.register("search_arxiv", lambda query, max_results: search_arxiv(
            query, max_results=max_results, db_path=db_path))
        reg.register("search_web", lambda query, max_results, include_domains=None: search_web(
            query, max_results=max_results, db_path=db_path, include_domains=include_domains))
    return reg


def run(question, max_papers=5, max_web=3, db_path=db.DB_PATH, fresh=True,
        log=print, approve=None, use_web=True, use_mcp=True):
    if fresh:
        Path(db_path).unlink(missing_ok=True)
    db.init_db(db_path)

    tools = make_registry(db_path, use_mcp=use_mcp)
    if use_mcp:
        log("[mcp]   search tools run through the MCP server")

    groups = plan_groups(question)
    found, query = search_with_relaxation(
        groups,
        lambda q: tools.call("researcher", "search_arxiv", query=q, max_results=max_papers),
        log=log)
    log(f"[plan]  query: {query or question}")
    if not found:
        log("        no results, falling back to the raw question")
        found = tools.call("researcher", "search_arxiv", query=question, max_results=max_papers)

    if use_web:
        try:
            web = tools.call("researcher", "search_web", query=question,
                             max_results=max_web, include_domains=TRUSTED_DOMAINS)
            if not web:
                log("[web]   no results from trusted domains")
            found += web
        except Exception as e:
            log(f"[web]   skipped: {type(e).__name__}: {e}")

    source_ids = [p["source_id"] for p in found]
    log(f"[1/4] search:   {len(source_ids)} sources")
    for p in found:
        log(f"        - {p['title']}")

    flagged = scan_sources(source_ids, db_path)
    for f in flagged:
        log(f"[scan]  excluded: {f['title']} ({', '.join(f['reasons'])})")
    log(f"[scan]  {len(flagged)} of {len(source_ids)} sources excluded as suspicious")

    researcher.extract_claims(question, source_ids, db_path)
    n_claims = len(db.get_claims("unchecked", db_path))
    log(f"[2/4] extract:  {n_claims} claims")

    results = fact_checker.check_all(db_path)
    counts = Counter(r["status"] for r in results.values())
    log(f"[3/4] check:    {dict(counts)}")

    out = writer.write_report(question, db_path)
    log(f"[4/4] write:    {len(out['invalid_citations'])} invalid citations, "
        f"{len(out['uncited_sentences'])} uncited sentences")

    for role, tool in tools.denied:
        log(f"[tools] BLOCKED: {role} tried to call {tool}")

    if not out["ok"]:
        log("        REJECTED: report failed the citation check")
    elif approve is not None:
        saved = save_with_approval(out["report"], approve)
        log(f"        saved to {saved}" if saved else "        not saved (no approval)")
    return out


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How should LLM agents be evaluated?"
    result = run(q, approve=cli_approve)
    if not result["ok"]:
        print("\n" + (result["note"] or "No report was produced."))