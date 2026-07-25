# Release automation (Phase 2) — design

**Date:** 2026-07-25 · **Status:** approved, not yet built

## Problem

The `releasing` skill runs a two-phase gitflow release. Phase 1 (prepare) opens the
`develop`→`main` PR; Phase 2 (publish) tags the merge commit, publishes the GitHub
Release, closes referenced issues, and back-merges `main`→`develop`. The **Trunk**
branch ruleset now requires every change to `develop` and `main` to go through a PR
with a passing `gate` check, so the Phase 2 back-merge — a direct push to `develop` —
is blocked. 1.3.0 shipped under a temporary Admin bypass.

Goal: move Phase 2 into CI so a release finishes automatically when the maintainer
merges the release PR, with no standing human/agent bypass on `develop`.

## Decisions

Settled during brainstorming; rationale kept brief because these are choices, not
durable guidance (an ADR would over-serve a transient design).

- **CI owns all of Phase 2**, triggered by the merge. The skill shrinks to Phase 1.
- **Trigger on `push: branches: [main]`, not `pull_request: closed`.** A push to `main`
  happens only via a merged, protected PR; forks cannot cause it; `github.sha` is the
  merge commit directly. Strictly smaller attack surface than a PR-payload trigger, for
  equal function — the release notes come from the CHANGELOG, not the PR object.
- **Auth via a GitHub App**, `Contents: write` only, added as a bypass actor scoped to
  `develop`. Not `GITHUB_TOKEN` (not a bypass actor); not a PAT/deploy key (long-lived,
  coarser than a per-run installation token).
- **No tag signing in CI.** A signing key in Actions secrets is a standing liability
  exposed to every job step, and there is no key-free path to a "Verified" *tag*
  (GitHub web-flow signs commits it creates, not tag objects created via the API).
  Release tags are unsigned but made immutable by a tag ruleset; provenance comes from
  the protected tag plus the Actions audit log.
- **No issue auto-closing in CI.** Issue references are rare here (notes cite ADRs), and
  the `#NNN` extractor risks auto-closing the wrong issue. Dropping it removes the need
  for `Issues: write`, collapsing the App to `Contents: write` only. The rare release
  that references issues is closed by hand.

## Architecture

### Credentials

One GitHub App, `Contents: write` only. Secrets: `APP_ID`, `APP_PRIVATE_KEY`. No GPG
key, no `Issues`/`Pull requests` scope.

### Rulesets (maintainer-managed)

- Split **Trunk** into **Trunk–develop** (targets `~DEFAULT_BRANCH`; bypass actor: the
  App, mode `always`) and **Trunk–main** (targets `refs/heads/main`; no bypass —
  `main` stays push-proof for everyone). Bypass is per-ruleset, so scoping the App to
  `develop` requires the split.
- New **tag ruleset** on `refs/tags/*`: `non_fast_forward` + `deletion` (immutable
  tags). No `required_signatures` — signing is not enforced.
- A scheduled workflow asserts Trunk–develop and Trunk–main stay identical except on
  bypass actors, catching drift between the two.

The App bypass is total on `develop`, not scoped to the back-merge: a compromised App
key could push unchecked commits there. Acceptable because the App only ever pushes an
already-reviewed back-merge, but the blast radius is stated, not hidden.

## Workflow — `.github/workflows/release.yml`

- **Trigger:** `push: branches: [main]`.
- **Concurrency:** a group serialises release runs, so a second `main` push cannot race
  a back-merge in flight.
- **Permissions:** workflow token `contents: read`; every write uses the App token,
  revoked at job end, with secrets scoped to the steps that need them.

Steps, each independently idempotent so the job is safe to re-run to completion from any
point (never short-circuiting on the first artefact found):

1. Mint the App token; checkout `main` at `github.sha` with full history; read the
   version from `.claude-plugin/plugin.json`.
2. **Guard:** if tag `X.Y.Z` already exists, exit success — this push is a hotfix or a
   re-run, not a new release.
3. Assert the top `## X.Y.Z` CHANGELOG heading matches `plugin.json`'s version; fail
   otherwise, rather than shipping stale notes.
4. Create an unsigned annotated tag `X.Y.Z` on `github.sha` and push it — skip if the
   tag is already present.
5. Publish the GitHub Release with notes sliced from the top CHANGELOG section — skip if
   the Release already exists.
6. Back-merge: `git merge --no-edit origin/main` into `develop` and push — skip if
   `origin/main` is already an ancestor of `origin/develop`. A real merge (not
   `--ff-only`) so a `develop` that advanced since the PR was cut still merges.
7. Verify on the *remote*: `origin/main` is an ancestor of `origin/develop`.

Any step failing fails the job (a red-X and GitHub's failure email). Because the job is
idempotent, the maintainer fixes the cause and re-runs.

## Tested helper

A `scripts/ci/` Python helper, unit-tested per the repo's `validate_manifests.py`
pattern, does the CHANGELOG top-slice and the version-match assertion (step 3), keeping
the fragile parsing out of inline shell.

## Slimmed `releasing` skill

- Phase 1 only: validation gate → notes → version → changelog → bump → commit → open
  PR → "merge it; CI finishes the release."
- Remove phase-detection and every Phase 2 step, plus the tag-signing default.
- Add a line to confirm the release workflow went green after merging.
- Replace "run Phase 2 manually" with a **state-checklist recovery note**: tag present?
  Release present? `origin/main` ancestor of `origin/develop`? — do only the missing
  steps. A hand-run recovery tag is signed (local `tag.gpgsign`); a mix of signed and
  unsigned release tags is fine, since signing is unenforced.

## Testing

A release workflow cannot be RED/GREEN-tested like a skill. Plan:

- Unit-test the CHANGELOG helper.
- Validate the workflow via a `workflow_dispatch` dry-run that does everything except
  push and publish.
- First real end-to-end on 1.4.0 with the maintainer watching and manual Phase 2 as the
  safety net.

## Maintainer setup (one-time)

1. Create the GitHub App (`Contents: write` only), install it on the repo, note the App
   ID, generate a private key.
2. Add `APP_ID` and `APP_PRIVATE_KEY` as Actions secrets.
3. Split **Trunk** into Trunk–develop (App as bypass actor) and Trunk–main (no bypass).
4. Add the `refs/tags/*` ruleset (`non_fast_forward` + `deletion`).
5. Cut-over (see below), then remove the temporary Admin bypass.

## Rollout sequencing

Until the App is live, the next release still needs a way to back-merge to `develop`.
Keep an interim bypass available until the App is built, installed, and its first
release has succeeded; only then remove the temporary Admin bypass. Closing the bypass
before the App works strands the next release's Phase 2.

## Out of scope

Collapsing the Phase 1 validation gate into a preflight script is orthogonal ergonomics,
deferred to a later change.
