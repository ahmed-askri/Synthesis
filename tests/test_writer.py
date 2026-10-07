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


def _web_db(tmp_path, origin="web"):
    path = tmp_path / "t.db"
    db.init_db(path)
    s = db.add_source("https://example.org/p", "Page", "text", origin, path)
    cid = db.add_claim("Page says X.", [s], path)
    db.set_claim_status(cid, "supported", path)
    return path, s


def test_code_adds_web_attribution_when_model_forgets(tmp_path):
    path, s = _web_db(tmp_path)
    calls = []

    def fake(system, user):
        calls.append(user)
        return f"First fact [{s}].\n\nSecond fact [{s}]."

    out = write_report("q?", path, ask_fn=fake)
    assert out["ok"] is True
    assert len(calls) == 1
    assert "A web source reports: First fact" in out["report"]
    assert "A web source reports: Second" not in out["report"]  # follow-up, not prefixed
    assert "\n\n" in out["report"]  # paragraph break kept


def test_existing_attribution_is_not_doubled(tmp_path):
    path, s = _web_db(tmp_path)
    text = f"A web source reports that X [{s}]. It also reports Y [{s}]."
    out = write_report("q?", path, ask_fn=lambda system, user: text)
    assert out["ok"] is True
    assert out["report"].count("web source reports") == 1


def test_paper_sentences_are_not_touched(tmp_path):
    path, s = _web_db(tmp_path, origin="arxiv")
    out = write_report("q?", path, ask_fn=lambda system, user: f"The authors show X [{s}].")
    assert out["ok"] is True
    assert "web source" not in out["report"]


def test_sentence_mixing_web_and_paper_is_rejected(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    w = db.add_source("https://blog.example", "Blog", "text", "web", path)
    p = db.add_source("https://arxiv.org/abs/1", "Paper", "text", "arxiv", path)
    for sid in (w, p):
        cid = db.add_claim("Claim.", [sid], path)
        db.set_claim_status(cid, "supported", path)
    out = write_report("q?", path, ask_fn=lambda system, user: f"X and Y [{w}][{p}].")
    assert out["ok"] is False
    assert out["unattributed_web_sentences"]

def test_each_web_source_gets_its_own_attribution(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    ids = []
    for name in ("A", "B"):
        s = db.add_source(f"https://{name}.example", f"Page {name}", "text", "web", path)
        cid = db.add_claim("Claim.", [s], path)
        db.set_claim_status(cid, "supported", path)
        ids.append(s)
    a, b = ids
    text = f"First [{a}]. Second [{b}]."
    out = write_report("q?", path, ask_fn=lambda system, user: text)
    assert out["report"].count("A web source reports:") == 2