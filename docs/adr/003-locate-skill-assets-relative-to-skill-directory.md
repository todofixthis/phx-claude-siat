---
status: Accepted
date: 2026-07-15
tags: [skills, plugin-root, hooks, versioning, creative-commits, file-paths, uv, single-source-of-truth, subagents]
summary: Locate a skill's bundled files relative to the skill's own directory, not via a hook-written plugin root pointer.
---

# 003: Locate skill assets relative to the skill directory

## Context

[`creative-commits`][] ships a Python package ([`seed.py`][]) that it must execute
via `uv run --project <path>`. The plugin installs into versioned cache
directories (`~/.claude/plugins/cache/todofixthis/phx/<version>/`), so that path
is not knowable when the skill is authored.

`${CLAUDE_PLUGIN_ROOT}` names that path, but is exported only to hooks and MCP
servers — a skill's Bash environment does not carry it. That absence is what
forced an indirection: a `SessionStart` hook wrote the variable to
`~/.claude/plugins/data/phx.root`, which the skill read back at run time.

The pointer is written once per session, but the served version can change within
one: installing or bumping the plugin and running `/reload-plugins` registers a
new version without re-firing `SessionStart`. The pointer then names a version
that is no longer being served. This was observed directly — with the plugin
bumped to 1.1.1 mid-session, `phx.root` still read `.../phx/1.1.0`, so the skill
text came from 1.1.1 while `emoji-seed` ran 1.1.0's code. The failure is silent:
both versions run and exit 0. It has gone unnoticed only because `seed.py` is
byte-identical across every version released to date.

## Options

### Option 1: Do nothing

**Pros:** No work, and no change to a mechanism that has not yet visibly broken.
**Cons:** Skill text and skill code can come from different versions.
**Risks:** The first change to `seed.py` makes the drift observable, as an old
seed script running against new skill instructions — a failure that presents as
inexplicable output rather than a missing file, and points nowhere near the hook
that caused it.

### Option 2: Resolve relative to the skill's own directory (Accepted)

Reference bundled files against the base directory Claude reports when the skill
loads.

**Pros:** The base directory is the served copy by construction, so text and
assets cannot disagree.
**Cons:** Resolution depends on the agent substituting a path it was told, rather
than reading it from a file — a softer guarantee.
**Risks:** `creative-commits` runs in a small-model subagent, which learns the
base directory only by loading the skill itself. Copies of the skill exist at
several guessable paths, so a wrong substitution can still land on a real
directory.

### Option 3: Keep the pointer, refresh it more often

Re-write `phx.root` from additional hook events so it tracks the served version
more closely.

**Pros:** Keeps a file-based mechanism that does not rely on the agent handling a
path.
**Cons:** No hook event corresponds to "the plugin version changed", so any
refresh is an approximation.
**Risks:** The remaining drift is rarer, and correspondingly harder to attribute.

### Option 4: Publish the seed tool and invoke it by name

Publish the package and run `uvx --from creative-commits==<version> emoji-seed`,
removing the path entirely; the version pin lives in `SKILL.md`.

**Pros:** No path to resolve. A version pin binds text to code more tightly than a
base directory does, and any change to that binding is visible in a diff.
**Cons:** Every release must keep the pin in step, and the tool is fetched over
the network at commit time.
**Risks:** A stale pin reintroduces the same text/code mismatch, sourced from a
registry rather than a cache.

## Decision

Resolve skill-bundled files against the skill's own directory.

The pointer duplicated a fact the harness already reports exactly, and every copy
of a fact is a chance for the copies to disagree — which is precisely how this
failed. Refreshing it more aggressively only narrows the window.

Publishing the tool closes the gap at least as firmly — arguably more so, since a
version pin is visible in a diff where a base directory is not. Its rejection is
not about correctness but cost: a second release lifecycle and a public identity
for a forty-line internal script — the maintenance burden [001][] declined while
there is a single plugin. That is a steep price for a fault that has not yet
bitten.

Option 2's cost is real, and we accept it for two reasons: [superpowers][] relies
on this same mechanism wherever its skills bundle runnable assets, and a wrong or
unsubstituted path usually fails immediately and visibly, where the pointer failed
silently and ran the wrong code to a successful exit. That "usually" is a residual
risk, not a closed one.

## Consequences

- `hooks/hooks.json` is deleted. It existed only to write the pointer, and was the
  plugin's only hook, so the plugin now ships no hooks; re-adding one means
  recreating that surface.
- `~/.claude/plugins/data/phx.root` is no longer written or read. Stale copies
  linger on machines that ran earlier versions; nothing reads them.
- `uv run --project` resolves dependencies into the directory it targets, so each
  version bump now pays a fresh dependency resolve on its first `emoji-seed` — the
  stale pointer had perversely reused a warm virtualenv. Under `--plugin-dir ./`
  the virtualenv materialises in the working tree and runs uncommitted `seed.py`:
  intended when dogfooding, but a change from before. Both follow from `--project`
  rather than from this decision, and a move to `uv run --script` with inline
  metadata would retire them; that is a separate decision. (The cache having to be
  writable is not new — the pointer addressed it too.)
- One silent failure survives: a plausible-but-wrong substitution. The working
  tree and each cached version hold a copy of the skill at a guessable path, so an
  agent that substitutes the wrong one still finds a real directory and exits 0.
  A maintainer's machine, holding all of them at once, is where this is most
  exposed.
- Skills bundling runnable assets must state that the path is the skill's own
  directory. A skill that dispatches to a subagent must let the subagent load the
  skill, since loading is what reports the base directory.
- Working-tree liveness is judged solely from the base directory reported at skill
  load — already the documented signal, now the only one.

[001]: 001-co-locate-marketplace-and-plugin.md
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[`seed.py`]: ../../skills/creative-commits/seed.py
[superpowers]: https://github.com/obra/superpowers
