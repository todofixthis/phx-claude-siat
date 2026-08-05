# Changelog

## 3.0.0 - 2026-08-05

### For phx plugin users

The plugin ships no validator, so nothing below fails a build of yours — these change
what `phx:writing-adrs` writes, and what it asks you.

#### Breaking changes

- **`status: Deprecated` is gone, and nothing replaces it.** It meant "the investigation
  concluded no change was warranted" — an ADR where Option 1, do nothing, won. That is
  now an ordinary `Accepted` ADR with its `(Accepted)` marker on Option 1. The
  option-numbering rule changed with it, and gained one it lacked: numbering and the
  marker are fixed when the ADR is written and never derived from `status`, so a
  superseded ADR keeps its marker on the option that won.

  **Migration:** an ADR carrying `status: Deprecated` becomes `Accepted`, marker left
  where it is. Do **not** rename it to `Archived` — that is a new and unrelated status,
  not this one under another name. Across a whole `docs/adr/`, hand the judgement to
  your agent rather than making it yourself:

  ````markdown
  Read the Frontmatter Fields and Conventions sections of the phx:writing-adrs skill,
  then find every ADR in docs/adr/ carrying `status: Deprecated`. For each, tell me
  which status it should now hold and why, before changing anything.
  ````

#### Added

- **A third status, `Archived`, for a decision worth keeping but not worth loading.** It
  still binds, but something other than someone reading the index stops people breaking
  it — typically a comment sitting where the breaking change would be written. Such a
  decision leaves `docs/adr/INDEX.md`, costing no context, and the skill has your agent
  search the archived ones before recording any new decision. The bar is deliberately
  hard: the defence must be met *while the work is still being planned*, so a check that
  fails afterwards does not qualify.

- **`archived-because`**, a frontmatter field required of an `Archived` ADR and refused
  of any other: one sentence naming that defence and where someone meets it, so whether
  and why a decision left the index reads at a glance.

#### Changed

- **The skill asks you rather than recording a premise it cannot check.** Where an ADR
  would rest on a claim about a tool, workflow, or live setting the agent cannot verify,
  it raises the question instead of writing the uncertainty in as a caveat. Its review
  pass now also checks archival timing, and that claims were checked against the thing
  itself rather than against documentation.

- **The README marks which skills need an instruction in your `CLAUDE.md` before an
  agent will reach for them** — `creative-commits`, `receiving-code-review` and
  `writing-plans` — with the lines to add beside each skill rather than in one distant
  section. Three skills were easy to install and never see used.

- **ADR frontmatter values must sit on one line** — no wrapping, no `>` or `|` block
  scalars, since a wrapped value truncates under a line-based parser. Advisory for you;
  nothing shipped enforces it.

#### Fixed

- **Installs now serve releases rather than integration.** The marketplace entry used a
  relative source, which resolves to the repository's default branch — `develop` — so
  every install since 1.0.0 has been served the integration branch. The entry now pins
  `ref: main` on GitHub, and CI asserts the pin. See ADR 010.

  **Mostly no action needed, with one hole.** The cache is keyed by version, so the new
  `source` reaches you with this release's bump. But the catalogue holding that `source`
  is itself read from the default branch: if your cached catalogue predates the pin,
  this version can be fetched through the old source and cached, and an update whose
  resolved version is unchanged is then skipped.

  For certainty you are on the released tree, refresh the catalogue and reinstall rather
  than relying on the update:

  ````shell
  /plugin uninstall phx@todofixthis
  /plugin marketplace update todofixthis
  /plugin install phx@todofixthis
  ````

### For phx-claude-siat contributors

#### Breaking changes

- **Run scripts as `python3 -m scripts.<area>.<name>` from the repo root** (ADR 011).
  A path invocation fails with an import error, and the scripts lost their shebang and
  executable bit, so `./scripts/...` fails too. The suite is
  `python3 -m unittest discover -s scripts -t . -p 'test_*.py'`. The hook and both
  workflows are converted; a shell alias of your own is not.

