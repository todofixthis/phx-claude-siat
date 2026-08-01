---
name: writing-adrs
description: Use when making significant architectural, tooling, or design decisions that would benefit from documented rationale — before implementing the decision
---

# Writing Architecture Decision Records

ADRs record _why_ things are the way they are, so future contributors don't relitigate settled decisions. Use one when choosing between libraries, patterns, or conventions, or any time "why didn't we just use X?" is a likely future question.

## Format

File: `docs/adr/NNN-<slug>.md` (zero-padded, kebab-case)

```markdown
---
status: Accepted
date: YYYY-MM-DD
tags: [tag1, tag2, tag3]
summary: One sentence describing what was decided (not why).
---

# NNN: Title (Imperative Mood)

## Context

Why is this a problem? Why now? What forces are at play?

## Options

### Option 1: Do nothing

**Pros:** ...
**Cons:** ...
**Risks:** ...

### Option 2: [Chosen option] (Accepted)

**Pros:** ...
**Cons:** ...
**Risks:** ...

### Option 3: [Rejected alternative]

**Pros:** ...
**Cons:** ...
**Risks:** ...

## Decision

State the decision and summarise the key reasons.

## Consequences

What follows — positive and negative.

<!-- Reference-style link definitions, alphabetised by label, go here -->
```

The `(Accepted)` marker goes on whichever option won, which is Option 1 where the decision
keeps the status quo — see Conventions.

## Frontmatter Fields

Every value sits on one line — no wrapping, no `>` or `|` block scalars. The index parser
reads line by line, so a wrapped `summary` would otherwise yield a truncated index row; both
generators now fail instead, but the constraint is the reason.

- **`status`** — `Accepted`, `Archived`, or `Superseded`. All three stay in the repo; the last two are excluded from `docs/adr/INDEX.md`, which is what an agent loads by default.
  - `Accepted` — in force, and worth carrying in context.
  - `Archived` — in force, but defended by something other than being read, so carrying it in context costs attention it does not need. Archive only when you can **name a defence that the breach path passes through**. Examples, not a closed list: an automated check that blocks the breach; a comment wherever a breach would be authored; a breach so large it needs its own ADR, which the archived-decisions check below then surfaces. Judge a defence by whether someone breaching the decision meets it — not by whether the rejected option is tempting, which decides nothing either way. Three ways one fails: a comment defends only the sites it sits in, so a set of files that grows can never be covered; a note in the files that *keep* a decision does not guard the new file that would break it; and where an ADR rejects several options, a defence covering one of them covers none. **Name the defence in the ADR**; archiving without one is a bet nobody recorded. Set it at any time, including long after writing, once a defence exists.
  - `Superseded` — replaced by a later ADR; set `superseded-by`.

  Status tracks whether a decision is in force and how it is defended, nothing else. A decision that is provisional, or close to its own revisit condition, stays `Accepted` — being nearly reopenable makes it more worth carrying, not less.
- **`date`** — ISO date the ADR was written.
- **`tags`** — lowercase keywords an agent would use to locate this ADR (e.g. `[database, migrations, schema]`). Think: "what would I search for to find this decision?"
- **`summary`** — one sentence: what was decided, not why. This appears verbatim in the index. Phrase it so a reader who sees _only_ the frontmatter won't breach the decision: name the binding choice, including the notable rejected alternative where one exists (e.g. "Use mypy, not ty"). When the decision is explicitly provisional — an option parked pending future conditions — name the revisit trigger too, so a reader of the index alone knows it is reopenable and when — and an `Archived` ADR needs it as much, for whoever finds it through the archived-decisions check.
- **`superseded-by`** — integer ADR number; omit unless status is `Superseded`.

## Conventions

