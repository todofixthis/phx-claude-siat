# phx-claude-siat — maintainer guidance for coding agents

This repo **is** the `phx` Claude Code plugin. Skills live in `skills/`, hooks in
`hooks/`, and the plugin/marketplace manifests in `.claude-plugin/`. Skills are
invoked as `phx:<skill-name>`.

## Dogfooding: confirm the working tree is live before editing skills

By default Claude loads the **published, cached** copy of the plugin, so edits to
`skills/` in the working tree have no effect — and the skills you are editing may
not resolve at all. The working-tree version is only active when Claude was
launched with `--plugin-dir ./`.

Before editing or testing any skill, check which copy is active:

```bash
root="$(cat ~/.claude/plugins/data/phx.root 2>/dev/null)"
repo="$(git rev-parse --show-toplevel 2>/dev/null)"
case "$root" in
  "$repo")            echo "live — working-tree skills active" ;;
  */plugins/cache/*)  echo "cached — relaunch with: claude --plugin-dir ./" ;;
  *)                  echo "unknown/stale phx.root" ;;
esac
```

`phx.root` is written each session by the plugin's `SessionStart` hook to
`${CLAUDE_PLUGIN_ROOT}` — the root of the plugin as actually loaded. A match
against the repo root is a trustworthy positive; treat anything else as not live,
since the file can be stale if the plugin is disabled.

If the working tree is **not** live, advise the user to relaunch with
`claude --plugin-dir ./` (and run `/reload-plugins` after subsequent edits). Do not
silently drive the cached copy — its skills are the last published release, not the
working tree.
