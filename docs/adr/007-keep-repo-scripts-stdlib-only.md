---
status: Superseded
date: 2026-07-28
scope: [scripts/]
summary: Keep every import under scripts/ stdlib-only, reaching for a root project rather than per-script PEP 723 metadata once a real dependency is needed — the root project ADR 031 later built, without scripts/ importing anything new.
revisit-when: The workflow substring-match already under the constraint causes a miss in practice.
revisit-discharged-by: [31]
superseded-by: 35
---

# 007: Keep repo scripts stdlib-only

## Context

> **Amended by [ADR 011][].** The stdlib-only decision below stands unchanged. Four things
> no longer hold. Scripts now run as `python3 -m scripts.<area>.<name>`. `scripts/` is a
> package. One shared frontmatter parser replaces the copy adapted per directory. And
> `scripts/adr` now has tests. Read any statement below that describes these as they were
> as history, not guidance.
>
> **Discharged in part by [ADR 031][].** The repository root now carries a Python project,
> a uv workspace with `scripts/` as a member. The Decision section reserved that
> contingency for the day a script needed a real dependency. No import in `scripts/`
> changed. PyYAML waits for a follow-up, tracked in `docs/backlog/`. Read "no Python
> project at the repo root" below as history, not as a constraint still standing.

`scripts/` has grown to five files: ADR index generation, manifest validation, release
notes, a shared version pattern, and one test module. CI, the pre-commit hook, and the
[`releasing`][] skill run each one as `python3 scripts/<area>/<name>.py` from the repo
root. None declares a dependency, and the repo root has no `pyproject.toml`.

[ADR 006][] already reasons from that constraint. It chose `tomllib` because `tomllib` is
standard library, and rejected alternatives that needed "a dependency the repo lacks".
[ADR 005][] already accepts one of the constraint's costs, the flat-frontmatter parser
adapted between [`adr.py`][] and [`validate_manifests.py`][]. Neither ADR states the
constraint itself. So each new script decides it again, and the first script to answer
"add a dependency" answers for everyone.

The cost is real and growing. [`semver`][] would replace hand-written version regexes.
[`PyYAML`][] would replace the adapted parser, whose two copies differ: the ADR-side copy
parses inline lists, and the manifest-side copy handles scalars only. The repo's one git
hook is hand-written shell. The conventional choice, the [`pre-commit`][] framework, has
dependencies. That raises a fair question: does this constraint keep faster local
feedback out of the project?

Packaged skills are a different case. Each `skills/<name>/` unit ships to users with its
own lifecycle, and [`creative-commits`][] already declares dependencies and runs under
`uv`.

## Options

### Option 1: Do nothing — keep `scripts/` stdlib-only (Accepted)

Every script imports only the standard library and runs as `python3 scripts/<area>/<name>.py`.

**Pros:** The scripts run unaided in any clone, any CI job, and the git hook, with nothing
to install, resolve, or keep current.
**Cons:** Hand-written parsing continues. So does the duplication between `scripts/adr`
and `scripts/ci`, which no dependency was needed to fix.
**Risks:** While the constraint stays unwritten, people follow it by accident and abandon
it by accident. A script then approximates a grammar it should parse, because nobody ever
weighed reaching for a parser.

### Option 2: Declare dependencies per script with PEP 723 inline metadata

Give each script a [PEP 723][] header and run it as `uv run scripts/ci/foo.py`.

**Pros:** Scripts get real libraries with no root project and no shared lockfile. This
repo already brings `uv` in through `creative-commits`.
**Cons:** Every caller changes from `python3` to `uv run`. Dependencies live in a per-file
comment block, not in the project manifest a developer checks first. Renovate reads inline
metadata through its separate `pep723` manager, so [`renovate.json`][] would have to add
that manager to its `enabledManagers` allowlist.
**Risks:** Each script pins on its own, so nobody coordinates a library two scripts share,
and its versions drift apart. [`versions.py`][] exists to prevent that failure one level
down. This option brings it back at the dependency level.

### Option 3: Add a Python project at the repo root

Give the root a `pyproject.toml` and lockfile.

**Pros:** One manifest sits where developers expect it, the existing Renovate configuration
already covers it, and one lock gives scripts that share a library the same version.
**Cons:** Every caller changes from `python3` to `uv run`, and a root venv sits alongside
the skill packages' own venvs.
**Risks:** An environment where the scripts used to run unaided now needs preparing first.
On a slow or absent network, a cold resolve turns a sub-second hook into a stall.

## Decision

Keep `scripts/` stdlib-only. Almost everything these scripts parse is grammar this repo
defines and constrains: flat skill frontmatter, `X.Y.Z` versions, and fixed changelog
headings. For those, a regex over a known shape does the whole job, not an approximation
of it. The two exceptions are kept at a distance. Stdlib `tomllib` reads skill TOML, and
the scripts substring-match `pr.yml` instead of parsing it, a loss of precision ADR 006
recorded on purpose.

Recording *which* option with dependencies to reach for matters more than it appears,
because the cheaper-looking option is the wrong one. Both impose the same migration on
callers, `python3` to `uv run`, and differ only in how much moves at once. At five scripts
that difference is not worth pricing. Coordination is what separates them. A root manifest
keeps one version of a shared library, in the place a developer looks first and the place
this repo's Renovate configuration already reads. Per-file blocks let two scripts drift
apart on the same dependency. ~~If a trigger below fires, the answer is a root
project.~~ **Built by ADR 031.** PEP 723 suits a standalone one-off script, not the way
in.

