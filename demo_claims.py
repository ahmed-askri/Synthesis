import evidence_db as db
from tools.arxiv_search import search_arxiv
from researcher import extract_claims

db.init_db()
question = "How should LLM agents be evaluated?"
found = search_arxiv(question, max_results=3)
ids = extract_claims(question, [r["source_id"] for r in found])
for c in db.get_claims():
    print(c["id"], c["source_ids"], c["text"])