---
status: Accepted
date: 2026-09-05
scope: [pyproject.toml, uv.lock, scripts/, skills/creative-commits/, skills/nz-english/, skills/writing-adrs/, .github/workflows/pr.yml]
summary: Restructure the repository as a uv workspace with a root pyproject.toml and one shared uv.lock, so scripts/ gains a dependency path without a project of its own and each of the three tool-shipping skills keeps its own standalone-buildable pyproject.toml.
revisit-when: A workspace member needs a dependency version the shared resolution cannot satisfy for every member at once.
---

# 031: Adopt a uv workspace at the repository root

## Context

Three skills, [`creative-commits`][], [`nz-english`][], and [`writing-adrs`][], each have a
complete `pyproject.toml` and their own `uv.lock`. Beside them sits `scripts/`, which
[ADR 007][] keeps stdlib-only with no project of its own. Nothing ties the three skill
projects together. Their dev-dependency groups declare identical version ranges, yet
before this change `skills/writing-adrs/uv.lock` had resolved five transitive packages
newer than the other two locks, because each lock is regenerated on its own during the
maintenance sweeps that [`renovate.json`][] enables. Their `black` and `ruff` settings had
drifted too. `nz-english` and `writing-adrs` agreed on a 96-column line length,
`creative-commits` set none, and only `writing-adrs` pinned a `black` `target-version`.

ADR 007 names its own largest cost. `scripts/` sits outside the lint, format, and
type-check layer that [ADR 005][] and [ADR 006][] built, because that layer reads what a
skill's `pyproject.toml` declares, and `scripts/` has none. ADR 007 also names its remedy
in advance, for the day a script needs a dependency the stdlib cannot supply: "if a
trigger below fires, the answer is a root project, never per-script metadata".

That trigger has now fired. `scripts/frontmatter.py`, reached from `scripts/` by symlink,
parses ADR frontmatter by hand as a flat grammar. GitHub renders the same frontmatter
through a real YAML parser. `yaml_hazard()` in [`adr.py`][] exists only to predict where
the two disagree. That makes it a second site approximating a grammar this repository
does not define, which is the exact condition ADR 007's `revisit-when` names. [PyYAML][]
would remove both the hand-written parser and `yaml_hazard()`, and ADR 007 forbids that
dependency under `scripts/` as it stands. ADR 007's Revisit watch entry of 2026-09-03
records the finding and leaves the answer to this decision.

Separately, the `python` job in `pr.yml` already runs a matrix over the three skill
directories. [`validate_manifests.py`][] matches those directories and their declared
tools against the workflow text by substring (ADR 006). Whatever shape this decision
takes must keep both working.

## Options

No option below changes the Python floor that each shipped tool sets for its consumers.
`scan.py`, `adr.py`, and `hook.py` guard 3.10 in code, because a consumer runs them as
`python3 <skilldir>/tool.py` with no `uv` and no install step ([ADR 017][]). `seed.py`
guards nothing, because `creative-commits` already runs through `uv` and nobody runs it
as bare `python3`. Each tool enforces its floor in its own source, not in Python project
metadata, so no option touches it. Every option does set the workspace's
`requires-python`. That value governs only how this repository resolves and tests its own
dev tooling. It is 3.12, the maintainer's stated floor for todofixthis projects as of
2026-09-03, and already the value every skill's `pyproject.toml` declared before this
decision.

### Option 1: Do nothing

Keep three independent skill projects and their three locks. Keep `scripts/` stdlib-only,
with no way to take a dependency.

**Pros:** Nothing to migrate, and no root project to keep working beside three
skill-level ones.
**Cons:** The measured drift is structural, not incidental: five newer transitive
packages in one lock, and three different combinations of line length and target
version. It comes back at every maintenance sweep. `scripts/frontmatter.py` keeps
parsing by hand a grammar that GitHub renders through a real parser, with `yaml_hazard()`
as the only defence.
**Risks:** ADR 007's fired trigger goes unanswered a second time, and the next reader of
its Revisit watch inherits the same open question.

### Option 2: Adopt a uv workspace, each skill keeping its own package (Accepted)

