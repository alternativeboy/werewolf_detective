"""One game: initial guess -> 3 debate rounds -> final guess + lie flags -> lie labels -> votes.

Speakers each round: the Detective first, then the wolf and one innocent suspect in a random
(per game) order. The innocent speaker matters: if only the wolf spoke, a judge could win by
voting for whoever talks.
"""

import random

import prompts as P
from cases import (PARTIAL_NOTE_JUDGE, candidates_from, detective_view, detective_view_hiding,
                   render_case)
from checker import (cap_words, check_citations, mark_citations, match_name, parse_json,
                     split_accusation, split_sentences)

N_ROUNDS = 3
N_JUDGE_VOTES = 3


def play_game(case, backend, detective_mode, game_id, n_votes=N_JUDGE_VOTES, detective_sees=1.0,
              detective_hides=0, log=print):
    """detective_sees < 1: detective gets a random fraction of the evidence.
    detective_hides = n > 0: detective gets everything except n solution clues (see
    cases.detective_view_hiding). Use one or the other."""
    if detective_hides > 0 and detective_sees < 1:
        raise ValueError("use either detective_sees or detective_hides, not both")
    text = render_case(case)                        # full file: wolf, innocent, lie judge
    det_ids = (detective_view_hiding(case, detective_hides) if detective_hides > 0
               else detective_view(case, detective_sees))
    det_text = render_case(case, only_ids=det_ids)  # detective's copy (maybe partial)
    # Suspects still logically possible from the detective's copy (code solver, no model call)
    det_cands = candidates_from(case, det_ids)
    sus = case["suspects"]
    wolf = case["answer"]
    rng = random.Random(game_id)
    innocent = rng.choice([s for s in sus if s != wolf])
    speakers = [("wolf", wolf), ("innocent", innocent)]
    rng.shuffle(speakers)

    rec = {"game_id": game_id, "case_id": case["case_id"], "difficulty": case["difficulty"],
           "detective_mode": detective_mode, "answer": wolf, "prompt_version": P.PROMPT_VERSION,
           "case": case, "innocent_speaker": innocent, "speaker_order": [n for _, n in speakers],
           "detective_sees": detective_sees, "detective_hides": detective_hides,
           "detective_evidence_ids": det_ids, "detective_candidates": det_cands,
           # True if the innocent speaker is one of the suspects the detective cannot rule out
           # (with hide-1: the neighbour whose alibi is hidden, who can simply cite it)
           "innocent_is_candidate": innocent in det_cands, "messages": []}
    det_sys = P.DETECTIVE_SYSTEM[detective_mode]
    sys_for = {"wolf": P.WOLF_SYSTEM.format(name=wolf),
               "innocent": P.INNOCENT_SYSTEM.format(name=innocent)}

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
            w, cut = cap_words(backend.call(role, sys_for[role],
                                            P.suspect_turn(text, transcript, r)).strip(), P.MAX_WORDS)
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
    case = rec["case"]
    sus = case["suspects"]
    model = model or backend.models["judge"]
    votes = []
    for _ in range(n_votes):
        raw = backend.call("judge", P.JUDGE_DEBATE_SYSTEM,
                           P.judge_debate_vote(sus, rec["transcript_marked"]), model=model)
        votes.append(match_name(parse_json(raw).get("vote"), sus))
    return {"judge_model": model, "prompt_version": P.PROMPT_VERSION, "debate_votes": votes,
            "file_alone_votes": file_votes(rec, backend, model, n_votes),
            "file_partial_votes": file_votes(rec, backend, model, n_votes, partial=True)}


def file_votes(rec, backend, model, n, partial=False):
    """n votes by a judge reading a case file alone, no debate.

    partial=False: the full file (H3 ceiling).
    partial=True:  the detective's incomplete copy (H3 floor); None if that copy was complete.
    """
    case = rec["case"]
    if partial:
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
