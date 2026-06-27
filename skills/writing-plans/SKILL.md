---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

**REQUIRED SUB-SKILL:** Use `superpowers:writing-plans` to build the plan, then apply the additional conventions below before finalising.

## Before Writing the Plan File

The main agent performs these two steps **first**, before writing any of the plan, and in this order. They put the branch and any agent-facing guidance in place so that subagents executing the plan inherit a correct workspace from their very first task.

### Step 1: Create the worktree and branch now

Create the isolated workspace **before** writing the plan — do not defer it. **REQUIRED SUB-SKILL:** Use `superpowers:using-git-worktrees` to create (or detect) an isolated worktree on a new feature branch.

This overrides the base skill's note that the worktree is created at execution time: the main agent creates it now, so by the time the plan is written the worktree already exists. The branch is needed immediately for the documentation commit in Step 2. (If the user has declined a worktree, still create a feature branch so that commit — and later implementation — never lands on `main`.)

### Step 2: Commit coding-agent documentation first

If the planned work would change documentation that coding agents read as guidance — `AGENTS.md`, `CLAUDE.md`, ADRs, skills, or similar — make those changes and commit them on the branch **now**, before writing the plan. Use the `creative-commits` skill for the commit.

Subagents that execute the plan read this guidance at the start of their work. Committing it first means it is already in place for every task; fold it into the plan instead and the earlier tasks run without it.

Do **not** add these documentation changes as tasks in the plan — they are already done. Record them in the plan's Architecture section as completed pre-work, so the self-review's spec-coverage check accounts for them.

## Additional Convention: Worktree Name in Plan Header

The worktree exists by now (from Step 1 above), so populate a `**Worktree:**` field in the plan header directly so executing agents know where to work:

```markdown
**Worktree:** `path/to/worktree` (branch: `feature/branch-name`)
```

Add this to every task in the self-review checklist too: "Does the plan header include a `**Worktree:**` field naming the existing worktree and branch?"

## Additional Convention: Commit Step

Every implementation commit step must remind the agent to check for stragglers before committing:

```markdown
- [ ] **Step N: Commit**

Run `git status` to catch any related unstaged or untracked files (e.g. lock files after dependency changes), then use the `creative-commits` skill.
```

Add this to every task in the self-review checklist too: "Does every commit step remind the agent to run `git status` first?"

## Additional Convention: Intentional Decisions Section

Add this section to every plan, immediately before the self-review checklist:

```markdown
## Intentional Decisions

*(Populated during review — reviewers must not re-raise these)*
```

During the review loop (below), append entries here for any reviewer-raised issues that are accepted as intentional rather than fixed. This prevents subsequent reviewers relitigating settled choices.

Add to the self-review checklist: "Does the plan include an Intentional Decisions section?"

## Additional Convention: Review Loop

After saving the plan, run a review loop (max 3 iterations) before offering execution options:

**Each iteration:**

1. Dispatch a review subagent. The brief must include:
   - The plan file path (the reviewer reads the plan directly — this covers the Intentional Decisions section and any prior fixes)
   - A concise spec summary (valid/invalid configurations — this is external to the plan and needed for coverage checks)
   - Instruction to read the files named in the plan's File Map for codebase context
   - Output format: categorise as **blocker** / **minor** / **suggestion** with quoted plan text and specific fix

2. Fix all **blocker**-severity findings in the plan.

3. Append to the plan's Intentional Decisions section any findings accepted as intentional rather than fixed.

4. If any blockers were fixed, run another iteration (up to the 3-iteration cap).

**Stop** when the reviewer finds no blockers, or after 3 iterations — whichever comes first. Only then offer the execution handoff.
