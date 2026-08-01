# phx-claude-siat

> *PHX and Claude sittin' in a tree*  
> *tokenmaxxin' for all to see*  
> Welcome to my personal Claude Code skills plugin.

A [Claude Code plugin](https://docs.anthropic.com/en/docs/claude-code/plugins)
containing reusable skills for coding agents. Skills are general enough to drop
into any project; they encode conventions around architecture decisions,
accessibility, documentation, and more.

## Skills

_\* denotes a skill that requires setup.
See [notes on specific skills](#notes-on-specific-skills) below._

| Skill                    | Trigger                                                         |
|--------------------------|-----------------------------------------------------------------|
| `accessibility-review`   | Auditing a React codebase for WCAG AA issues                    |
| `creative-commits`*      | Creating Git commits with distinctive emoji-adorned messages    |
| `domain-breakdown`       | Writing or updating a project's architecture/domain map         |
| `nz-english`             | Scanning for and correcting US English spellings                |
| `receiving-code-review`* | Responding to review feedback on a pull request                 |
| `reflection`             | Reviewing a session for friction and improving ecosystem files  |
| `writing-adrs`           | Documenting significant architectural or tooling decisions      |
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
> project. Review [notes on specific skills](#notes-on-specific-skills) above.

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
directory is
> mounted in the container at the same path as on the host system.

### Git hooks

Hooks live in `.githooks/` (tracked), but git does not install hooks on clone.
Activate them once per clone:

```bash
git config core.hooksPath .githooks
```

The `pre-commit` hook regenerates `docs/adr/INDEX.md` from ADR frontmatter
whenever an ADR is staged. The setting lives in the clone's shared config and
the path is relative, so a single activation also covers every worktree. To
regenerate the index by hand:

```bash
python3 -m scripts.adr.generate_index
```

## Licence

MIT
