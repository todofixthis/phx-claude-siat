---
status: Accepted
date: 2026-08-01
tags: [branches, default-branch, distribution, github, marketplace, plugin, ref, releases, source, updates, versioning]
summary: Pin the marketplace plugin entry to a github source at ref main — a branch, not a per-release tag — so what users install is the release branch rather than whichever branch happens to be the repository default, and assert the pin in CI; revisit if the marketplace and plugin ever split repositories.
---

# 010: Pin the marketplace entry to main

## Context

[ADR 001][] kept the marketplace and the plugin in one repository with the entry's
`source` set to `"./"`, and recorded the consequence: "With the marketplace `source: "./"`
and no ref pin, users track the repository's default branch." Releasing therefore became
"bump [`plugin.json`][] and land it on the default branch."

Nothing then held the default branch to `main`. It is `develop` — the branch every feature
merges into — so `"./"` resolved to integration, not to releases. Three things followed:

- A fresh install pulled `develop` HEAD, unreleased commits included.
- An installed copy updated when `plugin.json`'s version changed on `develop`. That is the
  release *preparation* commit, which the [`releasing`][] skill pushes before the release
  pull request is opened — so 2.0.0 reached users before it was reviewed, let alone tagged.
- [ADR 008][] reasoned from "the marketplace serves whatever `main` holds", and
  [`AGENTS.md`][] describes `main` as releases-only. The second was true about what *lands*
  on `main` and inert about what users got; the first was simply false.

The plugin's own manifest is not implicated: `plugin.json` remains the single version
authority, and the marketplace entry still carries no version.

## Options

### Option 1: Do nothing — distribution follows the default branch

`source: "./"` stays, and what ships is whatever branch GitHub reports as default.

**Pros:** No change, and one fewer place naming a branch.
**Cons:** The release branch and the distribution branch are different branches, so `main`
is inert and every document describing it as what users get is wrong.
**Risks:** The coupling is invisible in the repository — it lives in a GitHub setting no
file records. Anyone who changes the default branch silently changes what every user
installs, and nothing in CI can notice.

### Option 2: Pin the entry to a `github` source at `ref: main` (Accepted)

Replace `"./"` in [`marketplace.json`][] with a `github` source naming this repository and
the `main` ref.

**Pros:** A fresh installer and an existing updater on the same version now get the same
tree, closing the ambiguity ADR 001 recorded and could only mitigate with tags.
**Cons:** The entry names its own repository, which reads oddly for a co-located plugin.
**Risks:** Two clones of one repository now exist on each user's machine — the marketplace's
and the plugin's — each fetched over SSH by default on a public repo where that is
unnecessary.

#### Variant: pin a per-release tag instead of the branch

`ref: X.Y.Z`, bumped every release, with `sha` available alongside it for exact-commit
immutability.

**Pros:** Users install exactly a released commit, never a branch head.
**Cons:** Every release edits the marketplace entry as well as `plugin.json`, which is the
two-places-to-bump coupling ADR 001 removed.
**Risks:** The two can disagree. A release that bumps `plugin.json` but not the ref
advertises a new version while serving the old tree.

### Option 3: Make `main` the repository's default branch

Leave the entry relative and change the GitHub setting so the default *is* the release
branch.

**Pros:** No manifest change; every existing document becomes true as written.
**Cons:** New pull requests default to a `main` base, so contributors must select `develop`
each time — on a repository where `develop` is the integration branch and `main` takes only
release merges, the default is wrong for almost every pull request.
**Risks:** Restores the invariant without recording it. The next person to reconsider the
default branch — for the pull-request-base reason above — silently breaks distribution
again, because nothing connects the two.

## Decision

Pin to `ref: main`.

What distinguishes the options is not whether `main` ships — Option 2 and Option 3 both
achieve that — but whether a *file in the repository* says so. Option 3 fixes today's
symptom while leaving the same trap armed: the default branch is a GitHub setting, and this
whole ADR exists because that setting drifted from what every document assumed. A `ref` in
`marketplace.json` is reviewable and greppable.

Being reviewable is not enough on its own, which is the lesson [ADR 006][] already drew
about declarations that drift: `validate_manifests.py` now asserts the entry's `source`
matches the pin exactly. Dropping or repointing it breaks nothing at build time — installs
would simply start serving `develop` again — so nothing but an assertion would catch it.

Branch over tag, because the ref must not need editing per release. ADR 001 made
`plugin.json` the sole version authority and removed the marketplace entry's `version` to
get there; the tag variant reintroduces the same duplication one field over. `main` moves
only on release merges, so a branch ref is already release-granular here.

This does not disturb ADR 001's own decision. Co-location, the single version authority, and
the versionless entry all stand — only the consequence that distribution follows the default
branch is replaced, which is why ADR 001 remains `Accepted` rather than superseded.

**Revisit if** the marketplace and plugin split repositories, the trigger ADR 001 already
records. A `github` source pointing at a different repository is then the ordinary form
rather than a self-reference, and the `ref` should be reconsidered alongside it.

## Consequences

**Anyone already installed on 2.0.0 stays on the tree they have.** The plugin cache is keyed
by version (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`), and an update whose
resolved version is unchanged is skipped — so changing the `source` propagates to nobody by
itself. Those users keep `develop`-sourced content until the next version bump reaches them;
the fix therefore ships with the next release rather than on merge, and anyone wanting it
sooner must uninstall and reinstall. The 2.0.x release notes need to say so.

`marketplace.json` itself is still read from the default branch, because that is how the
marketplace is added and refreshed. Catalogue metadata — descriptions, the plugin list —
therefore reaches users from `develop` as soon as it is pushed, while plugin *content* comes
from `main`. Adding a second plugin makes it visible before it is released.

Installing from a *local* marketplace no longer serves the local tree: `/plugin marketplace
add ./` in a clone now fetches `main` from GitHub. `--plugin-dir ./` remains the way to run
working-tree code, as the README already advises, but the fallback of installing locally to
approximate it is gone.

`develop` stops being a distribution branch, which is what makes [ADR 009][]'s reasoning
hold: a direct push there reaches users only after a release pull request has merged it to
`main`, gated on the way.

ADR 008's revisit trigger — a marketplace with no channel concept — is now reachable without
one. Two marketplace entries pinned at different refs of this repository would give a
pre-release channel, so if pre-releases are ever wanted, that ADR reopens on a mechanism it
assumed did not exist.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 008]: 008-release-only-x-y-z-versions.md
[ADR 009]: 009-keep-a-standing-develop-bypass.md
[`AGENTS.md`]: ../../AGENTS.md
[`marketplace.json`]: ../../.claude-plugin/marketplace.json
[`plugin.json`]: ../../.claude-plugin/plugin.json
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
