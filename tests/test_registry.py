import pytest
from tools.registry import ToolRegistry, PermissionDenied


def make():
    reg = ToolRegistry()
    reg.register("search_web", lambda query: ["web:" + query])
    reg.register("search_arxiv", lambda query: ["arxiv:" + query])
    return reg


def test_researcher_can_search():
    assert make().call("researcher", "search_web", query="x") == ["web:x"]


def test_writer_cannot_search():
    with pytest.raises(PermissionDenied):
        make().call("writer", "search_web", query="x")


def test_fact_checker_cannot_search():
    with pytest.raises(PermissionDenied):
        make().call("fact_checker", "search_arxiv", query="x")


def test_unknown_role_is_denied():
    with pytest.raises(PermissionDenied):
        make().call("hacker", "search_web", query="x")


def test_denied_tool_never_runs():
    ran = []
    reg = ToolRegistry()
    reg.register("search_web", lambda query: ran.append(query))
    with pytest.raises(PermissionDenied):
        reg.call("writer", "search_web", query="x")
    assert ran == []


def test_denied_attempt_is_logged():
    reg = make()
    with pytest.raises(PermissionDenied):
        reg.call("writer", "search_web", query="x")
    assert reg.denied == [("writer", "search_web")]