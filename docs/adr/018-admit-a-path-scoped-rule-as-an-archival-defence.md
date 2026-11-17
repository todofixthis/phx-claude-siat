---
status: Accepted
date: 2026-08-29
scope: [docs/adr/, skills/writing-adrs/]
summary: Admit a path-scoped rule as a third qualifying archival defence beside a code comment and a breach large enough to need its own ADR, qualifying only where its globs and any other named defence reach every path in scope bar the rule's own entry, judged by the author for now rather than checked by the generator or generated from frontmatter.
revisit-when: An ADR here is archived on a rule, making a coverage check specifiable; or the load semantics narrow — rules ceasing to load in a subagent, or shell-first reading becoming the default across sessions rather than one mode among several — degrading the archivals already made.
---

# 018: Admit a path-scoped rule as an archival defence

## Context

[`writing-adrs`][] archives a decision, keeping it in force while dropping it from the index
that agents load, only where a defence exists that a breacher meets while the work is still
being planned. The skill named two such defences: a comment wherever a breach would be
authored, and a breach so large it needs its own ADR. Both were written before an agent
could load instructions scoped to file globs.

A sibling repository has since archived a decision on a third defence.
[filters-pydantic ADR 004][] keeps a docstring-per-test-function convention in force and out of its index. A
rule file defends it: `.agents/rules/testing.md`, reached through a `.claude/rules` symlink,
whose `paths` frontmatter loads the convention whenever an agent reads a matching test file.
That ADR reached the defence through the skill's own escape hatch, "unless another meets
that same timing test", and the kind of defence holds up. Its coverage does not. The rule
matches only `**/test_*.py` against a scope of `test/` and `scripts/`, so most of what the
decision binds meets nothing, and the rule's own path is absent from that scope. The first
time anyone used a defence admitted on judgement alone, they judged it generously.

