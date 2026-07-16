---
status: Accepted
date: 2026-07-16
tags: [autohooks, branch-protection, ci, github-actions, hooks, linting, pull-requests, python, releases, renovate, skills, testing, tooling, uv]
summary: Gate every pull request in CI with checks mirroring the tooling each skill declares — a skill that gains tooling gains matching checks in the same change — with branch protection requiring only the aggregate gate job.
---

# 005: Mirror each skill's declared tooling as a pull-request check

## Context

Nothing gated a pull request in this repo. There was no `.github/` directory on any
branch, so every invariant depended on a human or an agent remembering it — and three
were already drifting:

- The [pre-commit hook][] regenerates `docs/adr/INDEX.md`, but hooks are not installed on
  clone. [`AGENTS.md`][] documents both the required `git config core.hooksPath .githooks`
  and the symptom of forgetting it: a stale index. Nothing detected that.
- The [`releasing`][] skill hand-checks that both manifests are valid JSON, that the
  marketplace entry carries no `version` per [ADR 001][], and that the tests pass. Release
  is the last possible moment to discover any of those faults.
- `skills/creative-commits/pyproject.toml` declares `black`, `ruff`, and `pytest` through a
  `[tool.autohooks]` block, but [autohooks][] is not installed and `core.hooksPath` points
  at `.githooks`, which never invokes it. The block is inert, and `black` had consequently
  never run against the code it nominally governs.

The forces: [Renovate][] opens dependency PRs that no human meaningfully reviews, so an
unchecked lockfile bump is a blind merge. Skills reach users through the marketplace, so a
broken manifest is a broken install. And a declaration nobody executes decays unnoticed —
the inert block is the proof, not a hypothetical.

## Options

### Option 1: Do nothing

Keep enforcement in the pre-commit hook and the `releasing` skill.

**Pros:** No CI to maintain; no new failure surface.

**Cons:** Enforcement is opt-in — the hook only runs for a contributor who configured it.
Renovate PRs remain unverified.

**Risks:** A fault reaches `main`, where it is most expensive to unwind.

### Option 2: Gate pull requests in CI, mirroring declared tooling (Accepted)

A single [PR workflow][] runs each skill's own declared tooling, plus the checks the
`releasing` skill performed by hand. Path-filtered jobs converge on one aggregate `gate`
job, the only required status check.

**Pros:** Makes the release-time checklist executable rather than remembered.

**Cons:** A rule lives both in a skill's config and in the workflow, and the two can fall
out of step. The path filters are hand-rolled globs needing a new arm per skill.

**Risks:** The mirror is held by hand, so it drifts from the declaration it mirrors — a tool
added to a skill the workflow already gates simply never runs. That is the inert block's
shape, one layer up, and only its crudest form is cheap to detect.

#### Sub-option: derive the checks from the declaration

Rather than hand-writing jobs, parse `[tool.autohooks]` and generate them.

**Pros:** One source of truth; cannot fail open.

**Cons:** A parser and a codegen step, plus a schema mapping tools to runners.

**Risks:** Machinery outliving its justification — one package does not exercise it.

### Option 3: Make local hooks the enforcement layer

Wire `.githooks/pre-commit` to run `uv run --project skills/creative-commits autohooks
check` and bootstrap `core.hooksPath` on clone, treating that as where enforcement lives
instead of standing up CI.

**Pros:** Fails fastest — before a commit exists. Costs almost nothing to build:
`autohooks` is already a declared dev dependency, and the hook already shells out to
`python3`.

**Cons:** Enforces nothing for Renovate, which never runs a hook. Bypassable with
`--no-verify`.

**Risks:** Per-clone setup that silently no-ops when missed — the status quo's failure
mode, formalised rather than fixed.

## Decision

Adopt Option 2, and treat it as a standing strategy rather than a one-off workflow:
**when a skill gains executable tooling, add the matching PR check in the same change.**
The tooling a skill declares is the specification; CI is what executes it.

CI wins over local hooks because it is the only layer a bot passes through, and Renovate is
precisely the author whose PRs get the least scrutiny. A hook cannot gate the one case that
most needs gating. Option 3 is otherwise cheap and genuinely faster, so rejecting it rejects
hooks as the *authoritative* layer, not as a local aid — a contributor who wires them up
simply finds out sooner, and nothing depends on them doing so.

CI wins over release-time validation because a check is worth most at the moment the fault
is authored, not at the moment it ships.

The sub-option is refused on cost, not principle: a parser and codegen to serve one package
is machinery in search of a use. Refusing it, however, need not mean accepting the gap it
was for. The rule this ADR creates would otherwise be one more declaration nothing executes —
the very pathology named above — so CI asserts the half that is cheap to assert: every
skill shipping tooling must be referenced by the workflow, or the build fails, naming this
ADR. Adding a skill with tooling and no check is now an error rather than a silence.

That check is deliberately shallow. It cannot tell whether a job runs the *right* tools,
only that some job claims the skill, so the mirror can still hold the wrong shape — quietly
running `ruff` for a package that has since added `mypy`. Closing that needs the sub-option,
and the trade should be revisited at the second package with tooling, sooner if a wrong
mirror ever reaches `main`.

## Consequences

- Enabling a previously-inert check reformats the code it was never run against; enforcing
  `black` did exactly that on first contact. Expect it once per dormant tool.
- **Branch protection must require only the `gate` job.** Path-filtered jobs report
  `skipped`, not `success`, so requiring one directly deadlocks every PR that skips it.
- Branch protection is a repo setting, not a file: nothing here can verify or enforce it.
  Until a maintainer configures it on `develop` and `main`, every check below is advisory
  and this decision delivers none of what it claims.
- Manifest rules the `releasing` skill enforced in prose now execute in
  [`validate_manifests.py`][], runnable locally. That skill still describes them, so the two
  can diverge until it is rewired to call the script.
- Adding a skill with tooling means a new `case` arm in the workflow as well as a new job.
  Forgetting entirely fails the build; wiring the arm but gating the wrong tools does not.
- `validate_manifests.py` duplicates the frontmatter parser from [`generate_index.py`][],
  the same duplication this ADR indicts elsewhere, accepted for the same reason the
  sub-option was: coupling two sibling scripts costs more than the copy.
- `[tool.autohooks]` remains declaration-only. It reads as though autohooks runs on commit;
  it does not, and now the workflow is what actually enforces those tools.
- Actions are tag-pinned rather than SHA-pinned, so a tag could be moved under us;
  `permissions: contents: read` bounds the blast radius, and Renovate's `github-actions`
  manager keeps the pins current.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[`AGENTS.md`]: ../../AGENTS.md
[autohooks]: https://github.com/greenbone/autohooks
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[PR workflow]: ../../.github/workflows/pr.yml
[pre-commit hook]: ../../.githooks/pre-commit
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[Renovate]: ../../renovate.json
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
