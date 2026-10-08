# Parse ADR and skill frontmatter with PyYAML, run from a uv-synced environment

> Recorded 2026-09-05, while implementing
> [ADR 031](../adr/031-adopt-a-uv-workspace-at-the-repository-root.md). Re-scoped
> 2026-10-08 by [ADR 034][] and [ADR 035][], which decided the route.

## What

Implement [ADR 034][] and [ADR 035][]: declare PyYAML for the `writing-adrs` skill and for
`scripts/`, have [`frontmatter.py`][] parse every block with `CBaseLoader`, drop the
character-class guesswork in `yaml_hazard()` in [`adr.py`][], sync the skill's venv into
`${CLAUDE_PLUGIN_DATA}` from the `SessionStart` hook in [`hooks.json`][] and run every other
hook on that venv's `python`, and move every `scripts/` caller to
`uv run python -m scripts.<area>.<name>`. The two ADRs' Consequences list the docs and
citations to correct.

## Why it is still worth doing

The hand-written parser refuses valid frontmatter: a `scope` entry quoted because its path
opens with `{`, as every path under a cookiecutter template's
`{{ cookiecutter.github_project_name }}/` does. Both todofixthis cookiecutter repositories
are blocked from `check` and `index` until this lands and is released.

## Acceptance

- A regression test parses a quoted `scope` entry naming a templated path, and `for` matches
  that path.
- In a fresh session with an empty `${CLAUDE_PLUGIN_DATA}`, `SessionStart` builds the
  version's venv and the hooks inject as before. With `uv` absent, or offline on a first
  session, `SessionStart` says so and every other hook exits silently — including after a
  sync interrupted once `python` exists.
- Sessions on two plugin versions each keep their own venv, and nothing creates an
  environment in the plugin cache. A plugin loaded from a checkout uses that checkout's own
  venv, created if absent, with the dev group and other workspace members left installed.
  A developer's own bare `uv sync` at the root then keeps PyYAML, since it installs
  `writing-adrs`, which declares it.
- From a real session in a repository with no `docs/adr/`, the skill's `adr.py new`
  bootstraps the venv through its launcher and succeeds.
- A `pr.yml` check times at least 20 hook events on this repository's corpus and fails
  above a 1 s p95, `SessionStart` with its no-op sync included, and a fixture slowing the
  hook makes it fail. The mean hook cost per turn — events a turn from main and subagent
  transcripts, times mean cost an event — is recorded against ADR 034's session budget in
  a `## Revisit watch` section of ADR 034, beside a fresh measurement of the median turn.
- `pr.yml`, `release.yml`, the pre-commit hook and the `releasing` skill run `scripts/` and
  `adr.py` under `uv run`, and every existing `frontmatter.py`, `adr.py` and `scripts/`
  test passes.

[ADR 034]: ../adr/034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md
[ADR 035]: ../adr/035-run-repo-scripts-under-uv-with-declared-dependencies.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[`hooks.json`]: ../../hooks/hooks.json
