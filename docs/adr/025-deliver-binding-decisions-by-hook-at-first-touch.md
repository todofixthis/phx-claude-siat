---
status: Accepted
date: 2026-09-02
scope: [.agents/rules/, hooks/, skills/writing-adrs/]
summary: Inject the decisions binding a path from a PreToolUse hook the first time a session touches it — by a file tool or a shell command naming it — labelled as binding that path and not the corpus, beside a session-start instruction to read INDEX.md; still generate no rule files from frontmatter.
revisit-when: A proposed ADR relitigates an indexed decision that was not among the rows injected for the paths it touched; the injection's cost is measured above the 100 ms per event ADR 022 budgets; or the harness delivers path-keyed context itself.
---

# 025: Deliver binding decisions by hook at first touch

## Context

[ADR 013][] keyed ADRs to the paths they bind so the decisions governing a file could reach
whoever edits it, and delivered that from the pre-commit hook: after the work is authored,
and only in clones that installed the hook. [ADR 019][] declined to generate path-scoped
rules from that frontmatter, on two grounds: a rule keyed to the file in hand answers a
narrower question than the corpus read `AGENTS.md` mandates, and an agent holding the
narrow answer has reason to treat the broad instruction as discharged — displacement, whose
danger is that the two failure modes do not overlap, a reader who skips the index knowing
they skipped it where one served rows cannot tell they were served less than everything;
and the generated files would sit half-authored in `.agents/rules/`. It set two triggers: a
harness that loads a rule on file creation or on a shell read, or a measurement showing the
mandated index read is not happening.

Neither has fired. 019 was decided for this repository, where its do-nothing had a
counterpart: `AGENTS.md` mandating the index read, and the pre-commit lookup. [ADR 022][]
ships the skill to consumers, where that counterpart is nothing. The maintainer has asked
for delivery: an agent working on a bound file should receive the decisions without going
looking.

A `PreToolUse` hook runs before the tool and its `additionalContext` reaches the agent
alongside the tool's result, on the next model request; it fires for `Bash` as for the file
tools, with the command string in its input. Files referenced with `@` in a prompt fire no
tool call and so no hook. Verified against the [hooks reference][hooks] on 2026-09-02.

## Options

### Option 1: Do nothing

`INDEX.md` read as `AGENTS.md` requires here, and the pre-commit lookup over staged paths.

**Pros:** ADR 019's reasoning stands untouched.
**Cons:** Delivery arrives after the work, in clones that installed the hook, and on no
consumer at all.
**Risks:** The reader who does not know a decision exists stays unreached, which is the
reader ADR 013 was for.

### Option 2: Inject by hook at first touch (Accepted)

A `PreToolUse` hook on `Read`, `Edit`, `Write`, `NotebookEdit` and `Bash` injects each
binding decision not yet injected this session: number, status, title, summary, live
`revisit-when`, path. For `Bash`, the command string is tokenised and every token resolving
to a path under a managed root is looked up. Each injection is labelled as the decisions
binding those paths, not the corpus, and ends with the instruction to read `INDEX.md`
before proposing an architectural or tooling change; a `SessionStart` and `SubagentStart`
note carries the same instruction.

**Pros:** Fires on `Write` and on a shell read, the two routes ADR 019 itself identified as
the ones a rule misses. Nothing is generated into the repository. Each row lands once per
session, per subagent.
**Cons:** The rows arrive with the tool's result, so a first-touch `Write` has landed before
the agent reads them; what they precede is the next action, not the first. Delivery
reaches only a path under a managed root, as [ADR 024][] gates it.
**Risks:** That the label answers displacement is a claim, and unmeasured; the revisit
condition is what measures it. Context cost — up to ten rows per event, per subagent —
and one Python start per touched path. The tokeniser misses a path behind a shell
variable or a glob and can match a path quoted inside an `echo`.

### Option 3: Generate path-scoped rules

ADR 019's Option 2.

**Pros:** Loads with no plugin code at all.
**Cons:** Rejected by 019 on grounds this ADR does not dispute, and a rule never fires on
`Write` or a shell read.
**Risks:** As 019 recorded.

## Decision

Option 2. This supersedes ADR 019 by the maintainer's judgement, not because its trigger
fired, and that is said plainly so a later reader does not go looking for the measurement.
What tips it: for a consumer 019's do-nothing delivers nothing, and a hook reaches the two
routes 019 named as the ones a rule misses. 019's displacement ground is met with the label
on every injection: a reader served rows labelled as binding this path knows they were
served less than everything, which restores the overlap of failure modes 019 found
missing, and a rule could not carry the label; its second
ground, generated files in `.agents/rules/`, does not arise, and generating them stays
forbidden. 019's row-free variant — a note saying only to run the lookup and read the
index — is what the `SessionStart` note is, and it ships beside the rows rather than
instead of them.

Whether hook delivery qualifies as an archival defence is not decided here: [ADR 018][]'s
terms stand, and an `Archived` row injected at first touch reaches only a reader whose
harness runs the plugin.

## Consequences

- ADR 019 is marked `Superseded` by this ADR. Its measurements of rule loading stand and
  are still cited by ADR 018.
- `.agents/rules/` stays hand-authored; this ADR keeps that path in scope because
  generating into it is still the breach.
- An injection stays under the harness's 10,000-character cap, past which the text is
  swapped for a file path: at most ten rows per event, and the rest named by number and
  path.
- `Grep`, `Glob`, MCP file readers and `@`-referenced files deliver nothing; the first two
  return matches rather than a file, the rest fire no matched tool call.
- Root resolution follows ADR 024; what is reported after a change, and how often,
  follows [ADR 026][].

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[ADR 019]: 019-do-not-generate-path-scoped-rules-from-adr-frontmatter.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[hooks]: https://code.claude.com/docs/en/hooks
