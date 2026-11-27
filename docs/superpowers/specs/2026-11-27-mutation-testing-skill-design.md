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
- **ADR 017 and ADR 023 did not admit what this tool does, so ADR 036 does.** ADR 017 says a shipped tool
  "reports rather than edits". ADR 023 lets one write what it wholly owns, which includes
  text the agent passed to it verbatim. The `--with` value is such text, but the tool
  writes it into a consumer's source file, which the tool does not own, and then restores
  the file. See "ADR 036 comes first".
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

## ADR 036 comes first

ADR 036 records the decision that lets this tool ship. It supersedes ADR 023, restates
ADR 023's four kinds of write, and admits a fifth: an edit to a consumer's file that the
agent specified verbatim and the tool reverses before it exits. It was superseded, not
amended, because ADR 023 says "never" and `phx:writing-adrs` treats a contradiction of
such a claim as a partial supersession. Phoenix approves ADR 036 before implementation
starts.

ADR 036 sets conditions that the tool in `scripts/dev/` does not meet. Each is new work,
listed under "Changes to the tool".

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
- passing the narrowest test command that covers the check, usually one test module,
  because the tool runs the command twice;
- re-running with the whole suite after a MISSED from a narrow command, because that
  MISSED says only that the narrow command does not cover the check. CAUGHT needs no
  second run;
- what to do on each verdict, moved from `.agents/rules/testing.md`;
- recovery after a hard kill, by asking the tool to put the file back from its copy, and
  not with `git restore` or by moving the copy into place;
- giving the command more time than two runs of the suite can take, because a harness
  that stops a long command may send a signal the tool cannot catch. The tool's own
  bound is 300 seconds for each run;
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
- **The tool runs the command once before it mutates anything.** A suite that already
  fails reports CAUGHT for a check that no test covers. The baseline run uses the same
  command, timeout, and memory cap. Where it does not pass, the tool mutates nothing,
  says the suite must pass first, and exits non-zero. Phoenix agreed to this. Every
  mutation therefore runs the command twice, and a narrow command keeps both runs
  short (see "The skill"). On this container, the whole `writing-adrs` suite ran in
  about 6 seconds and one of its test modules in about 0.1 seconds.
- **The tool saves a copy of the original bytes before it edits.** ADR 036 requires it.
  The copy goes in a file outside the consumer's tree. The tool prints where the copy is
  before it writes the mutation, and deletes the copy only after the restore succeeds. A
  kill the tool cannot catch leaves the copy behind. A run on a file that already has a
  copy mutates nothing and prints how to put the original back. That refusal also stops
  a second run from reading mutated bytes as the original. The mutation runs before the
  new check is committed, so `git restore` would discard an unstaged check as well.
  Where the copy lives and how a run finds it are the builder's call.
- **The tool can restore from the moment it writes.** Today `mutate()` writes the
  mutated file and then installs the signal handlers, so a signal between the two leaves
  the file mutated. Install the handlers and open the `try` before the write.
- **A test covers the restore on `SIGTERM` and `SIGHUP`.** No test sends either signal
  today, and ADR 036 rests on those handlers.
- **A caught signal stops the suite as well.** The suite runs in its own session, so
  when a handler restores the file and the tool exits, the suite carries on with the
  mutated code loaded and with no timeout over it. Kill the suite's process group in the
  handler, before the restore.
- **The copy survives a restart, and the tool does the recovery.** ADR 036 requires both.
  The tool gains a command that puts a file back from its copy, with the same bytecode
  handling as the restore at exit, and a way to discard a copy that is no longer wanted.
  The refusal names both, and says how to tell whether the file still holds the
  mutation. The ADR's reviewer moved a copy into place by hand, and the next run
  executed the mutated bytecode, so no document tells the agent to do that. The tool
  deletes the copy last, after the bytecode is dealt with. The flag names are the
  builder's call.
- **No bytecode from the mutated source stays valid.** CPython accepts a cached `.pyc`
  where the source has the same size and the same modification time in whole seconds.
  The ADR's reviewer reproduced the fault on Python 3.13: a same-length mutation,
  restored within one second, left the mutated bytecode in `__pycache__`, and the next
  run executed it. A narrow command makes that timing likely. The tool must make sure
  that the mutated run compiles the mutated source and that every later run compiles
  the original. One way is to control the file's modification time: give the mutated
  file a time whose whole second differs from the original's, and restore the original
  time with the bytes. That suits CPython and is wrong for a build cache that compares
  times, which is one more reason the fix stays specific to this stack. The mechanism is
  the builder's call. `SKILL.md` names bytecode as the one cache the tool handles, as
  ADR 036 requires. An end-to-end test proves
  it: a same-length mutation, a suite that runs in well under a second, then a second
  run of the suite that must pass.
- **The timeout and the memory cap stay fixed.** Both suit the suites in this repository.
  `SKILL.md` states them as limits, and the backlog item records them. Reword the
  comment that justifies the cap as "enough for any suite here".
- **Docstrings and comments** drop the ADR numbers and the `scripts.dev` invocation, and
  describe the tool as a consumer meets it.

### Changes to this repository

- Delete `scripts/dev/`.
- The by-hand mutation that `.agents/rules/testing.md` keeps for the masking exception
  stops prescribing `git restore`. It says to undo the one edit instead.
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
- Repoint the `mutate.py` link definitions in ADR 016, ADR 027, and ADR 036. Change no
  sentence in any of them.
- Add a `## Revisit watch` entry to ADR 017 once the coupling test exists. Its trigger
  names another skill shipping tooling. Say what the new test couples and whether the
  per-skill tests now share a shape worth generalising.
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
  or Node may fail under it;
- the bytecode fix is specific to CPython. Another stack has its own build cache;
- one mutation of a file can run at a time, and the restore overwrites anything else
  written to the file during the run;
- each invocation runs its own baseline. A batch mode that takes several mutations and
  runs one baseline would cut the runs from 2N to N+1 where a suite is slow.

One finding is about this repository, not the tool. `python -m unittest discover -s tests
-t .` fails in `skills/creative-commits` before any test runs, because its `tests/` has
no `__init__.py`. Decide during the build whether to fix that here or record it.

Add to the item as you build. The pull request description summarises it.

## Left to the builder

- The exact wording of `SKILL.md`, and how much of the `testing.md` prose moves verbatim.
- How the environment variable encodes the command.
- The shape of the fixture projects.
- Whether the tool's docstring keeps its account of why the restore is built as it is.
