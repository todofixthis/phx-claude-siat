# writing-adrs should pre-approve its own tool once a grant is shown to work

> Recorded 2026-09-03, from the end-to-end run of the writing-adrs system. Not a GitHub
> issue (ADR 020).

## What

Give [`skills/writing-adrs/SKILL.md`][] frontmatter that pre-approves
`python3 ${CLAUDE_SKILL_DIR}/adr.py`, so the commands the skill tells the agent to run
cost no permission prompt, and restore the assertion in
[`skills/writing-adrs/tests/test_skill_drift.py`][] that couples the grant to those
command lines.

The grant was removed 2026-09-03, measured not to work. In nested `claude -p` sessions
launched with `--plugin-dir`, a skill carrying
`allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/adr.py:*)` was permission-denied at
invocation — the `Skill` tool itself — so the skill never loaded. With the invocation
pre-approved the skill loaded, and the `adr.py` command was still denied under both the
`:*` and the ` *` rule forms. So the grant cost a prompt and bought nothing.

## Why it is still worth doing

Every `adr.py` command the skill gives now prompts, as `nz-english`'s `scan.py` does: one
per scaffold, per check, per lookup, in a skill whose point is that the mechanics are cheap.
The block is the harness's, not the skill's, so this waits on a harness that honours a
skill's `allowed-tools` for a bundled tool.

## Acceptance

- A headless session (`claude -p` with `--plugin-dir`) invokes `phx:writing-adrs` without a
  permission denial.
- That session runs `python3 ${CLAUDE_SKILL_DIR}/adr.py check` without a permission denial.
- `skills/writing-adrs/tests/test_skill_drift.py` asserts the grant's rule text against the
  command lines the skill gives, in place of today's assertion that the frontmatter carries
  no grant.

[`skills/writing-adrs/SKILL.md`]: ../../skills/writing-adrs/SKILL.md
[`skills/writing-adrs/tests/test_skill_drift.py`]: ../../skills/writing-adrs/tests/test_skill_drift.py
