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

Where the subject resolves paths, the module docstring states its stance on `chdir`
and what the stance rests on — the two modules here take opposite ones for the same
reason, and ADR 015 is what decides which applies.

Where the subject takes its directories as arguments, pass a fixture and never chdir.
Its defaults are anchored to the module, so an argumentless call rewrites the real file
the subject generates no matter where the test stands; the only test that changes
directory is the one asserting that a `chdir` *cannot* redirect the defaults, and it
asserts the paths rather than calling the subject.

Where the subject reads module-level relative paths instead, chdir into a fixture repo
rather than patching each path, and assert the chdir took, or a positive test can pass
by reading the real repo. Those constants must stay relative for that to work — the
docstring says so, because anchoring one to `__file__` would break it silently.

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
python3 -m scripts.dev.mutate --file scripts/adr/generate_index.py \
    --anchor 'if not target.exists():' --with 'if False:'
```

Add `--occurrence N` where the anchor appears more than once; without it the first is
mutated and the run says so. The source is restored in a `finally` and on the signals a
shell sends, so an interrupted run cannot leave a deliberately broken check in a tree you
are about to commit. It exits 0 only on **CAUGHT**, so a sequence can be scripted rather
than read by eye — **MISSED**, **INVALID** (the mutation broke the import, proving
nothing) and **UNKNOWN** (the suite died without naming a case) all exit 1. This is a
step you run, not an artefact you leave behind, so say in the pull request which checks
you mutated and what caught each.

A check nothing can catch is untested however many tests surround it — but the failure
this finds most often is the other one: **a test that passes whether the check is there
or not**. Three shipped in this repo before a mutation found them, each asserting
something trivially true of the correct and the broken code alike. So when a mutation is
MISSED, suspect the test before the check: read the assertion again and ask what value it
would take under both, rather than adding a second test beside the first.

## Have someone else read the tests you wrote alongside the code

Where one change adds a module *and* the tests for it, nobody has read those tests as a
reader — you wrote both halves against the same mental model, so a gap in the model is
invisible from inside it. Dispatch a subagent as a test analyst: give it the subject, its
tests and this file, and ask what is **not** covered and which existing test would pass
with its subject's logic disabled.

The evidence for the rule is the tool above. It arrived mutation-tested and reviewed, and
an analyst still found that every fixture wrote to stdout while `unittest` writes its
whole result block to stderr — so the line joining the two streams was never exercised,
and dropping it would have reported "0 failing tests" for every real run while the suite
stayed green. Mutation testing and this pass catch different things: mutation finds tests
that assert nothing, an analyst finds tests that were never written.
