"""Extra it17 checks that analyze.py does not print (no model calls).

  python3 it17_checks.py   # reads results/main, results/wrongdet, results/rand2

- frame/misled vs the paired main-run honest game: council right, paired difference with a 95%
  bootstrap CI over cases
- who cites the decoy's hidden (frame) or swapped (misled) alibi, and council right by that
- which version of the swapped clue each speaker quoted (misled) and the clerk's label
- rand2: who first cites the hidden clue, council right when the wolf is silent
"""

import json
import random
from collections import Counter


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def majority(votes):
    c = Counter(v for v in votes if v)
    return c.most_common(1)[0][0] if c and c.most_common(1)[0][1] >= 2 else None


def right(g):
    return majority(g["judges"]["haiku"]["debate_votes"]) == g["answer"]


def clue_ids(g):
    """The decoy's alibi: hidden from the detective (hide-1) or swapped in its copy (misled)."""
    if g.get("detective_case"):
        dc = {e["id"]: e["text"] for e in g["detective_case"]["evidence"]}
        return {e["id"] for e in g["case"]["evidence"] if dc.get(e["id"]) != e["text"]}
    return {e["id"] for e in g["case"]["evidence"]} - set(g["detective_evidence_ids"])


def cites(g, who, ids):
    return any(c["id"] in ids for m in g["messages"] if m["speaker"] == who for c in m["citations"])


def first_citer(g, ids):
    return next((m["speaker"] for m in g["messages"] for c in m["citations"] if c["id"] in ids),
                None)


def main():
    main_run = {g["game_id"]: g for g in load("results/main/games.jsonl")}
    wrong = load("results/wrongdet/games.jsonl")
    for mode in ("frame", "misled"):
        gs = [g for g in wrong if g["detective_mode"] == mode]
        pairs = [(g, main_run[g["game_id"].replace(f"-{mode}", "-honest", 1)]) for g in gs]
        d = [right(g) - right(h) for g, h in pairs]
        rng = random.Random(0)
        bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(2000))
        print(f"== {mode}: {len(gs)} games ==")
        print(f"  council right {sum(right(g) for g in gs)}/{len(gs)}; paired honest "
              f"{sum(right(h) for _, h in pairs)}/{len(gs)}; difference {sum(d) / len(d):+.1%} "
              f"95% CI [{bs[50]:+.0%}, {bs[1949]:+.0%}] (bootstrap over cases)")
        for label, fn in [
            ("innocent cites the clue", lambda g, ids: cites(g, "innocent", ids)),
            ("wolf cites the clue", lambda g, ids: cites(g, "wolf", ids)),
            ("detective cites the clue", lambda g, ids: cites(g, "detective", ids)),
            ("detective accused the wolf out loud at least once",
             lambda g, ids: g["answer"] in [m["accused"] for m in g["messages"]
                                            if m["speaker"] == "detective"])]:
            y = [g for g in gs if fn(g, clue_ids(g))]
            n = [g for g in gs if not fn(g, clue_ids(g))]
            print(f"  {label:50} yes: council right {sum(map(right, y))}/{len(y)}   "
                  f"no: {sum(map(right, n))}/{len(n)}")
        print("  first to cite the clue:", dict(Counter(first_citer(g, clue_ids(g)) for g in gs)))
        print("  council majority:", dict(Counter(
            "wolf" if majority(g["judges"]["haiku"]["debate_votes"]) == g["answer"]
            else "decoy" if majority(g["judges"]["haiku"]["debate_votes"]) == g["detective_target"]
            else "no majority" if majority(g["judges"]["haiku"]["debate_votes"]) is None
            else "other suspect" for g in gs)))
        if mode == "misled":
            c = Counter()
            for g in gs:
                for m in g["messages"]:
                    for x in m["citations"]:
                        if x["id"] in clue_ids(g):
                            q = x["quoted"]
                            kind = ("swapped (names wolf)" if g["answer"] in q else
                                    "true (names decoy)" if g["detective_target"] in q else "neither")
                            c[(m["speaker"], kind, x["label"])] += 1
            print("  quotes of the swapped clue (speaker, version, clerk label):")
            for k, v in sorted(c.items()):
                print(f"    {k}: {v}")

    rand2 = load("results/rand2/games.jsonl")
    print(f"\n== rand2: {len(rand2)} games ==")
    for speaks in (True, False):
        gs = [g for g in rand2 if g["wolf_speaks"] == speaks]
        voted_speaker = sum(majority(g["judges"]["haiku"]["debate_votes"]) in g["speaker_order"]
                            for g in gs)
        print(f"  wolf {'speaks' if speaks else 'silent'}: {len(gs)} games, council right "
              f"{sum(map(right, gs))}/{len(gs)}, council majority for a speaker {voted_speaker}, "
              f"decoy speaks in {sum(g['detective_target'] in g['speaker_order'] if g.get('detective_target') else any(c in g['speaker_order'] for c in g['detective_candidates'] if c != g['answer']) for g in gs)}, "
              f"first to cite the clue {dict(Counter(first_citer(g, clue_ids(g)) for g in gs))}")


if __name__ == "__main__":
    main()
