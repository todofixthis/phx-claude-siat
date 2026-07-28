---
status: Accepted
date: 2026-07-28
tags: [adr, ci, dependencies, duplication, frontmatter, git-hooks, python, scripts, stdlib, tooling, uv]
summary: Keep everything under scripts/ stdlib-only with no Python project at the repo root, reaching for PEP 723 inline metadata rather than a root project if that changes; revisit on a second compromise over a grammar this repo does not define, or when the adapted frontmatter parser gains a third copy or its copies drift on shared input.
---

# 007: Keep repo scripts stdlib-only

## Context

`scripts/` has grown to five files — ADR index generation, manifest validation, release
notes, a shared version pattern, and one test module — run by CI, the pre-commit hook,
and the [`releasing`][] skill, each as `python3 scripts/<area>/<name>.py` from the repo
root. None declares a dependency, and the repo root carries no `pyproject.toml`.

[ADR 006][] already reasons from that constraint (choosing `tomllib` because it is
standard library, and rejecting alternatives needing "a dependency the repo lacks"), and
[ADR 005][] already accepts one of its costs: the flat-frontmatter parser adapted between
[`generate_index.py`][] and [`validate_manifests.py`][]. Neither states the constraint
itself, so each new script re-decides it, and the first to answer "add a dependency"
answers for everyone.

The cost is real and growing. [`semver`][] would replace hand-written version regexes;
[`PyYAML`][] would replace that adapted parser — the two copies are not identical, since
the ADR-side one parses inline lists and the manifest-side one handles scalars only.

Packaged skills are a different case: `skills/<name>/` units ship to users with their own
lifecycle, and [`creative-commits`][] already declares dependencies and runs under `uv`.

## Options

### Option 1: Do nothing

Leave the constraint an unstated habit.

**Pros:** No document to maintain; each script author judges its own case.
**Cons:** The habit is invisible, so it is followed by accident and abandoned by accident.
**Risks:** A dependency arrives for one convenient import, and whichever mechanism that
first author happens to pick — most likely the heaviest — becomes the precedent, without
anyone weighing it.

### Option 2: Declare `scripts/` stdlib-only, with a revisit trigger (Accepted)

Record the constraint, and the conditions that reopen it.

**Pros:** A new script inherits the answer; adding a dependency becomes a decision with a
written bar to clear.
**Cons:** Hand-written parsing continues, as does the duplication between `scripts/adr`
and `scripts/ci`, which no dependency was needed to fix in the first place.
**Risks:** The trigger is written too loosely to fire, and the constraint outlives its
justification.

### Option 3: Declare dependencies per script with PEP 723 inline metadata

Give each script a [PEP 723][] header and run it as `uv run scripts/ci/foo.py`. No root
project, no shared lockfile, dependencies isolated per script.

**Pros:** Real libraries, per script and without a shared lockfile; `uv` is already a
dependency of this repo through `creative-commits`.
**Cons:** Every caller's invocation changes from `python3` to `uv run`, including the
[pre-commit hook][], which then resolves an environment before it can do anything.
**Risks:** The hook stops being instant and offline — the two properties that make it
worth running at all — and a first-run resolve on a slow or absent network turns a
sub-second check into a stall or a failure.

### Option 4: Add a Python project at the repo root

Give the root a `pyproject.toml` and lockfile.

**Pros:** Scripts get libraries, and shared code lives in one importable module.
**Cons:** Everything in Option 3, plus a root venv sitting alongside the skill packages'
own, and a lockfile coupling unrelated scripts to a single resolution.
**Risks:** `python3 scripts/...` — which works in any clone with no setup — stops being
how these run, so an environment they previously ran in unaided now needs preparing
first.

## Decision

Keep `scripts/` stdlib-only. What these scripts parse is almost entirely grammar this
repo defines and constrains — flat skill frontmatter, `X.Y.Z` versions, fixed changelog
headings — where a regex over a known shape is the whole job rather than an
approximation of one. The two exceptions are held at arm's length: skill TOML is read
through stdlib `tomllib`, and `pr.yml` is substring-matched rather than parsed, which
ADR 006 recorded as a deliberate loss of precision. Options 3 and 4 buy libraries for
parsing that is not yet hard.

Between those two, PEP 723 is the better escape hatch and a root project is not worth its
price at any point this repo is likely to reach. **When a trigger below fires, the answer
is PEP 723 on the affected script** — and the pre-commit hook's script is the one to keep
stdlib-only longest, since its value is being instant and offline.

Duplication is a separate question from dependencies. Within a directory, sharing is
unremarkable: [`versions.py`][] holds the version shape that [`release_notes.py`][] and
`validate_manifests.py` both assert, precisely so the two cannot drift. The frontmatter
parsers stay apart only because `scripts/adr` and `scripts/ci` are siblings with no
package between them, and restructuring `scripts/` around one 8-line function is not yet
worth it.

**Revisit when either holds:**

- A script must parse a grammar this repo does not define — real YAML, TOML beyond flat
  lookups, semver *ordering* rather than shape. Hand-writing then approximates someone
  else's specification, and the failure mode changes from "obviously wrong" to "wrong on
  inputs nobody tried". One case already sits under the constraint: `validate_manifests.py`
  substring-matches `.github/workflows/pr.yml` rather than parsing it, a blindness ADR 006
  recorded knowingly. A second such compromise, or that one causing a miss in practice, is
  the trigger.
- The frontmatter parser gains a third copy, or the two copies disagree on input both must
  handle. Their current difference is one parsing a superset of the other, which is
  tolerable; drift on shared input is not, and neither is a third site to keep in step.

## Consequences

`scripts/` sits outside the enforcement regime ADRs 005 and 006 built. That regime keys
off what a skill *declares*, and these scripts declare nothing — so no formatter, linter,
or type check runs over the code that enforces everything else, and its tests use
`unittest` (with a `discover -s scripts/ci -t scripts/ci` invocation that exists only
because there is no package) where the rest of the repo uses `pytest`. That is the largest
cost here, larger than any duplicated parser, and it is the price of the scripts needing
no setup to run.

Each script's docstring names the constraint and cites this ADR, so it is visible at the
point of temptation rather than only here.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[PEP 723]: https://peps.python.org/pep-0723/
[pre-commit hook]: ../../.githooks/pre-commit
[`PyYAML`]: https://pyyaml.org/
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`semver`]: https://python-semver.readthedocs.io/
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`versions.py`]: ../../scripts/ci/versions.py