The load semantics are the other half of the problem. That ADR records one gap: a rule does
not load on the `Write` that creates a matching file ([anthropics/claude-code#23478][],
closed as not planned). It measured nothing else. This repository measured the rest against
its own [`testing.md`][], by reading a matching file first with the read tool and then with
`sed`. A rule loads on the read tool, in a subagent as well as in a main session. It does
not load on a shell read at all. The session that took the measurement ran under a harness
mode whose standing instruction was to prefer `sed` over the read tool. Under that mode the
defence would have been off for every file the session touched.

None of this was discoverable from a repository before this ADR. No `rg` answered "what
loads a rule", so an author who took the mechanism at its name archived a decision that
reads as defended and is not. It reads that way indefinitely, because an archived ADR is
invisible by design.

## Options

Options 2, 3, and 4 all put a decision's constraint into a second file that can drift from
the ADR, and all three rest on a harness feature this repository does not control. Neither
cost ranks them. What separates them is how much machinery stands behind the admission.

### Option 1: Do nothing — leave it to the escape hatch

The skill keeps its two named defences and, as now, admits any other that meets the timing
test.

**Pros:** The hatch has already carried one archival, and its choice of defence was right.
**Cons:** Each author re-derives the load semantics. The honest ones spend a probe, and the
rest guess.
**Risks:** The generous reading is the natural one, and the sibling ADR is the evidence. A
partial rule looks total, and the shortfall surfaces only when someone relitigates the
decision.

### Option 2: Admit it as an author-judged defence (Accepted)

`writing-adrs` names the rule beside the comment and states what a qualifying rule must do.
Its globs, or another named defence, must reach every path in `scope` except the rule's own
entry. The rule must name the ADR and state the constraint, be written in the same change as
the archival, live in the repository, and be named in `archived-because`. Its own path must
be listed in `scope`. The load semantics go in with a date and the probe that produced them.
Nothing checks any of it.

**Cons:** It rests on the same author judgement that read the first rule generously.
**Risks:** The dated semantics go stale on somebody else's release schedule. A reader who
trusts them then archives on a rule the harness has stopped loading.

### Option 3: Admit it and check glob coverage in the generator

[`adr.py`][] gains a check. For an `Archived` ADR that names a rule, every path under every
`scope` prefix must match some glob in that rule.

**Pros:** It catches the one failure that Context names as the natural mistake. It needs no
new grammar, because `scope` rejects globs.
**Cons:** A check sees globs and prefixes, never comments. It therefore fails every archival
that legitimately composes a rule with comments in the files the rule cannot reach, and that
is the shape the skill recommends.
**Risks:** What the check should do about a composed defence has to be decided against a
real archival, and there is none here. A check specified without one is believed anyway.

### Option 4: Generate the rule from the ADR's frontmatter

A generator writes `.agents/rules/adr-NNN.md` from each decision's `scope` and `summary`, so
coverage holds by construction.

**Pros:** Coverage cannot drift from `scope`, because the generator derives one from the
other, and no author translates prefixes into globs by hand.
**Cons:** `summary` says what was decided, not what to do, so the generated rule spends a
reader's context on an index row rather than an instruction.
**Risks:** ~~Every matching read pulls in prose nobody wrote, which is how a mechanism
meant to cheapen context makes it dearer.~~ Measured after this ADR and found to be once
per rule per session, not once per read. See ADR 019.

## Decision

Adopt Option 2, and treat the rule as a peer of the comment rather than its replacement.

Option 4 loses on the half that no generator supplies. A rule earns its place by telling an
author what to do at the moment they would do otherwise, and someone has to write that
sentence. [ADR 014][] made the same call against a checked citation schema: a mechanism that
buys the cheap half and reports a defended corpus is worse than none, because people
believe it.

Option 3 is postponed rather than rejected, and for 014's reason rather than Option 4's.
Glob coverage is mechanically decidable, and saying otherwise would be wrong. But coverage
is not the whole bar, because defences compose. The half a check cannot see is the half 014
could not check: where a comment sits, and whether it reaches. What such a check should do
with a rule that legitimately stops short has to be settled against a real archival, and
there is none here, so `revisit-when` carries it.

Listing the rule's own path in `scope` follows [ADR 013][], which puts [`pr.yml`][] in its
own scope because narrowing that filter is how someone breaches that decision. Narrowing a
rule is how someone breaches an archival, and the pre-commit lookup reports the ADR to
whoever stages that edit. A deletion escapes that lookup, and is caught later and elsewhere.

## Consequences

- Archiving on a rule costs more than archiving on a comment. The author translates prefixes
  into globs, checks coverage against the file the globs least obviously reach, names the
  rule in `scope`, and watches the rule load.
- No archival meets the bar this ADR sets, the precedent included. The sibling ADR's
  coverage falls short, and [ADR 016][] cannot archive on this repository's `testing.md` for
  the same reason. That rule matches `**/test_*.py` and `**/*_test.py`, while 016 scopes
  `scripts/`, where ten modules match neither.
- `scope` now carries entries that name where a defence lives, not only where a breach is
  authored. This extends ADR 013's field for one case and leaves its test intact for every
  other entry, so 013 is neither superseded nor discharged. `generate_index` validates such
  an entry for `Archived` decisions as well as `Accepted` ones, so a deleted rule fails the
  build. It fails on whichever later change runs the generator, since deleting the rule
  alone triggers neither the hook nor the `adr` job. The generator cannot tell that the
  entry names a rule, that its globs cover anything, or that a symlinked form of the path
  reaches the file the lookup will match.
- With `docs/adr/` and `skills/writing-adrs/` in scope, an ADR commit now reports three
  decisions rather than two. ADR 013 answers that per ADR: a scope wider than the decision
  is that ADR's to narrow, and this one is as wide as the decision.
- The skill ships to repositories whose agents load no rules at all. There the section
  qualifies nothing, which is the intended reading, and the dated semantics are theirs to
  re-measure with the probe the section names.
- ADR 014's deferred liveness check now has two defence shapes to specify for rather than
  one. Its trigger, an ADR archived on a defence that rests on a comment in code, is
  untouched. This decision neither meets that trigger nor closes a way it could arrive.
- The `.claude/rules` symlink is required here, not tidying. Claude Code scans only that
  path, so removing the symlink stops every rule loading, and nothing reports it. Measured
  by parking the symlink and re-reading a matching test file, which injected nothing.
- A later measurement showed that Option 4's risk overstated the cost: a rule loads once
  per session, at the first matching read, not once per matching read. [ADR 019][] carries
  the measurement and the decision it settled. This ADR's reasoning is unchanged, because
  Option 4 lost on the judgement a generator cannot make.

## Revisit watch

Re-measured 2026-09-01 against `testing.md`, whose globs are `**/test_*.py` and
`**/*_test.py`. The matching file was `scripts/adr/test_generate_index.py`, and the
non-matching one was `scripts/adr/generate_index.py` beside it. Each reader then reported
what had arrived unasked, without opening anything under `.agents/`. Each reader was also
asked for a Python line-length rule this repository does not have, and said it had none, so
the "yes" rows are not readers agreeing with the question. Each arm gave this result:

| Reader, tool, file | Rule loaded |
|---|---|
| Subagent, read tool, matching | yes, nine headings quoted correctly |
| Subagent, read tool, non-matching | no |
| Subagent, `sed -n '1,60p'`, matching | no |
| Main session, read tool, matching | yes |

Re-running this needs **one fresh context per arm**. A rule loads once per session, at the
first matching read (ADR 019), so arms that share a context return a spurious yes for every
arm after the first.

**Limb 1, an archival on a rule, is the limb the reader of this section stands on.** It
has not fired, because nothing here is `Archived` on a rule yet. When your archival is on
a rule, the limb fires, and it unlocks Option 3. The Decision parks Option 3 because what
a coverage check "should do with a rule that legitimately stops short has to be settled
against a real archival, and there is none here". Your archival is that case, so settle it
rather than only re-running the probe.

**Limb 2's first clause, rules ceasing to load in a subagent, has not fired.** The subagent
arm still loads the rule, and this section measures the main-session arm rather than
carrying it over from Context.

**Limb 2's second clause, shell-first reading becoming the default, is live and
unsettled.** This session ran under a standing instruction, which the harness itself calls
auto mode, to prefer `cat`, `head`, and `sed -n` over the read tool wherever they would do.
It is the same mode the original measurement ran under, and this is the second session
known to run under it. That is enough to say the mode is not a one-off, and not enough to
call it a default. Two observations by one author in one repository under one harness
configuration are not independent samples, and counting more of them the same way never
settles the question. Two things would settle it: the harness documenting the mode as a
default, or the mode arriving in a session that did not opt into it.

Until then the hazard is per session rather than global, and a single session is enough
for it to bite. **Before you rely on a rule as a defence, check whether your own session is
shell-first.** In a shell-first session you read a matching file with `sed` and meet
nothing. The decision you archived is then undefended for the whole session, and nothing
reports it. The third arm above is exactly that case.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 019]: 019-do-not-generate-path-scoped-rules-from-adr-frontmatter.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[anthropics/claude-code#23478]: https://github.com/anthropics/claude-code/issues/23478
[filters-pydantic ADR 004]: https://github.com/todofixthis/filters-pydantic/blob/main/docs/adr/004-docstring-per-test-function.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
