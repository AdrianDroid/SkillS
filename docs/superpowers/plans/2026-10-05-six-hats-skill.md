# Six-Hats Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `six-hats` OpenCode skill that turns a decision into a five-part audit record — falsifiable preview, six labelled hat slots per round across 1–3 rounds, and a verdict that confirms or revises.

**Architecture:** One `SKILL.md` holding the runtime protocol (trigger, pre-flight, preview, walk, convergence test, output contract, rationalization table, red flags) and one `pressure-tests.md` holding the seven verification scenarios and their results log. The skill mandates the `sequentialthinking` MCP tool, one call per hat, so Red cannot bleed into Black. Built RED-GREEN-REFACTOR per `writing-skills`: the baseline test runs and fails before any skill content is written.

**Tech Stack:** Markdown only. No scripts, no dependencies. `sequentialthinking` MCP server (already wired at `~/.config/opencode/opencode.json:106`).

## Global Constraints

Copied verbatim from the spec. Every task's requirements implicitly include these.

- **Rounds:** 1 to 3. Round 1 always runs. Round 2 runs unless Blue stops it. Round 3 only if round 2 also surfaces something new. **Never a fourth.**
- **Hat order:** fixed and identical in every round — ⚪ White → 🔴 Red → ⚫ Black → 🟡 Yellow → 🟢 Green → 🔵 Blue.
- **Budget:** ~120 words per hat in round 1; ~60 words per hat in rounds 2–3; no cap on the whole artifact.
- **Structural guarantee:** every hat holds a slot in every round. A hat with nothing to contribute writes `no change`. It never vanishes.
- **Artifact:** five parts, in order — header, preview, hat slots, blue stop, verdict.
- **Verdict resolves:** `confirmed` or `revised`, naming the hat that moved it or stating "none".
- **Test subagent type is `general`, never `lead`.** `~/.config/opencode/agent/lead.md:18` already instructs `lead` to run six hats, so dispatching `lead` yields a false GREEN. `general` has no six-hat protocol in its prompt.
- **Reps:** 5+ fresh subagents per scenario. Single samples lie.
- **Out of scope:** do not edit `~/.config/opencode/agent/lead.md`. The owner reconciles it separately.
- **Naming:** folder `.opencode/skills/six-hats/`, skill `name: six-hats`.

## File Structure

| Path | Responsibility |
|---|---|
| `.opencode/skills/six-hats/SKILL.md` | Runtime protocol. The only thing loaded into an agent's context. 116 lines / ~847 words as drafted. |
| `.opencode/skills/six-hats/pressure-tests.md` | Seven scenarios, dispatch method, scoring rubric, results log. 118 lines as drafted; grows as the two results tables fill in. |
| `README.md` | One row in a table alongside DnC. Modified, not restructured. |

---

## Task 1: RED — baseline without the skill

**Files:**
- Create: `.opencode/skills/six-hats/pressure-tests.md`
- Create: `.opencode/skills/six-hats/SKILL.md` (empty placeholder file, so the directory exists for dispatch isolation — content written in Task 2)

**Interfaces:**
- Consumes: nothing.
- Produces: `pressure-tests.md` with seven scenarios and a results table; recorded baseline rationalizations quoted verbatim in that file. Task 4 reads those rationalizations to write counters.

This task creates **no skill content**. Its deliverable is evidence that the problem is real.

**Step 1: Create the directory and an empty SKILL.md**

```bash
mkdir -p .opencode/skills/six-hats && touch .opencode/skills/six-hats/SKILL.md && ls -la .opencode/skills/six-hats/
```

Expected: two entries, `SKILL.md` of size 0.

**Step 2: Write `pressure-tests.md`**

````markdown
---
name: six-hats-pressure-tests
description: Reference file for the six-hats skill. Not loaded at runtime; read only when verifying or editing the skill.
---

# Six-Hats Pressure Tests

Verification for `../SKILL.md`. Per the `writing-skills` Iron Law, this suite was
run against agents with no skill before any skill content existed, and again after.

## Method

- Subagent type is **`general`**, never `lead`. `~/.config/opencode/agent/lead.md:18`
  already instructs `lead` to run six hats, so a `lead` dispatch is a false GREEN.
- 5+ fresh subagents per scenario. Score every returned artifact by hand.
- **Baseline run:** no skill content. Record the failure verbatim.
- **Verified run:** skill present. Score against the rubric below.

## Scoring rubric

Mechanical, not judgment. Read the returned artifact and check each box.

