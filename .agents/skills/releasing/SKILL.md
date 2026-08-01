---
name: releasing
description: Use when cutting a release of this plugin — taking the changes on `develop` to a new version on `main`.
---

# Releasing

Drive Phase 1 of the gitflow release: open the `develop`→`main` PR. When a human merges
it, the `release` GitHub Actions workflow finishes the release — tag, GitHub Release,
back-merge — as the App. The release notes come from `phx:writing-release-notes`; this
skill owns the version number and every piece of version metadata that skill leaves to
its caller.

**Announce at start:** "I'm using the releasing skill to cut the release."

**The one hard rule: never skip the validation gate.** It runs before Phase 1 mutates
anything, and any failure stops the release. Skipping it because the tree "looks clean"
or the change is "small" is still skipping it — don't.

## Preconditions

`phx:writing-release-notes` and `phx:creative-commits` must resolve. Both are plugin
skills (`phx:` prefix); this skill is a project skill (unprefixed). Because
`writing-release-notes` is unpublished until this process first ships it, run in this
repo launched with `--plugin-dir ./` so it resolves.

## Inputs (both optional)

- **`version`** — an explicit new version that overrides the computed one (the semver
  level from `writing-release-notes` then becomes advisory only).
- **`model`** — passed through to `phx:writing-release-notes` for its gather subagents
  (cost control).

## Model of the flow

