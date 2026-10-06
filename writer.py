import re

import evidence_db as db
import llm

SYSTEM = (
    "You write a short, factual research report answering a question. "
    "You are given verified claims, each with the source numbers that support it. "
    "Use ONLY these claims; add no outside facts, numbers or names. "
    "EVERY sentence must end with at least one citation in square brackets, like [3] or [3][7]. "
    "Do not cite any number that is not given. "
    "Do not write introductions, conclusions or general statements. "
    "Report what the sources found ('The authors show...', 'RecoAtlas reports...'), "
    "never general rules about how evaluation should be done. "
    "Write 2-4 short paragraphs of plain prose, no headings."
)


def write_report(question, db_path=db.DB_PATH, ask_fn=llm.ask):
    claims = db.get_claims("supported", db_path)
    if not claims:
        return {"report": "", "invalid_citations": [], "uncited_sentences": [],
                "note": "No supported claims."}

    allowed = sorted({sid for c in claims for sid in c["source_ids"]})
    lines = [f"- (sources: {', '.join(map(str, c['source_ids']))}) {c['text']}" for c in claims]
    user = f"Question: {question}\n\nVerified claims:\n" + "\n".join(lines)

    body = ask_fn(SYSTEM, user).strip()
    body = re.sub(r"\s*([.!?])\s*((?:\[\d+\])+)", r" \2\1", body)
   
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    invalid = sorted(cited - set(allowed))

    sentences = re.split(r"(?<=[.!?])\s+", body)
    uncited = [s for s in sentences if s and not re.search(r"\[\d+\]", s)]

    refs = []
    for sid in sorted(cited & set(allowed)):
        src = db.get_source(sid, db_path)
        refs.append(f"[{sid}] {src['title']} - {src['url']}")

    report = body + "\n\n## References\n" + "\n".join(refs)
    return {"report": report, "invalid_citations": invalid,
            "uncited_sentences": uncited, "note": ""}