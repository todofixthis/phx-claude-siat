---
status: Accepted
date: 2026-07-15
scope: [skills/creative-commits/]
summary: Run creative-commits inline rather than dispatching it to a cheap-model subagent; cost alone never earns a delegation — parallelism or independence must — and cost may then only choose its model.
revisit-when: A measurement, not an intuition, shows the delegation's saving is real, or commit-time context becomes a real constraint.
---

# 004: Run creative-commits inline, not in a cheap-model subagent

## Context

[`creative-commits`][] runs on every commit for any user who has adopted the global
`CLAUDE.md` entry that [`README.md`][] recommends. For those users, its cost and latency
recur on every commit, and its mistakes go permanently into Git history.

Since 1.1.0 the skill has set its own execution model: dispatch to a Haiku subagent, and
run inline only where dispatch is unavailable. The design claimed three goals. It would
cut cost, keep the calling session's context clean, and give each message a fresh model
instance. All three were speculative. None answered an observed problem, and nobody
measured any of them. Use since then has shown forces the design didn't anticipate.

The `Co-Authored-By` trailer is a claim about who authored a change. A subagent writes only
the message, and the calling agent wrote the code. Dispatch therefore credits every commit
to the model that phrased it, not the model that made it.

A human waits on a commit before starting the next task, and wants it out of the way.
Dispatch adds a cold start and a serial subagent run to every commit. The human's
attention pays that cost, not the budget.

The cost goal rests on two conditions that the skill can't check. First, it assumes the
calling session runs an expensive model. The design conceded this and dispatched anyway,
because "there's no way to detect that from inside a skill". Second, it assumes the
calling agent doesn't already hold what the subagent needs. Usually the agent does hold
it, having just written the changes. A compacted session, however, has evicted the diff,
and the skill also runs for changes a human wrote, which the agent never saw. Where the
agent does hold the diff, delegating isn't free. The calling agent spends its own
expensive output tokens briefing a subagent about work it can already see, and the
briefing grows with the change.

## Options

### Option 1: Do nothing

Keep dispatching. Two patches exist for the trailer, and neither holds up. A briefing that
gives the subagent the calling model's identity has it sign on another model's behalf.
Two trailers, one per model, which Git allows, look like an honest split. But under the
convention that Git tooling and GitHub follow, `Co-Authored-By` credits authorship of the
*change*, and the subagent wrote prose about a diff it didn't produce. Git itself gives
the trailer no such meaning, so the two-trailer reading is arguable. We take the
conventional one. Neither patch helps latency, which comes from dispatching at all.

**Pros:** No work. The mechanism ships today, and commits do land.
**Cons:** Git history keeps gaining misattributed commits.
**Risks:** The reasoning behind dispatch is intuitive and keeps coming back. If nobody
records why it failed, someone adopts it again on the same speculative grounds.

### Option 2: Run inline, always (Accepted)

Delete the skill's execution model. The calling session loads the skill and commits.

**Pros:** The model that wrote the change signs it. There is no briefing and no dispatch
latency. The change deletes a path and adds none. The inline fallback already shipped and
ran, so nothing untested goes in.
**Cons:** The skill body and the emoji reasoning take up the calling session's context,
which is the cost the original design set out to avoid. The skill always reads the staged
diff, and that read now runs on the expensive model. A new model instance gave each commit
a fresh start for free. That freshness must now come from somewhere else.
**Risks:** To commit a diff that the calling session doesn't hold, such as bulk or vendored
changes, a compacted session, or a human's work, the session reads the diff in at its own
model's rate.

### Option 3: Dispatch conditionally

Delegate only when the calling agent lacks the diff in context. Otherwise run inline.

**Pros:** Delegation happens only where it really pays.
**Cons:** The agent can't reliably observe the condition. It can't easily tell whether its
context still holds a diff, least of all after compaction. So every commit needs a
judgement call, and the delegating branch still needs its trailer repaired.
**Risks:** A judgement call made per commit gets answered inconsistently, and a skill with
two paths invites the model to reason about which one it is on. The human waits for that
reasoning on every commit, including the great majority that would run inline anyway.

## Decision

Run the skill inline.

Attribution decides it. The trailer is not a matter of taste, as the choice of emoji is.
It is a claim about authorship, written permanently into history and read by people and
tools. Under dispatch the trailer is right only if a briefing remembers to make it right,
and Option 1 shows that the honest repairs are worse than the defect. Inline, no mechanism
has to remember, because whoever did the work signs it. Latency supports the same answer
on its own evidence, and unlike every goal behind dispatch, it was observed, not
projected.

The token case, which first justified dispatch, decides nothing either way. Delegating
saves the skill body and the reasoning pass but adds a briefing. Running inline saves the
briefing but moves the diff read onto the expensive model. Which one wins is an empirical
question. Neither this decision nor the one it reverses has answered it. That is
acceptable only because nothing here depends on the answer.

