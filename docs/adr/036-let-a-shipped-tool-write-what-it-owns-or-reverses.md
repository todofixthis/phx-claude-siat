---
status: Accepted
date: 2026-11-27
scope: [.agents/skills/, hooks/, scripts/frontmatter.py, skills/]
summary: A tool shipped with a skill may write what it wholly owns — a generated index, a field with one right value given the command, a filename or heading number, its own fixed template, and text the agent passed to it verbatim — and may make one edit to a consumer's file that the agent specified verbatim, provided it first saves the original outside the consumer's tree, writes nothing else there, and puts the file back byte for byte before it exits; it never leaves any other text in a consumer's file changed, and the repository reaches the ADR frontmatter parser through a symlink into the skill, not a copy or an import by path.
revisit-when: A shipped tool needs to leave text it does not own changed after it exits; a file a shipped tool edited and should have put back reaches a commit or a later command still changed; a shipped tool needs to make such edits concurrently or several in one run; another tool claims the reversed edit; or nothing under scripts/ imports the frontmatter parser any longer.
---

# 036: Let a shipped tool write what it owns, or what it reverses

## Context

[ADR 017][] required code shipped with a skill to report rather than edit. [ADR 023][]
narrowed that clause to four kinds of write a tool wholly owns, and kept one prohibition:
a shipped tool never rewrites a sentence the agent wrote. Its `revisit-when` named the
condition that would reopen it: "A shipped tool needs to rewrite a sentence the agent
wrote".

[`mutate.py`][] met that condition. It is the mutation tool
[`.agents/rules/testing.md`][] requires after adding a check. The agent names a file, the
exact text of one check, and a replacement. The tool replaces that text in the file, runs
a test command, writes the original bytes back, and reports whether a test failed. When
this ADR was written it lived in `scripts/dev/`, outside the paths ADR 017 and ADR 023
bind. Shipping it as a `mutation-testing` skill would move it under both.

The replacement is "A value the agent passed on the command line, written verbatim",
which is ADR 023's fourth kind. The file is not the tool's. It is a consumer's source
file, and the text replaced is a line somebody wrote. ADR 023 argued its prohibition from
prose, and its reasoning applies to any text a tool does not own. Read that way, ADR 023
forbids the tool.

The same steps by hand are an edit, a test run, and a restore. The restore is the step
that fails: a mutated file left behind is the input to whatever runs next, and that is
usually a commit. `mutate.py` restored from a `finally` and from handlers for `SIGTERM`
and `SIGHUP`, with three gaps:

- It could not restore after a kill it cannot catch, such as `SIGKILL`. Its documentation
  prescribed `git restore`, which also discards the check under test where that check is
  unstaged, as it is when the mutation runs before the commit.
- It wrote the mutated file before it installed the handlers, so a signal between the two
  left the file mutated.
- Putting the bytes back did not put the tree back. CPython accepts a cached bytecode
  file where the source has the same size and the same modification time in whole
  seconds. A same-length mutation restored within one second left the mutated bytecode
  valid, and the next run executed it. A review of this ADR reproduced that on Python
  3.13.

## Options

### Option 1: Do nothing

Keep ADR 023 as written. The mutation tool stays in `scripts/dev/` and does not ship, or
ships as a reporter that prints the steps for the agent to carry out.

**Pros:** One rule covers every shipped tool, and no shipped tool writes to a consumer's
file.
**Cons:** A consumer's agent makes the edit and the restore by hand, which is the failure
the tool was written to remove.
**Risks:** An agent forgets the restore, or restores with `git restore` and loses
uncommitted work.

### Option 2: Admit an edit the tool reverses (Accepted)

A fifth kind of write joins ADR 023's four. A shipped tool may edit a consumer's file
where all of these hold:

- The agent passes the file, the text to replace, and the replacement, and the tool
  writes the replacement verbatim. The text to replace must match exactly once, and the
  tool refuses where it does not.
- Before the edit, the tool saves the original bytes to a copy outside the consumer's
  tree and says where the copy is. The tool refuses to edit a file that already has a
  copy, and says how to put the original back.
- The tool can put the file back from the moment the edit is written. It does so before
  it exits, on every exit it can catch: a return, an exception, an interrupt, and the
  termination signals a shell or a timeout sends. It deletes the copy only after that
  write succeeds.
- The tool writes nothing else in the consumer's tree, and nothing that a command it ran
  derived from the edited bytes stays valid after the file is put back.

