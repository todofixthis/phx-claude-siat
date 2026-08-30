---
status: Accepted
date: 2026-08-30
scope: [.agents/rules/, docs/adr/, scripts/adr/, skills/writing-adrs/]
summary: Do not generate path-scoped rule files from ADR frontmatter at any granularity; a hand-written rule stating a constraint stays welcome, and INDEX.md with the `--for` lookup remains how a path reaches the decisions binding it.
revisit-when: A harness loads a path-scoped rule on the creation of a matching file or on a shell read, so what a rule reaches stops depending on how a session happens to read; or an agent is found breaching a decision a generated rule would have put in front of it.
---

# 019: Do not generate path-scoped rules from ADR frontmatter

## Context

[ADR 018][] admitted a path-scoped rule as an archival defence and rejected generating one
per decision as such a defence. A different proposal followed: have [`generate_index.py`][]
also write rule files keyed to `scope`, so the decisions binding a file arrive when an agent
reads it. That is delivery of the index rather than a defence, and it answers a failure
[`AGENTS.md`][] already documents — `scope` entries are exact paths and prefixes, and a
reader treating them as literal paths misses most of what binds a file, with nothing to say
so.

The mechanism was measured before the proposal was judged, 018 having recorded one of these
wrong. A rule nested a directory deep loads. Several matching rules load together, in one
block. A rule loads **once per session, at the first read matching its globs**, and not
again — not on a later read of the same file, nor of another file matching the same globs —
while a rule matched only by a later read arrives then. Each subagent is its own session,
inheriting no load from whoever dispatched it. So 018's Option 4 risk, that "every matching
read pulls in prose nobody wrote", overstates the cost: it is once per rule, per session.
What does not load is unchanged from 018 — the `Write` creating a matching file, and any
read from a shell.

Everything the proposal needs therefore works, and costs less than 018 recorded.

## Options

### Option 1: Do nothing (Accepted)

[`INDEX.md`][] read on demand, the `--for` lookup from a path, and a hand-written rule where an
area earns one, as [`testing.md`][] does today for [ADR 016][].

**Pros:** One representation of a decision's row, so nothing can disagree with it.
**Cons:** The prefix-matching error `AGENTS.md` warns about stays the reader's to avoid
unaided. The one reverse route that fires without being asked for — `--for`, from the
pre-commit hook — runs over staged paths, so it arrives after the work is authored, which is
the timing the skill rejects when the same shape is offered as an archival defence.
**Risks:** A reader who never runs the lookup and never opens the index meets no decision at
all, and nothing reports that.

### Option 2: Generate rules from ADR frontmatter

The generator writes rule files whose `paths` cover scoped paths and whose bodies list the
decisions binding them, at one of three granularities:

- **Per distinct `scope` entry** — the most precise and the most files; the eighteen
  decisions in force here name twenty-two entries between them, and the count grows with
  scope breadth rather than with anything a reader wants.
- **Per top-level directory** — around eight files here, bounded by the repository's shape
  rather than by the corpus, and still narrowing eighteen decisions to the four binding
  `scripts/`. This is the strongest form, and the one the option is judged as.
- **One file covering every bound path** — one file, and every row on a touch of anything,
  which is `INDEX.md` with a trigger attached.

**Pros:** The decisions binding a file arrive while it is being read, before the work is
authored — earlier than `--for` can reach anyone. Prefixes become globs mechanically,
retiring a translation 018 books as a cost on the author. Generated files cost a session
that never touches them nothing at all, loading only on a match.
**Cons:** A route that usually delivers displaces the one that always does.
**Risks:** `.agents/rules/` becomes half authored and half generated, and a hand edit to a
generated file is regenerated away without a word.

### Option 3: Author a rule per scoped area by hand

Extend what `testing.md` does — prose stating the constraint and citing the decision — to
every area a decision binds, as a programme rather than where a rule is felt to be earned.

**Pros:** Each file says what to do rather than what was decided, so it can defend an
archival, which no generated pointer can.
**Cons:** Prose per area, written and maintained by hand, drifting from its ADR with nothing
to catch it — the failure 018 avoids by requiring the rule and the archival in one change.
**Risks:** The programme is as large as the corpus and has no forcing function, so partial
coverage looks exactly like finished coverage.

## Decision

Do nothing.

The measurements clear Option 2 of the objections easiest to make. The layout works, the
files are small, and they cost nothing to a session that never touches them — so their
number is a question of repository hygiene rather than of a reader's context, and the
bounded granularity keeps even that in proportion. On delivery alone Option 2 beats the
accepted option, and says so above: it reaches an author while they are reading, where
`--for` reaches them only once they stage.

What decides it is displacement. An agent handed the decisions binding the file in front of
it has been given a reason not to run the lookup and not to open the index — and cannot tell
from inside the session whether what it was handed is everything or nothing, because a
session that reads from a shell receives no rule and no notice that it received none. The
complete route stays available in principle and stops being taken in practice, which is how
a partial mechanism ends up subtracting. [ADR 014][] rejected a check on the same shape: one
that reports a defended corpus and is believed is worse than none.

That the accepted option's own reverse route arrives late is the honest price of this, and
it is not the same failure. `--for` is late and legible: it prints what binds the staged
paths, or prints nothing because nothing does. A generated rule is early and silent, and
silence there is indistinguishable from coverage.

Option 3 is not so much rejected as unscheduled. It is what `testing.md` already is, and
each such rule is worth more than any generated file, only prose stating a constraint being
able to defend an archival. As a programme it buys that at the price of hand-written prose
per area with nothing forcing it to keep up; taken one area at a time, as an area earns it,
it keeps the value without the programme — which is Option 1.

## Consequences

- `.agents/rules/` stays authored, and a rule added there is still welcome; what this
  forbids is the generated kind, not the directory.
- Scoping `skills/writing-adrs/` and `.agents/rules/` means an edit to the skill's rule
  section, or to a rules file, reports this decision alongside those already binding them.
  Both are where the guidance to generate these would be written.
- 018's Option 4 risk overstated the context cost, and its Option 4 con — that a `summary`
  says what was decided rather than what to do — stands, the bar there being a defence.
  018 keeps its status and gains a Consequences bullet pointing here.
- That bullet is a fifth kind of edit to a settled ADR, beside the four [`writing-adrs`][]
  names: correcting a factual premise a later measurement falsified, without touching the
  reasoning or the status. Recorded so the next author has a precedent rather than a
  judgement call.
- Every delivery claim above rests on the `.claude/rules` symlink 018 found load-bearing.
  Without it nothing loads, so a repository laid out differently has no version of this
  proposal to weigh.

[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`AGENTS.md`]: ../../AGENTS.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`INDEX.md`]: INDEX.md
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