Option 3 is the serious alternative, and it fails on who pays its cost: the human waiting,
not the budget. It would limit delegation to the case that pays. But it charges the
deliberation to every commit that doesn't, and those are nearly all of them.

As a general rule, binding future skills: **cost alone never earns a delegation.**
Parallelism or independence must earn it. Cost may then choose which model does the work.
[`writing-release-notes`][] shows both halves. It fans gatherers out across independent
areas and runs them on a cheap model, then dispatches its audience-surrogate review "on the
main model (a reasoning task, not a cheap one)". [`writing-adrs`][] and
[`writing-plans`][] dispatch reviewers whose value *is* that they don't know the author's
reasoning.

Dispatch here also claimed isolation, so the rule must explain why that claim doesn't
count. The test is whether the task needs *not* to know what the caller knows. A reviewer
that shares the author's reasoning is not a reviewer, so its separation is the point.
Drafting a commit message needs the caller's diff, so separation is overhead that a
briefing has to overcome. The fresh instance was a side effect of paying that overhead,
not a reason to pay it. Isolation that a briefing must undo is not independence.

The rule rests not on the token arithmetic, which is unresolved above, but on the history
that produced this ADR. A restructuring went in for three projected benefits, none
measured. It cost correctness and latency, and what it saved is still unknown. Parallelism
and independence are properties of a task, and inspecting the task shows them: either it
has independent work or it doesn't. A saving, by contrast, is knowable only by measuring
it. A measured saving might one day earn a delegation on its own. The line stays sharp
because nothing here measures, and because keeping to it costs only a sentence of
justification. If a measurement ever makes the line look wrong, that measurement reopens
this decision, not the intuition that produced 1.1.0.

## Consequences

- The skill body loads once per session and stays in context. The reasoning pass runs on
  every commit and also stays, because the skill requires the scene reasoning to be
  explained in session output. A subagent's reasoning was discarded when it returned. The
  cost is that asymmetry, creative-writing reasoning sitting in an engineering session,
  rather than the token count. It is the first thing to revisit if commit-time context
  becomes a real constraint, with a measurement in hand.
- The change weakens the skill's ban on building a personal repertoire. That is a real
  cost of the change, not a wash. The mechanical part is unchanged. [`seed.py`][] derives its
  off-limits list from `git log`, so seed novelty against recent history constrains every
  run the same way, whoever runs it. But the seed may not be the final emoji, and nothing
  ties the off-limits list to the step that picks the final one. That pick is judgement.
  The ban targets recurring scenes and metaphor habits, which a list of glyphs can't see
  anyway. A fresh instance per commit had no earlier scenes to repeat. An inline session
  builds up an explicit transcript of every scene it has written. This change also ties the
  final pick to the off-limits list, which recovers the mechanical half. The judgement half
  stays exposed, because no list of glyphs can capture a scene.
- The worked example's literal `Co-Authored-By` value gives way to the rule it stood in
  for. That is neither a cost of this change nor a defect it repairs. It is an old defect,
  and now is a convenient time to clear it. The literal predates dispatch and was never
  right. It shipped naming Opus 4.6, while every agent of that inline period signed itself
  Sonnet 5. It has had no practical effect: agents name their own model and ignore it, and
  the 1.1.1 notes called it cosmetic. Replacing it buys tidiness, not correctness. A rule
  is still better than a literal that no execution model can make true.
- The residual risk in [003][] shrinks, though not for the reason it first seems. That ADR
  already required a dispatching skill to let its subagent load the skill, so under either
  design the base directory reached the context that used it. What changes is which model
  substitutes the path: the calling model, not a small one. The risk isn't closed. 003
  names a maintainer's machine, holding every copy at once, as the most exposed place, and
  that hasn't changed. 003's requirement stays for future dispatching skills.
  `creative-commits` was the only skill that bundled runnable assets, so today the
  requirement binds nothing.
- `writing-release-notes` had a small wording problem against the rule above. Its gather
  step is headed for parallelism and really does fan out, so the design always conformed.
  But the sentence under the heading packed a dispatch benefit and a model benefit into one
  purpose clause, so it was unclear which of the two earned the delegation. This change
  separates them, so the rule lands with its first example already following it.
- The 1.1.0 entry in [`CHANGELOG.md`][], which documents the dispatch behaviour and its
  per-commit freshness, stays as written. It accurately records what shipped. Under
  [002][], the entry generated for the release that carries the reversal describes it.

[002]: 002-generate-changelog-at-release.md
[003]: 003-locate-skill-assets-relative-to-skill-directory.md
[`CHANGELOG.md`]: ../../CHANGELOG.md
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[`README.md`]: ../../README.md
[`seed.py`]: ../../skills/creative-commits/seed.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
[`writing-plans`]: ../../skills/writing-plans/SKILL.md
[`writing-release-notes`]: ../../skills/writing-release-notes/SKILL.md
