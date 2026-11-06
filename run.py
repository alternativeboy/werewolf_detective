"""Run the experiment. Finished games are saved one per line, so a rerun picks up where it stopped.

Examples:
  python run.py --backend mock --cases 4 --out test             # free test of the pipeline
  python run.py --backend cli  --cases 1 --modes honest         # 1 real game on your Claude plan
  python run.py --backend cli  --cases 5 --levels L1 L3         # 10 games (5 cases x 2 modes)
  python run.py --backend api  --cases 100 --levels L1 L3       # full run on API credits

Pick --levels after running pilot.py. Every case is checked by cases.solve() to have exactly
one possible answer, so there is no separate validation step.
"""

import argparse
import json
import os

from backends import make_backend
from cases import LEVELS, generate
from game import N_JUDGE_VOTES, play_game


def load_done(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {json.loads(l)["game_id"] for l in f if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["mock", "cli", "api"], default="mock")
    ap.add_argument("--cases", type=int, default=1, help="number of case files")
    ap.add_argument("--levels", nargs="+", default=["L1", "L3"], choices=LEVELS,
                    help="difficulty levels, assigned to cases in turn")
    ap.add_argument("--modes", nargs="+", default=["honest", "win"])
    ap.add_argument("--votes", type=int, default=N_JUDGE_VOTES, help="council votes per game")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    cases_path, games_path = f"{a.out}/cases.jsonl", f"{a.out}/games.jsonl"
    cases = generate(a.cases, a.seed, cases_path, levels=a.levels)
    backend = make_backend(a.backend)
    done = load_done(games_path)

    for case in cases:
        for mode in a.modes:
            gid = f"{case['case_id']}-{mode}"
            if gid in done:
                continue
            print(f"{gid} ({case['difficulty']})")
            rec = play_game(case, backend, mode, gid, n_votes=a.votes)
            with open(games_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\nSaved to {games_path}.\nNext: python rejudge.py --games {games_path} --judges ...  "
          f"(optional), then python analyze.py {games_path}")


if __name__ == "__main__":
    main()
