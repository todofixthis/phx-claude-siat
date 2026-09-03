# phx-claude-siat

> *PHX and Claude sittin' in a tree*  
> *tokenmaxxin' for all to see*  
> Welcome to my personal Claude Code skills plugin.

A [Claude Code plugin](https://docs.anthropic.com/en/docs/claude-code/plugins)
containing reusable skills for coding agents. Skills are general enough to drop
into any project; they encode conventions around architecture decisions,
accessibility, documentation, and more.

## Skills

_\* denotes a skill that requires setup or has prerequisites.
See [notes on specific skills](#notes-on-specific-skills) below._

| Skill                    | Trigger                                                         |
|--------------------------|-----------------------------------------------------------------|
| `accessibility-review`   | Auditing a React codebase for WCAG AA issues                    |
| `creative-commits`*      | Creating Git commits with distinctive emoji-adorned messages    |
| `domain-breakdown`       | Writing or updating a project's architecture/domain map         |
| `nz-english`*            | Scanning for and correcting US English spellings                |
| `receiving-code-review`* | Responding to review feedback on a pull request                 |
| `reflection`             | Reviewing a session for friction and improving ecosystem files  |
| `writing-adrs`*          | Documenting significant architectural or tooling decisions      |
| `writing-plans`*         | Writing implementation plans for multi-step tasks               |
| `writing-release-notes`  | Generating release notes or a changelog entry for a new version |

### Notes on specific skills

#### creative-commits

`creative-commits` produces narrative, emoji-adorned commit messages — a
deliberate style choice that trades extra token usage (the skill generates a
seed emoji, stages files, and reasons about human intent) for the entertainment
value of seeing AI-generated short stories play out in your agent sessions.

It may not suit projects where terse, conventional commit messages are expected
— or where your teammates consider emoji in commit logs to be blasphemy. The
skill also includes a small Python package that generates a random emoji seed;
it requires [uv](https://docs.astral.sh/uv/) to be installed.

> [!IMPORTANT]
> Coding agents will not use this skill by default. If you want to use creative
> commits, add the following to `~/.claude/CLAUDE.md` — or to a project's
> `AGENTS.md`, to scope it to that project:
>
> ````markdown
> **Always** use `phx:creative-commits` to create Git commits.
> ````

#### nz-english

`nz-english` ships a tool that performs the sweep, so the skill needs **`python3`
(3.10 or newer) and `git`** on your `PATH`. There is nothing to install beyond
those two — the tool uses only the standard library, and builds no virtualenv.

`git` is needed even for a tree that is not a repository, because the tool runs
it to find that out: an absent `git` stops the sweep before the non-repository
path is reached. Where either program is missing, the skill says so and stops.

#### writing-adrs

`writing-adrs` ships a tool and session hooks, so the skill needs **`python3` (3.10 or
newer)** on your `PATH`. Nothing else to install. (The CI recipe below needs only `uv`,
which fetches an interpreter meeting the tool's 3.12 floor.) The first ADR the agent
records creates `docs/adr/` and a generated `INDEX.md`; from then on the plugin's hooks
regenerate the index after the agent edits an ADR (an edit made through the shell is
reported, not fixed), inject the decisions binding a file the first time a session touches
it, and report a `scope` entry left dangling by a move or delete. The hooks are inert in a
repository whose `docs/adr/INDEX.md` the tool did not generate.

To gate a consumer's CI on the corpus, pinned to a release tag (`<tag>`):

```bash
uvx --from 'git+https://github.com/todofixthis/phx-claude-siat@<tag>#subdirectory=skills/writing-adrs' phx-adr check
```

#### Superpowers wrapper scripts

These scripts wrap the same-named skills from
the  [superpowers marketplace](https://github.com/obra/superpowers-marketplace),
adding conventions the base skills leave out:

- **`receiving-code-review`:** addresses a few edge cases when fetching
  feedback, adds replies to reviewer comments, adds a cleanup step, and mandates
  ADRs for major decisions surfaced during the review itself.
- **`writing-plans`:** creates the worktree+branch and commits coding agent
  documentation up-front, improvements for durability when execution is spread
  across sessions, strengthens the plan quality review loop.

> [!IMPORTANT]
> To ensure your coding agent loads the correct skills, add the following to
> `~/.claude/CLAUDE.md` — or to a project's `AGENTS.md`, to scope it to that
> project:
>
> ````markdown
> Where `phx` wraps a `superpowers` skill of the same name, always invoke the `phx:` one.
> ````

## Installation

### User-level (recommended)

Install once; skills are available in every project.

```
/plugin marketplace add todofixthis/phx-claude-siat
/plugin install phx@todofixthis
```

Then restart Claude Code.

> [!IMPORTANT]
> Some skills need an instruction before an agent will reach for them. Put those
> in `~/.claude/CLAUDE.md` so a once-and-for-all install behaves the same in every
> project. Others need a program on your `PATH`. Review
> [notes on specific skills](#notes-on-specific-skills) above for both.

### Project-level

To activate the plugin for a specific project only, add the following to the
project's `.claude/settings.json`:

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

When someone opens the project in Claude Code and trusts the folder, they will
be prompted to install the marketplace and plugin automatically.

### Local development

To test working-tree changes, launch Claude Code with the plugin loaded live
from this directory:

```
claude --plugin-dir ./
```

This loads the skills and commands directly from the working tree (taking
precedence over any installed copy for the session), so edits take effect after
`/reload-plugins` without reinstalling or clearing the cache.

> [!WARNING]
> Installing from a local marketplace (`/plugin marketplace add` +
> `/plugin install`) doesn't serve this directory at all: the marketplace entry
> pins `main` on GitHub, so it fetches the released branch and copies that into
> `~/.claude/plugins/cache/`.
>
> Moral of the story: use `--plugin-dir ./` for active development.

You can tell which copy a session is using from the **base directory** Claude
reports whenever a `phx:` skill loads: a path under this repo means the working
tree is live; a `.../plugins/cache/...` path means the published copy is active.

> [!NOTE]
> When working with Claude Code inside a container (e.g. using
> [paddock](https://pypi.org/project/phx-paddock/)), make sure the plugin
> directory is mounted in the container at the same path as on the host system.

### Git hooks

Hooks live in `.githooks/` (tracked), but git does not install hooks on clone.
Activate them once per clone:

```bash
git config core.hooksPath .githooks
```

The `pre-commit` hook does two things. It regenerates `docs/adr/INDEX.md` from ADR
frontmatter whenever an ADR is staged, and **refuses the commit if that fails** —
a malformed ADR stops you there. It then reports any decision whose `scope` covers
a staged path, which is advisory and never blocks:

```
Decisions binding these paths:
007 (Accepted): Keep repo scripts stdlib-only — docs/adr/007-keep-repo-scripts-stdlib-only.md
```

That report comes from `adr.py for`, which the session hooks also run, and it is where
`Archived` decisions appear — they are still in force but kept out of `INDEX.md`.
Skipping the hook is not free: `pr.yml` runs the tool's `check` on every pull request,
which fails the build on a stale index or on a `scope` entry naming a path that no longer
exists, and then runs the consumer recipe above against the checkout so it cannot rot. A
missing hook shows up as a red gate rather than a stale file.

The setting lives in the clone's shared config and the path is relative, so a single
activation also covers every worktree. To regenerate the index by hand:

```bash
python3 skills/writing-adrs/adr.py index
```

To ask which decisions bind a file before changing it, from the repo root:

```bash
python3 skills/writing-adrs/adr.py for scripts/ci/versions.py
```

Paths may be repo-relative or absolute; one outside the repository is refused rather
than answered with silence.

Contributions go to `develop` — `main` carries releases only. Run the `scripts/` suite
with `python3 -m unittest discover -s scripts -t . -p 'test_*.py'`, and each skill shipping
a `pyproject.toml` with `uv run pytest`, `uv run ruff check .` and `uv run black --check .`
from its directory, which is what CI gates; `AGENTS.md` has the rest of the
maintainer guidance.

## Licence

MIT
