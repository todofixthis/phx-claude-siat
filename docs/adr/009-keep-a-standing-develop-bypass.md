---
status: Accepted
date: 2026-08-01
tags: [admin, branch-protection, bypass, ci, develop, github-app, releases, releasing, rulesets, workflow]
summary: Keep the Admin bypass on the develop ruleset permanently, for release preparation and mid-release corrections only — ordinary work still goes by pull request — rather than removing it after rollout or routing preparation through release/X.Y.Z branches; revisit if a second person gains write access or a human stops needing to write to develop.
---

# 009: Keep a standing bypass on the develop ruleset

## Context

This repository has one human with write access. That person is also the Admin whose role
carries the exemption below, and the only reviewer any pull request would get.

The `trunk-develop` ruleset requires every change to `develop` to arrive by pull request
with a passing `gate` check — the aggregate job [`pr.yml`][] exposes to the ruleset. Two
*bypass actors*, in GitHub's ruleset vocabulary, are exempt: the release GitHub App, which
pushes the back-merge from [`release.yml`][], and the repository Admin role. Bypass actors
are configured per ruleset, so neither exemption reaches `main` — and since [ADR 010][],
`main` is the branch the marketplace serves.

The Admin exemption was introduced as scaffolding. [`release-automation.md`][] called it
temporary and told the maintainer to remove it once the App was installed and one release
had run end to end. The 2.0.0 release met both conditions, so that instruction is now live.

The release flow writes to `develop` before any release pull request exists: the
[`releasing`][] skill commits the CHANGELOG entry and version bump there and pushes them
directly. 2.0.0 then took three more direct pushes — a review response, a documentation
correction, and this decision's own paperwork — which is the point. Corrections to a release
already in flight are routine, not exceptional.

[ADR 005][] bears on this. It made CI the authoritative enforcement layer over local hooks
and release-time validation, reasoning that "a check is worth most at the moment the fault is
authored, not at the moment it ships" — the trade a bypass makes.

## Options

### Option 1: Do nothing — leave the runbook's removal step standing

`release-automation.md` goes on instructing a removal whose conditions are now satisfied.

**Pros:** No decision to write down, and the eventual end state is a fully gated `develop`.
**Cons:** The instruction is live guidance, so the next person to follow the runbook breaks
the release flow; meanwhile the bypass is present but documented as going away.
**Risks:** The breakage surfaces mid-release, once the CHANGELOG entry is committed locally
and cannot be pushed — the likeliest moment for the exemption to be re-granted in haste by
someone who never reasoned about it.

### Option 2: Keep the bypass permanently (Accepted)

Drop the "temporary" framing and treat the Admin exemption as part of the design.

**Pros:** Release preparation and mid-release corrections keep working with no per-release
ceremony.
**Cons:** The exemption follows the Admin *role* rather than a person, so it widens silently
to anyone later granted Admin.
**Risks:** A mistaken push lands as quietly as an intended one, and nothing catches it until
the release pull request.

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
**Risks:** Automating the commit moves the human check earlier than the material it checks;
the notes are drafted by a skill whose output the maintainer reviews.

## Decision

`develop` is not the branch that ships. `main`'s ruleset has no bypass actor, and the release
pull request's diff is `main..develop` — so every direct push of plugin content is checked
before it can reach users, by the same `gate` job, over the same paths. What the bypass
changes is *when* the check runs, not whether it runs or what it covers.

That is a carve-out from ADR 005. What 005 rejected was enforcement depending on someone's
local machine — per-clone hooks, release-time prose checklists — because those fail
invisibly. The fallback here is still CI, on a pull request, blocking a merge: the principle
survives, and its timing preference is what bends, for one branch and one class of change.

Option 3 is the correct answer for a team and the wrong one here: its enforcement is against
unreviewed pushes, so the added pull requests would document a conversation with nobody. The
cost is ceremony rather than latency — a correction routed normally faces the same `gate`
run, but as a separate branch, pull request, and merge for a one-line fix. Option 4 is the
better long-term answer, blocked on something unrelated to branch
protection — the interactive confirmations in preparation — so it stays a revisit trigger
rather than a rejected design.

**Revisit when either holds:**

- A second person gains write access. Narrow the exemption to a named actor if the ruleset's
  actor types allow one; otherwise adopt Option 3, which needs no trust in who holds a role.
- A human stops needing to write to `develop` — most likely via Option 4, which moves the
  writes to the App rather than ending them.

## Consequences

**A direct push to `develop` is unchecked until a release pull request exists**, which may be
weeks: no workflow runs on push to `develop`, since `pr.yml` triggers on `pull_request` only.
The fault then sits unnoticed until some pull request happens to touch the same paths, and
that pull request goes red for a fault its author did not introduce. An unrelated change
never runs the check at all, because `pr.yml` selects jobs from the pull request's own diff.

The ADR-index backstop goes the same way. `pr.yml` runs an `adr` job because
[`.githooks/pre-commit`][] is not installed on clone; activating it needs the `core.hooksPath`
setting [`AGENTS.md`][] describes. Push directly from a clone or worktree that lacks it, and a
stale `INDEX.md` is committed with nothing to catch it until the release pull request goes
red — mid-release, the failure mode charged against Option 1.

The marketplace catalogue is not covered by the release pull request at all. ADR 010 records
why: `marketplace.json` is read from the default branch, so a bypassed push that breaks it
reaches users at their next refresh, ungated.

No bypass mode prompts before a push — they grant or withhold exemption and nothing more —
so the discipline is entirely the maintainer's.

Nothing here can verify the exemption is still in force, as ADR 005 recorded of branch
protection generally, so `release-automation.md` and the live ruleset can drift in either
direction. The symptom is a push refused mid-release.

`release-automation.md` now describes the bypass as standing rather than pending, and carries
Option 3 as a note for projects porting this automation where a standing exemption is
unacceptable.

[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[`AGENTS.md`]: ../../AGENTS.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`release-automation.md`]: ../release-automation.md
[`release.yml`]: ../../.github/workflows/release.yml
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