- **Option 1 is always "Do nothing"** — sets the stakes. Describe the status quo and let its Pros/Cons/Risks show what deciding nothing costs; don't explain the option's purpose in the ADR — that's guidance to you, not content.
- **Option 2 is the accepted option** — except where the decision is to keep the status quo, when Option 1 is, and the ADR is `Accepted` like any other. Recording an existing constraint is not a different approach from keeping it, so don't split the two into rival options to satisfy the numbering. Rejected alternatives appear as Options 2, 3, etc. Trivial mitigations (e.g. adding a comment) are implementation details of the "do nothing" choice and do not warrant their own option. Numbering and the `(Accepted)` marker are both fixed when the ADR is written and record which option won; `status` changes later, so never derive one from the other — a superseded ADR keeps the marker on the option that won at the time.
- **Options must be mutually exclusive** — each must represent a fundamentally different approach. Test: could any two options be combined without contradiction? If yes, they aren't mutually exclusive. Two failure modes:
  - _Implementation details as options_ — if two options share the same core approach but differ in implementation, the variant belongs as a sub-heading within the parent option, not a top-level option
  - _Multi-dimensional problems_ — if what looks like a list of options is actually two separate decisions, structure around the primary; handle the secondary as a sub-question in the Decision section or write a follow-up ADR
- **Number sequentially** — never reuse or renumber
- **Check archived decisions before recording a new one** — `rg -l 'status: Archived' docs/adr/` and read any whose subject touches yours. They are out of the index by design, so writing an ADR is the one moment they resurface; a breach big enough to warrant an ADR under this skill is what makes archiving on that defence safe, and a breach that would not warrant one is what makes it unsafe. A new decision that contradicts an archived one supersedes it rather than sitting alongside it.
- **Never edit INDEX.md** — it is regenerated by the `adr-index` pre-commit hook on every commit
- **Supersede, don't edit** — new ADR for changed decisions; mark the old one superseded
- **Keep it concise** — enough to reconstruct the reasoning, not a thesis
- **Check every factual premise against the thing itself** before writing it — the tool's config, the workflow file, the live setting via its API. Documentation is not a source, including this repo's own: a doc asserting the same thing is as likely to be where the error came from. Premises outlive the session that wrote them and are read as settled. Where one can't be checked — a setting behind access you don't have — ask the maintainer rather than writing the gap into the ADR. A premise the decision rests on is worth waiting for an answer to; one that isn't should come out instead.
- **Each section has a distinct job — don't let them overlap:**
  - _Context_ — the problem and forces; stop before proposing any remedy
  - _Options_ — approaches and trade-offs; don't restate what Context already said
  - _Decision_ — why this option over others; don't re-describe the chosen option (Options already did that)
  - _Consequences_ — what changes or must be managed downstream; not a restatement of the accepted option's pros/cons

## Linking references

Link every reference to something outside the ADR's own prose — GitHub issues/PRs, web
pages, and code symbols (files, skills, functions, classes). If you name it as a source
of context, link it.

- **Mechanism** — reference-style Markdown links using the named/shortcut form, so the
  label *is* the anchor (`[#100]`, `` [`ClassRegistry`] ``). Collect definitions in one
  block at the very bottom of the file, after Consequences.
- **First mention only** — link the first occurrence of a given reference; later
  mentions stay plain (a code span for symbols, plain text for issues), so a repeated
  code symbol doesn't pepper the document with links. This tracks the reference itself,
  not its position, so it applies across sections too — a repeat in Decision stays
  plain even if the first mention was back in Context.
- **Symbols link to the file, not the line** — no line numbers or commit SHAs; both go
  stale and are not worth keeping in sync.
- **Paths resolve from the ADR, not the repo root** — the ADR lives in `docs/adr/`, so a
  path from the repo root needs the `../../` prefix (e.g.
  `../../skills/writing-adrs/SKILL.md`), and a peer ADR is bare (`001-some-decision.md`).
  A repo-root-relative path renders as a broken link.
- **Targets by type** — GitHub issue/PR → the full issue/PR URL; web page → its
  canonical URL; code symbol → the path to the defining file; peer ADR → its filename.
- **Order definitions alphabetically by label**, ignoring surrounding markup (so
  `` [`ClassRegistry`] `` sorts under C) — consistent with the repo-wide convention to
  alphabetise unordered collections.

### Worked example

```markdown
Following [#100][], we adopted the registry pattern from [`ClassRegistry`][].
See the [PEP 8 naming guidance][] for the convention.

We decided to implement `ClassRegistry` as proposed in #100, this time scoped
to a single module.

[#100]: https://github.com/todofixthis/class-registry/issues/100
[`ClassRegistry`]: ../../src/class_registry/registry.py
[PEP 8 naming guidance]: https://peps.python.org/pep-0008/#naming-conventions
```

### Common mistake

**Don't** re-link a reference just because it resurfaces in a later section —
the first link already spent it, no matter how far away or how many sections
apart the repeat is:

