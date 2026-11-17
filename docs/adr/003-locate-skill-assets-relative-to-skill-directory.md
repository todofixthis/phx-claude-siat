---
status: Accepted
date: 2026-07-15
scope: [skills/]
summary: Locate a skill's bundled files relative to the skill's own directory, not via a hook-written plugin root pointer.
---

# 003: Locate skill assets relative to the skill directory

## Context

[`creative-commits`][] ships a Python package ([`seed.py`][]) that it runs with
`uv run --project <path>`. The plugin installs into a versioned cache directory
(`~/.claude/plugins/cache/todofixthis/phx/<version>/`), so the skill's author can't know
that path.

`${CLAUDE_PLUGIN_ROOT}` holds the path, but Claude Code exports it only to hooks and MCP
servers. A skill's Bash environment doesn't have it. That gap forced an indirection. A
`SessionStart` hook wrote the variable to `~/.claude/plugins/data/phx.root`, and the
skill read it back at run time.

The hook writes the pointer once per session, but the served version can change within a
session. Installing or bumping the plugin and running `/reload-plugins` registers a new
version without firing `SessionStart` again. The pointer then names a version that is no
longer served. We saw this happen. With the plugin bumped to 1.1.1 mid-session,
`phx.root` still read `.../phx/1.1.0`, so the skill text came from 1.1.1 while
`emoji-seed` ran 1.1.0's code. Nothing reports the failure: both versions run and exit 0.
Nobody has noticed only because `seed.py` is byte-identical in every version released so
far.

## Options

### Option 1: Do nothing

**Pros:** No work, and no change to a mechanism that hasn't yet visibly broken.
**Cons:** Skill text and skill code can come from different versions.
**Risks:** The first change to `seed.py` makes the drift visible: an old seed script runs
against new skill instructions. The symptom is output nobody can explain, not a missing
file, and nothing in it points to the hook that caused it.

### Option 2: Resolve relative to the skill's own directory (Accepted)

Reference bundled files against the base directory Claude reports when the skill loads.

**Pros:** The base directory is always the served copy, so text and assets can't
disagree.
**Cons:** Resolution depends on the agent substituting a path it was told, not reading
one from a file. That is a weaker guarantee.
**Risks:** `creative-commits` runs in a small-model subagent, which learns the base
directory only by loading the skill itself. Copies of the skill sit at several guessable
paths, so a wrong substitution can still land on a real directory.

### Option 3: Keep the pointer, refresh it more often

Write `phx.root` again from more hook events, so that it tracks the served version more
closely.

**Pros:** Keeps a file-based mechanism that doesn't depend on the agent handling a path.
**Cons:** No hook event means "the plugin version changed", so any refresh only
approximates it.
**Risks:** The drift that remains is rarer, and so harder to trace to its cause.

### Option 4: Publish the seed tool and invoke it by name

Publish the package and run `uvx --from creative-commits==<version> emoji-seed`, which
removes the path. The version pin lives in `SKILL.md`.

**Pros:** There is no path to resolve. A version pin ties text to code more tightly than a
base directory does, and any change to the pin shows in a diff.
**Cons:** Every release must keep the pin in step, and the tool downloads over the network
at commit time.
**Risks:** A stale pin brings back the same mismatch between text and code, this time
from a registry, not a cache.

## Decision

Resolve skill-bundled files against the skill's own directory.

The pointer duplicated a fact that the harness already reports exactly. Every copy of a
fact is a chance for the copies to disagree, and that is how this failed. Refreshing the
pointer more often only shrinks the window.

Publishing the tool closes the gap at least as firmly, and arguably more so, because a
diff shows a version pin but not a base directory. We rejected it on cost, not
correctness. It needs a second release lifecycle and a public identity for a forty-line
internal script. That is the maintenance burden [001][] declined while there is one
plugin, and it is a high price for a fault that hasn't yet caused harm.

Option 2's cost is real, and we accept it for two reasons. First, [superpowers][] uses
the same mechanism wherever its skills bundle runnable assets. Second, a wrong or
unsubstituted path usually fails at once and visibly, whereas the pointer failed silently
and ran the wrong code to a successful exit. "Usually" leaves a residual risk open.

## Consequences

- `hooks/hooks.json` is deleted. It existed only to write the pointer and was the
  plugin's only hook, so the plugin now ships no hooks. Adding one back means recreating
  the hooks file and its wiring.
- Nothing writes or reads `~/.claude/plugins/data/phx.root` any more. Stale copies remain
  on machines that ran earlier versions, and nothing reads them.
- `uv run --project` resolves dependencies into the directory it targets, so the first
  `emoji-seed` after each version bump now resolves dependencies from scratch. The stale
  pointer had, by accident, reused a warm virtualenv. Under `--plugin-dir ./`, the
  virtualenv appears in the working tree and runs the uncommitted `seed.py`. That is what
  we want when dogfooding, but it is a change. Both effects come from `--project`, not
  from this decision. A move to `uv run --script` with inline metadata would remove them,
  and that is a separate decision. (The cache already had to be writable. The pointer
  addressed that too.)
- One silent failure remains: a substitution that is plausible but wrong. The working
  tree and each cached version hold a copy of the skill at a guessable path, so an agent
  that substitutes the wrong one still finds a real directory and exits 0. A maintainer's
  machine holds all the copies at once, so it is the most exposed.
- A skill that bundles runnable assets must state that the path is the skill's own
  directory. A skill that dispatches to a subagent must let the subagent load the skill,
  because loading is what reports the base directory.
- The base directory reported at skill load is now the only signal for whether the
  working tree is live. It was already the documented one.

[001]: 001-co-locate-marketplace-and-plugin.md
[`creative-commits`]: ../../skills/creative-commits/SKILL.md
[`seed.py`]: ../../skills/creative-commits/seed.py
[superpowers]: https://github.com/obra/superpowers
