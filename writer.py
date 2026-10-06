import re

import evidence_db as db
import llm

SYSTEM = (
    "You write a short, factual research report answering a question. "
    "You are given verified claims, each with the source numbers that support it "
    "and where it came from. "
    "Use ONLY these claims; add no outside facts, numbers or names. "
    "Claims whose 'from' list contains web come from web pages, which are less reliable "
    "than papers. Start each sentence built on such a claim with 'A web source reports that' "
    "or 'According to a web article,' and never present it as established fact. "
    "EVERY sentence must end with at least one citation in square brackets, like [3] or [3][7]. "
    "Do not cite any number that is not given. "
    "Do not write introductions, conclusions or general statements. "
    "Add no interpretation, consequences or purposes (no 'thereby', 'suggesting', 'which can'). "
    "Report what the sources found ('The authors show...', 'RecoAtlas reports...'), "
    "never general rules about how evaluation should be done. "
    "Write 2-4 short paragraphs of plain prose, no headings."
)


def _audit(body, allowed):
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    invalid = sorted(cited - set(allowed))
    sentences = re.split(r"(?<=[.!?])\s+", body)
    uncited = [s for s in sentences if s and not re.search(r"\[\d+\]", s)]
    return cited, invalid, uncited


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
                "uncited_sentences": [], "note": "No supported claims."}

    allowed = sorted({sid for c in claims for sid in c["source_ids"]})
    lines = [_claim_line(c, db_path) for c in claims]
    base = f"Question: {question}\n\nVerified claims:\n" + "\n".join(lines)

    user = base
    for _ in range(max_attempts):
        body = ask_fn(SYSTEM, user).strip()
        body = re.sub(r"\s*([.!?])\s*((?:\[\d+\])+)", r" \2\1", body)  # "text. [1]" -> "text [1]."
        cited, invalid, uncited = _audit(body, allowed)
        if not invalid and not uncited:
            break
        problems = []
        if uncited:
            problems.append("Sentences with no citation: " + " | ".join(uncited[:3]))
        if invalid:
            problems.append(f"Cited numbers that do not exist: {invalid}")
        user = (base + "\n\nYour previous draft broke the rules.\n" + "\n".join(problems)
                + "\nRewrite the whole report; every sentence must end with a valid [n] citation.")

    refs = []
    for sid in sorted(cited & set(allowed)):
        src = db.get_source(sid, db_path)
        tag = " (web)" if src["origin"] == "web" else ""
        refs.append(f"[{sid}] {src['title']}{tag} - {src['url']}")

    report = body + "\n\n## References\n" + "\n".join(refs)
    ok = not invalid and not uncited
    return {"report": report, "ok": ok, "invalid_citations": invalid,
            "uncited_sentences": uncited, "note": ""}