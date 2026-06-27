# phx-claude-siat — maintainer guidance for coding agents

This repo **is** the `phx` Claude Code plugin. Skills live in `skills/`, hooks in
`hooks/`, and the plugin/marketplace manifests in `.claude-plugin/`. Skills are
invoked as `phx:<skill-name>`.

## Dogfooding: notice when the working tree isn't live

By default Claude loads the **published, cached** copy of the plugin; the
working-tree version is active only when Claude was launched with `--plugin-dir ./`.
When it isn't, edits and tests in this repo don't take effect.

Don't probe for this proactively. Instead, the first time you reach for a `phx:`
skill in the normal course of work, let the load itself tell you. The working tree
is **not** live if either:

- the skill is unavailable (`Unknown skill`), or
- it loads from a `…/plugins/cache/…` base directory rather than this repo.

In that case, stop and confirm with the user whether that's intended before
continuing — they may want to relaunch with `claude --plugin-dir ./` (then
`/reload-plugins` after later edits) so the work actually exercises the working
tree.

(Ignore `~/.claude/plugins/data/phx.root` as a signal — it locates the
`creative-commits` seed script and points at the cached copy even under
`--plugin-dir`.)