A root `pyproject.toml` declares `[tool.uv.workspace]`, with `scripts/` and the three
skill directories as members, resolved into one `uv.lock`. Each skill keeps its complete
`pyproject.toml`: `[project]`, `[build-system]`, its entry point, and `[tool.autohooks]`.
A uv workspace shares dependency *resolution* across members but leaves each member
buildable on its own. `scripts/` gains a minimal `pyproject.toml` with no
`[build-system]`. uv treats it as a virtual member that it never builds or installs, so
`python3 -m scripts.<area>.<name>` ([ADR 011][]) still works unchanged. Toolchain pins and
`black` and `ruff` settings move to the root, declared once.

**Pros:** One lock ends the measured drift. `scripts/` gains the dependency path ADR 007
reserved for this trigger, without adding an install step to the way it is run today.
Each skill's `pyproject.toml` stays a complete standalone package, so the consumer
recipe in [ADR 022][] needs nothing new.
**Cons:** The `python` job in `pr.yml` needs restructuring. Running `uv sync --locked` per
leg, with the leg's directory as `cwd`, prunes the shared venv down to that leg's own
dependencies. A test run confirmed this: it uninstalled a sibling skill's package. So the
job syncs the whole workspace once and scopes each leg's checks with
`uv run --directory <skill>` instead.
**Risks:** `black` and `ruff` look for config by walking up from the invoking directory to
the nearest `pyproject.toml` that has their section. For every skill, that is now the
root, so a change at the root could bring back config drift without anyone noticing. One
shared lock also means one unresolvable dependency fails every skill's leg, not only the
leg of the skill that added it. Renovate's lock-maintenance sweep also bundles the
transitive bumps for all three skills into one pull request instead of three. Review and
rollback get coarser, in exchange for closing the drift that Option 1 leaves open.

#### Sub-question: a workspace scoped to fewer members

A narrower workspace, `scripts/` plus one skill with the others left standalone, is a
smaller instance of Option 2. It stays in reserve for a skill that a full workspace
cannot hold. Every check below passed for all three skills together. The one
config-inheritance problem named above is fully fixed by an explicit `src` list at the
root, and that fix costs no more for three skills than for one. No case failed in a full
workspace that a narrow one would have passed. A narrower workspace remains the fallback
if a fourth skill's tooling cannot resolve alongside the others. It is not needed here.

### Option 3: Flatten every skill into the root project

Replace the three skills' `pyproject.toml` files with one root `[project]` table that
covers all their code.

**Pros:** One manifest instead of four, and no workspace members to explain.
**Cons:** The consumer recipe in ADR 022,
`uvx --from 'git+…#subdirectory=skills/writing-adrs' phx-adr`, is a PEP 517 subdirectory
install. It needs `skills/writing-adrs/pyproject.toml` to stay a complete project that
builds on its own, and flattening removes that. Rebuilding the recipe against a single
root project would mean making the whole repository installable, which none of these
tools need.
**Risks:** A change to one skill's dependencies would touch a manifest shared by all
three. That brings back, at the file level, the coordination problem that workspace
members were meant to solve at the lock level.

### Option 4: PEP 723 inline metadata for `scripts/` alone

Give `scripts/frontmatter.py` a [PEP 723][] header that declares PyYAML, and run it as
`uv run scripts/frontmatter.py`. The three skills and the "no root project" stance stay
as they are.

**Pros:** The smallest change: one file, no workspace, and no migration for the three
skills.
**Cons:** ADR 007 already rejected this shape for scripts that need dependencies, and
recorded why. Every caller still moves from `python3` to `uv run`. The dependency lives
in a per-file comment block that a developer does not look at first. And Renovate would
need its separate `pep723` manager added to `enabledManagers`. This option repeats that
rejection without answering anything ADR 007 left open.
**Risks:** A second script that needs the same library pins it separately. ADR 007's
Option 2 already named that drift and rejected it once.

## Decision

Adopt Option 2. ADR 007 already committed to a root project as the answer once a script
needed a real dependency. `scripts/frontmatter.py` is that trigger, and ADR 007's Revisit
watch recorded it firing on 2026-09-03. This decision **discharges** the trigger's first
clause. It does not supersede ADR 007, because it reverses nothing in ADR 007's Decision,
"keep `scripts/` stdlib-only": no import in `scripts/` changes here. ADR 007 held the root
project only as a contingency ("if a trigger fires, the answer is a root project"). That
root project now exists, so the condition that would have reopened ADR 007 is answered
rather than renewed. The second clause of ADR 007's `revisit-when`, the workflow
substring match causing a miss in practice, is outside this decision and stays live.

