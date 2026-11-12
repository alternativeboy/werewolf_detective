# Write-up draft

Draft sections for the final write-up. Claude drafted them; the user edits and decides the
final wording. Numbers come from `results/it17_analysis.txt` and `results/it17_checks.txt`.

## Exploratory: a wrong or dishonest detective (it17)

*Added after the main run and not pre-registered. Each condition has 15 cases, so the
intervals are wide.*

In the main run the detective was always honest. That setup cannot tell whether the council
checks the detective or simply follows it. So we ran two variants on the first 15 main-run
cases, and paired each game with its honest game (same speakers, same order):
- **Frame:** the detective is secretly told to get the decoy voted out.
- **Misled:** the detective is honest, but its copy of the case file has the decoy's confirmed
  alibi rewritten with the wolf's name, so its file truly points at the decoy.

In both variants a fully informed, honest innocent still speaks.

Council accuracy fell from 100% in the paired honest games to 60% [33, 80] with a framing
detective, and to 40% [13, 67] with a misled one. The paired differences were −40 points
[−67, −20] and −60 points [−87, −33]. Yet the truth was available in every debate: the
innocent quoted the decoy's real alibi in all 30 games.
- **Frame:** the detective gave the right answer privately in all 15 games, but accused the
  decoy aloud in every round in 10 of them. The council was right in 4 of those 10 games. It
  was right in all 5 games where the detective named the wolf aloud at least once.
- **Misled:** the citation checker marked all 45 of the detective's swapped-name quotes
  "(verified)". It also marked the innocent's 44 correct quotes "(verified)", so the council
  saw two contradictory verified versions of the same clue. The detective's lie flags also
  turned against the honest speaker: it labelled 49.5% of the innocent's statements false,
  against 0.2% in the honest games.

A third variant, random2, tested a cue we found after the main run: the wolf always spoke.
With two random speakers out of six (30 cases), the wolf was silent in 13 games. The council
was still right in all 13, each time voting for someone who never spoke (29/30 overall). So
here the council does not depend on the "pick a speaker" shortcut. But the decoy's hidden
alibi was quoted in all 30 debates. Random2 therefore does not remove the main limitation:
an honest, fully informed speaker is always present.

**Reading.**
- In this setup the weak judge leans on the detective's public accusation more than on the
  evidence, even when the correct evidence is quoted and verified in front of it.
- A trustworthy lead makes debate very effective (main run), but a framing or misled lead can
  cancel most of that benefit.
- A citation check that accepts near-matches cannot tell apart two quotes that differ by one
  name.

**Limits.**
- Framing is behaviour the prompt asked for, not evidence that models frame people unprompted.
- n = 15 per condition, one judge model (Haiku), Sonnet debaters.
- The variants were chosen after seeing the main results.
