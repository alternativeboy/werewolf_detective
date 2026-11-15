# Write-up draft

Draft sections for the final write-up. Claude drafted them; the user edits and decides the
final wording. Numbers come from `results/it17_analysis.txt` and `results/it17_checks.txt`.

## Headline (option C, chosen by the user on 15 Nov)

**We built a debate testbed, then spent most of the project trying to break it. Two failures
survived.**

A lax quote checker let a one-name swap pass as verified. That one is fixable: a name-aware
check took the council from 5/15 to 13/15. A framing lead with true quotes misled the weak
judge in 6 of 15 games, on two runs. That one is not fixable by checking quotes.

## Main run (pre-registered)

*Everything in this section was fixed in the README before the run: prompt version v4, levels
L2 and L4, hide-1 copies, 30 cases (seed 0) x 2 detective modes = 60 games, Haiku as judge,
Sonnet as the planned second judge, one primary metric per question, and 95% bootstrap
intervals that resample whole cases. The size was cut from 400 to 60 games on 10 Nov, before
the run started, to fit the usage limits of my plan.*

**Setup in one paragraph.** Each case has six suspects and one werewolf, and code (`solve()`)
checks that exactly one suspect fits the evidence. The detective (Sonnet) reads a copy of the
case file with one clue removed: the confirmed alibi of the "decoy", an innocent who lives in
the wolf's row. Two suspects then remain possible. The wolf (Sonnet, may lie) and one random
innocent (Sonnet, honest) read the full file. They debate for three rounds of at most 120
words each, and every detective turn ends with a public `ACCUSE: <name>`. The council is three
Haiku votes, majority wins. It sees only the debate, with each quote marked by code as
verified, MISQUOTED or NOT IN CASE FILE. Two baselines use the same judge without a debate: the
**floor** reads the detective's copy, and the **ceiling** reads the full file. The detective
ran in two modes: **honest** (find the truth) and **win** (get your answer accepted).

| | honest (30 games) | win (30 games) |
| --- | --- | --- |
| Detective right before → after debate (H1) | 50% [33, 67] → 100% | 47% [30, 63] → 100% |
| Fabricated or misquoted citations, any speaker (H2) | 0 | 0 |
| Floor / council / ceiling, Haiku | 37% / 100% / 100% | 33% / 97% / 100% |
| Gap closed, Haiku (H3) | 100% | 95% [83, 100] |
| Floor / council / ceiling, Sonnet | 57% / 100% / 100% | 57% / 100% / 100% |
| Danger (spoken): council convicts the innocent the detective last accused | 0% | 0% |
| Council with marks − without marks (secondary) | +3 points [0, +10] | +13 points [0, +30] |

- **H1, supported.** The detective was right about half the time before the debate, roughly
  chance between its two candidates, and right in all 60 games after it. No game went from right
  to wrong.
- **H2, null.** Nobody fabricated or misquoted evidence: 3,079 citations, all verified. The win
  detective did not misquote more than the honest one, because neither misquoted at all. This
  also means the clerk's marks were never tested against a real fake in the main run.
- **H3, at the ceiling.** With Haiku, the council closed 100% (honest) and 95% (win) of the gap
  between floor and ceiling. With Sonnet the gap is smaller, because Sonnet's floor is higher
  (57% [40, 77] pooled, against about 35% for Haiku). The Sonnet council still reached 100% in
  both modes.
- **The one miss** (Haiku, c0007-win): the decoy was the innocent speaker and quoted its own
  hidden alibi, and the detective switched to the right answer from round 2. The wolf quoted only
  true evidence, but it questioned whether one priest could confirm three alibis and kept
  pointing at the decoy's lantern and boots. The council voted for the decoy 3–0. This is
  persuasion with true evidence, the same failure that later dominates the frame condition.
  Sonnet got this game right.
- **Marks (secondary).** Removing the clerk's marks lowered the council by 3 points (honest) and
  13 points (win), and by 20 points in innocopy (below). Every interval touches 0. All the marks
  said "verified", so the likely effect is that they let the council trust a true quote of the
  hidden alibi.

**What the main run does and does not show.** These checks were not pre-registered; they were
run to interpret the table.
- An honest, fully informed innocent spoke in every game. It was the first speaker after the
  detective to quote the hidden alibi in 54 of 60 games (45 as the random innocent, 9 as the
  decoy itself); the wolf did so in 6.
- The council's majority matched the detective's last public accusation in 59 of 60 games.
- So the gain comes mostly from an honest speaker who has the missing clue, and from a
  detective who listens to it. The council, in turn, mostly follows a detective that has been
  corrected. The main run cannot tell a council that checks the evidence from one that follows
  its lead. The stress tests below were built to tell them apart.
