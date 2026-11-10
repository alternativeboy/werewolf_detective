"""Run the experiment. Finished games are saved one per line, so a rerun picks up where it stopped.

Examples:
  python run.py --backend mock --cases 4 --out test             # free test of the pipeline
  python run.py --backend cli  --cases 1 --modes honest         # 1 real game on your Claude plan
  python run.py --backend cli  --cases 5 --levels L1 L3         # 10 games (5 cases x 2 modes)
  python run.py --backend api  --cases 100 --levels L1 L3       # full run on API credits
  python run.py --backend cli  --cases 15 --levels L2 L4 --detective-hides 1 --seed 0 \
      --modes honest --innocent-sees copy --out results/innocopy
      # it16 (exploratory): innocent reads the detective's copy. Same seed = same first 15 cases
      # as the main run; innocent speaker and order match the main-run games (paired)
  --wolf-model opus   gives the wolf a different model (not used in any planned run)

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
    ap.add_argument("--detective-sees", type=float, default=1.0,
                    help="fraction of evidence in the detective's copy of the case file (0-1]")
    ap.add_argument("--detective-hides", type=int, default=0,
                    help="hide this many solution clues from the detective (1 = one alibi of a "
                         "suspect in the wolf's row, leaving 2 possible suspects)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--wolf-model", default=None,
                    help="model for the wolf only, e.g. opus (it16); default: the backend's")
    ap.add_argument("--innocent-sees", choices=["full", "copy"], default="full",
                    help="copy = the innocent speaker reads the detective's incomplete copy "
                         "instead of the full file (it16, exploratory; needs --detective-hides)")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    cases_path, games_path = f"{a.out}/cases.jsonl", f"{a.out}/games.jsonl"
    cases = generate(a.cases, a.seed, cases_path, levels=a.levels)
    backend = make_backend(a.backend)
    done = load_done(games_path)
    # Only a non-default wolf changes the game id, so default-wolf ids stay as before
    wolf = a.wolf_model if a.wolf_model and a.wolf_model != backend.models["wolf"] else None

    for case in cases:
        for mode in a.modes:
            base = f"{case['case_id']}-{mode}" + (f"-sees{a.detective_sees:g}"
                                                    if a.detective_sees < 1 else "") + (
                f"-hide{a.detective_hides}" if a.detective_hides > 0 else "")
            gid = base + (f"-wolf{wolf}" if wolf else "") + (
                "-innocopy" if a.innocent_sees == "copy" else "")
            if gid in done:
                continue
            print(f"{gid} ({case['difficulty']})")
            # draw_seed=base: the innocent speaker and speaking order are drawn from the id
            # WITHOUT the condition suffixes, so e.g. c0003-honest-hide1 and
            # c0003-honest-hide1-innocopy have the same innocent speaker and order (paired).
            rec = play_game(case, backend, mode, gid, n_votes=a.votes,
                            detective_sees=a.detective_sees, detective_hides=a.detective_hides,
                            wolf_model=wolf, draw_seed=base, innocent_sees=a.innocent_sees)
            with open(games_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\nSaved to {games_path}.\nNext: python rejudge.py --games {games_path} --judges ...  "
          f"(optional), then python analyze.py {games_path}")


if __name__ == "__main__":
    main()