This constraint does not limit local feedback, so don't defend it with local feedback. The
`pre-commit` framework resolves each hook's environment itself, so adopting it would need
neither a root project nor an import in any script. The real obstacle is unrelated.
`pre-commit install` refuses to run while `core.hooksPath` is set, and this repo sets
`core.hooksPath` for the ADR-index hook. Whether to resolve that is a live question, and a
separate one. Likewise, `scripts/` goes unlinted because ADR 005's regime keys enforcement
off what a skill *declares*, and `scripts/` declares nothing.

Duplication is a separate question again. Sharing within a directory is unremarkable.
`versions.py` holds the version shape that both [`release_notes.py`][] and
`validate_manifests.py` assert, so that the two cannot drift. The frontmatter parsers stay
apart only because `scripts/adr` and `scripts/ci` are siblings with no package between
them, and restructuring `scripts/` around one small function is not yet worth it. That
restructuring needs no dependency, so neither option above is what unlocks it.

**Revisit when either holds:**

- ~~A second script hand-parses a grammar this repo does not define.~~ **Fired and
  discharged by ADR 031** for `scripts/frontmatter.py`. See the 2026-09-05 entry below. A
  hand-written parser approximates someone else's specification, and the failure mode
  changes from "obviously wrong" to "wrong on inputs nobody tried". One half survives.
  `validate_manifests.py` substring-matches `.github/workflows/pr.yml` instead of parsing
  it, a blindness ADR 006 recorded knowingly. Whether that blindness causes a miss in
  practice is still the live trigger.
- ~~The frontmatter parser gains a third copy, or the two copies disagree on input both must
  handle.~~ **Fired and discharged by ADR 011**, which replaced both copies with one shared
  module. The general form survives: a second site that hand-parses the same grammar is the
  trigger, whatever the grammar.

## Consequences

`scripts/` sits outside the lint, format, and type-check layer that ADRs 005 and 006
built. CI runs this code, but nothing checks it, though it is the code that enforces
everything else. The only tests are `scripts/ci`'s, and they use `unittest` where the rest
of the repo uses `pytest`. Their `discover -s scripts/ci -t scripts/ci` invocation exists
only because there is no package. `scripts/adr` has no tests. Only CI's diff of the index
it regenerates covers it. That gap is the largest cost here, larger than any duplicated
parser, and this decision does not stand in the way of closing it.

Each script's docstring names the constraint and cites this ADR, so a developer meets it
at the point of temptation, not only here.

## Revisit watch

The constraint still shapes design at one remove, as the Risks above anticipated. When
ADR 013 needed a `scope` matcher, nobody considered one with a dependency. So at the next
change under `scripts/`, however small, ask both questions again:

1. Is anything under `scripts/` approximating a grammar, such as a glob, a semver range, a
   TOML subset, or a path spec, instead of parsing it?
2. Has the workflow substring-match in `validate_manifests.py` caused a miss in practice?
   That is the trigger's second clause, and nobody has tested it.

If either answer is yes, this decision is due a revisit. ADR 011's amendment banner is the
precedent for recording one.

- 2026-08-10: assessed while designing [ADR 013][]'s `scope` field, and **not fired**.
  `scope_matches()` compares string prefixes. `scope_problems()` recognises `*`, `?` and
  `[` to reject glob-shaped entries, not to interpret them. Neither function parses. An
  early ADR 013 draft did justify rejecting globs by this decision, saying that matching
  one would mean hand-parsing a grammar the repo does not define. That was false, because
  `fnmatch` is standard library. The draft dropped the justification, and ADR 013 now
  rests on its own reasons.
- 2026-09-03: question 1 **fired**. Question 2 still answers no. The trigger reads "a second
  script hand-parses a grammar this repo does not define", and the first such script is
  `validate_manifests.py`'s substring match. The second is `scripts/frontmatter.py`. The
  Decision section counts flat frontmatter as a grammar this repo defines, and for ADR
  frontmatter that was never wholly true. GitHub renders the block through a real YAML
  parser, as ADR 027's summary found the hard way. [`adr.py`][]'s `yaml_hazard()` now
  refuses values that parser would misread. That is recognise-and-reject, which the
  2026-08-10 entry ruled is not parsing. But `scope`'s grammar is this repo's own
  invention, so rejecting there is definitional. `RE_YAML_INDICATOR`'s character class,
  by contrast, is a hand-written approximation of someone else's plain-scalar rules, wrong
  on exactly the inputs nobody tried. The packaged skill could take PyYAML on its own. But
  `scripts/` reaches the parser by symlink and would import PyYAML too, which this decision
  forbids. The answer this decision prescribes is a root project, and the monorepo backlog
  item this repository carried at the time went on to become ADR 031. No amendment banner
  yet. ADR 011's precedent names the amending ADR, and none exists until that analysis
  lands, so this decision stays in force as written.
- 2026-09-05: discharged by ADR 031, which built the root project this decision reserved
  for the trigger above. `scripts/` is now a uv workspace member, resolved against a shared
  root `uv.lock`. ADR 031 leaves `scripts/frontmatter.py` itself untouched. It answers only
  whether `scripts/` can reach a dependency, and defers the PyYAML swap to a follow-up
  tracked in `docs/backlog/`. The surviving half of the trigger, the workflow
  substring-match causing a miss in practice, is unaffected and stays live.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 031]: 031-adopt-a-uv-workspace-at-the-repository-root.md
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
