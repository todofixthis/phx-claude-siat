# Porting the ADR tool to a compiled runtime would cut most of each hook event's cost

> Recorded 2026-10-08, while restating the hook budget in [ADR 034][] at the
> maintainer's request. The runtime, whether Cython, Go, Rust, or another, is deliberately
> left open.

## What

Port the ADR tool to a runtime that starts faster than CPython, and decide in an ADR which
runtime to use and how it reaches consumers. The tool is `adr.py`, `hook.py`, and the
parser `frontmatter.py`, all under [`skills/writing-adrs/`][].

ADR 034 and [ADR 035][] are implemented. ADR 034's Revisit watch holds the per-event and
per-turn figures measured then, on 2026-10-13, and those figures are this item's baseline.

The new ADR replaces only ADR 034's delivery: the venv, `uv`, and the launcher. It keeps
the rest of ADR 034, so it restates those parts rather than superseding the whole ADR. It
keeps three things:

- YAML decides every value with no type resolution, so `yes`, `34`, and an ISO date stay
  strings.
- The line-level rules stand: one field per line, no block scalar, and no duplicate key.
- The turn budget and the 1 s p95 ceiling stand. [ADR 025][] cites them, and they must
  keep a home.

ADR 034's two `uv`-only revisit conditions lapse with `uv` and are not carried over. They
are a consumer without `uv`, and Claude Code installing Python dependencies itself.

## Why it is still worth doing

Each hook event pays mostly for Python itself. ADR 022 split its 74 ms median into 2 ms for
the shell gate, 15 ms of interpreter start, 24 ms of imports, 5 ms of handler work over 24
decisions, and 28 ms of process spawning and jitter. ADR 034 projects about 21 ms more for
the venv's start and the PyYAML import. A compiled binary drops interpreter start and
imports entirely. The cost compounds. In a repository with a managed `docs/adr/INDEX.md`,
every tool-calling turn fires about 1.7 events. Elsewhere, the shell gate exits in 2 ms.

It is not urgent. ADR 034's estimate sits inside both its bounds, and its named first
lever, caching the parsed corpus by file modification time, is far cheaper. Weigh the two
against each other before choosing this port.

## What shapes the choice

- **Distribution.** The plugin installs from git, with no build step for a consumer to
  run. A Go or Rust binary needs a prebuilt build per OS and architecture, shipped in the
  plugin or fetched at `SessionStart`. A toolchain on the consumer's machine is heavier
  than the `uv` that ADR 034 asked for. Cython keeps CPython's start-up, so measure what it
  actually saves.
- **The shared code.** [`scripts/adr.py`][] and [`scripts/frontmatter.py`][] are symlinks
  into the skill (ADRs 023 and 035). [`scripts/backlog.py`][] imports `adr`, and
  [`scripts/ci/validate_manifests.py`][] imports the parser. After a port, `scripts/`
  either calls the binary or keeps Python copies beside it, which is the duplication
  ADR 011 removed.
- **Every caller changes.** [`hooks/hooks.json`][], [`.githooks/pre-commit`][], and
  [`.github/workflows/pr.yml`][] run the tool, and `pr.yml` will hold ADR 034's p95 check.
- **The spec already exists.** The skill's `tests/`, including its drift test against
  `SKILL.md` (ADR 017), define the behaviour a port must match. Run them against the port
  rather than rewriting them.
- **What the tool may write** (ADR 023) and how it finds the repository (ADR 024) are
  behaviour, not implementation, and carry over unchanged.

## Acceptance

- An ADR records the runtime and distribution. It restates what it keeps from ADR 034,
  updates ADR 025's citation, and weighs the cache lever as an alternative.
- The port passes the existing suite, or a port of that suite shown to cover the same
  cases.
- The hook's mean cost per turn and p95 per event are measured before and after the port,
  on this repository's corpus and on `todofixthis/cookiecutter-py`'s, and recorded in the
  new ADR.
- `scripts/` either shares one parser with the tool, or the ADR says why it doesn't.
- A consumer needs nothing beyond what the new ADR states. A real session on a machine
  without the build toolchain confirms this.

[ADR 025]: ../adr/025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 034]: ../adr/034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md
[ADR 035]: ../adr/035-run-repo-scripts-under-uv-with-declared-dependencies.md
[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[`.github/workflows/pr.yml`]: ../../.github/workflows/pr.yml
[`hooks/hooks.json`]: ../../hooks/hooks.json
[`scripts/adr.py`]: ../../scripts/adr.py
[`scripts/backlog.py`]: ../../scripts/backlog.py
[`scripts/ci/validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`scripts/frontmatter.py`]: ../../scripts/frontmatter.py
[`skills/writing-adrs/`]: ../../skills/writing-adrs/
