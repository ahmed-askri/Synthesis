import evidence_db as db
from fact_checker import check_all

db.init_db()
results = check_all()
claims = {c["id"]: c for c in db.get_claims()}
for cid, r in results.items():
    print(cid, r["status"].upper(), "-", r["reason"])
    print("   ", claims[cid]["text"])