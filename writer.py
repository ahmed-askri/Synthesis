import re

import evidence_db as db
import llm

SYSTEM = (
    "You write a short, factual research report answering a question. "
    "You are given verified claims, each with the source numbers that support it "
    "and where it came from. "
    "Use ONLY these claims; add no outside facts, numbers or names. "
    "Claims whose 'from' list contains web come from web pages, which are less reliable "
    "than papers. The first sentence built on such a claim should say 'A web source reports that'. "
    "Never put a web claim and a paper claim in the same sentence. "
    "EVERY sentence must end with at least one citation in square brackets, like [3] or [3][7]. "
    "Do not cite any number that is not given. "
    "Do not write introductions, conclusions or general statements. "
    "Add no interpretation, consequences or purposes (no 'thereby', 'suggesting', 'which can'). "
    "Report what the sources found ('The authors show...', 'RecoAtlas reports...'), "
    "never general rules about how evaluation should be done. "
    "Write 2-4 short paragraphs of plain prose, no headings."
)

WEB_PHRASE = re.compile(r"\b(web (source|article|page|site|post)s?|according to a web)\b", re.I)
WEB_PREFIX = "A web source reports: "


def _audit(body, allowed):
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    invalid = sorted(cited - set(allowed))
    sentences = re.split(r"(?<=[.!?])\s+", body)
    uncited = [s for s in sentences if s and not re.search(r"\[\d+\]", s)]
    return cited, invalid, uncited


def _web_pass(body, web_ids, fix):
    """Walk the sentences. A sentence that cites only web sources must say it is a web
    source. A follow-up may continue only about a web source already introduced.
    With fix=True the CODE adds the prefix; sentences that mix web and paper sources
    cannot be fixed and are returned."""
    parts = re.split(r"(?<=[.!?])(\s+)", body)  # keeps the paragraph breaks
    bad = []
    attributed = set()  # web sources already introduced in the current run of sentences
    for i in range(0, len(parts), 2):
        s = parts[i]
        cites = {int(n) for n in re.findall(r"\[(\d+)\]", s)}
        if not cites & web_ids:
            attributed = set()
        elif WEB_PHRASE.search(s):
            attributed = cites & web_ids
        elif cites <= attributed:
            pass  # follow-up about a source that was already attributed
        elif fix and cites <= web_ids:
            parts[i] = WEB_PREFIX + s
            attributed = set(cites)
        else:
            bad.append(s)
            attributed = set()
    return "".join(parts), bad


def _unattributed(body, web_ids):
    return _web_pass(body, web_ids, fix=False)[1]


def _claim_line(claim, db_path):
    origins = set()
    for sid in claim["source_ids"]:
        src = db.get_source(sid, db_path)
        if src:
            origins.add(src["origin"])
    ids = ", ".join(map(str, claim["source_ids"]))
    return f"- (sources: {ids}; from: {', '.join(sorted(origins))}) {claim['text']}"


def write_report(question, db_path=db.DB_PATH, ask_fn=llm.ask, max_attempts=2):
    claims = db.get_claims("supported", db_path)
    if not claims:
        return {"report": "", "ok": False, "invalid_citations": [],
                "uncited_sentences": [], "unattributed_web_sentences": [],
                "note": "No supported claims."}

    allowed = sorted({sid for c in claims for sid in c["source_ids"]})
    web_ids = set()
    for sid in allowed:
        src = db.get_source(sid, db_path)
        if src and src["origin"] == "web":
            web_ids.add(sid)

    lines = [_claim_line(c, db_path) for c in claims]
    base = f"Question: {question}\n\nVerified claims:\n" + "\n".join(lines)

    user = base
    for _ in range(max_attempts):
        body = ask_fn(SYSTEM, user).strip()
        body = re.sub(r"\s*([.!?])\s*((?:\[\d+\])+)", r" \2\1", body)  # "text. [1]" -> "text [1]."
        body, _ = _web_pass(body, web_ids, fix=True)  # code guarantees web attribution
        cited, invalid, uncited = _audit(body, allowed)
        unattributed = _unattributed(body, web_ids)  # only mixed sentences can remain
        if not invalid and not uncited and not unattributed:
            break
        problems = []
        if uncited:
            problems.append("Sentences with no citation: " + " | ".join(uncited[:3]))
        if invalid:
            problems.append(f"Cited numbers that do not exist: {invalid}")
        if unattributed:
            problems.append("Sentences mixing web and paper sources: "
                            + " | ".join(unattributed[:3])
                            + ". Split them: one sentence per kind of source.")
        user = (base + "\n\nYour previous draft broke the rules.\n" + "\n".join(problems)
                + "\nRewrite the whole report; every sentence must end with a valid [n] citation.")

    refs = []
    for sid in sorted(cited & set(allowed)):
        src = db.get_source(sid, db_path)
        tag = " (web)" if src["origin"] == "web" else ""
        refs.append(f"[{sid}] {src['title']}{tag} - {src['url']}")

    report = body + "\n\n## References\n" + "\n".join(refs)
    ok = not invalid and not uncited and not unattributed
    note = ""
    if unattributed and not invalid and not uncited:
        note = "A sentence mixes web and paper sources and could not be separated."
    return {"report": report, "ok": ok, "invalid_citations": invalid,
            "uncited_sentences": uncited, "unattributed_web_sentences": unattributed,
            "note": note}