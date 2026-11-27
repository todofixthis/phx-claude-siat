# Ship the mutation tool as `phx:mutation-testing`

Scaffolding for one implementation. Delete this file on the branch before the pull
request is created.

## Intent

`scripts/dev/mutate.py` disables one check in place, runs a test suite, restores the
file, and reports whether a test caught the change. It has only ever run in this
repository. Phoenix wants to use it on other projects, so it ships with the plugin as a
published skill.

This first version assumes the stack this repository uses: Python, and a suite run with
`python -m unittest`. Making the tool work with other runners and platforms is a later
piece of work. Building this version is also how we find the stack-specific problems
that later work has to solve, so record each one you meet (see "Record what you find").

## Goals

- A consumer with the plugin installed can invoke `phx:mutation-testing`, run the tool
  with no install step, and act on its verdict.
- This repository uses the shipped tool and keeps no copy of its own.
- Automated tests and end-to-end tests prove both the tool and the skill.

## Non-goals

- Test runners other than `unittest`, including pytest.
- Windows. The tool imports `resource` and uses `preexec_fn`, which are POSIX-only.
- Generating mutations. The agent still chooses the anchor and the replacement.
- The "have someone else read the tests" analyst pass. It stays in
  `.agents/rules/testing.md`.

## Anti-goals

The work has failed, even if every test passes, where any of these is true:

- A run leaves a source file mutated after an exit the tool can catch.
- The tool prints CAUGHT, or exits 0, without naming a failing test.
- The skill lets an agent read MISSED, INVALID, or UNKNOWN as a pass.

## Constraints

- **ADR 003.** The skill finds `mutate.py` relative to its own directory.
- **ADR 005, ADR 006, and ADR 031.** The skill ships a `pyproject.toml`, so it becomes a
  uv workspace member, and `pr.yml` gains matching ruff, black, and pytest checks in the
  same change. `validate_manifests.py` fails the build otherwise.
- **ADR 017.** The tool needs no install step, and a test fails when `SKILL.md` and the
  code drift apart.
- **ADR 017 and ADR 023 forbid what this tool does.** ADR 017 says a shipped tool
  "reports rather than edits". ADR 023 lets one write only what it wholly owns. The
  mutation tool rewrites a consumer's source file, then restores it. See "A new ADR
  comes first".
- **ADR 027.** The target file comes from `--file`, and the test command runs in the
  working directory. Neither changes.
- **ADR 014.** Comments under `skills/` ship to users who have no `docs/adr/`. Name the
  constraint in them, not the ADR number.

## Approaches

**A. Move the tool, and this repository uses the shipped one (chosen).** One copy
exists, and this repository keeps testing what users get. Commit `327f760` did the same
for the ADR tool. The cost is that every reference to `scripts/dev/` moves.

**B. Move the tool, and leave a symlink at `scripts/dev/mutate.py`.** Existing commands
keep working. `scripts/frontmatter.py` is a symlink because `validate_manifests.py`
imports the parser. Nothing imports `mutate.py`, so a symlink here gives two ways to
run one tool and nothing else.

**C. Ship a copy.** The two copies drift. Rejected.

Phoenix chose A.

## A new ADR comes first

Before any code moves, record a decision with `phx:writing-adrs`. The proposal is to
admit one more class of write for a shipped tool: an edit the agent specified verbatim,
which the tool reverses before it exits. The ADR must say what makes that safe (the
byte-exact restore, the `finally`, the signal handlers) and what it cannot cover (a hard
kill). Scope it to `skills/mutation-testing/`. Phoenix approves the ADR before
implementation starts.

## Design

### The skill

`skills/mutation-testing/` holds `SKILL.md`, `mutate.py`, `pyproject.toml`, and
`tests/test_mutate.py`. Model `pyproject.toml` on `skills/nz-english/pyproject.toml`.
The tool stays standard library only.

`SKILL.md` is written for an agent. It covers:

- when to use the skill: after adding a check to code under test, before committing;
- the command, as `python3 ${CLAUDE_SKILL_DIR}/mutate.py --file … --anchor … --with …
  -- <test command>`;
- how to pick a mutation that still parses, such as `if False:` in place of a condition;
- what to do on each verdict, moved from `.agents/rules/testing.md`;
- recovery after a hard kill, with `git status` and `git restore`;
- the limits: unittest output only, POSIX only. With any other runner, the agent says so
  and stops, because a real catch would report UNKNOWN;