- **A wrapped `description:` in any `SKILL.md` now fails the build.** The manifest
  validator shares the ADR frontmatter parser, so every `SKILL.md` under both skill
  roots is held to one line per value — no wrapping, no block scalars, no duplicate
  keys, no key containing whitespace. The parser used to keep whatever fitted on the
  first line and say nothing. Descriptions are long, so this is the likeliest one to
  catch you: wrapping used to work.

  The limit exists because of ADR 007: the repo hand-parses frontmatter line by line
  rather than depending on PyYAML. Taking that dependency would lift it, and ADR 007's
  standing trigger is exactly a script having to parse a grammar this repo does not
  define — but we are not ready to take it yet.

- **Checks now reject, rather than pass or crash on, input they previously let by:**
  - an ADR with an unrecognised status, or a status missing the field it owns;
  - a file in `docs/adr` that is neither an ADR nor the index — a misfiled note, or an
    ADR named against the convention, which used to drop out of the index unseen;
  - a plugin manifest with no `name`;
  - a catalogue that is empty, lists more than one plugin (ADR 012), or names something
    other than what the plugin manifest declares;
  - a tooling declaration written as a bare string, a table, or with a trailing dot —
    the last matched any workflow, because it trims to the empty string;
  - a manifest holding valid JSON of the wrong shape, which used to end in an
    `AttributeError` rather than a message naming the file.

- **The release App's Actions secret is renamed** to `RELEASE_APP_CLIENT_ID`, because
  the token action takes the App's Client ID — a different value from the numeric App ID
  the deprecated input wanted. **Migration:** read the Client ID off the App's settings
  page and store it under the new name; the private key is unchanged. Full setup in
  `docs/release-automation.md`.

- **A pull request must be current with its base before it can merge.** The rulesets are
  renamed `trunk-develop` and `trunk-main`, the first targeting `refs/heads/develop`
  literally so it survives a default-branch change;
  `strict_required_status_checks_policy` is on and review threads must be resolved.

- **A fork cannot pass the `manifests` job unchanged.** The `source` check compares
  against `todofixthis/phx-claude-siat` at `main` exactly, with no escape hatch, so a
  fork fails on a file nobody touched. Repoint `EXPECTED_SOURCE` in
  `scripts/ci/validate_manifests.py`.

- **`/plugin marketplace add ./` no longer serves your clone** — it fetches the pinned
  `main` from GitHub. `--plugin-dir ./` remains the only way to run working-tree code.

- **Two conventions are enforced by review now, both written in `AGENTS.md`.** Every
  function annotates its return type and named parameters — `*args` and `**kwargs` stay
  bare, test functions are exempt, their helpers and fixtures are not. A literal
  duplicating a constant imports the constant instead, tests included.

#### Added

- **A test suite where there was almost none** — 90 new tests, 101 in total, over the
  frontmatter parser, the ADR index generator and the manifest validator. ADR 007 called
  `scripts/adr` having no tests "the largest cost here, larger than any duplicated
  parser". Every check is mutation-tested: disabled in turn, with a test confirmed to
  catch it.

- **`.agents/rules/testing.md`**, a path-scoped rule holding the testing conventions,
  loaded when you open a test file rather than every session. It also asks you to name
  in the pull request which checks you mutation-tested and what caught each — a new
  expectation, not a description of past work. The test-docstring rule moved here from
  `AGENTS.md` rather than being dropped; `.claude/rules` symlinks to it.

- **Four decision records.** ADR 009 keeps a standing bypass on the `develop` ruleset;
  ADR 010 pins the marketplace entry to `main`; ADR 011 makes `scripts/` a package;
  ADR 012 holds the catalogue to one plugin. ADRs 001 and 007 gain amendment notes, and
  ADR 008 a repointed citation.

- **A porting note in `docs/release-automation.md`** for a project that cannot keep a
  standing bypass on its integration branch — release branches instead, at three gated
  pull requests per release.

#### Fixed

- **One frontmatter parser instead of two adapted copies** (ADR 011). Both truncated a
  wrapped value silently, and the fix applied to input both of them read — the drift
  ADR 007's revisit trigger existed to catch, now fired and discharged.

- **ADR 006's drift check could not fire on the change it exists to catch.** The
  `manifests` path filter matched `skills/*/SKILL.md` but not `skills/*/pyproject.toml`,
  so adding a tool to `[tool.autohooks]` ran no manifest validation at all. It now
  covers whole skill directories under both roots.

## 2.0.0 - 2026-08-01

### For phx plugin users

#### Breaking changes

