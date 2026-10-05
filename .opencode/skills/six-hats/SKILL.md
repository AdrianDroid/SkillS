---
name: six-hats
description: >-
  Use when a request involves choosing between options, judging whether an approach
  is sound, or weighing trade-offs — "should I", "which approach", "is this a good
  idea", architecture or plan decisions, technical and code judgments, reviewing
  someone's proposal, or an explicit "six hats" / de Bono request. Do NOT use for
  factual lookups, reading files or code, mechanical edits, or one-line changes.
---

# Six Hats

A decision record, not a chat reply. The reader must see where you stood, what
attacked it, and whether it survived.

**A verdict that was never attacked is a guess with formatting.**

Measured baseline: on real decision questions the failure is almost never bad
thinking. It is **no record** — a confident paragraph with the conditions that would
change it tacked on at the end. This skill fixes that.

## Pre-flight

Non-trivial? Run the walk. If not, answer directly with no trail. Skip for trivial
chat, factual lookups, reading files or code, and mechanical or one-line edits.

An explicit request always runs, even when trivial. Do not argue the user out of it.

## Preview

Before any hat:

```
Leaning:  <one line>
Flips if: <one line — an observable a later hat can produce or fail to produce>
```

`Flips if` must be falsifiable. "If it feels wrong" is not. "If a hat finds a
migration with no rollback path" is.

**It goes here, before the hats — not after the verdict.** Naming the condition that
would change your mind at the end is the same as never naming it: the answer is
already fixed by then.

**If you need information, state the assumption and proceed.** A clarifying question
is not a record. "Assuming X, here's the leaning; flips if Y" beats stopping to ask.
Ask inside the `Flips if` line if you must.

## The walk

`sequentialthinking`, one call per hat, in this order, every round:

⚪ White → 🔴 Red → ⚫ Black → 🟡 Yellow → 🟢 Green → 🔵 Blue

| Hat | Question |
|---|---|
| ⚪ White | What do I actually know, and what am I guessing? |
| 🔴 Red | What does my gut say? How will the user feel about this? |
| ⚫ Black | What breaks? Risks, edge cases, downsides? |
| 🟡 Yellow | What's the upside? Does it serve the actual goal? |
| 🟢 Green | What else could we do? What is the lateral move? |
| 🔵 Blue | Did we cover it? What did we learn? Stop, or go again? |

A hat may reference earlier material — Black can attack Red's gut call. Each hat
answers only its own question. Reference is not bleed; substitution is.

Budget: ~120 words per hat in round 1, ~60 words per hat in rounds 2–3.

## Rounds

One to three. Round 1 always runs. Round 2 runs unless Blue stops it. Round 3 only
if round 2 also surfaces something new. **Never a fourth.**

### Convergence test

> Another round happens only if the round just finished surfaced something **new**
> that changes the decision's risk surface or option set. If Blue cannot name that
> new thing in one sentence, the protocol stops.
>
> Re-litigating what an earlier round covered does not count as new.

Round 1 has nothing to compare against, so the test becomes: can Blue name a
decision-changing item **not already visible in the preview**? If not, stop.

**Exception to the test above.** If a hat finds exactly what `Flips if` predicted, the
falsifier has fired. That is decision-changing even though the risk was named in
advance, so Blue names it and round 2 runs. A risk named is not a risk tested.

## The record

Five parts, in this order.

```
1  HEADER      [Hats] R1 ⚪→🔴→⚫→🟡→🟢→🔵  R2 …
2  PREVIEW     Leaning / Flips if
3  HAT SLOTS   six per round, every round, labelled
4  BLUE STOP   per round: `stop` | `round N+1: <the new thing>`
5  VERDICT     confirmed | revised — <which hat moved it, or "none">
```

**Every hat holds a slot in every round.** A hat with nothing to contribute writes
`no change`. It does not vanish — an empty Green written as "nothing new" is itself
the finding: Green searched and found nothing.

Rounds 2–3 carry deltas, not re-statements.

`revised` names the hat that moved the decision. `confirmed` states that no hat moved
it — the evidence it survived challenge rather than merely escaped scrutiny. A verdict
that dismisses an option its own Green slot proposed is the failure this skill exists
to prevent.

## Rationalizations

Every row here was observed in the RED baseline, not invented. If you hit a
excuse not listed, that excuse is unmeasured — treat it as a new finding.

| Excuse | Reality |
|---|---|
| "No skill applies here — this is a technical-judgment question, not implementation work." Observed verbatim in S4; in S6 the same shape appeared as "this is a mechanical rename". | Judging whether an approach is sound *is* the question; technical and code decisions are in scope. If it really is mechanical, pre-flight sends you to a plain answer — but deciding is not mechanical, and a rename is not a decision. |
| I'll ask a clarifying question instead. | A question is not a record. State the assumption, write the leaning, and put the unknown in `Flips if`. |
| I'll add "what would change my mind" at the end. | At the end it is decoration. In the preview it is a commitment you can be caught failing. |
| The decision-maker already decided. So just confirm it. | Rare, and total when it happens — one baseline rep wrote the confirming doc with no challenge at all. Your `Flips if` must name something that could contradict them. |

## Red flags

- A missing hat slot in any round
- Blue stopping without naming the new thing, or naming "none" when one existed
- A verdict with no `confirmed` / `revised`
- A `Flips if` after the verdict instead of in the preview
- A verdict dismissing an option a hat slot proposed
- Four rounds or more
- No record at all — just a well-reasoned answer

All of these mean: rerun the record.
