---
status: Accepted
date: 2026-06-27
tags: [changelog, release-notes, releases, unreleased, keep-a-changelog, single-source-of-truth]
summary: Generate each CHANGELOG entry from history at release time; do not maintain a hand-written [Unreleased] section.
---

# 002: Generate the changelog at release time, not a running [Unreleased]

## Context

We are introducing a `CHANGELOG.md` as part of the release process (the `releasing`
skill). The Keep-a-Changelog convention keeps an `[Unreleased]` section that
contributors append to as work lands. We also have the `phx:writing-release-notes`
skill, which generates release notes at release time from a range's commits, merged
PRs, linked issues, and diff, with an audience-surrogate review pass.

So a release's changelog entry can be produced two ways: maintained incrementally in
`[Unreleased]`, or generated fresh at release. One force in particular shapes the
choice: coding agents writing incremental entries tend to embed session-local,
non-portable references (e.g. "aligns with task 1's invariant", meaningless outside
that session).

## Options

### Option 1: Do nothing — maintain an `[Unreleased]` section

Follow Keep-a-Changelog as usual: contributors append to `[Unreleased]` as work lands,
and a release renames that section to the new version.

**Pros:** A human-curated place to record intent that history cannot reconstruct —
planned deprecations, embargoed or security notes, a *why* no commit or PR captures.
**Cons:** Incrementally hand-written entries accumulate non-portable, session-local
references, and the draft drifts from what actually shipped.
**Risks:** Note quality depends on every contributor writing good entries in the
moment — exactly where the non-portable cruft enters.

### Option 2: Generate each entry at release time (Accepted)

`CHANGELOG.md` records released versions only. At release, `phx:writing-release-notes`
generates the entry from the range's history, and the `releasing` skill prepends it
under the new version and date. There is no `[Unreleased]` section.

**Pros:** One source of truth — the commit/PR/issue history; the entry is
audience-facing.
**Cons:** No running draft of unreleased changes between releases; the *why* must
already live in commits/PRs/issues.
**Risks:** Generating fresh needs that history reachable at release (e.g. `gh`
available); offline, the notes fall back to commit messages alone.

### Option 3: Maintain `[Unreleased]` and also generate at release

Keep the running `[Unreleased]` draft and generate notes at release, reconciling the
two into the final entry.

**Pros:** The draft is a backstop against context lost from commits/PRs.
**Cons:** The most work, and the releaser must reconcile two sources.
**Risks:** Conflicting information at release time — the failure mode we most want to
avoid.

## Decision

Generate at release time (Option 2). The history is already the durable record and
`phx:writing-release-notes` exists to mine it, so a parallel `[Unreleased]` draft is
redundant — and the two-source reconciliation it forces (Option 3) is the worst
outcome. Generating fresh also routes every entry through the skill's
audience-surrogate review, which strips the session-local references incremental
entries (Option 1) accrue. Option 1's genuine upside — a place for intent not in the
history, like a planned deprecation or an embargoed note — is better served by a
tracking issue (which the skill already recurses into) or added by the human at
release, than by a standing draft. We accept the dependency on commit/PR/issue
hygiene, which we want regardless.

## Consequences

- `CHANGELOG.md` holds released versions only; the `releasing` skill prepends each new
  version's generated entry. No `[Unreleased]` section exists.
- "What is unreleased" is answered on demand by running `phx:writing-release-notes`
  over the unreleased range (the changes since the last release), not from a maintained
  draft.
- The *why* must live in commit, PR, and issue descriptions — weak descriptions
  degrade the generated notes — and generation depends on that history being reachable
  at release (e.g. `gh` available; offline it falls back to commit messages).
- This assumes every release runs through `releasing` + `phx:writing-release-notes`. A
  release cut by hand (e.g. an emergency hotfix) must write its changelog entry
  manually — there is no `[Unreleased]` draft to fall back on.
- `phx:writing-release-notes` is unaffected: it never placed notes or chose a version
  (the caller's job). The `releasing` skill adds the version heading and prepends the
  generated entry.
