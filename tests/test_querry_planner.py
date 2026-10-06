from query_planner import build_arxiv_query, plan_query


def test_groups_become_and_of_ors_with_categories():
    q = build_arxiv_query([["LLM", "large language model"], ["multi-agent"]])
    assert 'abs:"LLM" OR abs:"large language model"' in q
    assert 'AND (abs:"multi-agent")' in q
    assert "cat:cs.AI" in q


def test_terms_cannot_inject_search_syntax():
    q = build_arxiv_query([['LLM" OR all:"x']])
    assert q.count('"') == 2  # one quoted term, nothing broke out of it


def test_falls_back_to_question_when_model_fails():
    def boom(system, user):
        raise ValueError("bad json")

    assert plan_query("my question?", ask_fn=boom) == "my question?"