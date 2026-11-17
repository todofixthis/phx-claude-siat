# writing-adrs should pre-approve its own tool once a grant is shown to work

> Recorded 2026-09-03, from the end-to-end run of the writing-adrs system. Not a GitHub
> issue (ADR 020).

## What

Give [`skills/writing-adrs/SKILL.md`][] frontmatter that pre-approves
`sh "${CLAUDE_SKILL_DIR}/adr.sh" "${CLAUDE_PLUGIN_DATA}"`, so the commands the skill tells
the agent to run cost no permission prompt. Then restore the assertion in
[`skills/writing-adrs/tests/test_skill_drift.py`][] that couples the grant to those
command lines.

The grant was removed on 2026-09-03, because measurement showed it did not work. In nested
`claude -p` sessions launched with `--plugin-dir`, a skill carrying
`allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/adr.py:*)` was denied permission at
invocation, on the `Skill` tool itself, so the skill never loaded. With the invocation
pre-approved, the skill loaded, but the `adr.py` command was still denied under both the
`:*` and the ` *` rule forms. So the grant cost a prompt and bought nothing.

## Why it is still worth doing

Every `adr.sh` command the skill gives now prompts, as `nz-english`'s `scan.py` does. That
is one prompt per scaffold, per check, and per lookup, in a skill whose point is that the
mechanics are cheap. The harness, not the skill, causes the block, so this item waits on a
harness that honours a skill's `allowed-tools` for a bundled tool.

## Acceptance

- A headless session (`claude -p` with `--plugin-dir`) invokes `phx:writing-adrs` without a
  permission denial.
- That session runs `sh "${CLAUDE_SKILL_DIR}/adr.sh" "${CLAUDE_PLUGIN_DATA}" check`
  without a permission denial.
- `skills/writing-adrs/tests/test_skill_drift.py` asserts the grant's rule text against the
  command lines the skill gives, in place of today's assertion that the frontmatter carries
  no grant.

[`skills/writing-adrs/SKILL.md`]: ../../skills/writing-adrs/SKILL.md
[`skills/writing-adrs/tests/test_skill_drift.py`]: ../../skills/writing-adrs/tests/test_skill_drift.py
