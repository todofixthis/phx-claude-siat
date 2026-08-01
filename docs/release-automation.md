# Release automation — one-time setup

[`.github/workflows/release.yml`](../.github/workflows/release.yml) finishes each
release — tag, GitHub Release, back-merge to `develop` — as a GitHub App, so the
back-merge push isn't blocked by the branch protection it must satisfy. That needs the
App, its secrets, and the rulesets below in place first. Keep this file and the
workflow in sync when either changes.

## Setup

1. Create a GitHub App with the repository permission **Contents: write** only, and no
   others. Install it on `todofixthis/phx-claude-siat`. Note the App ID and generate a
   private key.
2. Add repository Actions secrets `RELEASE_APP_ID` and `RELEASE_APP_PRIVATE_KEY` from
   step 1.
3. Split the **Trunk** ruleset into two:
   - **Trunk–develop** — target `~DEFAULT_BRANCH`; add the App as a bypass actor, mode
     `always`.
   - **Trunk–main** — target `refs/heads/main`; no bypass actor.

   Both keep the existing rules: `deletion`, `non_fast_forward`, `pull_request`
   (merge-only), `required_status_checks: gate`.
4. Add a **tag ruleset** on `refs/tags/*`: `non_fast_forward` and `deletion`. No
   `required_signatures` — release tags are unsigned.

## Rollout order

The workflow first fires on the merge that lands it on `main`, so both secrets must
exist before that release merges.

Keep the temporary Admin bypass on `develop` until the App is installed and one release
has completed all the way through the workflow. Removing it earlier strands the next
release: the App can't push the back-merge, and no human bypass is left to push it by
hand.
