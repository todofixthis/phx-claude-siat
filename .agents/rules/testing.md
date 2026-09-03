---
paths:
  - "**/test_*.py"
  - "**/*_test.py"
---

# Testing conventions

## Name each class for its subject, and say which layer it is

Every test class opens with a docstring naming its layer and its subject, and takes
its name from the subject:

```py
class CellTests(unittest.TestCase):
    """Unit tests for ``cell()``."""

class GenerateFailureTests(AdrDirTestCase):
    """Integration tests: on any error the index must be left exactly as it was found."""

class AdrDirTestCase(unittest.TestCase):
    """A temp directory standing in for docs/adr, living for the whole test."""
```

A unit class is `<Function>Tests` and covers one function called directly: every edge
case of *its* input — malformed values, boundaries, each shape a field can take. An
integration class is `<EntryPoint>Tests` and reaches several units through the real
entry point. A class holding no tests is a fixture base, named `<Area>TestCase`, and
its docstring describes the fixture instead of a layer.

Split one subject across several classes where the cases fall into groups that share
a setup or a theme, and name each for its group rather than repeating the subject —
`GenerateFailureTests`, `DefaultDirectoryTests`, `BlockScalarTests`. Subject and layer
then live in the module docstring, which every such class inherits, and each class
docstring names only what its group is.

## Put a case in the layer that owns it

An integration class covers only what emerges from the composition: which file an
error is attributed to, whether a bad item stops the ones after it, what is left on
disk, the exit code. Everything else about one function's input belongs to that
function's unit class — exercised through the entry point it runs twice, fails for
two reasons, and localises neither.

Where the function under test delegates to a shared helper, the unit asserts that one
representative problem *propagates*, leaving the helper's own catalogue of cases to
the helper's tests.

## Every test function carries a docstring naming the scenario

The function name says what is called; the docstring says what must hold, in one
sentence. Write the sentence a reviewer would need to judge whether the assertion is
the right one — not a restatement of the call.

## One reason to fail per test

Start each test from a fixture that passes, break exactly one thing, and assert the
error naming it. A test asserting two unrelated faults reports whichever fires first
and hides the other. The exception is a test whose subject *is* reporting everything
at once — that one breaks several things deliberately and asserts all of them, so a
check short-circuiting its siblings fails here.

A passing fixture only means that while it does pass, so assert it: one test that runs
the untouched fixture and expects success. Without it, a fixture that has quietly
broken makes every negative test pass for the wrong reason.

## Say what the module does about the working directory, and why

Where the subject takes paths at all, the module docstring states its stance on `chdir`,
and which of two stances it takes depends on whose tree the module acts on. A module that
acts on the caller's tree — a tool shipped under `skills/` that resolves its root from the
path it was given, per ADR 024 — cites ADR 024, has no anchor of its own to test, and owes
tests that resolution follows the path given, a fixture root passed explicitly and a
worktree-shaped one included, and never the module's location; the rest of this section
does not apply to it. A module that acts on the tree it ships in cites ADR 016 and says
that the subject requires a root so no call can reach the real repository. There is no
working-directory-relative alternative for that second kind — ADR 015 described one and is
superseded, so a rule found there is not in force.

**Pass a fixture root and never chdir.** The subject anchors itself with
`REPO_ROOT = Path(__file__).resolve().parents[2]`, read on the `__main__` line and nowhere
else; every function below it requires the root, entry points included, and joins it to
repo-relative constants where each is read. So omitting the fixture root is a `TypeError`
rather than a test that passes while reading the real repository — the guarantee a `chdir`
used to buy with an assertion someone had to remember. Don't add a default back and reopen
it. Where a subject takes a second anchor as well, the entry point derives it from the
root and the tests inject each separately, so a fixture can point them at unrelated
directories.

Two tests cover the anchor itself, and a module resolving paths owes both. Neither calls
the subject; they read the constants, so they belong to a unit class named for the
constant rather than for an invocation:

- a `chdir` into a temp directory, asserting the anchor is absolute and does not fall
  inside it — that a moved cwd *cannot* redirect it;
