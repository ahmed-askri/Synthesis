import datetime
from types import SimpleNamespace

import evidence_db as db
from tools import arxiv_search


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def results(self, search):
        yield SimpleNamespace(
            entry_id="http://arxiv.org/abs/2401.00001v1",
            title="Evaluating Agents",
            summary="We study agent evaluation.",
            authors=[SimpleNamespace(name="A. Author")],
            published=datetime.datetime(2024, 1, 1),
        )


def test_search_arxiv_saves_sources(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    db.init_db(path)
    monkeypatch.setattr(arxiv_search.arxiv, "Client", FakeClient)

    out = arxiv_search.search_arxiv("agents", 1, db_path=path)

    assert out[0]["title"] == "Evaluating Agents"
    saved = db.get_source(out[0]["source_id"], path)
    assert saved["origin"] == "arxiv"
    assert "We study agent evaluation." in saved["text"]