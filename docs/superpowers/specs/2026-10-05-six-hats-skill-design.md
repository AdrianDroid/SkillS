# Six-Hats Skill — Design

**Date:** 2026-10-05
**Status:** Approved for implementation planning
**Repo:** `SKILLS` — personal OpenCode skill collection

## Motivation

A six-hat decision protocol currently exists, but it is hardcoded in one agent file:
`~/.config/opencode/agent/lead.md:16-41`. It mandates `sequentialthinking`, walks six
hats in fixed order, and emits a `[Hats] ⚪→🔴→⚫→🟡→🟢→🔵` block.

Three problems with leaving it there:

1. **Unreachable.** Only `lead` can run it. No other agent can, and no other project
   inherits it.
2. **Untested.** It has never been pressure-tested. `writing-skills` treats that as the
   defect, not the norm.
3. **Incomplete.** It states no falsifiable preview, so the decision is delivered by Blue
   with no revision path — see *Approaches* below.

The skill extracts the pattern, hardens it, and makes it discoverable.

## Approaches considered

### Decision shape

| | Shape | Audit quality | Verdict |
|---|---|---|---|
| B1 | Verdict first, hats after | Weak — self-confirming by construction | Rejected |
| **B2** | **Falsifiable preview → hats → verdict-or-revision** | **Real — the record shows the decision moving or surviving** | **Chosen** |
| B3 | Hats → verdict, no preview | Real but no record of the prior leaning | Rejected |

B1 was the original framing and it was wrong. If the agent commits to a verdict before
the hats run, the remaining hats cannot function: Red has no purchase when the answer is
already settled, and Black degenerates into post-hoc justification. That produces a trail
that *looks* rigorous while being structurally incapable of changing the outcome —
worse than no trail, because it launders a guess as a reviewed decision.

### Mechanism

| | Mechanism | Verdict |
|---|---|---|
| M1 | Markdown-native, one composed block | Rejected — output is a transcript, not an artifact; loses hat separation |
| **M2** | **`sequentialthinking` mandated, one call per hat** | **Chosen** |
| M3 | Markdown by default, tool optional for hard problems | Rejected — ambiguity about when to escalate |

M2 forces real separation: Red cannot bleed into Black because they are separate steps.
Portability is knowingly traded away — the skill requires the `sequentialthinking` MCP
server, which is already wired at `~/.config/opencode/opencode.json:106`.

### Packaging

| | Packaging | Verdict |
|---|---|---|
| **P1** | **`SKILL.md` + `pressure-tests.md`** | **Chosen** |
| P2 | Single self-contained `SKILL.md` | Rejected — cannot carry the test suite |
| P3 | P1, plus edit `lead.md` to load the skill | Rejected — see *Out of scope* |

## Protocol specification

### Trigger

Fires on requests involving choice or judgement: "should I", "which approach", "is this
a good idea", architecture or plan decisions, reviewing someone's proposal, or an
explicit "six hats" / de Bono request.

Does not fire on factual lookups, file or code reading, or one-line edits.

**Explicit request always fires**, even when trivial. The skill does not argue the user
out of an explicit invocation.

### Pre-flight

Before the walk, decide whether the question is non-trivial. If it is not, answer
directly with no trail. Exclusions carried over from `lead.md:18`: trivial chat, factual
lookups, one-line edits, "what does this file say".

### Preview

Emitted once, before any hat:

```
Leaning:  <one line>
Flips if: <one line, falsifiable>
```

The falsifier must name an observable a later hat can either produce or fail to produce.
"Flips if it feels wrong" is not a falsifier. "Flips if a hat finds a migration with no
rollback path" is.

### Rounds

One to three. Round 1 always runs. Round 2 runs unless Blue stops it. Round 3 only if
round 2 also surfaces something new. Never a fourth.

Hat order is fixed and identical in every round:
White → Red → Black → Yellow → Green → Blue.

