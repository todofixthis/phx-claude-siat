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

**Classify every entry by audience first: user-facing or maintainer-facing.**
User-facing changes affect someone *consuming* the project (installing it, calling its
API, invoking its skills/commands). Maintainer-facing changes affect someone
*contributing to* the project (its build, tests, contributor workflow, internal
tooling, or repo-local dev-environment setup) without changing what a consumer
installs or calls. A change touching both gets one entry per affected audience — don't
force a single framing. When genuinely unclear which audience a change belongs to,
default to user-facing (the more visible, harder-to-miss placement).

Write to the template below: high-level, grouped logically within each audience. Flag
security-sensitive or embargoed material (CVE details, undisclosed advisories) for
human decision rather than publishing it unreviewed.

**Breaking changes — flag, don't dismiss.** "Breaking" is broader than runtime API
breaks, and applies independently within *each* audience. The test: **if the consumer
or contributor does nothing differently, does anything — not just compile-time or
runtime behaviour — end up broken, stale, or silently out of sync?** That covers
changed or removed public API or behaviour; **type-surface** changes (altered public
signatures, or removed base classes/protocols that typed consumers may depend on);
**build- or contributor-workflow** changes (renamed dependency groups, changed
install/build/test commands, a new opt-in step like a hook that must be activated or
its output silently goes stale); and **dropped runtime or version support**. When a
change is plausibly breaking under this test, or a commit/PR/issue signals it — even if
you can argue it still works at runtime — put it under that audience's **Breaking
changes** with migration steps and let the human decide. Do not reason a flagged break
out of the notes.

### 5. Audience-surrogate review

Dispatch one subagent **on the main model** (a reasoning task, not a cheap one) per
**non-empty** audience block from step 4, each reading only that block and critiquing
it for clarity, gaps, and jargon from that audience's perspective:

- **User block reviewer:** infer the specific user audience from the README / package
  manifest / repo description; default to "a downstream developer consuming this
  project"; ask if genuinely ambiguous.
- **Maintainer block reviewer:** read as "a contributor to this project."

Each reviewer must also check **breaking-change completeness** for its block: would
someone in that audience be caught out by a change that isn't under that block's
Breaking changes — an altered contract, type surface, build/test/contributor workflow,
or dropped version support? Anything missing, under-called, or misclassified into the
wrong audience gets flagged. Address the feedback from both reviewers before continuing.

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

Two top-level audience blocks, **each emitted only when it has content**: a heading for
users (e.g. "For \<project\> users") and one for maintainers (e.g. "For contributors").
Within each block, Keep-a-Changelog sections, emitted only when non-empty: **Added,
Changed, Deprecated, Removed, Fixed, Security.** Above those, a dedicated **Breaking
changes** block listing that audience's breaking changes with migration steps. (This
block is a deliberate, opinionated deviation from Keep-a-Changelog's `**breaking**`
prefix.) A single-audience release omits the other block entirely rather than emitting
it empty. Entries are high-level and grouped — never a per-commit dump. The caller adds
any version heading.

## Edge cases

- **First release (no `base`):** review the full history; initial-release framing; no
  semver recommendation.
- **`gh` unavailable or unauthenticated:** likely unintentional — **stop and tell the
  human**, rather than silently degrading coverage by skipping the PR/issue gather.
  Proceed without it only if the human explicitly confirms.
- **Non-GitHub remote:** there is nothing for `gh` to fetch — skip the PR/issue gather,
  rely on the diff and commit bodies, and **state what you skipped** in the output.
- **`base` unresolvable or not an ancestor of `HEAD`:** stop with an error.
- **Empty range (no changes since `base`):** report that there is nothing to release
  and stop.
