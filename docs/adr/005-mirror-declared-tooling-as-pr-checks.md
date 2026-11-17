---
status: Accepted
date: 2026-07-16
scope: [.github/workflows/pr.yml, skills/]
summary: Gate every pull request in CI with checks mirroring the tooling each skill declares, making CI the authoritative enforcement layer rather than local git hooks or release-time validation — hooks stay welcome as a faster-failing local aid, just no longer the layer enforcement depends on — so a skill that gains tooling gains matching checks in the same change, with branch protection requiring only the aggregate gate job.
---

# 005: Mirror each skill's declared tooling as a pull-request check

## Context

Nothing gated a pull request in this repo. No branch had a `.github/` directory, so every
invariant held only if a human or an agent remembered it. Three were already drifting:

- The [pre-commit hook][] regenerates `docs/adr/INDEX.md`, but a clone doesn't install
  hooks. [`AGENTS.md`][] documents the required `git config core.hooksPath .githooks` and
  the symptom of forgetting it, a stale index. Nothing detected a stale index.
- The [`releasing`][] skill checks by hand that both manifests are valid JSON, that the
  marketplace entry has no `version` as [ADR 001][] requires, and that the tests pass.
  Release is the latest possible moment to find any of those faults.
- `skills/creative-commits/pyproject.toml` declares `black`, `ruff`, and `pytest` in a
  `[tool.autohooks]` block. But [autohooks][] isn't installed, and `core.hooksPath` points
  at `.githooks`, which never calls it. The block does nothing, so `black` had never run
  against the code it supposedly governs.

Three forces apply. [Renovate][] opens dependency PRs that no human really reviews, so an
unchecked lockfile bump is a blind merge. Skills reach users through the marketplace, so a
broken manifest is a broken install. And a declaration that nothing runs decays without
anyone noticing. The inert block proves it.

## Options

### Option 1: Do nothing

Keep enforcement in the pre-commit hook and the `releasing` skill.

**Pros:** No CI to maintain, and nothing new that can fail.

**Cons:** Enforcement is opt-in, because the hook runs only for a contributor who set it
up. Nothing verifies Renovate PRs.

**Risks:** A fault reaches `main`, where it costs the most to undo.

### Option 2: Gate pull requests in CI, mirroring declared tooling (Accepted)

One [PR workflow][] runs each skill's own declared tooling, plus the checks the
`releasing` skill did by hand. Path-filtered jobs feed one aggregate `gate` job, which is
the only required status check.

**Pros:** The release-time checklist runs as code, so nobody has to remember it.

**Cons:** A rule lives in both a skill's config and the workflow, and the two can get out
of step. The path filters are hand-written globs, and each new skill needs a new arm.

**Risks:** Someone keeps the mirror in step by hand, so it drifts from the declaration it
mirrors. A tool added to a skill the workflow already gates never runs. That is the inert
block's failure again, one layer up.

### Option 3: Make local hooks the enforcement layer

Make `.githooks/pre-commit` run `uv run --project skills/creative-commits autohooks
check`, set up `core.hooksPath` on clone, and treat the hook as the place enforcement
lives, with no CI.

**Pros:** Fails fastest, before a commit exists. Costs almost nothing to build: `autohooks`
is already a declared dev dependency, and the hook already calls `python3`.

**Cons:** Enforces nothing for Renovate, which never runs a hook. `--no-verify` bypasses
it.

**Risks:** Each clone needs setup, and a missed setup silently does nothing. That is the
current failure, written down instead of fixed.

## Decision

Adopt Option 2, as a standing strategy and not a one-off workflow: **when a skill gains
executable tooling, add the matching PR check in the same change.** The tooling a skill
declares is the specification, and CI runs it.

CI wins over local hooks because it is the only layer a bot passes through, and Renovate is
the author whose PRs get the least scrutiny. A hook can't gate the case that most needs
gating. Option 3 is otherwise cheap and really is faster. So this rejects hooks as the
*authoritative* layer, not as a local aid. A contributor who sets them up finds faults
sooner, and nothing depends on anyone doing so.

CI wins over release-time validation because a check is worth most at the moment the fault
is authored, not at the moment it ships.

That leaves the standing rule as prose and Option 2's drift risk unanswered. A mirror kept
in step by hand can drift from what it mirrors, which is the same fault this ADR
criticises, in a different place. Whether and how to detect that drift is a second
question, with its own options and costs. [ADR 006][] settles it.

## Consequences

- Turning on a check that never ran reformats the code it never ran against. Enforcing
  `black` did exactly that the first time. Expect it once for each dormant tool.
- **Branch protection must require only the `gate` job.** A path-filtered job reports
  `skipped`, not `success`, so requiring one directly blocks every PR that skips it,
  forever.
- Branch protection is a repo setting, not a file, so nothing in the repo can verify or
  enforce it. Until a maintainer configures it on `develop` and `main`, every check below
  is advisory, and this decision delivers none of what it claims.
- Manifest rules that the `releasing` skill stated in prose now run in
  [`validate_manifests.py`][], which that skill calls instead of restating them. Each rule
  lives in one place. It runs before the release changes anything, and again on the release
  PR.
- Adding a skill with tooling needs a new `case` arm in the workflow as well as a new job.
  ADR 006 decides what happens when someone forgets.
- `validate_manifests.py` duplicates the frontmatter parser from [`adr.py`][]. That is the
  kind of duplication this ADR criticises elsewhere. We accept it because coupling two
  sibling scripts costs more than the copy.
- `[tool.autohooks]` is still only a declaration. It reads as if autohooks runs on commit.
  It doesn't. The workflow is what enforces those tools now.
- Actions are pinned to tags, not SHAs, so someone could move a tag under us.
  `permissions: contents: read` limits the damage, and Renovate's `github-actions` manager
  keeps the pins current.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`AGENTS.md`]: ../../AGENTS.md
[autohooks]: https://github.com/greenbone/autohooks
[PR workflow]: ../../.github/workflows/pr.yml
[pre-commit hook]: ../../.githooks/pre-commit
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[Renovate]: ../../renovate.json
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
