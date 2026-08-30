---
status: Accepted
date: 2026-08-30
scope: [.agents/rules/, docs/adr/, scripts/adr/]
summary: Keep INDEX.md and the `--for` lookup the only routes from a path to the decisions binding it; do not have the generator write path-scoped rule files from ADR frontmatter, neither one per scope entry nor one carrying the whole index.
revisit-when: A harness loads a path-scoped rule without a read — on creating a matching file, or from a shell read — so what a session receives stops depending on how its agent happens to read; or the corpus outgrows an index a reader can scan.
---

# 019: Keep the index the only route from a path to its decisions

## Context

[ADR 018][] admitted a path-scoped rule as an archival defence, and rejected generating one
per decision as such a defence. A different proposal followed: have [`generate_index.py`][]
also write rule files keyed to `scope`, so the decisions binding a file arrive when an agent
reads it. That is delivery of the index rather than a defence, and it answers a failure
[`AGENTS.md`][] already documents — `scope` entries are exact paths and prefixes, and a
reader treating them as literal paths misses most of what binds a file, with nothing to say
so.

The mechanism was measured before the proposal was judged, 018 having recorded one of these
wrong. A rule nested a directory deep loads. Several matching rules load together, in one
block. A rule loads **once per session, at the first read that matches it**, and not again —
not on a later read of the same file, nor of another file matching the same globs — while a
rule matched only by a later read arrives then. So 018's Option 4 risk, that "every matching
read pulls in prose nobody wrote", overstates the cost: it is once per rule, per session.
What does not load is unchanged from 018 — the `Write` creating a matching file, and any
read from a shell.

The layout therefore works and costs less than recorded. What decides the proposal is
elsewhere: how many files it makes, and what a session receives when its agent reads from a
shell.

## Options

Options 2 and 3 both deliver nothing to a session that reads with `cat`, `sed` or `grep` —
measured, and the mode this repository's own sessions have run under — and both put
generated index content in a second place. Neither is ranked by that, and neither retires
`INDEX.md`, so the failure is a quiet no-op rather than a loss. What separates them is
precision against the number of files.

### Option 1: Do nothing — the index stays the only route (Accepted)

`INDEX.md` read on demand, the `--for` lookup from a path, and a hand-written rule where an
area earns one.

**Pros:** Nothing to generate, and one place a decision's row lives. A hand-written rule
that states a constraint stays available and is worth more per file than a generated
pointer, since only the former can defend an archival.
**Cons:** The prefix-matching error `AGENTS.md` warns about stays the reader's to avoid,
unaided.
**Risks:** A corpus that outgrows a scannable index has no fallback but this one, which is
what the trigger watches for.

### Option 2: A rule per scope entry

`generate_index` writes `.agents/rules/adr/<entry>.md` for each distinct `scope` entry,
listing the decisions binding it, with `paths` globbing that prefix.

**Pros:** Precise — a read pulls in the decisions binding that file and no others, and
overlapping entries compose, both measured.
**Cons:** One file per distinct scope entry, so the directory grows with decisions
multiplied by the breadth of their scopes rather than with anything a reader wants. The
eighteen decisions in force here name twenty-two distinct entries between them.
**Risks:** `.agents/rules/` becomes half authored and half generated, and a hand edit to a
generated file is regenerated away without a word.

### Option 3: One rule carrying the whole index

A single generated rule whose `paths` cover every path any decision binds.

**Pros:** One file, whatever the corpus does.
**Cons:** Injects every row on a touch of any bound path, which is `INDEX.md` with a trigger
attached rather than delivery of what binds this file.
**Risks:** Reads as precision delivery while being none, so it is the version most likely to
be believed.

## Decision

Do nothing.

Option 2's precision is real, and so is its shape: the directory tracks scope entries, not
decisions. A corpus of broad scopes — the case where an index is hardest to scan and this
would help most — is exactly the case that generates the most files. Paying in proliferation
where the benefit is greatest is the wrong slope to be on. Option 3 avoids that by
collapsing into the index it was meant to improve on.

Both are also silent under the condition that decides them. What a session receives
depends on how its agent happens to read, and nothing inside that session reveals which it
got. A delivery mechanism whose coverage cannot be observed is one people stop checking
behind — the shape [ADR 014][] rejected in a check that reports a defended corpus and is
believed. Here that would cost attention rather than a defence, `INDEX.md` remaining, but
the attention is the whole benefit being claimed.

The higher-value thing stays available and is not this: a hand-written rule stating a
constraint, as [`testing.md`][] does for [ADR 016][]. Generated pointers would have crowded
that directory with files carrying less.

## Consequences

- `generate_index` keeps one output, and `.agents/rules/` stays authored.
- The measurements are the durable result and live here, where the next person proposing
  this will look: nested directories load, several matching rules load together, and a
  rule loads once per session at the first matching read.
- `writing-adrs` gains that last fact, which softens the gap it records around files
  created new: one read matching the rule's globs covers the work that follows it. That is
  the globs and not the `scope` — the two differ wherever the translation between them was
  loose, which is the case the skill already warns about.
- 018's Option 4 risk overstated the context cost. Its decision does not rest on that line —
that option lost on the judgement a generator cannot make — so 018 keeps its status and
gains a pointer here rather than an edit to its reasoning. Its Option 4 con, that a
`summary` says what was decided rather than what to do, stands: the bar there is a
defence, where stating the constraint is the requirement.
- Scoping `.agents/rules/` means an edit to a rules file now reports this decision alongside
  the two that already bind `testing.md`. That is the intended reader — someone editing a
  rule is the one who might add generated ones.

[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`AGENTS.md`]: ../../AGENTS.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`testing.md`]: ../../.agents/rules/testing.md
