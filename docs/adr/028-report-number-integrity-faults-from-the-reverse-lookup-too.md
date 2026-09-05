---
status: Accepted
date: 2026-09-05
scope: [skills/writing-adrs/adr.py]
summary: The `for` reverse lookup (`binding()`) also reports a shared ADR number and a heading/filename mismatch, compared by value like `index` does, and never turns either into a refusal.
revisit-when: The reverse lookup's exit code needs to gate rather than merely advise, or hook.py's per-touch warnings from binding() are measured as noise worth deduping like ADR 026's other findings.
---

# 028: Report number-integrity faults from the reverse lookup too

## Context

[`inspect()`][], which [ADR 013][]'s `index` command renders into `INDEX.md`, checks two
number-integrity faults: two ADRs sharing a number, and an ADR whose heading number
disagrees with its filename. `binding()` — the reverse lookup `for` runs, and the one
[`.githooks/pre-commit`][] runs advisory on every staged path — checks neither, and
discards the heading number outright. So while either fault sits on disk, `for` renders it
wrong rather than saying nothing:

- two ADRs sharing a number list as two decisions, each printed with the number its own
  filename spells, instead of the one shared decision with a fault to fix;
- an ADR whose heading disagrees with its filename is rendered with the number from one
  file and the title from the other, naming a decision that does not exist.

`index` fails as soon as any ADR is staged, and `pr.yml`'s `adr` job runs on every pull
request regardless of what it touches ([ADR 021][]), so neither fault survives a commit
that stages an ADR, or a pull request. What is undetected is the window before either
fires — an ADR staged alongside unrelated work, or committed straight to a `develop`
bypass ([ADR 009][]) — and `binding()`'s advisory is, per ADR 013, the one place a
reader meets a bound decision without going looking. A row that is secretly one decision,
or that names a decision that does not exist, is exactly the reading that place is least
equipped to give.

[ADR 025][] has `hook.py`'s `PreToolUse` handler call `binding()` directly, once per agent
per touched path, so wherever the fix lives decides whether that live session hook gains
it too.

## Options

### Option 1: Do nothing

Leave `binding()` checking scope alone, as today.

**Pros:** No change to a function three other callers already depend on.
**Cons:** The advisory keeps misrendering both faults instead of naming them or staying
silent.
**Risks:** A later change to `inspect()`'s checks has no reason to touch `binding()`, so
the two stay divergent by default rather than by decision — the way they already had.

### Option 2: Report both faults from `binding()`, sharing `inspect()`'s comparison (Accepted)

Extract the by-value comparison `inspect()` already uses — a number and its heading
compared as integers, and a `dict[int, str]` of claimed numbers — into functions both
`inspect()` and `binding()` call, so the two can no longer check this differently by
accident. `binding()` warns on stderr and skips the file for either fault, the pattern it
already uses for a file that cannot be parsed at all. `command_for()`'s exit code is
untouched: it returns 0 by convention, being advisory rather than a gate.

**Pros:** Costs two small helper functions shared with `inspect()`.
**Cons:** `hook.py`'s `PreToolUse` handler inherits the same stderr warnings, unfiltered by
[ADR 026][]'s per-session dedup.

### Option 3: Check only in `command_for()`, leaving `binding()` and `hook.py` blind

Compare the numbers among the rows `binding()` already returned, inside `command_for()`
itself, after the call.

**Pros:** Confines the new code to the one caller that is advisory by convention, and
`hook.py`'s live session hook never sees the new warnings.
**Cons:** A collision or a mismatch is a property of the two files on disk, not of one
query's matches — checking it after `binding()` has already filtered to scope matches
misses a colliding pair where only one of the two binds the path in hand, which is most of
the time a collision matters at all. Reaching every ADR regardless of scope match means
either duplicating `binding()`'s directory walk inside `command_for()` too, or leaving
`hook.py` — which touches far more paths per session than a commit touches per commit —
carrying the same silent gap this ADR exists to close.

## Decision

Extend `binding()` itself (Option 2). The fault is a property of the corpus, not of one
query, so the function that already walks every ADR to answer one is where the check
belongs; bolting it onto `command_for()` would mean walking the directory twice or leaving
`hook.py` uninformed, defeating the point of fixing this once rather than per caller.

`binding()` reuses `inspect()`'s comparison rather than writing its own: the bug this ADR
closes is that the two had already diverged once, so encoding "by value" a second time in
a second place would only give the next divergence somewhere new to hide. Both faults stay
warnings, and `command_for()` keeps exiting 0 regardless of what it reported — a reverse
lookup that names a fault but refuses the commit over it would be a gate wearing an
advisory's contract, and nothing here calls for one: ADR 021's pull-request gate already
refuses a build over these two faults the moment an ADR is staged.

The noise Option 2's Cons raises for `hook.py` is not a new profile: the existing "could
not be read" warning there already prints unfiltered on every touch of an unparseable ADR,
so these two more cases fit a contract ADR 025 already accepted rather than opening one.

## Consequences

- `binding()` takes a `dict[int, str]` of claimed numbers, matching `inspect()`'s, and
  warns on stderr for a collision or a heading/filename mismatch, skipping the file for
  either — the same shape as its existing warning for a file that cannot be parsed at all.
- `hook.py`'s `PreToolUse` handler prints these warnings on every touched path while a
  fault stands, the same as it already does for an unparseable ADR.
- A later change to either check updates the shared comparison once, not `inspect()` and
  `binding()` separately — the reason this bug existed in the first place.

[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 021]: 021-validate-adr-scope-on-every-pull-request.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[`inspect()`]: ../../skills/writing-adrs/adr.py
