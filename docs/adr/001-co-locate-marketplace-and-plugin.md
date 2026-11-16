---
status: Accepted
date: 2026-06-27
scope: [.claude-plugin/]
summary: Keep the marketplace and plugin in one repository; the plugin version lives only in plugin.json, never duplicated in the marketplace entry.
revisit-when: A second plugin joins the marketplace, or stable-vs-latest channels are needed.
---

# 001: Co-locate the marketplace and plugin in one repository

## Context

This repository is both a Claude Code marketplace (`todofixthis`) and the one plugin
that marketplace lists (`phx`). The two have separate lifecycles. A plugin is versioned,
released software. A marketplace is a catalogue of where plugins live. This marketplace
lists only this author's own plugins, not third-party ones.

Claude Code's plugin-marketplaces documentation says a plugin's version resolves in this
order: `plugin.json`, then the marketplace plugin entry, then the git commit SHA. An
installed plugin updates, through `/plugin update` or auto-update at startup, only when
that resolved version string changes. If both `plugin.json` and the marketplace entry set
`version`, `plugin.json` wins and Claude Code ignores the marketplace value without a
warning. The marketplace file has no top-level version. Only plugin entries carry one.
Today `plugin.json` and the marketplace entry both declare `1.0.0`, which conflates the
two lifecycles. With the marketplace `source: "./"` and no ref pin, users track the
repository's default branch.

Our next change is the first non-trivial one since `1.0.0`, and it needs a release model.
That raises a prior question: should two separate things share one repository? Three
forces apply. Keep maintenance low while there is one plugin, keep version ownership
unambiguous, and keep the option to split later.

## Options

### Option 1: Do nothing

Leave both manifests at `version: 1.0.0` in one repository, with nothing separating the
lifecycles.

**Pros:** No work.
**Cons:** The marketplace and plugin lifecycles stay conflated, and the duplicated version
is a latent mistake for whoever next bumps it.
**Risks:** Bumping the marketplace entry does nothing, because `plugin.json` outranks it.
A release bumped in the wrong manifest never reaches users, and nothing says so.

### Option 2: Co-locate, version owned by plugin.json (Accepted)

Keep the marketplace and the plugin in this repository. `plugin.json` alone sets the
plugin version, and the marketplace plugin entry has no `version`. A marketplace change,
such as a catalogue edit or a re-pointed source, is a separate and rare event, not a
plugin release.

**Pros:** One repository, so one set of PRs, CI, and issues. Version ownership is
unambiguous.
**Cons:** Marketplace and plugin commits share one history. One catalogue serves both
local development and published distribution.
**Risks:** A contributor could edit the wrong lifecycle, or add a `version` back to the
marketplace entry.

### Option 3: Split into two repositories

Move the marketplace catalogue to its own repository. The plugin lives alone, listed by
GitHub source and optionally pinned to a release ref.

**Pros:** The lifecycles are fully independent. Ref pinning gives stable and latest
channels. Write access to the catalogue is separate from plugin-development access. The
catalogue gets its own identity and can list third-party plugins. Active plugin
development causes no catalogue churn.
**Cons:** With one first-party plugin, the marketplace repository holds almost nothing
but one file. If it pins per release, every release gains a step to re-point the ref in
the other repository.
**Risks:** Admin across two repositories costs more than it returns until a second plugin
or a channel requirement exists.

## Decision

Co-locate (Option 2). With one first-party plugin and no need for stable and latest
channels, one repository costs less work than two. A split pays off only when the
marketplace lists several plugins or pins releases to refs. Its other benefits don't
apply here. The catalogue lists only this author's plugins, so separate access control
and a third-party identity are worth nothing, and catalogue churn is negligible because
marketplace edits are rare. The separation that matters is logical, not physical.
`plugin.json` owns the version, the marketplace entry only points at the plugin, and the
docs describe the two lifecycles as separate. Revisit when a second plugin joins the
marketplace, or when stable and latest channels are needed.

## Consequences

> **Amended by [ADR 010][]:** the entry now pins `ref: main`, so distribution no longer
> follows the repository's default branch. That supersedes the bullets below that reason
> from the default branch, including the ambiguity between version and commit, on that
> point only. The decision above stands.

- The marketplace plugin entry loses `version`, which leaves `plugin.json` authoritative.
  Existing installs are safe. `plugin.json` already outranks the entry, so no resolved
  version changes and no false update fires. A release is now: bump `plugin.json` and
  land it on the default branch.
- One catalogue now serves both development and published distribution. The marketplace
  `description` (currently "Development marketplace…") changes to describe the published
  role, so that users who add the marketplace aren't misled.
- Installed copies update only when the version in `plugin.json` changes. A release
  therefore reaches existing users only when a bumped version lands on the default
  branch. The version field sets the batched release cadence, not each merge. A fresh
  install, however, pulls the default branch's HEAD. A new installer and an existing
  updater can both report `1.0.0` while running different commits. Tag each release
  commit, so that support and bisection can map a version to its commit. A tag needs no
  ref pin and no repository split.
- A check enforces the revisit trigger above, so nobody has to remember it. [ADR 012][]
  fails the manifest check on a second catalogue entry, so a second plugin can't join
  until this decision is reopened.
- The split trigger is on record, so the bet is reversible and a later migration is
  bounded. Create the new repository, move the marketplace manifest, update the install
  docs, and users re-add the marketplace once.

[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
