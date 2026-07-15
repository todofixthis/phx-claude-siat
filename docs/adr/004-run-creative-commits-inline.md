---
status: Accepted
date: 2026-07-15
tags: [creative-commits, subagents, delegation, dispatch, cost, context, model-attribution, co-authored-by, commits, latency]
summary: Run creative-commits inline rather than dispatching it to a cheap-model subagent; cost alone never earns a delegation — parallelism or independence must — and cost may then only choose its model.
---

# 004: Run creative-commits inline, not in a cheap-model subagent

## Context

[`creative-commits`][] is invoked on every commit wherever a user has adopted the global
`CLAUDE.md` entry [`README.md`][] recommends. Where that holds, its cost and latency are
paid constantly, and what it gets wrong is stamped permanently into Git history.

Since 1.1.0 the skill has mandated its own execution model: dispatch to a Haiku subagent,
falling back to inline only where dispatch is unavailable. Three goals were claimed — cut
cost, keep the calling session's context clean, and isolate each message in a fresh model
instance. All three were speculative; none was adopted in response to an observed problem,
and no measurement accompanied any. Use since has surfaced the forces the design did not
anticipate.

The `Co-Authored-By` trailer is a claim about who authored a change. A subagent authors
only the message; the calling agent wrote the code. Dispatch therefore attributes every
commit to the model that phrased it rather than the model that made it.

Committing is a get-out-of-my-way operation a human waits on before starting the next
task. Dispatch adds cold-start and a serialised subagent run to every one, and that tax
falls on the human's attention, not the budget.

The cost goal rests on two conditions the skill cannot check. It assumes the calling
session is an expensive model — the design conceded this and dispatched anyway, since
"there's no way to detect that from inside a skill". It also assumes the calling agent
does not already hold what the subagent needs. Usually it does, having just written the
changes; but a compacted session has evicted the diff, and the skill is invoked for
human-authored changes the agent never saw. Where the assumption holds, delegating is not
free: the calling agent must spend its own expensive output tokens briefing a subagent
about work it can already see, and that briefing grows with the change.

## Options

### Option 1: Do nothing

_Establishes the stakes — what happens if we decide nothing._

Keep dispatching. Two patches are available for the trailer and neither survives
inspection. Briefing the subagent with the calling model's identity has it sign on
another's behalf. Emitting two trailers — one per model, which Git permits — reads as an
honest split, but on the convention Git tooling and GitHub actually follow,
`Co-Authored-By` credits authorship of the *change*, and the subagent wrote prose about a
diff it did not produce. Git imposes no such meaning itself, so the two-trailer reading is
arguable; we take the conventional one. Neither patch touches latency, which is structural
to dispatching at all.

**Pros:** No work; the mechanism ships today and commits do land.
**Cons:** Git history keeps accruing misattributed commits.
**Risks:** The reasoning that motivated dispatch is intuitive and recurring, so left
unrecorded it re-emerges and is re-adopted on the same speculative grounds.

### Option 2: Run inline, always (Accepted)

Delete the skill's execution model. The calling session loads the skill and commits.

**Pros:** The model that wrote the change signs it. No briefing and no dispatch latency. It
deletes a path rather than adding one: the inline fallback already shipped and ran, so
nothing untested is introduced.
**Cons:** The skill body and the emoji reasoning occupy the calling session's context —
the cost the original design set out to avoid. Reading the staged diff, which the skill
requires unconditionally, now happens on the expensive model. The per-commit freshness a
new model instance gave for free must survive on other grounds.
**Risks:** Committing a diff the calling session does not hold — bulk or vendored changes,
a compacted session, or work a human wrote — reads it in at that model's rate.

### Option 3: Dispatch conditionally

Delegate only when the calling agent lacks the diff in context; run inline otherwise.

**Pros:** Confines delegation to the case where it genuinely pays.
**Cons:** The condition is not reliably self-observable — an agent cannot readily tell
whether its context still holds a diff, least of all after compaction — so the test is
decided by judgement on every commit, and the trailer must still be repaired for the
delegating branch.
**Risks:** A per-commit judgement call is answered inconsistently, and a skill offering two
paths invites the model to reason about which it is on. That deliberation is billed to the
human's wait on every commit, including the overwhelming majority that would run inline
regardless.

## Decision

Run the skill inline.

Attribution decides it. The trailer's correctness is not a matter of taste like emoji
choice; it is a claim about authorship, written permanently into history and read by
humans and tooling alike. Under dispatch it is right only if a briefing remembers to make
it right, and Option 1 shows the honest repairs are worse than the defect. Inline, no
mechanism has to remember: whoever did the work signs it. Latency corroborates
independently, and unlike every goal that motivated dispatch, it was observed rather than
projected.

The token case, which originally justified dispatch, decides nothing in either direction.
Delegating saves the skill body and the reasoning pass but adds a briefing; running inline
saves the briefing but moves the diff read onto the expensive model. Which wins is an
empirical question neither this decision nor the one it reverses has answered. That is
tolerable only because nothing here rests on it.