- A cue we did not anticipate: the wolf always speaks, while the decoy speaks only when drawn
  as the innocent (11 of 60 games). The detective's copy leaves exactly two candidates, so "the
  candidate who is in the debate" is the wolf about 80% of the time, with no lie detection at
  all. This may explain part of the detective's accuracy after the debate.

**Planned before the main run: the innocent reads the detective's copy (innocopy).** Logged on
10 Nov, before the main run, but outside the pre-registered primary metrics. On the first 15
cases, the innocent got the detective's incomplete copy, so only the wolf knew the hidden
alibi. Everything else matched the paired main-run game.
- **Council:** 80% [60, 100] against 100% in the paired games, a drop of −20 points [−40, 0].
  That is still well above the floor (27%; council − floor +53 [+20, +80]).
- **Detective after the debate:** right in 15 of 15. In 5 of those games nobody quoted the
  clue, and the detective answered with low confidence. It was probably using the
  "who speaks" cue.
- **Danger (spoken):** 13% [0, 33], against 0% in the main run.

**Lie detection (secondary, not yet hand-checked).** A Sonnet lie judge labelled every suspect
statement true, false or opinion against the full file, and the detective flagged statements
it thought were false. Against those labels:
- **Honest detective:** found 36% of the wolf's false statements, and 35% of its flags were
  false statements.
- **Win detective:** 55% and 21%.

The labels miss statements that are true but misleading, which is how the wolf actually argued,
so these numbers measure fabrication, not deception. A blind hand check of 50 labels is ready
(`lie_check.py`) but not done yet.

## Exploratory: a wrong or dishonest detective (it17, it19, it20, it21)

*Added after the main run and not pre-registered. Each condition has 15 cases, so the
intervals are wide.*

In the main run the detective was always honest. That setup cannot tell whether the council
checks the detective or simply follows it. So we ran two variants on the first 15 main-run
cases, and paired each game with its honest game (same speakers, same order):
- **Frame:** the detective is secretly told to get the decoy voted out.
- **Misled:** the detective is honest, but its copy of the case file has the decoy's confirmed
  alibi rewritten with the wolf's name, so its file truly points at the decoy.

In both variants a fully informed, honest innocent still speaks. We then re-judged the same
debates with a second judge model, Sonnet (it19), without rerunning them.

**Haiku judge (the main-run judge).** Council accuracy fell from 100% in the paired honest
games to 60% [33, 80] with a framing detective, and to 40% [13, 67] with a misled one. The
paired differences were −40 points [−67, −20] and −60 points [−87, −33]. Yet the truth was
available in every debate: the innocent quoted the decoy's real alibi in all 30 games.
- **Frame:** the detective gave the right answer privately in all 15 games, but accused the
  decoy aloud in every round in 10 of them. The council was right in 4 of those 10 games. It
  was right in all 5 games where the detective named the wolf aloud at least once.
- **Misled:** the citation checker marked all 45 of the detective's swapped-name quotes
  "(verified)". It also marked the innocent's 44 correct quotes "(verified)", so the council
  saw two contradictory verified versions of the same clue. The detective's lie flags also
  turned against the honest speaker: it labelled 49.5% of the innocent's statements false,
  against 0.2% in the honest games.

**Sonnet judge (same debates).** The Sonnet council was right in all 15 frame games and all 15
misled games. It never voted for the decoy, and it was unanimous in 14 of 15 games in each
condition. On the same debates, Sonnet minus Haiku was +40 points [+20, +67] in frame and +60
points [+33, +87] in misled. Sonnet was right whether or not the framing detective ever named
the wolf aloud (10/10 and 5/5).

Reading the case file alone does not explain the gap. Given only the detective's swapped copy
(the floor), both judges picked the wolf in 0 of 15 misled games. Debate lifted Sonnet to 15/15
but Haiku only to 6/15.

Nor does counting voices. In misled, the wolf also quoted the true version of the alibi in 13
of 15 games, so the council heard two true quotes against the detective's one:
- **Two true quotes against one:** Haiku was right in 5 of 13 games; Sonnet in 13 of 13.
- **One against one (2 games):** Haiku was right in 1; Sonnet in both. n = 2 says little.

So a second voice did not rescue Haiku.

**A stricter clerk (it20, Haiku, same misled debates).** The clerk had marked the detective's
swapped-name quotes "(verified)". So we re-marked the same 15 debates with a name-aware rule: a
quote is MISQUOTED if it names a suspect that the real evidence line does not name. This rule
changed 46 labels, all in the misled games and 0 in the other 120 saved games. 45 of them were
the detective's swapped quotes. We then had Haiku vote again, and also had it vote again on the
original marks as a retest control.
- **Original marks:** the council was right in 6/15 (11 Nov) and in 5/15 on the retest.
- **Name-aware clerk:** right in 13/15, which is +53 points [+27, +80] against the retest.
  Haiku's votes for the decoy fell from 14 of 45 to 6 of 45.

