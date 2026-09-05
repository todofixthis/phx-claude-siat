# phx-claude-siat — maintainer guidance for coding agents

> `CLAUDE.md` is a symlink to this file — edit `AGENTS.md` only.

This repo **is** the `phx` Claude Code plugin (skills and `.claude-plugin/`
manifests); its skills are invoked as `phx:<skill-name>`.

## Branches

- `main` — releases only; merge from `develop` via PR
- `develop` — main development branch
- Feature branches off `develop` for all new work

## Language and Style

NZ English throughout — spelling, not just prose. Place comments on the line
preceding the code they document, not as trailing comments.

## Python

- The repo root is a uv workspace (ADR 028): one root `pyproject.toml` and `uv.lock`
  resolve `scripts/` and every skill that ships its own `pyproject.toml`. Toolchain pins
  and `black`/`ruff` settings live once at the root; a skill's own `pyproject.toml` keeps
  only what makes it independently buildable — `[project]`, `[build-system]`, its entry
  point, `[tool.autohooks]`. `scripts/` stays stdlib-only (ADR 007) — the workspace gives
  it a dependency path, not a dependency.
- `scripts/` is a package (ADR 011), so run a script as `python3 -m scripts.<area>.<name>`
  from the repo root — a path invocation fails to import, and this is unchanged by the
  workspace, since `scripts/` still declares nothing to install. The `scripts/` suite is
  `python3 -m unittest discover -s scripts -t . -p 'test_*.py'`. After `uv sync --locked`
  at the repo root, each skill's checks run as `uv run --directory skills/<name> pytest`,
  `ruff check .` and `black --check .`, all three gated by `pr.yml`.
- `scripts/frontmatter.py` is a symlink into `skills/writing-adrs/`; edit the parser there.
- Every function annotates its return type and its named parameters, `-> None`
  included; `*args` and `**kwargs` are left bare. Test functions are exempt from
  both; the helpers and fixture classes serving them are not.
- Where a literal names something a module already defines a constant for — a
  filename, a path, a header — import the constant instead, tests included. A
  rename then fails in one place rather than passing against a stale string. Give a
  literal a constant of its own once a second use appears.
- Test conventions live in `.agents/rules/testing.md`; read it before writing or
  changing tests.

## Skill layout

Published skills live in `skills/<name>/` and ship with the plugin and marketplace,
invoked as `phx:<name>`. Project-local skills live in `.agents/skills/<name>/` (with
`.claude/skills` kept as a symlink to that directory, for tooling that still expects
the old path) — loaded in this repo but shipped with neither the plugin nor the
marketplace, and invoked unprefixed. Releases are cut by the project-local `releasing`
skill.

## Dogfooding: is the working tree live?

Claude loads the **published, cached** plugin unless launched with `--plugin-dir ./`;
otherwise edits and tests in this repo have no effect. Don't probe for this — let the
first `phx:` skill you load reveal it: the working tree is **not** live if the skill
is unavailable (`Unknown skill`) or loads from a `…/plugins/cache/…` base directory.
If so, **and this session edits or tests anything under `skills/`**, stop and ask; the
user may relaunch with `--plugin-dir ./` (then `/reload-plugins` after edits). Otherwise
note it and carry on — a cached plugin serves the released skill, which is what you want
when merely consuming one. Skills under `.agents/skills/` load from the working tree
either way.

A live base directory means the plugin is served from the working tree — not that the
skill text is current. Skills register at session start, so one you edit keeps serving
its pre-edit text until `/reload-plugins`, in your own invocations as much as in test
subagents. Reload after editing a skill you intend to invoke, and confirm the loaded
text carries your edit before following it.

## Testing skills

When RED/GREEN-testing a skill with subagents (see `superpowers:writing-skills`):

- **Reload before re-testing.** Test subagents load the *registered* skill, not your
  working-tree edit — run `/reload-plugins` after each change before the next run.
- **Brief the subagent on the fixture.** Fresh subagents flag intentional test states
  (a pinned/detached checkout, a deliberately odd spec) as errors and try to "fix"
  them; tell them the state is intentional, and have them work in a scratchpad rather
  than writing into the repo.