- reporting which checks were mutated and what caught each.

The skill's `description` is a "Use when…" trigger in the style of the other skills.

### Changes to the tool

Everything not listed here moves unchanged.

- **The test command becomes required.** `DEFAULT_TEST_COMMAND` is this repository's
  suite and goes. A run with no command after `--` is a usage error with a message that
  shows the form expected.
- **The recursion guard gets a new condition.** Today it refuses the default command
  when `MUTATE_IN_PROGRESS` is set. With no default, the variable carries the command
  of the run in progress, and a nested run refuses a command identical to it. A
  different command still runs, which the tool's own tests rely on. This is Claude's
  call, not Phoenix's.
- **Docstrings and comments** drop the ADR numbers and the `scripts.dev` invocation, and
  describe the tool as a consumer meets it.

### Changes to this repository

- Delete `scripts/dev/`.
- `.agents/rules/testing.md` keeps the rule "mutation-test each check you add" and
  points at the shipped tool, run here as `uv run python skills/mutation-testing/mutate.py`.
  It keeps the masking exception, which applies only to checks inside `mutate.py`, and
  the analyst pass. The verdict guidance moves to `SKILL.md`, so `testing.md` links to
  it and does not repeat it.
- Add `skills/mutation-testing` to the workspace members in the root `pyproject.toml`,
  to the `python` matrix in `pr.yml`, and to the path filter above the matrix. Run
  `uv lock`.
- Repoint the `mutate.py` link definitions in ADR 016 and ADR 027. Change no sentence
  in either.
- Add the skill to the README table, with a note on its prerequisites: `python3` 3.12 or
  newer, `git`, a POSIX system, and a `unittest` suite.
- Leave `CHANGELOG.md` alone. The release generates it (ADR 002).

## Testing

**Unit tests.** `test_mutate.py` moves with the tool and imports it as `mutate`. Rewrite
the cases that cover the default command and the recursion guard for the new behaviour.
Add the coupling test ADR 017 requires: `SKILL.md` names every verdict the tool can
print and the timeout the tool applies. Mutation-test each new or changed check with the
tool itself, as `.agents/rules/testing.md` requires.

**End-to-end test of the tool.** Add an automated test that builds a small project in a
temporary directory, with a real `unittest` suite, and runs `mutate.py` as a subprocess
with a real `python -m unittest` command. It asserts the verdict line, the exit code,
and that the source file is byte-identical afterwards, for at least one CAUGHT and one
MISSED mutation. The existing tests use stand-in commands, so nothing yet runs the tool
against real `unittest` output from start to finish.

**End-to-end test of the skill.** This one is manual, costs money, and does not run in
CI. Claude Code is installed in the cloud container, and `claude --plugin-dir ./ -p …`
loads skills from the working tree. A probe on 2026-11-27 confirmed that, at about
US$0.32 for a three-turn run.

1. Build a fixture project in a scratchpad directory: a module with one check a test
   covers and one check no test covers, in a Git repository.
2. Control: run headless Claude in the fixture with the cached plugin, which lacks the
   skill. Ask whether the tests cover each check. Confirm the answer falls short, for
   example by reasoning from the test file without running a mutation.
3. Run the same prompt with `--plugin-dir` pointing at the working tree. Confirm the
   agent invokes `phx:mutation-testing`, runs the tool, reports CAUGHT for one check and
   MISSED for the other, and leaves `git status` clean.
4. Run the shipped tool against this repository, with the example now in
   `.agents/rules/testing.md`.

Tell the subagent that the uncovered check is intentional, as `AGENTS.md` asks.

## Record what you find

Keep a list, in the pull request description, of each thing that would stop the tool
working on another stack or platform. Three are known now: the verdicts parse `unittest`
output only, the tool is POSIX-only, and INVALID relies on the wording `unittest` uses
for an import failure. The list is the input to the later work on generalising the tool.

## Left to the builder

- The exact wording of `SKILL.md`, and how much of the `testing.md` prose moves verbatim.
- How the environment variable encodes the command.
- The shape of the fixture projects.
- Whether the tool's docstring keeps its account of why the restore is built as it is.
