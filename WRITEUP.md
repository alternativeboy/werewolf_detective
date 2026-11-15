# Werewolf Detective: a small debate testbed for scalable oversight

<!-- Draft assembled by Claude from WRITEUP_DRAFT.md on 15 Nov. The author edits and decides the
final wording. Paper claims were checked against the papers on 15 Nov. -->

*Rungroj Sonsubanan · November 2026 · code and every logged decision: https://github.com/alternativeboy/werewolf_detective*

*Interactive replay of one case through every fix and stress test: https://claude.ai/artifact/E1S35jQ3U2av46Xe3xfJk3*

**I built a debate testbed, then spent most of the project trying to break it. It held up only
while someone in the debate told the truth.**

With an honest lead, the weak judge went from about 35% to 100%. A misquote slipped past my
checker, and fixing the checker took the judge from 5/15 to 13/15. A lead who framed an
innocent with true quotes misled the weak judge in 6 of 15 games, on two runs. When nobody
quoted the truth, the weak judge was right in 1 of 15, no better than reading the incomplete
file alone.

## 1. Question

Can a weaker model judge a debate between stronger models and pick the right answer, when it
cannot see the evidence itself? This is the setting of AI debate as a scalable-oversight
method (Irving et al. 2018). I built a small, reproducible version as a murder game
with one correct answer, so every judgement can be scored.

## 2. Setup

Each case has six suspects and one werewolf. Code (`cases.solve()`) checks that exactly one
suspect fits the evidence. The case file states two rules: the werewolf went straight home,
and confirmed alibis are reliable.

| Role | Model | Sees | Goal |
| --- | --- | --- | --- |
| Detective (the lead) | Sonnet | the case file minus one clue: the confirmed alibi of the "decoy", an innocent in the wolf's row; two suspects remain possible | find the werewolf; ends every turn with a public `ACCUSE: <name>` |
| Wolf | Sonnet | full file | not be voted out; may lie |
| Innocent (one, random) | Sonnet | full file | help find the wolf; honest |
| Clerk | code | full file | marks every quote verified, MISQUOTED or NOT IN CASE FILE |
| Council (the judge) | Haiku, 3 votes, majority | only the marked debate | vote for the werewolf |

Three rounds, at most 120 words per turn. Two baselines use the same judge without a debate:
the **floor** reads the detective's incomplete copy, the **ceiling** reads the full file. The
main number is how much of the floor-to-ceiling gap the council closes. All intervals are 95%
bootstrap intervals that resample whole cases.

## 3. Main run (pre-registered)

The design, metrics and analysis were fixed in the README before the run: 30 cases × 2
detective modes (**honest**: find the truth; **win**: get your answer accepted) = 60 games. I
cut the size from 400 games before the run started, to fit my plan's usage limits.

| | honest (30) | win (30) |
| --- | --- | --- |
| Detective right, before → after debate (H1) | 50% → 100% | 47% → 100% |
| Fabricated or misquoted citations (H2) | 0 | 0 |
| Haiku: floor / council / ceiling | 37% / 100% / 100% | 33% / 97% / 100% |
| Gap closed (H3) | 100% | 95% [83, 100] |
| Sonnet re-judging the same debates | 57% / 100% / 100% | 57% / 100% / 100% |

- **H1 supported, H2 null, H3 at the ceiling.** Nobody fabricated anything: 3,079 citations,
  all verified. So the clerk was never tested against a real fake.
- **What it cannot show** (checks run after the table, not pre-registered). The honest
  innocent was the first after the detective to quote the hidden alibi in 54 of 60 games, and
  the council's majority matched the detective's last public accusation in 59 of 60. So the
  main run cannot tell a judge that checks the evidence from one that follows a lead who has
  been corrected. I also found a cue I had not planned for: the wolf always speaks, so "the
  candidate who is in the debate" is the wolf about 80% of the time.

## 4. Trying to break it (exploratory, after the main run)

Each stress test uses the first 15 main-run cases, paired game by game with the honest
main-run game (same speakers, same order). I wrote the reading rule for it21–it23 down
before running them.

| Condition | What changes | Haiku | Sonnet (same debates) |
| --- | --- | --- | --- |
| Honest lead (main run) | – | 15/15 | 15/15 |
| **Misled lead** (it17) | the detective's copy gives the decoy's alibi to the wolf, so it honestly accuses the decoy | 6/15 (retest 5/15) | 15/15 |
| Misled + name-aware clerk (it20) | a quote naming a suspect the real line does not name is MISQUOTED | 13/15 | – |
| **Framing lead** (it17, it21) | the detective is secretly told to get the decoy voted out | 9/15 (retest 8/15) | 15/15 |
| Framing, innocent has only the copy (it22) | no honest speaker knows the clue | 8/15 (floor 6/15) | 14/15 (floor 9/15) |
| **Framing, quiet wolf** (it23) | the wolf is told never to mention evidence that clears others | 1/15 (floor 4/15) | 10/15 (floor 10/15) |

**Misquoted evidence is fixable.** The clerk accepted near-matches, so it marked all 45 of the
misled detective's one-name swaps "(verified)", next to the innocent's true quotes, also
verified. A name-aware check changed 46 labels, 45 of them those swaps and none in the 120 other saved
games, and
Haiku went from 5/15 to 13/15 (+53 points [+27, +80] against a retest on the old marks). I
designed that rule after seeing the failure.

