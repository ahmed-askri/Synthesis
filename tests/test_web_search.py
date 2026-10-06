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

class DomainTavily:
    def __init__(self):
        self.domains = "not called"

    def search(self, query, max_results, search_depth, include_domains=None):
        self.domains = include_domains
        return {"results": []}


def test_domain_list_is_passed_to_tavily(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    client = DomainTavily()
    out = search_web("q", 3, db_path=path, client=client, include_domains=["arxiv.org"])
    assert out == []
    assert client.domains == ["arxiv.org"]

class DuplicateTavily:
    def search(self, query, max_results, search_depth):
        return {"results": [
            {"title": "Paper", "url": "https://x.org/p", "content": "Same page."},
            {"title": "Paper", "url": "https://x.org/p#section", "content": "Same page."},
        ]}


def test_same_page_with_an_anchor_is_one_source(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    out = search_web("q", 2, db_path=path, client=DuplicateTavily())
    assert len(out) == 1
    assert db.get_source(out[0]["source_id"], path)["url"] == "https://x.org/p"

class ArxivTavily:
    def search(self, query, max_results, search_depth):
        return {"results": [{"title": "P", "url": "https://arxiv.org/html/2503.13657v2",
                             "content": "Abstract text."}]}


def test_arxiv_pages_found_by_web_search_count_as_arxiv(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    out = search_web("q", 1, db_path=path, client=ArxivTavily())
    assert db.get_source(out[0]["source_id"], path)["origin"] == "arxiv"