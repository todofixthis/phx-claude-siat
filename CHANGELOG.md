# Changelog

## 6.0.0 - 2026-09-04

### For phx plugin users

#### Breaking changes

- **`writing-adrs` now needs `python3` (3.10+) on your `PATH`.** The skill ships a bundled
  tool and session hooks that do its mechanical work — nothing else to install.
- **The skill's workflow changed:** the agent runs the shipped tool's commands
  (`new`, `check`, `supersede`, `discharge`, `renumber`, …) rather than hand-editing your
  `docs/adr/` files or index. If your own tooling or docs assumed the old hand-edit
  workflow, update them. If you already have a hand-written `docs/adr/`, the hooks stay
  silent until you bring it into the new format with one `adr.py index` pass.
- **`revisit-discharged-by` is now a list**, one entry per ADR that spent a condition — a
  scalar value fails `check` until you rewrite it as a list.
- **A frontmatter value GitHub's YAML renderer would misread now fails `check`** — an
  opening indicator character, `: ` or ` #` inside a value, or a trailing colon. Reword the
  value.
- **A lookup against a path outside your repository now answers silently rather than
  erroring.** Anything scripting against `adr.py for` should check for empty output rather
  than a non-zero exit.

#### Added

- **`writing-adrs` is now self-contained.** Nothing to set up: your agent's first ADR
  creates `docs/adr/` and a generated `INDEX.md`, and from then on session hooks keep the
  index current, hand the agent the decisions binding a file it touches, and flag a `scope`
  entry a move or delete left dangling.
