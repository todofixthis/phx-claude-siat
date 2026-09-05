---
status: Accepted
date: 2026-07-28
scope: [scripts/]
summary: Keep every import under scripts/ stdlib-only, reaching for a root project rather than per-script PEP 723 metadata once a real dependency is needed — the root project ADR 028 later built, without scripts/ importing anything new.
revisit-when: The workflow substring-match already under the constraint causes a miss in practice.
revisit-discharged-by: [28]
---

# 007: Keep repo scripts stdlib-only

## Context

> **Amended by [ADR 011][].** The stdlib-only decision below stands unchanged. What no longer
> holds: scripts run as `python3 -m scripts.<area>.<name>`, `scripts/` is a package, the
> frontmatter parser is shared rather than adapted per directory, and `scripts/adr` now has
> tests. Statements below describing any of those as they were are history, not guidance.
>
> **Discharged in part by [ADR 028][].** The repository root now carries a Python
> project — a uv workspace `scripts/` is a member of — which is the contingency this
> decision's Decision section reserved for the day a script needed a real dependency.
> No import in `scripts/` changed: PyYAML is deferred to a follow-up, tracked in
> `docs/backlog/`. Read "no Python project at the repo root" below as history, not as a
> constraint still standing.

`scripts/` has grown to five files — ADR index generation, manifest validation, release
notes, a shared version pattern, and one test module — run by CI, the pre-commit hook,
and the [`releasing`][] skill, each as `python3 scripts/<area>/<name>.py` from the repo
root. None declares a dependency, and the repo root carries no `pyproject.toml`.

[ADR 006][] already reasons from that constraint (choosing `tomllib` because it is
standard library, and rejecting alternatives needing "a dependency the repo lacks"), and
[ADR 005][] already accepts one of its costs: the flat-frontmatter parser adapted between
[`adr.py`][] and [`validate_manifests.py`][]. Neither states the constraint
itself, so each new script re-decides it, and the first to answer "add a dependency"
answers for everyone.

The cost is real and growing. [`semver`][] would replace hand-written version regexes;
[`PyYAML`][] would replace that adapted parser — the two copies are not identical, since
the ADR-side one parses inline lists and the manifest-side one handles scalars only.
The repo's one git hook is hand-written shell, where the conventional choice, the
[`pre-commit`][] framework, is dependency-bearing — raising the fair question of whether
this constraint is what keeps faster local feedback out of the project.

Packaged skills are a different case: `skills/<name>/` units ship to users with their own
lifecycle, and [`creative-commits`][] already declares dependencies and runs under `uv`.

## Options

### Option 1: Do nothing — keep `scripts/` stdlib-only (Accepted)

Every script imports only the standard library and runs as `python3 scripts/<area>/<name>.py`.

**Pros:** They run unaided — in any clone, any CI job, and the git hook — with nothing to
install, resolve, or keep current.
**Cons:** Hand-written parsing continues, as does the duplication between `scripts/adr`
and `scripts/ci` that no dependency was needed to fix.
**Risks:** Left unwritten, the habit is followed by accident and abandoned by accident —
and a script quietly approximates a grammar it should be parsing, because reaching for the
parser was never an option anyone weighed.

### Option 2: Declare dependencies per script with PEP 723 inline metadata

Give each script a [PEP 723][] header and run it as `uv run scripts/ci/foo.py`.

**Pros:** Real libraries with no root project and no shared lockfile; `uv` already comes
with this repo through `creative-commits`.
**Cons:** Every caller changes from `python3` to `uv run`; dependencies live in a per-file
comment block rather than the project manifest a developer checks first; and Renovate
reads inline metadata through its separate `pep723` manager, which [`renovate.json`][]
would have to add to its `enabledManagers` allowlist.
**Risks:** Each script pins independently, so a library two of them share is coordinated
by nobody and drifts — the failure [`versions.py`][] exists to prevent one level down,
reintroduced at the dependency level.

### Option 3: Add a Python project at the repo root

Give the root a `pyproject.toml` and lockfile.

**Pros:** One manifest where developers expect it, already covered by the existing
Renovate configuration, and one lock so scripts sharing a library share its version.
**Cons:** Every caller changes from `python3` to `uv run`, and a root venv sits alongside
the skill packages' own.
**Risks:** An environment these previously ran in unaided now needs preparing first, so a
cold resolve on a slow or absent network turns a sub-second hook into a stall.

## Decision

Keep `scripts/` stdlib-only. What these scripts parse is almost entirely grammar this
repo defines and constrains — flat skill frontmatter, `X.Y.Z` versions, fixed changelog
headings — where a regex over a known shape is the whole job rather than an
approximation of one. The two exceptions are held at arm's length: skill TOML is read
through stdlib `tomllib`, and `pr.yml` is substring-matched rather than parsed, which
ADR 006 recorded as a deliberate loss of precision.

Recording *which* dependency-bearing option to reach for matters more than it appears,
because the cheaper-looking one is the wrong one. Both impose the same migration on
callers — `python3` becomes `uv run` — differing only in how much moves at once, which at
five scripts is not worth pricing. What separates them is coordination: a root manifest
keeps one version of a shared library, in the place a developer looks first and the place
this repo's Renovate configuration already reads, where per-file blocks let two scripts
drift apart on the same dependency. ~~If a trigger below fires, the answer is a root
project.~~ **Built by ADR 028.** PEP 723 suits a genuinely standalone one-off, not
the way in.

