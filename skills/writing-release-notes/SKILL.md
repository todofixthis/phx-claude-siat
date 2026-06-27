---
name: writing-release-notes
description: Use when preparing a release and you need release notes or a changelog entry for a new version.
---

# Writing Release Notes

Investigate *what* changed and *why* across a release range, then produce grouped,
audience-checked release notes plus an advisory semver level. **Your only deliverable
is the notes text and the recommended level** — writing them to a `CHANGELOG.md`,
publishing a GitHub Release, choosing the version number, and tagging are the caller's
job, not yours.

**Announce at start:** "I'm using the writing-release-notes skill to draft the release notes."

## Arguments

All optional:

- **`base`** — the comparison base: any identifier `git rev-parse` accepts (a tag,
  commit, or branch). The range is `<base>..HEAD`. Omit only for a first release.
- **`model`** — model for the gather subagents; default the cheapest capable model
  (e.g. Haiku).
- **`path`** — restrict the range, diff, and PR discovery to a subtree (monorepos).

## Procedure

### 1. Resolve the range

With a `base`, it MUST satisfy both `git rev-parse --verify <base>` and
`git merge-base --is-ancestor <base> HEAD`. If either fails, **stop and report the
error** — do not guess another base. The range is `<base>..HEAD` (scoped by `path`).
Without a `base`, this is a first release: review the full history. State the resolved
range before continuing.

### 2. Gather (parallel subagents on the cheap `model`)

Dispatch three subagents, each returning a structured summary, run on the cheap
`model` to save context and cost:

- **What:** read `git diff --stat <range>` to map changed areas, then read full diffs
  per area in bounded chunks — fan out per area if the diffstat is large, so the cheap
  model's context isn't exceeded. Summarise by area.
- **Why:** parse `#NNN` references from `git log <range> --format=%s%n%b` (squash
  subjects `(#123)`, merge commits `Merge pull request #123`, body trailers like
  `Closes #45`); de-duplicate, then `gh pr view <N>` / `gh issue view <N>`. **Recurse**
  into `#NNN` references found in the fetched PR/issue bodies (visited set, bounded
  depth) — a PR often cites an issue no commit mentions. **Beware cross-repo refs:**
  dependency-bump PRs cite the *upstream* project's numbers; only attribute references
  that belong to this repo.
- **Significant-but-uncovered:** read commit message bodies for notable changes the
  diff and PR/issue summaries don't explain.

Normalise non-English source material to the notes' language.

### 3. Sense-check

Reconcile the three summaries yourself. Resolve contradictions and investigate
anything that looks off before trusting it. Don't silently drop a change a gather
subagent surfaced; if you reclassify or exclude one, record why, and when unsure keep
it. Err toward inclusion.

### 4. Draft

Write to the template below: high-level, grouped logically. Flag security-sensitive or
embargoed material (CVE details, undisclosed advisories) for human decision rather than
publishing it unreviewed.

**Breaking changes — flag, don't dismiss.** "Breaking" is broader than runtime API
breaks. Treat all of these as breaking: changed or removed public API or behaviour;
**type-surface** changes (altered public signatures, or removed base classes/protocols
that typed consumers may depend on); **build- or contributor-workflow** changes (renamed
dependency groups, changed install/build/test commands); and **dropped runtime or
version support**. When a change is plausibly breaking, or a commit/PR/issue signals it
— even if you can argue it still works at runtime — put it under **Breaking changes**
with migration steps and let the human decide. Do not reason a flagged break out of the
notes.

### 5. Audience-surrogate review

Dispatch a subagent **on the main model** (a reasoning task, not a cheap one) that
reads the draft as the release's audience and critiques it for clarity, gaps, and
jargon. It must also check **breaking-change completeness**: would a consumer be caught
out by a change that isn't under Breaking changes — an altered contract, type surface,
build/test workflow, or dropped version support? Anything missing or under-called gets
flagged. Infer the audience from the README / package manifest / repo description;
default to "a downstream developer consuming this project"; ask if genuinely ambiguous.
Address the feedback.

### 6. Quality pass

Remove repetition, regroup related items, and tighten without losing clarity. Then,
**only if the project uses NZ English** (per its stated convention or agent
instructions), run `phx:nz-english`. Other locales — including US English — get no
spelling pass.

### 7. Recommend the semver level (advisory)

Major for breaking changes, minor for backwards-compatible additions, patch for fixes
only — **except under `0.y.z`, where breaking changes are a minor bump**. For a first
release, label it the initial release and give no recommendation. Recommend the
*level* only; never compute or write the version number.

### 8. Output

Present the finished notes and the recommended level. Do not persist them: writing to
a changelog, choosing a version heading, publishing a Release, and tagging are the
caller's responsibility.

## Template

Keep-a-Changelog sections, emitted only when non-empty: **Added, Changed, Deprecated,
Removed, Fixed, Security.** Above them, a dedicated **Breaking changes** block listing
each breaking change with its migration steps. (This block is a deliberate, opinionated
deviation from Keep-a-Changelog's `**breaking**` prefix.) Entries are high-level and
grouped — never a per-commit dump. The caller adds any version heading.

## Edge cases

- **First release (no `base`):** review the full history; initial-release framing; no
  semver recommendation.
- **`gh` unavailable or unauthenticated, or a non-GitHub remote:** skip the PR/issue
  gather; rely on the diff and commit bodies; **state what you skipped** — never imply
  coverage a missing source could not provide.
- **`base` unresolvable or not an ancestor of `HEAD`:** stop with an error.
- **Empty range (no changes since `base`):** report that there is nothing to release
  and stop.
