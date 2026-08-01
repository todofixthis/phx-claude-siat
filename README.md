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
| `receiving-code-review` | Responding to review feedback on a pull request |
| `reflection` | Reviewing a session for friction and improving ecosystem files |
| `writing-adrs` | Documenting significant architectural or tooling decisions |
| `writing-plans` | Writing implementation plans for multi-step tasks |
| `writing-release-notes` | Generating release notes or a changelog entry for a new version |

### Notes on specific skills

**`receiving-code-review`** and **`writing-plans`** wrap the same-named skills from the [superpowers marketplace](https://github.com/obra/superpowers-marketplace), adding conventions the base skills leave out. Wrapping keeps those conventions applied no matter which session picks the work up — which matters most when plan execution or a review response spans several sittings. `receiving-code-review` adds the pull-request mechanics: enumerate every inline thread before answering any (review *bodies* are usually empty, and batches accumulate), reply per thread, and sweep the PR body for references to whatever the response deleted or renamed.

**`creative-commits`** produces narrative, emoji-adorned commit messages — a deliberate style choice that trades extra token usage (the skill runs `emoji-seed`, stages files, and reasons about human intent) for the entertainment value of reading AI-generated stories in your git log. It may not suit projects where terse, conventional commit messages are expected. The skill also includes a small Python package (`seed.py`) that generates a random emoji seed; it requires [uv](https://docs.astral.sh/uv/) to be installed. The skill locates the package relative to its own directory, so it always runs the copy that ships with the version being served.

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

This loads the skills and commands directly from the working tree (taking
precedence over any installed copy for the session), so edits take effect after
`/reload-plugins` without reinstalling or clearing the cache. Installing from a
local marketplace instead (`/plugin marketplace add` + `/plugin install`) copies
the plugin into `~/.claude/plugins/cache/`, so working-tree edits would *not* be
picked up — use `--plugin-dir` for active development.

You can tell which copy a session is using from the **base directory** Claude
reports whenever a `phx:` skill loads: a path under this repo means the working
tree is live; a `.../plugins/cache/...` path means the published copy is active.

> [!NOTE]
> When working with Claude Code inside a container (e.g. using
> [paddock](https://pypi.org/project/phx-paddock/)), make sure the plugin directory is
> mounted in the container at the same path as on the host system.

### Git hooks

Hooks live in `.githooks/` (tracked), but git does not install hooks on clone.
Activate them once per clone:

```bash
git config core.hooksPath .githooks
```

The `pre-commit` hook regenerates `docs/adr/INDEX.md` from ADR frontmatter whenever
an ADR is staged. The setting lives in the clone's shared config and the path is
relative, so a single activation also covers every worktree. To regenerate the index
by hand:

```bash
python3 scripts/adr/generate_index.py
```

## Required CLAUDE.md entries

Some skills require explicit instructions in `~/.claude/CLAUDE.md` to ensure Claude invokes them consistently. Add the following sections:

```markdown
# Skill resolution

Where `phx` wraps a `superpowers` skill of the same name, always invoke the `phx:` one: `receiving-code-review`, `writing-plans`.

# Git commits

**Always** use the `phx:creative-commits` skill when creating Git commits.
```

## Licence

MIT
