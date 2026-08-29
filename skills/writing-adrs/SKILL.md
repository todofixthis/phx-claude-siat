---
name: writing-adrs
description: Use when making significant architectural, tooling, or design decisions that would benefit from documented rationale — before implementing the decision
---

# Writing Architecture Decision Records

ADRs record _why_ things are the way they are, so future contributors don't relitigate settled decisions. Use one when choosing between libraries, patterns, or conventions, or any time "why didn't we just use X?" is a likely future question.

**What this assumes.** ADRs live in `docs/adr/`, and a generator maintains an `INDEX.md` beside them from their frontmatter, enforcing the field rules below. Where a repo has no such generator, every rule here still holds as a convention — write the frontmatter the same way — but nothing checks it, so anything below that says a breach "fails" or "is reported" means "goes unnoticed" instead. Check for the generator before relying on it, and don't tell a reader a check exists that doesn't.

Building or updating a generator against this contract: [`todofixthis/phx-claude-siat`](https://github.com/todofixthis/phx-claude-siat)'s own [`generate_index.py`](../../scripts/adr/generate_index.py) — together with its line parser, [`frontmatter.py`](../../scripts/frontmatter.py) — is the reference implementation of the Frontmatter Fields rules below (status pairing, revisit pairing, `scope` validation), and [its test suite](../../scripts/adr/test_generate_index.py) exercises each one. Port these rather than reverse-engineering the rules from prose, but expect to strip what's specific to that repository: the stdlib-only parsing, the `python3 -m scripts.adr.generate_index` invocation and `.githooks/pre-commit` wiring, and the ADR citations in its comments are how it satisfies the contract, not part of the contract itself.

## Format

File: `docs/adr/NNN-<slug>.md` (zero-padded, kebab-case)

```markdown
---
status: Accepted
date: YYYY-MM-DD
scope: [path/to/directory/, path/to/file.py]
summary: One sentence describing what was decided (not why).
# plus revisit-when where a condition would reopen this, and archived-because or
# superseded-by where the status calls for one
---

# NNN: Title (Imperative Mood)

## Context

Why is this a problem? Why now? What forces are at play?

## Options

<!-- Optional: one paragraph naming any cost two or more options share, and setting it
     aside. Omit where they share none. -->

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

The `(Accepted)` marker goes on whichever option won — Option 1 where the decision keeps the
status quo (see Conventions).

## Frontmatter Fields

Every value sits on one line — no wrapping, no `>` or `|` block scalars. The parsers read
line by line and now fail on anything else, where a wrapped `summary` used to yield a
truncated index row.

- **`status`** — `Accepted`, `Archived`, or `Superseded`. All three stay in the repo; the last two are excluded from `docs/adr/INDEX.md`, which is what an agent loads by default.
  - `Accepted` — in force, and worth carrying in context.
  - `Archived` — in force, but defended by something other than being read, so it need not be carried in context. Archive only when you can **name a defence the breach path passes through while the work is still being planned**. Only three qualify, unless another meets that same timing test: a comment wherever a breach would be authored, met as an agent explores the code; a path-scoped rule covering the scope, met when an agent reads a file the decision binds and qualifying only on the terms set out below; and a breach so large it needs its own ADR, met when the archived-decisions check below runs. An automated check is not enough on its own — a failing hook or pull request arrives after the wrong work is built, protecting the branch rather than the effort. Judge a defence by whether a breacher meets it in time; how tempting the rejected option is decides nothing. Four ways one fails: a comment covers only the sites it sits in, so treat a set of files as growing unless you can call it closed; a rule reaches only the reader whose tools load it, so a file read from a shell meets nothing and one created new meets nothing until something reads it back, which may be after the breach is authored; a note in the files that *keep* a decision does not guard the new file that would break it; and where an ADR rejects several options, a defence covering one covers none. **Name the defence in `archived-because`**; archiving without one is a bet nobody recorded. Set the status whenever a defence that passes the timing test exists, including long after writing.
  - `Superseded` — replaced by a later ADR; set `superseded-by`.

  Status tracks only whether a decision is in force and how it is defended. A provisional decision, or one near its revisit trigger, stays `Accepted` — nearly reopenable makes it more worth carrying, not less.
- **`date`** — ISO date the ADR was written.
- **`scope`** — **the paths where a breach of this decision would be authored**, as an inline list of exact files and directory prefixes ending in `/` (e.g. `[src/db/, alembic.ini]`). That is the test, not "what the decision is about": it is what lets the field be read backwards, from a file someone is editing to the decisions governing it, which reaches a reader who never thought to search. Required, because an absence would say no more than a missing keyword list did — unfilled and deliberate look alike.
  - **Paths resolve from the repo root**, unlike the reference links below, which resolve from the ADR. `src/db/` in `scope`; `../../src/db/` in a link.
  - **Not globs.** Matching one means parsing a grammar most repos do not define, and a prefix survives a rename that a pattern naming files would not.
  - **Name the shallowest set that is true.** A wide entry is right where the decision is wide. Where a decision covers three of six sibling directories, name the three: the parent would be shallower and false, and a false entry is worse than a long list. Every entry is a path a later refactor can break, so depth you did not need is maintenance you did.
  - **A repo-wide convention has no root shorthand** — name the top-level directories it genuinely reaches. Being made to list them is the point: most "repo-wide" decisions turn out not to be.
  - **An `Archived` ADR defended by a rule names that rule file too** — the files a comment defends are in `scope` already; the rule defending them is not. See Defending a decision with a path-scoped rule, below.
  - **`scope: []`** is a real answer, for a decision whose subject is not a file at all — a platform setting, a habit at review time. Say in Decision why there is no file home.
  - **Getting it wrong fails loudly**, where a generator enforces it: an entry naming nothing on disk is an error, as is a directory written without its trailing `/`, which would otherwise match that one path and silently cover nothing beneath it.
- **`summary`** — one sentence: what was decided, not why. This appears verbatim in the index. Phrase it so a reader who sees _only_ the frontmatter won't breach the decision: name the binding choice, including the notable rejected alternative where one exists (e.g. "Use mypy, not ty"). Leave the revisit trigger to `revisit-when`: the index carries that in a column of its own, so naming it here spends the reader's sentence twice.
- **`revisit-when`** — one sentence naming the condition that would change the choice; omit where none would. A condition the decision accommodates is a premise, not a trigger; one that would replace the decision outright is still a trigger, since it says when to look and what the answering ADR does is settled then, not now. State the condition alone and not the option it argues for — Decision has already weighed that. Where several conditions each reopen the ADR, put them on the one line and phrase each so it can be cut without the rest — the discharge workflow spends them one at a time.
- **`revisit-discharged-by`** — the number of the ADR that met the trigger and answered it, as a bare integer (`11`, not `011`); omit until one has, and never set it without `revisit-when`. It empties the ADR's Revisit cell in the index, which is its job: a spent condition stops costing every reader context.
- **`archived-because`** — one sentence naming the defence and where a breacher meets it, so whether and why an ADR left the index reads at a glance. Required when status is `Archived`; omit otherwise. One line, whichever defence applies:
  - `archived-because: A comment at the top of every workflow file names the pin, met while the workflow is being edited.`
  - `archived-because: Nothing breaches this without its own ADR, met at the archived-decisions check.`
  - `archived-because: .claude/rules/testing.md states the convention for every test file, met when an agent reads one.`
- **`superseded-by`** — the superseding ADR's number, as a bare integer; omit unless status is `Superseded`.

`Archived` and `Superseded` each require the field above bearing their name and refuse the other's; `Accepted` refuses both. A generator reports a breach of that pairing, where one is wired in, so a status changed without its field can't leave the old one behind reading as current. The revisit fields pair with each other rather than with a status: the breach reported is a `revisit-discharged-by` with no `revisit-when` to spend, and neither field is constrained by status — though a discharge on a `Superseded` ADR is dead metadata, for the reason the discharge workflow gives. Find out what triggers the generator you have rather than assuming it sees every change: this skill's reference implementation runs in CI on a pull request touching `docs/adr/` or `scripts/`, and locally only from a pre-commit hook, and only when the commit stages an ADR.

## Conventions

- **Option 1 is always "Do nothing"** — sets the stakes. Describe the status quo and let its Pros/Cons/Risks show what deciding nothing costs; don't explain the option's purpose in the ADR — that's guidance to you, not content.
- **Option 2 is the accepted option** — except where the decision is to keep the status quo, when Option 1 is, and the ADR is `Accepted` like any other. Recording an existing constraint is not a different approach from keeping it, so don't split the two into rival options to satisfy the numbering. Rejected alternatives appear as Options 2, 3, etc. Trivial mitigations (e.g. adding a comment or a rule) are implementation details of the "do nothing" choice and do not warrant their own option — unless the ADR archives itself on one, which makes it load-bearing, and the Decision must name it as the defence. Numbering and the `(Accepted)` marker are fixed when the ADR is written; `status` changes later, so never derive one from the other — a superseded ADR keeps the marker on the option that won.
- **Options must be mutually exclusive** — each must represent a fundamentally different approach. Test: could any two options be combined without contradiction? If yes, they aren't mutually exclusive. Two failure modes:
  - _Implementation details as options_ — if two options share the same core approach but differ in implementation, the variant belongs as a sub-heading within the parent option, not a top-level option
  - _Multi-dimensional problems_ — if what looks like a list of options is actually two separate decisions, structure around the primary; handle the secondary as a sub-question in the Decision section or write a follow-up ADR
- **Compare options on what differs, not on what they share** — where two or more options carry the same cost, name it once and set it aside, then rank on the residual. **Put it in a short paragraph directly under `## Options`, before Option 1**, naming which options share the cost and stating that it does not rank them; the per-option Pros/Cons/Risks have no slot for it, so without that paragraph the cost gets restated under each option and the section ranks by total weight rather than by substance — and the heavier-looking option loses without ever being compared. Worked example: two options both move every caller from `python3 x.py` to `uv run x.py`, so say that once; what remains — one of them lets each script pin a shared library independently, the other has a single lockfile — is the whole decision, and it reverses the ranking the migration cost implied.
- **Number sequentially** — never reuse or renumber
- **Check archived decisions before recording a new one** — `rg -l 'status: Archived' docs/adr/` and read any whose subject touches yours. They are out of the index by design, so writing an ADR is the one moment they resurface — which is what makes archiving on that defence safe, and unsafe for any breach too small to warrant one. A new decision contradicting an archived one supersedes it rather than sitting alongside it.
- **Read the live revisit triggers before recording a new decision** — the index carries them in a column where one is generated, and `rg 'revisit-when' docs/adr/` finds them where it is not. Either way they are how a trigger reaches someone who never opens the ADR holding it. Meeting a condition is not by itself discharging it: a decision that *answers* the condition discharges the trigger, one that only makes it fail loudly arms it, one that closes a mechanism by which the condition could arrive narrows it, and one that reverses the older decision supersedes it. Each has its own workflow below; each is a step of the work, not a note in passing.
- **Never edit INDEX.md** — the generator regenerates it, however this repo runs it; find that out rather than assuming a hook or a workflow does
- **Supersede, don't edit** — new ADR for changed decisions; mark the old one superseded
- **Keep it concise** — enough to reconstruct the reasoning, not a thesis
- **Check every factual premise against the thing itself** before writing it — the tool's config, the workflow file, the live setting via its API. Documentation is not a source, including this repo's own: a doc asserting the same thing is as likely to be where the error came from. Premises outlive the session that wrote them and are read as settled. Where one can't be checked — a setting behind access you don't have — ask the maintainer rather than writing the gap into the ADR: a premise the decision rests on is worth waiting for, and one that isn't should come out.
- **Each section has a distinct job — don't let them overlap:**
  - _Context_ — the problem and forces; stop before proposing any remedy
  - _Options_ — approaches and trade-offs; don't restate what Context already said
  - _Decision_ — why this option over others; don't re-describe the chosen option (Options already did that)
  - _Consequences_ — what changes or must be managed downstream; not a restatement of the accepted option's pros/cons

## Citing an ADR from code

A comment naming an ADR reaches a reader the index cannot: someone editing the file, who never thought to search. A comment defence under `archived-because` *is* such a citation, which makes these load-bearing rather than decorative — so the rules below are yours to apply while archiving, not only the code author's.

- **Archiving on a comment defence means writing the comments in the same change.** Archive first and cite later and the decision spends the gap out of the index and undefended. Name in `archived-because` where the comments went, and treat a set of files you cannot call closed as a reason not to archive at all. This is also the moment to ask whether anything verifies those comments still exist — the first archival is what makes such a check specifiable, so decide then and record the answer either way, rather than leaving it to a trigger nobody is reading.
- **A citation names the ADR number and what the decision forbids at that line — never the reasoning.** The reasoning has a home; a comment repeating it becomes a second source of truth, and the two drift. An error message is the exception, since its reader is already blocked and a clause of *why* is what makes it actionable. Fix one citation form per repo and record it where code authors meet it: two forms in one tree is what leaves a later check with nothing to match.
- **A citation covers the file it sits in and nothing else.** Citing three of five call sites reads as a defended decision and is not one.
- **Deletion is the failure to plan for, not staleness** — numbers are never reused, so an ageing citation still points into a chain. But refactor the code and the comment goes with it, and where it was an `Archived` ADR's defence, nothing reports the loss, because the ADR is invisible by design.

## Defending a decision with a path-scoped rule

A rule is a Markdown file in `.claude/rules/` whose frontmatter carries a `paths:` list of
globs; the harness injects the whole file when its read tool touches a file one of them
matches. A rule reaches files nobody has written yet, which a comment cannot — so where a
decision binds a set you cannot call closed, and no breach of it would be large enough to
need its own ADR, the rule is the defence left. It defends only what its harness reaches,
where a comment sits in the bytes and so meets every reader by every route. Archive on a
rule alone only where the breaches you are defending against would be authored by an agent
that reaches the file through the tool its harness loads rules on — see what loads it,
below, because the routes that miss are ordinary ones. Where a person in an editor would
author a breach, the files they touch need a comment too.

Written in the same change as the archival, naming the ADR's number and stating what the
decision forbids while the reasoning stays in the ADR, and named in `archived-because` —
as for a comment. Beyond that:

- **Every path in `scope` needs a defence reaching it**, bar the rule's own entry, which
  the next bullet puts there. Defences compose, so a rule for the growing part and
  comments in the files that are fixed is a complete answer — but only where that second
  part is closed, and a directory prefix rarely is, which usually leaves widening the
  globs as the only way to cover one. `scope` holds prefixes and never globs, so the
  translation is yours to make: `test/` needs `test/**`, where a rule matching only
  `**/test_*.py` leaves the rest of that prefix uncovered.
- **Name the rule file in `scope` as well**, by the path the repository stores — where
  `.claude/rules` is a symlink to another directory, that is the target's path, which is
  what gets staged and what a lookup matches. Deleting the rule removes the defence, and
  the ADR being out of the index by design, nothing obvious reports the loss. A reverse
  lookup from a path reports the ADR to whoever *narrows* the rule; whether it reports a
  deletion depends on the lookup, and one keyed to added and modified paths will not.
  Where a generator checks that scope entries resolve on disk, the deletion breaks the
  build — but on whichever later change runs the generator, which is rarely the one that
  deleted the rule. Neither mechanism catches the symlinked form of the entry, which
  resolves on disk and quietly matches nothing. Find out what each of yours does before
  counting on either.
- **Never archive on a rule outside the repository** — one in `~/.claude/rules/` loads on
  your machine and on nobody else's.
- **Read the file your globs cover least obviously, and watch the rule arrive**, before
  archiving on it. Any matching file proves the harness loads rules at all; the awkward
  one — the file at the edge of the prefix, the extension you nearly forgot — is what
  proves the coverage you are about to claim.

**What loads it, verified in Claude Code on 2026-08-29 and worth re-measuring — read a
matching file with the read tool, then with `sed`, and watch which one injects the rule:**
the read tool, in a subagent as much as a main session. Not a shell read (`cat`, `sed`,
`grep`), which is no edge case: a harness mode that steers reading to the shell makes it
the common path. Not the `Write` that creates a matching file either
([anthropics/claude-code#23478](https://github.com/anthropics/claude-code/issues/23478),
closed as not planned), so a rule reaches a new file only through whatever read comes
after it — and where a breach is authored file-first with nothing read beforehand, it
arrives after the work and defends nothing.

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
  stale and are not worth keeping in sync. That holds because an ADR describes a decision
  still in force, so following a moved path keeps the ADR true. The rule inverts wherever
  an entry describes a moment instead: a changelog entry is about one released version,
  so healing its links would make it describe a version that never existed — which is why
  `phx:writing-release-notes` requires a pinned ref there.
- **Paths resolve from the ADR, not the repo root** — the ADR lives in `docs/adr/`, so a
  path from the repo root needs the `../../` prefix (e.g.
  `../../skills/writing-adrs/SKILL.md`), and a peer ADR is bare (`001-some-decision.md`).
  A repo-root-relative path renders as a broken link.
- **Targets by type** — GitHub issue/PR → the full issue/PR URL; web page → its
  canonical URL; code symbol → the path to the defining file; peer ADR → its filename.
- **A code symbol from a dependency not vendored in this repo** links to that
  dependency's own upstream source (e.g. its GitHub repo, on its default branch) —
  never to a local install path (`.venv`, `node_modules`, etc.). That path is
  typically gitignored, so the link renders fine in your own checkout and is broken
  for everyone else's. Verify the branch and path resolve before citing them, the
  same as any other factual premise.
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

**Exception — a frontmatter migration across the whole corpus.** Renaming or rekeying a field in every ADR is one change, not N substantial edits, so the ADR recording the migration carries both passes on the corpus's behalf. Where the migration *authors* a value per ADR rather than rewriting one mechanically, that judgement is still worth checking somewhere: have Pass 1 on the migration ADR review the authored values as a set, and say in the prompt that it is doing so.

### Pass 1: Principal-engineer review (subagent)

Dispatch a subagent to review the draft as a senior engineer would. Give it the ADR file path; the codebase and prior ADRs (`docs/adr/`) are available to it. Prompt it to assess:

- **Soundness** — does the accepted option make sense for _this_ project, given its constraints and prior ADRs? Would a principal engineer choose differently?
- **Unsurfaced trade-offs** — are there notable costs, risks, or downsides of the accepted option the ADR does not mention?
- **Implicit assumptions** — what does the decision take for granted that a reader would not know? Each should be stated explicitly.
- **Archival** — if the ADR is `Archived`, does `archived-because` name a defence that exists and lands early enough to change the plan rather than only reject the result? Push back hard: a decision that merely feels settled is the tempting one to archive, and a wrongly archived one stays invisible until someone re-litigates it. Where the defence is a path-scoped rule, have it open the rule file: does it exist, does it live in the repository, is every path in `scope` bar the rule's own entry reached by the rule's globs or by another named defence, does it state the constraint itself rather than only pointing at the ADR, and did the archiver watch it load? If it is `Accepted`, ask whether a *qualifying* defence could be named — not whether anything defends it, since a real defence can still fail the timing test.
- **Revisit trigger** — does `revisit-when` state a condition whose arrival would change the choice, rather than one the decision already accommodates? Where it is unset, ask what would reopen the decision: nothing reopening it is a real answer, an unstated condition is one nobody will act on.
- **Factual accuracy** — is every claim about tooling, workflow, or platform behaviour true of the actual configuration? Have it check config, workflow files, and live settings itself rather than review your notes, and report what each claim was verified against.
- **Frontmatter sufficiency** — would an agent that reads _only_ the frontmatter (`summary`, `scope`, `status`, `revisit-when`) avoid breaching this decision? If the decision constrains future work, the `summary` must make that constraint discoverable and `scope` must name the paths where a breach would be authored — an ADR scoped narrower than it binds is unreachable from the files it governs. This holds for `Archived` ADRs too, even though nothing reads their frontmatter by default: archiving is reversible, and one restored later — perhaps because it was archived in error — carries whatever it was written with.

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
2. In the **old** ADR, set `status: Superseded` and the new ADR's number as `superseded-by` (`13`, never `013`)
3. Commit both files together

Superseded ADRs are excluded from the index automatically. Marking the old one is not a substantial edit — see the note at the foot of the next section.

## Discharging a Revisit Trigger

When a new ADR meets an older one's `revisit-when` and answers it:

1. Write the new ADR, quoting in its Context the trigger it met
2. In the **old** ADR, set the new ADR's number as `revisit-discharged-by` (`13`, never `013`), leave `revisit-when` as written, and strike through the condition everywhere the body sets it out, naming the ADR that spent it
3. Commit both files together

Step 2 edits the body because that is where the condition reads as an instruction, and it is what someone who opened the file is reading. Leave it standing and the ADR tells them to revisit while its frontmatter says the question is answered. Search the whole body rather than the section you expect: where an ADR carries several conditions, one may be argued in Decision and another only named in Consequences, each worded to its paragraph rather than to the field.

Where `revisit-when` names more than one condition and the new ADR spends only one, cut that condition from the field rather than setting `revisit-discharged-by`, striking it through in the body the same way. The ADR still holds a live trigger, so the field stays live and the index keeps carrying it.

A new ADR that reverses the older decision supersedes it instead — follow the supersession workflow above and set no discharge field. A `Superseded` ADR is already out of the index, so a discharge recorded on one empties a cell nobody reads.

A new ADR that closes one *mechanism* by which an older condition could arrive has not discharged it either: the condition survives, narrower. Cut the closed mechanism from `revisit-when` and name the closing ADR where the older body sets the condition out. This is the easiest of the four to miss, because the new ADR is not about the old one at all — and a narrowing left untraced reads as the two ADRs simply disagreeing.

An ADR that *arms* an older trigger has not discharged it either. Arming makes the condition fail loudly — a check that rejects the breach and names the ADR to reopen — where discharging answers the question the condition was waiting on. The condition is still the one to revisit on, so leave both fields as they are and record the arming as a Consequences bullet in the older ADR.

None of the edits these four workflows make to an older ADR — marking it superseded, striking a spent condition, cutting a closed mechanism, recording an arming — is a substantial one, so none owes the review passes. The decision is untouched, and the new ADR carries both passes for the pair.
