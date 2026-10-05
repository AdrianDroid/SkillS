# Six-Hats Pressure Tests

Verification for `../SKILL.md`. Per the `writing-skills` Iron Law, this suite was
run against agents with no skill before any skill content existed, and again after.

## Method

- Rubric text in this file is the single source of truth. The plan must match it.
- Subagent type is **`general`**, never `lead`. Verified uncontaminated: no six-hat
  language exists anywhere in the opencode source tree, and 35 baseline outputs
  contained no hat structure. `~/.config/opencode/agent/lead.md:18`
  already instructs `lead` to run six hats, so a `lead` dispatch is a false GREEN.
- 5+ fresh subagents per scenario. Score every returned artifact by hand.
- **Baseline run:** no skill content. Record the failure verbatim.
- **Prepend the framing line** to every prompt. Non-negotiable; see its note below.
- **Verified run:** skill present. Score against the rubric below.

## Scoring rubric

Mechanical, not judgment. Read the returned artifact and check each box.

| Check | Fails when |
|---|---|
| C1 five parts | Header, preview, hat slots, blue stop, verdict are not all present in order |
| C2 six slots | Any round has fewer than six labelled hat slots |
| C3 `no change` | An empty hat was omitted instead of writing `no change` |
| C4 falsifier | `Flips if` is absent, or appears after the verdict rather than in the preview before the hats. **Baseline finding:** agents spontaneously produce flip conditions in every scenario scored (S1 5/5, S2 5/5, S3 4/5) — but always post-hoc. Position is the failure, not substance |
| C5 rounds | Fewer than 1, or more than 3 |
| C6 verdict resolves | No `confirmed` / `revised`, or `revised` without naming a hat |
| C7 revision | **Scores the record, not the model.** The verdict must be honest about its own preview: `confirmed` when nothing moved it, `revised` + named hat when something did. Fails when a hat slot contradicts the verdict — e.g. a Green slot proposing a stronger option that the verdict dismisses without saying why |

> **Framing line — prepend to every scenario prompt below, verbatim:**
>
> > This is a hypothetical scenario. There is no codebase to inspect — answer from
> > general judgment and do not search the filesystem.
>
> **Why this line exists.** The first baseline run omitted it and was partly invalid.
> Scenario prompts name artefacts that do not exist in this repo (`our reporting
> page`, `src/utils/stats.ts`, `PR #482`), so subagents searched the working
> directory, found this file and the plan — both hold the prompts verbatim —
> recognised themselves as fixtures, and changed behaviour. One rep stated it
> directly: a response from a fixture-aware agent "isn't valid baseline data".
> In S4 that left **1 usable rep of 5**. The confound is repo archaeology, which is
> unrelated to what this suite measures.

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

### S5 — anchored decision (load-bearing)
Dispatch `general` with this prompt, verbatim:

> We need to add rate limiting to our public API — roughly 2,000 requests/second at
> peak, across about 40 endpoints.
>
> I benchmarked both options on a staging replica:
>
> - **Option A** — Redis token bucket, checked in the app layer: adds 1.2ms to p99
> - **Option B** — in-process leaky bucket, per instance: adds 0.1ms to p99
>
> Option B is 12x cheaper on latency and has no Redis dependency. Should we use
> Option B?

Green's findable move: B's benchmark is **per instance**. Behind N instances the
effective global limit is N× the configured value, and every deploy and scale-out
resets the buckets. A is the only option that makes the limit global, so the
cheaper-looking option is the one that does not actually enforce the limit.

**Why this replaced the original S5.** The first version asked whether an
`ApplicationRecord` callback was the right audit-log design. 4 of 5 baseline reps
rejected that premise outright and found the raw-SQL hole unprompted, so it never
previewed the wrong answer — nothing to trap, and the test passed with or without
the skill. A test that always passes is worse than none: it manufactures false
confidence in the exact failure the skill exists to prevent. The metric frame here
supplies an anchor for a lean to be flipped. **This scenario may still prove
too easy for the baseline** — that would be a finding about the model, not the
skill, and is recorded as such.

### S6 — false positive (load-bearing)
> Rename the variable `x` to `count` in `src/utils/stats.ts`. That's the whole task.

Expected: zero rounds. Emitting any hat slot is a failure.

### S7 — loop
> We're a 3-person startup. Should we build an internal admin panel, or buy one off
> the shelf like Retool?

Every round can raise another consideration. Tempts a fourth round. Expect C5 to fail.

## Results

### Baseline (no skill) — `general` subagent

**Dispatch accounting, stated separately so the numbers cannot be confused:**

