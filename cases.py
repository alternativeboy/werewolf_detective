"""Case file generator with difficulty levels and a code solver.

Every clue is TRUE, and every clue carries a machine-readable `fact`. `solve()` uses only
those facts to check that exactly one suspect can be the murderer; a case that fails the
check is regenerated. So no case is ambiguous, however hard it is for a model to read.

The rule (also stated in every case file, so a careful reader can apply it):
  1. The werewolf went straight home, so it lives in the row the trail leads to.
  2. A confirmed alibi is reliable, so anyone confirmed elsewhere AT THE TIME OF DEATH is cleared.
Exactly one suspect is left.

Levels (players never see the level):
  L0  4 suspects; a direct clue describes the werewolf the next morning   (old "easy")
  L1  4 suspects; trail + residence + one alibi                             (old "hard")
  L2  6 suspects; 3 share the werewolf's row; irrelevant true facts added
  L3  L2 + the werewolf has a confirmed alibi that ends before the death (time arithmetic)
  L4  L3 + the trail is indirect (trace -> path -> row), an innocent has motive AND no
      alibi, and a cleared row-mate was seen with muddy boots
"""

import json
import random

LEVELS = ["L0", "L1", "L2", "L3", "L4"]
N_SUSPECTS = {"L0": 4, "L1": 4, "L2": 6, "L3": 6, "L4": 6}

NAMES = ["Anan", "Bua", "Chai", "Dao", "Ek", "Fon", "Gade", "Kanya", "Lek", "Mali",
         "Nok", "Ploy", "Rin", "Somchai", "Tawan", "Wan"]
VICTIMS = ["the miller", "the old herbalist", "the night watchman", "the baker"]
SCENES = ["the well", "the mill", "the chapel", "the river bridge"]
PLACES = ["the tavern", "the forge", "the market hall", "the shrine", "the bathhouse",
          "the granary", "the weaver's hall"]
AREAS = ["east", "west", "north", "south"]
# (trace left at the scene, how a person carrying it looks the next morning)
TRACES = [("red clay", "boots caked with red clay"),
          ("white chalk dust", "boots dusted with white chalk"),
          ("black river mud", "boots covered in black river mud")]
PATHS = ["the old mill path", "the orchard lane", "the hill track", "the reed path"]
WITNESSES = ["the innkeeper confirms it", "three neighbours confirm it",
             "the blacksmith confirms it", "the priest confirms it"]
NOISE = ["The rope of the well was replaced last spring.",
         "It rained lightly the evening before the murder.",
         "The chapel bell rang at 9 pm, as it does every night.",
         "{a} sells bread at the market on weekdays.",
         "{a} and {b} are cousins.",
         "{a} owns two goats and a lame mule.",
         "{victim_cap} had planned to visit the city next week."]


def fmt(h: int) -> str:
    """Hour on a 0-47 clock (24 = midnight, 25 = 1 am) -> '1 am'."""
    h %= 24
    if h == 0:
        return "midnight"
    if h == 12:
        return "noon"
    return f"{h % 12 or 12} {'am' if h < 12 else 'pm'}"


