---
status: Superseded
date: 2026-08-30
scope: [.agents/rules/, docs/adr/, skills/writing-adrs/]
summary: Do not generate path-scoped rule files from ADR frontmatter at any granularity; a hand-written rule stating a constraint stays welcome, and INDEX.md with the `--for` lookup remains how a path reaches the decisions binding it.
superseded-by: 25
revisit-when: A harness loads a path-scoped rule on the creation of a matching file or on a shell read, so what a rule reaches stops depending on how a session happens to read; or the mandated index read is measured and found not to be happening.
---

# 019: Do not generate path-scoped rules from ADR frontmatter

## Context

[ADR 018][] admitted a path-scoped rule as an archival defence, and rejected generating one
rule per decision as such a defence. A different proposal followed: have [`adr.py`][] also
write rule files keyed to `scope`, so the decisions binding a file arrive when an agent
reads it. That delivers the index rather than defending a decision. It answers a failure
that [`AGENTS.md`][] already documents. `scope` entries are exact paths and prefixes, and a
reader who treats them as literal paths misses most of what binds a file, with nothing to
say so.

Because 018 had recorded one of the mechanism's behaviours wrong, the mechanism was measured
before the proposal was judged. A rule nested one directory deep loads. Several matching
rules load together, in one block. A rule loads **once per session, at the first read
matching its globs**, and not again. It does not reload on a later read of the same file,
or of another file that matches the same globs. A rule that only a later read matches
arrives at that later read. Each subagent is its own session and inherits no load from
whoever dispatched it. So 018's Option 4 risk, that "every matching read pulls in prose
nobody wrote", overstates the cost: the cost is once per rule, per session. What does not
load is unchanged from 018: the `Write` that creates a matching file, and any read from a
shell.

Everything the proposal needs therefore works.

## Options

### Option 1: Do nothing (Accepted)

Agents read [`INDEX.md`][] as `AGENTS.md` requires, run the `--for` lookup from a path, and
get a hand-written rule where an area earns one, as [`testing.md`][] does today for
[ADR 016][].

A programme of such rules covering every scoped area is the same approach at a larger
scale. It is prose per area with nothing forcing it to keep up, and partial coverage looks
the same as finished coverage.

**Pros:** A decision's row has one representation, and the instruction to read it reaches
every contributor by every tool.
**Cons:** The reader must still avoid, unaided, the prefix-matching error that `AGENTS.md`
warns about. `--for` runs over staged paths, so the one route that fires unasked arrives
after the work is authored. The skill rejects that timing when the same shape is offered as
an archival defence. Its silence is also ambiguous. It can mean that nothing binds the
path, that nobody installed the hook, or that the generator failed into `|| exit 0`.
**Risks:** The route depends on someone following an instruction, and nothing reports the
reader who does not.

### Option 2: Generate rules from ADR frontmatter

The generator writes rule files whose `paths` come from `scope`. Two things vary: how
finely the files are keyed, and what they carry. The forms considered were these:

- **Per distinct `scope` entry, carrying the decisions that name it.** This form is exact.
  Matching rules load together, so a read of `scripts/adr/generate_index.py` receives both
  the `scripts/` rule and the `scripts/adr/` rule, and nothing is left to match by hand. It
  needs twenty-two files here. An unmatched rule loads nothing, so the file count is a
  matter of hygiene rather than a cost to the reader.
- **Per top-level directory.** The tree bounds the file count rather than the corpus, at
  seven to nine files here, but the form cannot tell `scripts/adr/` from `scripts/ci/`. A
  complete file carries the ten decisions that name anything beneath `scripts/`. An
  incomplete one is partial, and nothing says so.
- **One file covering every bound path.** This is `INDEX.md` with a trigger attached.
- **Any of those forms carrying no rows.** The globs come from `scope`, and the body says
  only to run the lookup and read the index.

**Pros:** Keyed exactly, it does mechanically the prefix matching that `AGENTS.md` warns
about, which is the failure that prompted the proposal. It hands the result over while the
author is reading, rather than once they stage.
**Cons:** Every form that carries rows answers "which decisions bind this file". An agent
holding that answer has reason to treat the index read as done, although `AGENTS.md` asks
for the index read to answer a different question.
**Risks:** `.agents/rules/` becomes half authored and half generated, and the generator
silently overwrites a hand edit to a generated file.

## Decision

Do nothing.

The measurements clear Option 2 of the objections easiest to make, and the exact form works.
Matching rules compose, so the exact form hands an author every decision that names the
path in front of them, with no matching left to do. It mechanically retires a failure that
`AGENTS.md` documents and that `--for` can report only once paths are staged. On delivering
what binds a file, it beats the accepted option, and nothing below pretends otherwise.

What it does not deliver is what the mandated read is for. `AGENTS.md` requires agents to
read `INDEX.md` before proposing architectural or tooling changes, so that nobody
relitigates a settled decision. That is a question about the whole corpus. A rule keyed to
the file in hand answers a narrower one: what binds this file. An agent holding the narrow
answer has every reason to treat the broad instruction as done, and nothing in the session
tells the two apart. That is the displacement. The generated route does not say less about
the file; keyed exactly, it says more. The problem is that it looks like the answer to a
question it was never asked.

The mandated read is not reliable, and this ADR says so three times over. It is, though,
the only route that reaches every reader by every tool, and no rule does that. The decision
to keep it turns on the two failure modes not overlapping. A reader who skips the index
knows they skipped it. A reader served a rule cannot tell that they were served anything
less than everything.

The row-free variant escapes all of that, because a rule saying only "run the lookup, read
the index" cannot be mistaken for an answer. It is declined on a smaller ground. What it
carries already sits in `AGENTS.md`, which is in context from the start, so it buys
salience at the price of another generated file to keep matched to `scope`. If salience
turns out to be what was missing, the row-free variant is the one to reach for, and the
first part of this decision to give up.

## Consequences

- `.agents/rules/` stays authored, and a rule added there is still welcome. This decision
  forbids the generated kind of rule, not the directory.
- Because `skills/writing-adrs/` and `.agents/rules/` are in scope, an edit to the skill's
  rule section or to a rules file reports this decision alongside those already binding
  them. `scripts/adr/` is scoped for the generator that would write the rules.
- 018 keeps its status and gains a Consequences bullet pointing here. Its Option 4 con, that
  a `summary` says what was decided rather than what to do, stands untouched, because the
  bar there was a defence rather than delivery.
- That is a kind of edit to a settled ADR that [`writing-adrs`][] does not name: correcting
  a premise that a later measurement falsified, and leaving the reasoning and the status
  alone. Like the workflows the skill does name, the edit strikes the premise in 018's
  body, because that is where a reader of 018 meets it.
- A repository without the `.claude/rules` symlink, which 018 found to be required, has no
  version of this proposal to weigh at all, because nothing there loads a rule.

[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`AGENTS.md`]: ../../AGENTS.md
[`INDEX.md`]: INDEX.md
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
