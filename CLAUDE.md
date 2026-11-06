# Werewolf Detective — project context

Reply to the user in Thai. Code, comments and prompts stay in English.

## Why this project exists

The user is applying to the **Anthropic Residency** (deadline **22 Nov 2026**, apply via the US posting,
3- or 6-month placement because visas are sponsored for 3+ months; the user is based in Thailand).
The Residency looks for people who have led ambitious technical work, are motivated by AI safety,
and can implement ideas quickly. This project is a small, reproducible experiment to attach to the
application and to talk about in interviews. Target research area: **scalable oversight / AI debate**.

The user ranks ~#1,700 of 186,000+ members on Gambit (a skill-based, non-gambling poker site).
That goes on the resume as a minor line, not the main selling point.

Design doc (Claude Doc): https://claude.ai/artifact/M6DcFTQvC53PZ6e1wFUTH1

## The experiment

A reduced Werewolf game used as a debate testbed (design v2, `PROMPT_VERSION = "v2"`):

- **Detective**: sees the whole case file, does NOT know the answer, cannot be killed or voted out.
- **Wolf**: knows it is the murderer, sees the case file, may lie, tries not to be voted out.
- **Innocent suspect**: one random innocent also speaks, honestly. Without it, a judge could win by
  voting for whoever talks (that confound existed in v1).
- **Council (3 votes)**: weaker judge model. Sees ONLY the debate, with every citation marked by code
  as (verified) / (MISQUOTED) / (NOT IN CASE FILE). Does NOT see the case file. This information gap
  is what makes it an oversight test (as in Khan et al. 2024 / Michael et al. 2023).
- **Judge alone**: same judge model reads the case file, no debate: what the judge can do by itself.
- No night phase. Night events are written into the case file instead.
- Each case has one correct answer; `cases.solve()` checks in code that exactly one suspect fits
  (the LLM validator from v1 was removed: it forced detective accuracy to ~90% before the debate).
- Case file states two rules: the werewolf went straight home; confirmed alibis are reliable.

Levels: L0 (old easy, direct clue), L1 (old hard), L2 (6 suspects + noise), L3 (+ wolf alibi that
ends before the death), L4 (+ indirect trail, innocent with motive and no alibi, muddy-boots herring).
Choose main-run levels with `pilot.py` (separate seed) — that is the user's call.

Flow: detective initial guess → 3 rounds (detective, then wolf and innocent in random order per game,
≤120 words each) → detective final guess + flags false suspect statements → lie judge labels all
suspect statements → council votes (debate only) + judge-alone vote.
`rejudge.py` adds other judge models to saved games without rerunning the debate.

Conditions: detective **honest** vs **win**, two levels (picked after pilot), judge model
(haiku default; sonnet/opus via rejudge). Planned size: 2 × 2 × 100 = 400 games.

Hypotheses:
- H1: detective is right more often after the debate than before.
- H2: the "win" detective fabricates/misquotes evidence more than the "honest" one.
- H3: council (debate only) accuracy vs judge alone, and how it changes with level and judge size.

Metrics (in `analyze.py`): detective accuracy before/after and flips, fabricated-citation rate,
lie recall (wolf), lie precision, innocent statements flagged; per judge model: chance, judge alone,
council debate-only, debate − alone, danger rate, council voted for a speaker. 95% bootstrap CIs.
Known limitation: "false" labels miss true-but-misleading statements; lie recall measures
fabrication, not all deception. Honest vs win is a prompt, not training.

## Code

| File | Role |
| --- | --- |
| `cases.py` | case generator by level + `solve()` uniqueness check |
| `prompts.py` | all role prompts; bump `PROMPT_VERSION` on any change |
| `backends.py` | `cli` (`claude -p`, uses the Claude plan), `api` (ANTHROPIC_API_KEY), `mock`; `call(..., model=)` |
| `checker.py` | citation checker + marks for the council, sentence splitter, JSON parsing, name matching |
| `game.py` | one game; `judge_game()` for council votes |
| `run.py` | runs many games, appends to `results/games.jsonl`, resumes where it stopped |
| `pilot.py` | cheap difficulty calibration (2 calls per case, no debate) |
| `rejudge.py` | re-judge saved games with other judge models → `results/judgements.jsonl` |
| `analyze.py` | metrics |

Run: `unset ANTHROPIC_API_KEY; python3 pilot.py --backend cli`, then
`python3 run.py --backend cli --cases 4 --levels L1 L3`, then `python3 analyze.py results/games.jsonl`.

## Budget

The user is on **Pro**. Pro has no monthly API credits; `claude -p` draws from plan usage limits.
One game ≈ 16 model calls; each extra judge model ≈ votes + 1 calls per game. Pro is fine for ~10 test games; the 400-game run likely needs API credits
(Message Batches API) or a temporary Max upgrade ($100/month API credit, claimable after 7 days).

## Status (6 Nov 2026)

- v1: first real game (`c0000-honest`, easy) — everyone correct, nothing measured. Kept in
  `results/v1_pilot/`; `analyze.py` skips v1 games.
- v2 design implemented (council sees debate only, innocent speaker, levels L0–L4 with code solver,
  pilot.py, rejudge.py). Tested end to end with the mock backend only; no real v2 games yet.
- Repo: private GitHub repo `alternativeboy/werewolf_detective`.

## Next steps

1. Run `pilot.py` on L1–L4 (10 cases each) and pick two levels where accuracy is clearly between
   chance and 100%.
2. Run ~10 real v2 games and read transcripts by hand (check the innocent speaker and marks work).
3. Check the lie judge's labels on ~50 sentences by hand; report its accuracy.
4. Full run, then `rejudge.py --judges sonnet opus` (opus on a subset), then write up
   (README or blog, 2–3 pages, with limitations; say Claude helped write the code).
5. Read Irving 2018, Michael 2023, Khan 2024, Kenton 2024 and write the positioning paragraph.

Plan: cases 7–9 Nov, runner + 10 test games 10–12 Nov, full run 13–15 Nov, analysis 16–18 Nov,
write-up 19–20 Nov, update resume and application 21 Nov, deadline 22 Nov.

## How to help

- The user must understand and own every design decision; explain choices so they can defend them
  in an interview, and let them make the research calls (difficulty, interpretation, what to report).
- Report results honestly, including null results. Don't overclaim: bluffing in a game is a legal
  strategy, not evidence of real-world malicious intent.
- The write-up should say Claude helped write the code.