- **The skill-resolution instruction in your `CLAUDE.md` needs updating.** `phx` now
  wraps two `superpowers` skills rather than one, so an instruction naming only
  `writing-plans` leaves `phx:receiving-code-review` unused. Replace:

  ```markdown
  When asked to write an implementation plan, invoke `phx:writing-plans`, not `superpowers:writing-plans`.
  ```

  with:

  ```markdown
  Where `phx` wraps a `superpowers` skill of the same name, always invoke the `phx:` one.
  ```

  The replacement names no skills, so it keeps covering new wrappers as they arrive.

  **Without the superpowers plugin installed, both wrappers delegate to a skill you do
  not have.** It stays an optional install, so if you do not run it, adapt the rule to
  skip the wrappers or leave it out — better than pointing Claude at skills that cannot
  resolve. Splitting the wrappers into their own marketplace plugin is planned for a
  future version; it is too large a change to make mid-release.

- **`phx:writing-plans` now deletes the plan file.** The final task removes it before the
  pull request is created, so nothing that ships references it. Previously it stayed in
  the repo, readable during review.
  **Migration:** the plan is committed before it is deleted, so it survives in the
  branch's history. Anything worth keeping belongs in an architecture decision record,
  written during execution: by the time the deletion runs, the agent has finished.

#### Added

