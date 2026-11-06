"""Evidence citation checker and helpers. Pure code, no model calls."""

import difflib
import json
import re

CITE = re.compile(r"\[(E\d+)\s*:\s*([^\]]*)\]")


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def check_citations(message: str, case: dict) -> list:
    """Label every [E#: text] in a message as valid / misquoted / nonexistent."""
    ev = {e["id"]: e["text"] for e in case["evidence"]}
    out = []
    for eid, quoted in CITE.findall(message):
        if eid not in ev:
            label = "nonexistent"
        else:
            q, src = _norm(quoted), _norm(ev[eid])
            ratio = difflib.SequenceMatcher(None, q, src).find_longest_match(0, len(q), 0, len(src)).size
            # valid if the quote is (almost) a substring of the clue
            label = "valid" if q and (q in src or ratio >= 0.85 * len(q)) else "misquoted"
        out.append({"id": eid, "quoted": quoted, "label": label})
    return out


MARKS = {"valid": "(verified)", "misquoted": "(MISQUOTED)", "nonexistent": "(NOT IN CASE FILE)"}


def mark_citations(message: str, case: dict) -> str:
    """Append the checker's verdict after every citation, for judges who cannot see the case file."""
    labels = iter(c["label"] for c in check_citations(message, case))
    return CITE.sub(lambda m: f"{m.group(0)} {MARKS[next(labels)]}", message)


def split_sentences(text: str) -> list:
    """Split a message into sentences, keeping citations intact."""
    protected = CITE.sub(lambda m: m.group(0).replace(".", "§"), text)
    parts = re.split(r"(?<=[.!?])\s+", protected.strip())
    return [p.replace("§", ".") for p in parts if p.strip()]


def parse_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def match_name(raw, suspects):
    """Map a model's free-text answer onto a suspect name (or None)."""
    if not raw:
        return None
    raw = str(raw).lower()
    hits = [s for s in suspects if s.lower() in raw]
    return hits[0] if len(hits) == 1 else None
