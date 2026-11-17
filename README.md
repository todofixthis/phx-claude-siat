# phx-claude-siat

> *PHX and Claude sittin' in a tree*  
> *tokenmaxxin' for all to see*  
> Welcome to my personal Claude Code skills plugin.

A [Claude Code plugin](https://docs.anthropic.com/en/docs/claude-code/plugins) of
reusable skills for coding agents. The skills are general enough to drop into any
project. They encode conventions for areas such as architecture decisions,
accessibility, and documentation.

## Skills

_An asterisk (\*) marks a skill that needs setup or has prerequisites.
See [notes on specific skills](#notes-on-specific-skills) below._

| Skill                    | Trigger                                                         |
|--------------------------|-----------------------------------------------------------------|
| `accessibility-review`   | Auditing a React codebase for WCAG AA issues                    |
| `creative-commits`*      | Creating Git commits with distinctive emoji-adorned messages    |
| `domain-breakdown`       | Writing or updating a project's architecture or domain map      |
| `nz-english`*            | Scanning for and correcting US English spellings                |
| `receiving-code-review`* | Responding to review feedback on a pull request                 |
| `reflection`             | Reviewing a session for friction and improving ecosystem files  |
| `technical-writing`      | Writing or reviewing prose a person reads                       |
| `writing-adrs`*          | Documenting significant architectural or tooling decisions      |
| `writing-plans`*         | Writing implementation plans for multi-step tasks               |
| `writing-release-notes`  | Generating release notes or a changelog entry for a new version |

### Notes on specific skills

#### creative-commits

`creative-commits` writes narrative commit messages adorned with emoji. The style is
deliberate, and it costs extra tokens: the skill generates a seed emoji, stages files,
and reasons about human intent. In return, you get the entertainment of AI-generated
short stories playing out in your agent sessions.

It may not suit projects that expect terse, conventional commit messages, or teammates
who consider emoji in commit logs to be blasphemy. The skill also includes a small
Python package that generates a random emoji seed, which needs
[uv](https://docs.astral.sh/uv/) installed.

> [!IMPORTANT]
> Coding agents don't use this skill by default. To use creative commits, add the
> following to `~/.claude/CLAUDE.md`, or to a project's `AGENTS.md` to scope it to that
> project:
>
> ````markdown
> **Always** use `phx:creative-commits` to create Git commits.
> ````

#### nz-english

`nz-english` ships a tool that runs the sweep, so the skill needs **`python3`
(3.10 or newer) and `git`** on your `PATH`. You install nothing beyond those two. The
tool uses only the standard library and builds no virtualenv.

The tool needs `git` even for a tree that is not a repository, because it runs `git` to
find that out. Without `git`, the sweep stops before it reaches the non-repository path.
If either program is missing, the skill says so and stops.

> [!IMPORTANT]
> To run the sweep from a pre-commit hook instead of by hand, ask your agent to add the
> following to your project's `.githooks/pre-commit`. Have `phx:nz-english` loaded when you
> ask, so that `${CLAUDE_SKILL_DIR}` resolves to a real path. Redo this after you update
> the plugin, because that path can change:
>
> ````sh
> set --
> while IFS= read -r path; do
>     [ -n "$path" ] || continue
>     set -- "$@" "$path"
> done <<STAGED
> $(git diff --cached --name-only)
> STAGED
> python3 ${CLAUDE_SKILL_DIR}/scan.py --hook "$@"
> ````
>
> The `while read` loop matters. An unquoted `$(...)` word-splits, so it breaks on a path
> that contains whitespace. `--hook` treats an empty staged selection, and a staged
> deletion, as a skip (exit 4) rather than a failure. Read the exit code:
>
> - **0** and **1** mean what they always do: clean, or hits to triage.
> - **4** means nothing staged needed checking, because every staged path was excluded
>   (`*.lock`, `CHANGELOG.md`) or deleted. Let the commit through.
> - **2** and **3** keep their meanings: escalate a 2, fix a 3.

#### technical-writing

This skill merges `technical-writing` and `unslop` from the `pstack` plugin by
[poteto](https://x.com/poteto), in
[`cursor/plugins`](https://github.com/cursor/plugins/tree/bf0c7cd80abdbf7fe47b634978a7d1b4071f71a7/pstack/skills)
at `bf0c7cd`, vendored under the MIT licence that the skill directory carries. We
maintain it here as our own, and it does not track upstream. It covers prose a person
reads. Text that only a model reads favours fewer tokens over the readability these
rules buy.

#### writing-adrs

`writing-adrs` ships a tool and session hooks, so the skill needs **`uv`** on your `PATH`.
You install nothing else, because uv fetches an interpreter that meets the tool's 3.12
floor.

At session start, the plugin syncs the tool's virtual environment (with PyYAML) for the
plugin version, under the plugin's data directory. It also drops the environments of
versions that are no longer installed. Syncing an environment that is already current does
nothing. The first session after an update therefore needs network access. If the sync
fails, the session says so, and the checks are off for that session. If uv is
missing, an environment that an earlier session synced still runs every hook. With no such
environment, the session says the checks are off until uv is installed.

The first ADR the agent records creates `docs/adr/` and a generated `INDEX.md`. From then
on, the plugin's hooks do three things:

- Regenerate the index after the agent edits an ADR. An edit made through the shell is
  reported, not fixed.
- Inject the decisions binding a file the first time a session touches it.
- Report a `scope` entry that a move or delete left dangling.

The hooks do nothing in a repository whose `docs/adr/INDEX.md` the tool did not generate.
[How the writing-adrs hooks shape a session](docs/writing-adrs-hooks.md) walks through each
hook and shows what the agent sees at every step.

To gate a consumer's CI on its ADR corpus, run the tool pinned to a release tag (`<tag>`):

```bash
uvx --from 'git+https://github.com/todofixthis/phx-claude-siat@<tag>#subdirectory=skills/writing-adrs' phx-adr check
```

#### Superpowers wrapper skills

These skills wrap the same-named skills from the
[superpowers marketplace](https://github.com/obra/superpowers-marketplace) and add
conventions the base skills leave out:

- **`receiving-code-review`** handles a few edge cases when fetching feedback, replies to
  reviewer comments, adds a cleanup step, and requires an ADR for any major decision that
  comes up during the review itself.
- **`writing-plans`** creates the worktree and branch, and commits coding-agent
  documentation up front. It also makes plans more durable when execution spans several
  sessions, and strengthens the plan quality review loop.

> [!IMPORTANT]
> To make sure your coding agent loads the right skills, add the following to
> `~/.claude/CLAUDE.md`, or to a project's `AGENTS.md` to scope it to that project:
>
> ````markdown
> Where `phx` wraps a `superpowers` skill of the same name, always invoke the `phx:` one.
> ````

## Installation

### User-level (recommended)

Install once, and the skills are available in every project.

```
/plugin marketplace add todofixthis/phx-claude-siat
/plugin install phx@todofixthis
```

Then restart Claude Code.

> [!IMPORTANT]
> Some skills need an instruction before an agent reaches for them. Put those
> instructions in `~/.claude/CLAUDE.md`, so a user-level install behaves the same in every
> project. Other skills need a program on your `PATH`. The
> [notes on specific skills](#notes-on-specific-skills) above cover both.

### Project-level

To activate the plugin for one project only, add the following to the project's
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "todofixthis": {
      "source": {
        "source": "github",
        "repo": "todofixthis/phx-claude-siat"
      }
    }
  },
  "enabledPlugins": {
    "phx@todofixthis": true
  }
}
```

When someone opens the project in Claude Code and trusts the folder, they are prompted
to install the marketplace and the plugin automatically.

### Local development

To test working-tree changes, launch Claude Code with the plugin loaded live
from this directory:

```
claude --plugin-dir ./
```

This loads the skills and commands straight from the working tree, ahead of any installed
copy, for that session. Edits take effect after `/reload-plugins`, with no reinstall and no
cache clearing.

Under `--plugin-dir`, the `writing-adrs` hooks use the checkout's own virtual environment,
`${UV_PROJECT_ENVIRONMENT:-.venv}`. The sync removes nothing else in it. Leave
`UV_PROJECT_ENVIRONMENT` unset, or set it to a path inside the checkout that has no `..`
component and is not the checkout itself. The sync refuses any other path, and the hooks
stay off.

> [!WARNING]
> Installing from a local marketplace (`/plugin marketplace add`, then
> `/plugin install`) doesn't serve this directory at all. The marketplace entry pins
> `main` on GitHub, so it fetches the released branch and copies that into
> `~/.claude/plugins/cache/`.
>
> Use `--plugin-dir ./` for active development.

You can tell which copy a session uses from the **base directory** Claude reports whenever
a `phx:` skill loads. A path under this repo means the working tree is live. A
`.../plugins/cache/...` path means the published copy is active. The reported path is only
a liveness check. A skill reaches its own bundled tools through `${CLAUDE_SKILL_DIR}`, not
by reading the base directory.

> [!NOTE]
> When you run Claude Code inside a container, for example with
> [paddock](https://pypi.org/project/phx-paddock/), mount the plugin directory in the
> container at the same path as on the host.

### Git hooks

Hooks live in `.githooks/`, which is tracked, but git does not install hooks on clone.
Activate them once per clone:

```bash
git config core.hooksPath .githooks
```

The `pre-commit` hook does two things. Whenever an ADR is staged, it regenerates
`docs/adr/INDEX.md` from ADR frontmatter and **refuses the commit if that fails**, so a
malformed ADR stops you there. It then reports any decision whose `scope` covers a staged
path. That report is advisory and never blocks:

```
Decisions binding these paths:
007 (Accepted): Keep repo scripts stdlib-only — docs/adr/007-keep-repo-scripts-stdlib-only.md
```

The report comes from `adr.py for`, the same lookup the session hooks make. It is also
where `Archived` decisions appear, because they are still in force but kept out of
`INDEX.md`.

Skipping the hook moves the failure to CI. On every pull request, `pr.yml` runs the tool's
`check`, which fails the build on a stale index or on a `scope` entry that names a path
that no longer exists. It then runs the consumer recipe above against the checkout, so the
recipe can't break unnoticed. A missing hook shows up as a failing check rather than a
stale file.

The setting lives in the clone's shared config and the path is relative, so one activation
covers every worktree too. To regenerate the index by hand:

```bash
uv run python skills/writing-adrs/adr.py index
```

To check which decisions bind a file before you change it, run this from the repo root:

```bash
uv run python skills/writing-adrs/adr.py for scripts/ci/versions.py
```

Paths can be repo-relative or absolute. A path outside the repository binds nothing and
prints nothing.

### Contributing

Contributions go to `develop`. `main` carries releases only. Run the `scripts/` suite
with `uv run python -m unittest discover -s scripts -t . -p 'test_*.py'`.

The repository root is a uv workspace (`pyproject.toml` plus one shared `uv.lock`) that
spans `scripts/` and every skill that ships its own `pyproject.toml`. After
`uv sync --locked` at the repo root, CI gates each skill on three checks:
`uv run --directory skills/<name> pytest`, `ruff check .`, and `black --check .`.
`AGENTS.md` has the rest of the maintainer guidance.

## Licence

MIT
