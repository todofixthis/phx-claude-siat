# Changelog

## 1.1.0 - 2026-07-05

### For phx plugin users

#### Added

- **`phx:writing-adrs`: new reference-linking guidance for ADRs.** Link GitHub
  issues/PRs, web references, and code symbols on first mention using reference-style
  Markdown links, with a worked example, documented anti-patterns, and stronger checks
  for orphaned or duplicate links during the skill's own review pass. The ADR template
  also gained a one-line addition showing where the link-definition block belongs.

#### Changed

- **`phx:creative-commits`: commit-message drafting now runs in an isolated,
  lightweight (Haiku) subagent** instead of the calling session, for lower cost and
  cleaner context — it only falls back to drafting in the current session if subagent
  dispatch isn't available (e.g. nested too deep). Commit message format and quality
  are unchanged; wording may vary slightly run-to-run since a fresh model instance now
  drafts each message.

### For phx-claude-siat contributors

#### Changed

- **Project-local skills relocated from `.claude/skills/` to `.agents/skills/`**, to
  keep the directory agent-agnostic (matching the repo's existing
  `AGENTS.md`/`CLAUDE.md`-symlink convention rather than being Claude-specific).
  `.claude/skills` is kept as a **symlink** (not a directory) pointing at the new
  location, so normal file reads/edits still work. Tooling that doesn't follow
  symlinks (`tar`/`zip` archiving, Docker `COPY`, `find -type d`) will see an empty or
  literal-text result at the old path, and checkouts on Windows without
  `core.symlinks=true` will get a plain text file instead of a working directory.
- **`.gitignore` now excludes `.worktrees/`**, so isolated git-worktree workspaces
  created by the `superpowers:using-git-worktrees` workflow no longer show up in
  `git status`.

## 1.0.0 - 2026-07-03

### For phx plugin users

#### Breaking changes

- **`phx:writing-plans` now makes real commits to your repo — creating the feature
  branch and worktree, and committing any coding-agent-facing documentation changes
  (`AGENTS.md`, ADRs, skills) — before the plan file itself is written or reviewed.**
  Previously the worktree/branch appeared only once execution began, and doc updates
  arrived as a plan task you could review before it ran. Even if you decline the
  worktree, a feature branch is still created so those commits never land on `main`.
  **Migration:** don't expect to review a plan before anything touches your repo — the
  branch, worktree, and any documentation commits now precede it. Any tooling or
  reviewer assuming the plan file is the first commit on the branch needs updating too.

#### Added

- **New skill: `phx:writing-release-notes`.** Invoke it when preparing a release to
  draft grouped, audience-reviewed release notes and an advisory semver level for a
  commit/PR/issue range — optionally scoped with `base` (comparison point), `path`
  (monorepo subtree), or `model` (cost control for its gather subagents). Gathering is
  done by cheap-model subagents, with a full-model pass reviewing the draft for clarity
  and breaking-change completeness, separately for user-facing and maintainer-facing
  content. Deliberately conservative about breaking changes, and stays neutral about
  where the notes get published, so it composes into any project's release process.

#### Changed

- The marketplace catalogue's description was corrected to describe its published role
  ("Claude Code plugins by Phoenix Zerin") rather than a development-only description.
- **The marketplace catalogue entry no longer carries a `version` field** (see
  `docs/adr/001-co-locate-marketplace-and-plugin.md`). This does not change install or
  update behaviour — `plugin.json` already took priority over the marketplace entry's
  version, so a resolved version never changed. Any external tooling that read the
  version from `marketplace.json` directly should read `plugin.json` instead.

### For phx-claude-siat contributors

This is the first tagged release, so "breaking" below means *if you already have a
checkout and habits from before this release, here's what changes under you* — not
that a previously published contributor workflow is being broken.

#### Breaking changes

- **Local development now requires launching with `--plugin-dir ./`, not adding the
  repo as a marketplace.** The README's local-development instructions were rewritten
  around this flow, and guidance was added for telling a live working-tree copy of a
  skill apart from a cached one (a skill's reported base directory reveals which).
  **Migration:** switch to launching with `--plugin-dir ./` and run `/reload-plugins`
  after edits.
- **`CLAUDE.md` is now a symlink to `AGENTS.md`.** Codex, Gemini, and Claude now read
  the same maintainer-guidance file instead of each tool getting its own copy.
  **Migration:** edit `AGENTS.md` only. If your environment or tooling doesn't resolve
  symlinks (some Windows setups, zip downloads instead of `git clone`), read `AGENTS.md`
  directly rather than `CLAUDE.md`.
- **A `pre-commit` hook now regenerates `docs/adr/INDEX.md` whenever an ADR is staged
  — but it isn't installed on clone.** If you do nothing, the hook stays inactive and
  `INDEX.md` silently goes stale after your next ADR commit, with no error to flag it.
  **Migration:** activate the hook once per clone with `git config core.hooksPath
  .githooks` (it carries across worktrees). A stale `INDEX.md` after an ADR commit
  means the hook wasn't active — set `core.hooksPath` and re-commit.
- **Working-tree liveness is no longer read from `~/.claude/plugins/data/phx.root`.**
  That pointer can report cached even when the tree is live, so anyone still checking
  it for this purpose gets a wrong answer. **Migration:** determine liveness from the
  base directory the first-loaded `phx:` skill reports instead (a skill is non-live if
  it's unavailable or loads from a `…/plugins/cache/…` path) — see `AGENTS.md`'s
  "Dogfooding" section.

#### Added

- **Architecture Decision Records.** Introduced an ADR practice under `docs/adr/`,
  indexed in `docs/adr/INDEX.md`. The first ADR
  (`docs/adr/001-co-locate-marketplace-and-plugin.md`) records the decision to keep the
  marketplace and plugin co-located in one repository, with the plugin version owned
  solely by `plugin.json`.
- **New `AGENTS.md` section: "Testing skills."** Documents gotchas when RED/GREEN-
  testing a skill with subagents — reload before re-testing, brief the subagent that
  intentional test fixtures aren't errors, and confirm the RED control can actually
  fail before trusting GREEN.
- **New `AGENTS.md` sections: "Branches" and "Language and Style."** Documents the
  `main`/`develop`/feature-branch model, NZ English spelling, and comment placement,
  matching the conventions used across the author's other projects.

#### Changed

- **Maintainer guidance was trimmed**, converting explanatory rationale and a bulleted
  list into tighter prose in the dogfooding and testing-skills guidance — every
  actionable instruction and caution stayed, only the surrounding explanation shrank.
