"""Extra it17 checks that analyze.py does not print (no model calls).

  python3 it17_checks.py   # reads results/main, results/wrongdet, results/rand2

- frame/misled vs the paired main-run honest game: council right, paired difference with a 95%
  bootstrap CI over cases
- who cites the decoy's hidden (frame) or swapped (misled) alibi, and council right by that
- which version of the swapped clue each speaker quoted (misled) and the clerk's label
- rand2: who first cites the hidden clue, council right when the wolf is silent
- it19: the same checks for every judge model in judgements.jsonl (Sonnet rejudge), and the
  paired difference Sonnet - Haiku on the same debates
"""

import json
import os
import random
from collections import Counter

from analyze import merge_judgements

JUDGES = ("haiku", "sonnet")


def load(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def load_games(d):
    """Games with their judgements merged in: g["judges"][model] for every judge model."""
    gs = load(f"{d}/games.jsonl")
    merged = merge_judgements(gs, load(f"{d}/judgements.jsonl"))
    for g in gs:
        g["judges"] = {m: j for (gid, m), j in merged.items() if gid == g["game_id"]}
    return gs


def majority(votes):
    c = Counter(v for v in votes if v)
    return c.most_common(1)[0][0] if c and c.most_common(1)[0][1] >= 2 else None


def council(g, judge="haiku"):
    return majority(g["judges"][judge]["debate_votes"])


def right(g, judge="haiku"):
    return council(g, judge) == g["answer"]


def paired_ci(d, seed=0, n=2000):
    """Mean of paired differences (one per case) with a 95% bootstrap CI over cases."""
    rng = random.Random(seed)
    bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d) / len(d):+.1%} 95% CI [{bs[int(n * .025)]:+.0%}, {bs[int(n * .975) - 1]:+.0%}]"


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
    main_run = {g["game_id"]: g for g in load_games("results/main")}
    wrong = load_games("results/wrongdet")
    for mode in ("frame", "misled"):
        gs = [g for g in wrong if g["detective_mode"] == mode]
        pairs = [(g, main_run[g["game_id"].replace(f"-{mode}", "-honest", 1)]) for g in gs]
        for judge in JUDGES:
            if not all(judge in g["judges"] and judge in h["judges"] for g, h in pairs):
                continue
            r = lambda g: right(g, judge)
            d = [r(g) - r(h) for g, h in pairs]
            print(f"== {mode}: {len(gs)} games, judge={judge} ==")
            print(f"  council right {sum(map(r, gs))}/{len(gs)}; paired honest "
                  f"{sum(r(h) for _, h in pairs)}/{len(gs)}; difference {paired_ci(d)} "
                  f"(bootstrap over cases)")
            for label, fn in [
                ("innocent cites the clue", lambda g, ids: cites(g, "innocent", ids)),
                ("wolf cites the clue", lambda g, ids: cites(g, "wolf", ids)),
                ("detective cites the clue", lambda g, ids: cites(g, "detective", ids)),
                ("detective accused the wolf out loud at least once",
                 lambda g, ids: g["answer"] in [m["accused"] for m in g["messages"]
                                                if m["speaker"] == "detective"])]:
                y = [g for g in gs if fn(g, clue_ids(g))]
                n = [g for g in gs if not fn(g, clue_ids(g))]
                print(f"  {label:50} yes: council right {sum(map(r, y))}/{len(y)}   "
                      f"no: {sum(map(r, n))}/{len(n)}")
            print("  council majority:", dict(Counter(
                "wolf" if council(g, judge) == g["answer"]
                else "decoy" if council(g, judge) == g["detective_target"]
                else "no majority" if council(g, judge) is None
                else "other suspect" for g in gs)))
        print("  first to cite the clue:", dict(Counter(first_citer(g, clue_ids(g)) for g in gs)))
        # it21: retest (rejudge.py --retest) of these games and of their paired honest games, to
        # see whether the council result holds when the same debates are voted on again
        for judge in JUDGES:
            f = ("debate_votes", "debate_votes_retest")
            if not all(x["judges"].get(judge, {}).get(k) for g, h in pairs for x in (g, h) for k in f):
                continue
            ok = lambda x, k: majority(x["judges"][judge][k]) == x["answer"]
            print(f"  it21 judge={judge} retest: {mode} council right, original "
                  f"{sum(ok(g, f[0]) for g in gs)}/{len(gs)}, retest {sum(ok(g, f[1]) for g in gs)}"
                  f"/{len(gs)}; paired honest original {sum(ok(h, f[0]) for _, h in pairs)}/"
                  f"{len(gs)}, retest {sum(ok(h, f[1]) for _, h in pairs)}/{len(gs)}")
            for k in f:
                d = [ok(g, k) - ok(h, k) for g, h in pairs]
                print(f"    {mode} - honest, {k}: {paired_ci(d)}")
            print(f"    majority right/wrong changed between runs: {mode} "
                  f"{sum(ok(g, f[0]) != ok(g, f[1]) for g in gs)}/{len(gs)}, honest "
                  f"{sum(ok(h, f[0]) != ok(h, f[1]) for _, h in pairs)}/{len(gs)}")
            print(f"    {mode} retest council majority:", dict(Counter(
                "wolf" if majority(g["judges"][judge][f[1]]) == g["answer"]
                else "decoy" if majority(g["judges"][judge][f[1]]) == g["detective_target"]
                else "no majority" if majority(g["judges"][judge][f[1]]) is None
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
            # it19 check: is "two speakers (innocent + wolf) quote the true clue against the
            # detective's one" enough to explain the council? Split by whether the wolf quoted it.
            def wolf_true(g):
                return any(x["id"] in clue_ids(g) and g["detective_target"] in x["quoted"]
                           for m in g["messages"] if m["speaker"] == "wolf" for x in m["citations"])
            print("  council right by whether the wolf quoted the TRUE clue (innocent always did):")
            for judge in JUDGES:
                if all(judge in g["judges"] for g in gs):
                    y = [g for g in gs if wolf_true(g)]
                    n = [g for g in gs if not wolf_true(g)]
                    print(f"    judge={judge}: wolf quoted it {sum(right(g, judge) for g in y)}/"
                          f"{len(y)}   wolf did not {sum(right(g, judge) for g in n)}/{len(n)}"
                          f" ({', '.join(g['game_id'] for g in n)})")
            # it20: same debates re-marked by the name-aware clerk (rejudge.py --clerk2), and a
            # retest on the original marks (--retest) to see how much the majority moves anyway
            for judge in JUDGES:
                f = ("debate_votes", "debate_votes_retest", "debate_votes_clerk2")
                if not all(g["judges"].get(judge, {}).get(k) for g in gs for k in f):
                    continue
                ok = {k: [majority(g["judges"][judge][k]) == g["answer"] for g in gs] for k in f}
                print(f"  it20 judge={judge}: council right, original marks {sum(ok[f[0]])}/{len(gs)}"
                      f"; retest, original marks {sum(ok[f[1]])}/{len(gs)}; name-aware clerk "
                      f"{sum(ok[f[2]])}/{len(gs)}")
                for a, b in ((2, 1), (2, 0), (1, 0)):
                    d = [x - y for x, y in zip(ok[f[a]], ok[f[b]])]
                    print(f"    {f[a]} - {f[b]}: {paired_ci(d)}")
                print("    name-aware clerk council majority:", dict(Counter(
                    "wolf" if majority(g["judges"][judge][f[2]]) == g["answer"]
                    else "decoy" if majority(g["judges"][judge][f[2]]) == g["detective_target"]
                    else "no majority" if majority(g["judges"][judge][f[2]]) is None
                    else "other suspect" for g in gs)))

    print("\n== it19: Sonnet - Haiku on the same debates (council right; floor; ceiling) ==")
    by_mode = {}
    for g in list(main_run.values()) + wrong:
        if all(j in g["judges"] for j in JUDGES):
            by_mode.setdefault(g["detective_mode"], []).append(g)
    for mode, gs in by_mode.items():
        def acc(g, judge, field):
            return majority(g["judges"][judge][field]) == g["answer"]
        parts = []
        for field, name in (("debate_votes", "council"), ("file_partial_votes", "floor"),
                            ("file_alone_votes", "ceiling")):
            h = sum(acc(g, "haiku", field) for g in gs)
            s_ = sum(acc(g, "sonnet", field) for g in gs)
            parts.append(f"{name} haiku {h}/{len(gs)} sonnet {s_}/{len(gs)}")
        # one difference per case: average over the case's games in this mode (1 game per case
        # per mode here, so it is the game's difference)
        d = [right(g, "sonnet") - right(g, "haiku") for g in gs]
        print(f"  {mode:7} {len(gs):2} games: " + "; ".join(parts) +
              f"; council sonnet - haiku {paired_ci(d)}")
        unan = Counter(len(set(g["judges"]["sonnet"]["debate_votes"])) == 1 for g in gs)
        print(f"          sonnet council unanimous in {unan[True]}/{len(gs)} games")

    # it22: framing detective + innocent reads the detective's copy, so no honest speaker knows
    # the hidden clue. Paired with the frame game (wrongdet) and the honest innocopy game.
    # it23: the same with a "quiet" wolf (never brings up evidence that clears others), also
    # paired with it22.
    frame = {g["game_id"]: g for g in wrong if g["detective_mode"] == "frame"}
    inno = {g["game_id"]: g for g in load_games("results/innocopy")}
    hard_by_id = {g["game_id"]: g for g in load_games("results/hardest")}
    base = lambda gid: gid.replace("-quietwolf", "")
    for label, gs, partners in [
            ("it22 hardest (frame + innocopy)", list(hard_by_id.values()), [
                ("frame (innocent has full file)", frame, lambda i: i.replace("-innocopy", "")),
                ("honest innocopy", inno, lambda i: i.replace("-frame", "-honest", 1))]),
            ("it23 quiet wolf (frame + innocopy + quiet wolf)", load_games("results/quietwolf"), [
                ("it22 (wolf not told to stay quiet)", hard_by_id, base),
                ("frame (innocent has full file)", frame,
                 lambda i: base(i).replace("-innocopy", "")),
                ("honest innocopy", inno, lambda i: base(i).replace("-frame", "-honest", 1))])]:
        if not gs:
            continue
        print(f"\n== {label}: {len(gs)} games ==")
        side = lambda g, v: ("wolf" if v == g["answer"] else "decoy" if v == g["detective_target"]
                             else "no majority" if v is None else "other suspect")
        for judge in JUDGES:
            if not all(judge in g["judges"] for g in gs):
                continue
            acc = lambda g, k: majority(g["judges"][judge][k]) == g["answer"]
            c = [acc(g, "debate_votes") for g in gs]
            fl = [acc(g, "file_partial_votes") for g in gs]
            ce = [acc(g, "file_alone_votes") for g in gs]
            print(f"  judge={judge}: council {sum(c)}/{len(gs)}, floor {sum(fl)}/{len(gs)}, "
                  f"ceiling {sum(ce)}/{len(gs)}")
            print(f"    council - floor: {paired_ci([a - b for a, b in zip(c, fl)])}")
            for name, other, key in partners:
                pairs = [(g, other.get(key(g["game_id"]))) for g in gs]
                if all(h and judge in h["judges"] for _, h in pairs):
                    d = [right(g, judge) - right(h, judge) for g, h in pairs]
                    print(f"    {label.split()[0]} - {name}: {sum(right(h, judge) for _, h in pairs)}/"
                          f"{len(pairs)} paired; difference {paired_ci(d)}")
            print("    council majority:", dict(Counter(side(g, council(g, judge)) for g in gs)))
            print("    floor majority:  ", dict(Counter(
                side(g, majority(g["judges"][judge]["file_partial_votes"])) for g in gs)))
        print("  first to cite the hidden clue:",
              dict(Counter(first_citer(g, clue_ids(g)) for g in gs)))
        for who in ("detective", "wolf", "innocent"):
            print(f"  {who} cites the hidden clue in "
                  f"{sum(cites(g, who, clue_ids(g)) for g in gs)}/{len(gs)} games")
        print(f"  detective private final = wolf: "
              f"{sum(g['detective_final']['suspect'] == g['answer'] for g in gs)}/{len(gs)}; "
              f"accused the wolf out loud at least once: "
              f"{sum(g['answer'] in [m['accused'] for m in g['messages'] if m['speaker'] == 'detective'] for g in gs)}"
              f"/{len(gs)}; decoy is the innocent speaker: "
              f"{sum(g['innocent_speaker'] == g['detective_target'] for g in gs)}/{len(gs)}")
        print("  misquoted / not in file citations, by speaker:", dict(Counter(
            (m["speaker"], x["label"]) for g in gs for m in g["messages"] for x in m["citations"]
            if x["label"] != "valid")))

    rand2 = load_games("results/rand2")
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
