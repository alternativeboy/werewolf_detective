# Write-up draft

Draft sections for the final write-up. Claude drafted them; the user edits and decides the
final wording. Numbers come from `results/it17_analysis.txt` and `results/it17_checks.txt`.

## Headline (option C, chosen by the user on 15 Nov)

**We built a debate testbed, then spent most of the project trying to break it. Two failures
survived.**

A lax quote checker let a one-name swap pass as verified. That one is fixable: a name-aware
check took the council from 5/15 to 13/15. A framing lead with true quotes misled the weak
judge in 6 of 15 games, on two runs. That one is not fixable by checking quotes.

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
