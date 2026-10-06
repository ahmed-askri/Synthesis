from guardrails.approval import save_with_approval


def test_denied_saves_nothing(tmp_path):
    target = tmp_path / "r.md"
    assert save_with_approval("# report", lambda r: False, str(target)) is None
    assert not target.exists()


def test_approved_saves(tmp_path):
    target = tmp_path / "out" / "r.md"
    assert save_with_approval("# report", lambda r: True, str(target)) == str(target)
    assert target.read_text(encoding="utf-8") == "# report"


def test_only_a_real_yes_counts(tmp_path):
    target = tmp_path / "r.md"
    assert save_with_approval("# report", lambda r: "yes", str(target)) is None
    assert not target.exists()


def test_empty_report_is_never_saved(tmp_path):
    target = tmp_path / "r.md"
    assert save_with_approval("   ", lambda r: True, str(target)) is None
    assert not target.exists()