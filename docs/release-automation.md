# Release automation — one-time setup

[`.github/workflows/release.yml`](../.github/workflows/release.yml) finishes each
release — tag, GitHub Release, back-merge to `develop` — as a GitHub App, so the
back-merge push isn't blocked by the branch protection it must satisfy. That needs the
App, its secrets, and the rulesets below in place first. Keep this file and the
workflow in sync when either changes.

## Setup

1. Create a GitHub App with the repository permission **Contents: write** only, and no
   others. Install it on `todofixthis/phx-claude-siat`. Note the **Client ID** — not the
   App ID, which the action's deprecated `app-id` input wanted — and generate a private
   key.
2. Add repository Actions secrets `RELEASE_APP_CLIENT_ID` and `RELEASE_APP_PRIVATE_KEY`
   from step 1.
3. Split the **Trunk** ruleset into two:
   - **trunk-develop** — target `refs/heads/develop`, named literally rather than
     `~DEFAULT_BRANCH` so it keeps targeting the same branch if the default changes; add
     the App as a bypass actor, mode `always`, alongside the standing Admin bypass
     ([ADR 009](adr/009-keep-a-standing-develop-bypass.md)).
   - **trunk-main** — target `refs/heads/main`; no bypass actor.

   Both keep the existing rules: `deletion`, `non_fast_forward`, `pull_request`
   (merge-only), and `required_status_checks: gate` with
   `strict_required_status_checks_policy` on, so a branch must be current with its base
   before it can merge.
4. Add a **tag ruleset** on `refs/tags/*`: `non_fast_forward` and `deletion`. No
   `required_signatures` — release tags are unsigned.

## Rollout order

The workflow first fires on the merge that lands it on `main`, so both secrets must
exist before that release merges.

## Porting this to a project that can't keep a bypass

The Admin bypass on `develop` is the one piece of this setup that assumes a solo
maintainer: the releasing skill commits the CHANGELOG entry and version bump directly to
`develop`, and mid-release corrections go the same way. Everything else ports unchanged.

Where a standing bypass isn't acceptable, cut a `release/X.Y.Z` branch from `develop`,
commit the preparation there, and merge it back by pull request — so nothing writes to
`develop` directly and the App's bypass is the only one left. The cost is three gated
pull requests per release instead of one, and a second merge order to get right. ADR 009
records why that trade is wrong here and would be right with more than one committer.
