# scripts/frontmatter.py should parse ADR frontmatter with PyYAML, not a hand-rolled scanner

> Recorded 2026-09-05, while implementing
> [ADR 028](../adr/028-adopt-a-uv-workspace-at-the-repository-root.md), which gave
> `scripts/` a dependency path but deliberately left this swap for a separate change.

## What

[`scripts/frontmatter.py`][] (reached from `scripts/` by symlink into
`skills/writing-adrs/`) hand-parses ADR frontmatter line by line, as a grammar this
repository defines. GitHub instead renders that frontmatter through a real YAML parser,
so `yaml_hazard()` in [`adr.py`][] exists purely to predict where the two disagree — a
second site approximating a grammar nobody has written down. Swapping the parser for
[PyYAML][] would remove both `frontmatter.py`'s hand-rolled scanner and `yaml_hazard()`'s
guesswork, parsing and constructing frontmatter the same way GitHub reads it.

`scripts/pyproject.toml` now exists (ADR 028) with `dependencies = []`; adding PyYAML
there is what this item spends.

## Why it is still worth doing

ADR 007's `revisit-when` named this exact condition and ADR 028 answered only the
structural half — that `scripts/` can reach a dependency at all — leaving the parser
itself untouched on purpose, since the swap is a large enough, independently testable
change to review on its own. `yaml_hazard()` is a standing admission that the current
parser is wrong on inputs nobody has tried yet.

## Acceptance

- `scripts/frontmatter.py` parses ADR frontmatter with PyYAML, matching how GitHub
  renders the same block, rather than a hand-written line scanner.
- `yaml_hazard()` in `adr.py` is removed once the parser it exists to guess around no
  longer needs guessing.
- Every existing `scripts/frontmatter.py` and `adr.py` test still passes, plus a
  regression case for whatever the old scanner and GitHub's renderer disagreed on.
- `scripts/pyproject.toml` declares PyYAML, `uv lock` and `uv sync --locked` succeed
  against the shared root lock, and `python3 skills/writing-adrs/adr.py check` still
  passes — following `superpowers:test-driven-development`, per `AGENTS.md`.

[`adr.py`]: ../../skills/writing-adrs/adr.py
[PyYAML]: https://pyyaml.org/
[`scripts/frontmatter.py`]: ../../scripts/frontmatter.py