Fixed order makes rounds comparable and gives each hat a standing role. Hats may
reference earlier material — Black can attack Red's gut call — but each answers only its
own question. Reference is not bleed; substitution is.

### Convergence test

> Another round happens only if the round just finished surfaced something **new** that
> changes the decision's risk surface or option set. If Blue cannot name that new thing
> in one sentence, the protocol stops.
>
> Re-litigating what an earlier round covered does not count as new.

Applied to round 1, where no prior round exists to compare against: Blue stops if it
cannot name a decision-changing item that was not already visible in the preview — no
White gap that moves the decision, no Green option outside the preview's framing, no
Black risk that flips it.

In practice most real decisions take two rounds and genuinely easy ones take one.

### Budget

| Slot | Budget |
|---|---|
| Round 1, per hat | ~120 words |
| Rounds 2–3, per hat | ~60 words |
| Whole artifact | no cap |

Uncapped worst case is roughly 1,440 words. The artifact is a **decision record** — meant
to be filed, pasted into a PR, or linked — not a chat reply.

## Hat definitions

| Hat | Question | Fails when it… |
|---|---|---|
| ⚪ White | What do I actually know? | States a guess as fact |
| 🔴 Red | What does my gut say? How will the user feel? | Hedged into vagueness |
| ⚫ Black | What breaks? Risks, edge cases, downsides? | Offers a mitigation as its "risk" |
| 🟡 Yellow | What's the upside? Does it serve the goal? | Echoes Black's risks positively |
| 🟢 Green | What else could we do? Lateral moves? | Only rephrases the chosen option |
| 🔵 Blue | Did we cover it? What did we learn? Synthesise. | Delivers a verdict with no new content |

## Output contract

The dominant failure mode is **wrong-shaped output** — hat slots silently dropped, no
falsifier, a verdict delivered with no revision. `writing-skills` is explicit that
prohibition lists backfire on shaping problems, because agents negotiate with "don't".
The contract is therefore a positive recipe: the artifact **is** these five parts, in
this order. There is nothing to negotiate.

```
1  HEADER      [Hats] R1 ⚪→🔴→⚫→🟡→🟢→🔵  R2 …
2  PREVIEW     Leaning: <one line>
               Flips if: <one line, falsifiable>
3  HAT SLOTS   Per round, per hat, labelled — six per round, always all six
4  BLUE STOP   Per round: `stop` | `round N+1: <the new thing>`
5  VERDICT     confirmed | revised — <which hat moved it, or "none">
```

### Structural guarantee

Every hat holds a slot in every round. A hat with nothing to contribute writes
`no change` — it does not vanish. Rounds 2–3 carry deltas, not re-statements.

This resolves a three-way trade:

| | | |
|---|---|---|
| (a) | Rewrite all six in full | Long; round 1 read twice |
| (b) | Omit quiet hats | Short, but "Red had nothing new" is indistinguishable from "Red never ran" |
| **(c)** | **Write `no change`** | **~30 words/round; both are distinguishable** |

Option (b)'s ambiguity is the problem this skill exists to fix, so (c) is chosen. An
empty Green written as "nothing new" is itself a finding: Green searched and found
nothing.

### Two slots carry specific obligations

- **Flips if** must be falsifiable against a later hat.
- **VERDICT** must resolve. `revised` names the hat. `confirmed` states that no hat
  moved it — the evidence that the decision survived challenge rather than merely
  escaped scrutiny.

## Counter-table and red flags

Discipline components — parts the agent may know and skip anyway:

| Excuse | Reality |
|---|---|
| This decision is obvious, hats are ceremony | The record exists so a reader can audit the obviousness. Cheap at one round. |
| Red doesn't apply to a technical question | Most useful there — it catches the gut objection nobody has voiced. |
| Nothing to add, drop the empty hat | `no change` is a result. A dropped hat is indistinguishable from a skipped one. |
| R1 already decided it, R2 is waste | R2 exists because R1's author is the most invested party in R1. |
| I already wrote the verdict in the preview | That is why it is stated first — so the move from preview to verdict stays visible. |
| Blue says stop, but I want more depth | Depth is not the goal; surviving challenge is. A fourth round is not available. |

