---
status: Accepted
date: 2026-08-29
scope: [docs/adr/, skills/writing-adrs/]
summary: Admit a path-scoped rule as a third qualifying archival defence beside a code comment and a breach large enough to need its own ADR, qualifying only where its globs and any other named defence reach every path in scope bar the rule's own entry, judged by the author for now rather than checked by the generator or generated from frontmatter.
revisit-when: An ADR here is archived on a rule, making a coverage check specifiable; or the load semantics narrow — rules ceasing to load in a subagent, or shell-first reading becoming the default across sessions rather than one mode among several — degrading the archivals already made.
---

# 018: Admit a path-scoped rule as an archival defence

## Context

[`writing-adrs`][] archives a decision — keeps it in force while dropping it from the index
agents load — only where a defence exists that a breacher meets while the work is still
being planned. It named two: a comment wherever a breach would be authored, and a breach so
large it needs its own ADR. Both were written before an agent could load instructions scoped
to file globs.

A sibling repository has since archived on a third. [filters-pydantic ADR 004][] holds a
docstring-per-test-function convention in force and out of its index, defended by a rule
file — `.agents/rules/testing.md`, reached through a `.claude/rules` symlink — whose `paths`
frontmatter loads the convention whenever an agent reads a matching test file. It reached
that defence through the skill's own escape hatch, "unless another meets that same timing
test", and the kind of defence holds up. Its coverage does not: the rule matches
`**/test_*.py` alone against a scope of `test/` and `scripts/`, so most of what the decision
binds meets nothing, and the rule's own path is absent from that scope. A defence admitted
on judgement alone was judged generously the first time it was used.

