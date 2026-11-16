---
status: Accepted
date: 2026-06-27
scope: [.agents/skills/releasing/, CHANGELOG.md, scripts/ci/release_notes.py]
summary: Generate each CHANGELOG entry from history at release time; do not maintain a hand-written [Unreleased] section.
---

# 002: Generate the changelog at release time, not a running [Unreleased]

## Context

The release process, run by the `releasing` skill, is gaining a `CHANGELOG.md`. The
Keep-a-Changelog convention keeps an `[Unreleased]` section that contributors add to as
work lands. We also have the `phx:writing-release-notes` skill. At release time it
generates notes from a range's commits, merged PRs, linked issues, and diff, and runs an
audience-surrogate review over them.

So there are two ways to produce a release's changelog entry: maintain it bit by bit in
`[Unreleased]`, or generate it fresh at release. One force shapes the choice most. Coding
agents that write entries as they go tend to embed references that mean nothing outside
their session, such as "aligns with task 1's invariant".

## Options

### Option 1: Do nothing — maintain an `[Unreleased]` section

Follow Keep-a-Changelog as usual. Contributors add to `[Unreleased]` as work lands, and a
release renames that section to the new version.

**Pros:** A human-curated place to record intent that history can't reconstruct, such as
a planned deprecation, an embargoed or security note, or a *why* that no commit or PR
captures.
**Cons:** Entries written by hand as work lands collect references that only made sense
in one session, and the draft drifts from what actually shipped.
**Risks:** Note quality depends on every contributor writing a good entry at the time,
which is exactly where the session-local references get in.

### Option 2: Generate each entry at release time (Accepted)

`CHANGELOG.md` records released versions only. At release, `phx:writing-release-notes`
generates the entry from the range's history, and the `releasing` skill prepends it under
the new version and date. There is no `[Unreleased]` section.

**Pros:** The history of commits, PRs, and issues is the one source of truth. The entry
is written for its audience.
**Cons:** There is no running draft of unreleased changes between releases. The *why*
must already be in commits, PRs, or issues.
**Risks:** Generating fresh needs that history to be reachable at release, for example
with `gh` available. Offline, the notes fall back to commit messages alone.

### Option 3: Maintain `[Unreleased]` and also generate at release

Keep the running `[Unreleased]` draft, generate notes at release, and reconcile the two
into the final entry.

**Pros:** The draft is a backstop for context that commits and PRs lost.
**Cons:** It is the most work, and the releaser must reconcile two sources.
**Risks:** The two sources disagree at release time, which is the failure we most want to
avoid.

## Decision

Generate at release time (Option 2). History is already the durable record, and
`phx:writing-release-notes` exists to mine it, so a parallel `[Unreleased]` draft is
redundant. Reconciling two sources, which Option 3 forces, is the worst outcome.
Generating fresh also sends every entry through the skill's audience-surrogate review,
which strips the session-local references that entries written as work lands (Option 1)
collect. Option 1 does have a real upside: a place for intent that isn't in the history,
like a planned deprecation or an embargoed note. A tracking issue, or the human at
release, serves that better than a standing draft, because the skill already follows
linked issues. We accept that the notes depend on good commit, PR, and issue descriptions,
which we want anyway.

## Consequences

- `CHANGELOG.md` holds released versions only. The `releasing` skill prepends each new
  version's generated entry. No `[Unreleased]` section exists.
- To see what is unreleased, run `phx:writing-release-notes` over the unreleased range
  (the changes since the last release). No maintained draft answers that.
- The *why* must live in commit, PR, and issue descriptions. Weak descriptions weaken the
  generated notes. Generation also needs that history reachable at release, for example
  with `gh` available. Offline, it falls back to commit messages.
- This assumes every release runs through `releasing` and `phx:writing-release-notes`. A
  release cut by hand, such as an emergency hotfix, must have its changelog entry written
  by hand, because there is no `[Unreleased]` draft to fall back on.
- `phx:writing-release-notes` doesn't change. It never placed notes or chose a version,
  which is the caller's job. The `releasing` skill adds the version heading and prepends
  the generated entry.
