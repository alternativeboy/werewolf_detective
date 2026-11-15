"""Judge saved debates again with other judge models. The debate itself is NOT rerun.

The transcript does not depend on who judges it, so adding a judge model costs only the
judge calls (3 x votes per game: debate, full file = ceiling, detective's copy = floor), not a
whole new game.

Examples:
  python rejudge.py --backend cli --judges sonnet opus
  python rejudge.py --backend cli --judges opus --votes 1 --limit 100   # cheaper sanity check

Results go to <games dir>/judgements.jsonl (one line per game x judge). analyze.py reads it.
Reruns skip pairs that are already done.

--file-votes-only tops up the H3 floor and ceiling (judge reading a case file alone, no debate)
to --votes votes each, for judge models that already voted on the debate. Use it on games
judged before it11, which have one floor/ceiling vote instead of three:
  python rejudge.py --backend cli --games results/smoke_hide1/games.jsonl --judges haiku --file-votes-only

--no-marks (ablation, it14) adds --votes council votes on the same debate with the clerk's
(verified)/(MISQUOTED)/(NOT IN CASE FILE) marks removed, to see how much the council relies on
them. The debate is not rerun, so the speakers behave exactly as in the marked condition:
  python rejudge.py --backend cli --games results/smoke_hide1/games.jsonl --judges haiku --no-marks

--clerk2 (it20) adds --votes council votes on the same debate re-marked by the name-aware clerk
(checker.CLERK2_VERSION: a quote that names a suspect the real evidence line does not name is
MISQUOTED). --retest adds --votes council votes on the ORIGINAL marked debate, to measure how
much the majority moves between runs. Both can be given together; --mode keeps only games of
one detective mode:
  python rejudge.py --backend cli --games results/wrongdet/games.jsonl --judges haiku \\
      --mode misled --clerk2 --retest
"""

import argparse
import json
import os

from analyze import file_votes_of, merge_judgements
from backends import make_backend
from checker import CLERK2_VERSION
from game import (N_JUDGE_VOTES, debate_votes, file_votes, judge_game, marked_transcript,
                  nomarks_votes)
from prompts import NOMARKS_VERSION, PROMPT_VERSION


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def append(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def top_up(g, j, backend, model, n):
    """Return {field: full vote list} for the floor/ceiling lists that have fewer than n votes."""
    out = {}
    for kind, partial in (("file_alone", False), ("file_partial", True)):
        if partial and g.get("detective_evidence_ids") is None:
            continue  # detective saw the full file: no floor to measure
        have = file_votes_of(j, kind) or []
        if len(have) < n:
            extra = file_votes(g, backend, model, n - len(have), partial=partial)
            out[kind + "_votes"] = have + extra
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["mock", "cli", "api"], default="mock")
    ap.add_argument("--games", default="results/games.jsonl")
    ap.add_argument("--judges", nargs="+", required=True,
                    help="judge models, e.g. haiku sonnet opus")
    ap.add_argument("--votes", type=int, default=N_JUDGE_VOTES)
    ap.add_argument("--limit", type=int, default=None, help="only the first N games")
    ap.add_argument("--file-votes-only", action="store_true",
                    help="only top up floor and ceiling votes to --votes each (no debate votes)")
    ap.add_argument("--no-marks", action="store_true",
                    help="ablation: council votes on the debate with the clerk's marks removed")
    ap.add_argument("--clerk2", action="store_true",
                    help="it20: council votes on the debate re-marked by the name-aware clerk")
    ap.add_argument("--retest", action="store_true",
                    help="it20: council votes again on the original marked debate")
    ap.add_argument("--mode", default=None, help="only games with this detective_mode")
    a = ap.parse_args()

    out = os.path.join(os.path.dirname(a.games) or ".", "judgements.jsonl")
    games = [g for g in load_jsonl(a.games) if "transcript_marked" in g
             and (a.mode is None or g.get("detective_mode") == a.mode)][:a.limit]
    backend = make_backend(a.backend)
    merged = merge_judgements(games, load_jsonl(out))

    if a.clerk2 or a.retest:
        for g in games:
            # the rebuild must reproduce what the council saw, or the comparison is not paired
            assert marked_transcript(g) == g["transcript_marked"], g["game_id"]
            for m in a.judges:
                j = merged.get((g["game_id"], m), {})
                row = {}
                if a.retest and j.get("debate_votes_retest") is None:
                    row["debate_votes_retest"] = debate_votes(g, backend, m, a.votes)
                if a.clerk2 and j.get("debate_votes_clerk2") is None:
                    row["debate_votes_clerk2"] = debate_votes(
                        g, backend, m, a.votes, transcript=marked_transcript(g, names=True))
                    row["clerk2_version"] = CLERK2_VERSION
                if not row:
                    continue
                print(f"{g['game_id']} judge={m}: original {j.get('debate_votes')}, retest "
                      f"{row.get('debate_votes_retest')}, clerk2 {row.get('debate_votes_clerk2')}, "
                      f"answer {g['answer']}")
                append(out, {"game_id": g["game_id"], "judge_model": m,
                             "prompt_version": PROMPT_VERSION, **row})
        print(f"\nSaved to {out}. Next: python it17_checks.py")
        return

    if a.no_marks:
        for g in games:
            for m in a.judges:
                j = merged.get((g["game_id"], m), {})
                if j.get("debate_votes_nomarks") is not None:
                    continue
                v = nomarks_votes(g, backend, m, a.votes)
                print(f"{g['game_id']} judge={m}: no marks {v}, "
                      f"with marks {j.get('debate_votes')}, answer {g['answer']}")
                append(out, {"game_id": g["game_id"], "judge_model": m,
                             "prompt_version": PROMPT_VERSION, "nomarks_version": NOMARKS_VERSION,
                             "debate_votes_nomarks": v})
        print(f"\nSaved to {out}. Next: python analyze.py {a.games}")
        return

    if a.file_votes_only:
        for g in games:
            for m in a.judges:
                j = merged.get((g["game_id"], m))
                if j is None or "debate_votes" not in j:
                    print(f"{g['game_id']} judge={m}: no debate votes yet, run without --file-votes-only")
                    continue
                new = top_up(g, j, backend, m, a.votes)
                if not new:
                    continue
                print(f"{g['game_id']} judge={m}: ceiling {new.get('file_alone_votes', '(full)')}, "
                      f"floor {new.get('file_partial_votes', '(full)')}, answer {g['answer']}")
                append(out, {"game_id": g["game_id"], "judge_model": m,
                             "prompt_version": PROMPT_VERSION, **new})
        print(f"\nSaved to {out}. Next: python analyze.py {a.games}")
        return

    done = {k for k, j in merged.items() if "debate_votes" in j}
    for g in games:
        for m in a.judges:
            if (g["game_id"], m) in done:
                continue
            j = judge_game(g, backend, model=m, n_votes=a.votes)
            print(f"{g['game_id']} judge={m}: debate {j['debate_votes']}, "
                  f"ceiling {j['file_alone_votes']}, floor {j['file_partial_votes']}, "
                  f"answer {g['answer']}")
            append(out, {"game_id": g["game_id"], **j})
    print(f"\nSaved to {out}. Next: python analyze.py {a.games}")


if __name__ == "__main__":
    main()
