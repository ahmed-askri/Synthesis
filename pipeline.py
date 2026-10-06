import sys
from collections import Counter
from pathlib import Path

import evidence_db as db
import fact_checker
import researcher
import writer
from query_planner import plan_query
from tools.arxiv_search import search_arxiv


def run(question, max_papers=5, db_path=db.DB_PATH, fresh=True, log=print):
    if fresh:
        Path(db_path).unlink(missing_ok=True)
    db.init_db(db_path)

    query = plan_query(question)
    log(f"[plan]  query: {query}")
    papers = search_arxiv(query, max_results=max_papers, db_path=db_path)
    if not papers:
        log("        no results, falling back to the raw question")
        papers = search_arxiv(question, max_results=max_papers, db_path=db_path)
    source_ids = [p["source_id"] for p in papers]
    log(f"[1/4] search:   {len(source_ids)} sources")
    for p in papers:
        log(f"        - {p['title']}")

    researcher.extract_claims(question, source_ids, db_path)
    n_claims = len(db.get_claims("unchecked", db_path))
    log(f"[2/4] extract:  {n_claims} claims")

    results = fact_checker.check_all(db_path)
    counts = Counter(r["status"] for r in results.values())
    log(f"[3/4] check:    {dict(counts)}")

    out = writer.write_report(question, db_path)
    log(f"[4/4] write:    {len(out['invalid_citations'])} invalid citations, "
        f"{len(out['uncited_sentences'])} uncited sentences")

    if out["ok"]:
        Path("reports").mkdir(exist_ok=True)
        Path("reports/report.md").write_text(out["report"], encoding="utf-8")
        log("        saved to reports/report.md")
    else:
        log("        REJECTED: report failed the citation check and was NOT saved")
    return out


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How should LLM agents be evaluated?"
    result = run(q)
    print("\n" + (result["report"] or result["note"]))