# Changelog

## 1.0.0 - 2026-07-03

### Breaking changes

- **Local development now requires launching with `--plugin-dir ./`, not adding the
  repo as a marketplace.** The README's local-development instructions were rewritten
  around this flow, and guidance was added for telling a live working-tree copy of a
  skill apart from a cached one (a skill's reported base directory reveals which).
  **Migration:** contributors following the old marketplace-add workflow should switch
  to launching with `--plugin-dir ./` and run `/reload-plugins` after edits.
- **The marketplace catalogue entry no longer carries a `version` field.** Version is
  now owned solely by `plugin.json` (see `docs/adr/001-co-locate-marketplace-and-plugin.md`).
  Any tooling that read the version from `marketplace.json` needs to read `plugin.json`
  instead.
- **`CLAUDE.md` is now a symlink to `AGENTS.md`.** Codex, Gemini, and Claude now read
  the same maintainer-guidance file instead of each tool getting its own copy.
  **Migration:** edit `AGENTS.md` only. If your environment or tooling doesn't resolve
  symlinks (some Windows setups, zip downloads instead of `git clone`), read `AGENTS.md`
  directly rather than `CLAUDE.md`.
- **`writing-plans` now creates the branch and worktree, and commits any coding-agent-
  facing documentation changes (`AGENTS.md`, ADRs, skills), before writing the plan
  file** — previously both appeared only once execution began, and doc updates arrived
  as a plan task. **Migration:** any tooling or reviewer expecting the plan file to be
  the first commit on the branch, or expecting doc updates to appear as a plan task,
  should instead expect the worktree/branch and any documentation commits to precede
  the plan file.

### Added

- **New skill: `writing-release-notes`.** Drafts grouped, audience-reviewed release
  notes and an advisory semver level from a commit/PR/issue range — gathering is done
  by cheap-model subagents, with a full-model pass reviewing the draft for clarity and
  breaking-change completeness. Deliberately conservative about breaking changes and
  stays neutral about where the notes get published, so it composes into any project's
  release process (including this plugin's own, from this release on).
- **Architecture Decision Records.** Introduced an ADR practice under `docs/adr/`,
  indexed in the new `docs/adr/INDEX.md`, with a `pre-commit` hook that regenerates the
  index automatically whenever an ADR is staged. The first ADR records the decision to
  keep the marketplace and plugin co-located in one repository, with the plugin version
  owned in a single place. **Setup:** the hook isn't installed on clone — activate it
  once per clone with `git config core.hooksPath .githooks` (it carries across
  worktrees). A stale `INDEX.md` after an ADR commit means the hook wasn't active; set
  `core.hooksPath` and re-commit.

### Changed

- **Detecting a stale (non-live) working-tree copy is now organic, not a preflight
  probe.** A skill is flagged as non-live only when it's unavailable or its reported
  base directory points into the plugin cache — this costs nothing until it actually
  matters, and no longer relies on a session pointer that can read as cached even when
  the tree is live.
- **Maintainer guidance was trimmed**, keeping every actionable instruction while
  cutting back the surrounding rationale.
- The marketplace catalogue's description was corrected to describe its published role
  ("Claude Code plugins by Phoenix Zerin") rather than a development-only description.
