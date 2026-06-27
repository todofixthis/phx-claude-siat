# phx-claude-siat

> *PHX and Claude sittin' in a tree*
> *tokenmaxxin' for all to see*
> Welcome to my personal Claude Code skills plugin.

A [Claude Code plugin](https://docs.anthropic.com/en/docs/claude-code/plugins) containing reusable skills for coding agents. Skills are general enough to drop into any project; they encode conventions around commit messages, architecture decisions, accessibility, documentation, and more.

## Skills

| Skill | Trigger |
|-------|---------|
| `accessibility-review` | Auditing a React codebase for WCAG AA issues |
| `creative-commits` | Creating Git commits with distinctive emoji-adorned messages |
| `domain-breakdown` | Writing or updating a project's architecture/domain map |
| `nz-english` | Scanning for and correcting US English spellings |
| `reflection` | Reviewing a session for friction and improving ecosystem files |
| `writing-adrs` | Documenting significant architectural or tooling decisions |
| `writing-plans` | Writing implementation plans for multi-step tasks |

### Notes on specific skills

**`writing-plans`** is a wrapper around `superpowers:writing-plans` (from the [superpowers marketplace](https://github.com/obra/superpowers-marketplace)) that adds project-specific conventions on top of the base skill. This improves stability when plan execution is split across multiple sessions, since the wrapper's additional conventions are always applied consistently regardless of which session picks up the work.

**`creative-commits`** produces narrative, emoji-adorned commit messages — a deliberate style choice that trades extra token usage (the skill runs `emoji-seed`, stages files, and reasons about human intent) for the entertainment value of reading AI-generated stories in your git log. It may not suit projects where terse, conventional commit messages are expected. The skill also includes a small Python package (`seed.py`) that generates a random emoji seed; it requires [uv](https://docs.astral.sh/uv/) to be installed. The plugin's `SessionStart` hook writes the plugin root path to `~/.claude/plugins/data/phx.root` so the skill can locate the package regardless of where the plugin is cached.

## Installation

### User-level (recommended)

Install once; skills are available in every project.

```
/plugin marketplace add todofixthis/phx-claude-siat
/plugin install phx@todofixthis
```

Then restart Claude Code.

### Project-level

To activate the plugin for a specific project only, add the following to the project's `.claude/settings.json`:

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

When someone opens the project in Claude Code and trusts the folder, they will be prompted to install the marketplace and plugin automatically.

### Local development

To test working-tree changes, launch Claude Code with the plugin loaded live from
this directory:

```
claude --plugin-dir ./
```

This loads the skills, hooks, and commands directly from the working tree (taking
precedence over any installed copy for the session), so edits take effect after
`/reload-plugins` without reinstalling or clearing the cache. Installing from a
local marketplace instead (`/plugin marketplace add` + `/plugin install`) copies
the plugin into `~/.claude/plugins/cache/`, so working-tree edits would *not* be
picked up — use `--plugin-dir` for active development.

You can tell which copy a session is using from the **base directory** Claude
reports whenever a `phx:` skill loads: a path under this repo means the working
tree is live; a `.../plugins/cache/...` path means the published copy is active.
(Don't use `~/.claude/plugins/data/phx.root` for this — it locates the
`creative-commits` seed script and points at the cached copy even under
`--plugin-dir`.)

> [!NOTE]
> When working with Claude Code inside a container (e.g. using
> [paddock](https://pypi.org/project/phx-paddock/)), make sure the plugin directory is
> mounted in the container at the same path as on the host system.

## Required CLAUDE.md entries

Some skills require explicit instructions in `~/.claude/CLAUDE.md` to ensure Claude invokes them consistently. Add the following sections:

```markdown
# Skill resolution

When asked to write an implementation plan, invoke `phx:writing-plans`, not `superpowers:writing-plans`.

# Git commits

**Always** use the `phx:creative-commits` skill when creating Git commits.
```

## Licence

MIT
