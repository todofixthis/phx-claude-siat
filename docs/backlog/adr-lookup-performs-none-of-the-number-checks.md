# The `--for` lookup performs none of the index generator's number checks

> Recorded 2026-09-01, from the test-analyst and surrogate passes on the ADR number
> collision check — the item that check closed was
> `adr-number-collisions-are-not-detected.md`. Never filed as a GitHub issue.

## What

Both number checks live in `generate()`, which writes `docs/adr/INDEX.md`.
[`generate_index.py`][]'s `report_scoped_to()` — the `--for` reverse lookup — does neither,
and its call discards the heading number in a `_`. So:

- **two ADRs sharing a number** list as two decisions, each printed with the number its
  filename spells:

  ```
  001 (Accepted): … — docs/adr/001-a.md
  1 (Accepted): … — docs/adr/1-b.md
  ```

- **an ADR whose heading disagrees with its filename** is reported the way the index would
  have rendered it, number from the filename and title from the heading, naming a decision
  that does not exist.

[`.githooks/pre-commit`][] reaches this. It runs `generate` only when a
`docs/adr/[0-9]*-*.md` path is staged, but runs `--for` over every staged path — so a
commit touching only `scripts/` meets the advisory while either fault sits undetected on
disk.

## Why it is still worth doing

The window is narrow, and that narrowness is the argument for deferring rather than for
ignoring: `generate` fails as soon as any ADR is staged, and `pr.yml`'s `adr` job runs on
any change under `docs/adr/` or `scripts/`, so neither fault can survive a pull request.
What survives is the interval before either fires — and the advisory is the one place a
reader meets these decisions without going looking, which is the whole argument for it in
ADR 013. Rows that are secretly one decision, or that name a decision that does not exist,
are the readings it is least equipped to give.

## The design call to make first

Whether the advisory should report either fault at all. `report_scoped_to()` returns 0 by
convention, being advisory rather than a gate, and that contract is what a warning has to
fit. Note the hook does not enforce it — its `--for` line ends `|| exit 0`, so a non-zero
return would be swallowed there — but `pr.yml` and any later caller read the code, so the
contract is real and belongs in the decision rather than being inferred from the hook.

## Acceptance

- A decision is recorded on whether the advisory reports these faults. If yes, an ADR records
  the lookup's contract; if no, the reasoning is recorded where the next reader meets it —
  an ADR, or a `revisit-when` on ADR 013 — before this file is deleted. Deleting it on a
  bare "no" erases the analysis and the same output gets re-filed by the next review pass.
- If it reports, it stays exit 0: the lookup is advisory, and a commit is not refused over
  a decision it merely mentions.
- Fixtures in [`test_generate_index.py`][] cover whichever way it settles, `ReportScopedToTests`
  having no case with two ADRs sharing a number, and none with a disagreeing heading.

[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`test_generate_index.py`]: ../../scripts/adr/test_generate_index.py