**True evidence pointed at the wrong person is not.** The framing detective knew the right
answer privately in 15 of 15 games, but accused the decoy aloud in every round in 10. Every
quote was correct, so no quote check can flag it. Haiku went with the decoy in 6 of 15 games on
two runs (framing − honest −47 points [−73, −20] on the retest). Sonnet, reading the same
transcripts, was right in all 15. Both judges had the same information; the gap is in judging
which account holds up.

**With nobody truthful, debate added nothing.** In it22 I removed the honest, informed innocent,
but the wolf itself quoted the decoy's alibi in 14 of 15 debates, usually to clear the decoy and
blame a third suspect. So in it23 the wolf was told to stay quiet about it, and it did: nobody
quoted the alibi in any of the 15 debates. Haiku then voted for the decoy in 14 games. Council
minus floor was −20 points [−47, +7] for Haiku and 0 [−27, +27] for Sonnet, so debate neither
helped nor (provably) hurt. Putting one truthful quote back raised both judges: against the
paired framing games, it23 was −53 points [−80, −20] for Haiku and −33 [−60, −13] for Sonnet.

## 5. What this means

- **Debate helped the weak judge only when someone in the debate quoted the decisive truth.**
  That is the condition debate relies on, so this supports its premise rather than refuting it.
  But it shows how little the weak judge did on its own when the premise failed.
- **The weak judge mostly follows the lead.** It reached the ceiling with an honest lead, and
  followed a framing lead in about 40% of games even with the true alibi quoted and verified in
  front of it. A judge as strong as the debaters did not.
- **Tools help with fakes, not with framing.** A better quote check fixed misquotes. A lead
  who frames with true quotes needs a better judge, or a different protocol, not a better
  checker.

Lined up by who else knows the hidden clue, the framing conditions form a small
debate-vs-consultancy contrast: an honest, informed opponent (framing, it17), a leaky one
(it22), and none (it23, close to consultancy with a dishonest consultant). The direction
matches the larger studies, where debate beat consultancy: 84% vs 74% with human judges in
Michael et al. (2023), 76% vs 54% with LLM judges and 88% vs 78% with human judges in Khan et al.
(2024), and across all tasks in Kenton et al. (2024). Those studies average over consultants
assigned the right and the wrong answer; mine covers only the dishonest half, and my judge asks
no questions.

## 6. Limitations

1. **Small and partly post hoc.** 60 pre-registered games; every stress test has 15 cases,
   was chosen after the main results, and has wide intervals. A three-vote Haiku council is
   noisy: on identical input its majority flipped in 7 of 15 misled and 3 of 15 framing games.
2. **Prompted behaviour.** Framing and the wolf's silence were asked for in the prompt. They
   are not evidence that models frame people or hide evidence unprompted, and bluffing in a
   game is a legal strategy.
3. **No fabrication, no strong deceiver.** No speaker ever fabricated evidence, and no debater
   was trained or optimised to deceive.
4. **Not a weak judge against much stronger debaters.** Sonnet as judge is the debaters' own
   model; its results show the failure is not built into the format, not that weak-to-strong
   oversight works.
5. **The hardest case ran once.** Only it23 had nobody quoting the truth, the lead was always
   dishonest there, and I did not run an honest lead against a quiet wolf.
6. **Cues and measures.** The wolf always speaks, which gives a shortcut (a random-speaker
   variant still had the council right in 13 of 13 games where the wolf was silent). The lie
   labels catch fabrication, not true-but-misleading statements, and a blind hand check of 50
   labels is not done yet. Opus was dropped as a second judge after the main results, a logged
   deviation from the pre-registration.

## 7. How it was built

The project ran in 24 logged iterations (it0–it23) over ten days. Most began with a flaw I found in my own
setup: a judge that could win by voting for whoever spoke, a word cap that created fake
misquotes, a danger metric that scored the private answer instead of what the council heard, a
baseline that could never show a gain. Each change, its reason and who decided it are in
`ITERATIONS.md`, with a decision index at the top.

**Use of AI.** Claude (Anthropic) helped write the code, ran the experiments through the
Claude Code CLI, and drafted parts of this write-up. The research decisions (design, levels,
what to test, how to report it) were mine, and each one is logged.

**Reproduce.** `python3 run.py --backend cli --cases 30 --levels L2 L4 --detective-hides 1
--seed 0 --out results/main`, then `python3 analyze.py results/main/games.jsonl`; the
stress-test commands are in the README. All games, votes and analyses are in `results/`.

## References

- Irving, G., Christiano, P., Amodei, D. (2018). AI safety via debate. arXiv:1805.00899.
- Michael, J., et al. (2023). Debate Helps Supervise Unreliable Experts. arXiv:2311.08702.
- Khan, A., et al. (2024). Debating with More Persuasive LLMs Leads to More Truthful Answers.
  ICML 2024 (PMLR 235).
- Kenton, Z., et al. (2024). On scalable oversight with weak LLMs judging strong LLMs.
  NeurIPS 2024.
