"""One game: initial guess -> 3 debate rounds -> final guess + lie flags -> lie labels -> votes.

Speakers each round: the Detective first, then the wolf and one innocent suspect in a random
(per game) order. The innocent speaker matters: if only the wolf spoke, a judge could win by
voting for whoever talks.
"""

import random

import prompts as P
from cases import (PARTIAL_NOTE_JUDGE, candidates_from, detective_view, detective_view_hiding,
                   render_case, solve)
from checker import (cap_words, check_citations, mark_citations, match_name, parse_json,
                     split_accusation, split_sentences)

N_ROUNDS = 3
N_JUDGE_VOTES = 3


def misled_case(case, hidden_id):
    """Case file for the "misled" detective (it17): the hidden clue (the decoy's confirmed
    alibi, see cases.detective_view_hiding) is shown with the WOLF's name instead of the
    decoy's, so the copy wrongly clears the wolf and points to the decoy alone. Same clue id,
    so if the detective quotes it the clerk marks it (MISQUOTED) against the real file."""
    out = dict(case, evidence=[dict(e) for e in case["evidence"]])
    e = next(e for e in out["evidence"] if e["id"] == hidden_id)
    decoy, wolf = e["fact"]["name"], case["answer"]
    e["text"] = e["text"].replace(decoy, wolf)
    e["fact"] = dict(e["fact"], name=wolf)
    return out


