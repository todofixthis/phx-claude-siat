# Set up release automation

[`.github/workflows/release.yml`](../.github/workflows/release.yml) finishes each
release as a GitHub App: it tags, publishes the GitHub Release, and back-merges to
`develop`. Running as the App stops the branch protection that the back-merge push must
satisfy from blocking that push. The App, its secrets, and the rulesets below must be in
place first. When either this file or the workflow changes, update the other to match.

## Setup

1. Create a GitHub App with the repository permission **Contents: write** and no others.
   Install it on `todofixthis/phx-claude-siat`. Note its **Client ID**, not the App ID
   that the action's deprecated `app-id` input wanted. Generate a private key.
2. Add the repository Actions secrets `RELEASE_APP_CLIENT_ID` and
   `RELEASE_APP_PRIVATE_KEY`, from the values in step 1.
3. Split the **Trunk** ruleset into two:
   - **trunk-develop** targets `refs/heads/develop`. Name the branch literally, not as
     `~DEFAULT_BRANCH`, so the ruleset keeps targeting the same branch if the default
     changes. Add the App as a bypass actor, mode `always`, alongside the standing Admin
     bypass ([ADR 009](adr/009-keep-a-standing-develop-bypass.md)).
   - **trunk-main** targets `refs/heads/main`, with no bypass actor.

   Both keep the existing rules: `deletion`, `non_fast_forward`, `pull_request`
   (merge-only), and `required_status_checks: gate` with
   `strict_required_status_checks_policy` on. The strict policy means a branch must be
   current with its base before it can merge.
4. Add a **tag ruleset** on `refs/tags/*` with `non_fast_forward` and `deletion`. Leave
   out `required_signatures`, because release tags are unsigned.

## Add both secrets before the workflow reaches `main`

The workflow first runs on the merge that lands it on `main`, so both secrets must exist
before that release merges.

## Port this to a project that can't keep a bypass

The Admin bypass on `develop` is the only part of this setup that assumes a solo
maintainer. The releasing skill commits the CHANGELOG entry and the version bump straight
to `develop`, and mid-release corrections go the same way. Everything else ports
unchanged.

If a standing bypass isn't acceptable, cut a `release/X.Y.Z` branch from `develop`, commit
the preparation there, and merge it back by pull request. Then nothing writes to `develop`
directly, and the App's bypass is the only one left. The cost is three gated pull requests
per release instead of one, and a second merge order to get right. ADR 009 records why
that trade is wrong here and would be right with more than one committer.
