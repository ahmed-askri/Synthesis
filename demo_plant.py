import evidence_db as db
from fact_checker import check_all

db.init_db()
claims = db.get_claims()
reco = claims[0]["source_ids"]   # RecoAtlas source
defa = claims[5]["source_ids"]   # DeFA / Trace2Skill source

planted = {
    "Contradiction":   db.add_claim("Using DeFA's feedback lowers downstream accuracy by 40 percentage points.", defa),
    "Invented number": db.add_claim("RecoAtlas was evaluated on 10 million shopping sessions.", reco),
    "Overreach":       db.add_claim("DeFA is the best failure-attribution method for every LLM agent.", defa),
}

results = check_all()   # only checks the new, unchecked claims
for label, cid in planted.items():
    r = results[cid]
    print(f"{label:16} -> {r['status'].upper()} | {r['reason']}")