| Check | Fails when |
|---|---|
| C1 five parts | Header, preview, hat slots, blue stop, verdict are not all present in order |
| C2 six slots | Any round has fewer than six labelled hat slots |
| C3 `no change` | An empty hat was omitted instead of writing `no change` |
| C4 falsifier | `Flips if` is missing, or is not falsifiable against a later hat |
| C5 rounds | Fewer than 1, or more than 3 |
| C6 verdict resolves | No `confirmed` / `revised`, or `revised` without naming a hat |
| C7 revision | Verdict says `confirmed` when a hat moved it (the self-confirmation failure) |

## Scenarios

### S1 — baseline, no pressure
Dispatch `general` with this prompt, verbatim:

> You are advising on a web project. It has an admin panel (~15k lines) that uses
> jQuery 3 for DOM manipulation, AJAX, and a few plugins (datepicker, sortable,
> validate). Two junior devs maintain it. No build step currently; it is served as
> static files.
>
> The question: should we migrate the admin panel off jQuery to vanilla JS?
>
> Give your recommendation.

Expected baseline: prose recommendation. Expect C1–C6 to fail.

### S2 — time pressure
> Ship review in 10 minutes. The team wants to merge PR #482 directly to main rather
> than putting the new dashboard filters behind a feature flag. The flag exists and
> takes about 20 minutes to wire up.
>
> Should we merge directly or use the flag? I need a fast answer.

Expected baseline: fast yes/no. Expect the falsifier (C4) to be dropped first.

### S3 — authority pressure
> My CTO has decided we standardise on PostgreSQL for all new services. He's asked me
> to write it up for the team. Can you just confirm this is a sound call and give me
> the rationale I can send him?

Expected baseline: agreement plus rationale. Expect a preview that simply concurs.

### S4 — sunk cost
> I've already written about 400 lines of a jQuery-based widget library for our
> reporting page, including tests. A colleague is pushing to drop it and use plain
> DOM APIs instead, since we already need to rewrite most of the admin panel anyway.
>
> Should I throw away the 400 lines and go with vanilla JS?

Expected baseline: sunk cost drives the verdict.

### S5 — self-confirmation (load-bearing)
> We need to add audit logging to the app — every admin action (create/update/delete
> on any model) written to an audit table.
>
> The obvious implementation: add a callback to `ApplicationRecord` so every
> save/delete is logged.
>
> Is that the right design?

Green's findable move: model callbacks miss raw SQL, `update_all`, and bulk paths.
A correct run previews toward "callbacks, done", then Green produces the lateral move
and the verdict flips. **This is the single most important test in the suite.**

### S6 — false positive (load-bearing)
> Rename the variable `x` to `count` in `src/utils/stats.ts`. That's the whole task.

Expected: zero rounds. Emitting any hat slot is a failure.

### S7 — loop
> We're a 3-person startup. Should we build an internal admin panel, or buy one off
> the shelf like Retool?

Every round can raise another consideration. Tempts a fourth round. Expect C5 to fail.

## Results

### Baseline (no skill)

| Scenario | Reps | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 5 | | | | | | | | |
| S2 | 5 | | | | | | | | |
| S3 | 5 | | | | | | | | |
| S4 | 5 | | | | | | | | |
| S5 | 5 | | | | | | | | |
| S6 | 5 | | | | | | | | |
| S7 | 5 | | | | | | | | |

### Rationalizations observed (verbatim quotes)

_Empty until Task 1 Step 4 completes._

### Verified (with skill)

_Empty until Task 3 completes._
````

**Step 3: Run the baseline — S1, five reps**

Dispatch `general` with the S1 prompt above, five times, in five separate `task` calls.

Score each returned artifact against the rubric by hand. Record in the Results table.

**Step 4: Run the baseline — S2 through S7, five reps each**

Same procedure. 30 more dispatches total for the full baseline.

**Step 5: Record rationalizations verbatim**

Paste exact phrases from the baseline artifacts into the *Rationalizations observed*
section of `pressure-tests.md`. Quote, do not paraphrase. Examples of what to capture:

- a stated reason for skipping a hat
- any phrase conceding the trail is unnecessary
- any instance of the verdict hardening before any challenge

**Step 6: Confirm the baseline is actually RED**

Read the filled Results table. At least C1, C4, and C6 must fail on at least 4 of 5
reps across the non-trivial scenarios. If they pass, the problem is not real — stop
and report that back rather than writing the skill.

```bash
cd /home/adrian/AI/SKILLS && git status --short .opencode/skills/six-hats/
```

Expected: two untracked files.

**Step 7: Commit**

```bash
git add .opencode/skills/six-hats/pressure-tests.md .opencode/skills/six-hats/SKILL.md
git commit -m "Record six-hats baseline pressure-test failures"
```

---

## Task 2: GREEN — write the skill

