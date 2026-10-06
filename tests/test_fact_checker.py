import evidence_db as db
from fact_checker import check_all

SOURCE_TEXT = "Agents need evals before they ship to production."


def _setup(tmp_path, text=SOURCE_TEXT):
    path = tmp_path / "t.db"
    db.init_db(path)
    s1 = db.add_source("https://a.com", "A", text, "web", path)
    return path, s1


def _status(path, cid):
    return {c["id"]: c["status"] for c in db.get_claims(path=path)}[cid]


def _ans(status, quote=""):
    return lambda system, user: {"status": status, "quote": quote, "reason": "r"}


def test_supported_with_real_quote(tmp_path):
    path, s1 = _setup(tmp_path)
    cid = db.add_claim("Evals are needed before shipping.", [s1], path)
    check_all(path, ask_fn=_ans("supported", "Agents need evals before they ship"))
    assert _status(path, cid) == "supported"


def test_quote_matches_despite_dash_and_case(tmp_path):
    path, s1 = _setup(tmp_path, "Behavior\u2011grounded metrics are introduced by the paper.")
    cid = db.add_claim("The paper introduces metrics.", [s1], path)
    check_all(path, ask_fn=_ans("supported", "behavior-grounded metrics are introduced"))
    assert _status(path, cid) == "supported"


def test_fabricated_quote_is_rejected(tmp_path):
    path, s1 = _setup(tmp_path)
    cid = db.add_claim("Evals are needed.", [s1], path)
    check_all(path, ask_fn=_ans("supported", "This sentence is not in the source at all"))
    assert _status(path, cid) == "unsupported"


def test_missing_quote_is_rejected(tmp_path):
    path, s1 = _setup(tmp_path)
    cid = db.add_claim("Evals are needed.", [s1], path)
    check_all(path, ask_fn=_ans("supported", ""))
    assert _status(path, cid) == "unsupported"


def test_garbled_answer_fails_closed(tmp_path):
    path, s1 = _setup(tmp_path)
    cid = db.add_claim("Evals are needed.", [s1], path)
    check_all(path, ask_fn=_ans("banana"))
    assert _status(path, cid) == "unsupported"


def test_quarantined_source_is_unsupported(tmp_path):
    path, s1 = _setup(tmp_path)
    db.quarantine_source(s1, path)
    cid = db.add_claim("Evals are needed.", [s1], path)
    check_all(path, ask_fn=_ans("supported", "Agents need evals before they ship"))
    assert _status(path, cid) == "unsupported"