import re
import unicodedata
import html
import evidence_db as db

ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")

# (name, regex, severity)
# high   = quarantine from any origin
# medium = quarantine web content only, because papers about prompt injection
#          legitimately quote phrases like these
PATTERNS = [
    ("chat-template-token",
     r"<\|(?:im_start|im_end|system|assistant|user)\|>|\[/?INST\]|<</?SYS>>", "high"),
    ("hide-from-user",
     r"\b(?:do not|don't|never)\s+(?:tell|inform|mention|reveal|show)\b[^.\n]{0,30}\b(?:user|human|reader)\b", "high"),
    ("exfiltration-link",
     r"!\[[^\]]*\]\(https?://[^)\s]*[?&][^)\s]*\)", "high"),
    ("ignore-instructions",
     r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all|your|system)\b"
     r"[^.\n]{0,30}\b(?:instructions?|prompts?|rules?|guidelines?)\b", "medium"),
    ("role-change",
     r"\byou are now\b|\bfrom now on,? you\b|\bnew instructions\s*:", "medium"),
    ("prompt-leak-request",
     r"\b(?:reveal|print|repeat|output|show)\b[^.\n]{0,30}\b(?:system prompt|hidden prompt|your instructions|api key|secret)s?\b", "medium"),
    ("send-to-url",
     r"\b(?:send|post|upload|forward|email)\b[^.\n]{0,60}\bhttps?://", "medium"),
    ("role-line",
     r"^\s*(?:system|assistant)\s*:", "medium"),
]
COMPILED = [(n, re.compile(p, re.I | re.M), s) for n, p, s in PATTERNS]


def scan_text(text):
    """Return a list of (pattern_name, severity) found in the text."""
    hits = []
    if len(ZERO_WIDTH.findall(text)) >= 3:
        hits.append(("invisible-text", "medium"))
    clean = ZERO_WIDTH.sub("", unicodedata.normalize("NFKC", text))
    for name, pattern, severity in COMPILED:
        if pattern.search(clean):
            hits.append((name, severity))
    return hits


def should_quarantine(hits, origin):
    if any(sev == "high" for _, sev in hits):
        return True
    return bool(hits) and origin != "arxiv"


def scan_sources(source_ids, db_path=db.DB_PATH):
    """Scan stored sources, quarantine the suspicious ones, return what was flagged."""
    flagged = []
    for sid in source_ids:
        src = db.get_source(sid, db_path)
        if src is None or src["quarantined"]:
            continue
        hits = scan_text(src["text"])
        if should_quarantine(hits, src["origin"]):
            db.quarantine_source(sid, db_path)
            flagged.append({"source_id": sid, "title": src["title"],
                            "reasons": sorted({name for name, _ in hits})})
    return flagged

TAG = re.compile(r"<[^>]+>")
SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_web_text(text, max_len=4000):
    """Strip markup where hidden instructions like to live, and cap the length."""
    text = COMMENT.sub(" ", text)
    text = SCRIPT.sub(" ", text)
    text = TAG.sub(" ", text)
    text = html.unescape(text)
    text = CONTROL.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:max_len]