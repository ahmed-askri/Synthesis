from pathlib import Path

import evidence_db as db
from writer import write_report

db.init_db()
out = write_report("How should LLM agents be evaluated?")
print(out["report"] or out["note"])
if out["invalid_citations"]:
    print("\nWARNING, invented citations:", out["invalid_citations"])
if out["uncited_sentences"]:
    print("\nWARNING, uncited sentences:")
    for s in out["uncited_sentences"]:
        print("  -", s)

Path("reports").mkdir(exist_ok=True)
Path("reports/report.md").write_text(out["report"], encoding="utf-8")