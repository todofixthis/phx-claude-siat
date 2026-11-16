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
rather than edits", and a test that fails when prose and code drift. It argued the second
from `nz-english`, whose only edit is a rename, "the thing the skill says kills you".

[ADR 022][] ships a tool that must write. The tool generates `INDEX.md`, which
[`adr.py`][] has always written, and scaffolds an ADR from the skill's template. It also
takes over the deterministic halves of the skill's workflows: setting `status: Superseded`
and `superseded-by`, setting `revisit-discharged-by`, and renumbering a file with its
heading and every peer field that names the old number. These are the edits the skill
warns against by hand, twice over (`13`, "never `013`"). Read literally, 017 forbids all
of them.

The tool also needs the frontmatter parser. [ADR 011][] put the parser in
[`frontmatter.py`][] so that `scripts/adr` and `scripts/ci` would stop keeping adapted
copies. A skill resolves its bundled files relative to its own directory ([ADR 003][]), so
the parser must sit inside the skill. `validate_manifests.py` still needs it from
`scripts/`.

## Options

### Option 1: Do nothing

Keep 017's clause as written. The tool reports, and the agent edits.

**Pros:** One rule covers every shipped tool, and no tool can overwrite a consumer's file.
**Cons:** The agent types the frontmatter edits by hand, which is what the skill's
warnings exist for. Once the generator ships with the skill, the index it has always
written becomes an edit the rule forbids.
**Risks:** The first tool that needs to write breaks the rule quietly, and no ADR records
where the line moved.

### Option 2: Write what the tool wholly owns, never a sentence the agent wrote (Accepted)

Four kinds of bytes qualify:

- A file generated from other files, such as the index.
- A field with one right value given the command: `status`, `superseded-by`,
  `revisit-discharged-by`, a filename, a heading number, or a reference-link target that
  names a renumbered file.
- The skill's own fixed template.
- A value the agent passed on the command line, written verbatim.

Striking through a spent condition, moving the `(Accepted)` marker, and writing citations
stay with the agent.

**Pros:** The tool makes only the edits with one right answer, so it displaces none of the
agent's judgement. A tool's write set can be listed, so it can be tested.
**Cons:** After a renumber, the agent moves citations elsewhere in the tree by hand. The
tool lists them.
**Risks:** Each tool is judged on what it "wholly owns", and a later tool stretches the
term.

### Option 3: Write anything the skill's workflows specify

Let the tool make every edit a workflow step names, prose included.

**Pros:** Each workflow becomes one command.
**Cons:** Body text has no single right form. A tool that edits it either rewrites the
agent's words or leaves a machine's words behind. The failure 017 named for renames
returns.
**Risks:** A tool reads a consumer's paragraph as a pattern and rewrites it.

## Decision

Option 2. 017's clause protected a consumer's prose from a tool armed with a pattern and a
rename, and that protection stands. The clause did not need to protect a file the tool
generates, a field with one right value given the command, or text the agent handed to the
tool. In each of these there is one right value and the tool knows it, so the agent typing
it adds only error. The line falls at the sentence the agent wrote, because that is where a
single right answer stops.

### Sub-question: one parser, two homes

There were three ways to give the skill and `scripts/` the same parser.

A copy in each place, held identical by a test, would extend 017's prose-to-code coupling
to a copy-to-copy coupling. It would also bring back the duplication ADR 011 retired.

Importing across the boundary by path is the shape of ADR 011's rejected Option 4. ADR 011
rejected it because a script's imports would depend on how the script was invoked. Here
the unshipped tree would also feed the shipped one, which a consumer's cache cannot honour.

A symlink, `scripts/frontmatter.py` pointing into the skill, keeps one file and needs no
test. It follows a convention the repository already uses for `CLAUDE.md`, `.claude/rules`
and `.claude/skills`.

The symlink is chosen. The file lives under `skills/`, so its docstring names the
constraints it serves rather than ADR numbers, as `AGENTS.md` requires of anything that
ships.

## Consequences

- ADR 017 stays in force with its second clause narrowed. Instead of a supersession, it
  gains a Consequences bullet that points here, and its other two clauses stay untouched.
- Every subcommand of the shipped tool documents its write set. The skill's tests assert
  that `check` and `for` write nothing.
- The tool regenerates the index behind the agent only after the agent's own edit under
  `docs/adr/`, or from a command the agent ran. The hook that checks after a shell command
  reports and does not write.
- `scripts/frontmatter.py` is a symlink, so a parser fix lands in the skill and ships.
  `python3 -m scripts.ci.validate_manifests` imports it unchanged. The move rewrites the
  module docstring, which today cites an ADR number.
- The scope names `skills/` and `.agents/skills/`, the paths ADR 017 binds, because every
  skill's tool is under the rule. It also names the symlink, because replacing the symlink
  with a file is the breach.

[ADR 003]: 003-locate-skill-assets-relative-to-skill-directory.md
[ADR 011]: 011-make-scripts-a-package.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`frontmatter.py`]: ../../scripts/frontmatter.py
