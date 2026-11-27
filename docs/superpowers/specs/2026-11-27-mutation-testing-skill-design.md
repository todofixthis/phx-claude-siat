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
- **ADR 017 and ADR 023 do not admit what this tool does.** ADR 017 says a shipped tool
  "reports rather than edits". ADR 023 lets one write what it wholly owns, which includes
  text the agent passed to it verbatim. The `--with` value is such text, but the tool
  writes it into a consumer's source file, which the tool does not own, and then restores
  the file. See "A new ADR comes first".
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
kill). Scope it to `skills/mutation-testing/`. Follow `phx:writing-adrs` for how the
new ADR relates to ADR 017 and ADR 023, including whether either gains a
`## Revisit watch` entry. ADR 017's `revisit-when` names another skill shipping tooling,
which this is. Phoenix approves the ADR before implementation starts.

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
- **The tool refuses to run on a Python older than 3.10.** `mutate()` writes the mutated
  file before it defines the restore handler, and that handler's `FrameType | None`
  annotation raises `TypeError` on Python 3.9. The source would stay mutated, which is
  the first anti-goal. The reviewer reasoned this from the code, because the container
  has no Python 3.9 to run. Check the version before anything is written, as
  `MINIMUM_PYTHON` does in `skills/nz-english/scan.py`. Claude's call.
- **CAUGHT requires proof that `unittest` ran.** `RE_FAILING_TEST` matches any line that
  starts with `ERROR: `. The reviewer ran the tool with `-- uv run pytest nonexistent_dir`,
  and it printed CAUGHT and exited 0 on a pytest usage error. That breaks the second
  anti-goal. Report CAUGHT only where the output also carries the `Ran N tests` line
  that `unittest` prints. Otherwise report UNKNOWN. Claude's call.
- **The tool runs the suite once before it mutates anything (proposed, Phoenix to
  confirm).** A suite that already fails reports CAUGHT for a check that no test covers.
  The baseline run uses the same command, timeout, and memory cap. Where it does not
  pass, the tool mutates nothing, says the suite must pass first, and exits non-zero.
  The cost is that every mutation runs the suite twice.
- **The timeout and the memory cap stay fixed.** Both suit the suites in this repository.
  `SKILL.md` states them as limits, and the backlog item records them. Reword the
  comment that justifies the cap as "enough for any suite here".
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
  `uv lock`. Update the comments in those two files that count the tool-shipping skills.
- Add `skills/mutation-testing/` to the `scope` of ADR 031, which lists each workspace
  member by path. Leave its summary and body as written. Claude's call.
- Repoint the `mutate.py` link definitions in ADR 016 and ADR 027. Change no sentence
  in either.
- Add the skill to the README table, with a note on its prerequisites: `python3` 3.10 or
  newer, `git`, a POSIX system, and a `unittest` suite. CI tests the tool on Python 3.12
  only, as it does `scan.py`.
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
2. Control: run headless Claude in the fixture without `--plugin-dir`. First confirm
   that this run has no `phx:mutation-testing` skill. Ask whether the tests cover each
   check. Confirm the answer falls short, for example by reasoning from the test file
   without running a mutation.
3. Run the same prompt with `--plugin-dir` pointing at the working tree. Confirm the
   agent invokes `phx:mutation-testing`, runs the tool, reports CAUGHT for one check and
   MISSED for the other, and leaves `git status` clean.
4. Run the shipped tool against this repository, with the example now in
   `.agents/rules/testing.md`.

Tell the subagent that the uncovered check is intentional, as `AGENTS.md` asks.

## Record what you find

Generalising the tool is deferred work, so it goes in one backlog item,
`docs/backlog/generalise-the-mutation-tool.md`, in the shape `docs/backlog/README.md`
fixes. The item names `skills/mutation-testing/`, and lists each thing that would stop
the tool working on another stack or platform. These are known now:

- the verdicts parse `unittest` output only;
- INVALID relies on the wording `unittest` uses for an import failure;
- the tool is POSIX-only;
- the 300-second timeout is fixed;
- the 2 GiB cap limits address space, not resident memory, so a suite that starts a JVM
  or Node may fail under it.

Add to the item as you build. The pull request description summarises it.

## Left to the builder

- The exact wording of `SKILL.md`, and how much of the `testing.md` prose moves verbatim.
- How the environment variable encodes the command.
- The shape of the fixture projects.
- Whether the tool's docstring keeps its account of why the restore is built as it is.