`main` is the stable branch the marketplace serves (ADR 001's default branch); `develop`
is integration. A release is the `develop`→`main` PR. The unreleased range is always
`base = origin/main`, `HEAD = develop` — tag-independent, so it works even with no tags
yet. Tags are a version→commit record, not the range source.

**Resolve `main` as `origin/main` after fetching — never the local `main` branch.** This
flow never checks out, builds from, or commits to `main`; it only reads it as a reference
point, so local `main` sits wherever an earlier release left it. A stale local `main`
fails silently in both directions: the divergence check passes when it should fail, and
the notes range widens back over released commits and re-reports them as new. Reading
`origin/main` also means no gate check ever checks out or updates a local branch, and it
works in fresh clones and worktrees, where a local `main` may not exist at all and the
check would error outright rather than pass. Leave local `main` alone — it is unused, not
broken.

## Phase 1 — prepare (on `develop`)

1. **Run the validation gate (below). Stop on any failure** — before anything mutates.
2. Run `phx:writing-release-notes` with `base = origin/main` (pass `model` through) → the
   notes and an advisory semver level.
3. **Compute the new version and confirm.** Read the version in `.claude-plugin/plugin.json`
   and apply the
   level: patch bumps Z; minor bumps Y and resets Z to 0; major bumps X and resets Y and
   Z to 0. The `version` input overrides. (The `0.y.z` carve-out never applies — the
   plugin is past `1.0.0`.) If the level is absent or ambiguous, require an explicit
   `version` rather than guessing. Now evaluate the gate's version check (greater than
   `origin/main`'s, not already tagged) against this chosen number — still before any
   mutation.
   Confirm with the maintainer **both** the version **and** that the notes contain
   nothing embargoed or security-sensitive that `writing-release-notes` flagged — before
   anything is placed or published.
4. **Prepend the entry to `CHANGELOG.md`** (Keep-a-Changelog; create the file if absent,
   matching the `writing-release-notes` template including its Breaking-changes block):
   the generated notes go under a heading of the new version + today's date. There is no
   `[Unreleased]` section — the changelog records released versions only (ADR 002).
5. **Bump `plugin.json`** to the new version — and **only** there; the marketplace entry
   carries no version (ADR 001).
6. **Commit** the prep (`CHANGELOG.md` + `plugin.json`) via `phx:creative-commits` on
   `develop`; push, and verify the push succeeded before continuing.
7. **Open the PR** `develop`→`main` with the notes as the body
   (`gh pr create --base main --head develop`). If an open `develop`→`main` PR already
   exists (a prior aborted run), update its body rather than creating a duplicate. Tell
   the maintainer to **merge via a merge commit, not squash or rebase** — a merge commit
   keeps `develop`'s tip a parent of `main`, so the CI back-merge carries no content; a
   squash or rebase replays the work under new SHAs and the back-merge then conflicts.
   Report the PR URL and stop.

## After merge — CI publishes

Merging the release PR triggers `.github/workflows/release.yml`, which as the App tags
the merge commit `X.Y.Z` (unsigned annotated), publishes the GitHub Release from the
CHANGELOG top entry, and back-merges `main`→`develop`. The skill's work ends at Phase 1;
read the run's outcome yourself rather than asking the maintainer:
`gh run list --workflow=Release --branch main --limit 1` reports the conclusion, and is
the whole check once the run has finished.

While one is still going, bound the wait rather than watching it open-endedly — the job
usually takes under a minute, but a queued runner can stall indefinitely and the default
watch prints every step of every poll:

```bash
timeout 300 gh run watch <id> --compact --exit-status
```

`--compact` drops all but the relevant and failed steps, `--exit-status` makes a failed
run a non-zero exit, and `timeout` caps the wait. Read the exit code rather than the
output: `0` succeeded, `124` means it is still running at the cap (report that and stop
— don't re-watch), anything else is a failed run to triage below.

### If the run fails

**Triage before touching anything.** Read the failing step —
`gh run view <id> --log-failed` — and classify it:

- **Transient** (network, a GitHub API blip, a token that failed to mint): re-run with
  `gh run rerun <id> --failed`. Every step self-guards, so the re-run redoes only what
  is missing.
- **Anything else** — a version mismatch, a back-merge conflict, a rejected push —
  report the failing step to the maintainer and stop. The pushes below need the App or a
  `develop` bypass you do not have, so doing them by hand mostly fails again, more
  confusingly.

Once the cause is fixed, re-running the workflow is the way back. The by-hand path is
for when it cannot run at all:

- **Tag missing?** `git tag -a X.Y.Z -m "Release X.Y.Z" <merge-commit-oid>` then
  `git push origin X.Y.Z`. Read the merge commit from
  `gh pr view <N> --json mergeCommit`. A hand-cut tag is signed (local `tag.gpgsign`);
  a mix of signed and unsigned release tags is fine, since signing is unenforced.
- **Release missing?** `gh release create X.Y.Z --notes-file notes.md`, notes from
  `python3 scripts/ci/release_notes.py --out notes.md`.
- **Back-merge missing?** From `develop`: `git fetch origin && git merge --no-edit origin/main && git push`.
  Verify on the remote:
  `git fetch origin && git merge-base --is-ancestor origin/main origin/develop`.
- **Issues to close?** Rare here (notes cite ADRs). Close any `#NNN` the notes reference
  by hand with a link to the Release.

## Validation gate

Run before Phase 1 mutates anything; **any** failure stops the release. Start with
`git fetch origin --tags` — every check below reads `origin/main`, and the fetch is the
only way it is current:

- on `develop`, with a clean working tree;
- local `develop` matches `origin/develop`. Fast-forward it if it is merely behind —
  someone pushed from elsewhere — and stop if the two have diverged. Left unchecked, a
  stale local `develop` silently narrows the notes range, so the CHANGELOG entry is
  written missing those commits and the step 6 push then fails *after* the entry is
  committed;
- `origin/main` is an ancestor of `develop`
  (`git merge-base --is-ancestor origin/main develop`) **and** `develop` has commits
  beyond `origin/main`. The usual cause of failure is a failed CI back-merge; the
  other is a hotfix committed to `main` that never came back. Either way, stop and tell
  the maintainer to merge `origin/main` into `develop` first. If `develop` has no new
  commits, there is nothing to release;
- `gh auth status` succeeds and a GitHub remote exists;
- the manifests and skill frontmatter validate —
  `python3 scripts/ci/validate_manifests.py`, checking the exit code explicitly. This is
  the same script CI runs on every PR, so the rules — valid JSON, the ADR 001 no-`version`
  invariant, skill frontmatter, declared tooling gated — live in one place and cannot
  drift from what CI enforces (ADR 005). Running it here fails *before* step 4 mutates
  anything, rather than on the release PR after the CHANGELOG is already committed;
- the chosen version is greater than `origin/main`'s current version and not already
  tagged. (The number isn't known until step 3, so this check is evaluated there — still
  before the first mutation in step 4.)
- the `creative-commits` package tests pass —
  `uv run --project skills/creative-commits pytest` — checking the exit code explicitly.
  CI is not a substitute here: its `python` job is path-filtered, so a release touching
  nothing under `skills/creative-commits` skips it and `gate` passes the skip. This run is
  unconditional. Nor does CI check the version bump above — `validate_manifests.py` has no
  git access and checks semver *shape* only, so an unbumped or already-tagged release PR
  goes green. Both bullets look redundant with CI and are not.

## Defaults

- **Tag format:** `X.Y.Z`, no `v` prefix — matches the `plugin.json` version string. CI
  creates an **unsigned** annotated tag (`git tag -a X.Y.Z -m "Release X.Y.Z"`); a
  `refs/tags/*` ruleset makes release tags immutable (`non_fast_forward` + `deletion`)
  rather than signed. A hand-cut recovery tag is signed by local `tag.gpgsign`, which is
  harmless since signing is unenforced.
- **CHANGELOG.md:** repo root; released versions only; each entry generated fresh at
  release; no `[Unreleased]` section (ADR 002).

## Edge cases

- **No new commits on `develop`:** nothing to release; stop.
- **`origin/main` diverged from `develop`:** stop; the maintainer merges `origin/main`
  into `develop` first (keeps `base = origin/main` an ancestor of `develop` for the notes
  range). Usually a failed CI back-merge, not a hotfix.
- **Chosen version already tagged / not greater than `origin/main`'s:** stop with an
  error.
- **Open `develop`→`main` PR already exists:** reuse it (update the body), don't duplicate.
- **Not on `develop` / dirty tree / `gh` unavailable:** stop before any commit.
