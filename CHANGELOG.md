# Changelog

## 1.1.1 - 2026-07-15

### For phx plugin users

#### Fixed

- **`phx:creative-commits` no longer produces commit messages with a run-together
  subject line.** Messages came out with no blank line between title and body, so git —
  which treats the first paragraph as the subject — absorbed the bullets into it, and
  `git log --oneline` showed one 250–350 character subject instead of a ~50 character
  title. The skill's worked example contradicted the formatting rule it sits under, and
  agents followed the example. The two now agree, and the rule names the failure mode
  itself. (The example also dropped the blank line before the `Co-Authored-By` trailer —
  a layout git cannot parse as a trailer at all — though agents kept that line in
  practice, so co-author attribution generally survived. Its trailer also named a
  superseded model, which is cosmetic since agents name their own.)

  **Existing commits are not corrected retroactively.** Anything already written this way
  keeps its long subject line; list them with `git log --oneline | awk 'length > 72'`.
  Repairing them rewrites history and changes SHAs, so confine it to branches you have
  not shared. Tooling tuned to the old output — commit-subject linting, changelog
  generators, PR titles taken from the first commit — now sees standard formatting.

### For phx-claude-siat contributors

#### Breaking changes

- **The release gate now reads the real `origin/main`, and hard-fails when `develop` is
  behind it.** The divergence check tested the *local* `main`, a branch the release flow
  never checks out, so a `main` left behind by an earlier release silently passed. The
  same stale reference set the release-notes range: this release would have been the
  first to re-report 1.1.0's work as new. No published release notes were affected, as
  local `main` only went stale when 1.1.0 landed, after 1.1.0's own notes had been
  generated. Every check now fetches and reads `origin/main`, so the gate touches no
  local branch and works in fresh clones and worktrees, where the old check errored
  outright.

  Merging a release PR leaves a merge commit on `main` that `develop` lacks, so
  `origin/main` stops being an ancestor of `develop` the moment any release lands. The
  `releasing` skill now back-merges as its final step, so this resolves itself from here
  on. But a release cut *before* this version left `develop` behind, and the gate will
  refuse the next release until you repair it.

  **Migration.** Check whether this affects you:

  ```
  git fetch origin && git merge-base --is-ancestor origin/main develop && echo "up to date"
  ```

  If that prints nothing, back-merge by hand:

  ```
  git switch develop && git merge --no-edit origin/main && git push
  ```

  It carries no content, so expect an empty diff — a fast-forward if `develop` has not
  moved since the release, a merge commit if it has. A conflict means the release PR was
  squashed or rebased rather than merged: resolve in favour of `develop` and commit,
  since the gate only needs `origin/main` reachable from `develop`. This repo's `develop`
  was repaired as part of this release, so it needs nothing.

#### Fixed

- **The documented reason for requiring a merge commit had the ancestry backwards**, and
  so never explained the rule it justified. The gate needs `origin/main` reachable from
  `develop`: a merge commit keeps `develop`'s tip as a parent of `main`, so the
  back-merge applies cleanly, whereas a squash or rebase replays the work under new SHAs
  and the back-merge then conflicts against its own duplicated changes. (Documentation
  only — the rule and the check are unchanged.)
- **Maintainer docs pointed at the old project-local skills path.** They now describe
  project-local skills at `.agents/skills/<name>/`, with `.claude/skills` retained as a
  symlink for tooling that still expects the old path. (Documentation only; the move
  itself shipped in 1.1.0.)

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
