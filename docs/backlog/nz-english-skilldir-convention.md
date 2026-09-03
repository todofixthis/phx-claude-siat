# nz-english should reach its tool the way writing-adrs does

> Recorded 2026-09-02, from the writing-adrs tooling work. Not a GitHub issue (ADR 020).

## What

Give [`skills/nz-english/SKILL.md`][] the convention [`skills/writing-adrs/SKILL.md`][] now
uses: `${CLAUDE_SKILL_DIR}` in every command line, and an `allowed-tools` rule pre-approving
the tool.

`nz-english` instead tells the agent to substitute for `<skilldir>` the base directory the
skill reported when it loaded. ADR 022 records that `${CLAUDE_SKILL_DIR}` is the harness's
own form of the skill-relative resolution ADR 003 requires, so this is a migration rather
than a reopened decision.

## Why it is still worth doing

Two ways to reach a bundled tool in one plugin is one convention too many, and the
substitution costs a step the agent can get wrong. The `allowed-tools` rule then spares a
permission prompt per sweep.

## The README note is a liveness test, not a running instruction

[`README.md`][] tells the reader to judge which copy of the plugin a session serves from the
base directory a `phx:` skill reports at load — as `AGENTS.md` and ADR 003's Consequences
both do. That survives the migration and must not be deleted with the `<skilldir>`
substitution; it needs rewording so the two are plainly different uses of the same reported
path.

## Acceptance

- Every `scan.py` command line in `skills/nz-english/SKILL.md` reads
  `python3 ${CLAUDE_SKILL_DIR}/scan.py …`, and no `<skilldir>` placeholder survives.
- That skill's frontmatter carries `allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scan.py:*)`.
- `README.md`'s base-directory paragraph reads only as the liveness test — nothing in it
  reads as how to reach a bundled tool.

[`README.md`]: ../../README.md
[`skills/nz-english/SKILL.md`]: ../../skills/nz-english/SKILL.md
[`skills/writing-adrs/SKILL.md`]: ../../skills/writing-adrs/SKILL.md