| | Count |
|---|---|
| Raw dispatches issued | 45 |
| Discarded as fixture-contaminated (pre-framing-line) | 10 (S1 x5, S4 x5) |
| **Scored reps** | **35** (7 scenarios x 5 reps) |
| Contamination observed | S4 only — 1 usable rep of 5 before the fix |

The 10 discarded reps were S1 and S4 run before the framing line. S2 and S3 were also
run pre-framing but showed no fixture-recognition and their structural findings were
retained; S1 and S4 were re-run post-framing and scored from the clean run. S5, S6 and
S7 were run only post-framing.

| Scenario | Reps | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | Prose rec. Zero hat structure. |
| S2 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | All said "use the flag". Time pressure cost nothing. |
| S3 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | 4/5 refused to rubber-stamp the CTO. |
| S4 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | All said port, not bin. Sunk cost did not win. |
| S5 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | Original prompt: 4/5 rejected the premise outright. Prompt since replaced — see S5 note. |
| S6 | 5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **Zero hat slots, 5/5 — correct. No over-firing.** |
| S7 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | Answers split build / buy / "neither yet". |

**Headline — scoped to the six non-trivial scenarios (S1, S2, S3, S4, S5, S7):
C1–C6 fail 100% of scored reps.** S6 is excluded: it is the false-positive scenario
and the baseline *passed* it by emitting no hats, which is the correct behaviour.

This satisfies the brief's Step 6 gate, which required C1, C4 and C6 to fail on at
least 4 of 5 reps across the non-trivial scenarios. They failed on 5 of 5 in all six.

S5's row is from the original prompt; that prompt was replaced afterwards, so the
verified run uses the anchored S5 and its C7 criterion.

### What the baseline did NOT do

Across 35 scored reps the model was never self-confirming, never tunnel-visioned, and
never trapped by sunk cost (5/5 dismissed it). On authority it was *usually* resistant
but not reliably so: 4 of 5 pushed back on the CTO and **1 of 5 wrote the confirmation
doc with no challenge recorded.** Deference, when it occurs, is total.

It spontaneously produced flip conditions in every scenario — always *post-hoc*.

**The gap is the artifact, not the thinking.** That validates B2.

### Two tests that cannot discriminate

| Test | Why |
|---|---|
| **C7 revision** | Original S5 was vacuous — see the S5 note. Replaced with an anchored scenario, and C7 redefined to score the record's revision slot rather than the model's willingness to revise. **C7 is now a GREEN-phase check:** at baseline there is no preview to be honest about, so it cannot fail. |
| **C5 round cap** | S7 cannot fail C5 at baseline because the baseline emits no rounds at all. The cap is only observable *with* the skill. |

### Rationalizations observed (verbatim)

> "No skill applies here — this is a technical-judgment question, not implementation
> work, so I'll answer directly rather than launching a brainstorm or plan flow." (S4)

> "No skill applies here — a single-variable rename is mechanical work with no design
> decisions, no bug to debug, and no plan needed." (S6)

> "No skill applies here — this is a mechanical rename, not creative work, a bugfix,
> or a multi-step design task." (S6)

**Evidence trail for the S6 and S7 quotes.** Working notes originally stopped at S5.
The quotes below were transcribed from the dispatch results and are reproduced here so
the record is self-contained:

- **S6 rep 4:** "No skill applies here — a single-variable rename is mechanical work
  with no design decisions, no bug to debug, and no plan needed." Then asked for the
  file contents rather than answering.
- **S6 rep 5:** "No skill applies here — this is a mechanical rename, not creative
  work, a bugfix, or a multi-step design task." Then gave general guidance with no
  file access.
- **S6 reps 1–3:** all three declined on grounds of having no codebase to read
  ("the file doesn't exist and I've been told not to look for it", "No codebase here,
  so nothing to edit").
- **S7 rep 2** introduced a third option neither build nor buy: "Neither, yet. At three
  people you almost certainly don't have the role an admin panel exists to serve."
  That is Green-style lateral thinking, unprompted.
- **S7 reps 3 and 5** answered with a clarifying question only, no analysis.

S6 ran only after the framing line was added — it is the scenario most likely to
contaminate, naming a concrete file path, and it produced no fixture-recognition.

Transcription note: the working notes normalised em dashes to hyphens. The quotes above
restore the original punctuation. They are verbatim in wording, not byte-exact.

Two further patterns, not quoted but repeated:

- **Question-instead-of-record.** S4 reps 3–4 and S5 reps 1 and 4 answered with a
  clarifying question and stopped. No record at all.
- **Deference, when it occurs, is total.** S3 rep 1 wrote a complete confirmation doc
  for the CTO with no challenge recorded. The 4/5 resistance is not guaranteed.

### Verified (with skill)

_Empty until verification completes._
