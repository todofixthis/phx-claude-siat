# ADR Reference Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Worktree:** `.worktrees/adr-reference-linking` (branch: `feature/adr-reference-linking`)

**Goal:** Add reference-linking guidance to the `writing-adrs` skill so agent-authored ADRs link GitHub issues/PRs, web pages, and code symbols instead of naming them as bare, unlinked text.

**Architecture:** Three additive edits to `skills/writing-adrs/SKILL.md`: a new `## Linking references` section (convention rules + worked example), a one-line addition to the `## Format` template skeleton showing where the definition block sits, and two verification bullets added to the existing Pass 2 conciseness review. No tooling, lint hook, or frontmatter/numbering changes — enforcement is skill-guidance only, the same way the skill's other conventions are enforced.

**Tech Stack:** Markdown skill documentation only; no code, no dependencies.

**Pre-work already committed on this branch:** `72f9b15` added `.worktrees/` to `.gitignore` (needed so this worktree itself doesn't pollute `git status`). No other documentation changes were required before starting — this plan's own deliverable *is* the documentation change, so it is implemented via the tasks below (with RED/GREEN verification), not committed out-of-band ahead of the plan.

## Global Constraints

- No tooling or lint hook enforces linking — guidance only, checked in the skill's own review passes.
- No changes to ADR frontmatter fields, numbering scheme, or supersession workflow.
- Symbol links point to the relative repo file path only — no line numbers, no commit SHAs.
- Reference definitions are ordered alphabetically by label, ignoring surrounding markup (consistent with the repo-wide convention to alphabetise unordered collections).
- Link only the first mention of a given reference; later mentions stay plain.
- NZ English spelling throughout (repo-wide convention).

---

## File Map

- **Modify:** `skills/writing-adrs/SKILL.md` — add `## Linking references` section after `## Conventions`; add a trailing comment to the `## Format` skeleton; add two verification bullets to `### Pass 2: Conciseness pass` under `## Review`.
- **Reference (read, do not modify):** `docs/superpowers/specs/2026-06-29-adr-reference-linking-design.md` — the source spec this plan implements.
- **Reference (read, do not modify):** `docs/adr/002-generate-changelog-at-release.md` — a real existing ADR in this repo's current (unlinked) style, useful as a "before" reference when judging the RED test output.

---

### Task 1: Add the `## Linking references` section

**Files:**
- Modify: `skills/writing-adrs/SKILL.md` (insert after the `## Conventions` section, which currently ends at the "Keep it concise" bullet, and before `## Review`)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the `## Linking references` section itself — Task 2 and Task 3 read its final state to check consistency, but do not depend on any function/type signature (this is prose, not code).

- [ ] **Step 1: Insert the new section**

Open `skills/writing-adrs/SKILL.md`. Find the end of `## Conventions` (the line reading `- **Keep it concise** — enough to reconstruct the reasoning, not a thesis`, followed by the "Each section has a distinct job" bullet block, which ends just before the `## Review` heading). Insert the following new section immediately before `## Review`:

````markdown
## Linking references

Link every reference to something outside the ADR's own prose — GitHub issues/PRs, web
pages, and code symbols (files, skills, functions, classes). If you name it as a source
of context, link it.

- **Mechanism** — reference-style Markdown links using the named/shortcut form, so the
  label *is* the anchor (`[#100]`, `` [`ClassRegistry`] ``). Collect definitions in one
  block at the very bottom of the file, after Consequences.
- **First mention only** — link the first occurrence of a given reference; later
  mentions stay plain (a code span for symbols, plain text for issues), so a repeated
  code symbol doesn't pepper the document with links.
- **Symbols link to the file, not the line** — use a relative repo path (e.g.
  `skills/writing-adrs/SKILL.md`). No line numbers or commit SHAs — both go stale and
  are not worth keeping in sync.
- **Targets by type** — GitHub issue/PR → the full issue/PR URL; web page → its
  canonical URL; code symbol → the relative repo path to the defining file.
- **Order definitions alphabetically by label**, ignoring surrounding markup (so
  `` [`ClassRegistry`] `` sorts under C) — consistent with the repo-wide convention to
  alphabetise unordered collections.

### Worked example

```markdown
Following [#100][], we adopted the registry pattern from [`ClassRegistry`][].
See the [PEP 8 naming guidance][] for the convention.

[#100]: https://github.com/todofixthis/class-registry/issues/100
[`ClassRegistry`]: src/class_registry/registry.py
[PEP 8 naming guidance]: https://peps.python.org/pep-0008/#naming-conventions
```
````

- [ ] **Step 2: Read the file back and confirm placement**

Run: `rg -n "^## " skills/writing-adrs/SKILL.md`
Expected output order: `## Format`, `## Frontmatter Fields`, `## Conventions`, `## Linking references`, `## Review`, `## Supersession Workflow` — confirming the new section sits between `Conventions` and `Review`.

- [ ] **Step 3: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

---

### Task 2: Update the `## Format` skeleton and the Pass 2 review checklist

**Files:**
- Modify: `skills/writing-adrs/SKILL.md` (the `## Format` fenced template, and the `### Pass 2: Conciseness pass` subsection under `## Review`)

**Interfaces:**
- Consumes: nothing from Task 1's new section beyond its existence (no shared code interface — both are prose additions to the same file).
- Produces: the final SKILL.md content that Task 3 tests via RED/GREEN.

- [ ] **Step 1: Add the trailing comment to the Format skeleton**

In the `## Format` section's fenced template, the `## Consequences` block currently reads:

```markdown
## Consequences

What follows — positive and negative.
```

Change it to:

```markdown
## Consequences

What follows — positive and negative.

<!-- Reference-style link definitions, alphabetised by label, go here -->
```

- [ ] **Step 2: Add verification bullets to Pass 2**

In `## Review` → `### Pass 2: Conciseness pass`, this is a verification wrap-up, not one of the "common cases" — add it at the very end of the subsection, after the existing closing paragraph "Target the shortest version that preserves all reasoning and flow — don't strip the Options comparison so far that the accepted option loses its profile. Stop when no sentence can be cut or moved without losing reasoning." Append a new paragraph and bullet list:

```markdown
Reference-style links have one weak spot: a missing or mismatched definition renders as
literal text rather than erroring. Also verify:

- Every reference label used has a matching definition, and every definition is used —
  no orphans. A conciseness pass can remove a reference's last usage but leave its
  definition behind; watch for that specifically.
- Each target resolves — the issue/PR exists, the path exists, the URL is valid.
```

- [ ] **Step 3: Read the file back and confirm both edits landed**

Run: `rg -n "Reference-style link definitions|Each target resolves" skills/writing-adrs/SKILL.md`
Expected: two matches, one in the `## Format` skeleton, one in `### Pass 2: Conciseness pass`.

- [ ] **Step 4: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

---

### Task 3: RED/GREEN verify the updated guidance

**Files:**
- Test only — no files created or modified beyond what Tasks 1–2 already changed.

**Interfaces:**
- Consumes: the final `skills/writing-adrs/SKILL.md` produced by Tasks 1–2.
- Produces: a pass/fail verification result for this plan's own completion criteria; nothing downstream depends on it.

This task tests the *prompt text*, not a registered/reloaded skill — it sidesteps this repo's dogfooding caveat (a plugin-dir reload only affects the session that owns it, and subagents dispatched from inside this worktree cannot be guaranteed to see a live-reloaded copy). Instead, dispatch subagents that read the SKILL.md file directly by path and follow its instructions — this exercises the actual text these tasks just wrote, without depending on plugin registration.

Both RED and GREEN use the same fixture, drawn directly from the spec's own motivating example (`docs/superpowers/specs/2026-06-29-adr-reference-linking-design.md`):

> Write an ADR (in the format taught by the ADR-writing instructions you're given) documenting a decision to adopt the registry pattern from `ClassRegistry` (a class defined in `src/class_registry/registry.py`) in response to GitHub issue https://github.com/todofixthis/class-registry/issues/100. Mention `ClassRegistry` at least twice in the ADR's prose (once in Context, once in Decision). Do not write the file to disk — return the full ADR markdown as your final response.

- [ ] **Step 1: Run the RED control**

Dispatch a general-purpose subagent with this prompt:

```
Write an ADR documenting a decision to adopt the registry pattern from `ClassRegistry`
(a class defined in `src/class_registry/registry.py`) in response to GitHub issue
https://github.com/todofixthis/class-registry/issues/100. Mention `ClassRegistry` at
least twice in the ADR's prose (once in Context, once in Decision). Use a plausible ADR
structure (Context / Options / Decision / Consequences). Do not write any file to disk —
return the full ADR markdown as your final response.
```

Deliberately do **not** mention the `writing-adrs` skill or SKILL.md in this prompt — this is the control run, representing an agent with no reference-linking guidance.

- [ ] **Step 2: Confirm the RED control fails the way the spec predicts**

Read the returned ADR text. Expected (confirming RED *can* fail, i.e. the gap is real): the GitHub issue is mentioned as bare text or a bare URL, not as a `[#100][]`-style reference link, and there is no definitions block at the foot of the document. If the control subagent happens to produce correctly-linked output unprompted, stop and re-read Tasks 1–2's diff — this would mean the fixture doesn't actually distinguish RED from GREEN, and the fixture (not the guidance) needs revising before continuing.

- [ ] **Step 3: Run the GREEN test**

Dispatch a fresh general-purpose subagent (no shared context with Step 1) with this prompt:

```
Read the file skills/writing-adrs/SKILL.md in this repository and follow its
instructions to write an ADR documenting a decision to adopt the registry pattern from
`ClassRegistry` (a class defined in `src/class_registry/registry.py`) in response to
GitHub issue https://github.com/todofixthis/class-registry/issues/100. Mention
`ClassRegistry` at least twice in the ADR's prose (once in Context, once in Decision).
Do not write any file to disk — return the full ADR markdown as your final response.
```

- [ ] **Step 4: Confirm the GREEN output matches the new convention**

Check the returned ADR against all of:
- The GitHub issue is linked reference-style on first mention (e.g. `[#100][]` or `[issue #100][]`), not a bare URL or plain text.
- `ClassRegistry` is linked (as a code span, e.g. `` [`ClassRegistry`][] ``) only on its first mention; its second mention is a plain code span with no link.
- The symbol's definition target is the relative repo path `src/class_registry/registry.py` — no line number, no commit SHA.
- A definitions block sits at the very bottom of the document, after Consequences.
- Definitions are ordered alphabetically by label, ignoring surrounding markup, matching the spec's own worked example: `[#100]` (sorting under the `#`/number position) comes before `` [`ClassRegistry`] `` (sorting under C).

If any check fails, re-read the relevant part of Tasks 1–2's edits, fix the wording in `skills/writing-adrs/SKILL.md`, and re-run Steps 3–4 (fresh subagent each retry — a subagent that has already seen a failed attempt in its own context is not a clean re-test).

- [ ] **Step 5: Commit**

Run `git status` to catch any related unstaged or untracked files (this step likely has nothing to stage if Steps 1–4 required no further edits; if Step 4 required a fix, stage that fix here), then use the `creative-commits` skill.

---

## Intentional Decisions

*(Populated during review — reviewers must not re-raise these)*

- **Task 2 Step 2 consolidates the spec's three verification points ("matching definition," "no orphans," "target resolves") into two bullets**, folding the first two together since they're the same check stated from both directions. Intentional consolidation, not a dropped requirement.
- **Task 3 tests by reading `SKILL.md` directly by file path, rather than through the Skill tool with `/reload-plugins`.** The spec's Testing section asks for verification "honouring the repo's dogfooding constraint (`--plugin-dir ./`, `/reload-plugins` between runs)." That constraint governs testing *within a single interactive session*; it doesn't have a clean equivalent for subagents dispatched from inside a worktree, which have no guarantee of inheriting a live-reloaded plugin registration. Reading the file by path exercises the same prose the skill would serve, without depending on plugin registration state. Accepted as a substitution for the letter of that instruction, not a gap.

---

## Self-Review Checklist

- [ ] Does the plan header include a `**Worktree:**` field naming the existing worktree and branch?
- [ ] Does every commit step remind the agent to run `git status` first?
- [ ] Does the plan include an Intentional Decisions section?
- [ ] **Spec coverage:** every spec item has a task —
  - "New `## Linking references` section" → Task 1
  - "`## Format` template update" → Task 2, Step 1
  - "Review section additions" (Pass 2 verification bullets) → Task 2, Step 2
  - "Testing" (RED/GREEN, dogfooding-aware) → Task 3
  - "Scope / non-goals" (no tooling, no frontmatter/numbering changes) → Global Constraints; no task implements them because none should
- [ ] **Placeholder scan:** no "TBD"/"handle edge cases"/"similar to Task N" — all three SKILL.md edits are given in full, the fixture prompt is given in full, and the pass/fail criteria in Task 3 are concrete and checkable.
- [ ] **Type consistency:** N/A — no code, no function signatures across tasks; the only cross-task "interface" is the shared file `skills/writing-adrs/SKILL.md`, whose final shape is fully specified by the end of Task 2.
