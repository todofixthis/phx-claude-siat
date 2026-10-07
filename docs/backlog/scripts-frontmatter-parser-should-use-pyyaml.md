# Parse ADR and skill frontmatter with the PyYAML ADR 034 vendors

> Recorded 2026-09-05, while implementing
> [ADR 031](../adr/031-adopt-a-uv-workspace-at-the-repository-root.md). Re-scoped
> 2026-10-07 by [ADR 034][], which decided the route: vendored, not declared.

## What

Implement [ADR 034][] and [ADR 035][]: vendor PyYAML's pure-Python package into
`skills/writing-adrs/`, have [`frontmatter.py`][] defer every value it cannot prove plain
to PyYAML's `BaseLoader`, loaded lazily under a private name, and drop the character-class
guesswork in `yaml_hazard()` in [`adr.py`][]. ADR 034's Consequences list the rest — the
wheel's `only-include`, the version pin and its `pr.yml` check, and the docs and citations
to correct.

## Why it is still worth doing

The hand-written parser refuses valid frontmatter: a `scope` entry quoted because its path
opens with `{`, as every path under a cookiecutter template's
`{{ cookiecutter.github_project_name }}/` does. Both todofixthis cookiecutter repositories
are blocked from `check` and `index` until this lands and is released.

## Acceptance

- `frontmatter.py` defers non-plain values to the vendored PyYAML, and
  `scripts/frontmatter.py` reaches it through the symlink under bare `python3`, with
  nothing installed — and with an installed PyYAML present, still the vendored copy.
- A test checks that every value the allowlist accepts loads to the same string under the
  vendored `BaseLoader`, over generated cases reaching every edge ADR 034's Decision names,
  with a fixture value the allowlist must defer.
- A regression test parses a quoted `scope` entry naming a templated path, and `for` matches
  that path.
- `pr.yml` fails when the vendored tree differs from the pinned release.
- A hook event's median cost is measured within 100 ms on this repository's corpus and on
  a cookiecutter corpus, whose quoted paths load PyYAML.
- Every existing `frontmatter.py`, `adr.py` and `scripts/` test passes, and
  `python3 skills/writing-adrs/adr.py check` passes.

[ADR 034]: ../adr/034-ship-the-adr-tool-with-a-vendored-pyyaml-parser.md
[ADR 035]: ../adr/035-keep-repo-scripts-stdlib-only-bar-the-vendored-yaml-parser.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
