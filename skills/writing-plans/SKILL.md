---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

**REQUIRED SUB-SKILL:** Use `superpowers:writing-plans` to build the plan, then apply the additional conventions below before finalising.

## Additional Convention: Worktree Name in Plan Header

After the worktree is created (by the brainstorming skill), add a `**Worktree:**` field to the plan header so executing agents know where to work:

```markdown
**Worktree:** `path/to/worktree` (branch: `feature/branch-name`)
```

If the plan is written before the worktree exists, add a first step to the first task:

```markdown
- [ ] **Step 1: Record worktree path**

Run: `git worktree list`
Update the `**Worktree:**` field in this plan's header with the path and branch name, then save.
```

Add this to every task in the self-review checklist too: "Does the plan header include a `**Worktree:**` field?"

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
