---
status: Superseded
date: 2026-08-11
superseded-by: 16
scope: [.agents/rules/testing.md, scripts/]
summary: Anchor a script's default paths to `__file__` where the paths are injectable parameters, and keep them relative to the working directory where they are module-level constants the tests chdir around — the discriminator is whether a test can inject a fixture path, not which form reads better.
revisit-when: A script must deliberately act on whichever checkout the caller is standing in, rather than on the one it ships inside.
---

# 015: Anchor default paths to the module

## Context

Every script under `scripts/` resolves its paths relative to the working directory:
`Path("docs/adr")`, `Path(".claude-plugin/plugin.json")`, `Path(".github/workflows/pr.yml")`.
The documented way to run them is `python3 -m scripts.<area>.<name>` from the repository
root ([ADR 011][]). `-m` puts the working directory on `sys.path`, so a wrong directory
usually fails at import instead of failing silently.

Usually, not always. With the repository root on `PYTHONPATH`, the import succeeds from
anywhere, and the paths then name whatever sits under the caller's working directory.
[ADR 013][] raised the stakes. `generate_index` gained a `repo_root`, which it uses to
check that every `scope` entry still names something on disk. A wrong working directory
therefore no longer produces a missing-file error. It produces a *plausible* error:
entries reported as rotten against a tree that was never theirs.

The two modules that resolve paths do so differently enough that one rule cannot obviously
cover both. [`adr.py`][] takes its directories as parameters, with defaults so that callers
need no arguments. [`validate_manifests.py`][] holds five module-level constants and reads
them directly, and [its tests][] `chdir` into a fixture repository instead of patching all
five. The module docstring already records that stance, along with a warning that
anchoring one of the constants to `__file__` would silently break it.

## Options

Options 2, 3, and 4 all make a script act on the tree it ships inside, not on whatever tree
the caller is standing in. That is the whole point, so it ranks none of them. They differ
only in what they cost the tests, and the comparison rests on that cost.

### Option 1: Do nothing — every path stays relative to the working directory

**Pros:** One rule across `scripts/`, and every test can still `chdir` into a fixture.
**Cons:** The invocation contract is documented but not enforced, so the one case that
escapes it, the repository root on `PYTHONPATH`, fails silently.
**Risks:** A scope check run from the wrong tree reports entries as rotten. That report
invites someone to "fix" the ADRs by deleting entries that were correct.

### Option 2: Anchor defaults to `__file__`, keep injectable constants relative (Accepted)

Where paths are parameters, their defaults resolve from the module. Where they are
module-level constants that a test redirects by `chdir`, they stay relative.

**Pros:** Each module keeps the property its tests depend on, and neither module has to be
rewritten to gain it.
**Cons:** Two forms in one directory, so an author has to read the rule before a new
script picks one.
**Risks:** A diff does not show the distinction. A later edit that turns a parameter into a
module constant, or the reverse, silently moves a module to the wrong side.

### Option 3: Anchor every path to `__file__`

**Pros:** One form everywhere, and no module can run against the wrong tree.
**Cons:** `validate_manifests`'s tests redirect five constants with a single `chdir`.
Anchoring the constants means injecting all five per test, or patching them, and the
module's docstring already rejects patching as a risk of a half-applied patch.
**Risks:** Those tests would keep passing while silently reading the real repository
instead of the fixture. That is the failure their current stance exists to prevent.

### Option 4: Require an explicit root argument on every script

Each script takes `--repo-root`, with no default.

**Pros:** Nothing is implicit, and a caller in the wrong tree finds out at once.
**Cons:** Every call site changes to pass a value that is the same in all of them: the
hook, two CI jobs, and the release skill.
**Risks:** The obvious way to supply the value is `$(pwd)`. That reintroduces the
working-directory dependence this decision removes, now spelled out and looking
deliberate.

## Decision

Anchor a default, and leave a constant alone. The discriminator is not which form reads
better, but **whether a test can inject a fixture path**. Where a test can, the default is
free to name this repository, because no test relies on it. Where a test cannot, the path
must stay relative, or the tests lose the only redirection they have.

So `generate_index` is the module to change, and `validate_manifests` is the module to
leave. The rule also explains why the two modules now look different without either being
wrong. It predicts what a new script should do, too: take its paths as parameters and
anchor the defaults. That is the better shape anyway, and it keeps the exception from
spreading.

Use `Path(__file__).resolve()`, not `Path(__file__)`, so a symlinked checkout resolves to
the real tree. This repository symlinks `CLAUDE.md` and `.claude`, so that case is not
hypothetical.

## Consequences

- A test that calls `generate()` with no arguments now rewrites this repository's real
  index whatever the working directory is. Before, a `chdir` redirected it. The test
  module says so, and its tests of default resolution assert the paths instead of calling
  the function.
- `.agents/rules/testing.md` gains a third stance. A module whose paths are parameters is
  tested by injection, and the only test that changes directory is the one asserting that
  a `chdir` *cannot* redirect the defaults.
- The two forms coexist in `scripts/`, so an author has to read the rule, not infer it from
  a neighbouring file. That is the cost of Option 2, and the cost recurs every time someone
  adds a script.
- Nothing enforces the distinction. A parameter demoted to a module constant keeps its
  `__file__` anchor and quietly breaks the `chdir` that its new tests would expect. This
  ADR is the only thing in the place where a check would go.

[ADR 011]: 011-make-scripts-a-package.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[its tests]: ../../scripts/ci/test_validate_manifests.py