- **New skill: `phx:receiving-code-review`** — for answering pull-request review
  feedback. It wraps `superpowers:receiving-code-review` with the mechanics that skill
  leaves out: gather every inline thread before answering any, reply in each thread,
  sweep the repo *and the PR body* for references the response made stale, and record
  review-driven decisions as an architecture decision record rather than a reply.

  It needs the [superpowers marketplace](https://github.com/obra/superpowers-marketplace)
  plugin for the skill it delegates to, and an authenticated `gh` — it posts thread
  replies under your credentials.

### For phx-claude-siat contributors

#### Breaking changes

- **Releases are tagged and published by CI.** Merging the `develop`→`main` release PR
  triggers a workflow that tags the merge commit, publishes the GitHub Release from the
  CHANGELOG's top entry, and back-merges to `develop`. The releasing skill's own
  mutations end at opening that PR; after the merge it watches the run and triages
  failures.

  **This is a prerequisite of the next release merge, not an optional upgrade.** The
  workflow triggers on every push to `main` and mints a GitHub App token first, so until
  the App, its two Actions secrets, and the split branch and tag rulesets exist, a
  release merge fails red on `main` rather than doing nothing. Setup:
  `docs/release-automation.md`.

- **Release tags are no longer signed.** CI creates an unsigned annotated tag; a
  `refs/tags/*` ruleset forbidding deletion and non-fast-forward substitutes immutability
  for the signature. No signing key exists in CI, and adding one buys rotation and
  revocation work for a guarantee the ruleset already gives. Hand-cut recovery tags are
  still signed by the local `tag.gpgsign`, so tag history is deliberately mixed.
  **Migration:** stop verifying signatures on release tags.

- **Releases no longer close referenced issues.** The old Phase 2 closed every `#NNN` the
  notes cited, with a comment linking the release. This repo tracks its work outside
  GitHub, so that step never had an issue to close — and the App is `Contents: write`
  only, so it could not close one anyway. Should a release ever cite an issue here, close
  it by hand.

- **Pre-release versions can no longer be published.** The manifest validator used to
  accept suffixes and build metadata that the release flow would then refuse; both now
  share one pattern (`scripts/ci/versions.py`), so `X.Y.Z` is all that passes either —
  import `RE_VERSION` rather than writing a third. No migration: a marketplace serving
  whatever sits on the default branch cannot offer a release candidate only to whoever
  asked for one. See ADR 008.

#### Added

- A release-notes helper (`scripts/ci/release_notes.py`) extracts the CHANGELOG's top
  entry and asserts it matches the plugin manifest, so a release cannot be tagged with
  one version and described with another. Its unit tests run in CI.

#### Changed

- **The `manifests` job does more and runs on more pull requests.** It now also runs the
  `scripts/ci` unit tests and the release-notes helper against the real CHANGELOG; its
  path filter covers `CHANGELOG.md`, the plugin manifests, any `SKILL.md`, and
  `scripts/ci/*`, so an ordinary skill-text change meets these checks too. New tests need
  a `test_*.py` name under `scripts/ci` to be discovered.

- **Design specs and plans are deleted before the pull request is created**, on the
  branch that added them — new guidance. Once the work lands, the code carries the *what*
  and an ADR the *why*.

- **`scripts/` is standard-library only, with no Python project at the repo root**
  (ADR 007) — now recorded rather than merely practised, with the convention that every
  test docstring names its scenario. If a script ever needs a dependency, the ADR's
  answer is a root project, **not** per-script PEP 723 metadata; either way every caller
  moves from `python3` to `uv run`.

## 1.3.0 - 2026-07-22

### For phx plugin users

#### Changed

- **`phx:creative-commits` writes grounded commit titles.** Titles now name the concrete
  change — so the log stays scannable under `git bisect` — instead of leaning on the
  emoji or metaphor to carry it. No action needed; messages simply read more literally.

- **`phx:writing-release-notes` applies conciseness gates.** Each candidate entry must
  earn its place — it has to be changelog-worthy and not already explained elsewhere — so
  generated notes come out shorter. Entries you might have expected can be gated out;
  breaking changes and their migration steps never are.

- **`phx:writing-adrs` records a revisit trigger on provisional decisions.** When an ADR
  parks a decision pending future conditions, the skill now names what would reopen it in
  the summary, so the ADR index alone tells a reader the decision is reopenable and when.

### For phx-claude-siat contributors

#### Breaking changes

- **A skill that declares tooling must wire a matching PR check.** CI now fails if a skill
  that ships tooling (`package.json`/`pyproject.toml`, or a `[tool.autohooks]` entry) is
  not mirrored in `.github/workflows/pr.yml`: the check looks for the skill's directory
  path and each declared tool name as plain substrings of the workflow. In the same change
  that adds the tooling, add a job to `pr.yml` that runs it, and make sure the skill's path
  and tool names appear there. See
  [ADR 005](docs/adr/005-mirror-declared-tooling-as-pr-checks.md) and
  [ADR 006](docs/adr/006-validate-the-declaration-to-catch-mirror-drift.md).

- **Branch protection must require only the `gate` check.** PR jobs are path-filtered and
  report `skipped` (not `success`) when their paths are untouched, so a required individual
  job would leave every PR that skips it hanging on a check that never runs. Point branch
  protection at the aggregate `gate` job alone; contributors otherwise just see a PR stuck
  on an unresolved check. See
  [ADR 005](docs/adr/005-mirror-declared-tooling-as-pr-checks.md).

#### Added

- **PR CI workflow** (`.github/workflows/pr.yml`): path-filtered jobs for the ADR index,
  plugin/skill manifests, and the `creative-commits` Python package, converging on a single
  required `gate` job.

- **Manifest validation** (`scripts/ci/validate_manifests.py`): checks plugin and
  marketplace manifests and skill frontmatter, and enforces the tooling/PR-check mirror
  above. Runs on every PR and again in the `releasing` skill's validation gate.

#### Changed

- **CI actions pinned to commit digests.** Every GitHub Action is pinned to an immutable
  commit SHA, with Renovate keeping the pins current
  (`helpers:pinGitHubActionDigests`).

- **The `releasing` skill is hardened.** New gates make a release fail sooner and for
  clearer reasons: it resolves the real `origin/main` rather than a stale local branch,
  requires local `develop` to match `origin/develop`, and verifies the back-merge reached
  the remote before calling the release done.

## 1.2.0 - 2026-07-16

### For phx plugin users

#### Breaking changes

- **Commits are now signed with your session's model, not `Claude Haiku 4.5`.** Drafting
  no longer runs in a Haiku subagent, so the `Co-Authored-By` trailer names the model that
  wrote the code rather than the one that phrased the message. GitHub's attribution
  follows the new value automatically, but tooling pinned to the `Claude Haiku 4.5`
  literal stops matching silently rather than failing. See
  [ADR 004](docs/adr/004-run-creative-commits-inline.md).

#### Changed

- **`phx:creative-commits` runs in your session instead of dispatching to a Haiku
  subagent.** Committing is faster, but drafting and the emoji reasoning now cost your
  session's model rather than Haiku's, and stay in its context. See
  [ADR 004](docs/adr/004-run-creative-commits-inline.md).

- **The first commit after each upgrade installs the skill's Python dependencies** — a few
  seconds, once per version.

- **`phx:writing-adrs` no longer copies the "do nothing" option's purpose note into
  records.** The note is guidance to the drafter, not content for the ADR.

#### Fixed

- **Commit emoji no longer repeat ones recent commits used.** `emoji-seed` prints an
  off-limits list, but only the seed emoji was barred from the final pick and the list
  itself was ignored. It now binds the pick.

- **`phx:writing-adrs` no longer writes reference links that silently break.** Links
  resolve from `docs/adr/`: peer ADRs are bare filenames, and repo-root paths need a
  `../../` prefix.

- **`phx:creative-commits` can no longer pair one version's instructions with another
  version's script.** The mismatch was silent but never triggered — `seed.py` has been
  identical in every release — so no action is needed. See
  [ADR 003](docs/adr/003-locate-skill-assets-relative-to-skill-directory.md).

#### Removed

- **The plugin ships no hooks.** Its only hook wrote the plugin-root pointer that the fix
  above retires. `~/.claude/plugins/data/phx.root` is no longer written or read; copies
  left by earlier versions are inert and safe to delete.

### For phx-claude-siat contributors

#### Breaking changes

- **Skills must reference bundled files from the skill's own base directory.** The
  `phx.root` pointer is gone, so a skill that still locates a script through it runs the
  wrong version's code and exits 0 — it fails silently. Use
  `uv run --project <this skill's directory>`, substituted at run time, and let a
  dispatching skill's subagent load the skill itself, since loading is what reports the
  base directory. Nothing in-repo is affected; this binds new skills and any you maintain
  elsewhere. See [ADR 003](docs/adr/003-locate-skill-assets-relative-to-skill-directory.md).

#### Changed

- **Cost alone no longer earns a delegation.** Parallelism or independence must earn it;
  cost may then only choose which model serves it. See
  [ADR 004](docs/adr/004-run-creative-commits-inline.md).

- **Working-tree liveness is judged solely from the base directory reported at skill
  load.** A live base directory means the plugin is served from the working tree — not
  that the skill text is current, which needs `/reload-plugins` after every edit.

## 1.1.1 - 2026-07-15

### For phx plugin users

#### Fixed

- **`phx:creative-commits` no longer runs the commit title together with the body.**
  Messages came out with no blank line after the title, so git — which treats the first
  paragraph as the subject — absorbed the bullets into it, and `git log --oneline` showed
  a 250–350 character subject instead of a ~50 character title. The skill's worked example
  contradicted the rule it sat under, and agents followed the example.

  **Existing commits are not corrected retroactively**; list them with
  `git log --oneline | awk 'length > 72'`. Repairing them rewrites history and changes
  SHAs, so confine it to branches you have not shared.

### For phx-claude-siat contributors

#### Breaking changes

- **The release gate now reads the real `origin/main`, and hard-fails when `develop` is
  behind it.** The divergence check tested the *local* `main` — a branch the release flow
  never checks out — so a `main` left behind by an earlier release silently passed, and
  the same stale reference set the release-notes range. No published notes were affected.
  Every check now fetches and reads `origin/main`, so the gate touches no local branch and
  works in fresh clones and worktrees, where the old check errored outright.

  Merging a release PR leaves a merge commit on `main` that `develop` lacks, so
  `origin/main` stops being an ancestor of `develop` the moment any release lands. The
  `releasing` skill now back-merges as its final step, so this resolves itself from here
  on — but a release cut *before* this version left `develop` behind, and the gate refuses
  the next release until you repair it.

  **Migration.** Check whether this affects you:

  ```
  git fetch origin && git merge-base --is-ancestor origin/main develop && echo "up to date"
  ```

  If that prints nothing, back-merge by hand:

  ```
  git switch develop && git merge --no-edit origin/main && git push
  ```

  It carries no content, so expect an empty diff. A conflict means the release PR was
  squashed or rebased rather than merged: resolve in favour of `develop` and commit, since
  the gate only needs `origin/main` reachable from `develop`. This repo's `develop` was
  repaired as part of this release, so it needs nothing.

## 1.1.0 - 2026-07-05

### For phx plugin users

#### Added

- **`phx:writing-adrs` gained reference-linking guidance.** ADRs link GitHub issues/PRs,
  web references, and code symbols on first mention using reference-style Markdown links,
  with a worked example and checks for orphaned or duplicate links during the skill's own
  review pass.

#### Changed

- **`phx:creative-commits` drafting moved to an isolated, lightweight (Haiku) subagent**
  instead of the calling session, for lower cost and cleaner context — falling back to the
  calling session only where dispatch is unavailable. Message format and quality are
  unchanged; wording may vary slightly run-to-run, since a fresh model instance drafts
  each message.

### For phx-claude-siat contributors

#### Changed

- **Project-local skills relocated from `.claude/skills/` to `.agents/skills/`**, keeping
  the directory agent-agnostic. `.claude/skills` is kept as a **symlink**, so normal reads
  and edits still work — but tooling that doesn't follow symlinks (`tar`/`zip` archiving,
  Docker `COPY`, `find -type d`) sees an empty or literal-text result at the old path, as
  do Windows checkouts without `core.symlinks=true`.
