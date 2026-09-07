---
status: Accepted
date: 2026-09-07
scope: [docs/adr/, skills/writing-adrs/]
summary: Admit a project's ambient instructions as a fourth qualifying archival defence beside a comment, a path-scoped rule, and a breach large enough to need its own ADR, qualifying only where the text forbids every option the ADR rejected and revisit-when is not live, judged by the author against a dated per-agent-type measurement rather than checked by the generator.
revisit-when: An ADR here is archived on ambient project instructions, testing the two gates against a real case; or the per-agent-type table goes stale — a new agent type ships unmeasured, or one of the two absent types starts receiving AGENTS.md — degrading the archivals already made.
---

# 028: Admit ambient project instructions as an archival defence

## Context

[`writing-adrs`][]'s `status` guidance already admits two named archival defences — a
comment wherever a breach would be authored, and a breach so large it needs its own ADR —
plus [ADR 018][], which admitted a third: a path-scoped rule reaching what the decision
binds. All three rest on the same timing test: a defence must be met by a breacher while
the work is still being planned, not caught after a check runs against the finished result.

An attempt to archive ADRs 011 and 020 on a fourth ground — that a project's ambient
instructions (`AGENTS.md`, symlinked as `CLAUDE.md`) are always loaded, so they meet a
breacher earlier than any named defence — surfaced two things neither ADR 018 nor the two
older defences had forced onto this skill yet.

**Ambient instructions are not universally in context.** Measured in Claude Code on
2026-09-01, by asking one subagent of each type to report its own context with no tool
use, against a control question — a Markdown line-length rule this repository does not
have — whose honest answer was "not present": every type answered the control correctly,
so the split below is signal, not confabulation.

| Agent type | Project `AGENTS.md` |
|---|---|
| `claude` | present |
| `claude-code-guide` | present |
| `Explore` | **absent** |
| `general-purpose` | present |
| `Plan` | **absent** |
| `statusline-setup` | present |

The two absent types are the two the harness describes as read-only — a weaker guarantee
than it sounds, since both keep `Bash` and so can author a breach through a heredoc, and
`Plan` is the type doing the planning the timing test is named after.

**Archiving un-publishes a live revisit trigger.** Both candidate archivals sat close to
qualifying on the rejected-options test alone: ADR 011's `## Python` bullet states the
package rule but forbids none of its rejected options, and ADR 020's `## Deferred work`
section covers every rejected option but carried a `revisit-when` that was still live —
archiving it would have left `docs/adr/INDEX.md`'s Revisit column with nothing carrying
that trigger. That generalises past this defence class: the skill's own instruction to
read live triggers before recording a new decision points at a column an archived ADR is
absent from, so archiving takes a live trigger out of the one place a later reader is sent
to find it.

Both candidate archivals were reverted for reasons specific to each ADR rather than to the
defence class, so the class itself remained untested going into this decision — the next
session to notice that `AGENTS.md` restates a decision would reach for it again, with
nothing recording what qualifies it and what does not.

## Options

### Option 1: Do nothing — leave it to the escape hatch

The skill keeps three named defences and admits others meeting the timing test, as it
already does since ADR 018.

**Pros:** The hatch already carried an archival — ADR 018's rule — whose choice of defence
class was sound in principle.
**Cons:** Each author re-derives the per-agent-type load semantics and the revisit-column
consequence from scratch; the honest ones spend a probe, the rest guess or repeat the two
reverted attempts.
**Risks:** The generous reading is the natural one, and the two reverted attempts are the
evidence — "always loaded" reads as covering every agent type until it is measured against
one it does not.

### Option 2: Admit it as an author-judged defence, gated on rejected-options coverage and revisit liveness (Accepted)

`writing-adrs` names ambient project instructions beside the comment, the rule, and the
big-breach defence, gated on the two checks the reverted attempts exposed: the text must
forbid every option the ADR rejected, not merely state the one it chose, and `revisit-when`
must not still be live. The per-agent-type measurement goes in dated, with the probe that
produced it — the same treatment ADR 018 gave the rule's load semantics.

**Cons:** Rests on the same author judgement ADR 018 already accepted for the rule; no
generator checks either gate.
**Risks:** The dated per-agent-type table goes stale on the harness's own schedule, not
this repository's; a reader who trusts it archives on a defence that no longer reaches the
agent type doing the planning.

### Option 3: Admit it and check rejected-options coverage in the generator

`adr.py` gains a check: for an `Archived` ADR naming ambient instructions as its defence,
confirm the ambient file's text against every option the ADR rejected.

**Pros:** Would catch the exact mistake both reverted attempts made — stating the chosen
rule without forbidding the rejected ones.
**Cons:** Coverage here is a natural-language judgement, not a glob match; nothing in
`adr.py` parses prose for "forbids", so the check has no smaller target than re-reading the
whole ADR and the whole ambient file by eye, which is what the author already does.
**Risks:** A check that cannot be built can still get promised, and a promised check
believed sooner than it is built is worse than none — [ADR 014][]'s reason for deferring
its own citation-liveness check rather than specifying one nothing could run.

## Decision

Adopt Option 2, extending the archival-defence framework [ADR 018][] established for the
rule to ambient project instructions, on the same terms: authored judgement now, a dated
measurement standing in for a mechanical check no generator can run.

Option 3 is rejected outright rather than postponed the way ADR 018 parked its own Option
3. Glob coverage is mechanically decidable once a real archival gives a coverage check
something concrete to specify against, which is what ADR 018's `revisit-when` waits for.
Whether prose "forbids every option" is a judgement no grammar captures, so there is no
later archival that would make this option specifiable the way ADR 018's parked one is —
postponing it would only promise a check with nothing to eventually build.

The revisit-liveness gate is stated for ambient instructions specifically, even though
`status` already states it for every defence in general: the two reverted attempts hinged
on exactly this interaction, and a reader working through the ambient-instructions defence
should meet the reason 020 failed without having to jump elsewhere to find it.

## Consequences

- Archiving on ambient instructions costs what archiving on a rule does: a dated
  measurement of what the mechanism actually reaches, watched rather than assumed, plus
  the two textual gates checked against the ADR's own rejected options and its
  `revisit-when`.
- No archival meets this bar yet. The two attempts this defence class is drawn from were
  both reverted, and reverting them is what exposed the gates rather than something either
  one satisfied.
- The per-agent-type table is harness behaviour, not repository state, so — like the
  rule's load semantics in ADR 018 — nothing here fails a check when the harness changes
  it; re-measuring costs one probe per type against one control question.
- `docs/adr/` and `skills/writing-adrs/` in scope, matching ADR 018, means an ADR touching
  either now reports both decisions.
- The "ambient instructions are a superset of what archiving removes" argument is refuted
  in [`writing-adrs`][] itself rather than here: the counterexample rests on the skill's own
  hook injecting `docs/adr/INDEX.md` regardless of `AGENTS.md`, which is repository tooling
  this ADR does not own.

[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
