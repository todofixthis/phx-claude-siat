---
status: Accepted
date: 2026-09-05
scope: [pyproject.toml, uv.lock, scripts/, skills/creative-commits/, skills/nz-english/, skills/writing-adrs/, .github/workflows/pr.yml]
summary: Restructure the repository as a uv workspace with a root pyproject.toml and one shared uv.lock, so scripts/ gains a dependency path without a project of its own and each of the three tool-shipping skills keeps its own standalone-buildable pyproject.toml.
revisit-when: A workspace member needs a dependency version the shared resolution cannot satisfy for every member at once.
---

# 028: Adopt a uv workspace at the repository root

## Context

Three skills — [`creative-commits`][], [`nz-english`][] and [`writing-adrs`][] — each
carry a complete `pyproject.toml` and their own `uv.lock`, beside a `scripts/` that
[ADR 007][] keeps stdlib-only with no project of its own. Nothing holds the three
skill projects together: their dev-dependency groups already declare identical
version ranges, yet `skills/writing-adrs/uv.lock` resolved five transitive packages
newer than the other two before this change, because each lock is regenerated
independently between the maintenance sweeps [`renovate.json`][] enables. Their
`black`/`ruff` settings had drifted too — `nz-english` and `writing-adrs` agreed on a
96-column line length, `creative-commits` set none, and only `writing-adrs` pinned a
`black` `target-version`.

ADR 007 already names its own largest cost: `scripts/` sits outside the lint, format
and type-check layer [ADR 005][] and [ADR 006][] built, because that layer keys off
what a skill's `pyproject.toml` declares and `scripts/` has none. It also names its
own remedy in advance — "if a trigger below fires, the answer is a root project,
never per-script metadata" — for the day a script needs a dependency stdlib cannot
supply.

That trigger has now fired. `scripts/frontmatter.py`, reached from `scripts/` by
symlink, hand-parses ADR frontmatter as a flat grammar, but GitHub renders that
frontmatter through a real YAML parser; `yaml_hazard()` in [`adr.py`][] exists only to
predict where the two disagree, which is a second site approximating a grammar this
repository does not define — the exact condition ADR 007's `revisit-when` names.
[PyYAML][] would remove both the hand-rolled parser and the guesswork around it, and
ADR 007 forbids that dependency under `scripts/` as it stands. Its 2026-09-03 Revisit
watch entry records the finding and defers the answer to this decision.

Separately, `pr.yml`'s `python` job already runs a matrix over the three skill
directories, and [`validate_manifests.py`][] substring-matches those directories and
their declared tools against the workflow (ADR 006) — whatever shape this decision
takes has to keep both working.

## Options

Every option below keeps each shipped tool's own consumer-facing Python floor
untouched: `scan.py` and `adr.py`/`hook.py` guard 3.10 in code, because a consumer
runs them as `python3 <skilldir>/tool.py` with no `uv` and no install step
([ADR 017][]); `seed.py` guards nothing, because `creative-commits` already runs
through `uv` and is never invoked as bare `python3`. None of that is a Python-project
concern — it is enforced in each tool's own source — so no option touches it. What
every option below does set is the *workspace's* `requires-python`, which governs
only how this repository resolves and tests its own dev tooling: 3.12, the maintainer's
stated floor for todofixthis projects as of 2026-09-03, already the value every
skill's `pyproject.toml` declared before this decision.

### Option 1: Do nothing

Keep three independent skill projects and their three locks; keep `scripts/`
stdlib-only with no path to a dependency.

**Pros:** Nothing to migrate, and no root project to keep working alongside three
skill-level ones.
**Cons:** The drift already measured — five newer transitive packages in one lock,
three different line-length/target-version combinations — is structural, not
incidental, and recurs at every future maintenance sweep. `scripts/frontmatter.py`
keeps hand-parsing a grammar GitHub renders through a real parser, with `yaml_hazard()`
as the only defence.
**Risks:** ADR 007's fired trigger goes unanswered a second time, and the next reader
of its Revisit watch inherits the same open question.

### Option 2: Adopt a uv workspace, each skill keeping its own package (Accepted)

