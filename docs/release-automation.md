# Release automation

## Overview

Cutting a release is split across two actors. The `releasing` skill (unprefixed,
project-local) drives Phase 1 only — it prepares `develop`, opens the `develop`→`main`
PR, and stops for a human to merge it. The `push: [main]` workflow then finishes
Phase 2 — tagging the merge commit, publishing the GitHub Release, and back-merging
`main` into `develop` — running as a GitHub App rather than the human who merged, so
the back-merge push isn't blocked by the same branch protection it must satisfy.

The workflow implementing this setup is
[`.github/workflows/release.yml`](../.github/workflows/release.yml); keep the two in
sync when either changes.

## One-time setup

1. Create a GitHub App with the repository permission **Contents: write** only, and no
   others. Install it on `todofixthis/phx-claude-siat`. Note the App ID and generate a
   private key.
2. Add repository Actions secrets `APP_ID` and `APP_PRIVATE_KEY` (the App ID and the
   private key from step 1).
3. Split the **Trunk** ruleset into two:
   - **Trunk–develop** — target `~DEFAULT_BRANCH`; add the App as a bypass actor, mode
     `always`.
   - **Trunk–main** — target `refs/heads/main`; no bypass actor.

   Both keep the existing rules: `deletion`, `non_fast_forward`, `pull_request`
   (merge-only), `required_status_checks: gate`.
4. Add a **tag ruleset** on `refs/tags/*`: `non_fast_forward` and `deletion`. No
   `required_signatures` — release tags are unsigned.

## Rollout order (important)

Keep the temporary Admin bypass on `develop` until the App is installed and one
release has completed all the way through the workflow. Only then remove the bypass.
Closing it first strands the next release's Phase 2: the App can't push the
back-merge, and there is no human bypass left to push it manually.

## Recovery

For a half-finished release, work through the `releasing` skill's Manual recovery
section — covering a stuck back-merge, an already-open `develop`→`main` PR, and a
validation gate failure — rather than improvising a fix.