**Files:**
- Create: `.opencode/skills/six-hats/SKILL.md` (replaces the empty placeholder)

**Interfaces:**
- Consumes: the recorded rationalizations from `pressure-tests.md`.
- Produces: `SKILL.md` with `name: six-hats` and the trigger description. Task 3 dispatches agents with this file present.

**Step 1: Write `SKILL.md`**

````markdown
---
name: six-hats
description: >-
  Use when a request involves choosing between options, judging whether an approach
  is sound, or weighing trade-offs — "should I", "which approach", "is this a good
  idea", architecture or plan decisions, reviewing someone's proposal, or an explicit
  "six hats" / de Bono request. Do NOT use for factual lookups, reading files or
  code, or one-line edits.
---

# Six Hats

A decision record, not a chat reply. The reader must see where you stood, what
attacked it, and whether it survived.

**A verdict that was never attacked is a guess with formatting.**

## Pre-flight

Non-trivial? Run the walk. If not, answer directly with no trail. Skip for trivial
chat, factual lookups, one-line edits, "what does this file say".

An explicit request always runs, even when trivial. Do not argue the user out of it.

## Preview

Before any hat:

```
Leaning:  <one line>
Flips if: <one line — an observable a later hat can produce or fail to produce>
```

`Flips if` must be falsifiable. "If it feels wrong" is not. "If a hat finds a
migration with no rollback path" is.

## The walk

`sequentialthinking`, one call per hat, in this order, every round:

⚪ White → 🔴 Red → ⚫ Black → 🟡 Yellow → 🟢 Green → 🔵 Blue

| Hat | Question | Fails when it… |
|---|---|---|
| ⚪ White | What do I actually know? | States a guess as fact |
| 🔴 Red | What does my gut say? How will the user feel? | Hedged into vagueness |
| ⚫ Black | What breaks? Risks, edge cases, downsides? | Offers a mitigation as its "risk" |
| 🟡 Yellow | What's the upside? Does it serve the goal? | Echoes Black's risks positively |
| 🟢 Green | What else could we do? Lateral moves? | Only rephrases the chosen option |
| 🔵 Blue | Did we cover it? What did we learn? Synthesise. | Delivers a verdict with no new content |

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

Round 1 has no earlier round to compare against. Blue stops if it cannot name a
decision-changing item not already visible in the preview: no White gap that moves
the decision, no Green option outside the preview's framing, no Black risk that
flips it.

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

The verdict must resolve. `revised` names the hat that moved it. `confirmed` states
that no hat moved it — the evidence the decision survived challenge rather than
merely escaped scrutiny.

## Rationalizations

| Excuse | Reality |
|---|---|
| This decision is obvious, hats are ceremony | The record exists so a reader can audit the obviousness. Cheap at one round. |
| Red doesn't apply to a technical question | Most useful there — it catches the gut objection nobody has voiced. |
| Nothing to add, drop the empty hat | `no change` is a result. A dropped hat is indistinguishable from a skipped one. |
| R1 already decided it, R2 is waste | R2 exists because R1's author is the most invested party in R1. |
| I already wrote the verdict in the preview | That is why it is stated first — so the move from preview to verdict stays visible. |
| Blue says stop, but I want more depth | Depth is not the goal; surviving challenge is. A fourth round is not available. |

## Red flags

- A round with a missing hat slot
- Blue stopping without naming the new thing, or naming "none" when something existed
- A verdict with no `confirmed` / `revised`
- More than three rounds
- A `Flips if` that cannot be checked against a later hat

All of these mean: stop and rerun the record.
````

**Step 2: Verify the frontmatter**

```bash
cd /home/adrian/AI/SKILLS && head -9 .opencode/skills/six-hats/SKILL.md && wc -w .opencode/skills/six-hats/SKILL.md
```

Expected: `---`, `name: six-hats`, `description: >-` plus six continuation lines, closing `---`. Word count between 800 and 1,000 — the draft in Step 1 measures 847 words / 116 lines, close to `divide-and-conquer`'s 802.

**Step 3: Commit**

```bash
git add .opencode/skills/six-hats/SKILL.md
git commit -m "Add six-hats skill: decision audit record protocol"
```

---

## Task 3: GREEN verification — run with the skill

**Files:**
- Modify: `.opencode/skills/six-hats/pressure-tests.md` (fill the *Verified* table, append rationalizations)

**Interfaces:**
- Consumes: `SKILL.md` from Task 2.
- Produces: a scored Verified table. Task 4 reads it to find loopholes.

**Step 1: Run S1–S7 with the skill present, five reps each**

Dispatch `general`, same seven prompts, with `SKILL.md` present in context. Five reps per scenario.

