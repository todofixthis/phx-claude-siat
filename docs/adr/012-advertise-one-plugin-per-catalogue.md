---
status: Accepted
date: 2026-08-05
tags: [catalogue, ci, manifests, marketplace, plugins, releases]
summary: Advertise exactly one marketplace entry; a second fails the manifest check, so adding a plugin means an ADR plus a release flow that names both — not a generalised flow built up front.
revisit-when: A second plugin joins the marketplace.
---

# 012: Advertise One Plugin Per Catalogue

## Context

`.claude-plugin/marketplace.json` is the catalogue a user adds before installing.
[ADR 001][] keeps it beside the plugin manifest and already records the trigger
"revisit when a second plugin joins the marketplace"; [ADR 010][] pins every entry's
`source` to this repository at `main`. [`validate_manifests.py`][] enforces both —
each entry versionless and correctly pinned, and some entry naming what
`plugin.json` declares — but nothing constrained how many entries there were.

Because of ADR 010's pin, a second entry cannot come from anywhere else: it is
another plugin released from this repository, or a duplicate of the one already
there. The rest of the repo assumes neither exists. `plugin.json` carries the single
version the release flow bumps, `CHANGELOG.md` holds one entry per release, and a
tag names one version. A second entry passes every check while leaving all of that
ambiguous: nothing would say which plugin a release was of.

## Options

### Option 1: Do nothing

**Pros:** No code to write, and a maintainer adding a plugin is not stopped by
tooling that predates the intent.
**Cons:** A catalogue the release flow cannot serve passes the gate, so the mismatch
surfaces at the next release rather than at the edit that caused it.
**Risks:** ADR 001's revisit trigger stays a sentence someone has to remember, in an
ADR the breaching edit gives no reason to open — the gap [ADR 006][] named for skill
tooling, in the file ADR 010 pinned.

### Option 2: Reject a catalogue holding more than one entry (Accepted)

**Pros:** The check that already reads the catalogue asserts the assumption the
release flow makes of it, and the failure names the ADR to reopen.
**Cons:** Adding a second plugin means editing this check as well as the manifest.
**Risks:** Read as a ban rather than a checkpoint, so someone works around it —
mitigated by an error message that says which change the failure is asking for.

### Option 3: Generalise the release flow to many plugins

**Pros:** A second plugin needs no decision, because versioning, changelog, and
tagging already carry one each.
**Cons:** Rebuilds the release flow, the changelog format, and the tag scheme for a
plugin nobody has proposed.
**Risks:** The generalised flow is designed against a guess at the second plugin, and
is likelier to be wrong than absent.

## Decision

Take Option 2. Adding a plugin is not a manifest edit but an architectural change:
it decides how two plugins share a version, a changelog, and a tag, and it changes
what every existing install is offered. ADR 001 already asks for that decision; what
was missing is anything that stops the edit landing without it, which is the same
reasoning ADR 006 applied to skill tooling and ADR 010 to the `source` pin.

Option 3 pre-builds for a plugin nobody has proposed, and whatever it guessed would
still need this decision — only earlier, with less to go on.

The check counts entries rather than distinct plugin names, because under ADR 010's
pin those differ only when the catalogue duplicates an entry — which is a fault
either way.

## Consequences

Adding a second plugin now takes the ADR, this check, and everything downstream that
names one version: the [`releasing`][] skill's prep and tagging steps, the release
workflow's single tag and GitHub Release, [`release_notes.py`][]'s assertion that the
changelog's top entry matches `plugin.json`, the changelog format of [ADR 002][], and
the tag scheme of [ADR 008][]. That is the cost of the checkpoint, and it is the work
the entry implies either way.

It also closes the pre-release channel ADR 010 sketched for ADR 008 — two entries
pinned at different refs. ADR 010's `source` equality check had already made that
unreachable; this makes it deliberate. Pre-releases reopen ADR 008 on some other
mechanism, not on a second entry.

The check runs on pull requests and in the `releasing` skill's preflight, not in the
pre-commit hook or the release workflow. [ADR 009][] keeps a standing bypass on
`develop`, and ADR 010 records that `marketplace.json` itself is read from the
default branch — so an entry pushed straight to `develop` is in every user's
catalogue before anything fails. The checkpoint holds the review path, not every
path.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 002]: 002-generate-changelog-at-release.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 008]: 008-release-only-x-y-z-versions.md
[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
