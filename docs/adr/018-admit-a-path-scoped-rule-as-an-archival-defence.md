---
status: Accepted
date: 2026-08-29
scope: [docs/adr/, skills/writing-adrs/]
summary: Admit a path-scoped rule file as a third qualifying archival defence beside a code comment and a breach large enough to need its own ADR, writing its verified load semantics and coverage rules into writing-adrs rather than generating a rule per ADR from frontmatter.
revisit-when: A harness loads a path-scoped rule when a matching file is created rather than only when one is read, or an archived decision here loses its rule without the loss being reported.
---

# 018: Admit a path-scoped rule as an archival defence

## Context

[`writing-adrs`][] archives a decision — keeps it in force while dropping it from the index
agents load — only where a defence exists that a breacher meets while the work is still
being planned. It names two: a comment wherever a breach would be authored, and a breach so
large it needs its own ADR. Both were written before an agent could load instructions scoped
to file globs.

A sibling repository has since archived on a third. [filters-pydantic ADR 004][] holds a
docstring-per-test-function convention in force and out of its index, defended by a
`.claude/rules/testing.md` whose `paths` frontmatter loads the convention whenever an agent
reads a matching test file. It reached that defence through the skill's own escape hatch —
"unless another meets that same timing test" — and the judgement holds. What the hatch left
unwritten is the part each author must otherwise re-derive: which tool calls actually load a
rule.

Measured here against [`testing.md`][], those calls are narrower than the mechanism's
name suggests. A rule loads on the read tool, in a subagent as much as a main session. It does
not load on the `Write` that creates a matching file ([anthropics/claude-code#23478][]), so
a decision whose breaches arrive as new files is undefended until something reads one back.
Nor does it load when a file is read from a shell — `cat`, `sed`, `grep`. That last one is
not an edge case: the session that measured it ran under a harness mode whose standing
instruction was to read files with `sed` in preference to the read tool, which would have
switched the defence off for every file it touched.

None of that is discoverable from a repository. No `rg` answers "what loads a rule", so an
author who takes the mechanism at its name archives a decision that reads as defended and is
not — and reads that way indefinitely, an archived ADR being invisible by design.

## Options

Options 2 and 3 both put a decision's constraint into a second file that can drift from the
ADR, and both rest on a harness feature this repository does not control. Neither is ranked
by that. What separates them is whether a rule qualifies as a defence by an author's
judgement or by construction.

### Option 1: Do nothing — leave it to the escape hatch

The skill keeps two named defences and admits others that meet the timing test, as it
already does.

**Pros:** The hatch has carried one archival correctly, in a repository whose author had the
timing test to hand.
**Cons:** Each author re-derives the load semantics, which no amount of reading a repository
answers; the honest ones spend a probe, the rest guess.
**Risks:** The cheap guess is the wrong one. A rule matching `**/test_*.py` under a `test/`
scope covers a fraction of it and looks total, and the resulting archival surfaces only when
someone relitigates the decision.

### Option 2: Name it as a third defence, with its mechanics (Accepted)

`writing-adrs` names the rule beside the comment and states what a qualifying one must do:
cover every path in `scope`, state the constraint rather than point at the ADR, be written
in the same change as the archival, be named in `archived-because`, and have its own path
listed in `scope`. The load semantics go in with the date they were verified and an
instruction to re-check them.

**Cons:** Adds a section to an already dense skill, and ships a dated harness fact that goes
stale on somebody else's release schedule.
**Risks:** A reader takes the dated semantics as permanent and archives on a rule the
harness has since stopped loading; the verification step is what that risk rests on holding.

### Option 3: Generate a rule per ADR from its frontmatter

A generator writes `.claude/rules/adr-NNN.md` for each decision from its `scope` and
`summary`, so every ADR defends itself by construction and the index keeps only the
decisions with no file home.

**Pros:** Coverage cannot drift from `scope`, one being derived from the other, and no
author translates prefixes into globs by hand.
**Cons:** `summary` says what was decided, not what to do, so the generated rule spends a
reader's context on an index row rather than an instruction.
**Risks:** Every matching read pulls in whole files nobody wrote, and the volume — one per
decision — is what makes the corpus expensive exactly where it was meant to be cheap.

## Decision

Adopt Option 2, and treat the rule as a peer of the comment rather than its replacement.

Option 3 loses on the judgement it cannot make: whether a rule's globs cover the scope, and
whether its prose tells an author what to do. That is the same argument [ADR 014][] made
against a checked citation schema — a mechanism that validates the cheap half and reports a
defended corpus is worse than no mechanism, because it is believed.

Peer, not preferred, because the two defences fail in different places. A rule reaches files
nobody has written yet, which is precisely the case that disqualifies a comment; a comment
sits in the bytes, so it reaches every reader by every route, including the shell reads and
first writes a rule misses. Where both are available, both.

Listing the rule's own path in `scope` follows [ADR 013][], which puts `pr.yml` in its own
scope because narrowing that filter is how the decision gets breached. Narrowing or deleting
a rule is how an archival gets breached, so the rule belongs in the scope of the decision it
defends — which is the only thing that puts that decision in front of whoever stages the
deletion.

## Consequences

- Archiving on a rule costs what archiving on a comment costs: the rule goes in with the
  status change, `archived-because` names it, and the archiver checks the globs cover the
  scope and watches the rule load before relying on it.
- `scope` now carries entries naming where a defence lives, not only where a breach is
  authored. [`generate_index.py`][] validates such an entry for `Archived` decisions as
  well as `Accepted` ones, so deleting the rule fails the build, and `--for` reports the
  decision to whoever stages the file; neither checks that the entry names a rule, or that
  its globs cover anything.
- No decision here is archived on a rule yet, and the coverage requirement bites the obvious
  candidate: `testing.md` matches `**/test_*.py` and `**/*_test.py`, while [ADR 016][]
  scopes `.agents/rules/testing.md` and `scripts/` — every non-test script under that prefix
  is uncovered, so 016 stays `Accepted`.
- ADR 014's deferred liveness check now has two defence shapes to specify for rather than
  one. Its trigger — an ADR archived on a defence resting on a comment in code — is
  untouched: this decision neither meets it nor closes a way it could arrive.
- The new section ships to users whose checkout holds no `docs/adr/`, so it names the
  constraint rather than leaning on an ADR number, per ADR 014.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[anthropics/claude-code#23478]: https://github.com/anthropics/claude-code/issues/23478
[filters-pydantic ADR 004]: https://github.com/todofixthis/filters-pydantic/blob/main/docs/adr/004-docstring-per-test-function.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
