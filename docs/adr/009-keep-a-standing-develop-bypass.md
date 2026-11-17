---
status: Accepted
date: 2026-08-01
scope: []
summary: Keep the Admin bypass on the develop ruleset permanently, for release preparation and mid-release corrections only — ordinary work still goes by pull request — rather than removing it after rollout or routing preparation through release/X.Y.Z branches.
revisit-when: A second person gains write access, or a human stops needing to write to develop.
---

# 009: Keep a standing bypass on the develop ruleset

## Context

This repository has one human with write access. That person is also the Admin whose role
carries the exemption below, and the only reviewer any pull request would get.

The `trunk-develop` ruleset requires every change to `develop` to arrive by pull request
with a passing `gate` check, the aggregate job that [`pr.yml`][] exposes to the ruleset.
Two *bypass actors*, in GitHub's ruleset vocabulary, are exempt. One is the release GitHub
App, which pushes the back-merge from [`release.yml`][]. The other is the repository Admin
role. Each ruleset configures its own bypass actors, so neither exemption reaches `main`.
Since [ADR 010][], `main` is the branch the marketplace serves.

The Admin exemption began as a temporary measure. [`release-automation.md`][] called it
temporary and told the maintainer to remove it once the App was installed and one release
had run end to end. The 2.0.0 release met both conditions, so that instruction is now live.

The release flow writes to `develop` before any release pull request exists. The
[`releasing`][] skill commits the CHANGELOG entry and version bump there and pushes them
directly. 2.0.0 then took three more direct pushes: a review response, a documentation
correction, and this decision's own paperwork. That is the point. Corrections to a release
already in flight are routine, not exceptional.

[ADR 005][] bears on this. It made CI the authoritative enforcement layer over local hooks
and release-time validation, reasoning that "a check is worth most at the moment the fault is
authored, not at the moment it ships". A bypass gives up exactly that.

## Options

### Option 1: Do nothing — leave the runbook's removal step standing

`release-automation.md` goes on telling the maintainer to remove the exemption, and the
conditions for doing so are now met.

**Pros:** There is no decision to write down, and `develop` ends up fully gated.
**Cons:** The instruction is live guidance, so the next person to follow the runbook breaks
the release flow. Meanwhile the bypass stays in place but is documented as going away.
**Risks:** The breakage surfaces mid-release, once the CHANGELOG entry is committed locally
and cannot be pushed. That is the likeliest moment for someone to grant the exemption again
in haste, without ever reasoning about it.

### Option 2: Keep the bypass permanently (Accepted)

Drop the "temporary" framing and treat the Admin exemption as part of the design.

**Pros:** Release preparation and mid-release corrections keep working with no extra steps
per release.
**Cons:** The exemption follows the Admin *role*, not a person, so it widens silently to
anyone later granted Admin.
**Risks:** A mistaken push lands as quietly as an intended one, and nothing catches it until
the release pull request.

### Option 3: Route release preparation through `release/X.Y.Z` branches

Cut a release branch from `develop`, commit the preparation there, and merge it back by
pull request, so no *human* writes to `develop` directly.

**Pros:** The gate checks every human commit that reaches `develop` as it is written, and
the mechanism holds however many people have write access.
**Cons:** Each release needs two gated pull requests instead of one, plus another for every
mid-release correction. The App's bypass stays regardless, because the App pushes the
back-merge. So this option removes one class of bypass, not bypasses altogether.
**Risks:** Preparation now merges to `develop` while the release merges to `main`, so the
flow has two merge orders to get right. Reversing them strands the version bump on a
branch `main` never sees. This option also removes the human bypass that `releasing`'s
recovery path assumes when someone must push a back-merge by hand.

### Option 4: Move release preparation into CI

Have the App commit the CHANGELOG entry and version bump from a `workflow_dispatch` job,
so no human needs to write to `develop` at all.

**Pros:** It removes the human bypass without adding pull requests, using access the App
already holds.
**Cons:** Preparation needs a human. `releasing` step 3 requires the maintainer to confirm
the computed version *and* that the notes carry nothing embargoed, before anything is
written. A job would have to either drop both confirmations or turn them into inputs
guessed in advance.
**Risks:** Automating the commit moves the human check earlier than the material it checks.
A skill drafts the notes, and the maintainer reviews that skill's output.

## Decision

`develop` is not the branch that ships. `main`'s ruleset has no bypass actor, and the release
pull request's diff is `main..develop`. So the same `gate` job checks every direct push of
plugin content, over the same paths, before it can reach users. The bypass changes *when*
the check runs, not whether it runs or what it covers.

That is a carve-out from ADR 005. ADR 005 rejected enforcement that depends on someone's
local machine, such as per-clone hooks and release-time prose checklists, because those fail
invisibly. The fallback here is still CI, on a pull request, blocking a merge. The principle
survives. Its preference for early checks bends, for one branch and one class of change.

Option 3 is the correct answer for a team and the wrong one here. It enforces against
unreviewed pushes, so its extra pull requests would record a review with nobody. Its cost
is extra steps, not delay. A correction routed through Option 3 faces the same `gate` run,
but needs its own branch, pull request, and merge for a one-line fix. Option 4 is the
better long-term answer. Something unrelated to branch protection blocks it: the
interactive confirmations in preparation. So Option 4 stays a revisit trigger, not a
rejected design.

**Revisit when either holds:**

- A second person gains write access. Narrow the exemption to a named actor if the ruleset's
  actor types allow one. Otherwise adopt Option 3, which needs no trust in who holds a role.
- A human stops needing to write to `develop`. Option 4 is the likeliest route, and it moves
  the writes to the App instead of ending them.

## Consequences

**Nothing checks a direct push to `develop` until a release pull request exists**, which may
take weeks. No workflow runs on push to `develop`, because `pr.yml` triggers on
`pull_request` only. The fault then sits unnoticed until some pull request happens to touch
the same paths, and that pull request goes red for a fault its author did not introduce. An
unrelated change never runs the check at all, because `pr.yml` selects jobs from the pull
request's own diff.

The ADR-index backstop has the same gap. `pr.yml` runs an `adr` job because cloning does
not install [`.githooks/pre-commit`][]. Activating the hook needs the `core.hooksPath`
setting that [`AGENTS.md`][] describes. If you push directly from a clone or worktree that
lacks it, a stale `INDEX.md` goes in, and nothing catches it until the release pull request
goes red. That is mid-release, the failure mode charged against Option 1.

The release pull request does not cover the marketplace catalogue at all. ADR 010 records
why. The marketplace reads `marketplace.json` from the default branch, so a bypassed push
that breaks it reaches users, ungated, at their next refresh.

No bypass mode prompts before a push. Each mode grants or withholds the exemption and does
nothing more, so the discipline rests entirely with the maintainer.

Nothing here can verify that the exemption is still in force, as ADR 005 recorded of branch
protection generally. So `release-automation.md` and the live ruleset can drift in either
direction. The symptom is a push refused mid-release.

`release-automation.md` now describes the bypass as standing, not pending. It also carries
Option 3 as a note for projects that port this automation and cannot accept a standing
exemption.

[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[`AGENTS.md`]: ../../AGENTS.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`release-automation.md`]: ../release-automation.md
[`release.yml`]: ../../.github/workflows/release.yml
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