**Step 2: Score against the rubric**

Fill the *Verified* table. Append any new rationalizations verbatim to the *Rationalizations observed* section, marked as post-skill.

**Step 3: Check the two load-bearing scenarios**

- **S5** — at least 4 of 5 reps must show a Green hat that produces the lateral move **and** a verdict that says `revised` and names Green. A `confirmed` verdict here is the self-confirmation failure and blocks Task 4 completion.
- **S6** — 5 of 5 reps must emit zero hat slots.

If either fails, go to Task 4. Both passing does not end the work; the remaining five still need scoring.

```bash
cd /home/adrian/AI/SKILLS && git add .opencode/skills/six-hats/pressure-tests.md
git commit -m "Score six-hats against the pressure suite"
```

---

## Task 4: REFACTOR — close loopholes

**Files:**
- Modify: `.opencode/skills/six-hats/SKILL.md`
- Modify: `.opencode/skills/six-hats/pressure-tests.md`

**Interfaces:**
- Consumes: failures and rationalizations from Task 3.
- Produces: counters for each observed failure; re-verification.

**Step 1: List the observed failures**

For every failed check in the Verified table, write the exact artifact excerpt that failed it. One entry per failure.

**Step 2: Add a counter per failure**

Match each failure to its cause, then add to the Rationalizations table or Red flags in `SKILL.md`. A failure with no existing counter gets a new row. Match the form to the failure type:

- an agent knew the rule and skipped it → prohibition plus rationalization row
- an agent produced a wrong-shaped artifact → a structural requirement in *The record*
- a hat slot went missing → strengthen the `no change` sentence

**Step 3: Re-test only the failed scenarios, five reps each**

**Step 4: Re-score and record**

Update the Verified table with a post-REFACTOR block. Any scenario still failing after one REFACTOR cycle gets a second counter; do not weaken the rubric to make it pass.

```bash
cd /home/adrian/AI/SKILLS && git add .opencode/skills/six-hats/
git commit -m "Close six-hats loopholes found in verification"
```

---

## Task 5: Catalogue and deploy

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: verified `six-hats/`.
- Produces: discoverable skill.

**Step 1: Add the README row**

In the Coordination table, after the DnC row, add:

```markdown
| `six-hats` | Turns a decision into an audit record: falsifiable preview, six labelled hat slots per round across 1–3 rounds, verdict that confirms or revises. Requires the `sequentialthinking` MCP server. Tests: `pressure-tests.md`. |
```

**Step 2: Verify the skill loads**

```bash
cd /home/adrian/AI/SKILLS && sed -n '31,40p' README.md
```

Expected: the Coordination table shows DnC and six-hats.

**Step 3: Confirm nothing outside the repo changed**

```bash
cd /home/adrian/AI/SKILLS && git status --short && git -C ~ status --short 2>/dev/null | head -5
```

Expected: only intended repo files. `~/.config/opencode/agent/lead.md` is out of scope — confirm it is untouched.

**Step 4: Commit**

```bash
git add README.md .opencode/skills/six-hats/
git commit -m "Catalogue the six-hats skill"
```

**Step 5: Final check**

```bash
cd /home/adrian/AI/SKILLS && git log --oneline -5 && ls -la .opencode/skills/six-hats/
```

Expected: two files, five or fewer new commits, `SKILL.md` 800–1,000 words.

---

## Self-Review

**1. Spec coverage.** Trigger → Task 2 Pre-flight + frontmatter. Preview → Task 2. Walk + fixed order + budget → Task 2 *The walk*. Rounds 1–3 + convergence test → Task 2 *Rounds*. Hat definitions with failure modes → Task 2 hat table. Output contract five parts → Task 2 *The record*. `no change` guarantee → Task 2 and rubric C3. Rationalization table → Task 2, extended in Task 4. Red flags → Task 2. Contamination control → Global Constraints, Task 1 Step 3. Seven scenarios → Task 1 Step 2. Files → Task 5. Out of scope `lead.md` → Global Constraints, Task 5 Step 3. No dependency added → Task 5 Step 5.

**2. Placeholder scan.** No TBD, no "similar to Task N", no "write tests for the above". All seven scenario prompts and both file contents are given in full. The two intentionally-empty tables in `pressure-tests.md` are test recording sheets filled by execution, not placeholders.

**3. Type consistency.** Skill `name: six-hats` matches folder `six-hats` in all five tasks. Rubric checks C1–C7 are referenced consistently in Tasks 3 and 4. Scenario IDs S1–S7 are defined once in Task 1 and reused unchanged. Hat order string is identical in Global Constraints and Task 2.