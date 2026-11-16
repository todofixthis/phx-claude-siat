---
status: Accepted
date: 2026-07-28
scope: [.agents/skills/releasing/, scripts/ci/versions.py]
summary: Release only X.Y.Z versions — no pre-release suffixes or build metadata — from one shared pattern, failing loudly at the pull-request gate rather than after the merge to main.
revisit-when: The plugin marketplace gains a pre-release or channel concept, or a release must reach a subset of users by some mechanism other than a second catalogue entry.
---

# 008: Release only X.Y.Z versions

## Context

The marketplace serves whatever `main` holds ([ADR 010][]), and has no notion of a
channel. Every installer resolves the same entry, so anything on `main` is the current
release for everyone. A `1.4.0-rc.1` has nowhere to sit where only the people who asked
for it can reach it.

Three things still take a position on version shape, and as first written they
disagreed. [`validate_manifests.py`][] matched the full semver grammar, so a pre-release
version in `plugin.json` passed the pull-request gate. [`release_notes.py`][], added
later, matched only `X.Y.Z`, and skipped any heading it did not match. A
`## 1.4.0-rc.1 - …` entry therefore fell through to the release below it. The
[`releasing`][] skill's bump rules assume three numbers throughout, but they are prose,
and nothing checks them.

The changelog heading is where this bites. [ADR 002][] has each entry written fresh at
release time, so the run that writes the heading is the same run that must then publish
under it.

## Options

### Option 1: Do nothing

Leave each of the three with its own opinion.

**Pros:** No change.
**Cons:** A pre-release version clears the gate, then fails or misbehaves later, in a
process that has already merged to `main`.
**Risks:** The skipped heading is the dangerous path. The notes silently become the
*previous* entry's. Only the version-match assertion stands between a mismatched heading
and the wrong notes going out under a release tag.

### Option 2: Restrict to `X.Y.Z` from one shared pattern, and fail loudly (Accepted)

Define the shape once, assert it in both scripts, and make the notes extractor treat a
version-shaped heading it cannot release as an error, not a miss.

**Pros:** With one definition, the two scripts cannot drift. A bad version stops at the
pull-request gate.
**Cons:** Publishing a release candidate means reopening this decision first.
**Risks:** The loud failure reaches only headings that are well formed apart from the
version. A heading malformed in some other way still matches nothing, and the extractor
still skips it silently, exactly as before.

### Option 3: Support pre-releases end to end

Widen the pattern and extend the skill's bump rules to `rc.1` → `rc.2` → final.

**Pros:** Release candidates become expressible.
**Cons:** The grammar is much harder to assert than three numbers, and the bump rules have
no obvious stopping point.
**Risks:** The work buys nothing until distribution can tell a candidate from a release.
Merging `1.4.0-rc.1` to `main` ships it to every user as the current version. The feature
appears to work while doing the opposite of what it promises.

## Decision

Restrict releases to `X.Y.Z`. The constraint is not a matter of style. Pre-releases are
unshippable here because the marketplace cannot serve one selectively, so accepting the
syntax would only admit versions the release flow must then refuse. Build metadata goes
for its own reason. It never identifies a distinct release, so it does not belong in a
changelog heading, however pre-releases are handled.

**Revisit if** the plugin marketplace gains a pre-release or channel concept, or a release
otherwise needs to reach a subset of users before everyone. A second catalogue entry does
not count: ADR 010 raised that mechanism and [ADR 012][] then closed it. What remains is
an upstream change nobody here watches for, so the error messages carry the pointer. The
first person to try a pre-release version learns which decision to reopen.

## Consequences

Both halves of the check now run on the pull request. `validate_manifests.py` asserts
`plugin.json`'s shape. The `manifests` job in [`pr.yml`][] runs `release_notes.py`
against the real `CHANGELOG.md`, so `CHANGELOG.md` had to join that job's path filter.
Without that second run, the loud failure would fire first in the release workflow,
after the merge to `main`, where fixing it costs another PR to `main`.

Two places assert the shape mechanically, and both read [`versions.py`][]. The
`releasing` skill's bump rules are prose that assumes the same shape. To change the
shape, change that module, the skill's rules, the tests that pin the behaviour, the two
error messages that spell the rule out in words, and this ADR.
The release workflow needs no separate check. It takes the version from
`release_notes.py`'s output instead of reading `plugin.json` itself, so nothing
unreleasable can reach a `git tag`. That matters, because the `refs/tags/*` ruleset makes
a tag immutable once pushed.

One gap remains by design. The loud failure fires on headings that are well formed apart
from the version. A malformed heading (`## 1.4.0-rc.1 - 22 July 2026`) matches no pattern
and the extractor still skips it. The version-match assertion catches it downstream, but
with no message that names the problem.

[ADR 002]: 002-generate-changelog-at-release.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`versions.py`]: ../../scripts/ci/versions.py
