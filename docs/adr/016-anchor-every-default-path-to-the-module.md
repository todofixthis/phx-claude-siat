---
status: Superseded
date: 2026-08-15
scope: [.agents/rules/testing.md, scripts/]
summary: Anchor every script's default paths to `__file__`, read that anchor only on the `__main__` line, and require a `repo_root` everywhere below it — so tests inject a fixture root and never chdir, and a script given no path acts on the tree it ships in.
revisit-when: A script must resolve a path it was given no argument for against whichever checkout the caller is standing in, rather than against the one it ships inside.
superseded-by: 27
---

# 016: Anchor every default path to the module

## Context

[ADR 015][] anchored a script's default paths to `__file__` where those paths are
injectable parameters. Where they are module-level constants that the tests `chdir`
around, it left them relative to the working directory. Its discriminator was **whether a
test can inject a fixture path**. Three things ADR 015 did not weigh make that
discriminator unsound.

Its two categories do not partition the modules. [`release_notes.py`][] holds two
module-level relative constants *and* offers them as `--changelog`, `--plugin-manifest`,
and `plugin_version`'s argument. It sits in both categories at once, and
[`test_release_notes.py`][] both injects paths and `chdir`s. ADR 015 counted two modules
that resolve default paths. There are three, and the one it missed is the one that breaks
the categories.

ADR 015 rejected its Option 3, anchor everything, on a cost it never checked: that
[`validate_manifests.py`][]'s tests would have to inject five paths per test, or patch
them, because a single `chdir` currently redirects all five. That cost is avoidable, so
ADR 015 ranked the option last against an obstacle that need not exist.

What is left separates the modules by no property they have, only by which test shape each
acquired first. That describes the repository at one moment. It is not a rule a later
author can apply, because their tests do not exist yet.

## Options

Every option below agrees that a script should act on the tree it ships inside, not on
whichever tree the caller is standing in. That is ADR 015's finding, and none of the
options reopens it. They differ over whether the rule carries an exception.

### Option 1: Do nothing

ADR 015 stands as written, `release_notes` goes on breaching it, and nobody notices.

**Pros:** No change to three modules and their tests, and every test can still `chdir`
into a fixture.
**Cons:** The rule is already false about the repository it governs, and its lack of
enforcement kept that quiet for a month.
**Risks:** The next reader finds the same undercount and writes this ADR anyway, after
trusting the rule long enough to place a script by it.

### Option 2: Anchor every default, with one injectable `repo_root` per module (Accepted)

Each module defines `REPO_ROOT` from `__file__` and reads it on the `__main__` line alone.
Every function below that line requires a `repo_root`, holds its path constants
repo-relative, and joins the two at the call that touches the filesystem.

**Pros:** One form, so an author has nothing to read before placing a new script. Nothing
has a default, entry points included, so a test that omits its fixture root raises
`TypeError` instead of passing while it reads the real repository. `validate_manifests`
gains one parameter per check, not five per test.
**Cons:** Three modules and their tests change together. Keeping constants repo-relative
and joining them at use is a second convention, and it exists only to keep error messages
readable.
**Risks:** A check that builds a `Path` inline instead of joining it to `repo_root`
reintroduces the working-directory dependence, and nothing reports it.

### Option 3: Keep ADR 015's discriminator and exempt `release_notes`

Record the module as a stated exception, since it belongs to both categories and so cannot
simply go in one.

**Pros:** The smallest change that makes ADR 015 true about the repository.
**Cons:** An exception with nothing behind it makes the real rule "whichever way the tests
were written first". The discriminator would have to be rewritten before anyone could
apply it.
**Risks:** ADR 015 recorded that a diff does not show the distinction, so a parameter
demoted to a constant silently moves a module to the wrong side. ADR 015 accepted that
risk for a benefit this option no longer has.

## Decision

Anchor every default path to the module, with no exception, and make `repo_root` the
single injection point per module.

The checks require `repo_root` instead of defaulting it, and so does each entry point:
`validate`, `main`, and `generate`. The entry points are what make the guarantee real. A
default on an entry point would let `ValidateTests` call `validate()` bare and pass against
the real repository. The `chdir` assertion existed to catch that failure. The signature
now gives those tests the property they used to get from a `chdir`, so nobody has to
remember anything.

Path constants stay repo-relative, and the code joins them where it reads them, so every
message names a path a reader can act on. Absolute paths would leak a temporary directory
into test failures and a container path into CI. And `check_skill_tooling` matches a skill
directory against the workflow's text, where only the repo-relative form appears.

[`mutate.py`][] is not an exception to any of this. It resolves no default path. It takes
its target as a required `--file`, and it runs its test command in the caller's tree
deliberately, because the two must name the same checkout. An argument the caller must
supply is not the failure this decision prevents, ~~which is why the revisit trigger names a
path *no* argument was given for~~. [ADR 024][] met that trigger: the shipped ADR tool is
the script it describes, and resolves its root from the caller's path, not from the tree it
ships in. [ADR 027][] restates this decision by the tree a script acts on, and supersedes
it.

ADR 015 rejected an explicit `--repo-root` on every script. This correction leaves that
option untouched, and it stays rejected for the reason ADR 015 gave: the obvious way to
supply the value is `$(pwd)`, which restores the working-directory dependence and makes it
look deliberate.

Keep `Path(__file__).resolve()`. ADR 015 justified it by this repository's `CLAUDE.md` and
`.claude` symlinks, and that justification is wrong twice over. The surviving links all
point inside the tree and change nothing about where the root resolves, and `.claude` is
no longer a symlink at all. `resolve()` is worth keeping for a checkout reached through a
symlinked parent, where an unresolved anchor and a caller's resolved path compare unequal.

## Consequences

- [`.agents/rules/testing.md`][] replaces its two stances with one: where a module resolves
  paths, pass a fixture root and never `chdir`.
- [`test_validate_manifests.py`][] loses the `chdir` and the assertion that guarded it. That
  assertion existed because a lost `chdir` let a positive test pass against the real
  repository. `test_release_notes.py` loses two more. Each test module gains a fixture
  root instead.
- [`adr.py`][] was already anchored, but it defaulted its root in every signature that took
  one and held its `docs/adr` constant pre-joined. It now defaults in none, and that
  constant is repo-relative like the rest.
- No call site changes. The hook, three CI jobs, and the release skill all invoke these
  modules as `python3 -m scripts.<area>.<name>` and pass no paths. That invocation is the
  one whose behaviour this decision fixes.
- Nothing enforces the anchoring, exactly as ADR 015 recorded. ADR 015 left two things
  unenforced. This decision removes the second, which side a module sits on, and leaves
  the first.
- A script that must read the caller's tree now needs an argument saying so, not a default
  nobody declared.

[ADR 015]: 015-anchor-default-paths-to-the-module.md
[`.agents/rules/testing.md`]: ../../.agents/rules/testing.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[ADR 027]: 027-anchor-a-script-to-the-tree-it-acts-on.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`mutate.py`]: ../../scripts/dev/mutate.py
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`test_release_notes.py`]: ../../scripts/ci/test_release_notes.py
[`test_validate_manifests.py`]: ../../scripts/ci/test_validate_manifests.py
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
