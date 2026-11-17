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
script given no path acts on the tree it ships in. ADR 016 set one revisit trigger: a script
that must resolve a path it was given no argument for against the caller's checkout.
[ADR 024][] met that condition. The `writing-adrs` tool ships in a plugin cache and acts on
a consumer's tree, so it resolves its root from the path in hand. ADR 024 recorded this as
a discharge and left 016 in force.

Review of the pull request that carried both ADRs ([#53][]) found the result
contradictory. Two decisions were in force: one said every script anchors to `__file__`,
and the other said a class of script must not. [`writing-adrs`][] already draws the line
that this classification crossed. A decision that *answers* a condition discharges the
trigger, and a decision that *reverses* the older decision supersedes it. 024 reverses
016's universal claim for one class of script.

Two scripts already resolve paths of both kinds. [`scan.py`][] anchors its bundled fixtures
to `__file__`, as [ADR 003][] requires of every file a skill ships with. It sweeps the
paths it is given, and defaults to the working directory the person typed in.
[`mutate.py`][] takes its target file as a required argument, and runs its test command in
the working directory, which 016 named as deliberate. Neither is a script of one kind.

## Options

Options 2 and 3 both supersede 016, and both move its code citations. That cost is shared
and does not rank them.

### Option 1: Do nothing

Keep 016 `Accepted` with its trigger discharged, and keep 024 beside it.

**Pros:** No further ADR is needed, and 016's mechanics stay unchanged for the scripts
they govern.
**Cons:** "Every script, with no exception" stays in force while false. A reader of 016
cannot tell which rule binds a script they are about to write.
**Risks:** The next shipped tool copies whichever anchor its author read first.

### Option 2: Anchor each path to the tree it acts on, superseding 016 (Accepted)

One rule applies per path rather than per script:

- A file the script ships with, such as a fixture, a table, or a sibling module, resolves
  from `__file__`. ADR 003 already settles this for skills.
- A target in the caller's tree resolves from the path in hand. Where a person ran the tool
  with no path, it resolves from the working directory. 024 sets this out.

A repository script under `scripts/` acts on the tree it ships in, so its default *paths*
are of the first kind, and 016's mechanics stand for them unchanged. `mutate.py`'s child
test command runs in the working directory by design, which is the second kind. That
command is why the rule applies per path.

**Pros:** The rule names the question a script's author answers for each default path,
and each answer keeps the mechanics its ADR already argued. It fits the two scripts that
mix kinds.
**Cons:** Location becomes a heuristic rather than the rule: `scripts/` is where own-tree
scripts live today. A reader has to ask the question instead of reading the directory.
**Risks:** A path into a third tree, such as a repository the caller names, has no anchor
here and stays an argument. A script that needs a default for one is the revisit
condition.

### Option 3: Widen 024 to cover `scripts/` and supersede 016 with it

**Pros:** It needs one fewer ADR.
**Cons:** 024 is a resolution order for a tool with no tree of its own. The repository
scripts have a tree of their own, and a rule that walks up from the path in hand is wrong
for them. Widening 024 mixes two mechanisms under one number.
**Risks:** 024's own trigger, a configurable ADR directory, would then reopen `scripts/`.

## Decision

Option 2. The contradiction lies in 016's universality, not in either mechanism. The
restatement therefore keeps both mechanisms and replaces "every" with the question that
selects between them. This ADR supersedes 016 rather than editing it, because narrowing a
decision's claim changes the decision, and "supersede, don't edit" reserves that for a new
ADR.

016's mechanics carry forward for every own-tree default, so this ADR restates them rather
than leaving them in a superseded file:

- The anchor is `Path(__file__).resolve()`, read on the `__main__` line and nowhere else.
- Every function below the anchor in the call chain, entry points included, requires the root
  rather than defaulting it. A test therefore injects a fixture root, and cannot reach the
  real repository by omitting one.
- Path constants stay repo-relative and are joined to the root where they are read, so
  messages name a path a reader can act on.

The discharge that 024 recorded on 016 was the wrong classification, and this ADR
withdraws it. A reversal supersedes, and a discharge on a superseded ADR is dead metadata.
`writing-adrs` gains the case in its discharge workflow. The next answered trigger that
contradicts a claim in the older ADR is then recognised as a partial supersession.

## Consequences

- 016 is `Superseded` by this ADR and loses its `revisit-discharged-by`. The struck-through
  trigger in its body names this ADR.
- 024's Decision no longer claims to discharge 016. It answers the condition 016 waited
  on, and this ADR carries the supersession.
- Code and rule citations of ADR 016 now cite this ADR. They sit in `scripts/ci/` and in
  `.agents/rules/testing.md`, which already states both stances. A citation left pointing
  at 016 still resolves through its `superseded-by`.
- A new script's author answers the question for each default path. The testing rule
  tells a test author which stance the module under test took, and the two must agree.

[#53]: https://github.com/todofixthis/phx-claude-siat/pull/53
[ADR 003]: 003-locate-skill-assets-relative-to-skill-directory.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[`mutate.py`]: ../../scripts/dev/mutate.py
[`scan.py`]: ../../skills/nz-english/scan.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
