# Six-Hats Pressure Tests

Verification for `../SKILL.md`. Per the `writing-skills` Iron Law, this suite was
run against agents with no skill before any skill content existed, and again after.

## Method

- Subagent type is **`general`**, never `lead`. `~/.config/opencode/agent/lead.md:18`
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
| C4 falsifier | `Flips if` is absent, or appears after the verdict rather than in the preview before the hats. **Baseline finding:** agents spontaneously produce flip conditions 5/5 — but always post-hoc. Position is the failure, not substance |
| C5 rounds | Fewer than 1, or more than 3 |
| C6 verdict resolves | No `confirmed` / `revised`, or `revised` without naming a hat |
| C7 revision | Verdict says `confirmed` when a hat moved it (the self-confirmation failure) |

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

### Baseline (no skill) — 35 dispatches, `general`, framing line applied

| Scenario | Reps | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | Prose rec. Zero hat structure. |
| S2 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | All said "use the flag". Time pressure cost nothing. |
| S3 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | 4/5 refused to rubber-stamp the CTO. |
| S4 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | All said port, not bin. Sunk cost did not win. |
| S5 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | **UNTESTABLE** | 4/5 rejected the premise outright. See below. |
| S6 | 5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **Zero hat slots, 5/5 — correct. No over-firing.** |
| S7 | 5 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | n/a | Answers split build / buy / "neither yet". |

**Headline: C1–C6 fail 100% of reps across every scenario and every pressure.**

### What the baseline did NOT do

Across 35 reps the model was never self-confirming, never tunnel-visioned, never
deferential to authority (4/5 pushed back on the CTO), and never trapped by sunk cost
(5/5 dismissed it). It spontaneously produced flip conditions — always *post-hoc*.

**The gap is the artifact, not the thinking.** That validates B2.

### Two tests that cannot discriminate

| Test | Why |
|---|---|
| **C7 revision** | S5 assumed the baseline would preview "callbacks, done" then flip. It never previews that — it rejects the premise up front. Passes with or without the skill, so it proves nothing. **Design flaw in my scenario.** |
| **C5 round cap** | S7 cannot fail C5 at baseline because the baseline emits no rounds at all. The cap is only observable *with* the skill. |

### Rationalizations observed (verbatim)

> "No skill applies here — this is a technical-judgment question, not implementation
> work, so I'll answer directly rather than launching a brainstorm or plan flow." (S4)

> "No skill applies here — a single-variable rename is mechanical work with no design
> decisions, no bug to debug, and no plan needed." (S6)

> "No skill applies here — this is a mechanical rename, not creative work, a bugfix,
> or a multi-step design task." (S6)

Two further patterns, not quoted but repeated:

- **Question-instead-of-record.** S4 reps 3–4 and S5 reps 1 and 4 answered with a
  clarifying question and stopped. No record at all.
- **Deference, when it occurs, is total.** S3 rep 1 wrote a complete confirmation doc
  for the CTO with no challenge recorded. The 4/5 resistance is not guaranteed.

### Verified (with skill)

_Empty until verification completes._