- **A documented recipe for using the ADR tool outside the plugin:**
  `uvx --from 'git+https://github.com/todofixthis/phx-claude-siat@<tag>#subdirectory=skills/writing-adrs' phx-adr check`.

  Reasoning in [ADR 022](https://github.com/todofixthis/phx-claude-siat/blob/3affcff/docs/adr/022-ship-the-adr-tooling-and-hooks-with-the-skill.md),
  [023](https://github.com/todofixthis/phx-claude-siat/blob/3affcff/docs/adr/023-let-a-shipped-tool-write-what-it-wholly-owns.md) and
  [025](https://github.com/todofixthis/phx-claude-siat/blob/3affcff/docs/adr/025-deliver-binding-decisions-by-hook-at-first-touch.md).

### For contributors

#### Breaking changes

- **`scripts/adr/` is gone.** Run `python3 skills/writing-adrs/adr.py check` (or `index`,
  `for`) in place of `python3 -m scripts.adr.generate_index` — the pre-commit hook and
  `pr.yml`'s `adr` job already do. `scripts/frontmatter.py` is now a symlink to
  `skills/writing-adrs/frontmatter.py`; edit the parser at that target.

#### Added

- **Six new ADRs (022–027)** record the shipped-tool architecture: bundling the tool and
  hooks with the skill, what a shipped tool may write, resolving its root from the path in
  hand, delivering bindings by hook at first touch, reporting findings by delta from a
  session baseline, and anchoring a script to the tree it acts on (superseding ADR 016).
  ADR 019 is superseded; 013, 017 and 021 gain consequences or renewed conditions.
- **`skills/writing-adrs` now carries its own `pyproject.toml`, `uv.lock` and pytest suite**
  (238 tests), gated in CI alongside `ruff`/`black` and picked up by the release gate's
  per-skill test loop — reproduce it locally with `uv run pytest`/`ruff check .`/`black
  --check .` from `skills/writing-adrs/`.
- **CI's `adr` job now runs `adr.py check` directly**, and a new step validates the `uvx`
  consumer recipe above.

  Reasoning in [ADR 024](https://github.com/todofixthis/phx-claude-siat/blob/3affcff/docs/adr/024-resolve-the-repository-root-from-the-path-in-hand.md),
  [026](https://github.com/todofixthis/phx-claude-siat/blob/3affcff/docs/adr/026-report-findings-by-delta-from-a-session-baseline.md) and
  [027](https://github.com/todofixthis/phx-claude-siat/blob/3affcff/docs/adr/027-anchor-a-script-to-the-tree-it-acts-on.md).

## 5.1.0 - 2026-09-02

### For phx plugin users

#### Breaking changes

- **Plan review now runs the commands a plan names.** Where a task names a build, lint,
  type-check, test or CI step, `phx:writing-plans` has its reviewer run it in the plan's
  worktree rather than read it. Those commands now execute on your machine, taking time and
  touching whatever they touch. Reading alone cannot catch a broken verification step: a
  command failing because the task's own code does not exist yet is expected, where one that
  cannot run at all — a bad path, an unknown flag, missing config — is a blocker.
- **Fully-mechanical plans now execute inline without asking first.** Where every task writes
  its file contents in full and leaves the executor no discovery or decision,
  `phx:writing-plans` skips the execution-handoff question and runs the plan inline rather than
  spawning a subagent per task. If you used that question as a checkpoint before anything was
  written, ask for subagent execution explicitly.

#### Added

- **A path-scoped rule now counts as a defence for an archived decision**, where
  `phx:writing-adrs` previously admitted only two: a comment wherever a breach would be
  authored, and a breach large enough to need its own ADR. Such a rule is a file whose glob
  list makes your harness inject it when a matching file is read. A new section covers what
  loads one, which routes miss it — a reader working from a shell meets nothing — and that an
  ADR archived on a rule must name the rule file in `scope`.
  Reasoning in [ADR 018](https://github.com/todofixthis/phx-claude-siat/blob/51ee504/docs/adr/018-admit-a-path-scoped-rule-as-an-archival-defence.md).
- **A rule for linking third-party dependencies**: cite the dependency's upstream source, not a
  gitignored local install path no one else can reach.
- A pointer to a reference implementation of the ADR index generator and its tests, for anyone
  porting the contract.

#### Changed

- **Renumbering an ADR is now permitted where nothing cites its number yet**, and a new
  `Renumbering an ADR` section sets out the procedure — when a collision appears and why
  nothing surfaces it, which of the two ADRs may move, the six places that name a number, and
  what to do when both are cited. Reuse always breaks citations, where renumbering breaks them
  only once the number has been cited; never-reuse stays absolute.
- **`phx:writing-adrs` no longer tells you when your index generator runs.** It previously
  asserted that the generator runs on every pull request touching `docs/adr/` and locally
  wherever the pre-commit hook is installed; it now tells you to find out what triggers your
  own. If you built a workflow on that claim, check it.
- **Dependencies:** the bundled tooling for `phx:creative-commits` and `phx:nz-english` moves
  to newer pinned versions. Both resolve from their own lockfiles at run time, so this changes
  what installs on invocation; no declared requirement changed.

### For contributors

#### Breaking changes

- **Deferred work is no longer filed as a GitHub issue** (ADR 020). It goes in
  `docs/backlog/<slug>.md`, one file per item; an item that is not there is recorded nowhere.
  The tracker stays enabled for Renovate and for people who installed the plugin, so nothing
  stops you filing one — but nothing routes an agent there, so an issue holding deferred work
  goes unread. Asked to file one, an agent now writes the backlog file instead and says so; it
  complies only if you repeat the request having heard that.
  **Three cases override the default:** a condition that would reopen a settled decision goes
  in that ADR's `revisit-when`; a finding about whether it has fired goes in a
  `## Revisit watch` section in that ADR's body; and a constraint a future editor must meet
  goes in a comment where they will meet it. **Two standing habits come with it:** read the
  backlog before starting on an area, not only when deferring from one, and name in an item's
  prose the paths it binds — `rg <area> docs/backlog/` is the whole routing mechanism, so an
  item naming no path cannot be found. **Migration:** convert any open issue holding deferred
  work. This repository's three — `#28`, `#38` and `#39` — are done; only two became backlog
  files, `#28` becoming the `## Revisit watch` in ADR 007.
- **The ADR index generator now rejects two states it used to accept**, so a branch carrying
  either fails the `adr` job, and the pre-commit hook too where your commit stages an ADR.
  **Two ADRs sharing a number:** numbers are allocated by reading the directory, so two
  branches open at once take the same one; every reference is by number, so both files resolve
  and the wrong one reads as correct. A rebase produced exactly this during the cycle.
  **A heading number disagreeing with its filename:** renumbering is two edits, and the index
  takes its number from the filename and its title from the heading, so a half-done renumber
  renders a self-consistent row naming a decision that does not exist. Numbers compare by
  value, so `001` and `1` are the same ADR.
  **Migration:** run `python3 -m scripts.adr.generate_index`. It names both files in a collision
  and both numbers in a mismatch, but not which file to move — the file it names first is first
  in filename order, not first authored, so decide that against the rule in `phx:writing-adrs`,
  and follow that skill's new `Renumbering an ADR` section, since a renumber has to move every
  citation of the number, not just the filename and heading.
- **ADR scope is now validated on every pull request** (ADR 021), where the `adr` job previously
  ran only for changes under `docs/adr/` or `scripts/`. The generator revalidates every ADR's
  `scope`, so **deleting or renaming a file named in an ADR's `scope` now means updating that
  ADR in the same pull request** — and a pull request touching neither directory can fail on
  scope rot that predates it.

#### Added

- **`docs/backlog/`**, with a README fixing the shape of an item and the work deferred during
  this cycle.
- **Four decisions recorded:** ADR 018 admits a path-scoped rule as an archival defence, ADR 019
  rejects generating those rules from ADR frontmatter, ADR 020 moves deferred work into the
  repository, and ADR 021 validates scope on every pull request. ADR 013 gains a note that ADR
  021 narrows one of its known tensions.
- **A standing question on ADR 007.** Its new `## Revisit watch` records the stdlib-only
  constraint as assessed and *not* fired, and asks that at the next change under `scripts/`,
  however small, you re-ask two questions: whether anything there approximates a grammar rather
  than parsing it, and whether the workflow substring-match in `validate_manifests.py` has
  caused a miss in practice.

#### Fixed

- **The release recovery step could close a pull request instead of an issue.** `gh issue view`
  and `gh issue close` resolve a pull-request number through the same endpoint rather than
  refusing it, so the old instruction, run against an unmerged pull request, would close it and
  report success. ADR 020 made that likelier: with deferred work now a file, a `#NNN` in the
  notes is usually a pull request.

  The step now resolves every reference before acting on any, reads the exit code rather than
  the printed value, and warns that a zero exit answers for this repository alone — a bare
  `#NNN` meaning another repository's issue resolves here to whatever local object holds that
  number. It also moved from the failed-run recovery list into the steps that follow a
  successful run; the recovery list gains a **Steps still owed** bullet in its place, because a
  release finished by hand passes through none of those steps.

## 5.0.0 - 2026-08-26

### For phx plugin users

#### Breaking changes

- **`phx:nz-english` now requires `python3` and `git`, and runs a tool that ships beside the skill.** The skill previously required the coding agent to execute nine `rg` commands by hand; it now runs one bundled command. There is nothing to *install* — the tool is standard-library only, with no virtualenv to build — but both programs must be on your `PATH`. It needs **Python 3.10 or newer**, checked at startup, and shells out to `git ls-files` to decide which files to sweep.

  **Migration:** none, where `python3` and `git` are both present. Where either is missing, or the run fails for any other reason, the skill now **stops and reports the problem** rather than falling back to the old commands. Those commands encoded a guard character and a sixty-word false-positive list that a retyped search does not reproduce, so improvising them back would cover less than the sweep it replaced.

#### Changed

- **One invocation replaces the nine searches.** The agent runs the bundled tool once and reads its report, which is grouped by substitution row and prints **every** row including those with nothing to show — so a search that found nothing is visible rather than absent, which is how a sweep that never ran used to pass for a clean one. Its exit code distinguishes a clean tree from hits to triage, a failed run, and a malformed invocation.
- **The report's header carries the diagnostics.** It names the path swept, how many files were read, and whether `git` or a directory walk supplied them. A file count far below what the repository holds is the one failure the tool cannot catch by itself — an ignored subtree is invisible to it, exactly as it was to `rg`.
- **Known false positives are collapsed rather than printed**, so the report is far shorter than the old commands' output, and a flag expands them again. Rows needing a decision — `license`, `program`, `practice`, `meter`, `judgment` — are marked read-don't-apply rather than left to the agent's memory.
- **Verifying a rename no longer needs a guard character worked out by hand.** Given the old spelling, the tool finds its row, computes the guard, and reports every surviving reference.
- **Proving the searches still work is a flag.** The tool runs its patterns over controls that ship with the skill, replacing the two control files the agent used to write by hand before every sweep.
- **A sweep that reads no files is an error rather than a clean result.** Aimed at a path it excludes, the tool says nothing was read instead of reporting a clean tree it never looked at.
- **Long reports stay bounded.** Hits are capped per row while the counts stay exact, so a tree with a great many of them still produces a report worth reading.
- **Sweeping a very large repository can take minutes**, where an ordinary one takes seconds. A single Python pass is slower than nine `rg` processes, though not obviously slower than the whole exchange it replaces, since generating nine commands cost tokens and a round trip of their own. Where it does matter, the tool accepts explicit paths rather than a whole tree — a pre-commit hook can hand it just the staged files.

- **`phx:writing-release-notes` now writes for a human reader explicitly.** Agents read release notes too, and disambiguate better than people do, so writing for the person is what makes the notes serve both. The rule names the trap it exists to catch: where a product is invoked *through* a coding agent, "you" slides onto whoever performs each step, and the reader ends up told they used to type commands an agent typed.

#### Fixed

- **The `-og` row now catches camel-cased names such as `dialogUrl`.** The hand-run search was case-insensitive, so its guard excluded a following `U` as well as a `u` and the name reached no search at all — a miss the skill documented and had the agent convert by hand. The cost is that a SCREAMING_CASE `DIALOGUE` is now reported; over-reporting is the direction this skill prefers.

### For contributors

#### Breaking changes

- **Editing `skills/nz-english` now needs `uv` and Python 3.12 or newer**, including for prose-only edits. The directory previously had no tooling at all; it now ships a `pyproject.toml` and a committed `uv.lock`, and CI runs `pytest`, `ruff`, `black` and `uv lock --check` against it. Change its `pyproject.toml` without re-locking and the build goes red.
- **`skills/nz-english/*` is newly in `pr.yml`'s path filter.** A prose-only edit to that skill now runs the whole Python job where it previously ran nothing.
- **The substitution table in `SKILL.md` is parsed by a test**, so its *structure* is now a contract. Cosmetic reformatting is safe; what breaks the suite is renaming or removing the `## Substitutions` heading, moving the table out of that section, converting it away from pipe-delimited rows, or inserting a column before the US column.
- **Adding or changing a row is a three-place edit**: the table in `SKILL.md`, `table.py`, and `tests/fixtures/us/prose.md` — every word inside an alternation must appear in the US fixture. Check `tests/fixtures/nz/prose.md` too where the new word has an already-correct form. The coupling tests in `tests/test_table.py` fail when these drift.

#### Added

- **`skills/nz-english` gains a uv dev project and 95 tests.** It is not an installable package — no `[build-system]`, no console script, no runtime dependencies — it exists to give the bundled tool a dev toolchain matching `skills/creative-commits`.
- **[ADR 017](https://github.com/todofixthis/phx-claude-siat/blob/d65cb1b/docs/adr/017-move-a-skills-deterministic-steps-into-shipped-code.md) records the general rule** this is the first instance of: a skill's deterministic steps move into code that ships with the skill, needs no install step, and reports rather than edits. It also records why Vale was assessed and rejected.

#### Changed

- **A second skill now ships tooling, and both gates widened to take it.** `pr.yml`'s `python` job is a matrix over the two skill directories, spelled as full paths because `validate_manifests.py` looks for each one as a plain substring of the workflow; a change to either skill runs both legs. The release gate runs each skill package's suite from inside its own directory, over a list derived from the skills that ship a `pyproject.toml`.

  A third tooling skill is half automatic: the release gate picks it up with no edit, the `pr.yml` matrix leg ADR 005 requires is still added by hand, and a skill shipping a `package.json` rather than a `pyproject.toml` needs its own command in both.
- **ADR 006's revisit trigger is narrower.** It named two conditions, either of which reopens the decision on its own. "A second skill ships tooling" fired here and has been cut; "a skill ships a `package.json` rather than a `pyproject.toml`" is untouched and still live.

## 4.1.0 - 2026-08-22

### For phx plugin users

> **Check the notes you have already published.** The two `phx:writing-release-notes`
> changes below correct output that 4.0.0 and earlier produced, and neither repairs an
> entry already written. Notes drafted before this release may carry a `Fixed` entry for a
> defect that never shipped, and any link in them pointing at a **branch** rather than a
> commit or tag — `…/blob/main/…` and its equivalent on whatever host and default branch
> you use — is not guaranteed to serve what it served when you published it.

#### Added

- **`phx:writing-release-notes` now requires every link in the notes to be pinned to a commit or a tag, and read rather than merely resolved.** A branch reference is wrong at both moments it is read: while the release is under review it still serves the pre-change file, and once the entry is frozen the branch moves on without it. Where a project squash- or rebase-merges, a commit on the release branch does not survive either, so pin an already-published tag or add the link after the release commit exists.

#### Changed

- **`phx:writing-adrs` marks its linking rule as out of reach of the one above.** Without this, an agent that has just read the pinning rule has every reason to start pinning an ADR's links too. The added clause explains why it should not: an ADR describes a decision still in force, so following a moved path keeps it true, where an entry about one released version would be falsified by the same repair.

#### Fixed

- **`phx:writing-release-notes` reported defects that never shipped as fixes.** It reads pull-request bodies to work out what changed, and a pull request describes the *work* rather than the released state — so a defect the same branch introduced and repaired arrived looking exactly like a fix. The notes then carried migration steps sending readers to audit work they never did, against tooling no released version ever had.

  4.0.0 left this to a reviewer's judgement at the review pass. It is now a gate at drafting, ahead of the two that judge length: a `Fixed` entry survives only where the defect is genuinely in the base's copy of the file, read rather than assumed. Its verdict is final — where 4.0.0 would publish anything a pull request called a breaking change, the gate can now suppress one, because a break introduced and repaired before release broke nobody.

## 4.0.0 - 2026-08-21

### For phx plugin users

#### Breaking changes

- **`phx:nz-english` now renames the identifiers a repo defines** — parameters, methods, classes, attributes, locals and filenames — where it previously refused to touch a public API identifier. A sweep that used to edit prose alone can now rename symbols across a tree.

  *Migration:* a project wanting US-spelled identifiers states that convention in its `AGENTS.md` or `CLAUDE.md`, in a line such as "This project follows US English spelling, identifiers included". The skill reads both at the root plus any nested file covering the subtree it is sweeping, and a nested file governs its own subtree. Doing nothing is the risk, and deliberately so: an already US-spelled tree is what the skill is invoked to change, so it cannot double as the opt-out signal. There is no dry-run — run it on a clean tree and read `git diff`, which will be larger than this change alone accounts for, because the substitution table grew too (below).

  Whole trees are excluded, which is also new: vendored and third-party directories, test fixtures that assert on US spelling, `CHANGELOG.md` and past release notes, and the skill's own directory. Names fixed outside the repo are still skipped, and a third category is new: names the repo defines that something outside holds a copy of — a serialised field name or database column, the repo's own CLI flags and environment variables, public API, a filename a branch-protection rule names. Those are skipped and listed in the agent's report, each needing its own migration.

- **`phx:writing-adrs` replaces the `tags` frontmatter field with `scope`**, which names the paths a decision binds, so a decision is found from the file you are editing rather than from a word you guess.

  *Migration:* replace each ADR's `tags` with the paths it binds — exact paths or directory prefixes, never globs, and give a directory its trailing `/`. Where you generate an index from that frontmatter, the field it reads has moved; [this repo's own generator](https://github.com/todofixthis/phx-claude-siat/blob/4575ec935b5cb0ddcb651c47eace7b7bafa6acd7/scripts/adr/generate_index.py) is a working example, and it rejects a stale `tags`, a glob, an entry naming nothing on disk, and a directory missing its slash. Without a generator none of that is checked — see the note under Added.

#### Added

- **`phx:nz-english` gained seven substitutions it never had**: `-yze`→`-yse`, `skeptic`→`sceptic`, `judgment`/`acknowledgment`→`judgement`/`acknowledgement`, `pretense`→`pretence`, `sizable`→`sizeable`, `-eler`→`-eller`, and the bare verbs `fulfill`/`enroll`→`fulfil`/`enrol`, whose inflections keep the double `l` and stay as they are. These are conversions the skill never previously made, so a sweep will change words earlier sweeps left alone. One caveat on the new `judgment` row: a court's `judgment` keeps that spelling in NZ legal usage.
- **`phx:receiving-code-review` gained the machinery it only ever described.** It now documents a helper for posting replies, each carrying a signed footer; a verification step that asks which threads you do not have the last word on, rather than whether you replied at all; a guard naming the repository before anything is read or posted, since `GH_REPO` silently outranks the checkout you are standing in; issue comments as a further feedback surface, and a command for the review bodies it previously only warned were easy to miss; and rules for skipping bot threads and your own. Every block is POSIX shell and behaves identically under `bash`, `zsh` and `dash`.
- **`phx:writing-adrs` records revisit triggers in frontmatter.** `revisit-when` names the condition that would reopen a decision and `revisit-discharged-by` names the ADR that spent it, with a workflow for discharging, narrowing, arming and superseding a trigger. It also gained a rule for citing decisions from code comments — including that the comments are written in the same change that archives a decision, or the decision is not archived — and requires any cost two or more options share to be stated once, above Option 1, rather than repeated in each.

  These are conventions, not checks. The skill says so plainly: without a generator reading the frontmatter, anything it describes as failing goes unnoticed instead.

- **`phx:writing-release-notes` makes its reviewers verify rather than read.** Each audience-surrogate reviewer now checks the block's claims against the thing described — the code at both ends of the range, the workflow file, the live setting — and is handed the pre-image, since a diff shows what a change became and never what it displaced. Where a reviewer's budget runs short, verification outranks clarity.

#### Fixed

- **`phx:nz-english`'s searches hung, and missed words its own table promised.** None of its five commands took a path, so ripgrep read standard input — a terminal for a human, an open pipe for an agent, where it blocks until killed rather than searching. Separately, the searches never covered much of the table: bare `catalog`, `dialog` and `analog` had no search at all, `-ize` reached only seven stems plus `ization`, and `cataloged`, `cataloging`, `tumor`, `rumor`, `savior` and `meager` escaped every command. Coverage is now a stated rule — a row and its search ship together — and two control files, one US-spelled and one NZ-spelled, prove the searches can fail before you believe a clean result.
- **`phx:receiving-code-review`'s documented `gh api` calls 404'd.** Both left `{pr}` as a placeholder, and `gh` substitutes only `{owner}`, `{repo}` and `{branch}`.

### For contributors

#### Breaking changes

- **Every function in `scripts/` that resolves a *default* path now requires a `repo_root` argument**, read from `__file__` at one place per module — the `__main__` line. A script whose path is a required argument, like `scripts/dev/mutate.py`, is outside the rule and threads no root. Expect rebase conflicts on an in-flight branch touching `scripts/`. The visible fix: `python3 -m scripts.ci.validate_manifests` run from another directory used to validate whichever tree the caller stood in, and now validates the one it ships in. Recorded as ADR 016, superseding ADR 015.

  One CLI contract moved with it: `release_notes.py` resolves a relative `--changelog` and `--plugin-manifest` against the repo root now, where they used to resolve against the working directory. `--out` still resolves against the working directory, deliberately, so a caller can write notes where it stands.

- **Test modules must pass a fixture root and never `chdir`**, reversing `.agents/rules/testing.md`, which previously *required* a `chdir` into a fixture repo for a module holding relative path constants. A path-resolving module now owes two anchor tests, and only the second — asserting the anchor reaches this repository — catches `parents[1]` written for `parents[2]`. An in-flight branch whose new tests `chdir` is written against a superseded rule, and ADR 015, where a contributor would go looking, is now `Superseded`.

- **ADR frontmatter must carry `scope`, and `tags` is now rejected outright** rather than ignored, so a half-finished migration fails in both directions. `scope` takes exact paths and directory prefixes ending in `/`, never globs, and every entry must exist on disk. `scope: []` is valid and means the decision binds no path. This is the enforcement side; the convention itself ships in `phx:writing-adrs`.

  **Those last three checks fire only on a full index run** — locally when you stage an ADR, in CI when the change touches `docs/adr/`, `scripts/` or `.github/workflows/` — and none apply to a `Superseded` ADR. So renaming or deleting a path some ADR scopes, and `AGENTS.md`, `.githooks/`, `.claude-plugin/marketplace.json` and `skills/creative-commits/` are all scoped today, passes your commit and your pull request, then fails for whoever next stages an ADR, in a file they did not touch.

#### Added

- **`python3 -m scripts.dev.mutate`** disables one check in place, runs the suite, and reports CAUGHT, MISSED, INVALID or UNKNOWN — only CAUGHT exits 0, so a sequence can be scripted rather than read by eye. It edits the working tree in place: the source is restored from a `finally` and from SIGTERM/SIGHUP, and after a hard kill the recovery is `git restore <file>`, the mutation being one anchor replaced once.
- **`python3 -m scripts.adr.generate_index --for <path>`** reports which decisions bind a path, `Archived` ones included — the only surface on which those appear at all.
- **`revisit-when` and `revisit-discharged-by` ADR frontmatter fields**, the first naming the condition that would reopen a decision and the second the ADR that spent it. Declaring a discharge with no trigger to spend is an error, and a discharged trigger blanks the row's Revisit cell rather than filling it.
- **ADRs 013–016**: keying decisions to paths, citing decisions from code comments, and the two path-anchoring decisions.

#### Changed

- **`.githooks/pre-commit` now reports binding decisions on every commit**, where it used to exit early unless an ADR was staged. The report is advisory and never blocks. It only runs in a clone that has had `git config core.hooksPath .githooks` set, which remains a per-clone step.
- `docs/adr/INDEX.md` trades its Tags column for Scope and gains a Revisit column.
- The project-local `releasing` skill no longer asks for `--plugin-dir ./` except where the release itself changes `phx:writing-release-notes` or `phx:creative-commits`; it requires the version bump to be an in-place string replace rather than a re-serialise, which would reformat the manifest around the one line that changed; and it gains a diagnosis step for a pull request whose checks are green but whose merge state is `BLOCKED`.
- `python3 -m scripts.adr.generate_index` now rejects an unrecognised argument rather than ignoring it.
- `.agents/rules/testing.md` makes the mutation step a scripted one and adds a subagent test-coverage audit where a change adds a module and its tests together.
- `astral-sh/setup-uv` moves from v9.0.0 to v10.0.1, digest-pinned as the repo pins every action. No workflow here is affected by v10's caching change, which applies to `pull_request_target`, `workflow_run` and `release` events; the only workflow using the action runs on `pull_request`.
- `ruff` moves from 0.15.21 to 0.16.4, whose nested-context-manager and non-raising-subprocess lints the `creative-commits` package now satisfies.

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