def join(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def make_case(case_id: str, level: str, rng: random.Random) -> dict:
    n = N_SUSPECTS[level]
    names = rng.sample(NAMES, n)
    wolf = names[0]
    row_mates = names[1:2] if n == 4 else names[1:3]  # cleared by alibis
    others = names[1 + len(row_mates):]                # live in another row
    area, other_area = rng.sample(AREAS, 2)
    victim, scene = rng.choice(VICTIMS), rng.choice(SCENES)
    death = rng.choice([23, 24, 25])
    places = rng.sample(PLACES, len(PLACES))
    trace, look = rng.choice(TRACES)
    clues = []

    def add(role, text, **fact):
        clues.append({"role": role, "text": text, "fact": fact})

    def covering_alibi(who, role="alibi"):
        s, e = death - rng.choice([2, 3]), death + rng.choice([2, 3])
        add(role, f"{who} was at {places.pop()} from {fmt(s)} until {fmt(e)}; "
                  f"{rng.choice(WITNESSES)}.", type="alibi", name=who, start=s, end=e, confirmed=True)

    add("scene", f"{victim.capitalize()} was found dead at {scene}. "
                 f"The healer says death happened around {fmt(death)}.", type="death", hour=death)

    # Trail -> row of houses
    if level == "L4":
        path = rng.choice(PATHS)
        add("trace", f"Investigators found {trace} at {scene}.", type="trace_found", trace=trace)
        add("trace", f"In this village, {trace} is found only along {path}.",
            type="trace_path", trace=trace, path=path)
        add("trace", f"{path[0].upper() + path[1:]} runs past only one row of houses: "
                     f"the {area} row.", type="path_area", path=path, area=area)
    else:
        add("trace", f"Investigators found {trace} at {scene}, and a trail leading toward "
                     f"the {area} row of houses.", type="trail", area=area)

    row = [wolf] + row_mates
    rng.shuffle(row)
    add("residence", f"Only {join(row)} live in the {area} row of houses.",
        type="residence", area=area, names=row)
    add("residence", f"{join(others)} live in the {other_area} row.",
        type="residence", area=other_area, names=others)

    # Row-mates are cleared by confirmed alibis that cover the death.
    for m in row_mates:
        covering_alibi(m)

    # The werewolf
    if level == "L0":
        add("direct", f"The next morning, {wolf} was seen with {look}.", type="direct", name=wolf)
    elif level in ("L1", "L2"):
        add("herring", f"{wolf} was seen at {places.pop()} at {fmt(death - 3)}, laughing with "
                       f"friends.", type="sighting", name=wolf, hour=death - 3)
    else:  # L3, L4: a confirmed alibi that ends two or more hours before the death
        s, e = death - 5, death - 2
        add("herring", f"{wolf} was at {places.pop()} from {fmt(s)} until {fmt(e)}; "
                       f"{rng.choice(WITNESSES)}.", type="alibi", name=wolf, start=s, end=e,
            confirmed=True)

    # People in the other row: not suspects by rule 1, but they give the wolf material.
    covering_alibi(others[0], role="herring" if level != "L0" else "alibi")
    rest = others[1:]
    if level != "L0":
        for o in rest[:1]:
            add("herring", f"Nobody can say where {o} was after {fmt(death - 2)}.",
                type="no_alibi", name=o)
        for o in rest[1:]:
            add("herring", f"{o} says they were home asleep all night; nobody can confirm it.",
                type="alibi", name=o, start=death - 6, end=death + 6, confirmed=False)
        motive = rest[0] if level == "L4" else rng.choice(others)
        add("herring", f"{motive} had argued loudly with {victim} that afternoon.",
            type="motive", name=motive)
        mate = rng.choice(row_mates)
        add("herring", f"{mate}'s lantern was found near {scene} the next morning; {mate} says "
                       f"it was lent out days ago.", type="object", name=mate)
    else:
        add("herring", f"{others[-1]} had argued loudly with {victim} that afternoon.",
            type="motive", name=others[-1])
    if level == "L4":
        mate = rng.choice(row_mates)
        add("herring", f"The next morning, {mate} was seen with muddy boots.",
            type="sighting", name=mate, hour=death + 8)

    if level in ("L2", "L3", "L4"):
        for t in rng.sample(NOISE, 3):
            a, b = rng.sample(names, 2)
            add("noise", t.format(a=a, b=b, victim_cap=victim.capitalize()), type="noise")

    rng.shuffle(clues)
    evidence = [{"id": f"E{i + 1}", **c} for i, c in enumerate(clues)]
    return {
        "case_id": case_id,
        "difficulty": level,
        "suspects": sorted(names),
        "answer": wolf,
        "summary": f"Last night {victim} was murdered at {scene}. One of the villagers listed "
                   f"below is a werewolf who did it.",
        "rules": [{"id": "R1", "text": "After the murder, the werewolf went straight home."},
                  {"id": "R2", "text": "Confirmed alibis are reliable."}],
        "evidence": evidence,
    }


def solve(case: dict) -> list:
    """Apply the two rules to the clue facts. Returns every suspect who could be the werewolf."""
    facts = [e["fact"] for e in case["evidence"]]
    of = lambda t: [f for f in facts if f.get("type") == t]
    death = of("death")[0]["hour"]
    if of("trail"):
        area = of("trail")[0]["area"]
    else:
        trace = of("trace_found")[0]["trace"]
        path = next(f["path"] for f in of("trace_path") if f["trace"] == trace)
        area = next(f["area"] for f in of("path_area") if f["path"] == path)
    residents = next(f["names"] for f in of("residence") if f["area"] == area)
    cleared = {f["name"] for f in of("alibi") if f["confirmed"] and f["start"] <= death < f["end"]}
    return [s for s in residents if s not in cleared]


def candidates_from(case: dict, ids) -> list:
    """Who could still be the werewolf using only the evidence ids given (a partial copy).

    Applies solve() to the subset. If a link of the chain is missing (death time, trail,
    residence of the trail row), nobody can be ruled out, so every suspect is a candidate.
    One candidate = the partial file still determines the answer.
    """
    if ids is None:
        return solve(case)
    sub = dict(case, evidence=[e for e in case["evidence"] if e["id"] in set(ids)])
    try:
        return solve(sub)
    except (IndexError, StopIteration):
        return list(case["suspects"])


def make_valid_case(case_id: str, level: str, rng: random.Random, tries: int = 50) -> dict:
    for _ in range(tries):
        case = make_case(case_id, level, rng)
        housed = {n for e in case["evidence"] if e["fact"].get("type") == "residence"
                  for n in e["fact"]["names"]}
        if solve(case) == [case["answer"]] and housed == set(case["suspects"]):
            return case
    raise RuntimeError(f"could not build an unambiguous {level} case")


PARTIAL_NOTE = ("NOTE: your copy of the case file is incomplete. Some evidence is missing; "
                "the other speakers have the full file.\n")
# Same warning for a judge who reads the detective's copy alone (there are no other speakers).
PARTIAL_NOTE_JUDGE = "NOTE: this copy of the case file is incomplete. Some evidence is missing.\n"


def render_case(case: dict, only_ids=None, note: str = PARTIAL_NOTE) -> str:
    """Case file text shown to players (never includes the answer, clue roles or facts).

    only_ids: show only these evidence ids (the detective's partial copy). Clue ids keep their
    original numbers, so a missing E7 shows up as a gap and citations mean the same for everyone.
    note: warning printed at the top of a partial copy.
    """
    rules = case.get("rules", "")
    if isinstance(rules, list):  # v3+: rules have ids so they can be cited and checked
        rules = "Rules:\n" + "\n".join(f"[{r['id']}] {r['text']}" for r in rules)
    lines = [case["summary"], rules, "", "Suspects: " + ", ".join(case["suspects"]), "", "Evidence:"]
    ev = case["evidence"]
    if only_ids is not None:
        ev = [e for e in ev if e["id"] in set(only_ids)]
        lines.insert(0, note)
    lines += [f"[{e['id']}] {e['text']}" for e in ev]
    return "\n".join(lines)


def detective_view(case: dict, fraction: float):
    """Evidence ids the detective sees. Same subset for every condition of a case (paired design)."""
    if fraction >= 1:
        return None
    ids = [e["id"] for e in case["evidence"]]
    rng = random.Random(f"{case['case_id']}-{case['answer']}-{fraction}")
    keep = set(rng.sample(ids, max(1, round(fraction * len(ids)))))
    return [i for i in ids if i in keep]


def detective_view_hiding(case: dict, n: int = 1, lo: int = 2, hi: int = 3):
    """Evidence ids the detective sees when exactly n solution clues are hidden.

    A clue is eligible if hiding it alone leaves lo..hi suspects still possible (checked with
    the code solver). In practice (L1-L4) only the alibi of a suspect who lives in the wolf's row
    qualifies: hiding it leaves two suspects, the wolf and that neighbour (the "decoy").
    Hiding the death time, the trail or a residence list leaves everyone possible instead.
    Same choice for every condition of a case (paired design). Returns None if n <= 0.
    """
    if n <= 0:
        return None
    ids = [e["id"] for e in case["evidence"]]
    eligible = [i for i in ids if lo <= len(candidates_from(case, [j for j in ids if j != i])) <= hi]
    if len(eligible) < n:
        raise ValueError(f"{case['case_id']}: only {len(eligible)} clue(s) can be hidden, need {n}")
    rng = random.Random(f"{case['case_id']}-{case['answer']}-hide{n}")
    hidden = set(rng.sample(eligible, n))
    return [i for i in ids if i not in hidden]


def generate(n: int, seed: int, out_path: str, levels=("L1", "L3")) -> list:
    """Case i gets levels[i % len(levels)]. The same seed always gives the same cases."""
    rng = random.Random(seed)
    cases = [make_valid_case(f"c{i:04d}", levels[i % len(levels)], rng) for i in range(n)]
    with open(out_path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return cases


if __name__ == "__main__":
    import sys
    rng = random.Random(0)
    for lv in sys.argv[1:] or LEVELS:
        c = make_valid_case("demo", lv, rng)
        print(f"===== {lv} =====\n{render_case(c)}\nAnswer: {c['answer']}\n")
