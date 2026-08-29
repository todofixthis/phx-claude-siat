# testing.md's second anchor test is wrong for a skill, and the rule does not say so

> Recorded 2026-08-29, from the departure taken while writing `nz-english`'s suite.
> Never filed as a GitHub issue.

## What

[`testing.md`][], under "Say what the module does about the working directory", requires two
tests of a module's own anchor:

> - a `chdir` into a temp directory, asserting the anchor is absolute and does not fall
>   inside it — that a moved cwd *cannot* redirect it;
> - no `chdir` at all, asserting the anchor reaches this repository (`__file__` is relative
>   to it, and a file the subject expects is really there). This is the one that catches
>   `parents[1]` for `parents[2]`, which the first test passes happily.

The second is wrong for anything under `skills/`. A skill is served from a plugin cache with
the repository nowhere near it — that being the whole reason [`scan.py`][] anchors on
`__file__` and carries an own-directory guard. A test asserting the anchor reaches this
repository would pass in a checkout and fail in the shape every consumer gets.

## The answer already exists; only the rule is missing it

`nz-english` did not drop the second test. It replaced it, in [`test_scan.py`][]:

```python
def test_the_anchor_holds_the_bundled_files(self):
    """The anchor must name the directory the fixtures and the table actually live in."""
    anchor = Path(scan.__file__).resolve().parent
    self.assertTrue((anchor / "table.py").is_file())
    self.assertTrue((anchor / "tests" / "fixtures" / "us").is_dir())
```

That keeps what the rule's second test is for — catching `parents[1]` written for
`parents[2]`, which the first test passes happily — by asserting the anchor names files the
skill itself ships. True in a checkout and in a plugin cache alike.

So the work is not design. It is lifting a pattern that already runs green into the rule,
and correcting two places that understate it: the rule, which states its requirement
unconditionally, and `test_scan.py`'s own module docstring, which says "Only the first of
the two anchor tests that rule asks for is written here" when the second was in fact
replaced.

## Why it is still worth doing

The departure note serves anyone reading `test_scan.py`. It does not serve the next person
writing a *new* skill's tests: they read `testing.md`, find the requirement stated with no
condition on it, and either write a test that is wrong in the deployed shape or re-derive
the same exception alone.

The rule's own history points the same way. It was written for `scripts/`-anchored modules
under ADR 016, whose scope is `[.agents/rules/testing.md, scripts/]` — the rule file itself,
but not the code its glob now claims.

## Acceptance

- `testing.md` states the condition in prose rather than in a bullet, its behaviour flipping
  on where the module ships, and gives the ships-with-the-module form as what a skill writes
  instead of the reaches-this-repository one.
- `test_scan.py`'s module docstring stops saying the second test is absent, and cites the
  rule rather than restating the reasoning.

[`scan.py`]: ../../skills/nz-english/scan.py
[`test_scan.py`]: ../../skills/nz-english/tests/test_scan.py
[`testing.md`]: ../../.agents/rules/testing.md
