---
status: Accepted
date: 2026-06-27
tags: [marketplace, plugin, repository-structure, versioning, releases, single-source-of-truth]
summary: Keep the marketplace and plugin in one repository; the plugin version lives only in plugin.json, never duplicated in the marketplace entry.
---

# 001: Co-locate the marketplace and plugin in one repository

## Context

This repository is simultaneously a Claude Code marketplace (`todofixthis`) and the
single plugin that marketplace lists (`phx`). The two are conceptually distinct
entities with independent lifecycles: a plugin is versioned, released software; a
marketplace is a catalog recording where plugins live. This marketplace lists only
this author's own plugins — it is not a general catalog for third-party plugins.

Per Claude Code's documented behaviour, a plugin's version resolves in priority
order: `plugin.json`, then the marketplace plugin entry, then the git commit SHA. An
installed plugin updates (via `/plugin update` or startup auto-update) only when that
resolved version string changes (per Claude Code's plugin-marketplaces documentation). When `version` is set in both `plugin.json` and the
marketplace entry, `plugin.json` wins silently and the marketplace value is ignored.
The marketplace file itself carries no top-level version — versioning applies only to
plugin entries. Today both `plugin.json` and the marketplace entry declare `1.0.0`,
conflating the two lifecycles. With the marketplace `source: "./"` and no ref pin,
users track the repository's default branch.

We are about to make our first non-trivial change since `1.0.0` and need a release
model. That forces a prior question: should two distinct entities share one
repository, or live apart? Forces: minimise maintenance toil while there is a single
plugin, keep version ownership unambiguous, and preserve the option to separate
later.

## Options

### Option 1: Do nothing

Leave both manifests carrying `version: 1.0.0` in one repository, lifecycles
undistinguished.

**Pros:** No work.
**Cons:** Marketplace and plugin lifecycles stay conflated, and the duplicated
version is a latent footgun.
**Risks:** Bumping the marketplace entry expecting it to take effect silently does
nothing — `plugin.json` outranks it — so a release bumped in the wrong manifest never
reaches users.

### Option 2: Co-locate, version owned by plugin.json (Accepted)

Keep marketplace and plugin in this repository. `plugin.json` is the sole source of
truth for the plugin version; the marketplace plugin entry carries no `version`. A
marketplace change (catalog edits, re-pointing a source) is a distinct, rare event
from a plugin release.

**Pros:** One repository, one PR/CI/issue surface; unambiguous version ownership.
**Cons:** Marketplace and plugin commits share one history; one catalog serves both
local development and published distribution.
**Risks:** A contributor could edit the wrong lifecycle, or re-add a `version` to the
marketplace entry.

### Option 3: Split into two repositories

Move the marketplace catalog to its own repository; the plugin lives alone, listed by
GitHub source and optionally pinned to a release ref.

**Pros:** Fully independent lifecycles; stable-vs-latest channels via ref pinning;
catalog write-access decoupled from plugin-development access; a clean catalog
identity able to list third-party plugins; no catalog churn from active plugin
development.
**Cons:** For a single first-party plugin, the marketplace repository is a near-empty
one-file repository; if it pins per release, every release gains a cross-repo
re-point step.
**Risks:** Ongoing cross-repo admin outweighs the benefit until a second plugin or a
channel requirement exists.

## Decision

Co-locate (Option 2). With a single first-party plugin and no need for stable/latest
channels, one repository is less total toil than two: splitting pays off only when
the marketplace lists multiple plugins or pins releases to refs. Its other benefits
do not apply here — the catalog lists only this author's plugins, so decoupled access
control and a third-party identity carry no weight, and catalog churn is negligible
because marketplace edits are rare. The separation that matters is logical, not
physical: `plugin.json` owns the version, the marketplace entry is a pointer, and the
two lifecycles are documented as distinct. Revisit when a second plugin joins the
marketplace, or stable-vs-latest channels are needed.

## Consequences

- `version` is removed from the marketplace plugin entry, leaving `plugin.json`
  authoritative. This is safe for existing installs: `plugin.json` already outranks
  the entry, so no resolved version changes and no spurious update fires. Releasing
  becomes: bump `plugin.json` and land it on the default branch.
- One catalog now serves both development and published distribution, so the
  marketplace `description` (currently "Development marketplace…") is corrected to
  describe that published role, lest users adding it be misled.
- Installed copies update only when `plugin.json`'s version changes, so work
  accumulates on the default branch and reaches existing users only on a deliberate
  bump — the batched cadence is enforced by the version field. But a fresh install
  pulls default-branch HEAD, so a new installer and an existing updater can both
  report `1.0.0` while running different commits. Tag each release commit to restore a
  version→commit mapping for support and bisection; a tag needs no ref pin or repo
  split.
- The split trigger is recorded, so the bet is reversible: migration later is bounded
  — create the new repository, move the marketplace manifest, update the install docs,
  and users re-add the marketplace once.
