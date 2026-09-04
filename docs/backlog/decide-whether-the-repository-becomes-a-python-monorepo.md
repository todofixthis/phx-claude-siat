# Three skills carry three Python projects; decide whether one root project replaces them

> Recorded 2026-09-03, from the maintainer's review of the writing-adrs system branch
> (pull request #53). Never filed as a GitHub issue. The analysis is the deliverable, not
> the conversion: nothing here is decided.

## What

Analyse, then decide by ADR, whether the repository becomes one Python project — a root
`pyproject.toml` whose workspace members are the skills that ship tooling — in place of
`skills/creative-commits/pyproject.toml`, `skills/nz-english/pyproject.toml` and
`skills/writing-adrs/pyproject.toml`, each with its own `uv.lock`, beside a stdlib-only
`scripts/`.

## Why it is still worth doing

**Three projects drift, and nothing holds them together.** Live today: the three dev
dependency groups declare identical ranges, yet the three locks resolve independently, so
a lock regenerated between the maintenance sweeps `renovate.json` enables sits ahead of
the others until the next sweep — `skills/writing-adrs/uv.lock`, written on this branch,
currently resolves five transitive packages newer than the other two. Two projects set a
96-column line length and `creative-commits` sets none; `writing-adrs` alone pins a
`black` target version. Of the four shipped tools, three guard a 3.10 floor under two names —
`PYTHON_FLOOR` in `skills/writing-adrs/adr.py` and `skills/writing-adrs/hook.py`,
`MINIMUM_PYTHON` in `skills/nz-english/scan.py` — and `skills/creative-commits/seed.py`
guards nothing; every `pyproject.toml` says `>=3.12` and CI runs 3.12 alone, so the 3.10
floor is asserted and never exercised. `.github/workflows/pr.yml` runs one `python` job
with a matrix leg per skill directory, and `scripts/ci/validate_manifests.py`
substring-matches those directories against the workflow, so the shape is load-bearing in
CI as well.

**[ADR 007][] names its own cost, and a root project is what closes it.** `scripts/` sits
outside the lint, format and type-check layer that [ADR 005][] and [ADR 006][] built —
CI runs it, nothing checks it, and it is the code enforcing everything else. 007 calls that
its largest cost and says the answer, should a trigger fire, is a root project, never
per-script metadata. A monorepo is that root project, so adopting one supersedes 007
rather than sitting beside it.

**007's trigger has fired once, and the answer is deferred to this item.**
`skills/writing-adrs/frontmatter.py`, reached from `scripts/` by symlink, is a hand-rolled
line parser for frontmatter GitHub renders through a real YAML parser. `yaml_hazard()` in
`skills/writing-adrs/adr.py` exists only to predict where the two disagree — a second
site approximating a grammar this repository does not define, which 007's `## Revisit
watch` records. PyYAML for parsing and construction would remove both; 007 forbids the
dependency under `scripts/`.

**The Python floor is a policy exception with a possible way out.** The maintainer's
policy for todofixthis projects, as stated in the review comment this item records, is
the three latest Python versions — 3.12 the floor on 2026-09-03. Three of the four shipped
tools run on whatever `python3` a consumer's operating system installed, with a 3.10
floor, and the consumer's repository need not be a Python project at all; that is why the
policy is relaxed here. A root project governs how this repository invokes its own
scripts; consumers are reached through [ADR 022][]'s `uvx` recipe and the `uv run` entry
`creative-commits` already ships, and because `uv` provisions the interpreter, a
uv-mediated entry can promise a supported Python whatever the consumer's `python3` is —
at the cost of the install step [ADR 017][] refuses. Whether that trade is worth making is
for the analysis.

## Complications

- [ADR 017][]'s no-install clause assumes nothing is installed: a shipped tool runs as
  `python3 <skilldir>/tool.py`. A workspace threatens it only where the tooling grows a
  dependency — which `skills/creative-commits/seed.py` already has, importing `emoji` and
  `regex` and running under `uv`, so one of the four tools sits outside the clause today.
- [ADR 022][]'s consumer recipe,
  `uvx --from 'git+…#subdirectory=skills/writing-adrs' phx-adr`, assumes the skill is
  installable on its own; a workspace changes what `--from` names.
- ADR 005 and 006 mirror each skill's tooling as a pull-request check and validate the
  declaration by substring; a root project changes what there is to mirror.
- ADR 007 notes that a root manifest is where Renovate already reads, and that the
  `pre-commit` framework is blocked by `core.hooksPath`, not by the stdlib rule.

## Acceptance

- A written analysis weighing the status quo against a root project with workspace
  members, naming any third shape it rejected and why.
- The analysis weighs the unchecked `scripts/` layer.
- The analysis weighs toolchain drift across the skill projects.
- The analysis weighs PyYAML for frontmatter parsing and construction.
- The analysis weighs the Python floor the shipped tools promise.
- The analysis weighs whether `uv run` becomes the mandated entry for every script call.
- The analysis weighs the consumer recipe and the CI mirror.
- The decision recorded as an ADR: superseding ADR 007 if a root project is adopted, or
  leaving 007 in force with the reading added to its `## Revisit watch` if not.
- The Python floor answered in that ADR or one depending on it: what the shipped tools
  promise, and whether it can be a todofixthis-supported version.
- If adopted: one lockfile.
- If adopted: one set of toolchain pins and formatter settings.
- If adopted: every skill's tests still run in CI.
- If adopted: the consumer recipe still works.

[ADR 005]: ../adr/005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: ../adr/006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 007]: ../adr/007-keep-repo-scripts-stdlib-only.md
[ADR 017]: ../adr/017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: ../adr/022-ship-the-adr-tooling-and-hooks-with-the-skill.md