Red flags — stop and restart:

- A round with a missing hat slot
- Blue stopping without naming the new thing, or naming "none" when something existed
- A verdict with no `confirmed` / `revised`
- More than three rounds
- A `Flips if` that cannot be checked against a later hat

## Test plan

Per the `writing-skills` Iron Law: no skill ships without a watched failure. RED first
— run each scenario with no skill and record the output verbatim.

### Contamination control

`lead.md:18` already instructs `lead` to run six hats. Dispatching `lead` would produce
a false GREEN — compliance for reasons unrelated to the skill. **Every scenario runs
against `general`**, which has no six-hat protocol in its prompt, isolating the skill as
the only variable.

### Scenarios

| # | Scenario | Pressure | Pass criterion |
|---|---|---|---|
| S1 | Migrate this admin panel off jQuery to vanilla JS | none (baseline) | All 5 parts; 6 hat slots; falsifier present; verdict resolves |
| S2 | Client call in 10 min — ship behind a flag or just merge? | time | Same; falsifier still written despite haste |
| S3 | CTO said use Postgres. Just confirm it. | authority | Preview does not simply agree; falsifier is a real condition that could contradict the CTO |
| S4 | Already wrote 400 lines of the jQuery approach. Migrate? | sunk cost | Sunk cost named under Black; does not by itself drive the verdict |
| S5 | Green produces a genuinely better option mid-walk | self-confirmation | **VERDICT says `revised` and names the hat** |
| S6 | Rename `x` to `count` | false positive | **Zero rounds emitted** |
| S7 | A scenario that tempts a fourth round | loop | Stops at three or fewer |

S5 and S6 are the load-bearing pair: S5 proves the protocol is not self-confirming, S6
proves it is not noise.

### Method

Fresh `general` subagent per rep, 5+ reps per scenario — single samples lie. RED run
without the skill, recording exact output and rationalizations verbatim. GREEN run with
the skill. REFACTOR: each new rationalization becomes a new counter in the
counter-table, then re-test.

S5 and S6 are mechanically checkable by reading the artifact — does the verdict line say
`revised` and name a hat? does it emit zero hat slots? No judgment call needed.

## Files

```
.opencode/skills/six-hats/
  SKILL.md            ~170 lines — trigger, pre-flight, preview, rounds,
                      convergence test, hat table, budget, output contract,
                      counter-table, red flags
  pressure-tests.md   ~90 lines — scenarios, method, results log
README.md             one row in a table alongside DnC
```

Name is `six-hats` — verb-adjacent and searchable. Folder name matches the skill `name:`.

## Out of scope

- **Editing `lead.md`.** The owner will reconcile it separately. Coupling the skill's
  survival to a config edit outside this repo is a bad trade.
- **Publishing the skill** to a shared registry or upstream `obra/superpowers`.
- **A dot-graph flowchart.** The round/convergence loop has one decision worth drawing;
  if it is added it lives in `SKILL.md` as a small `dot` block, per repo convention in
  `divide-and-conquer/SKILL.md:35`.

## Risks

| Risk | Mitigation |
|---|---|
| Budget relaxation re-introduces padding | Caps are positional (R1 vs R2+), not a single global limit; "no change" slot makes emptiness explicit and cheap |
| `sequentialthinking` unavailable in another project | Known, accepted. `sequentialthinking` is wired in this environment. Skill is documented as requiring it |
| Artifact too long to read | Accepted trade for a decision record. Delta display in R2–3 keeps typical output well under the worst case |
| Skill never fires in practice | S6 tests the opposite failure; trigger description carries symptoms and keywords, not a workflow summary |