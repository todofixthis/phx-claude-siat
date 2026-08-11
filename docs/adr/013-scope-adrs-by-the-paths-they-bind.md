---
status: Accepted
date: 2026-08-10
scope: [.github/workflows/pr.yml, .githooks/pre-commit, docs/adr/, scripts/adr/, skills/writing-adrs/]
summary: Key ADR frontmatter to the paths a decision binds — exact paths and directory prefixes, never globs — rather than to free-text tags, and answer the reverse question, which decisions bind this file, from the pre-commit hook.
revisit-when: A third decision scopes `[]`, making decisions with no file home common enough that an empty scope stops carrying signal.
---

# 013: Scope ADRs by the paths they bind

## Context

Every ADR carries a `tags` list, described by [`writing-adrs`][] as "keywords an agent
would use to locate this ADR". Twelve ADRs in, the corpus can be measured rather than
guessed at: 70 distinct tags across 116 uses, **45 of them used exactly once**, and only
five appearing on four or more ADRs (`releases` and `ci` on seven; `marketplace`,
`versioning` and `python` on four). The Tags column was 1211 of `INDEX.md`'s 6184
characters — a fifth of the file an agent loads by default.

Neither end of that distribution filters anything. A tag used once is a synonym for one
document, which its own title and summary already name; a tag on seven of twelve
documents excludes nothing. Nor does any tooling read the field: [`generate_index.py`][]
renders it and nothing else consults it, so the index is scanned rather than searched.

The cause is not that authors tagged carelessly. A free vocabulary has no coordination
point, so each author mints terms without reference to the last, and — decisively — **a
tag can never be wrong**. Nothing can contradict it, so nothing ever pushed back.

Underneath the tagging question is one the index has never answered. `INDEX.md` serves a
reader who already suspects a decision exists and goes looking. The reader who most needs
an ADR is the one who does not: someone editing a file, unaware that a decision binds it.
[ADR 001][]'s no-`version` invariant and [ADR 010][]'s `source` pin are both defended
against that reader by a check; most decisions are not.

## Options

Options 2 to 5 all rewrite the frontmatter of twelve ADRs. That cost is identical across
the four and ranks none of them, so it is set aside here; what follows compares them on
what the field is keyed to, what can be checked once it is, and what each does to the size
of the index.

### Option 1: Do nothing — keep `tags`

Authors keep tagging, and the guidance to think "what would I search for?" stands.

**Pros:** No migration, and no decision to make about a field nobody has complained about.
**Cons:** The measurements above are the steady state, not a transitional mess: three more
ADRs add roughly fifteen more terms on the same terms as the last seventy.
**Risks:** A field that cannot be wrong cannot be fixed either, so the decay is invisible
to every check and every reviewer, and only ever noticed by someone who goes counting.

### Option 2: Key the field to the paths a decision binds (Accepted)

`scope` lists exact file paths and directory prefixes; `[]` says the decision binds no
path. `generate_index` rejects an entry naming nothing on disk, and a `--for <path>` mode
reports the decisions binding a path, which the pre-commit hook runs over staged files.

**Pros:** The filesystem is a coordination point that already exists, so there is no
vocabulary to agree on and nothing to mint. Replaces the Tags column with a smaller one.
**Cons:** Narrower than what `tags` claimed: this serves retrieval from the work and
abandons the grouping-by-subject the tag list gestured at.
**Risks:** Some decisions bind no file — a GitHub ruleset, a habit at commit time — and
for those the field says nothing the reader can act on.

### Option 3: Key the field to a domain register

A committed register of domains; each ADR picks one, and adding a domain is a deliberate
edit to the register.

**Pros:** A closed vocabulary that groups the index, and one that covers the decisions
binding no path. Membership is checkable, so it cannot decay the way free tags did.
**Cons:** Whether an ADR picked the *right* domain is not checkable, and no domain answers
"which decisions bind the file in front of me" — the register would have to be consulted
by someone who already suspected an ADR existed.
**Risks:** At this corpus size a register fine enough to discriminate is close to one
domain per two ADRs, so it buys an argument per ADR before it buys a filter.

### Option 4: Add `scope` and keep `tags`, or add `scope` and a domain register

Two fields and two columns: scope for retrieval, and a second axis for grouping — either
the existing tags or the register from Option 3.

**Pros:** Nothing is given up, and the grouping claim survives. Paired with a register
rather than tags, the second axis is checkable too.
**Cons:** Adds a column to the index on top of replacing one, so the file an agent loads
by default grows — against a grouping benefit that twelve ADRs of evidence say went
unrealised.
**Risks:** Two axes to fill per ADR. Paired with tags, one of them still cannot be wrong,
so it decays as before while `scope` lends the pair an air of being maintained.

### Option 5: Drop `tags` and add nothing

Delete the field and the column; find ADRs through the summary column and `rg` over
`docs/adr/`.

**Pros:** Reclaims the index space for no new schema, and the ADR bodies are richer than
any tag list.
**Cons:** Leaves the reader who does not know a decision exists exactly where they were,
which is the half of the problem the tag field was never solving either.
**Risks:** Nothing to check and nothing to look up, so the next person to notice the gap
re-opens this from scratch.

