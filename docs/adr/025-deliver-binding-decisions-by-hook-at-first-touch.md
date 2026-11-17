---
status: Accepted
date: 2026-09-02
scope: [.agents/rules/, hooks/, skills/writing-adrs/]
summary: Inject the decisions binding a path from a PreToolUse hook the first time a session touches it — by a file tool or a shell command naming it — labelled as binding that path and not the corpus, beside a session-start instruction to read INDEX.md; still generate no rule files from frontmatter.
revisit-when: A proposed ADR relitigates an indexed decision that was not among the rows injected for the paths it touched; the injection's cost breaches the hook budgets ADR 034 sets; or the harness delivers path-keyed context itself.
---

# 025: Deliver binding decisions by hook at first touch

## Context

[ADR 013][] keyed ADRs to the paths they bind, so that the decisions governing a file could
reach whoever edits it. ADR 013 delivered them from the pre-commit hook, which runs after
the work is written, and only in clones that installed the hook.

[ADR 019][] declined to generate path-scoped rules from that frontmatter, on two grounds.
The first ground is displacement. A rule keyed to the file in hand answers a narrower
question than the corpus read that `AGENTS.md` mandates, and an agent that holds the narrow
answer has reason to treat the broad instruction as done. The danger is that the two
failure modes do not overlap. A reader who skips the index knows they skipped it. A reader
served rows cannot tell they were served less than everything. The second ground is that
the generated files would sit half-authored in `.agents/rules/`. ADR 019 set two triggers:
a harness that loads a rule on file creation or on a shell read, or a measurement showing
that agents are not doing the mandated index read.

Neither trigger has fired. ADR 019 was decided for this repository, where its do-nothing
option had a counterpart: `AGENTS.md` mandating the index read, and the pre-commit lookup.
[ADR 022][] ships the skill to consumers, where that counterpart is nothing. The maintainer
has asked for delivery: an agent working on a bound file should receive the decisions
without going looking.

A `PreToolUse` hook runs before the tool. Its `additionalContext` reaches the agent with
the tool's result, on the next model request. The hook fires for `Bash` as it does for the
file tools, with the command string in its input. A file referenced with `@` in a prompt
fires no tool call, so it fires no hook. These facts were verified against the
[hooks reference][hooks] on 2026-09-02.

## Options

### Option 1: Do nothing

Keep the `INDEX.md` read that `AGENTS.md` requires here, and the pre-commit lookup over
staged paths.

**Pros:** ADR 019's reasoning stands untouched.
**Cons:** Delivery arrives after the work, only in clones that installed the hook, and on
no consumer at all.
**Risks:** The reader who does not know a decision exists stays unreached, and that is the
reader ADR 013 was for.

### Option 2: Inject by hook at first touch (Accepted)

A `PreToolUse` hook on `Read`, `Edit`, `Write`, `NotebookEdit` and `Bash` injects each
binding decision not yet injected this session. Each row gives the number, status, title,
summary, live `revisit-when`, and path. For `Bash`, the hook splits the command string into
tokens and looks up every token that resolves to a path under a managed root. Each
injection is labelled as the decisions that bind those paths, not the corpus. It ends with
the instruction to read `INDEX.md` before proposing an architectural or tooling change. A
`SessionStart` and `SubagentStart` note carries the same instruction.

**Pros:** The hook fires on `Write` and on a shell read, the two routes that ADR 019 itself
found a rule misses. Nothing is generated into the repository. Each row lands once per
session, per subagent.
**Cons:** The rows arrive with the tool's result, so a first-touch `Write` has landed
before the agent reads them. The rows precede the next action, not the first. Delivery
reaches only a path under a managed root, as [ADR 024][] gates it.
**Risks:** The claim that the label answers displacement is unmeasured, and the revisit
condition is what measures it. Each event costs context, up to ten rows per event per
subagent, and one Python start per touched path. The tokeniser misses a path behind a
shell variable or a glob, and can match a path quoted inside an `echo`.

### Option 3: Generate path-scoped rules

This is ADR 019's Option 2.

**Pros:** The rules load with no plugin code at all.
**Cons:** ADR 019 rejected this option on grounds this ADR does not dispute, and a rule
never fires on `Write` or a shell read.
**Risks:** As ADR 019 recorded.

## Decision

Option 2. This ADR supersedes ADR 019 by the maintainer's judgement, not because 019's
trigger fired. It says so plainly, so that a later reader does not go looking for the
measurement.

Two things tip the decision. For a consumer, 019's do-nothing option delivers nothing. A
hook also reaches the two routes that 019 named as the ones a rule misses.

The label on every injection meets 019's displacement ground. A reader served rows
labelled as binding this path knows they were served less than everything. That restores
the overlap of failure modes that 019 found missing, and a rule could not carry the label.
019's second ground, generated files in `.agents/rules/`, does not arise, and generating
them stays forbidden. 019's row-free variant, a note saying only to run the lookup and read
the index, is what the `SessionStart` note is. It ships beside the rows, not instead of
them.

This ADR does not decide whether hook delivery qualifies as an archival defence.
[ADR 018][]'s terms stand, and an `Archived` row injected at first touch reaches only a
reader whose harness runs the plugin.

## Consequences

- ADR 019 is marked `Superseded` by this ADR. Its measurements of rule loading stand, and
  ADR 018 still cites them.
- `.agents/rules/` stays hand-authored. This ADR keeps that path in scope because
  generating into it is still the breach.
- An injection stays under the harness's 10,000-character cap, past which the harness
  replaces the text with a file path. Each event carries at most ten rows and names the
  rest by number and path.
- `Grep`, `Glob`, MCP file readers and `@`-referenced files deliver nothing. `Grep` and
  `Glob` return matches rather than a file, and the others fire no matched tool call.
- Root resolution follows ADR 024. What is reported after a change, and how often, follows
  [ADR 026][].
- The cost condition in `revisit-when` first cited ADR 022's 100 ms per event. [ADR 034][]
  replaced that budget with one per tool-calling turn and a 1 s per-event ceiling, which
  loosens the condition. The condition now cites those.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[ADR 019]: 019-do-not-generate-path-scoped-rules-from-adr-frontmatter.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[ADR 034]: 034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md
[hooks]: https://code.claude.com/docs/en/hooks
