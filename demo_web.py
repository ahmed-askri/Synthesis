import evidence_db as db
from tools.web_search import search_web

db.init_db()
for r in search_web("how to evaluate LLM agents in production", max_results=3):
    print(r)