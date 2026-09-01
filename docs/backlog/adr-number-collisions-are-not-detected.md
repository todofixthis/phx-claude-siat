# Two ADRs can share a number without anything failing

> Recorded 2026-09-01, found when rebasing a feature branch onto `develop` produced two
> ADR 018s. Never filed as a GitHub issue.

## What

[`generate_index.py`][] never compares ADR numbers. Rebasing `feature/retire-github-issues`
onto `develop` brought in `018-admit-a-path-scoped-rule-as-an-archival-defence.md` beside
the branch's own `018-track-deferred-work-in-the-repository.md`, and everything passed:

- the generator regenerated `docs/adr/INDEX.md` with two rows labelled `018` and exited 0;
- `.githooks/pre-commit` committed it without comment;
- the `adr` job in `pr.yml`, which regenerates the index and fails on a diff, went green —
  it compares the index against the ADRs, and both agreed there were two 018s.

The collision was found by reading the directory listing, which is the only thing that
found it.

## Why it is worth doing

`phx:writing-adrs` fixes the numbering as "never reuse or renumber", so a collision has to
be caught before the second one merges — afterwards the fix is renumbering something
already referenced, which is the thing the rule forbids. Nothing enforces it.

The collision is also the normal case rather than a freak one. Numbers are allocated by
reading the directory at authoring time, so any two branches open at once allocate the
same next number, and this repo routinely has a feature branch and a `claude/…` branch in
flight together. It went unnoticed here only because a person asked.

What makes it worth fixing rather than watching for: every downstream reference is by
number. `ADR 018` in a comment, an `archived-because`, or a `[ADR 018]` link target resolves
to whichever file the reader opens first, and both resolve — so a wrong one reads as
correct.

## Acceptance

- Two ADR files sharing a number is an error naming both paths, raised where the existing
  frontmatter and scope problems are raised, so the pre-commit hook and the `adr` job both
  catch it.
- A fixture covers it. The real tree is single-numbered and will stay that way, so a check
  written against it alone would pass while checking nothing.
- The message says to renumber the unmerged one, since the merged number is the one that
  cannot move.

[`generate_index.py`]: ../../scripts/adr/generate_index.py
