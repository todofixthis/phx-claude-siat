---
status: Accepted
date: 2026-08-05
scope: [.claude-plugin/, scripts/ci/validate_manifests.py]
summary: Advertise exactly one marketplace entry; a second fails the manifest check, so adding a plugin means an ADR plus a release flow that names both — not a generalised flow built up front.
revisit-when: A second plugin joins the marketplace.
---

# 012: Advertise one plugin per catalogue

## Context

`.claude-plugin/marketplace.json` is the catalogue a user adds before installing.
[ADR 001][] keeps it beside the plugin manifest, and already records the trigger
"revisit when a second plugin joins the marketplace". [ADR 010][] pins every entry's
`source` to this repository at `main`. [`validate_manifests.py`][] enforces both. It
checks that each entry is versionless and correctly pinned, and that some entry names
what `plugin.json` declares. But nothing limited how many entries there were.

Because of ADR 010's pin, a second entry cannot come from anywhere else. It is either
another plugin released from this repository, or a duplicate of the one already there.
The rest of the repo assumes neither exists. `plugin.json` carries the single version
the release flow bumps, `CHANGELOG.md` holds one entry per release, and a tag names one
version. A second entry passes every check and leaves all of that ambiguous, because
nothing would say which plugin a release was of.

## Options

### Option 1: Do nothing

**Pros:** No code to write, and tooling written before anyone meant to add a plugin
does not stop a maintainer who adds one.
**Cons:** A catalogue the release flow cannot serve passes the gate. The mismatch then
surfaces at the next release, not at the edit that caused it.
**Risks:** ADR 001's revisit trigger stays a sentence someone has to remember, in an
ADR that the breaking edit gives no reason to open. [ADR 006][] named the same gap for
skill tooling, and here it sits in the file ADR 010 pinned.

### Option 2: Reject a catalogue holding more than one entry (Accepted)

**Pros:** The check that already reads the catalogue asserts what the release flow
assumes about it, and the failure names the ADR to reopen.
**Cons:** Adding a second plugin means editing this check as well as the manifest.
**Risks:** Someone may read the check as a ban, not a checkpoint, and work around it.
The error message reduces that risk by saying which change the failure asks for.

### Option 3: Generalise the release flow to many plugins

**Pros:** A second plugin needs no decision, because versioning, the changelog, and
tagging already carry one per plugin.
**Cons:** It rebuilds the release flow, the changelog format, and the tag scheme for
a plugin nobody has proposed.
**Risks:** Designers would build the generalised flow against a guess at the second
plugin, so it is likelier to be wrong than to be missing.

## Decision

Take Option 2. Adding a plugin is an architectural change, not a manifest edit. It
decides how two plugins share a version, a changelog, and a tag, and it changes what
every existing install is offered. ADR 001 already asks for that decision. What was
missing was anything that stops the edit landing without it. ADR 006 applied the same
reasoning to skill tooling, and ADR 010 to the `source` pin.

Option 3 builds ahead for a plugin nobody has proposed. Whatever it guessed would still
need this decision, only earlier and with less to go on.

The check counts entries, not distinct plugin names. Under ADR 010's pin, the two
counts differ only when the catalogue duplicates an entry, and a duplicate is a fault
either way.

## Consequences

Adding a second plugin now takes the ADR, this check, and everything downstream that
names one version:

- the [`releasing`][] skill's prep and tagging steps
- the release workflow's single tag and GitHub Release
- [`release_notes.py`][]'s assertion that the changelog's top entry matches `plugin.json`
- the changelog format of [ADR 002][]
- the tag scheme of [ADR 008][]

That is the cost of the checkpoint, and the entry implies the same work either way.

The check also closes the pre-release channel that ADR 010 sketched for ADR 008, two
entries pinned at different refs. ADR 010's `source` equality check had already made
that channel unreachable. This check makes it deliberate. Pre-releases reopen ADR 008
on some other mechanism, not on a second entry.

The check runs on pull requests and in the `releasing` skill's preflight. It does not
run in the pre-commit hook or the release workflow. [ADR 009][] keeps a standing bypass
on `develop`, and ADR 010 records that the marketplace reads `marketplace.json` itself
from the default branch. So an entry pushed straight to `develop` reaches every user's
catalogue before anything fails. The checkpoint guards the review path, not every path.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 002]: 002-generate-changelog-at-release.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 008]: 008-release-only-x-y-z-versions.md
[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