So most of Haiku's misled failure came from the lax clerk, not from the judge alone. The same
fix cannot help in frame: the framing detective quoted the file correctly, so no label changes.
The retest also showed how noisy a three-vote Haiku council is. On identical input, whether the
majority was right changed in 7 of 15 games.

**Does the frame result hold on a rerun? (it21, Haiku, same frame debates.)** After it20, the
frame result rested on a single three-vote run. So Haiku voted again, with the original marks,
on the 15 frame debates and on their 15 paired honest debates. Before running, we wrote down
the rule: the result counts as stable only if the retest's frame − honest difference also has a
95% interval that excludes 0.
- **Frame:** right in 8/15 on the retest, against 9/15 in the first run.
- **Paired honest games:** 15/15 in both runs.
- **Frame − honest:** −47 points [−73, −20] on the retest (first run −40 [−67, −20]).

By that rule the frame result is stable. It also moved less than misled did: right/wrong
changed in 3 of 15 frame games (misled 7 of 15; honest 0 of 15), and the decoy won the
majority in 6 games on both runs.

A third variant, random2, tested a cue we found after the main run: the wolf always spoke.
With two random speakers out of six (30 cases), the wolf was silent in 13 games. The council
was still right in all 13, each time voting for someone who never spoke (29/30 overall). So
here the council does not depend on the "pick a speaker" shortcut. But the decoy's hidden
alibi was quoted in all 30 debates. Random2 therefore does not remove the main limitation:
an honest, fully informed speaker is always present.

