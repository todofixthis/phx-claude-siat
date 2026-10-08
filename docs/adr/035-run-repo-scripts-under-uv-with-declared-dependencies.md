---
status: Accepted
date: 2026-10-08
scope: [.agents/skills/releasing/, .githooks/pre-commit, .github/workflows/pr.yml, .github/workflows/release.yml, AGENTS.md, scripts/]
summary: Let scripts/ import what scripts/pyproject.toml declares under the root uv workspace, and run every script as `uv run python -m scripts.<area>.<name>` from the repo root — never per-script PEP 723 metadata, never bare python3, and never an import the declaration lacks.
revisit-when: A site under scripts/ hand-parses a grammar a declarable library parses, or the substring match validate_manifests.py runs against pr.yml causes a miss in practice.
---

# 035: Run repo scripts under uv with declared dependencies

## Context

[ADR 007][] keeps every import under `scripts/` stdlib-only, so its scripts run unaided in
any clone, CI job and git hook with nothing to install. [ADR 011][] made `scripts/` a
package run as `python3 -m scripts.<area>.<name>`, so one frontmatter parser serves every
caller. [ADR 031][] then made `scripts/` a uv workspace member with no dependencies.

[ADR 034][] has that parser import PyYAML, and `scripts/frontmatter.py` is a symlink to it
([ADR 023][]). Through it, or through `adr.py` by the same route, `validate_manifests.py`,
`backlog.py` and their tests import PyYAML, which ADR 007 forbids and which bare `python3`
cannot resolve.

This ADR restates ADR 007 and ADR 011 with those claims replaced, and supersedes both.

## Options

### Option 1: Do nothing

Keep ADR 007 and ADR 011 as written.

**Pros:** Scripts keep running under bare `python3` from any clone.
**Cons:** `scripts/` can no longer share the parser, so `validate_manifests.py` needs a copy
of its own — the duplication ADR 011 removed — or ADR 034 cannot be implemented as decided.
**Risks:** The copy keeps hand-parsing skill frontmatter, which is YAML as much as ADR
frontmatter is.

### Option 2: Declare dependencies, run every script under `uv run` (Accepted)

`scripts/pyproject.toml` declares PyYAML, and every caller — `pr.yml`, `release.yml`, the
pre-commit hook, the `releasing` skill — runs `uv run python -m scripts.<area>.<name>`.

**Pros:** One invocation for every script, and imports resolve the same way in CI, the hook
and a shell.
**Cons:** Every caller changes, and the pre-commit hook needs `uv`, syncing the workspace
on its first run in a clone.
**Risks:** A cold resolve on a slow or absent network stalls a commit, the risk ADR 007
named.

### Option 3: Run under `uv` only the scripts that import the parser

`validate_manifests.py`, `backlog.py` and their tests move to `uv run`; the rest stay on
bare `python3`.

**Pros:** Scripts that need no dependency keep running unaided.
**Cons:** Two invocations, chosen by an import chain a caller cannot see.
**Risks:** A script gaining an import through `scripts.frontmatter` fails under `python3`
wherever its callers were not updated.

## Decision

Option 2. ADR 034 makes `uv` a requirement wherever the tool runs, and the scripts that
import the parser are the ones CI and the hook run most, so the unaided-`python3` property
ADR 007 protected is already gone where it mattered. Option 3 keeps it for the remainder at
the cost of a second invocation chosen by an invisible import chain. Option 1 rebuilds the
duplication ADR 011 removed.

The rest of ADR 007 and ADR 011 stands, reasoning included. A dependency goes in
`scripts/pyproject.toml`, the root project ADR 031 built, never in per-script PEP 723
metadata, and a script imports nothing that file does not declare: an import resolving only
because another workspace member installed it passes under `uv run` and breaks the day that
member drops it. Scripts run as modules from the repository root, as ADR 011 decided, and
the suite as `uv run python -m unittest discover -s scripts -t . -p 'test_*.py'`; shared
code lives in the narrowest package containing every importer. ADR 007's standing question
carries over too, as the first half of the trigger above, asked at every change under
`scripts/`: is anything there approximating a grammar — a glob, a semver range, a TOML
subset — rather than parsing it? Now that a dependency is a declaration away, a hand-written
grammar is a choice to justify rather than a constraint to accept. The answers so far:

- 2026-08-10 (ADR 007): `scope` matching compares string prefixes and recognises glob
  characters only to reject them. Not parsing.
- 2026-09-03 (ADR 007): `scripts/frontmatter.py` approximated YAML. Answered by ADR 034.

## Consequences

- `pr.yml`, `release.yml`, `.githooks/pre-commit`, the `releasing` skill, `AGENTS.md`, the
  README and the module docstrings that give the invocation or cite ADR 007's stdlib-only
  rule are corrected in the change implementing ADR 034. `release.yml` sets up no `uv`
  today, so it gains that step before its `scripts/` call, or the release fails on `main`.
- [ADR 006][] accepted a substring match against `pr.yml` because the repository had no
  YAML dependency. It now has one, so that blindness is a choice rather than a constraint —
  not one this ADR revisits.

[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 031]: 031-adopt-a-uv-workspace-at-the-repository-root.md
[ADR 034]: 034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md
