---
status: Accepted
date: 2026-09-07
scope: [docs/adr/, skills/writing-adrs/]
summary: Admit a project's ambient instructions as a fourth qualifying archival defence beside a comment, a path-scoped rule, and a breach large enough to need its own ADR, qualifying only where the text forbids every option the ADR rejected and revisit-when is not live, judged by the author against a dated per-agent-type measurement rather than checked by the generator.
revisit-when: An ADR here is archived on ambient project instructions, testing the two gates against a real case; or the per-agent-type table goes stale — a new agent type ships unmeasured, or one of the two absent types starts receiving AGENTS.md — degrading the archivals already made.
---

# 028: Admit ambient project instructions as an archival defence

## Context

The `status` guidance in [`writing-adrs`][] already admits two named archival defences: a
comment wherever a breach would be authored, and a breach so large it needs its own ADR.
[ADR 018][] admitted a third: a path-scoped rule that reaches what the decision binds. All
three rest on the same timing test. A breacher must meet the defence while the work is
still being planned, not after a check runs against the finished result.

An attempt to archive ADRs 011 and 020 used a fourth ground. A project's ambient
instructions (`AGENTS.md`, symlinked as `CLAUDE.md`) are always loaded, the argument went,
so they meet a breacher earlier than any named defence. The attempt surfaced two things
that neither ADR 018 nor the two older defences had yet forced onto this skill.

**Ambient instructions are not universally in context.** This was measured in Claude Code
on 2026-09-01. One subagent of each type reported its own context with no tool use. Each
also answered a control question about a Markdown line-length rule this repository does
not have, whose honest answer was "not present". Every type answered the control
correctly, so the split below is signal, not confabulation.

| Agent type | Project `AGENTS.md` |
|---|---|
| `claude` | present |
| `claude-code-guide` | present |
| `Explore` | **absent** |
| `general-purpose` | present |
| `Plan` | **absent** |
| `statusline-setup` | present |

The two absent types are the two the harness describes as read-only. That guarantee is
weaker than it sounds. Both types keep `Bash`, so either can author a breach through a
heredoc. `Plan` is also the type that does the planning the timing test is named after.

**Archiving un-publishes a live revisit trigger.** On the rejected-options test alone,
both candidate archivals came close to qualifying:

- ADR 011's `## Python` bullet states the package rule, but forbids none of its rejected
  options.
- ADR 020's `## Deferred work` section covers every rejected option, but ADR 020 carried a
  `revisit-when` that was still live. Archiving ADR 020 would have left nothing in the
  Revisit column of `docs/adr/INDEX.md` carrying that trigger.

The problem reaches past this defence class. The skill tells authors to read live
triggers before recording a new decision, and points them at a column that leaves out
archived ADRs. Archiving therefore removes a live trigger from the one place a later
reader is sent to find it.

Both candidate archivals were reverted for reasons specific to each ADR, not to the
defence class. The class itself was therefore untested going into this decision. The next
session to notice that `AGENTS.md` restates a decision would reach for the class again,
with nothing to record what qualifies it and what does not.

## Options

### Option 1: Do nothing — leave it to the escape hatch

The skill keeps three named defences, and admits others that meet the timing test, as it
has since ADR 018.

**Pros:** The escape hatch has already carried an archival, ADR 018's rule, whose choice
of defence class was sound in principle. **Cons:** Each author works out the
per-agent-type load behaviour and the effect on the Revisit column from scratch. The
careful ones spend a probe. The rest guess, or repeat the two reverted attempts.
**Risks:** The generous reading is the natural one, and the two reverted attempts are the
evidence. "Always loaded" reads as covering every agent type until someone measures it
against a type it does not cover.

### Option 2: Admit it as an author-judged defence, gated on rejected-options coverage and revisit liveness (Accepted)

`writing-adrs` names ambient project instructions beside the comment, the rule, and the
big-breach defence. Two gates apply, the two checks the reverted attempts exposed:

- The text must forbid every option the ADR rejected, not merely state the one it chose.
- `revisit-when` must not still be live.

The per-agent-type measurement goes into the skill, dated, with the probe that produced
it. ADR 018 gave the rule's load behaviour the same treatment.

**Cons:** The defence rests on the same author judgement ADR 018 already accepted for the
rule. No generator checks either gate.
**Risks:** The dated per-agent-type table goes stale on the harness's schedule, not this
repository's. A reader who trusts the table archives on a defence that no longer reaches
the agent type doing the planning.

### Option 3: Admit it and check rejected-options coverage in the generator

`adr.py` gains a check. For an `Archived` ADR that names ambient instructions as its
defence, the check confirms the ambient file's text against every option the ADR rejected.

**Pros:** The check would catch the exact mistake both reverted attempts made: stating the
chosen rule without forbidding the rejected ones.
**Cons:** Coverage here is a natural-language judgement, not a glob match. Nothing in
`adr.py` parses prose for "forbids". The check has no smaller target than re-reading the
whole ADR and the whole ambient file by eye, which is what the author already does.
**Risks:** People can still promise a check that cannot be built. A promised check that is
believed before it exists is worse than none. That is why [ADR 014][] deferred its own
citation-liveness check rather than specify one that nothing could run.

## Decision

Adopt Option 2. This extends to ambient project instructions the archival-defence
framework that ADR 018 set up for the rule, on the same terms: the author judges now, and
a dated measurement stands in for a mechanical check that no generator can run.

This ADR rejects Option 3 outright, rather than postponing it the way ADR 018 parked its
own Option 3. Glob coverage can be decided mechanically once a real archival gives a
coverage check something concrete to specify against, and ADR 018's `revisit-when` waits
for that. Whether prose "forbids every option" is a judgement that no grammar captures. No
later archival would make this option specifiable the way ADR 018's parked option is.
Postponing it would only promise a check with nothing to build.

The `status` guidance already states the revisit-liveness gate for every defence. This ADR
states it again for ambient instructions, because the two reverted attempts turned on
exactly this interaction. A reader working through the ambient-instructions defence should
meet the reason 020 failed without having to look elsewhere.

## Consequences

- Archiving on ambient instructions costs what archiving on a rule does. The author needs
  a dated measurement of what the mechanism actually reaches, watched rather than assumed.
  The author also checks the two text gates against the ADR's own rejected options and its
  `revisit-when`.
- No archival meets this bar yet. This defence class is drawn from two attempts, and both
  were reverted. The reverts exposed the gates. Neither attempt satisfied them.
- The per-agent-type table records harness behaviour, not repository state. As with the
  rule's load behaviour in ADR 018, nothing here fails a check when the harness changes.
  Re-measuring costs one probe per type against one control question.
- `docs/adr/` and `skills/writing-adrs/` are in scope, matching ADR 018, so an ADR that
  touches either path now reports both decisions.
- `writing-adrs` itself, not this ADR, refutes the argument that "ambient instructions are
  a superset of what archiving removes". The counterexample rests on the skill's own hook,
  which injects `docs/adr/INDEX.md` regardless of `AGENTS.md`. That hook is repository
  tooling this ADR does not own.

[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
