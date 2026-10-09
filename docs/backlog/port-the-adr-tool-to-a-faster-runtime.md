# Porting the ADR tool to a compiled runtime would cut most of each hook event's cost

> Recorded 2026-10-08, while restating the hook budget in [ADR 034][] on the
> maintainer's request. The runtime — Cython, Go, Rust or another — is deliberately
> left open.

## What

Port the ADR tool — `adr.py`, `hook.py` and the parser `frontmatter.py`, all under
[`skills/writing-adrs/`][] — to a runtime that starts faster than CPython, and decide in an
ADR which runtime and how it reaches consumers.

Land ADR 034 first; the [PyYAML item][] tracks it. Its per-event figures are projections
until that implementation measures them, and those measurements are this item's baseline.

The new ADR replaces only ADR 034's delivery: the venv, `uv` and the launcher. It keeps the
rest, so it restates them rather than superseding them wholesale — YAML decides every value
with no type resolution, so `yes`, `34` and an ISO date stay strings; the line-level rules
stand (one field per line, no block scalar, no duplicate key); and so do the turn budget and
the 1 s p95 ceiling, which [ADR 025][] cites and which must keep a home. ADR 034's two
`uv`-only revisit conditions — a consumer without `uv`, and Claude Code installing Python
dependencies itself — lapse with `uv`, and are not carried over.

## Why it is still worth doing

Each hook event pays mostly for Python itself. ADR 022 split its 74 ms median into 2 ms for
the shell gate, 15 ms of interpreter start, 24 ms of imports, 5 ms of handler work over 24
decisions, and 28 ms of process spawning and jitter. ADR 034 projects about 21 ms more for
the venv's start and the PyYAML import. A compiled binary drops interpreter start and
imports outright. The cost compounds: in a repository with a managed `docs/adr/INDEX.md`,
every tool-calling turn fires about 1.7 events (elsewhere the shell gate exits in 2 ms).

It is not urgent. ADR 034's estimate sits inside both its bounds, and its named first lever
— caching the parsed corpus by file modification time — is far cheaper. Weigh the two
against each other before choosing this.

## What shapes the choice

- **Distribution.** The plugin installs from git, with no build step a consumer runs. A Go
  or Rust binary needs a prebuilt build per OS and architecture, shipped in the plugin or
  fetched at `SessionStart`; a toolchain on the consumer's machine is heavier than the `uv`
  ADR 034 asked for. Cython keeps CPython's start-up, so measure what it actually saves.
- **The shared code.** [`scripts/adr.py`][] and [`scripts/frontmatter.py`][] are symlinks
  into the skill (ADRs 023 and 035); [`scripts/backlog.py`][] imports `adr`, and
  [`scripts/ci/validate_manifests.py`][] imports the parser. A port leaves `scripts/` either
  calling the binary or keeping Python copies beside it — the duplication ADR 011 removed.
- **Every caller changes.** [`hooks/hooks.json`][], [`.githooks/pre-commit`][] and
  [`.github/workflows/pr.yml`][] run the tool, and `pr.yml` will hold ADR 034's p95 check.
- **The spec already exists.** The skill's `tests/`, including its drift test against
  `SKILL.md` (ADR 017), define the behaviour a port must match. Run them against the port
  rather than rewrite them.
- **What the tool may write** (ADR 023) and how it finds the repository (ADR 024) are
  behaviour, not implementation, and carry over unchanged.

## Acceptance

- An ADR records the runtime and distribution, restating what it keeps from ADR 034 and
  updating ADR 025's citation, with the cache lever weighed as an alternative.
- The port passes the existing suite, or a port of it shown to cover the same cases.
- The hook's mean cost per turn and p95 per event are measured before and after, on this
  repository's corpus and on `todofixthis/cookiecutter-py`'s, and recorded in the new ADR.
- `scripts/` either shares one parser with the tool or the ADR says why it does not.
- A consumer needs nothing beyond what the new ADR states, checked from a real session on a
  machine without the build toolchain.

[ADR 025]: ../adr/025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 034]: ../adr/034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md
[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[`.github/workflows/pr.yml`]: ../../.github/workflows/pr.yml
[`hooks/hooks.json`]: ../../hooks/hooks.json
[PyYAML item]: scripts-frontmatter-parser-should-use-pyyaml.md
[`scripts/adr.py`]: ../../scripts/adr.py
[`scripts/backlog.py`]: ../../scripts/backlog.py
[`scripts/ci/validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`scripts/frontmatter.py`]: ../../scripts/frontmatter.py
[`skills/writing-adrs/`]: ../../skills/writing-adrs/
