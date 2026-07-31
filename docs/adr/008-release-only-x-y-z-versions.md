---
status: Accepted
date: 2026-07-28
tags: [changelog, ci, marketplace, plugin, pre-release, releases, semver, validation, versioning]
summary: Release only X.Y.Z versions — no pre-release suffixes or build metadata — from one shared pattern, failing loudly at the pull-request gate rather than after the merge to main; revisit if the plugin marketplace gains a pre-release or channel concept.
---

# 008: Release only X.Y.Z versions

## Context

The marketplace serves whatever `main` holds ([ADR 001][]), and has no notion of a
channel: every installer resolves the same entry, so anything on `main` is the current
release for everyone. There is nowhere for a `1.4.0-rc.1` to sit and be reachable only by
people who asked for it.

Three things nonetheless take a position on version shape, and as first written they
disagreed. [`validate_manifests.py`][] matched the full semver grammar, so a pre-release
version in `plugin.json` passed the pull-request gate. [`release_notes.py`][], added
later, matched `X.Y.Z` only — and a heading it did not match was simply skipped, so a
`## 1.4.0-rc.1 - …` entry fell through to the release below it. The [`releasing`][]
skill's bump rules assume three numbers throughout, but they are prose: nothing checks
them.

The changelog heading is where this bites, because [ADR 002][] has each entry written
fresh at release time — so the heading is authored by the same run that must then publish
under it.

## Options

### Option 1: Do nothing

Leave each of the three independently opinionated.

**Pros:** No change.
**Cons:** A pre-release version clears the gate, then fails — or misbehaves — later in a
process that has already merged to `main`.
**Risks:** The skipped-heading path is the dangerous one: the notes silently become the
*previous* entry's, caught only by the version-match assertion standing between a
mismatched heading and the wrong notes going out under a release tag.

### Option 2: Restrict to `X.Y.Z` from one shared pattern, and fail loudly (Accepted)

Define the shape once, assert it in both scripts, and make the notes extractor treat a
version-shaped heading it cannot release as an error rather than a miss.

**Pros:** One definition, so the two scripts cannot drift; the pull-request gate is where
a bad version stops.
**Cons:** Publishing a release candidate needs this decision reopened first.
**Risks:** The loud failure reaches only headings that are well formed apart from the
version. A heading malformed in some other way still matches nothing and is skipped
silently, exactly as before.

### Option 3: Support pre-releases end to end

Widen the pattern and extend the skill's bump rules to `rc.1` → `rc.2` → final.

**Pros:** Release candidates become expressible.
**Cons:** A grammar considerably harder than three numbers to assert, and bump rules with
no obvious stopping point.
**Risks:** The work buys nothing until distribution can tell a candidate from a release.
Merging `1.4.0-rc.1` to `main` ships it to every user as the current version — the
capability appears to work while doing the opposite of what it promises.

## Decision

Restrict releases to `X.Y.Z`. The constraint is not stylistic: pre-releases are
unshippable here because the marketplace cannot serve one selectively, so accepting the
syntax would only admit versions the release flow must then refuse. Build metadata goes
on its own terms — it never identifies a distinct release, so it has no business in a
changelog heading however pre-releases are handled.

**Revisit if** the plugin marketplace gains a pre-release or channel concept, or a release
otherwise needs to reach a subset of users before everyone. That is an upstream change
nobody here watches for, so the error messages carry the pointer: whoever first tries a
pre-release version is told which decision to reopen.

## Consequences

Both halves of the check now run on the pull request. `validate_manifests.py` asserts
`plugin.json`'s shape, and the `manifests` job in [`pr.yml`][] runs `release_notes.py`
against the real `CHANGELOG.md` — for which `CHANGELOG.md` had to join that job's path
filter. Without that second run, the loud failure would first fire in the release
workflow, after the merge to `main`, where fixing it costs another PR to `main`.

The shape is asserted mechanically in two places, both reading [`versions.py`][]; the
`releasing` skill's bump rules are prose that assumes it. Changing the shape means
changing that module, the skill's rules, the tests pinning the behaviour, the two error
messages that spell the rule out in words, and this ADR.
The release workflow needs no separate check: it takes the version from
`release_notes.py`'s output rather than reading `plugin.json` itself, so nothing
unreleasable can reach a `git tag` — which matters, because the `refs/tags/*` ruleset
makes a tag immutable once pushed.

One gap remains by design. The loud failure fires on headings that are well formed apart
from the version; a malformed heading (`## 1.4.0-rc.1 - 22 July 2026`) matches no pattern
and is still skipped, caught downstream by the version-match assertion rather than by a
message naming the problem.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 002]: 002-generate-changelog-at-release.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`versions.py`]: ../../scripts/ci/versions.py
