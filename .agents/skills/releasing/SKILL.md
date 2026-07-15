---
name: releasing
description: Use when cutting a release of this plugin — taking the changes on `develop` to a new version on `main`.
---

# Releasing

Drive the gitflow release of the phx plugin: open the `develop`→`main` PR (Phase 1),
then — after a human merges it — tag the merge commit and publish the GitHub Release
(Phase 2). The release notes come from `phx:writing-release-notes`; this skill owns the
version number and every piece of version metadata that skill leaves to its caller.

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

## Phase detection

Invoked once per phase; decide which by querying the release PR:

```bash
gh pr list --base main --head develop --state all --json number,state,mergeCommit
```

- **No open or merged PR** (none at all, or only a closed-unmerged one from an aborted
  run) → Phase 1 (prepare).
- **An open PR** → report it and stop; wait for the maintainer to merge.
- **A merged PR whose version is not yet tagged** → Phase 2 (publish). Prior releases
  leave merged **and** tagged PRs behind, so after `git fetch --tags` pick the most
  recent merged `develop`→`main` PR whose version has no matching tag — that one is this
  release; if every merged PR is already tagged, there is nothing to publish.

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
   keeps `develop`'s tip as a parent of `main`, so the two branches share history and the
   step 11 back-merge carries no content. A squash or rebase merge replays the work onto
   `main` under new SHAs, so `develop`'s commits never become ancestors of `main` and the
   back-merge conflicts against its own duplicated changes. Report the PR URL and stop —
   the maintainer reviews and merges.

## Phase 2 — publish (after the PR is merged to `main`)

8. Read the merged PR's merge commit (`gh pr view <N> --json mergeCommit`) and tag
   `mergeCommit.oid` as `X.Y.Z` — **not** `main` HEAD and not "the merge commit" by name,
   either of which a squash/rebase merge or a later commit would get wrong. Push the tag.
9. Publish the GitHub Release for that tag with the same notes
   (`gh release create X.Y.Z`). No artefacts, checksums, or signing.
10. **Close referenced issues.** Extract every `#NNN` reference from the published
    notes and close each with a comment linking to the release
    (`gh issue close NNN --comment "Implemented in [X.Y.Z](<release URL>)."`). Skip
    references that don't belong to this repo (e.g. a dependency-bump entry citing an
    upstream project's issue number).
11. **Back-merge `main` into `develop`** — the release is not finished without it:
    `git fetch origin && git merge --no-edit origin/main && git push` from `develop`.
    Merging the PR puts a merge commit on `main` that `develop` does not have, so
    `origin/main` stops being an ancestor of `develop` the moment the PR lands; this
    step is what restores that, and the *next* release's gate hard-fails until it is
    done. It carries no content — the release merge commit's tree already matches
    `develop` — so expect an empty diff either way, but note it fast-forwards (creating
    no merge commit) if `develop` has not moved since the PR was opened, and only
    creates one if it has. A conflict means the PR was squashed or rebased rather than
    merged: resolve in favour of `develop` and commit, since the gate only needs
    `origin/main` reachable from `develop`.

## Validation gate

Run before Phase 1 mutates anything; **any** failure stops the release. Start with
`git fetch origin --tags` — every check below reads `origin/main`, and the fetch is the
only way it is current:

- on `develop`, with a clean working tree;
- `origin/main` is an ancestor of `develop`
  (`git merge-base --is-ancestor origin/main develop`) **and** `develop` has commits
  beyond `origin/main`. The usual cause of failure is a skipped step 11 back-merge; the
  other is a hotfix committed to `main` that never came back. Either way, stop and tell
  the maintainer to merge `origin/main` into `develop` first. If `develop` has no new
  commits, there is nothing to release;
- `gh auth status` succeeds and a GitHub remote exists;
- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are valid JSON;
- the marketplace plugin entry carries **no** `version` (ADR 001 invariant);
- the chosen version is greater than `origin/main`'s current version and not already
  tagged. (The number isn't known until step 3, so this check is evaluated there — still
  before the first mutation in step 4.)
- the `creative-commits` package tests pass —
  `uv run --project skills/creative-commits pytest` — checking the exit code explicitly.

## Defaults

- **Tag format:** `X.Y.Z`, no `v` prefix — matches the `plugin.json` version string.
- **CHANGELOG.md:** repo root; released versions only; each entry generated fresh at
  release; no `[Unreleased]` section (ADR 002).

## Edge cases

- **No new commits on `develop`:** nothing to release; stop.
- **`origin/main` diverged from `develop`:** stop; the maintainer merges `origin/main`
  into `develop` first (keeps `base = origin/main` an ancestor of `develop` for the notes
  range). Usually a skipped step 11, not a hotfix.
- **Chosen version already tagged / not greater than `origin/main`'s:** stop with an
  error.
- **Open `develop`→`main` PR already exists:** reuse it (update the body), don't duplicate.
- **Not on `develop` / dirty tree / `gh` unavailable:** stop before any commit.
- **Phase 2 invoked before the PR has merged:** phase detection reports the open PR and waits.
