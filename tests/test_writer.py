import evidence_db as db
from writer import write_report


def _setup(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    s1 = db.add_source("https://a.com", "Paper A", "text a", "arxiv", path)
    cid = db.add_claim("Paper A proposes X.", [s1], path)
    db.set_claim_status(cid, "supported", path)
    bad = db.add_claim("Paper A proves Y.", [s1], path)
    db.set_claim_status(bad, "unsupported", path)
    return path, s1


def test_only_supported_claims_reach_writer(tmp_path):
    path, s1 = _setup(tmp_path)
    seen = {}

    def fake_ask(system, user):
        seen["user"] = user
        return f"Paper A proposes X [{s1}]."

    out = write_report("q?", path, ask_fn=fake_ask)
    assert "proposes X" in seen["user"]
    assert "proves Y" not in seen["user"]
    assert "Paper A - https://a.com" in out["report"]
    assert out["invalid_citations"] == []


def test_invented_citation_is_flagged(tmp_path):
    path, s1 = _setup(tmp_path)
    out = write_report("q?", path, ask_fn=lambda s, u: f"Fact [{s1}] and fake fact [99].")
    assert out["invalid_citations"] == [99]


def test_no_supported_claims_means_no_model_call(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)

    def boom(system, user):
        raise AssertionError("model must not be called")

    out = write_report("q?", path, ask_fn=boom)
    assert out["report"] == ""


def test_citation_after_period_is_handled(tmp_path):
    path, s1 = _setup(tmp_path)
    out = write_report("q?", path, ask_fn=lambda s, u: f"Fact one. [{s1}] Fact two. [{s1}]")
    assert out["uncited_sentences"] == []


def test_uncited_sentence_is_flagged(tmp_path):
    path, s1 = _setup(tmp_path)
    out = write_report("q?", path, ask_fn=lambda s, u: f"Cited fact. [{s1}] Unsupported opinion.")
    assert out["uncited_sentences"] == ["Unsupported opinion."]

def test_retry_fixes_a_bad_first_draft(tmp_path):
    path, s1 = _setup(tmp_path)
    drafts = iter(["No citation here.", f"Now it is cited [{s1}]."])
    out = write_report("q?", path, ask_fn=lambda s, u: next(drafts))
    assert out["ok"] is True
    assert out["uncited_sentences"] == []

def test_web_claims_are_marked_for_the_writer(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    s = db.add_source("https://blog.example", "Blog", "text", "web", path)
    cid = db.add_claim("Blogs say X.", [s], path)
    db.set_claim_status(cid, "supported", path)
    seen = {}

    def fake(system, user):
        seen["user"] = user
        return f"A web source reports that X [{s}]."

    out = write_report("q?", path, ask_fn=fake)
    assert "from: web" in seen["user"]
    assert "(web)" in out["report"]