**PyYAML itself is deferred.** [A follow-up backlog item][pyyaml-backlog] tracks it. This
decision answers the *structural* question of whether `scripts/` can reach a dependency
at all, and that needed a root project. Swapping the parser in `scripts/frontmatter.py`
is a separate change that can be tested on its own, against code this decision does not
touch. So `scripts/pyproject.toml` ships with `dependencies = []`. The workspace member
exists and nothing now blocks adding to that list, but nothing is in it yet.

Each claim below was checked against this repository:

- `uv lock`, run once at the root after removing the three skills' own `uv.lock` files,
  resolved 44 packages into one lock. `uv lock --check` and `uv sync --locked` both
  succeed from a clean `.venv`.
- Each skill's `ruff check .`, `black --check .`, and `pytest` pass unchanged under
  `uv run --directory <skill>`, run from the repository root exactly as the restructured
  `pr.yml` runs them.
- `python3 -m unittest discover -s scripts -t . -p 'test_*.py'`, `python3 -m
  scripts.ci.validate_manifests`, and `python3 skills/writing-adrs/adr.py check` all pass
  without changes. The workspace changes nothing that `validate_manifests.py` reads. It
  inspects each skill's own `[tool.autohooks]` and the text of `pr.yml`, and neither
  moved.
- `uvx --from ./skills/writing-adrs phx-adr check` builds and runs `writing-adrs` as a
  standalone package from inside the workspace. Workspace membership does not affect it.
  This is the exact recipe ADR 022 documents and the `adr` job in `pr.yml` already runs.
- `uv run --project skills/creative-commits emoji-seed`, the invocation that the
  `SKILL.md` of `creative-commits` documents, runs unchanged.

One problem showed up only when tested. Moving `[tool.ruff]` to the root changed where
ruff resolves its `src` root for first-party import detection, from each skill's own
directory to the repository root. Ruff then reclassified the local imports of two files
(`seed`, `hook`) as third-party, and both failed the import-sort rule in `ruff check .`.
Ruff's `src` accepts globs, which a test against this repository confirmed. So
`src = ["scripts", "skills/*"]` at the root restores the passing result for both files,
and it covers a future skill directory without an edit to this list.

## Consequences

- `uv run` does **not** become the required entry point for `scripts/`. Scripts still run
  as `python3 -m scripts.<area>.<name>` (ADR 011) with no venv to activate, because no
  dependency has been added yet. The PyYAML follow-up must decide how `scripts/` reaches
  an installed dependency without breaking that invocation. That problem belongs to that
  change, not this one.
- The `python` job in `pr.yml` syncs the whole workspace once per matrix leg, since each
  leg is a separate runner, and scopes its three checks with
  `uv run --directory <skill>`. The path filter for the `python` output of the `changes`
  job gains `pyproject.toml`, `uv.lock`, and `scripts/pyproject.toml`, because a change to
  any of them now affects what every leg resolves.
- `scripts/` still has no lint, format, or type-check gate of its own. This decision
  leaves ADR 007's largest named cost open, as ADR 007's Consequences expected ("closing
  it is a change this decision does not stand in the way of"). Now that the toolchain
  lives in a workspace that includes `scripts/`, `pr.yml` could lint it, but that is
  separate work this decision does not take on.
- Toolchain pins (`black`, `ruff`, `pytest`, `autohooks*`) and `black` and `ruff` settings
  (`line-length = 96`, `target-version = ["py312"]`) are declared once, at the root. Each
  skill's `pyproject.toml` keeps only what makes it buildable on its own: `[project]`,
  `[build-system]`, its entry point, and `[tool.autohooks]`.
- The `pep621` manager in `renovate.json` already scans every `pyproject.toml` in the
  repository, both the root and the workspace members, so no Renovate configuration
  changes.
- The same change updates the Python sections of `README.md` and `AGENTS.md` to describe
  the workspace and the `uv run --directory <skill>` invocation.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[`nz-english`]: ../../skills/nz-english/SKILL.md
[PEP 723]: https://peps.python.org/pep-0723/
[pyyaml-backlog]: https://github.com/todofixthis/phx-claude-siat/blob/b314689/docs/backlog/scripts-frontmatter-parser-should-use-pyyaml.md
[PyYAML]: https://pyyaml.org/
[`renovate.json`]: ../../renovate.json
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
