import evidence_db as db


def test_source_and_claim_roundtrip(tmp_path):
    path = tmp_path / "test.db"
    db.init_db(path)

    sid = db.add_source("https://arxiv.org/abs/1", "A paper", "Some text", "arxiv", path)
    assert db.add_source("https://arxiv.org/abs/1", "A paper", "Some text", "arxiv", path) == sid

    cid = db.add_claim("Agents need evals", [sid], path)
    assert db.get_claims("unchecked", path)[0]["source_ids"] == [sid]

    db.set_claim_status(cid, "supported", path)
    assert db.get_claims("supported", path)[0]["id"] == cid
    assert db.get_claims("unchecked", path) == []


def test_quarantine(tmp_path):
    path = tmp_path / "test.db"
    db.init_db(path)
    sid = db.add_source("https://x.com", "t", "text", "web", path)
    db.quarantine_source(sid, path)
    assert db.get_source(sid, path)["quarantined"] == 1