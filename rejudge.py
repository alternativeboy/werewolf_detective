"""Judge saved debates again with other judge models. The debate itself is NOT rerun.

The transcript does not depend on who judges it, so adding a judge model costs only the
judge calls (votes + 1 file-alone vote per game), not a whole new game.

Examples:
  python rejudge.py --backend cli --judges sonnet opus
  python rejudge.py --backend cli --judges opus --votes 1 --limit 100   # cheaper sanity check

Results go to <games dir>/judgements.jsonl (one line per game x judge). analyze.py reads it.
Reruns skip pairs that are already done.
"""

import argparse
import json
import os

from backends import make_backend
from game import N_JUDGE_VOTES, judge_game


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["mock", "cli", "api"], default="mock")
    ap.add_argument("--games", default="results/games.jsonl")
    ap.add_argument("--judges", nargs="+", required=True,
                    help="judge models, e.g. haiku sonnet opus")
    ap.add_argument("--votes", type=int, default=N_JUDGE_VOTES)
    ap.add_argument("--limit", type=int, default=None, help="only the first N games")
    a = ap.parse_args()

    out = os.path.join(os.path.dirname(a.games) or ".", "judgements.jsonl")
    games = [g for g in load_jsonl(a.games) if "transcript_marked" in g][:a.limit]
    done = {(j["game_id"], j["judge_model"]) for j in load_jsonl(out)}
    done |= {(g["game_id"], m) for g in games for m in g.get("judges", {})}
    backend = make_backend(a.backend)

    for g in games:
        for m in a.judges:
            if (g["game_id"], m) in done:
                continue
            j = judge_game(g, backend, model=m, n_votes=a.votes)
            print(f"{g['game_id']} judge={m}: debate {j['debate_votes']}, "
                  f"alone {j['file_alone_vote']}, answer {g['answer']}")
            with open(out, "a", encoding="utf-8") as f:
                f.write(json.dumps({"game_id": g["game_id"], **j}, ensure_ascii=False) + "\n")
    print(f"\nSaved to {out}. Next: python analyze.py {a.games}")


if __name__ == "__main__":
    main()
