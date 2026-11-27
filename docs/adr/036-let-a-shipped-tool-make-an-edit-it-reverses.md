---
status: Accepted
date: 2026-11-27
scope: [.agents/skills/, scripts/frontmatter.py, skills/]
summary: A tool shipped with a skill may write what it wholly owns — a generated index, a field with one right value given the command, a filename or heading number, its own fixed template, and text the agent passed to it verbatim — and may make an edit to a consumer's file that the agent specified verbatim and the tool reverses byte for byte before it exits, keeping a copy of the original until it has; it never leaves a sentence the agent wrote rewritten, and the repository reaches the ADR frontmatter parser through a symlink into the skill rather than a copy.
revisit-when: A shipped tool needs to leave a sentence the agent wrote rewritten after it exits; a run leaves a consumer's file changed with no copy to restore it from; or validate_manifests.py stops needing the parser.
---

# 036: Let a shipped tool make an edit it reverses

## Context

[ADR 017][] required code shipped with a skill to report rather than edit. [ADR 023][]
narrowed that clause to four kinds of write a tool wholly owns, and kept one prohibition:
a shipped tool never rewrites a sentence the agent wrote. Its `revisit-when` named the
condition that would reopen it: "A shipped tool needs to rewrite a sentence the agent
wrote".

[`mutate.py`][] met that condition. It is the mutation tool
[`.agents/rules/testing.md`][] requires after adding a check. The agent names a file, the
exact text of one check, and a replacement. The tool replaces that text in the file, runs
a test command, writes the original bytes back, and reports whether a test failed. It
lived in `scripts/dev/`, outside the paths ADR 017 and ADR 023 bind. Shipping it as the
`mutation-testing` skill moves it under both.

The replacement is "a value the agent passed on the command line, written verbatim",
which is ADR 023's fourth kind. The file is not the tool's. It is a consumer's source
file, and the text replaced is a line somebody wrote. Read literally, ADR 023 forbids the
tool.

The same steps by hand are an edit, a test run, and a restore. The restore is the step
that fails: a mutated file left behind is the input to whatever runs next, and that is
usually a commit. `mutate.py` restores from a `finally` and from handlers for `SIGTERM`
and `SIGHUP`. It cannot restore after a kill that it cannot catch, such as `SIGKILL`.
The mutation runs before the new check is committed, so `git restore` after such a kill
also discards the uncommitted check.

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
- The tool writes the original bytes back before it exits, on every exit it can catch: a
  return, an exception, an interrupt, and the termination signals a shell or a timeout
  sends.
- The tool keeps a copy of the original bytes outside the consumer's tree until that
  write succeeds, and says where the copy is.
- The tool writes nothing else in the consumer's tree.

**Pros:** The agent's judgement stays where it was, in choosing the check and the
replacement. The edit a consumer can lose work to is made by code with tests, not typed.
**Cons:** A shipped tool now writes to a file it does not own. For the length of one test
run, the working tree holds a change nobody asked to keep.
**Risks:** A kill the tool cannot catch leaves the file mutated. A later tool cites this
kind for an edit it only mostly reverses.

### Option 3: Mutate a copy of the tree

Copy the consumer's tree to a temporary directory, mutate the copy, and run the test
command there. The tool never touches the consumer's file.

**Pros:** ADR 023 stands as written. No kill can leave the consumer's file mutated.
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

Option 3 removes the risk Option 2 only bounds, and it lost on what the copy costs. How
much of a tree a suite needs differs by stack, and the mutation tool had only ever run by
editing in place. The copy of the original bytes answers the same risk for one file. The
revisit condition names the case where that answer fails.

This ADR supersedes ADR 023 rather than sitting beside it. ADR 023 said "never", and a
second decision in force that says "except" would leave a reader of either with half the
rule. ADR 023's four kinds carry forward unchanged:

- A file generated from other files, such as the index.
- A field with one right value given the command: `status`, `superseded-by`,
  `revisit-discharged-by`, a filename, a heading number, or a reference-link target that
  names a renumbered file.
- The skill's own fixed template.
- A value the agent passed on the command line, written verbatim.

Striking through a spent condition, moving the `(Accepted)` marker, and writing citations
stay with the agent. The repository still reaches the ADR frontmatter parser through the
symlink `scripts/frontmatter.py`, for the reasons ADR 023 gave.

## Consequences

- ADR 023 is `Superseded` by this ADR. ADR 017 gains a Consequences bullet that points
  here, and its other two clauses stand as written.
- Citations of ADR 023 in ADR 022, ADR 034, ADR 035, and one backlog item resolve through
  its `superseded-by`. None of them concerns the rule this ADR changes.
- The mutation tool gains the copy of the original bytes when it moves into the skill.
  `mutate.py` kept none while it lived in `scripts/dev/`.
- The tool's tests must cover the restore on each exit the tool can catch. When this ADR
  was written, no test sent `SIGTERM` or `SIGHUP`, so the move adds one.
- The skill tells the agent how to recover after a kill the tool cannot catch, from the
  copy and not with `git restore`.
- A harness that stops a long command may send a signal the tool cannot catch. The skill
  therefore tells the agent to give the command more time than two runs of the suite can
  take.
- A later tool that claims this kind documents the edit it makes and tests the restore,
  as every subcommand of the ADR tool documents its write set.

[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[`.agents/rules/testing.md`]: ../../.agents/rules/testing.md
[`mutate.py`]: ../../scripts/dev/mutate.py