## Decision

Key the field to paths. The measurements settle Option 1, and among the rest the deciding
property is **reach**: a path is what a person editing code already has in hand, which is
what makes the `--for` lookup possible at all. No vocabulary can offer that, however well
governed, because a domain is something you must already be searching by. That is the point
of the change rather than a convenience laid on top of it — without the reverse lookup this
would be a renamed column, since a differently-keyed field an agent still has to think to
consult is the same field. Option 4 buys the grouping axis back at the cost of a wider
index, and the evidence above is that grouping was the half nobody used.

Checkability is a real but narrower advantage than it looks, and worth stating honestly: an
entry naming a path that does not exist fails, so scope *rots* loudly where a tag could not.
Nothing checks the converse — that every path the decision binds is listed — and that gap
is the one that matters, because an unlisted path is a decision `--for` will never surface.
Scope is checked against false positives only.

Entries are exact paths and directory prefixes rather than globs, and an entry that looks
like one is rejected rather than merely discouraged. Not for want of a matcher — `fnmatch`
is standard library and would do it — but because a prefix survives the file renames a
pattern naming files would not, and because an exact entry makes the rot check a single
`Path.exists` where a pattern needs a filesystem walk to answer whether it still matches
anything.

The narrowing in Option 2's Cons is accepted rather than mitigated. Grouping by subject was
what `tags` promised and, on the evidence above, is not what it delivered; giving up a claim
the field was not honouring costs nothing real.

## Consequences

- `scope` is required and `[]` is a valid value. An optional field's absence would carry
  no more than a missing tag list does — unfilled and deliberate look identical — so the
  empty index cell means "this decision binds no path" only because the field cannot
  simply be left out.
- Scope is checked for `Accepted` and `Archived` decisions, both being in force and both
  editable, and not for `Superseded` ones: a superseded ADR naming a deleted path would be
  a build failure whose only remedy — editing it — "supersede, don't edit" forbids. That
  the rule is absolute even where an edit changes no decision is a question about the rule
  rather than about scope, and is not settled here.
- `--for` runs only in the pre-commit hook, which is opt-in per clone and not installed by
  CI, so the central benefit reaches only clones that ran `git config core.hooksPath`.
- **`--for` does not qualify as an archival defence** and must not be mistaken for one: it
  fires at commit time, after the work exists, which is the timing `writing-adrs` rejects
  when it declines to let an automated check archive a decision. It prompts rework where a
  comment in the code changes the plan. [ADR 014][] covers the in-time case; the two are
  complementary.
- Removing `tags` breaks any repository whose own conventions rest on it, and
  `generate_index` now rejects the field outright rather than ignoring it, so a
  half-finished migration cannot pass in either direction.
- The field ships to other repositories through `writing-adrs`, generalised from a
  corpus whose decisions are unusually filesystem-shaped because this repository largely
  *is* its own tooling. Where decisions concern runtime behaviour, data or process, scope
  will be empty far more often than it is here, and the revisit trigger above is written
  against this repository's corpus rather than theirs.

### Known tensions

Grouped for citation, not as a template: this is an ad-hoc heading in one ADR, not a
section `writing-adrs` defines, and one use is not enough to know whether the grouping
earns its keep.

Both entries are costs this decision **accommodates deliberately**, which is why neither is
a `revisit-when` — a condition the decision already absorbs is a premise, not a trigger.
They are accepted because `scope` is a net gain over the tags it replaces while carrying
both. The answer to each is also the same: `writing-adrs` is intended to grow from a
skill-and-scripts amalgam into a system with its own hooks, tools and state, and the entries
accumulated meanwhile — brittle ones included — are the evidence that design will draw on.

1. **Scope rot is silent outside the paths that trigger a check.** Both the hook and the
   `adr` job in [`pr.yml`][] fire only on ADR or script changes, so a rename under
   `skills/`, `.claude-plugin/` or `.githooks/` rots an entry and surfaces on some later,
   unrelated ADR commit — landing the remedy on whoever is committing then rather than
   whoever renamed. That is why `pr.yml` is itself in this ADR's scope: narrowing that
   filter is how this decision gets breached. Where the failure is real rot rather than a
   typo, drop the entry, and ask whether a decision binding nothing should still be
   `Accepted`. Not a trigger: the remedy is not to reopen this decision but to watch paths
   continuously, which is the system above rather than a different keying.
2. **Shallow prefixes and useful output pull against each other.** Deep entries break on
   rename, so the advice is to prefer the shallowest prefix that is true — but `scripts/`
   is already scoped by three decisions, so any script commit reports three. Advisory
   output that fires on almost every commit is tuned out, and nothing measures that. Not a
   trigger: the remedy is per-ADR, since a decision reporting on most commits has a scope
   wider than the decision, and the fix is that ADR's scope rather than this one's rule.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`pr.yml`]: ../../.github/workflows/pr.yml
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