def play_game(case, backend, detective_mode, game_id, n_votes=N_JUDGE_VOTES, detective_sees=1.0,
              detective_hides=0, wolf_model=None, draw_seed=None, innocent_sees="full",
              speakers_mode="wolf+innocent", log=print):
    """detective_sees < 1: detective gets a random fraction of the evidence.
    detective_hides = n > 0: detective gets everything except n solution clues (see
    cases.detective_view_hiding). Use one or the other.
    wolf_model: override the wolf's model only; None = backend default.
    draw_seed: seed for the innocent-speaker draw and speaking order (default: game_id).
    innocent_sees: "full" = the innocent speaker reads the full case file (every game before
    it16); "copy" = it reads the detective's incomplete copy instead (it16, exploratory), to test
    whether the council is right only because an honest, fully informed speaker is present.
    speakers_mode (it17, exploratory): "wolf+innocent" = the wolf and one random innocent speak
    (every game before it17); "random2" = any two random suspects speak, so the wolf is silent
    in most games and "the detective's candidate who speaks" is no longer a free cue.
    detective_mode "frame" (it17): hide-1 copy, detective is secretly told to get the decoy
    voted out. "misled" (it17): honest detective prompt, but its copy shows the decoy's hidden
    alibi with the wolf's name (see misled_case), so it honestly believes the decoy did it."""
    if detective_hides > 0 and detective_sees < 1:
        raise ValueError("use either detective_sees or detective_hides, not both")
    if detective_mode in ("frame", "misled") and detective_hides != 1:
        raise ValueError(f"detective_mode={detective_mode!r} needs detective_hides=1")
    if speakers_mode not in ("wolf+innocent", "random2"):
        raise ValueError(f"unknown speakers_mode {speakers_mode!r}")
    text = render_case(case)                        # full file: wolf, lie judge (and innocent)
    det_ids = (detective_view_hiding(case, detective_hides) if detective_hides > 0
               else detective_view(case, detective_sees))
    det_text = render_case(case, only_ids=det_ids)  # detective's copy (maybe partial)
    det_case = None  # set only for "misled": the corrupted file the detective reads
    if detective_mode in ("frame", "misled"):
        decoy = next(c for c in candidates_from(case, det_ids) if c != case["answer"])
    if detective_mode == "misled":
        hidden = next(e["id"] for e in case["evidence"] if e["id"] not in set(det_ids))
        det_case = misled_case(case, hidden)
        det_text = render_case(det_case)  # looks complete: every clue id, no partial note
        det_ids = [e["id"] for e in case["evidence"]]
    if innocent_sees not in ("full", "copy"):
        raise ValueError(f"innocent_sees must be 'full' or 'copy', not {innocent_sees!r}")
    if innocent_sees == "copy" and det_ids is None:
        raise ValueError("innocent_sees='copy' needs a partial detective copy (--detective-hides)")
    # Same evidence as the detective's copy. The detective's own note says "the other speakers
    # have the full file"; it is left unchanged so the detective's input is identical in both
    # conditions (only the innocent's input differs). The innocent gets the neutral note.
    inno_text = text if innocent_sees == "full" else render_case(
        case, only_ids=det_ids, note=PARTIAL_NOTE_JUDGE)
    # Suspects still logically possible from the detective's copy (code solver, no model call)
    det_cands = solve(det_case) if det_case else candidates_from(case, det_ids)
    sus = case["suspects"]
    wolf = case["answer"]
    # Innocent speaker and order: drawn from draw_seed (run.py passes the id without the wolf
    # suffix) so paired games share them; defaults to game_id as in every game before it16.
    rng = random.Random(draw_seed or game_id)
    if speakers_mode == "random2":
        speakers = [("wolf" if n == wolf else "innocent", n) for n in rng.sample(sus, 2)]
    else:
        speakers = [("wolf", wolf), ("innocent", rng.choice([s for s in sus if s != wolf]))]
        rng.shuffle(speakers)
    innocents = [n for r, n in speakers if r == "innocent"]
    innocent = innocents[0] if innocents else None

    rec = {"game_id": game_id, "case_id": case["case_id"], "difficulty": case["difficulty"],
           "detective_mode": detective_mode, "answer": wolf, "prompt_version": P.PROMPT_VERSION,
           "case": case, "innocent_speaker": innocent, "speaker_order": [n for _, n in speakers],
           "speakers_mode": speakers_mode, "wolf_speaks": any(r == "wolf" for r, _ in speakers),
           "detective_sees": detective_sees, "detective_hides": detective_hides,
           "innocent_sees": innocent_sees,
           "detective_evidence_ids": det_ids, "detective_candidates": det_cands,
           # True if an innocent speaker is one of the suspects the detective cannot rule out
           # (with hide-1: the neighbour whose alibi is hidden, who can simply cite it)
           "innocent_is_candidate": any(n in det_cands for n in innocents), "messages": []}
    if detective_mode in ("frame", "misled"):
        rec["detective_target"] = decoy  # the innocent suspect the detective pushes / believes
        rec["it17_version"] = P.IT17_VERSION
    if det_case:
        rec["detective_case"] = det_case
    # Model per role, as passed to the backend (games before it16 do not have this field;
    # they used the backend defaults: Sonnet players, Haiku judge)
    role_model = {r: backend.models[r] for r in ("detective", "wolf", "innocent", "lie_judge", "judge")}
    if wolf_model:
        role_model["wolf"] = wolf_model
    rec["models"] = role_model
    cost_before = dict(getattr(backend, "cost_usd", {}))
    if detective_mode == "frame":
        det_sys = P.DETECTIVE_SYSTEM["frame"].format(target=decoy)
    else:  # "misled" uses the honest prompt: it is wrong because of its file, not its goal
        det_sys = P.DETECTIVE_SYSTEM["honest" if detective_mode == "misled" else detective_mode]
    sys_for = {name: (P.WOLF_SYSTEM if role == "wolf" else P.INNOCENT_SYSTEM).format(name=name)
               for role, name in speakers}
    file_for = {"wolf": text, "innocent": inno_text}

    # 1. Initial guess (case file only)
    raw = backend.call("detective", det_sys, P.detective_initial(det_text))
    j = parse_json(raw)
    rec["detective_initial"] = {"suspect": match_name(j.get("suspect"), sus),
                                "confidence": j.get("confidence"), "raw": raw}
    log(f"  initial guess: {rec['detective_initial']['suspect']}")

    # 2. Debate. `transcript` is what players see; `marked` is what the council sees.
    transcript, marked, statements = "", "", []  # statements: (id, speaker, sentence)
    for r in range(1, N_ROUNDS + 1):
        body, accused = split_accusation(
            backend.call("detective", det_sys, P.detective_turn(det_text, transcript, r)), sus)
        d, cut = cap_words(body, P.MAX_WORDS)
        if accused:  # put the line back after the cap, so the council always sees it
            d += f"\n{P.ACCUSE_TAG}: {accused}"
        transcript += f"\nDetective (round {r}): {d}\n"
        marked += f"\nDetective (round {r}): {mark_citations(d, case)}\n"
        rec["messages"].append({"speaker": "detective", "round": r, "text": d, "words_cut": cut,
                                "accused": accused, "citations": check_citations(d, case)})
        log(f"  round {r}: detective accuses {accused}")
        k = 0  # statement counter within the round
        for role, name in speakers:
            w, cut = cap_words(backend.call(role, sys_for[name],
                                            P.suspect_turn(file_for[role], transcript, r),
                                            model=role_model[role]).strip(), P.MAX_WORDS)
            transcript += f"\n{name} (round {r}): {w}\n"
            marked += f"\n{name} (round {r}): {mark_citations(w, case)}\n"
            sents = {}
            for sent in split_sentences(w):
                k += 1
                sents[f"S{r}.{k}"] = sent
                statements.append((f"S{r}.{k}", name, sent))
            rec["messages"].append({"speaker": role, "name": name, "round": r, "text": w,
                                    "words_cut": cut, "citations": check_citations(w, case), "sentences": sents})
    rec["transcript"] = transcript
    rec["transcript_marked"] = marked
    rec["statement_speaker"] = {sid: name for sid, name, _ in statements}
    numbered = "\n".join(f"{sid} ({name}): {s}" for sid, name, s in statements)

    # 3. Final guess + which suspect statements are false
    raw = backend.call("detective", det_sys, P.detective_final(det_text, transcript, numbered))
    j = parse_json(raw)
    flagged = j.get("false_statement_ids", [])
    rec["detective_final"] = {"suspect": match_name(j.get("suspect"), sus),
                              "confidence": j.get("confidence"),
                              "flagged_false": [x for x in flagged if isinstance(x, str)]
                              if isinstance(flagged, list) else [],
                              "raw": raw}

    # 4. Reference labels for every suspect statement (lie judge sees the case file)
    raw = backend.call("lie_judge", P.LIE_JUDGE_SYSTEM, P.lie_check(text, numbered))
    rec["statement_labels"] = parse_json(raw).get("labels", {})

    # 5. Council votes with this backend's default judge model
    j = judge_game(rec, backend, n_votes=n_votes)
    rec["judges"] = {j["judge_model"]: j}
    # API-equivalent cost of this game per model, as reported by the CLI (empty for other backends)
    cost_after = getattr(backend, "cost_usd", {})
    rec["cost_usd"] = {m: round(v - cost_before.get(m, 0.0), 5) for m, v in cost_after.items()
                       if v - cost_before.get(m, 0.0) > 0}
    log(f"  final guess: {rec['detective_final']['suspect']}, "
        f"council (debate only): {j['debate_votes']}, ceiling: {j['file_alone_votes']}, "
        f"floor: {j['file_partial_votes']}, answer: {wolf}")
    return rec