A root `pyproject.toml` declares `[tool.uv.workspace]` with `scripts/` and the three
skill directories as members, resolved against one `uv.lock`. Each skill keeps its own
complete `pyproject.toml` — `[project]`, `[build-system]`, its entry point,
`[tool.autohooks]` — since a uv workspace aggregates dependency *resolution* without
replacing a member's own buildability. `scripts/` gains a minimal `pyproject.toml` with
no `[build-system]`, which uv resolves as a virtual member: never built, never
installed, so `python3 -m scripts.<area>.<name>` ([ADR 011][]) is unchanged. Toolchain
pins and `black`/`ruff` settings move to the root, once.

**Pros:** One lock closes the drift already measured. `scripts/` gains the dependency
path ADR 007 reserved for this trigger, without forcing an install step onto its
existing invocation. Each skill's own `pyproject.toml` stays a complete, standalone
package, so [ADR 022][]'s consumer recipe needs nothing new.
**Cons:** `pr.yml`'s `python` job needs restructuring: a per-leg `uv sync --locked` run
with the leg's directory as `cwd` prunes the shared venv down to that leg's own closure
(verified empirically — a sibling skill's package was uninstalled), so the job syncs the
whole workspace once and scopes each leg's checks with `uv run --directory <skill>`
instead.
**Risks:** `black`/`ruff` config resolution walks up from the invoking directory to the
nearest `pyproject.toml` carrying the section, which for every skill is now the root —
config drift becomes something a change here could invisibly reintroduce. One shared
lock also means one unresolvable dependency now fails every skill's leg, not only the
one that added it, and Renovate's lock-maintenance sweep bundles all three skills'
transitive bumps into a single pull request rather than three independent ones — coarser
review and rollback, in exchange for closing the drift Option 1 leaves open.

#### Sub-question: a workspace scoped to fewer members

A narrower workspace — `scripts/` plus one skill, leaving the others standalone — is
one instance of Option 2's own shape, held in reserve for a skill that a full workspace
could not accommodate. Every empirical check below passed for all three skills
together, with the one config-inheritance gotcha named above fully answered by an
explicit `src` list at the root, and the fix isn't costlier for three skills than for
one, so there was no case a full workspace failed and a narrow one would not have.
Narrower adoption stays the fallback this option would reach for if a fourth skill's
tooling could not resolve alongside the others — not needed here.

### Option 3: Flatten every skill into the root project

Replace the three skills' own `pyproject.toml` files with one root `[project]` table
covering all their code.

**Pros:** One manifest instead of four; no workspace member indirection to explain.
**Cons:** ADR 022's consumer recipe, `uvx --from 'git+…#subdirectory=skills/writing-adrs' phx-adr`,
is a PEP 517 subdirectory install that needs `skills/writing-adrs/pyproject.toml` to
remain a complete, standalone-buildable project on its own — which flattening removes.
Rebuilding that recipe against a single root project would mean publishing the whole
repository as installable, which none of these tools need.
**Risks:** A change to any one skill's dependencies now touches a manifest shared by
all three, reintroducing at the file level the coordination problem workspace members
were meant to solve at the lock level.

### Option 4: PEP 723 inline metadata for `scripts/` alone

Give `scripts/frontmatter.py` a [PEP 723][] header declaring PyYAML and run it as
`uv run scripts/frontmatter.py`, leaving the three skills and the "no root project"
stance untouched.

**Pros:** Smallest possible change — one file, no workspace, no migration for the
three skills.
**Cons:** ADR 007 already rejected this shape for the repository's dependency-bearing
scripts and recorded why: every caller still moves from `python3` to `uv run`, but the
dependency lives in a per-file comment block a developer does not check first, and
Renovate would need its separate `pep723` manager added to `enabledManagers`. This
option re-derives that rejection rather than answering anything ADR 007 left open.
**Risks:** A second script needing the same library pins it independently, the drift
ADR 007's Option 2 already named and rejected once.

## Decision

Adopt Option 2. ADR 007 already committed to a root project as the answer once a
script needed a real dependency, and `scripts/frontmatter.py` is that trigger, fired
and recorded in ADR 007's Revisit watch on 2026-09-03. This decision **discharges**
that trigger's first clause rather than superseding ADR 007: nothing in ADR 007's
Decision — "keep `scripts/` stdlib-only" — is reversed, because no import in
`scripts/` changes here. What was true only as a contingency ("if a trigger fires, the
answer is a root project") is now built, so the condition that would have reopened
ADR 007 is answered rather than renewed. The second clause of ADR 007's `revisit-when`
— the workflow substring-match causing a miss in practice — is untouched by this
decision and stays live.

**PyYAML itself is deferred**, tracked in [a follow-up backlog item][pyyaml-backlog]
rather than implemented here. This decision answers the *structural* question — can
`scripts/` reach a dependency at all — and a root project is what that needed;
swapping `scripts/frontmatter.py`'s parser is a separable, independently testable
change against code this decision does not touch. `scripts/pyproject.toml` therefore
ships with `dependencies = []`: the workspace member exists, and adding to that list is
now unblocked, but nothing has been added yet.

Every empirical claim below was checked against this repository, not assumed:

- `uv lock`, run once at the root after removing the three skills' own `uv.lock` files,
  resolved 44 packages into one lock; `uv lock --check` and `uv sync --locked` both
  succeed from a clean `.venv`.
- Each skill's `ruff check .`, `black --check .` and `pytest` pass unchanged under
  `uv run --directory <skill>`, run from the repository root exactly as the
  restructured `pr.yml` invokes them.
- `python3 -m unittest discover -s scripts -t . -p 'test_*.py'`, `python3 -m
  scripts.ci.validate_manifests` and `python3 skills/writing-adrs/adr.py check` all
  pass unmodified — the workspace changes nothing `validate_manifests.py` reads, since
  it inspects each skill's own `[tool.autohooks]` and `pr.yml`'s text, neither of which
  moved.
- `uvx --from ./skills/writing-adrs phx-adr check` — the exact recipe ADR 022
  documents and `pr.yml`'s `adr` job already runs — builds and runs `writing-adrs` as a
  standalone package from inside the workspace, unaffected by workspace membership.
- `uv run --project skills/creative-commits emoji-seed` — the invocation
  `creative-commits`'s `SKILL.md` documents — runs unchanged.

One gotcha surfaced only empirically: moving `[tool.ruff]` to the root changed where
ruff resolves its `src` root for first-party import detection, from each skill's own
directory to the repository root, which caused two files' local imports (`seed`,
`hook`) to be reclassified as third-party and fail `ruff check .`'s import-sort rule.
Ruff's `src` accepts globs, verified against this repository, so `src = ["scripts",
"skills/*"]` at the root restores the original passing result for both and covers a
future skill directory without a matching edit to this list.

## Consequences

- `uv run` does **not** become the mandated entry for `scripts/`. It stays invoked as
  `python3 -m scripts.<area>.<name>` (ADR 011) with no venv to activate, because no
  dependency has been added yet; the PyYAML follow-up will need to decide how `scripts/`
  reaches an installed dependency without breaking that invocation, which is that
  change's problem to solve, not this one's.
- `pr.yml`'s `python` job syncs the whole workspace once per matrix leg (each leg is
  an independent runner) and scopes its three checks with `uv run --directory <skill>`;
  the `changes` job's path filter for the `python` output gains `pyproject.toml`,
  `uv.lock` and `scripts/pyproject.toml`, since a change to any of them now affects
  what every leg resolves.
- `scripts/` still sits outside a lint/format/type-check gate of its own — ADR 007's
  largest named cost is unclosed by this decision, exactly as ADR 007's Consequences
  already anticipated ("closing it is a change this decision does not stand in the way
  of"). Extending `pr.yml` to lint `scripts/` is possible now that the toolchain lives
  in a workspace it belongs to, but is separate work this decision does not undertake.
- Toolchain pins (`black`, `ruff`, `pytest`, `autohooks*`) and `black`/`ruff` settings
  (`line-length = 96`, `target-version = ["py312"]`) are declared once, at the root;
  each skill's own `pyproject.toml` keeps only what makes it independently
  buildable — `[project]`, `[build-system]`, its entry point and `[tool.autohooks]`.
- `renovate.json`'s `pep621` manager already scans every `pyproject.toml` in the
  repository, root and workspace members alike, so no Renovate configuration changes.
- `README.md` and `AGENTS.md`'s Python sections are updated to describe the workspace
  and the `uv run --directory <skill>` invocation, in the same change.

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
[pyyaml-backlog]: ../backlog/scripts-frontmatter-parser-should-use-pyyaml.md
[PyYAML]: https://pyyaml.org/
[`renovate.json`]: ../../renovate.json
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