The load semantics are the other half. That ADR records one gap — a rule does not load on
the `Write` creating a matching file ([anthropics/claude-code#23478][], closed as not
planned) — and the rest went unmeasured. Measured here against
this repository's [`testing.md`][], by reading a matching file with the read tool and then
with `sed`: a rule loads on the read tool, in a subagent as much as a main session, and not
on a shell read at all. The session that measured it ran
under a harness mode whose standing instruction was to read files with `sed` in preference
to the read tool, which would have switched the defence off for every file it touched.

None of it was discoverable from a repository before this ADR: no `rg` answered "what
loads a rule", so an author who took the mechanism at its name archived a decision that
reads as defended and is not — and reads that way indefinitely, an archived ADR being
invisible by design.

## Options

Options 2, 3 and 4 all put a decision's constraint into a second file that can drift from
the ADR, and all rest on a harness feature this repository does not control. Neither cost
ranks them. What separates them is how much machinery stands behind the admission.

### Option 1: Do nothing — leave it to the escape hatch

The skill keeps two named defences and admits others meeting the timing test, as it already
does.

**Pros:** The hatch already carried an archival whose choice of defence was right.
**Cons:** Each author re-derives the load semantics; the honest ones spend a probe, the rest
guess.
**Risks:** The generous reading is the natural one, and the sibling ADR is the evidence — a
partial rule looks total, and the shortfall surfaces only when someone relitigates the
decision.

### Option 2: Admit it as an author-judged defence (Accepted)

`writing-adrs` names the rule beside the comment and states what a qualifying one must do:
have every path in `scope` bar its own entry reached by its globs or by another named
defence, name the ADR
and state the constraint, be written in the same change as the archival, live in the
repository, be named in `archived-because`, and have its own path listed in `scope`. The
load semantics go in dated, with the probe that produced them. Nothing checks any of it.

**Cons:** Rests on the same author judgement that read the first rule generously.
**Risks:** The dated semantics go stale on somebody else's release schedule, and a reader
who trusts them archives on a rule the harness has stopped loading.

### Option 3: Admit it and check glob coverage in the generator

[`generate_index.py`][] gains a check: for an `Archived` ADR naming a rule, every path under every
`scope` prefix must match some glob in that rule.

**Pros:** Catches the one failure Context names as the natural mistake, and needs no new
grammar, `scope` rejecting globs.
**Cons:** A check sees globs and prefixes, never comments — so it fails every archival that
legitimately composes a rule with comments in the files a rule cannot reach, which is the
shape the skill recommends.
**Risks:** What it should do about a composed defence has to be decided against a real
archival, and there is none here; a check specified without one is believed anyway.

### Option 4: Generate the rule from the ADR's frontmatter

A generator writes `.claude/rules/adr-NNN.md` from each decision's `scope` and `summary`, so
coverage holds by construction.

**Pros:** Coverage cannot drift from `scope`, one being derived from the other, and no
author translates prefixes into globs by hand.
**Cons:** `summary` says what was decided, not what to do, so the generated rule spends a
reader's context on an index row rather than an instruction.
**Risks:** Every matching read pulls in prose nobody wrote, which is how a mechanism meant
to cheapen context makes it dearer.

## Decision

Adopt Option 2, and treat the rule as a peer of the comment rather than its replacement.

Option 4 loses on the half no generator supplies. A rule earns its place by telling an
author what to do at the moment they would do otherwise, and that sentence has to be
written. [ADR 014][] made the same call against a checked citation schema: a mechanism that
buys the cheap half and reports a defended corpus is worse than none, because it is
believed.

Option 3 is postponed rather than rejected, and for 014's reason rather than that one. Glob
coverage is mechanically decidable, and saying otherwise would be wrong — but coverage is
not the whole bar, because defences compose, and the half a check cannot see is the same
half 014 could not check: where a comment sits, and whether it reaches. What such a check
should do with a rule that legitimately stops short has to be settled against a real
archival, and there is none here, so `revisit-when` carries it.

Listing the rule's own path in `scope` follows [ADR 013][], which puts [`pr.yml`][] in its
own scope because narrowing that filter is how the decision gets breached. Narrowing a
rule is how an archival gets breached, and the pre-commit lookup reports the ADR to
whoever stages that edit. A deletion escapes that lookup, and is caught later and
elsewhere.

## Consequences

- Archiving on a rule costs more than archiving on a comment: prefixes translated into
  globs, coverage checked against the file the globs least obviously reach, the rule named
  in `scope`, and the rule watched as it loads.
- No archival meets the bar this sets, the precedent included. The sibling ADR's coverage
  falls short, and [ADR 016][] cannot archive on this repository's `testing.md` for the same
  reason — that rule matches `**/test_*.py` and `**/*_test.py`, while 016 scopes `scripts/`,
  where ten modules are neither.
- `scope` now carries entries naming where a defence lives, not only where a breach is
authored — an extension of ADR 013's field for one case, leaving its test intact for every
other entry, so 013 is neither superseded nor discharged. `generate_index` validates such
an entry for `Archived` decisions as well as `Accepted` ones, so a deleted rule fails the
build — on whichever later change runs the generator, since deleting the rule alone
triggers neither the hook nor the `adr` job. It cannot tell that the entry names a rule,
that its globs cover anything, or that a symlinked form of the path reaches the file the
lookup will match.
- `docs/adr/` and `skills/writing-adrs/` in scope means an ADR commit now reports three
  decisions rather than two. ADR 013 answers that per-ADR: a scope wider than the decision
  is that ADR's to narrow, and this one is as wide as the decision.
- The skill ships to repositories whose agents load no rules at all. There the section
  qualifies nothing, which is the intended reading, and the dated semantics are theirs to
  re-measure with the probe it names.
- ADR 014's deferred liveness check now has two defence shapes to specify for rather than
  one. Its trigger — an ADR archived on a defence resting on a comment in code — is
  untouched: this decision neither meets it nor closes a way it could arrive.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[anthropics/claude-code#23478]: https://github.com/anthropics/claude-code/issues/23478
[filters-pydantic ADR 004]: https://github.com/todofixthis/filters-pydantic/blob/main/docs/adr/004-docstring-per-test-function.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`pr.yml`]: ../../.github/workflows/pr.yml
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