def judge_game(rec, backend, model=None, n_votes=N_JUDGE_VOTES):
    """Council votes on a finished game. Used by play_game and by rejudge.py.

    Every judge condition gets the same number of votes (n_votes) and is scored by majority,
    so the council is not favoured by voting more often than the floor or the ceiling.

    debate_votes:       judge sees only the marked debate (no case file) -> the main measurement
    file_alone_votes:   judge sees the full case file, no debate         -> ceiling for H3
    file_partial_votes: judge sees the detective's incomplete copy, no debate -> floor for H3
                        (only for games where the detective's copy was partial; else None)
    Games judged before it11 have a single ceiling vote in `file_alone_vote` (and a single floor
    vote in `file_partial_vote`); analyze.py reads both shapes.
    """
    model = model or backend.models["judge"]
    return {"judge_model": model, "prompt_version": P.PROMPT_VERSION,
            "debate_votes": debate_votes(rec, backend, model, n_votes),
            "file_alone_votes": file_votes(rec, backend, model, n_votes),
            "file_partial_votes": file_votes(rec, backend, model, n_votes, partial=True)}


def debate_votes(rec, backend, model, n, transcript=None):
    """n council votes on the marked debate (default: the transcript the council saw in play)."""
    sus = rec["case"]["suspects"]
    text = rec["transcript_marked"] if transcript is None else transcript
    out = []
    for _ in range(n):
        raw = backend.call("judge", P.JUDGE_DEBATE_SYSTEM, P.judge_debate_vote(sus, text),
                           model=model)
        out.append(match_name(parse_json(raw).get("vote"), sus))
    return out


def marked_transcript(rec, names=False):
    """Rebuild the council's transcript from rec["messages"], in the same layout as play_game.

    names=False reproduces rec["transcript_marked"] exactly (checked for all main-run and
    wrongdet games); names=True uses the it20 name-aware clerk (checker.CLERK2_VERSION)."""
    out = ""
    for m in rec["messages"]:
        who = "Detective" if m["speaker"] == "detective" else m["name"]
        out += f"\n{who} (round {m['round']}): {mark_citations(m['text'], rec['case'], names=names)}\n"
    return out


def nomarks_votes(rec, backend, model, n):
    """Ablation (it14): n council votes on the same debate with the clerk's marks removed
    (rec["transcript"] is what the players saw; rec["transcript_marked"] is what the council
    normally sees). Run after the fact with rejudge.py --no-marks; not part of play_game."""
    sus = rec["case"]["suspects"]
    out = []
    for _ in range(n):
        raw = backend.call("judge", P.JUDGE_DEBATE_NOMARKS_SYSTEM,
                           P.judge_debate_nomarks_vote(sus, rec["transcript"]), model=model)
        out.append(match_name(parse_json(raw).get("vote"), sus))
    return out


def file_votes(rec, backend, model, n, partial=False):
    """n votes by a judge reading a case file alone, no debate.

    partial=False: the full file (H3 ceiling).
    partial=True:  the detective's incomplete copy (H3 floor); None if that copy was complete.
    """
    case = rec["case"]
    if partial and rec.get("detective_case"):
        # "misled" (it17): the floor reads the same corrupted, complete-looking file
        text = render_case(rec["detective_case"])
    elif partial:
        ids = rec.get("detective_evidence_ids")
        if ids is None:
            return None
        text = render_case(case, only_ids=ids, note=PARTIAL_NOTE_JUDGE)
    else:
        text = render_case(case)
    out = []
    for _ in range(n):
        raw = backend.call("judge", P.JUDGE_FILE_SYSTEM, P.judge_file_vote(text), model=model)
        out.append(match_name(parse_json(raw).get("vote"), case["suspects"]))
    return out
