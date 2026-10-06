import re

import llm

CATEGORIES = ("cs.AI", "cs.CL", "cs.MA", "cs.LG", "cs.SE")

SYSTEM = (
    "You turn a research question into an arXiv search plan. "
    "Return 2 to 4 concept groups. Each group is a list of 1 to 4 short synonyms or "
    "spellings for ONE concept that a relevant paper's abstract must mention. "
    "Order the groups from most essential to least essential. "
    "Keep the subject concept precise (for example 'LLM' and 'large language model', "
    "not just 'agent'). "
    'Return JSON: {"groups": [["LLM", "large language model"], ["multi-agent"], ["failure", "error"]]}'
)


def _clean(term):
    return re.sub(r"[^\w\s\-\.]", "", term).strip()


def build_arxiv_query(groups, categories=CATEGORIES):
    parts = []
    for group in groups[:4]:
        if not isinstance(group, list):
            continue
        terms = [_clean(t) for t in group[:4] if isinstance(t, str)]
        terms = [t for t in terms if t]
        if terms:
            parts.append("(" + " OR ".join(f'abs:"{t}"' for t in terms) + ")")
    if not parts:
        return ""
    cats = " OR ".join(f"cat:{c}" for c in categories)
    return " AND ".join(parts) + f" AND ({cats})"


def plan_groups(question, ask_fn=llm.ask_json):
    try:
        groups = ask_fn(SYSTEM, question).get("groups", [])
    except Exception:
        return []
    return [g for g in groups if isinstance(g, list)][:4]


def plan_query(question, ask_fn=llm.ask_json):
    return build_arxiv_query(plan_groups(question, ask_fn)) or question


def search_with_relaxation(groups, search_fn, min_results=3, log=None):
    """Search with all concept groups. If too few results, drop the last group and retry.
    Never goes below 2 groups. Returns (results, query_used)."""
    if not groups:
        return [], ""
    floor = min(2, len(groups))
    found, query = [], ""
    for n in range(len(groups), floor - 1, -1):
        query = build_arxiv_query(groups[:n])
        found = search_fn(query)
        if len(found) >= min_results:
            break
        if log and n > floor:
            log(f"        only {len(found)} results, dropping the last search term")
    return found, query