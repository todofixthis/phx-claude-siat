---
status: Accepted
date: 2026-09-05
scope: [skills/writing-adrs/adr.py]
summary: The `for` reverse lookup (`binding()`) also reports a shared ADR number and a heading/filename mismatch, compared by value like `index` does, and never turns either into a refusal.
revisit-when: The reverse lookup's exit code needs to gate rather than merely advise, or hook.py's per-touch warnings from binding() are measured as noise worth deduping like ADR 026's other findings.
---

# 029: Report number-integrity faults from the reverse lookup too

## Context

[ADR 013][]'s `index` command renders the output of [`inspect()`][] into `INDEX.md`.
`inspect()` checks two number-integrity faults: two ADRs that share a number, and an ADR
whose heading number disagrees with its filename. `binding()` checks neither, and throws
away the heading number. `binding()` is the reverse lookup that `for` runs, and that
[`.githooks/pre-commit`][] runs as an advisory on every staged path. While either fault
sits on disk, `for` renders it wrongly instead of saying nothing:

- Two ADRs that share a number appear as two decisions, each printed with the number its
  own filename spells. They do not appear as the one shared decision with a fault to fix.
- An ADR whose heading disagrees with its filename appears with the number from one and
  the title from the other, naming a decision that does not exist.

`index` fails as soon as any ADR is staged. `pr.yml`'s `adr` job runs on every pull
request, whatever it touches ([ADR 021][]). Neither fault therefore survives a commit that
stages an ADR, or a pull request. What goes undetected is the window before either check
fires: an ADR staged alongside unrelated work, or committed straight to `develop` through
the bypass ([ADR 009][]). Per ADR 013, `binding()`'s advisory is the one place a reader
meets a bound decision without going looking. A row that is secretly one decision, or that
names a decision that does not exist, is the reading that place is least able to give.

[ADR 025][] has `hook.py`'s `PreToolUse` handler call `binding()` directly, once per agent
per touched path. Where the fix lives therefore decides whether that live session hook
gets it too.

## Options

### Option 1: Do nothing

Leave `binding()` checking scope alone, as it does today.

**Pros:** No change to a function that three other callers already depend on.
**Cons:** The advisory keeps rendering both faults wrongly instead of naming them or
staying silent.
**Risks:** A later change to the checks in `inspect()` has no reason to touch `binding()`.
The two stay divergent by default rather than by decision, as they already were.

### Option 2: Report both faults from `binding()`, sharing `inspect()`'s comparison (Accepted)

Move the by-value comparison that `inspect()` already uses into functions that both
`inspect()` and `binding()` call. The comparison treats a number and its heading as
integers, and keeps a `dict[int, str]` of claimed numbers. Sharing it means the two
functions can no longer check this differently by accident. For either fault, `binding()`
warns on stderr and skips the file, as it already does for a file it cannot parse at all.
The exit code of `command_for()` is untouched. It returns 0 by convention, because it is
advisory rather than a gate.

**Pros:** The cost is two small helper functions shared with `inspect()`.
**Cons:** `hook.py`'s `PreToolUse` handler inherits the same stderr warnings, which
[ADR 026][]'s per-session dedup does not filter.

### Option 3: Check only in `command_for()`, leaving `binding()` and `hook.py` blind

Compare the numbers among the rows that `binding()` already returned, inside
`command_for()` itself, after the call.

**Pros:** The new code stays in the one caller that is advisory by convention, and
`hook.py`'s live session hook never sees the new warnings.
**Cons:** A collision or a mismatch is a property of the two files on disk, not of one
query's matches. By the time `command_for()` runs, `binding()` has already filtered to
scope matches. The check would miss a colliding pair where only one of the two binds the
path in hand, and that is most of the cases where a collision matters at all. To reach
every ADR whatever its scope, `command_for()` would have to repeat `binding()`'s directory
walk. The alternative leaves `hook.py` with the same silent gap this ADR exists to close,
and `hook.py` touches far more paths per session than a commit touches.

## Decision

Extend `binding()` itself (Option 2). The fault is a property of the corpus, not of one
query. `binding()` already walks every ADR to answer a query, so the check belongs there.
Adding it to `command_for()` would mean walking the directory twice or leaving `hook.py`
uninformed, and the point is to fix this once rather than in each caller.

`binding()` reuses the comparison from `inspect()` rather than writing its own. The bug
this ADR closes is that the two had already diverged once. Writing "by value" a second
time in a second place would only give the next divergence somewhere new to hide.

Both faults stay warnings, and `command_for()` keeps exiting 0 whatever it reported. A
reverse lookup that names a fault and refuses the commit over it would be a gate posing as
an advisory, and nothing here calls for one. ADR 021's pull-request gate already
refuses a build over these two faults as soon as an ADR is staged.

Option 2's Cons raise the noise for `hook.py`, but that noise is not new. The hook already
prints the existing "could not be read" warning, unfiltered, on every touch of an
unparseable ADR. These two cases fit a contract that ADR 025 already accepted, rather than
opening a new one.

## Consequences

- `binding()` takes a `dict[int, str]` of claimed numbers, matching `inspect()`. For a
  collision or a heading and filename mismatch, it warns on stderr and skips the file. That
  is the same shape as its existing warning for a file it cannot parse at all.
- While a fault stands, `hook.py`'s `PreToolUse` handler prints these warnings on every
  touched path, as it already does for an unparseable ADR.
- A later change to either check updates the shared comparison once, not `inspect()` and
  `binding()` separately. Separate copies are the reason this bug existed.

## Revisit watch

- 2026-10-03: the second clause, "hook.py's per-touch warnings from binding() are measured
  as noise worth deduping", **not fired**. Three `hook.py` runs on one path, in a corpus
  holding two files numbered 003, printed the warning to stderr each time and put none of
  it in stdout. The hooks reference says stderr from a hook that exits 0 goes only to the
  debug log. The Consequences' "prints on every touched path" therefore costs the agent no
  context, and also shows it nothing. The findings route (`SessionStart`, `PostToolBatch`,
  `Stop`) still reports the fault. Only the per-path "binds nothing here" line is lost. See
  [`hook-warnings-from-binding-reach-nobody.md`](../backlog/hook-warnings-from-binding-reach-nobody.md).

[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 021]: 021-validate-adr-scope-on-every-pull-request.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[`inspect()`]: ../../skills/writing-adrs/adr.py