**Pros:** The agent's judgement stays where it was, in choosing the check and the
replacement. The edit a consumer can lose work to is made by code with tests, not typed.
**Cons:** A shipped tool writes to a file it does not own. For the length of one test
run, the working tree holds a change nobody asked to keep. Only one such edit to a file
can be in progress, and putting the file back overwrites anything an editor, a formatter,
or another agent wrote to it during the run.
**Risks:** A kill the tool cannot catch leaves the file edited until somebody notices. A
later tool cites this kind for an edit it only mostly reverses.

### Option 3: Mutate a copy of the tree

Copy the consumer's tree to a temporary directory, mutate the copy, and run the test
command there. The tool never touches the consumer's file.

**Pros:** ADR 023 stands as written. No kill can leave the consumer's file mutated, and
runs do not block each other.
**Cons:** The check under test is uncommitted, so a `git worktree` would not hold it, and
the copy must take the working tree as it stands. A suite also needs what Git ignores,
such as a virtual environment or installed packages, and the tool must either copy that
or rebuild it on every run. A test command that names an absolute path runs against the
original.
**Risks:** A copy that differs from the tree reports a verdict about code the consumer
does not have.

## Decision

Option 2. ADR 023 drew its line "at the sentence the agent wrote, because that is where a
single right answer stops". A reversed edit leaves one right answer behind, the bytes the
file held before, and the tool holds them. What ADR 023 protected was the content of a
consumer's file after the tool exits, and that protection stands.

Option 3 removes the risk that Option 2 only bounds. It lost on scope: the skill's first
version runs one mutation on one file at a time, for Python with `unittest`, and at that
size the copy of a tree buys nothing the copy of one file does not. The copy of the file
makes an edit that outlives the tool recoverable. It does not stop the edited file being
committed first, and noticing depends on the agent seeing the kill or on a later run on
the same file. The revisit conditions name the arrivals that would move this decision to
Option 3.

This ADR supersedes ADR 023 rather than sitting beside it. ADR 023 said "never", and a
second decision in force that says "except" would leave a reader of either with half the
rule. "A sentence the agent wrote" is read here as any text in a consumer's file that the
tool did not generate. ADR 023's four kinds carry forward unchanged:

- A file generated from other files, such as the index.
- A field with one right value given the command: `status`, `superseded-by`,
  `revisit-discharged-by`, a filename, a heading number, or a reference-link target that
  names a renumbered file.
- The skill's own fixed template.
- A value the agent passed on the command line, written verbatim.

Striking through a spent condition, moving the `(Accepted)` marker, and writing citations
stay with the agent. So do ADR 023's rules for the tools it covered:

- Every subcommand of a shipped tool documents its write set, and the skill's tests
  assert that a subcommand documented as writing nothing writes nothing.
- The ADR tool regenerates the index behind the agent only after the agent's own edit
  under `docs/adr/`, or from a command the agent ran. A hook that checks after a shell
  command reports and does not write.
- The repository reaches the ADR frontmatter parser through the symlink
  `scripts/frontmatter.py`. A copy in each place, held identical by a test, brings back
  the duplication that [ADR 011][] retired. An import across the boundary by path makes a
  script's imports depend on how it was invoked, and feeds the shipped tree from the
  unshipped one. The `scope` names the symlink because replacing it with a file is the
  breach.

Two assumptions sit under the fifth kind. The tool is the only writer of the file for the
length of the run. And the tool runs on a POSIX system, where the signals named above
exist.

## Consequences

- ADR 023 is `Superseded` by this ADR. ADR 017 gains a Consequences bullet that points
  here, and its other two clauses stand as written.
- Citations of ADR 023 in ADR 022, ADR 034, ADR 035, and one backlog item resolve through
  its `superseded-by`. None of them concerns the rule this ADR changes.
- The mutation tool changes when it moves into the skill, because the tool in
  `scripts/dev/` does not meet the conditions. It saves the copy before the edit, refuses
  a file that already has one, installs its handlers before it writes, and leaves no
  valid bytecode from the mutated source.
- The tool's tests must cover each of those, and the restore on each exit the tool can
  catch. When this ADR was written, no test sent `SIGTERM` or `SIGHUP`.
- The skill and `.agents/rules/testing.md` tell the agent to recover after a kill the
  tool cannot catch from the copy, and not with `git restore`.
- Which signal a harness sends when it stops a long command was not established. One
  observation in Claude Code on 2026-11-27 saw `SIGTERM` on an explicit stop, which the
  tool catches. The skill tells the agent to give the command more time than the tool's
  own bounds allow, so that the tool's timeout fires first.
- A later tool that claims the fifth kind fires this ADR's revisit condition, and the
  ADR that answers it says whether the conditions above fit a second case.

[ADR 011]: 011-make-scripts-a-package.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[`.agents/rules/testing.md`]: ../../.agents/rules/testing.md
[`mutate.py`]: ../../scripts/dev/mutate.py
