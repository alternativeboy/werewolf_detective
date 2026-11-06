"""Cheap difficulty calibration before the main run: no debate, 2 model calls per case.

For each level, on fresh cases: the detective's initial guess and a judge reading the case
file alone. Pick the main-run levels where both are clearly between chance and 100%.

  python pilot.py --backend cli --levels L1 L2 L3 L4 --per-level 10

Pilot cases use a different seed from the main run, so the difficulty is not tuned on the
same cases that are later reported.
"""

import argparse
import json
import os
import random

import prompts as P
from backends import make_backend
from cases import LEVELS, make_valid_case, render_case
from checker import match_name, parse_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["mock", "cli", "api"], default="mock")
    ap.add_argument("--levels", nargs="+", default=["L1", "L2", "L3", "L4"], choices=LEVELS)
    ap.add_argument("--per-level", type=int, default=10)
    ap.add_argument("--judge-model", default=None, help="default: the backend's judge model")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--out", default="results/pilot.jsonl")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    done = {}
    if os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    r = json.loads(l)
                    done[r["key"]] = r
    backend = make_backend(a.backend)
    judge = a.judge_model or backend.models["judge"]
    rng = random.Random(a.seed)
    rows = []

    for lv in a.levels:
        for i in range(a.per_level):
            case = make_valid_case(f"p{lv}-{i:03d}", lv, rng)
            key = f"{a.seed}-{case['case_id']}-{judge}"
            if key in done:
                rows.append(done[key])
                continue
            text, sus = render_case(case), case["suspects"]
            det = match_name(parse_json(backend.call(
                "detective", P.DETECTIVE_SYSTEM["honest"], P.detective_initial(text))).get("suspect"), sus)
            jv = match_name(parse_json(backend.call(
                "judge", P.JUDGE_FILE_SYSTEM, P.judge_file_vote(text), model=judge)).get("vote"), sus)
            r = {"key": key, "level": lv, "judge_model": judge, "answer": case["answer"],
                 "n_suspects": len(sus), "detective": det, "judge": jv}
            rows.append(r)
            with open(a.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"{case['case_id']}: detective {det}, judge {jv}, answer {case['answer']}")

    print(f"\n{'level':<6}{'n':>4}{'chance':>9}{'detective':>12}{'judge (' + judge + ')':>18}")
    for lv in a.levels:
        rs = [r for r in rows if r["level"] == lv]
        acc = lambda k: sum(r[k] == r["answer"] for r in rs) / len(rs)
        print(f"{lv:<6}{len(rs):>4}{1 / rs[0]['n_suspects']:>9.0%}{acc('detective'):>12.0%}"
              f"{acc('judge'):>18.0%}")
    print("\nWith n=10 per level, each rate is +/- ~30 points. Use it to rule levels in or out, "
          "not as a result.")


if __name__ == "__main__":
    main()
