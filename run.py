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
  python run.py --backend cli  --cases 15 --levels L2 L4 --detective-hides 1 --seed 0 \
      --modes honest --speakers random2 --out results/rand2
      # it17 (exploratory): any two random suspects speak, so the wolf is usually silent
  python run.py --backend cli  --cases 15 --levels L2 L4 --detective-hides 1 --seed 0 \
      --modes frame misled --out results/wrongdet
      # it17 (exploratory): detective secretly pushes the decoy / honestly reads a file that
      # points to the decoy; paired with the main-run honest games (same speakers and order)
  python run.py --backend cli  --cases 15 --levels L2 L4 --detective-hides 1 --seed 0 \
      --modes frame --innocent-sees copy --wolf-prompt quiet --out results/quietwolf
      # it23 (exploratory): framing detective, innocent reads the copy, wolf never brings up
      # evidence that clears others; paired with results/hardest (it22)
  --wolf-model opus   gives the wolf a different model (not used in any planned run)
  --max-games 70      stop after 70 new games; the same command again plays the next 70

Pick --levels after running pilot.py. Every case is checked by cases.solve() to have exactly
one possible answer, so there is no separate validation step.
"""

import argparse
import json
import os
import time

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
    ap.add_argument("--modes", nargs="+", default=["honest", "win"],
                    choices=["honest", "win", "frame", "misled"],
                    help="frame/misled (it17, exploratory, need --detective-hides 1): detective "
                         "secretly pushes the decoy / honestly reads a file that points to it")
    ap.add_argument("--speakers", choices=["wolf+innocent", "random2"], default="wolf+innocent",
                    help="random2 = any two random suspects speak, so the wolf is usually silent "
                         "(it17, exploratory)")
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
    ap.add_argument("--wolf-prompt", choices=["default", "quiet"], default="default",
                    help="quiet = the wolf is told never to bring up evidence that clears another "
                         "suspect (it23, exploratory); game id suffix -quietwolf")
    ap.add_argument("--max-games", type=int, default=None,
                    help="play at most this many new games, then stop (rerun the same command "
                         "for the next batch, e.g. to stay inside a plan usage window)")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    cases_path, games_path = f"{a.out}/cases.jsonl", f"{a.out}/games.jsonl"
    cases = generate(a.cases, a.seed, cases_path, levels=a.levels)
    backend = make_backend(a.backend)
    done = load_done(games_path)
    # Only a non-default wolf changes the game id, so default-wolf ids stay as before
    wolf = a.wolf_model if a.wolf_model and a.wolf_model != backend.models["wolf"] else None

    # Games in a fixed order (case, then mode), so batches with --max-games always continue
    # with the next unplayed game and the finished set never depends on how it was split.
    todo = []
    for case in cases:
        for mode in a.modes:
            base = f"{case['case_id']}-{mode}" + (f"-sees{a.detective_sees:g}"
                                                    if a.detective_sees < 1 else "") + (
                f"-hide{a.detective_hides}" if a.detective_hides > 0 else "")
            gid = base + (f"-wolf{wolf}" if wolf else "") + (
                "-innocopy" if a.innocent_sees == "copy" else "") + (
                "-quietwolf" if a.wolf_prompt == "quiet" else "") + (
                "-rand2" if a.speakers == "random2" else "")
            if gid not in done:
                todo.append((case, mode, base, gid))
    total = len(cases) * len(a.modes)
    batch = todo[:a.max_games] if a.max_games is not None else todo
    print(f"{total - len(todo)}/{total} games already done; playing {len(batch)} now.")

    for k, (case, mode, base, gid) in enumerate(batch, 1):
        print(f"[{k}/{len(batch)}] {gid} ({case['difficulty']})")
        t0 = time.time()
        # draw_seed=base: the innocent speaker and speaking order are drawn from the id
        # WITHOUT the condition suffixes, so e.g. c0003-honest-hide1 and
        # c0003-honest-hide1-innocopy have the same innocent speaker and order (paired).
        # frame/misled games draw speakers like the HONEST game of the same case, so each pairs
        # with a main-run honest game (same innocent speaker and order)
        seed = base.replace(f"-{mode}", "-honest", 1) if mode in ("frame", "misled") else base
        rec = play_game(case, backend, mode, gid, n_votes=a.votes,
                        detective_sees=a.detective_sees, detective_hides=a.detective_hides,
                        wolf_model=wolf, draw_seed=seed, innocent_sees=a.innocent_sees,
                        speakers_mode=a.speakers, wolf_prompt=a.wolf_prompt)
        rec["seconds"] = round(time.time() - t0)
        with open(games_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  ({rec['seconds']} s)")

    left = len(todo) - len(batch)
    print(f"\n{total - left}/{total} games done, {left} left."
          + (" Run the same command again for the next batch." if left else ""))
    print(f"Saved to {games_path}.\nNext: python rejudge.py --games {games_path} --judges ...  "
          f"(optional), then python analyze.py {games_path}")


if __name__ == "__main__":
    main()