- no `chdir` at all, asserting the anchor reaches this repository (`__file__` is relative
  to it, and a file the subject expects is really there). This is the one that catches
  `parents[1]` for `parents[2]`, which the first test passes happily. Where the module
  ships under `skills/` it runs from a plugin cache with the repository nowhere near it,
  so this second test asserts instead that the anchor names the files the skill bundles —
  true in a checkout and in a cache alike, and it still catches the miscounted parent.

## Guard against a partial pass

A single-item case cannot tell "handled every item" from "stopped after the first".
Where the subject walks a collection, give it two items. Where the subject produces
one artefact — a generated file, a rendered row — assert the artefact entire rather
than that it contains something expected; a subject that only appends to a list of
errors is asserted per error instead.

## Assert the output a human reads

Where a script prints a summary or a count, assert it. It is what a maintainer
believes when they skim a CI log, and a count disagreeing with the file is how a
skipped item goes unnoticed.

## Mutation-test each check you add

After adding a check to the code under test, disable it in place, confirm a test
fails, and restore it before committing:

```
python3 -m scripts.dev.mutate --file skills/writing-adrs/adr.py \
    --anchor 'if not target.exists():' --with 'if False:' \
    -- uv run --directory skills/writing-adrs python -m unittest discover -s tests -t .
```

Only **CAUGHT** exits 0. Act on the other three rather than reading past them:

- **MISSED** — suspect the test before the check. This is the failure the step finds most
  often: a test that passes whether the check is there or not. Three shipped here before a
  mutation found them, each asserting something trivially true of the correct and the
  broken code alike. Read the assertion again and ask what value it would take under both,
  rather than adding a second test beside the first.
- **INVALID** — the mutated source will not import, so it tested nothing. Pick a mutation
  that still parses: `if False:` in place of a condition, not a deleted line.
- **UNKNOWN** — the suite exited without naming a case, so it was killed, crashed, or ran
  past the 300-second bound. Usually the mutation removed a loop guard or an exit
  condition. Read its output before deciding anything.

Say in the pull request which checks you mutated and what caught each; the run itself
leaves nothing behind. The source is restored from a `finally` and from the signals a
shell sends, but a hard kill cannot be caught from inside the process — after one, check
`git status` and use `git restore <file>`, since the mutation is one anchor replaced once.

**When MISSED is masking rather than a gap.** Masking needs the runner to set the *same*
state the check does, so the child inherits it either way and the effect is unobservable.
In practice that is the two things `run_tests` sets — the address-space cap and the
recursion flag — which confines the exception to checks inside `mutate.py` itself. It is
not a general property of environment variables or resource limits: a module elsewhere
setting one of its own is caught normally. So MISSED means what it says everywhere except
there, and the question to ask is "does the runner set this too?", not "is it
inheritable?". Where it does apply, verify by hand — mutate the check, run its module
directly (`python3 -m unittest scripts.dev.test_mutate`), confirm the named case fails,
then `git restore` — and say so in the pull request, or the next reader takes MISSED for
untested.

## Have someone else read the tests you wrote alongside the code

Where one change writes both a unit of behaviour *and* the tests for it — a new module, or
a function substantial enough to carry its own cases — nobody has read those tests as a
reader, because you wrote both halves against the same mental model and a gap in the model
is invisible from inside it. Dispatch a subagent as a test analyst: give it the subject,
its tests and this file, and ask **what is not covered** — which inputs reach the subject
that no test supplies, and which real-world shapes the fixtures fail to represent. Don't
ask which test would pass with its subject disabled; the mutation step answers that
mechanically. Write the missing tests, and record in the pull request what the pass found,
alongside the mutation results.

The evidence for the rule is the tool above. It arrived mutation-tested and reviewed, and
an analyst still found that every fixture wrote to stdout while `unittest` writes its
whole result block to stderr — so the line joining the two streams was never exercised,
and dropping it would have reported "0 failing tests" for every real run while the suite
stayed green. Mutation testing and this pass catch different things: mutation finds tests
that assert nothing, an analyst finds tests that were never written.
