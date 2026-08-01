---
status: Accepted
date: 2026-08-01
tags: [admin, branch-protection, bypass, ci, develop, github-app, releases, releasing, rulesets, workflow]
summary: Keep the Admin bypass on the develop ruleset permanently, for release preparation and mid-release corrections only — ordinary work still goes by pull request — rather than removing it after rollout or routing preparation through release/X.Y.Z branches; revisit if a second person gains write access or a human stops needing to write to develop.
---

# 009: Keep a standing bypass on the develop ruleset

## Context

The `trunk-develop` ruleset requires every change to `develop` to arrive by pull request
with a passing `gate` check from [`pr.yml`][]. Two actors are exempt: the release GitHub App,
which pushes the back-merge from [`release.yml`][], and the repository Admin role. Bypass
actors are configured per ruleset, so neither exemption reaches `main`.

The Admin exemption was introduced as scaffolding. [`release-automation.md`][] called it
temporary and told the maintainer to remove it once the App was installed and one release
had run end to end — conditions 2.0.0 has now met, which forces the question.

The release flow writes to `develop` before any release pull request exists. The
[`releasing`][] skill commits the CHANGELOG entry and version bump there and pushes them
directly; 2.0.0 then needed three further direct pushes, for a review response, a
documentation correction, and this decision's own paperwork.

[ADR 005][] bears directly on this. It made CI the authoritative enforcement layer over
local hooks and release-time validation, reasoning that "a check is worth most at the
moment the fault is authored, not at the moment it ships" — which is the trade a bypass
makes.

The repository has one human with write access, who is also the Admin the exemption
follows and the only reviewer any pull request would get.

## Options

### Option 1: Do nothing — leave the runbook's removal step standing

`release-automation.md` goes on instructing a removal whose conditions are now satisfied.

**Pros:** No decision to write down, and the eventual end state is a fully gated `develop`.
**Cons:** The instruction is live guidance, so the next person to follow the runbook breaks
the release flow; meanwhile the bypass's status is ambiguous — present, but documented as
going away.
**Risks:** The breakage surfaces mid-release, once the CHANGELOG entry is committed locally
and cannot be pushed. That is the worst moment to discover a policy change and the likeliest
to be resolved by hastily re-granting the exemption nobody has since reasoned about.

### Option 2: Keep the bypass permanently (Accepted)

Drop the "temporary" framing and treat the Admin exemption as part of the design.

**Pros:** Release preparation and mid-release corrections keep working with no per-release
ceremony.
**Cons:** Nothing distinguishes a deliberate release push from an accidental one.
**Risks:** The exemption is scoped to a *role*, so it widens silently — a second person
granted Admin inherits it without anyone deciding they should have it.

### Option 3: Route release preparation through `release/X.Y.Z` branches

Cut a release branch from `develop`, commit the preparation there, and merge it back by
pull request, so no *human* writes to `develop` directly.

**Pros:** Every human commit reaching `develop` is gated as it is authored, and the
mechanism holds however many people have write access.
**Cons:** Two gated pull requests per release rather than one, plus another for every
mid-release correction. The App's bypass stays regardless — it pushes the back-merge — so
this removes a class of bypass, not the concept.
**Risks:** Preparation now merges to `develop` while the release merges to `main`, giving
the flow two merge orders to get right; reversing them strands the version bump on a branch
`main` never sees. It also removes the human bypass that `releasing`'s recovery path
assumes when a back-merge must be pushed by hand.

### Option 4: Move release preparation into CI

Have the App commit the CHANGELOG entry and version bump from a `workflow_dispatch` job,
so no human needs to write to `develop` at all.

**Pros:** Removes the human bypass without adding pull requests, using access the App
already holds.
**Cons:** Preparation is not headless. `releasing` step 3 requires the maintainer to
confirm the computed version *and* that the notes carry nothing embargoed, before anything
is written — a job would have to either drop both confirmations or reimplement them as
inputs guessed in advance.
**Risks:** The notes are drafted by a skill whose output the maintainer reviews. Automating
the commit that follows moves the human check earlier than the material it checks.

## Decision

`develop` is not the branch that ships. The marketplace entry pins `main` ([ADR 010][]),
whose ruleset has no bypass actor, and the release pull request's diff is `main..develop` —
so every direct push of plugin *content* is checked before it can reach users, by the same
`gate` job, over the same paths. What the bypass changes is *when* the check runs, not
whether it runs or what it covers.

One surface is genuinely uncovered. The marketplace catalogue is read from the default
branch, so a bypassed push that breaks `marketplace.json` reaches users at their next
refresh with no gate in front of it — and that file is exactly what `validate_manifests.py`
exists to protect. The exposure is narrow (catalogue metadata, not plugin content) and the
same push would be caught on the release pull request, but "nothing reaches users ungated"
would be too strong a claim.

That is a carve-out from ADR 005, and worth naming as one. What 005 rejected was enforcement
that depends on someone's local machine — per-clone hooks, release-time prose checklists —
because those fail silently and invisibly. The fallback here is still CI, on a pull request,
blocking a merge. The principle 005 established survives; its timing preference is what
bends, for one branch, for one class of change.

Option 3 is the correct answer for a team and the wrong one here. Its enforcement is against
people pushing to `develop` without review — and there is one person, who is also the only
reviewer, so the added pull requests document a conversation with nobody. The cost is
ceremony rather than latency: a correction routed normally would face the same `gate` run,
but as a separate branch, pull request, and merge for a one-line fix to a release already in
flight. Option 4 is the better long-term answer and is blocked on something unrelated to
branch protection — the interactive confirmations in preparation — so it stays a revisit
trigger rather than a rejected design.

**Revisit when either holds:**

- A second person gains write access. Narrow the exemption to a named actor if the ruleset's
  actor types allow one; otherwise adopt Option 3, which needs no trust in who holds a role.
- A human stops needing to write to `develop` — most likely via Option 4, which moves the
  writes to the App rather than ending them.

## Consequences

**A direct push to `develop` is unchecked until a release pull request exists**, which may
be weeks. No workflow runs on push to `develop`: `pr.yml` triggers on `pull_request` only.
The fault then surfaces on the next pull request that touches the same filter paths, whose
author did not cause it — `pr.yml` selects jobs from the pull request's own diff, so an
unrelated change escapes it rather than inheriting it.

The ADR-index backstop is bypassed with it. `pr.yml`'s `adr` job exists because
[`.githooks/pre-commit`][] is not installed on clone, so a direct push from a clone or
worktree without the `core.hooksPath` setting [`AGENTS.md`][] calls for commits a stale
`INDEX.md` with nothing to catch it until the
release pull request goes red — mid-release, the failure mode charged against Option 1.

No bypass mode prompts before a push; they grant or withhold exemption and nothing more, so
the discipline is entirely the maintainer's.

Nothing in this repository can verify the decision is in force, as ADR 005 already recorded
of branch protection generally. `release-automation.md` and the live ruleset can drift in
either direction, and the symptom of drift is a push refused mid-release.

`release-automation.md` now describes the bypass as standing rather than pending, and carries
Option 3 as a note for anyone porting this automation to a project where a standing exemption
is unacceptable. That file is otherwise specific to this repository, down to the installation
target.

[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[`AGENTS.md`]: ../../AGENTS.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`release-automation.md`]: ../release-automation.md
[`release.yml`]: ../../.github/workflows/release.yml
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
