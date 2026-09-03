---
status: Accepted
date: 2026-09-02
scope: [.agents/rules/testing.md, skills/writing-adrs/]
summary: A script that acts on the caller's tree resolves its root from the path in hand — an explicit --repo-root, else the nearest ancestor of the touched file or the hook's cwd holding a managed docs/adr/INDEX.md, else the nearest .git — never from the tree it ships in, with the launch directory read only by the hook's cheap gate.
revisit-when: A consumer needs the ADR directory somewhere other than docs/adr/, or silence for a path under no managed root stops being acceptable.
---

# 024: Resolve the repository root from the path in hand

## Context

[ADR 016][] anchors every script under `scripts/` to `__file__`, so a script given no path
acts on the tree it ships in, and names as its revisit trigger "a script must resolve a
path it was given no argument for against whichever checkout the caller is standing in".
The tool [ADR 022][] ships is exactly that script: it lives in a plugin cache and acts on a
consumer's repository, so the tree it ships in is never the one it should touch.

The obvious anchor for a hook is `CLAUDE_PROJECT_DIR`, the directory the session launched
in. A worktree is not that directory wherever it lives — the [`using-git-worktrees`][]
skill puts one under `.worktrees/` inside it, [`EnterWorktree`][worktrees] may put one
anywhere — and
a hook receives the working directory in its input's `cwd` field, which follows the
agent's `cd` (verified against the [hooks reference][hooks] on 2026-09-02). Anchored to
the launch directory, a `git mv` inside a worktree would be checked against the main
checkout.

[`testing.md`][] binds every `test_*.py`, the skill's tests included, and demands two tests
of a module's anchor — one of which asserts the anchor reaches this repository, which a
module that has no anchor of its own cannot pass.

## Options

### Option 1: Do nothing — anchor to the module, as ADR 016 does

**Pros:** One rule for every Python file in the repository.
**Cons:** The tool would act on the plugin cache, which holds no ADRs. The rule cannot
apply, so doing nothing here means having no rule.
**Risks:** A hook that reports "no decisions bind this" because it looked in the wrong tree.

### Option 2: Resolve from the path in hand (Accepted)

`--repo-root` where given; otherwise the nearest ancestor of the file touched, or of the
hook's `cwd`, that holds a `docs/adr/INDEX.md` opening with the tool's header; otherwise
the nearest ancestor holding `.git`, so that `new` run from a subdirectory creates the
corpus at the repository root and not beside the caller; otherwise the working directory.
The innermost managed corpus wins, and the walk stops at the first `.git`, so a submodule
is its own root. A path under no managed root binds nothing, silently.

**Pros:** Right in a worktree, in the launch directory, and from a shell. The managed
header doubles as the gate, so an unmanaged `docs/adr/` is never touched.
**Cons:** A few `stat` calls per event, bounded by depth. Where a `Bash` command names
paths under two managed roots, [ADR 025][]'s injection covers each and [ADR 026][]'s check
runs for every root a file tool wrote an ADR under, and for the `cwd`'s.
**Risks:** The `cwd` fallback is the working-directory dependence [ADR 015][] and 016
rejected, and `--repo-root` is the explicit argument 016 reaffirmed rejecting over
`$(pwd)`; both are accepted here because the tree the tool ships in is never the target.
The fallback is reached only where nothing managed and no `.git` lies above the path.

### Option 3: Anchor to `CLAUDE_PROJECT_DIR`

**Pros:** One variable, always set in a hook, and the shell gate already reads it.
**Cons:** Wrong in every worktree, nested or not.
**Risks:** The failure is silent: a dangling scope in the worktree passes, and the launch
directory's index may be rewritten from the wrong ADRs.

## Decision

Option 2, stated generally: any script that must act on the caller's tree resolves from
the path in hand. The shipped tool has no tree of its own to act on, so ADR 016's anchor
has nothing to anchor; the caller's tree is the only candidate, and the path in hand is the
most precise statement of which caller. `CLAUDE_PROJECT_DIR` stays in the hook's shell gate
as a cheap first test beside `cwd`, and per-path resolution applies once the gate passes.

This discharges ADR 016's trigger: the condition it waited on has arrived and is answered,
by a rule for scripts outside `scripts/`, leaving ADR 016 in force for everything inside
it.

## Consequences

- Every subcommand and every hook event takes the same resolution, implemented once.
- A worktree outside both the launch directory and `cwd` is inert until the agent `cd`s
  into it: the shell gate cannot see the touched path, which arrives on stdin.
- `testing.md` gains the third shape in prose: a module resolving from the caller's path
  owes tests that resolution follows the path given and never the module's location, in
  place of the anchor tests. That also lifts the ships-with-the-module form `nz-english`
  already uses into the rule, closing the backlog item that asked for it.
- The `docs/adr/` location is fixed, since the walk looks for exactly that path.

[ADR 015]: 015-anchor-default-paths-to-the-module.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[hooks]: https://code.claude.com/docs/en/hooks
[`testing.md`]: ../../.agents/rules/testing.md
[`using-git-worktrees`]: https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md
[worktrees]: https://code.claude.com/docs/en/worktrees
