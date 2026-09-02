# creative-commits: the test suite does not follow the repo's testing conventions

> Recorded 2026-08-29, noticed while writing `nz-english`'s suite under the same rules.
> Never filed as a GitHub issue.

## What

[`testing.md`][] declares `paths: ["**/test_*.py", "**/*_test.py"]`, which claims
[`test_seed.py`][]. That file predates the conventions and does not follow them.

The divergence is not really class structure. `test_seed.py` is pytest-native — six
functions taking `capsys`, plus `pytest.raises` — while `testing.md` is written wholly in
`unittest` idiom, and every `scripts/` suite says so outright. **`testing.md` never states
which it means**, and that is the decision this item has to make first, because pytest
refuses to inject a fixture into a `unittest.TestCase` method: adopting the rule's class
scheme means either giving up `capsys` for manual stdout capture, or using bare pytest
classes that satisfy the naming but not the idiom.

## Audited rule by rule

All nine sections of `testing.md`, read against the file:

- **Name each class for its subject, and say which layer it is** — breached. No classes at
  all, and no module docstring naming subject or layer. `skills/nz-english/tests/` carries
  22 classes under the same rule, so two suites in one plugin read as though written to
  different standards.
- **Assert the output a human reads** — breached, and this is the one worth fixing whatever
  is decided about classes. `test_git_nonzero_exit` and `test_git_subprocess_raises` assert
  only `capsys.readouterr().err != ""`, which passes for any message at all, while
  [`seed.py`][] prints two distinct and specific ones — `Failed to run git: …` and `git log
  failed: …`. Neither test would notice the wrong one.
- **Every test function carries a docstring naming the scenario** — satisfied, and they are
  good: each names the input and the expected shape.
- **Put a case in the layer that owns it** — no breach is possible. `seed.py` exposes only
  `main() -> None`, so every test is entry-point level by construction.
- **One reason to fail per test** — satisfied.
- **Guard against a partial pass** — satisfied. `test_normal_case` uses two emoji, and every
  test asserts the whole stdout string rather than a substring.
- **Say what the module does about the working directory** — does not apply. The rule opens
  "Where the subject takes paths at all", and `seed.py` touches no path. Do not add an
  anchor stance to satisfy a rule that never fired.
- **Mutation-test each check you add** and **Have someone else read the tests you wrote
  alongside the code** — process rules binding a change, not properties an existing file can
  breach.

## Why it is still worth doing

The stderr assertions are a real hole: the suite would stay green if `seed.py` printed the
wrong message, or the same message for both failures.

The rest costs the conventions their authority. An agent that reads `testing.md` and then
opens the nearest existing suite to pattern-match finds one that contradicts it, with no
note saying why — which is how a rule quietly stops being followed.

## Acceptance

- `testing.md` says whether a skill's suite is `unittest` or pytest, since the rule's class
  scheme and `capsys` cannot both hold.
- The two stderr tests assert the message `seed.py` actually prints, not merely that
  something was printed.
- `test_seed.py` opens with a module docstring naming subject and layer, and its cases sit
  in classes named per whichever idiom the first bullet settles.
- The suite still passes under `uv run pytest` from `skills/creative-commits/`, which is
  what `pr.yml`'s `python` job and the release gate run.
- No working-directory stance is added, the subject taking no paths.

[`seed.py`]: ../../skills/creative-commits/seed.py
[`test_seed.py`]: ../../skills/creative-commits/tests/test_seed.py
[`testing.md`]: ../../.agents/rules/testing.md
