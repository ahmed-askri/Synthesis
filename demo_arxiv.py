import evidence_db as db
from tools.arxiv_search import search_arxiv

db.init_db()
for r in search_arxiv("Codefuse CGM", max_results=3):
    print(r)