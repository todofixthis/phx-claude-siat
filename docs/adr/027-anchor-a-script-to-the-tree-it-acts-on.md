---
status: Accepted
date: 2026-09-03
scope: [.agents/rules/testing.md, scripts/, skills/]
summary: Anchor each path a script resolves to the tree that path acts on — a file the script ships with resolves from __file__, a target in the caller's tree from the path in hand or the working directory; no anchor is the rule for every path, which is what ADR 016 claimed.
revisit-when: A script needs a default path into a tree that is neither the one it ships in nor the caller's, so neither anchor names it.
---

# 027: Anchor a script to the tree it acts on

## Context

[ADR 016][] anchored every script's default paths to `__file__`, "with no exception", so a
script given no path acts on the tree it ships in, and set one revisit trigger: a script that
must resolve a path it was given no argument for against the caller's checkout. [ADR 024][]
met that condition — the `writing-adrs` tool ships in a plugin cache and acts on a consumer's
tree, so it resolves its root from the path in hand — and recorded the meeting as a
discharge, leaving 016 in force.

Review of the pull request carrying both ([#53][]) found the result contradictory: two
decisions in force, one saying every script anchors to `__file__`, the other that a class of
script must not. [`writing-adrs`][] already draws the line the classification crossed: a
decision that *answers* a condition discharges the trigger, one that *reverses* the older
decision supersedes it. 024 reverses 016's universal claim for one class.

Two scripts already resolve paths of both kinds. [`scan.py`][] anchors its bundled fixtures
to `__file__`, as [ADR 003][] requires of every file a skill ships with, and sweeps the paths
it is given, defaulting to the working directory the person typed in. [`mutate.py`][] takes
its target file as a required argument and runs its test command in the working directory,
which 016 named as deliberate. Neither is a script of one kind.

## Options

Options 2 and 3 both supersede 016 and both move its code citations. That cost is shared
and does not rank them.

### Option 1: Do nothing

Keep 016 `Accepted` with its trigger discharged, and 024 beside it.

**Pros:** No further ADR, and 016's mechanics are unchanged for the scripts they govern.
**Cons:** "Every script, with no exception" stays in force while false. A reader of 016 has
no way to tell which rule binds a script they are about to write.
**Risks:** The next shipped tool copies whichever anchor its author read first.

### Option 2: Anchor each path to the tree it acts on, superseding 016 (Accepted)

One rule, applied per path rather than per script. A file the script ships with — a fixture,
a table, a sibling module — resolves from `__file__`, which ADR 003 already settles for
skills. A target in the caller's tree resolves from the path in hand, or from the working
directory where a person ran the tool with no path, which 024 sets out. A repository script
under `scripts/` acts on the tree it ships in, so its default *paths* are of the first kind
and 016's mechanics stand for them unchanged; `mutate.py`'s child test command runs in the
working directory by design, which is the second kind, and is why the rule is per path.

**Pros:** Names the question a script's author answers for each default path, and each
answer keeps the mechanics its ADR already argued. Fits the two scripts that mix kinds.
**Cons:** Location becomes a heuristic — `scripts/` is where own-tree scripts live today —
rather than the rule, so a reader has to ask the question rather than read the directory.
**Risks:** A path into a third tree — a repository the caller names — has no anchor here
and stays an argument; a script that needs a default for one is the revisit condition.

### Option 3: Widen 024 to cover `scripts/` and supersede 016 with it

**Pros:** One fewer ADR.
**Cons:** 024 is a resolution order for a tool with no tree of its own; the repository
scripts have one, and a rule that walks up from the path in hand is wrong for them.
Widening 024 mixes two mechanisms under one number.
**Risks:** 024's own trigger, a configurable ADR directory, would then reopen `scripts/`.

## Decision

Option 2. The contradiction is in 016's universality, not in either mechanism, so the
restatement keeps both and replaces "every" with the question that selects between them.
016 is superseded rather than edited: narrowing a decision's claim changes the decision,
which "supersede, don't edit" reserves for a new ADR.

016's mechanics carry forward for every own-tree default, so they are restated here rather
than left in a superseded file: the anchor is `Path(__file__).resolve()`, read on the
`__main__` line and nowhere else; every function below it, entry points included, requires
the root rather than defaulting it, so a test injects a fixture root and can never reach the
real repository by omitting one; path constants stay repo-relative and are joined to the
root where they are read, so messages name a path a reader can act on.

The discharge 024 recorded on 016 was the wrong classification and is withdrawn: a reversal
supersedes, and a discharge on a superseded ADR is dead metadata. `writing-adrs` gains the
case in its discharge workflow, so the next answered trigger that contradicts a claim in the
older ADR is recognised as a partial supersession.

## Consequences

- 016 is `Superseded` by this ADR and loses its `revisit-discharged-by`; its body's
  struck-through trigger names this ADR.
- 024's Decision no longer claims to discharge 016; it answers the condition 016 waited on,
  and this ADR carries the supersession.
- Code and rule citations of ADR 016 — in `scripts/ci/` and in `.agents/rules/testing.md`,
  which already states both stances — cite this ADR. A citation left pointing at 016 still
  resolves through its `superseded-by`.
- A new script's author answers the question per default path; the testing rule tells a
  test author which stance the module under test took, and the two must agree.

[#53]: https://github.com/todofixthis/phx-claude-siat/pull/53
[ADR 003]: 003-locate-skill-assets-relative-to-skill-directory.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[`mutate.py`]: ../../scripts/dev/mutate.py
[`scan.py`]: ../../skills/nz-english/scan.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
