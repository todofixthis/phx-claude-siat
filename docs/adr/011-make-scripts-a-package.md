---
status: Accepted
date: 2026-08-01
scope: [scripts/]
summary: Make scripts/ a Python package and run every script as `python3 -m scripts.<area>.<name>`, so the frontmatter parser can be imported once instead of adapted per directory; this amends ADR 007's plain-file invocation and retires its parser-duplication trigger, leaving its stdlib-only constraint intact; run the suite with `python3 -m unittest discover -s scripts -t .`.
---

# 011: Make scripts a package

## Context

[ADR 007][] recorded a flat-frontmatter parser adapted between [`generate_index.py`][] and
[`validate_manifests.py`][], and set a revisit trigger: "The frontmatter parser gains a third
copy, or the two copies disagree on input both must handle."

The second half fired. Both copies silently truncated a wrapped value, and the fix needed
three rules — reject an indented continuation, a key containing whitespace, a repeated key —
all applying to input both parsers read. Fixing both by hand leaves two implementations to
keep in step and two test suites for one behaviour.

Sharing the parser needs somewhere to import it from. `scripts/adr` and `scripts/ci` are
siblings with no package between them, so a plain-file script can import only its own
directory — `sys.path[0]` is the script's location. ADR 007 anticipated this: "restructuring `scripts/` around one small function is not yet worth it. That
restructuring needs no dependency, so neither option above is what unlocks it."

## Options

### Option 1: Do nothing — keep an adapted copy per directory

Apply the three fixes twice, and every future fix twice.

**Pros:** No invocation changes anywhere; each script stays runnable as a plain file.
**Cons:** One behaviour, two implementations, and two test suites to keep honest.
**Risks:** The trigger has fired once already, and the next divergence is likelier to go
unnoticed, because the copies now look identical enough that a reader assumes they are.

### Option 2: Make `scripts/` a package (Accepted)

Add `__init__.py` to `scripts/` and each subdirectory, put the parser in
[`frontmatter.py`][], and invoke every script as `python3 -m scripts.<area>.<name>`.

**Pros:** Ordinary imports, at the cost of nothing ADR 007 protects.
**Risks:** `-m` is easy to forget. A contributor running the old path form gets an import
error rather than a subtle failure, which is the right way round, but it is still a trap for
anyone working from memory.

### Option 3: Flatten `scripts/` into one directory, still without a package

Drop the `adr`/`ci` split so sibling import needs no package, and keep plain-file invocation.

**Pros:** Keeps plain-file invocation exactly as ADR 007 assumes.
**Cons:** Loses the grouping by purpose, and renames every script.
**Risks:** The rename churn buries this change's real content in a diff of moves.

### Option 4: Put the parser on `sys.path` from each script

Keep the layout, and have each importer insert `scripts/` onto the path first.

**Pros:** Touches only the two importing scripts; no caller changes at all.
**Cons:** Two lines of path manipulation in each script, ahead of its imports.
**Risks:** Makes a script's imports depend on how it was invoked — the opposite of ADR 007's
premise that these run unaided, and a failure mode that presents as an unrelated
`ModuleNotFoundError`.

## Decision

Make it a package.

ADR 007 already settled the substance: it named divergence between the copies as the thing
that must not happen, so the fix is to remove the second copy rather than keep synchronising
it. What it left open was the mechanism, on the grounds that restructuring was not yet worth
it — three shared fixes at once is what changes that.

Option 4 is the cheap one and the wrong one: a `sys.path` insertion makes a script's imports a
function of how it was launched, where a package makes them work by construction. Option 3
buys the same outcome at the price of renaming everything, and discards the grouping that
tells a reader which job a script belongs to.

**This decision does not touch ADR 007's constraint.** Everything under `scripts/` remains
standard-library only, with no project at the repository root, no lockfile, and nothing to
install — a package directory is not a dependency. What it amends is ADR 007's *invocation*,
and "runs unaided" narrows slightly: `-m` resolves `scripts` because Python prepends the
working directory to `sys.path`, so these now run from the repo root under default path
semantics rather than from anywhere.

## Consequences

Every caller now runs `python3 -m scripts.<area>.<name>` from the repo root: the
[`.githooks/pre-commit`][] hook, [`pr.yml`][] and the release workflow, the [`releasing`][]
skill, and the README — each from the repo root, which all of them already used. Running a
script by path now fails with an import error, which is loud rather than subtle.

The hook satisfies that rule without doing anything: Git runs a hook with the working
directory at the top of the working tree, whatever directory the committer typed `git
commit` in. Worth stating because the failure it implies is a phantom — run the module
by hand from a subdirectory and it raises `ModuleNotFoundError`, which reads as a bug in
the hook and is not one. Reproduce through an actual commit before changing anything
here.

One test command covers the lot — `python3 -m unittest discover -s scripts -t . -p 'test_*.py'`
— where discovery previously had to run once per script directory.

ADR 007 called `scripts/adr` having no tests "the largest cost here, larger than any duplicated
parser". That cost is now paid: the generator has its own suite, and the shared parser one of
its own.

The pull-request path filter routes any `scripts/` change to both the `adr` and `manifests`
jobs, where it previously routed the two directories separately — wrong once a parser change
can break either consumer.

`validate_manifests.py`'s own checks have their own suite too, so no script under `scripts/`
is now unexercised.

Two shared modules now sit at different levels — `frontmatter.py` at the package root,
`versions.py` inside `scripts/ci`. Share at the narrowest package containing every importer,
so a module pulled up is a signal that a second area started using it.

[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[`frontmatter.py`]: ../../scripts/frontmatter.py
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`pr.yml`]: ../../.github/workflows/pr.yml
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
