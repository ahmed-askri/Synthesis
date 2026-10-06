import re

import llm

CATEGORIES = ("cs.AI", "cs.CL", "cs.MA", "cs.LG", "cs.SE")

SYSTEM = (
    "You turn a research question into an arXiv search plan. "
    "Return 2 to 4 concept groups. Each group is a list of 1 to 4 short synonyms or "
    "spellings for ONE concept that a relevant paper's abstract must mention. "
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


def plan_query(question, ask_fn=llm.ask_json):
    try:
        groups = ask_fn(SYSTEM, question).get("groups", [])
    except Exception:
        groups = []
    return build_arxiv_query(groups) or question  # fall back to the raw question