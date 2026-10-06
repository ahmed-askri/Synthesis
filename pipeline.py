import sys
from collections import Counter
from pathlib import Path

import evidence_db as db
import fact_checker
import researcher
import writer
from guardrails.approval import cli_approve, save_with_approval
from guardrails.sanitize import scan_sources
from query_planner import plan_query
from tools.arxiv_search import search_arxiv
from tools.web_search import search_web


def run(question, max_papers=5, max_web=3, db_path=db.DB_PATH, fresh=True,
        log=print, approve=None, use_web=True):
    if fresh:
        Path(db_path).unlink(missing_ok=True)
    db.init_db(db_path)

    query = plan_query(question)
    log(f"[plan]  query: {query}")
    found = search_arxiv(query, max_results=max_papers, db_path=db_path)
    if not found:
        log("        no results, falling back to the raw question")
        found = search_arxiv(question, max_results=max_papers, db_path=db_path)

    if use_web:
        try:
            found += search_web(question, max_results=max_web, db_path=db_path)
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