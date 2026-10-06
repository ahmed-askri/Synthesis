import evidence_db as db
from fact_checker import check_all


def test_statuses_and_failing_closed(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    s1 = db.add_source("https://a.com", "A", "Agents need evals.", "web", path)
    bad = db.add_source("https://bad.com", "Bad", "text", "web", path)
    db.quarantine_source(bad, path)

    c_ok = db.add_claim("Agents need evals.", [s1], path)
    c_garbled = db.add_claim("Something else.", [s1], path)
    c_quarantined = db.add_claim("From bad source.", [bad], path)

    def fake_ask(system, user):
        if "Agents need evals." in user.split("Sources:")[0]:
            return {"status": "supported", "reason": "stated"}
        return {"status": "banana"}  # garbled output

    check_all(path, ask_fn=fake_ask)

    status = {c["id"]: c["status"] for c in db.get_claims(path=path)}
    assert status[c_ok] == "supported"
    assert status[c_garbled] == "unsupported"
    assert status[c_quarantined] == "unsupported"