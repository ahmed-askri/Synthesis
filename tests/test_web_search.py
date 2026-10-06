import evidence_db as db
from tools.web_search import search_web


class FakeTavily:
    def search(self, query, max_results, search_depth):
        return {
            "results": [
                {"title": "Agent evals", "url": "https://example.com/a", "content": "Evals matter."},
                {"title": "Tracing", "url": "https://example.com/b", "content": "Traces help."},
            ]
        }


def test_search_web_saves_sources(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)

    out = search_web("agents", 2, db_path=path, client=FakeTavily())

    assert [r["title"] for r in out] == ["Agent evals", "Tracing"]
    saved = db.get_source(out[0]["source_id"], path)
    assert saved["origin"] == "web"
    assert "Evals matter." in saved["text"]