Local feedback is not what this constrains, and should not be defended with it. The
`pre-commit` framework resolves each hook's environment itself, so adopting it would need
neither a root project nor an import in any script. The real obstacle is unrelated:
`pre-commit install` refuses to run while `core.hooksPath` is set, and this repo sets it
for the ADR-index hook. Whether to resolve that is a live question, and a separate one.
Likewise, what leaves `scripts/` unlinted is ADR 005's regime keying enforcement off what
a skill *declares* — and `scripts/` declares nothing.

Duplication is a separate question again. Within a directory, sharing is unremarkable:
`versions.py` holds the version shape that [`release_notes.py`][] and
`validate_manifests.py` both assert, precisely so the two cannot drift. The frontmatter
parsers stay apart only because `scripts/adr` and `scripts/ci` are siblings with no
package between them, and restructuring `scripts/` around one small function is not yet
worth it. That restructuring needs no dependency, so neither option above is what unlocks
it.

**Revisit when either holds:**

- ~~A second script hand-parses a grammar this repo does not define.~~ **Fired and
  discharged by ADR 028** for `scripts/frontmatter.py` — see the 2026-09-05 entry
  below. Hand-writing a grammar approximates someone else's specification, and the
  failure mode changes from "obviously wrong" to "wrong on inputs nobody tried". The
  surviving half: `validate_manifests.py` substring-matches `.github/workflows/pr.yml`
  rather than parsing it, a blindness ADR 006 recorded knowingly, and whether that one
  causes a miss in practice is still the live trigger.
- ~~The frontmatter parser gains a third copy, or the two copies disagree on input both must
  handle.~~ **Fired and discharged by ADR 011**, which replaced both copies with one shared
  module. The general form survives it: a second site hand-parsing the same grammar is the
  trigger, whatever the grammar.

## Consequences

`scripts/` sits outside the lint, format, and type-check layer of the regime ADRs 005 and
006 built — CI runs this code, but nothing checks it, though it is the code enforcing
everything else. What tests exist are `scripts/ci`'s, under `unittest` (with a
`discover -s scripts/ci -t scripts/ci` invocation that exists only because there is no
package) where the rest of the repo uses `pytest`; `scripts/adr` has none, covered only by
CI diffing the index it regenerates. That is the largest cost here, larger than any
duplicated parser, and closing it is a change this decision does not stand in the way of.

Each script's docstring names the constraint and cites this ADR, so it is visible at the
point of temptation rather than only here.

## Revisit watch

The constraint is still shaping design at one remove, which the Risks above anticipated:
when ADR 013 needed a `scope` matcher, a dependency-bearing one was never a live candidate.
So at the next change under `scripts/`, however small, re-ask both:

1. Is anything under `scripts/` approximating a grammar — a glob, a semver range, a TOML
   subset, a path spec — rather than parsing it?
2. Has the workflow substring-match in `validate_manifests.py` caused a miss in practice?
   That is the trigger's second clause, and nobody has tested it.

If either answers yes, this decision is due a revisit, and ADR 011's amendment banner is
the precedent for recording one.

- 2026-08-10: assessed while designing [ADR 013][]'s `scope` field, and **not fired**.
  `scope_matches()` compares string prefixes; `scope_problems()` recognises `*`, `?` and
  `[` to reject glob-shaped entries rather than interpreting them. Neither is parsing. An
  early ADR 013 draft did justify rejecting globs by this decision — matching one would
  mean hand-parsing a grammar the repo does not define. That was false, `fnmatch` being
  standard library, and the justification was removed; what ADR 013 rests on now stands on
  its own.
- 2026-09-03: question 1 **fired**; question 2 still answers no. The trigger reads "a second
  script hand-parses a grammar this repo does not define", the first being
  `validate_manifests.py`'s substring match. The second is `scripts/frontmatter.py`. The
  Decision section counts flat frontmatter as a grammar this repo defines, and for ADR
  frontmatter that was never wholly true: GitHub renders the block through a real YAML parser,
  which ADR 027's summary found the hard way. [`adr.py`][]'s `yaml_hazard()` now refuses values
  that parser would misread. That is recognise-and-reject, which the 2026-08-10 entry ruled is
  not parsing — but `scope`'s grammar is this repo's own invention, so rejecting there is
  definitional, where `RE_YAML_INDICATOR`'s character class is a hand-written approximation of
  someone else's plain-scalar rules, wrong on exactly the inputs nobody tried. The packaged
  skill could take PyYAML on its own, but `scripts/` reaches the parser by symlink and would
  import it too, which this decision forbids; the answer it prescribes is a root project, and
  the monorepo backlog item this repository carried at the time went on to become ADR 028.
  No amendment banner yet: ADR 011's precedent names the amending ADR, and none exists until
  that analysis lands, so this decision stays in force as written.
- 2026-09-05: discharged by ADR 028, which built the root project this decision reserved
  for the trigger above — `scripts/` is now a uv workspace member, resolved against a shared
  root `uv.lock`. `scripts/frontmatter.py` itself is untouched: ADR 028 answers only whether
  `scripts/` can reach a dependency, deferring the PyYAML swap to a follow-up tracked in
  `docs/backlog/`. The surviving half of the trigger — the workflow substring-match causing a
  miss in practice — is unaffected and stays live.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 028]: 028-adopt-a-uv-workspace-at-the-repository-root.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[PEP 723]: https://peps.python.org/pep-0723/
[`pre-commit`]: https://pre-commit.com/
[`PyYAML`]: https://pyyaml.org/
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`renovate.json`]: ../../renovate.json
[`semver`]: https://python-semver.readthedocs.io/
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`versions.py`]: ../../scripts/ci/versions.py