```markdown
## Context

Following [#100][], we adopted the registry pattern from [`ClassRegistry`][].

## Decision

<!-- Wrong: #100 was already linked above, in Context -->
We chose this approach because [#100][] specifically called out the need for
lazy registration.
```

The corrected form keeps `#100` plain text in Decision, since Context already
linked it:

```markdown
## Decision

We chose this approach because #100 specifically called out the need for
lazy registration.
```

## Review

After drafting an ADR — and before committing it — run two review passes, in order. Both apply to new ADRs and to any ADR you substantially edit.

### Pass 1: Principal-engineer review (subagent)

Dispatch a subagent to review the draft as a senior engineer would. Give it the ADR file path; the codebase and prior ADRs (`docs/adr/`) are available to it. Prompt it to assess:

- **Soundness** — does the accepted option make sense for _this_ project, given its constraints and prior ADRs? Would a principal engineer choose differently?
- **Unsurfaced trade-offs** — are there notable costs, risks, or downsides of the accepted option the ADR does not mention?
- **Implicit assumptions** — what does the decision take for granted that a reader would not know? Each should be stated explicitly.
- **Archival** — if the ADR is `Archived`, does it name a defence, does that defence exist, and would it actually be met at the moment of breach? Push back hard here: the temptation is to archive a decision that merely feels settled, and a wrongly archived one is invisible until someone re-litigates it. If it is `Accepted`, ask the converse — is being read the only thing defending it?
- **Factual accuracy** — is every claim about tooling, workflow, or platform behaviour true of the actual configuration? Have it check config, workflow files, and live settings itself rather than review your notes, and report what each claim was verified against.
- **Frontmatter sufficiency** — would an agent that reads _only_ the frontmatter (`summary`, `tags`, `status`) avoid breaching this decision? If the decision constrains future work, the `summary` and `tags` must make that constraint discoverable. This holds for `Archived` ADRs too, even though nothing reads their frontmatter by default: archiving is reversible, and one restored later — perhaps because it was archived in error — carries whatever frontmatter it was written with. Check as well that it says why it need not be in mind.

Ask for specific, actionable findings — not a rewrite. Incorporate the feedback, then **re-dispatch a fresh subagent** with the revised draft to verify each finding was addressed and no new issue was introduced. Repeat until the review returns no material findings.

### Pass 2: Conciseness pass

Edit the ADR yourself for redundancy and consolidation. The rule: each point lives in exactly one section — the one whose job it is (see Conventions). When the same point appears in two sections, keep it where it belongs and cut the duplicate. Common cases:

- **A Pro/Con/Risk that restates a downstream effect** belongs in Consequences; cut it from Options.
- **A Pro that the Decision already gives as a reason** — the Decision explains why the option won, so the matching Pro is redundant. Cut it, keeping only a distinct detail it adds (if any). The accepted option's Pros are the usual offender, because the Decision elaborates exactly those points.
- **A Context sentence that argues _for_ the chosen approach**, rather than stating the problem and forces, belongs in Decision; move it.

When you cut or relocate a point, remove it cleanly — do not leave a note explaining the edit (e.g. "(see Decision)", "moved from Context", "covered above"). Such pointers re-add the words you just saved and read as edit history the reader does not need.

Target the shortest version that preserves all reasoning and flow — don't strip the Options comparison so far that the accepted option loses its profile. Stop when no sentence can be cut or moved without losing reasoning.

Reference-style links are easy to get subtly wrong: a missing or mismatched definition
renders as literal text rather than erroring, and over-linking is easy to miss. Verify:

- Every reference label used has a matching definition, and every definition is used —
  no orphans. A conciseness pass can remove a reference's last usage but leave its
  definition behind; watch for that specifically.
- Each target resolves — the issue/PR exists, the path exists, the URL is valid.
- Scan the whole draft for any reference whose link syntax (`[label][]`) appears more
  than once — keep the first occurrence linked and convert every later occurrence of
  the same reference to plain text (or a code span, for symbols).

## Supersession Workflow

When a new ADR overrides an existing one:

1. Write the new ADR referencing the old one in the Context section
2. In the **old** ADR, set `status: Superseded` and `superseded-by: NNN` (new ADR number)
3. Commit both files together

Superseded ADRs are excluded from the index automatically.