- **`.gitignore` now excludes `.worktrees/`**, so git-worktree workspaces no longer show
  up in `git status`.

## 1.0.0 - 2026-07-03

### For phx plugin users

#### Breaking changes

- **`phx:writing-plans` now makes real commits to your repo** — creating the feature
  branch and worktree, and committing any coding-agent-facing documentation changes
  (`AGENTS.md`, ADRs, skills) — before the plan file itself is written or reviewed.
  Previously the worktree and branch appeared only once execution began, and doc updates
  arrived as a plan task you could review before it ran. Even if you decline the worktree,
  a feature branch is still created so those commits never land on `main`.
  **Migration:** don't expect to review a plan before anything touches your repo — the
  branch, worktree, and any documentation commits now precede it. Any tooling or reviewer
  assuming the plan file is the first commit on the branch needs updating too.

#### Added

- **New skill: `phx:writing-release-notes`** — drafts grouped, audience-reviewed release
  notes and an advisory semver level for a commit/PR/issue range. It is deliberately
  conservative about breaking changes and stays neutral about where notes get published,
  so it composes into any project's release process. See the skill for its `base`, `path`,
  and `model` arguments.

#### Changed

- **The marketplace catalogue entry no longer carries a `version` field**
  ([ADR 001](docs/adr/001-co-locate-marketplace-and-plugin.md)). Install and update
  behaviour is unchanged — `plugin.json` already took priority over it — but external
  tooling reading the version from `marketplace.json` should read `plugin.json` instead.

