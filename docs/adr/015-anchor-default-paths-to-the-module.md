---
status: Accepted
date: 2026-08-11
scope: [.agents/rules/testing.md, scripts/]
summary: Anchor a script's default paths to `__file__` where the paths are injectable parameters, and keep them relative to the working directory where they are module-level constants the tests chdir around — the discriminator is whether a test can inject a fixture path, not which form reads better.
revisit-when: A script must deliberately act on whichever checkout the caller is standing in, rather than on the one it ships inside.
---

# 015: Anchor default paths to the module

## Context

Every script under `scripts/` resolves its paths relative to the working directory:
`Path("docs/adr")`, `Path(".claude-plugin/plugin.json")`, `Path(".github/workflows/pr.yml")`.
Running them is documented as `python3 -m scripts.<area>.<name>` from the repo root
([ADR 011][]), and `-m` puts the working directory on `sys.path`, so a wrong directory
usually fails at import rather than silently.

Usually, not always. With the repo root on `PYTHONPATH`, the import succeeds from anywhere
and the paths then name whatever sits under the caller's working directory. [ADR 013][]
raised the stakes: `generate_index` gained a `repo_root` used to check that every `scope`
entry still names something on disk, so a wrong working directory no longer produces a
missing-file error but a *plausible* one — entries reported as rotten against a tree that
was never theirs.

The two modules that resolve paths do it differently enough that one rule cannot obviously
cover both. [`generate_index.py`][] takes its directories as parameters, defaulting them so
callers need no arguments. [`validate_manifests.py`][] holds five module-level constants and
reads them directly, and [its tests][] `chdir` into a fixture repo rather than patching all
five — a stance its module docstring already records, along with the warning that anchoring
one of them to `__file__` would break that silently.

## Options

Options 2, 3 and 4 all make a script act on the tree it ships inside rather than on whatever
the caller is standing in, which is the whole point and ranks none of them. They differ only
in what that costs the tests, so that is what the comparison rests on.

### Option 1: Do nothing — every path stays relative to the working directory

**Pros:** One rule across `scripts/`, and every test keeps the `chdir`-into-a-fixture
technique available.
**Cons:** The invocation contract is documented but unenforced, so the one case that
escapes it — the repo root on `PYTHONPATH` — is silent.
**Risks:** A scope check run from the wrong tree reports entries as rotten and invites
someone to "fix" the ADRs by deleting entries that were correct.

### Option 2: Anchor defaults to `__file__`, keep injectable constants relative (Accepted)

Where paths are parameters, their defaults resolve from the module. Where they are
module-level constants a test redirects by `chdir`, they stay relative.

**Pros:** Each module keeps the property its tests depend on, and neither has to be
rewritten to gain it.
**Cons:** Two forms in one directory, so the rule has to be read before a new script
picks one.
**Risks:** The distinction is invisible in a diff — a later edit turning a parameter into
a module constant, or the reverse, silently moves a module to the wrong side.

### Option 3: Anchor every path to `__file__`

**Pros:** One form everywhere, and no module can be run against the wrong tree.
**Cons:** `validate_manifests`'s tests redirect five constants with a single `chdir`;
anchoring them means injecting all five per test, or patching them, which its docstring
already rejects as a half-applied-patch risk.
**Risks:** Those tests would keep passing while silently reading the real repository
instead of the fixture — the failure their current stance exists to prevent.

### Option 4: Require an explicit root argument on every script

Each script takes `--repo-root`, with no default.

**Pros:** Nothing is implicit, and a caller in the wrong tree is told so immediately.
**Cons:** Every call site changes — the hook, two CI jobs, the release skill — to pass a
value that is the same in all of them.
**Risks:** The obvious way to supply it is `$(pwd)`, which reintroduces exactly the
working-directory dependence this decision removes, now spelled out and looking deliberate.

## Decision

Anchor a default; leave a constant alone. The discriminator is not which form reads better
but **whether a test can inject a fixture path**: where it can, the default is free to name
this repository, because no test relies on it; where it cannot, the path must stay relative
or the tests lose the only redirection they have.

That makes `generate_index` the module to change and `validate_manifests` the module to
leave, and it explains why the two now look different without either being wrong. It also
predicts what a new script should do: take its paths as parameters and anchor the defaults,
which is the better shape anyway, and keeps the exception from spreading.

`Path(__file__).resolve()` rather than `Path(__file__)`, so a symlinked checkout resolves to
the real tree; this repository symlinks `CLAUDE.md` and `.claude`, so that case is not
hypothetical.

## Consequences

- A test that calls `generate()` with no arguments now rewrites this repository's real
  index whatever the working directory is, where previously a `chdir` redirected it. The
  test module says so, and its default-resolution tests assert the paths rather than
  calling the function.
- `.agents/rules/testing.md` gains the third stance: a module whose paths are parameters
  is tested by injection, and the only test that changes directory is the one asserting a
  `chdir` *cannot* redirect the defaults.
- The two forms coexist in `scripts/`, so the rule has to be read rather than inferred
  from a neighbouring file. That is the cost of Option 2 and it is paid every time someone
  adds a script.
- Nothing enforces the distinction. A parameter demoted to a module constant keeps its
  `__file__` anchor and quietly breaks the `chdir` its new tests would expect — the ADR is
  the only thing standing where a check would go.

[ADR 011]: 011-make-scripts-a-package.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[its tests]: ../../scripts/ci/test_validate_manifests.py