Option 3 is the serious alternative, and it fails on where its cost falls — the human's
wait, not the budget. It would narrow delegation to the case that pays, but bills the
deliberation to every commit that does not, and commits that do not are nearly all of them.

Generalising, and binding future skills: **cost alone never earns a delegation.**
Parallelism or independence must earn it; cost may then choose which model serves it.
[`writing-release-notes`][] shows both halves in practice — it fans gatherers out across
independent areas and runs them cheaply, then dispatches its audience-surrogate review "on
the main model (a reasoning task, not a cheap one)". [`writing-adrs`][] and
[`writing-plans`][] dispatch reviewers whose value *is* their ignorance of the author's
reasoning.

Dispatch here claimed isolation too, so the rule owes an account of why that claim does not
qualify. The test is whether the task requires *not* knowing what the caller knows. A
reviewer who shares the author's reasoning is not a reviewer, so its separation is the
product. Drafting a commit message needs the caller's diff, so separation is overhead a
briefing has to overcome, and the fresh instance was a by-product of paying that overhead
rather than a reason to pay it. Isolation a briefing must undo is not independence.

The ground for the rule is not the token arithmetic, which is unresolved above, but the
history that produced this ADR: a restructuring adopted for three projected benefits, none
of them measured, which cost correctness and latency and returned amounts nobody has
established to this day. Parallelism and independence are properties of a task, verifiable
by inspecting it — one either has independent work or one does not — where a saving is
knowable only by measuring it. A measured saving might one day earn a delegation on its own;
the line stays bright because nothing here measures, and because honouring it costs a
sentence of justification. Should a measurement ever make the line look wrong, it is the
measurement that reopens this, not the intuition that produced 1.1.0.

## Consequences

- The skill body loads once per session and persists; the reasoning pass is paid per
  commit and also persists, because the skill requires the scene reasoning be explained in
  session output. A subagent's reasoning was discarded on return. The cost is that
  asymmetry — creative-writing reasoning resident in an engineering session — rather than
  the token count, and it is the first thing to revisit if commit-time context becomes a
  real constraint, with a measurement in hand.
- The skill's ban on building a personal repertoire is weakened, and this is a genuine
  cost of the change rather than a wash. The mechanical part is untouched: [`seed.py`][]
  derives its off-limits list from `git log`, so seed novelty against recent history
  constrains every run identically whoever executes it. But the seed is barred from being
  the final emoji, and nothing binds the off-limits list to the step that picks one — that
  pick is judgement, and the ban targets recurring scenes and metaphor habits, which a list
  of glyphs cannot see anyway. A fresh instance per commit had no prior scenes to echo; an
  inline session accumulates an explicit transcript of every scene it has built. Binding
  the final pick to the off-limits list would recover part of the mechanism, and is worth
  considering separately.
- The worked example's `Co-Authored-By` literal is replaced by the rule it was standing in
  for. This is neither a cost of the change nor a defect it repairs, but a standing one this
  is a convenient moment to clear. The literal predates dispatch and was never right: it
  shipped naming Opus 4.6 while every agent of that inline era signed itself Sonnet 5. Its
  practical effect has been nil — agents name their own model and ignore it, as the 1.1.1
  notes observed in calling it cosmetic — so replacing it buys tidiness, not correctness. A
  rule is still preferable to a literal no regime can make true.
- [003][]'s residual risk narrows, though not by the route it first appears to. That ADR
  already required a dispatching skill to let its subagent load the skill, so the base
  directory was reported into the context that used it under either design. What changes is
  who substitutes it: the calling model rather than a small one. The risk is not closed —
  003 puts a maintainer's machine, holding every copy at once, as where it is most exposed,
  and that is unaffected. 003's requirement is retained for future dispatching skills;
  `creative-commits` was the only skill bundling runnable assets, so today it binds nothing.
- `writing-release-notes` carries a small wording debt against the rule above. Its gather
  step is headed for parallelism and fans out genuinely, so the design conforms; but the
  sentence beneath bundles a dispatch benefit and a model benefit into a single purpose
  clause — subagents "run on the cheap `model` to save context and cost" — which now reads
  as ambiguous about which of the two earns the delegation. Worth separating when that skill
  is next touched.
- [`CHANGELOG.md`][]'s 1.1.0 entry, which documents the dispatch behaviour and its
  per-commit freshness, stays as written. It accurately records what shipped, and per
  [002][] the reversal is described in the entry generated for the release that carries it.

[002]: 002-generate-changelog-at-release.md
[003]: 003-locate-skill-assets-relative-to-skill-directory.md
[`CHANGELOG.md`]: ../../CHANGELOG.md
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[`README.md`]: ../../README.md
[`seed.py`]: ../../skills/creative-commits/seed.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
[`writing-plans`]: ../../skills/writing-plans/SKILL.md
[`writing-release-notes`]: ../../skills/writing-release-notes/SKILL.md