### For phx-claude-siat contributors

This is the first tagged release, so "breaking" below means *if you already have a
checkout and habits from before this release, here's what changes under you* — not that a
previously published contributor workflow is being broken.

#### Breaking changes

- **Local development now requires launching with `--plugin-dir ./`, not adding the repo
  as a marketplace.** **Migration:** launch with `--plugin-dir ./`, and run
  `/reload-plugins` after edits.
- **`CLAUDE.md` is now a symlink to `AGENTS.md`**, so Codex, Gemini, and Claude read one
  maintainer-guidance file rather than a copy each. **Migration:** edit `AGENTS.md` only.
  Where symlinks don't resolve (some Windows setups, zip downloads instead of
  `git clone`), read `AGENTS.md` directly.
- **A `pre-commit` hook now regenerates `docs/adr/INDEX.md` whenever an ADR is staged —
  but it isn't installed on clone.** Do nothing and the hook stays inactive while
  `INDEX.md` silently goes stale after your next ADR commit, with no error to flag it.
  **Migration:** activate it once per clone with `git config core.hooksPath .githooks` (it
  carries across worktrees), then re-commit if the index already went stale.
- **Working-tree liveness is no longer read from `~/.claude/plugins/data/phx.root`.** That
  pointer can report cached even when the tree is live, so anyone still checking it gets a
  wrong answer. **Migration:** judge liveness from the base directory the first-loaded
  `phx:` skill reports — a skill is non-live if it's unavailable or loads from a
  `…/plugins/cache/…` path. See `AGENTS.md`.

#### Added

- **Architecture Decision Records**, under `docs/adr/` and indexed in `docs/adr/INDEX.md`.
  The first records keeping the marketplace and plugin co-located, with the version owned
  solely by `plugin.json` ([ADR 001](docs/adr/001-co-locate-marketplace-and-plugin.md)).
- **`AGENTS.md` gained "Testing skills", "Branches", and "Language and Style" sections**,
  documenting the `main`/`develop`/feature-branch model, NZ English, comment placement,
  and the gotchas of RED/GREEN-testing skills with subagents.