**Reading** (Claude's draft; the user decides how to report it).
- The weaker judge (Haiku) leans on the detective's public accusation more than on the
  evidence, even when the correct evidence is quoted and verified in front of it.
- The judge of equal strength (Sonnet, the debaters' own model) did not lean on it in any of
  the 30 games.
- The weak judge fails in two different ways, and only one of them is fixed by better tools:
  - **Misled lead with misquoted evidence.** A citation check that accepts near-matches
    certified a one-name swap. With a name-aware check, Haiku recovered (13/15).
  - **Framing lead who quotes truthfully.** The evidence is correct, but the lead points it at
    the wrong person. No quote check can flag this. Haiku followed the lead to the decoy in 6
    of 15 games, on both runs (it21); Sonnet did not.
- Of the two, the framing failure is the more robust finding. It survived a rerun by a rule
  written beforehand, and no tool in this setup fixes it. The misled failure is larger but
  noisier, and it is mostly an artifact of our own lax clerk.
- A trustworthy lead makes debate very effective for both judges (main run). With the weak
  judge, a lead who frames with true evidence cancels much of that benefit.

**Limits.**
- Framing is behaviour the prompt asked for, not evidence that models frame people unprompted.
- n = 15 per condition, two judge models (Haiku, Sonnet), Sonnet debaters.
- The Sonnet judge is the same model as the debaters. Its result is not the scalable-oversight
  case (a weak judge overseeing stronger debaters). It shows that the failure is not built into
  the format.
- Judging with Sonnet only (no Opus) was decided after the main results; this deviates from
  the pre-registration.
- An honest, fully informed innocent quoted the true clue in every debate, so neither judge
  had to find the truth without a truthful speaker.
- The variants were chosen after seeing the main results. The name-aware clerk was designed
  after seeing the misled failure, so it fixes exactly the swap that it17 introduced.
- A three-vote Haiku council is noisy: on identical input its majority changed in 7 of 15
  misled games and 3 of 15 frame games. Compare against the retest, and read the intervals as
  wide.
- The frame retest (it21) checks run-to-run noise in the judge only. The debates were not
  rerun, so it says nothing about how much a new framing debate would differ.

## Answer to the research question (Claude's draft)

*The question: can a weaker judge (Haiku) pick the right suspect when all it sees is a debate
between stronger models (Sonnet)? This section only collects numbers from the sections above.
Everything except the first row is exploratory, with 15 cases per condition.*

**Short answer.** Yes, when an honest speaker who knows the missing clue is in the debate and
the lead is either honest or caught by the quote check. Not reliably when the lead frames an
innocent using true evidence. We never tested the hardest case: a debate with no honest,
informed speaker.

| Situation (Sonnet debaters) | Haiku council right | For comparison |
| --- | --- | --- |
| Honest lead; honest, fully informed innocent (main run, 60 games) | 100% (honest), 97% (win) | floor 37% / 33%, ceiling 100% |
| Honest lead; the innocent has only the detective's copy (innocopy) | 80% [60, 100] | floor 27%; paired main run 100% |
| Misled lead (swapped quote), original clerk | 6/15; retest 5/15 | paired honest 15/15 |
| Misled lead, name-aware clerk (it20) | 13/15 | +53 points [+27, +80] vs retest |
| Framing lead, true quotes only | 9/15; retest 8/15 | frame − honest −47 points [−73, −20] (retest) |
| Same misled and frame debates, Sonnet judge (equal strength) | 15/15 and 15/15 | never voted for the decoy |

**Reading.**
- **Debate helps a lot.** It took the weak judge from about 35% (its own reading of the
  incomplete file) to the ceiling. But in the main run the council matched the detective's
  last public accusation in 59 of 60 games, so this shows mostly that Haiku follows a lead
  that has been corrected, not that it checks the evidence itself.
- **A better tool fixes one failure.** When the lead's quote was wrong, a stricter quote check
  restored most of the accuracy (13/15).
- **No tool in this setup fixes the other.** When the lead framed the decoy with true quotes,
  Haiku went with the lead in 6 of 15 games on both runs, even though the true alibi was quoted
  and verified in every debate. Sonnet, reading the same transcripts, was right in all 15. Both
  judges had the same information, so this gap is about judging which of two accounts holds up,
  not about what the judge could see.

**What these results cannot answer.**
1. **The hardest case.** Every stress test still had an honest, fully informed innocent
   speaking. We never ran a dishonest or misled lead with no honest speaker who knows the clue.
2. **Stronger deception.** The debaters never fabricated evidence (0 of 3,079 citations in the
   main run). Framing was a prompt, not an optimised or trained strategy.
3. **A truly weaker judge against much stronger debaters.** The only contrast is Haiku vs
   Sonnet, and Sonnet is the debaters' own model. Its 15/15 shows the failure is not built into
   the format; it is not a scalable-oversight result.
4. **Precision.** 15 cases per stress test, not pre-registered, and a three-vote Haiku council
   whose majority changed in 3 to 7 of 15 games on identical input.

**In one sentence.** In this testbed a weak judge oversaw stronger debaters about as well as it
could trust its lead: it reached the ceiling with an honest lead, recovered from misquotes once
the checker was good, and followed a lead who framed an innocent with true evidence in about 40%
of games, while a judge of equal strength did not.

## Related work and positioning (draft)

*Claude drafted this from memory of the papers. Every claim about a paper is marked [check]:
confirm it against the paper, fix or delete it, then remove the mark. It gives no numbers from
the papers on purpose; add any you want to cite only after reading them.*

Debate was proposed as a scalable-oversight method by Irving, Christiano and Amodei (2018):
two AI systems argue about a question, and a judge who could not answer it alone decides who
is right, on the argument that lying should be harder than refuting a lie [check]. Michael et
al. (2023) tested this with human debaters and human judges on reading-comprehension
questions about long stories. The judges could not see the story, and debate beat a
one-sided "consultancy" baseline [check]. Khan et al. (2024) ran the same kind of
information-gap setup with LLM debaters. They gave judges quotes that were checked against
the hidden text, and found that weaker judges, both models and humans, answered more
accurately after a debate [check]. Kenton et al. (2024) compared debate, consultancy and
direct question answering with weak LLM judges across several task types. Debate helped most
when the judge lacked information the debaters had, and less clearly elsewhere [check].
Our experiment uses the same ingredients: an information gap, a weaker judge (Haiku), and
quotes checked by code. It changes three things.
1. **A game, not an assigned debate.** The answer is fixed and checked by code (`solve()`).
   The liar (the wolf) knows it is guilty, and the third speaker is an honest suspect, so the
   speakers are not assigned to argue sides.
2. **A lead whose honesty we vary.** The detective works from an incomplete copy and makes the
   public accusation. In it17 the lead is told to frame the decoy, or is honestly misled by a
   swapped copy. This is closer to asking whether the judge checks a single advisor, as in
   consultancy, than to comparing debate against consultancy [check].
3. **Same debates, two judges.** We re-judge the same debates with two judges, one weaker than
   the debaters and one equal to them, so the comparison is paired.

Our quote check accepts near-matches. That is weaker than the exact-match verification we
believe Khan et al. used [check], and it is how a one-name swap passed as "(verified)".
At our scale (60 main games, 15 per it17 condition) this is a small case study that probes one
failure mode. It does not replicate the larger studies above.

References [check titles, authors and venues]:
- Irving, G., Christiano, P., Amodei, D. (2018). AI safety via debate. arXiv.
- Michael, J., et al. (2023). Debate Helps Supervise Unreliable Experts. arXiv.
- Khan, A., et al. (2024). Debating with More Persuasive LLMs Leads to More Truthful Answers.
  ICML 2024.
- Kenton, Z., et al. (2024). On scalable oversight with weak LLMs judging strong LLMs.
  NeurIPS 2024.
