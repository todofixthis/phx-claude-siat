---
status: Accepted
date: 2026-10-07
scope: [scripts/]
summary: Keep every import under scripts/ to the standard library, except that scripts.frontmatter loads the PyYAML ADR 034 vendors beside writing-adrs — no other module imports yaml, even where an installed copy would resolve; a further dependency goes in scripts/pyproject.toml under the root workspace, never per-script PEP 723 metadata.
revisit-when: A site under scripts/ hand-parses a grammar this repository does not define, or the substring match validate_manifests.py runs against pr.yml causes a miss in practice.
---

# 035: Keep repo scripts stdlib-only, bar the vendored YAML parser

## Context

[ADR 007][] keeps every import under `scripts/` stdlib-only, so its scripts run unaided in
any clone, CI job and git hook with nothing to install. [ADR 034][] vendors PyYAML beside
the `writing-adrs` skill as the frontmatter parser's authority on values, and
`scripts/frontmatter.py` is a symlink to that parser ([ADR 023][]). Through it, or through
`adr.py` by the same route, `validate_manifests.py`, `backlog.py` and their tests all reach
the vendored package, so the import lands under `scripts/`, which ADR 007 forbids.

This ADR restates ADR 007 with that claim narrowed, and supersedes it.

## Options

### Option 1: Do nothing

Keep ADR 007 as written.

**Pros:** The rule stays absolute, with no exception to explain.
**Cons:** `scripts/` can no longer share the parser, so `validate_manifests.py` needs a copy
of its own — the duplication [ADR 011][] removed — or ADR 034 cannot be implemented as
decided.
**Risks:** The copy keeps hand-parsing skill frontmatter, which is YAML as much as ADR
frontmatter is.

### Option 2: Admit the vendored parser as the one exception (Accepted)

`scripts/` imports only the standard library, plus what `scripts.frontmatter` loads.

**Pros:** The property ADR 007 protected survives: vendored code needs no install step, so
`python3 -m scripts.<area>.<name>` still runs anywhere.
**Cons:** An exception a reader must know about, to the one rule `scripts/` docstrings cite.
**Risks:** A direct `import yaml` passes under `uv run`, where the workspace installs PyYAML
for the drift check, and fails under bare `python3`.

### Option 3: Drop the constraint

Let `scripts/` import whatever `scripts/pyproject.toml` declares under the workspace
[ADR 031][] built.

**Pros:** No exception to explain, and no hand-parsing where a library exists.
**Cons:** Every caller moves from `python3` to `uv run`, and the git hook needs a synced
environment first.
**Risks:** A cold resolve stalls a sub-second hook, the risk ADR 007 named.

## Decision

Option 2. Vendored code keeps what ADR 007 protected, where Option 3 spends it for no
current need and Option 1 rebuilds the duplication ADR 011 removed. The exception is bounded
by what it is: one parser, vendored for a shipped tool's sake and loaded under a private
name, which `scripts/` reaches by the symlink it already used. It is no licence to import
`yaml` elsewhere, nor to vendor further libraries for `scripts/`'s own convenience.

The rest of ADR 007 stands, reasoning included. A further dependency goes in
`scripts/pyproject.toml`, the root project ADR 031 built, never in per-script PEP 723
metadata. The rule constrains neither local feedback — the `pre-commit` framework needs no
import in any script — nor what leaves `scripts/` unlinted. And its standing question
carries over, asked at every change under `scripts/`: is anything there approximating a
grammar — a glob, a semver range, a TOML subset — rather than parsing it? That is the first
half of the trigger above; ADR 007's Revisit watch holds the answers so far.

## Consequences

- The `ADR 007` citations in `scripts/` docstrings and `AGENTS.md`, several reading
  "stdlib-only, like everything under scripts/", and `backlog.py`'s uncited "Standard
  library only", are retargeted to this ADR or corrected in the change that vendors the
  parser, when their wording stops being true.
- [ADR 006][] accepted a substring match against `pr.yml` because the repository had no
  YAML dependency. `scripts.frontmatter` now carries one, so that blindness is a choice
  rather than a constraint — not one this ADR revisits.

[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 031]: 031-adopt-a-uv-workspace-at-the-repository-root.md
[ADR 034]: 034-ship-the-adr-tool-with-a-vendored-pyyaml-parser.md
