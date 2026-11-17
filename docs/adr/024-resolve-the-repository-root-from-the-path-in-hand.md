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
acts on the tree it ships in. ADR 016's revisit trigger is "a script must resolve a path it
was given no argument for against whichever checkout the caller is standing in". The tool
[ADR 022][] ships is exactly that script. It lives in a plugin cache and acts on a
consumer's repository, so the tree it ships in is never the one it should touch.

The obvious anchor for a hook is `CLAUDE_PROJECT_DIR`, the directory the session launched
in. A worktree is never that directory, wherever the worktree lives. The
[`using-git-worktrees`][] skill puts one under `.worktrees/` inside the launch directory,
and [`EnterWorktree`][worktrees] may put one anywhere. A hook receives the working
directory in the `cwd` field of its input, and that field follows the agent's `cd`
(verified against the [hooks reference][hooks] on 2026-09-02). A hook anchored to the
launch directory would check a `git mv` inside a worktree against the main checkout.

[`testing.md`][] binds every `test_*.py`, the skill's tests included. It demands two tests
of a module's anchor, and one of them asserts that the anchor reaches this repository. A
module with no anchor of its own cannot pass that test.

## Options

### Option 1: Do nothing — anchor to the module, as ADR 016 does

**Pros:** One rule covers every Python file in the repository.
**Cons:** The tool would act on the plugin cache, which holds no ADRs. The rule cannot
apply, so doing nothing here means having no rule.
**Risks:** A hook reports "no decisions bind this" because it looked in the wrong tree.

### Option 2: Resolve from the path in hand (Accepted)

The tool picks the root in this order:

1. `--repo-root`, where given.
2. The nearest ancestor of the touched file, or of the hook's `cwd`, that holds a
   `docs/adr/INDEX.md` opening with the tool's header.
3. The nearest ancestor that holds `.git`. With this step, `new` run from a subdirectory
   creates the corpus at the repository root, not beside the caller.
4. The working directory.

The innermost managed corpus wins. The walk stops at the first `.git`, so a submodule is
its own root. A path under no managed root binds nothing, and the tool says nothing.

**Pros:** The resolution is right in a worktree, in the launch directory, and from a
shell. The managed header also works as the gate, so the tool never touches an unmanaged
`docs/adr/`. **Cons:** Each event costs a few `stat` calls, bounded by depth. Where a
`Bash` command names paths under two managed roots, [ADR 025][]'s injection covers each
root. [ADR 026][]'s check runs for every root that a file tool wrote an ADR under, and for
the root of `cwd`. **Risks:** The `cwd` fallback is the working-directory dependence that
[ADR 015][] and 016 rejected. `--repo-root` is the explicit argument that 016 reaffirmed
rejecting, because its obvious value is `$(pwd)`. This ADR accepts both because the tree
the tool ships in is never the target. The tool reaches the fallback only where no managed
corpus and no `.git` lie above the path.

### Option 3: Anchor to `CLAUDE_PROJECT_DIR`

**Pros:** It is one variable, always set in a hook, and the shell gate already reads it.
**Cons:** It is wrong in every worktree, nested or not.
**Risks:** The failure is silent. A dangling scope in the worktree passes, and the tool
may rewrite the launch directory's index from the wrong ADRs.

## Decision

Option 2, stated generally: any script that must act on the caller's tree resolves its
root from the path in hand. The shipped tool has no tree of its own to act on, so ADR 016's
anchor has nothing to anchor. The caller's tree is the only candidate, and the path in hand
says most precisely which caller. `CLAUDE_PROJECT_DIR` stays in the hook's shell gate as a
cheap first test beside `cwd`. Per-path resolution applies once the gate passes.

This ADR answers the condition ADR 016's trigger waited on, with a rule for scripts outside
`scripts/`. It also reverses 016's claim that every script anchors to `__file__`. [ADR 027][]
therefore restates 016 by the tree a script acts on and supersedes it. This ADR is the
caller's-tree half of that rule.

## Consequences

- Every subcommand and every hook event resolves the root the same way, and the code that
  does it exists once.
- A worktree outside both the launch directory and `cwd` stays inert until the agent runs
  `cd` into it. The shell gate cannot see the touched path, because that path arrives on
  stdin.
- `testing.md` gains the third shape in prose. A module that resolves from the caller's
  path owes tests that resolution follows the path given and never the module's location.
  These replace the anchor tests. The change also lifts into the rule the
  ships-with-the-module form that `nz-english` already uses, and closes the backlog item
  that asked for it.
- The `docs/adr/` location is fixed, because the walk looks for exactly that path.

[ADR 015]: 015-anchor-default-paths-to-the-module.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[ADR 027]: 027-anchor-a-script-to-the-tree-it-acts-on.md
[hooks]: https://code.claude.com/docs/en/hooks
[`testing.md`]: ../../.agents/rules/testing.md
[`using-git-worktrees`]: https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md
[worktrees]: https://code.claude.com/docs/en/worktrees
