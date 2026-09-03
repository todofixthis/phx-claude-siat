---
status: Accepted
date: 2026-09-02
scope: [.agents/skills/, scripts/frontmatter.py, skills/]
summary: A tool shipped with a skill may write what it wholly owns — a generated index, a field with one right value given the command, a filename or heading number, its own fixed template, and text the agent passed to it verbatim — and never rewrite a sentence the agent wrote; the repository reaches the ADR frontmatter parser through a symlink into the skill rather than a copy.
revisit-when: A shipped tool needs to rewrite a sentence the agent wrote, or validate_manifests.py stops needing the parser.
---

# 023: Let a shipped tool write what it wholly owns

## Context

[ADR 017][] made three demands of code shipped with a skill: no install step, "reports
rather than edits", and a test that fails when prose and code drift. The second was argued
from `nz-english`, whose only edit is a rename, "the thing the skill says kills you".

[ADR 022][] ships a tool that must write. It generates `INDEX.md`, which
[`generate_index.py`][] has always written; it scaffolds an ADR from the skill's template;
and the deterministic halves of the skill's workflows — set `status: Superseded` and
`superseded-by`, set `revisit-discharged-by`, renumber a file with its heading and every
peer field naming the old number — are the edits the skill has to warn against by hand
(`13`, "never `013`", twice over). Read literally, 017 forbids all of it.

The tool also needs the frontmatter parser, which [ADR 011][] put in [`frontmatter.py`][]
so `scripts/adr` and `scripts/ci` would stop keeping adapted copies. A skill resolves its
bundled files relative to its own directory ([ADR 003][]), so the parser must sit inside
the skill, and `validate_manifests.py` still needs it from `scripts/`.

## Options

### Option 1: Do nothing

Keep 017's clause as written: the tool reports, the agent edits.

**Pros:** One rule for every shipped tool, and no tool can overwrite a consumer's file.
**Cons:** The agent types the frontmatter edits by hand, which is what the skill's
warnings exist for; and once the generator ships with the skill, the index it has always
written becomes an edit the rule forbids.
**Risks:** The rule gets quietly broken by the first tool that needs to write, with no ADR
saying where the line moved.

### Option 2: Write what the tool wholly owns, never a sentence the agent wrote (Accepted)

Four kinds of bytes qualify: a file generated from other files (the index); a field with
one right value given the command (`status`, `superseded-by`, `revisit-discharged-by`, a
filename, a heading number, a reference-link target naming a renumbered file); the skill's
own fixed template; and a value the agent passed on the command line, written verbatim.
Striking a spent condition through, moving the `(Accepted)` marker, writing citations stay
the agent's.

**Pros:** The edits that move are the ones with one right answer, so none of the agent's
judgement is displaced, and a tool's write set is enumerable and so testable.
**Cons:** A renumber leaves the agent citations elsewhere in the tree to move by hand; the
tool lists them.
**Risks:** "Wholly owns" is judged per tool, and a later tool stretches it.

### Option 3: Write anything the skill's workflows specify

Let the tool make every edit a workflow step names, prose included.

**Pros:** The workflows become one command each.
**Cons:** Body text has no single right form; a tool that edits it either rewrites the
agent's words or leaves a machine's. The failure 017 named for renames returns.
**Risks:** A consumer's paragraph is rewritten by a tool that read it as a pattern.

## Decision

Option 2. 017's clause protected a consumer's prose from a tool with a pattern and a
rename; that protection stands. What it did not need to protect is a file the tool
generates, a field with one right value given the command, or text the agent handed it — there is one
right value, the tool knows it, and the agent typing it adds only error. The line is drawn
at the sentence the agent wrote, because that is where a single right answer stops.

### Sub-question: one parser, two homes

Three ways to give the skill and `scripts/` the same parser. A copy in each, held
identical by a test, extends 017's prose-to-code coupling to a copy-to-copy one and
reinstates the duplication ADR 011 retired. Importing across the boundary by path is the shape of ADR 011's rejected Option
4, rejected there because a script's imports would depend on how it was invoked; here it
would also have the unshipped tree feeding the shipped one, which a consumer's cache
cannot honour. A symlink — `scripts/frontmatter.py` pointing into the skill — keeps one
file, needs no test, and follows a convention the repository already uses for `CLAUDE.md`,
`.claude/rules` and `.claude/skills`. The symlink is chosen. The file lives under
`skills/`, so its docstring names the constraints it serves rather than ADR numbers, as
`AGENTS.md` requires of anything that ships.

## Consequences

- ADR 017 stays in force with its second clause narrowed; it gains a Consequences bullet
  pointing here rather than a supersession, its other two clauses untouched.
- Every subcommand of the shipped tool documents its write set, and the skill's tests
  assert that `check` and `for` write nothing.
- The tool never regenerates the index behind the agent except after the agent's own edit
  under `docs/adr/`, or from a command the agent ran; the hook that checks after a shell
  command reports and does not write.
- `scripts/frontmatter.py` is a symlink, so a parser fix lands in the skill and ships;
  `python3 -m scripts.ci.validate_manifests` imports it unchanged. The move rewrites the
  module docstring, which today cites an ADR number.
- The scope names `skills/` and `.agents/skills/`, the paths ADR 017 binds, since any
  skill's tool is under the rule, and the symlink, since replacing it with a file is the
  breach.

[ADR 003]: 003-locate-skill-assets-relative-to-skill-directory.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[`frontmatter.py`]: ../../scripts/frontmatter.py
[`generate_index.py`]: ../../scripts/adr/generate_index.py
