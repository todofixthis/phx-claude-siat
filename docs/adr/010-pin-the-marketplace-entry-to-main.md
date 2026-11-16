---
status: Accepted
date: 2026-08-01
scope: [.claude-plugin/marketplace.json]
summary: Pin the marketplace plugin entry to a github source at ref main — a branch, not a per-release tag — so what users install is the release branch rather than whichever branch happens to be the repository default, and assert the pin in CI.
revisit-when: The marketplace and plugin split repositories.
---

# 010: Pin the marketplace entry to main

## Context

[ADR 001][] kept the marketplace and the plugin in one repository. So the plugin entry in
[`marketplace.json`][] pointed at the repository root, `"source": "./"`, instead of naming
a git repository and ref. ADR 001 recorded the consequence: "With the marketplace
`source: "./"` and no ref pin, users track the repository's default branch." Releasing
became "bump [`plugin.json`][] and land it on the default branch."

Nothing then held the default branch to `main`. The default is `develop`, the branch every
feature merges into, so `"./"` resolved to integration, not to releases. Three things
followed:

- A fresh install pulled `develop` HEAD, unreleased commits included.
- An installed copy updated when `plugin.json`'s version changed on `develop`. That change
  is the release *preparation* commit, which the [`releasing`][] skill pushes before anyone
  opens the release pull request. So 2.0.0 reached users before review, let alone tagging.
  Nothing came of it that time, because `develop` and `main` held identical trees
  throughout.
- [ADR 008][] reasoned from "the marketplace serves whatever `main` holds", which was
  false. [`AGENTS.md`][] describes `main` as releases-only. That was true of what *lands*
  on `main`, and said nothing about what users got.

The plugin's own manifest is not affected. `plugin.json` remains the single version
authority, and the marketplace entry still carries no version.

## Options

### Option 1: Do nothing — distribution follows the default branch

`source: "./"` stays, and users get whatever branch GitHub reports as default.

**Pros:** No change, and one fewer place that names a branch.
**Cons:** The release branch and the distribution branch differ. So `main` has no effect on
users, and every document that describes `main` as what users get is wrong.
**Risks:** The coupling lives in a GitHub setting that no file records. Anyone who changes
the default branch silently changes what every user installs, and nothing in CI can notice.

### Option 2: Pin the entry to a `github` source at `ref: main` (Accepted)

Replace `"./"` with a `github` source that names this repository and the `main` ref.

**Pros:** A fresh install and an update of an existing install, at the same version, now
get the same tree. ADR 001 could only reduce that ambiguity by tagging each release
commit. The pin removes it.
**Cons:** The entry names its own repository, which reads oddly for a co-located plugin.
Each user also clones that repository twice, once for the marketplace and once for the
plugin.
**Risks:** Nothing reads the pin as a check. If someone drops or repoints it, nothing
fails, and installs quietly revert to the default branch.

#### Variant: pin a per-release tag instead of the branch

Set `ref: X.Y.Z` and bump it every release. `sha` can sit alongside it to fix the exact
commit.

**Pros:** Users install exactly a released commit, never a branch head.
**Cons:** Every release edits the marketplace entry as well as `plugin.json`. ADR 001
removed exactly that need to bump two places.
**Risks:** The two can disagree. A release that bumps `plugin.json` but not the ref
advertises a new version while serving the old tree.

### Option 3: Make `main` the repository's default branch

Leave the entry relative, and change the GitHub setting so the default *is* the release
branch.

**Pros:** The manifest does not change, and every existing document becomes true as
written.
**Cons:** New pull requests default to a `main` base. On a repository where `develop` is
the integration branch, that base is wrong for almost all of them.
**Risks:** It restores the invariant without recording it. The next person to reconsider
the default branch, for that very reason, silently breaks distribution again, because
nothing connects the two.

## Decision

Pin to `ref: main`.

Options 2 and 3 both make `main` ship. What separates them is whether a *file in the
repository* says so. Option 3 fixes today's symptom and leaves the same trap in place. The
default branch is a GitHub setting, and this whole ADR exists because that setting drifted
from what every document assumed. A `ref` in `marketplace.json` can be reviewed and
found with a search.

Review alone is not enough, the lesson [ADR 006][] already drew about declarations that
drift. Anyone can drop a pin that nothing checks, at no cost, so CI asserts this one.

Choose a branch over a tag, because the ref must not need an edit every release. ADR 001
made `plugin.json` the sole version authority, and removed the marketplace entry's
`version` to get there. The tag variant brings the same duplication back one field over.
`main` moves only on release merges, so a branch ref already changes only once per release
here.

This does not disturb ADR 001's own decision. Co-location, the single version authority,
and the versionless entry all stand. This ADR replaces only one consequence, that
distribution follows the default branch. That is why ADR 001 remains `Accepted`, not
superseded.

**Revisit if** the marketplace and plugin split repositories, the trigger ADR 001 already
records. A `github` source that points at a different repository is then the ordinary
form, not a self-reference, and the `ref` needs reconsidering at the same time.

## Consequences

[`validate_manifests.py`][] asserts that the entry's `source` matches the pin exactly. If
someone drops or repoints the pin, the pull request fails, and what users install does not
quietly change.

**Anyone already installed on 2.0.0 stays on the tree they have.** The plugin cache is
keyed by version, and Claude Code skips an update whose resolved version is unchanged. So
changing the `source` reaches nobody by itself. Those users keep `develop`-sourced content
until the next version bump reaches them. To get it sooner, they must uninstall and
reinstall. The 2.0.x release notes need to say so.

The marketplace still reads `marketplace.json` itself from the default branch, because
that is how users add and refresh the marketplace. So catalogue metadata, such as
descriptions and the plugin list, reaches users from `develop` as soon as someone pushes
it, while plugin *content* comes from `main`. A second plugin added to the catalogue
becomes visible before it is released.

Installing from a *local* marketplace no longer serves the local tree. `/plugin marketplace
add ./` in a clone now fetches `main` from GitHub. To run working-tree code, use
`--plugin-dir ./`, as the README already advises.

`develop` stops being a distribution branch, and that is what makes [ADR 009][]'s
reasoning hold. A direct push to `develop` reaches users only after a release pull request
has merged it to `main`, through the gate.

ADR 008's revisit trigger, a marketplace with no channel concept, is now reachable without
one. Two marketplace entries pinned at different refs of this repository would give a
pre-release channel. So if pre-releases are ever wanted, ADR 008 reopens on a mechanism it
assumed did not exist. [ADR 012][] has since closed that mechanism by holding the catalogue
to one entry, so ADR 008 reopens on some other mechanism.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 008]: 008-release-only-x-y-z-versions.md
[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[`AGENTS.md`]: ../../AGENTS.md
[`marketplace.json`]: ../../.claude-plugin/marketplace.json
[`plugin.json`]: ../../.claude-plugin/plugin.json
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
