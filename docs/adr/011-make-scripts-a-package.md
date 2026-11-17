---
status: Superseded
date: 2026-08-01
scope: [scripts/]
summary: Make scripts/ a Python package and run every script as `python3 -m scripts.<area>.<name>`, so the frontmatter parser can be imported once instead of adapted per directory; this amends ADR 007's plain-file invocation and retires its parser-duplication trigger, leaving its stdlib-only constraint intact; run the suite with `python3 -m unittest discover -s scripts -t .`.
superseded-by: 35
---

# 011: Make scripts a package

## Context

[ADR 007][] recorded a flat-frontmatter parser adapted between [`adr.py`][] and
[`validate_manifests.py`][], and set a revisit trigger: "The frontmatter parser gains a third
copy, or the two copies disagree on input both must handle."

The second half fired. Both copies silently truncated a wrapped value. The fix needed three
rules, all applying to input both parsers read: reject an indented continuation, reject a
key that contains whitespace, and reject a repeated key. Fixing both copies by hand leaves
two implementations to keep in step, and two test suites for one behaviour.

To share the parser, scripts need somewhere to import it from. `scripts/adr` and
`scripts/ci` are siblings with no package between them. A plain-file script can import
only from its own directory, because `sys.path[0]` is the script's location. ADR 007
anticipated this: "restructuring `scripts/` around one small function is not yet worth
it. That restructuring needs no dependency, so neither option above is what unlocks it."

## Options

### Option 1: Do nothing — keep an adapted copy per directory

Apply the three fixes twice, and every future fix twice.

**Pros:** No invocation changes anywhere, and each script stays runnable as a plain file.
**Cons:** One behaviour has two implementations and two test suites to keep in step.
**Risks:** The trigger has fired once already. The next divergence is likelier to go
unnoticed, because the copies now look so alike that a reader assumes they are identical.

### Option 2: Make `scripts/` a package (Accepted)

Add `__init__.py` to `scripts/` and each subdirectory, put the parser in
[`frontmatter.py`][], and invoke every script as `python3 -m scripts.<area>.<name>`.

**Pros:** Scripts use ordinary imports, and give up nothing ADR 007 protects.
**Risks:** `-m` is easy to forget. A contributor who runs the old path form gets an import
error, not a subtle failure. That is the right way round, but it still catches anyone
working from memory.

### Option 3: Flatten `scripts/` into one directory, still without a package

Drop the `adr`/`ci` split so sibling import needs no package, and keep plain-file invocation.

**Pros:** Plain-file invocation stays exactly as ADR 007 assumes.
**Cons:** The grouping by purpose goes, and every script gets a new name.
**Risks:** The renames bury this change's real content in a diff of moves.

### Option 4: Put the parser on `sys.path` from each script

Keep the layout, and have each importer insert `scripts/` onto the path first.

**Pros:** Only the two importing scripts change. No caller changes at all.
**Cons:** Each script carries two lines of path manipulation ahead of its imports.
**Risks:** A script's imports then depend on how it was invoked. That is the opposite of
ADR 007's premise that these scripts run unaided, and the failure shows up as an
unrelated-looking `ModuleNotFoundError`.

## Decision

Make it a package.

ADR 007 already settled the substance. It named divergence between the copies as the thing
that must not happen, so the fix is to remove the second copy, not to keep the two in sync.
ADR 007 left the mechanism open, on the grounds that restructuring was not yet worth it.
Three shared fixes at once change that.

Option 4 is the cheap option and the wrong one. A `sys.path` insertion makes a script's
imports depend on how it was launched, whereas a package makes them work by construction.
Option 3 gets the same outcome by renaming everything, and discards the grouping that
tells a reader which job a script belongs to.

**This decision does not touch ADR 007's constraint.** Everything under `scripts/` remains
standard-library only, with no project at the repository root, no lockfile, and nothing to
install. A package directory is not a dependency. This decision amends ADR 007's
*invocation*, and narrows "runs unaided" slightly. `-m` resolves `scripts` because Python
prepends the working directory to `sys.path`. So the scripts now run from the repo root
under default path semantics, not from anywhere.

## Consequences

Every caller now runs `python3 -m scripts.<area>.<name>` from the repo root. The callers
are the [`.githooks/pre-commit`][] hook, [`pr.yml`][] and the release workflow, the
[`releasing`][] skill, and the README, and all of them already ran from the repo root.
Running a script by path now fails with an import error, which is loud, not subtle.

The hook meets that rule without doing anything. Git runs a hook with the working
directory at the top of the working tree, whatever directory the committer typed `git
commit` in. This is worth stating because the failure it implies is a phantom. Run the
module by hand from a subdirectory and it raises `ModuleNotFoundError`, which reads as a
bug in the hook but is not one. Reproduce the failure through an actual commit before
changing anything here.

One test command covers every script:
`python3 -m unittest discover -s scripts -t . -p 'test_*.py'`. Before, discovery had to
run once per script directory.

ADR 007 called the lack of tests for `scripts/adr` "the largest cost here, larger than any
duplicated parser". That cost is now paid. The generator has its own suite, and so does
the shared parser.

The pull-request path filter now routes any `scripts/` change to both the `adr` job and
the `manifests` job. It used to route the two directories separately, which is wrong once
a parser change can break either consumer.

`validate_manifests.py`'s own checks have their own suite too, so no script under
`scripts/` is unexercised.

Two shared modules now sit at different levels: `frontmatter.py` at the package root, and
`versions.py` inside `scripts/ci`. Share a module at the narrowest package that contains
every importer. Then a module that moves up signals that a second area started using it.

[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`frontmatter.py`]: ../../scripts/frontmatter.py
[`pr.yml`]: ../../.github/workflows/pr.yml
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
