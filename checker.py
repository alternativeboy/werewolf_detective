"""Evidence citation checker and helpers. Pure code, no model calls."""

import difflib
import json
import re

CITE = re.compile(r"\[([ER]\d+)\s*:\s*([^\]]*)\]")  # E# = evidence, R# = case rules


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


# it20: the name-aware clerk. The default clerk (85% fuzzy match) marks a quote that swaps one
# suspect's name for another as (verified). With names=True a quote is also MISQUOTED if it
# names a suspect that the real evidence line does not name. Games are played with the default
# clerk; names=True is only used by rejudge.py --clerk2.
CLERK2_VERSION = "names1"


def _names_in(text: str, suspects: list) -> set:
    t = _norm(text)
    return {s for s in suspects if re.search(rf"\b{re.escape(_norm(s))}\b", t)}


def check_citations(message: str, case: dict, names: bool = False) -> list:
    """Label every [E#: text] in a message as valid / misquoted / nonexistent."""
    ev = {e["id"]: e["text"] for e in case["evidence"]}
    if isinstance(case.get("rules"), list):
        ev.update({r["id"]: r["text"] for r in case["rules"]})
    out = []
    for eid, quoted in CITE.findall(message):
        if eid not in ev:
            label = "nonexistent"
        else:
            q, src = _norm(quoted), _norm(ev[eid])
            ratio = difflib.SequenceMatcher(None, q, src).find_longest_match(0, len(q), 0, len(src)).size
            # valid if the quote is (almost) a substring of the clue
            label = "valid" if q and (q in src or ratio >= 0.85 * len(q)) else "misquoted"
            if (names and label == "valid"
                    and not _names_in(quoted, case["suspects"]) <= _names_in(ev[eid], case["suspects"])):
                label = "misquoted"
        out.append({"id": eid, "quoted": quoted, "label": label})
    return out


MARKS = {"valid": "(verified)", "misquoted": "(MISQUOTED)", "nonexistent": "(NOT IN CASE FILE)"}


def mark_citations(message: str, case: dict, names: bool = False) -> str:
    """Append the checker's verdict after every citation, for judges who cannot see the case file."""
    labels = iter(c["label"] for c in check_citations(message, case, names=names))
    return CITE.sub(lambda m: f"{m.group(0)} {MARKS[next(labels)]}", message)


CUT_MARK = "... (cut: over word limit)"  # round brackets, so CITE never reads it as a citation


def cap_words(text: str, limit: int):
    """Cut a message after `limit` words, keeping its formatting. Returns (text, words_cut).

    If the cut lands inside a citation, the whole unfinished citation is dropped. Otherwise a
    half citation such as "[E9: Nobody can say where" is checked as MISQUOTED: in v3/v4 smoke
    games every "bad" citation (10 of 10) was this artifact, not a real misquote.
    """
    words = list(re.finditer(r"\S+", text))
    if len(words) <= limit:
        return text, 0
    cut = text[:words[limit - 1].end()]
    start = cut.rfind("[")
    if start != -1 and "]" not in cut[start:]:
        cut = cut[:start].rstrip()
    kept = len(re.findall(r"\S+", cut))
    return f"{cut} {CUT_MARK}", len(words) - kept


def is_cut_artifact(citation: dict) -> bool:
    """True for a citation that was half cut by cap_words before the fix above."""
    return "[cut: over word limit" in citation.get("quoted", "")


ACCUSE_LINE = re.compile(r"^[\s*_#>-]*ACCUSE[\s*_]*:[\s*_]*(.+?)[\s*_.]*$", re.I | re.M)


def split_accusation(text: str, suspects: list):
    """Take the detective's 'ACCUSE: <name>' line out of a message.

    Returns (body without that line, accused suspect or None). If there are several such
    lines, the last one counts. The body is what gets word-capped, so the line is never cut.
    """
    found = list(ACCUSE_LINE.finditer(text))
    if not found:
        return text.strip(), None
    last = found[-1]
    body = (text[:last.start()] + text[last.end():]).strip()
    return body, match_name(last.group(1), suspects)


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
    raw = str(raw).strip().lower()
    exact = [s for s in suspects if s.lower() == raw]
    if exact:
        return exact[0]
    # Whole words only: "Ek" must not match inside "Lek", "Chai" not inside "Somchai".
    hits = [s for s in suspects if re.search(rf"\b{re.escape(s.lower())}\b", raw)]
    return hits[0] if len(hits) == 1 else None