- **Make sure RED can fail.** Confirm the no-skill control genuinely falls short
  before trusting GREEN, and that the fixture doesn't leak the answer (e.g. a past
  release whose PR body already holds the notes you're asking for).

## Design specs and plans

`docs/superpowers/specs/` and `docs/superpowers/plans/` hold dated design docs and their
implementation plans. Both are scaffolding for one implementation: commit while the work
is in flight so a fresh session can resume mid-branch, then **delete on the same branch
before the PR is created** — the rule `phx:writing-plans` already applies to plans,
extended here to specs. Anything in one still worth keeping earns an ADR, not a reprieve.

## Deferred work

**Deferred work is never a GitHub issue here (ADR 020).** The tracker stays enabled — for
Renovate's dependency dashboard, and so a user who installed the plugin has a channel — so
nothing stops you filing one, and `gh issue` will not fail to tell you otherwise. That is
why this is stated as a prohibition: an issue you file is a note no future session will
read, because nothing sends an agent to the tracker.

Asked to "file an issue for that", write the backlog file instead and say that is what you
did and why. Do it their way only if they say so again, having heard that.

Work you defer goes in `docs/backlog/<slug>.md`, one file per item, saying where it came
from, what the work is, why it is still worth doing, and what would count as done —
`docs/backlog/README.md` fixes the shape. That is the default, a
one-line defect in a single file included. Three cases override it: a condition that would
reopen a settled decision belongs in that ADR's `revisit-when`; a finding about whether
such a condition has fired belongs in a `## Revisit watch` section in that ADR's body,
since `revisit-when` holds the condition rather than the finding about it; and a constraint
a future editor must meet belongs in a comment where they will meet it.

**Read the backlog before starting on an area, not only when deferring from one.** Nothing
routes you there: no hook, no index, no Scope column. `rg <area> docs/backlog/` is the
whole mechanism, which works only because every item names the paths it binds in its prose
— so name them in one you write, or it is unfindable. The pre-commit hook does report the
ADRs binding a staged path, but it fires once the change is written and names only their
titles, so a `## Revisit watch` inside one arrives late and unannounced.

Delete an item on the branch that finishes its work. Nothing checks for stale items.

The reason `gh issue` cannot warn you: `view` and `close` resolve **pull-request** numbers
through the same endpoint, so a `#NNN` handed to either reaches a pull request rather than
erroring. Read what a number is before closing anything.

## Architecture Decision Records

Before proposing architectural or tooling changes, read `docs/adr/INDEX.md` and don't
relitigate settled decisions; open an individual ADR only for its full rationale.
Record significant decisions as a new ADR via the `phx:writing-adrs` skill. Its Format
template does not include `## Revisit watch`, which is repo-local (ADR 020) — keep one
you find rather than reading it as non-conforming, and add one where Deferred work above
says to.

Work out which decisions cover the files you are changing from `INDEX.md`'s Scope column
(ADR 013). **Entries are exact paths or directory prefixes ending in `/`, never globs, and
a prefix binds everything beneath it** — so `scripts/` covers `scripts/ci/versions.py`.
Read them as literal paths and you will miss most of what binds a file, with nothing to
tell you. `Archived` decisions are in force but kept out of `INDEX.md`, so check for them
with `rg -l 'status: Archived' docs/adr/` before recording a new decision.
`python3 skills/writing-adrs/adr.py for <path>` answers which decisions bind a path,
`Archived` ones included; the plugin's hooks inject them the first time a session touches
one.

When code depends on a decision, cite it in a comment: the ADR number and what the
decision forbids at that line, never the reasoning, which stays in the ADR (ADR 014).
Use the `ADR NNN` form in comments and docstrings, and the `docs/adr/NNN` path form in
error messages, where the reader is stopped and needs somewhere to go, and where a clause
of *why* is what makes the message actionable. A citation under `skills/` ships to users
with no `docs/adr/` to open, so name the constraint rather than relying on the number.

Hooks aren't installed on clone: run `git config core.hooksPath .githooks` once per
clone (it carries across worktrees). Without it `INDEX.md` goes stale, and `pr.yml`'s
`adr` job runs the tool's `check` on every pull request, which fails the build on a stale
index or on a `scope` entry naming a path that no longer exists. Set `core.hooksPath` and
re-commit.
