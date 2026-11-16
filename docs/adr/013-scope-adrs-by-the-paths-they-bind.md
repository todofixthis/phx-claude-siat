---
status: Accepted
date: 2026-08-10
scope: [.github/workflows/pr.yml, .githooks/pre-commit, docs/adr/, skills/writing-adrs/]
summary: Key ADR frontmatter to the paths a decision binds — exact paths and directory prefixes, never globs — rather than to free-text tags, and answer the reverse question, which decisions bind this file, from the pre-commit hook.
revisit-when: A third decision scopes `[]`, making decisions with no file home common enough that an empty scope stops carrying signal.
---

# 013: Scope ADRs by the paths they bind

## Context

Every ADR carries a `tags` list, which [`writing-adrs`][] describes as "keywords an agent
would use to locate this ADR". Twelve ADRs in, the corpus can be measured instead of
guessed at. It holds 70 distinct tags across 116 uses, and **45 of them appear exactly
once**. Only five appear on four or more ADRs: `releases` and `ci` on seven, and
`marketplace`, `versioning`, and `python` on four. The Tags column took 1211 of
`INDEX.md`'s 6184 characters, a fifth of the file an agent loads by default.

Neither end of that distribution filters anything. A tag used once is a synonym for one
document, and that document's title and summary already name it. A tag on seven of twelve
documents excludes nothing. No tooling reads the field either. [`adr.py`][] renders it,
nothing else consults it, and so agents scan the index instead of searching it.

The cause is not that authors tagged carelessly. A free vocabulary has no point of
coordination, so each author invents terms without reference to the last. The deciding
cause is that **a tag can never be wrong**. Nothing can contradict a tag, so nothing ever
pushed back.

Under the tagging question sits one the index has never answered. `INDEX.md` serves a
reader who already suspects a decision exists and goes looking. The reader who most needs
an ADR is the one who does not suspect: someone editing a file, unaware that a decision
binds it. A check defends [ADR 001][]'s no-`version` invariant and [ADR 010][]'s `source`
pin against that reader. Most decisions have no such check.

## Options

Options 2 to 5 all rewrite the frontmatter of twelve ADRs. That cost is the same for all
four and ranks none of them, so this section sets it aside. It compares the options on what
the field is keyed to, what a check can verify once it is, and what each does to the size
of the index.

### Option 1: Do nothing — keep `tags`

Authors keep tagging, and the guidance to think "what would I search for?" stands.

**Pros:** No migration, and no decision to make about a field nobody has complained about.
**Cons:** The measurements above are the steady state, not a transitional mess. Three more
ADRs would add about fifteen more terms, chosen the same way as the last seventy.
**Risks:** A field that cannot be wrong cannot be fixed either. No check and no reviewer
sees the decay, and only someone who goes counting ever notices it.

### Option 2: Key the field to the paths a decision binds (Accepted)

`scope` lists exact file paths and directory prefixes, and `[]` says the decision binds no
path. `generate_index` rejects an entry that names nothing on disk. A `--for <path>` mode
reports the decisions that bind a path, and the pre-commit hook runs it over staged files.

**Pros:** The filesystem is a point of coordination that already exists, so there is no
vocabulary to agree on and no term to invent. A smaller column replaces the Tags column.
**Cons:** Narrower than what `tags` claimed. Scope serves retrieval from the work, and gives
up the grouping by subject that the tag list gestured at.
**Risks:** Some decisions bind no file, such as a GitHub ruleset or a habit at commit time.
For those decisions the field says nothing the reader can act on.

### Option 3: Key the field to a domain register

A committed register of domains. Each ADR picks one, and adding a domain is a deliberate
edit to the register.

**Pros:** A closed vocabulary that groups the index and covers the decisions that bind no
path. A check can verify membership, so the register cannot decay the way free tags did.
**Cons:** No check can verify that an ADR picked the *right* domain, and no domain answers
"which decisions bind the file in front of me". Only someone who already suspected an ADR
existed would consult the register.
**Risks:** At this corpus size, a register fine enough to discriminate needs close to one
domain per two ADRs. It costs an argument per ADR before it delivers a filter.

### Option 4: Add `scope` and keep `tags`, or add `scope` and a domain register

Two fields and two columns: `scope` for retrieval, and a second axis for grouping. The
second axis is either the existing tags or the register from Option 3.

**Pros:** Nothing is given up, and the grouping claim survives. Paired with a register
instead of tags, the second axis is checkable too.
**Cons:** Adds a column to the index on top of replacing one, so the file an agent loads by
default grows. Twelve ADRs of evidence say the grouping it pays for went unused.
**Risks:** Authors fill two axes per ADR. Paired with tags, one axis still cannot be wrong,
so it decays as before, and `scope` makes the pair look maintained.

### Option 5: Drop `tags` and add nothing

Delete the field and the column, and find ADRs through the summary column and `rg` over
`docs/adr/`.

**Pros:** Frees the index space without a new schema, and the ADR bodies say more than any
tag list.
**Cons:** Leaves the reader who does not know a decision exists exactly where they were.
The tag field never served that reader either.
**Risks:** With nothing to check and nothing to look up, the next person to notice the gap
reopens the question from scratch.

## Decision

Key the field to paths. The measurements rule out Option 1. Among the rest, the deciding
property is **reach**. A person editing code already has a path in hand, and that path is
what makes the `--for` lookup possible at all. No vocabulary can offer the lookup, however
well governed, because you must already be searching by a domain to use one. The reverse
lookup is the point of the change, not a convenience added to it. Without the lookup, the
change would only rename a column, because a field keyed differently that an agent still
has to think to consult is the same field. Option 4 gets the grouping axis back at the cost
of a wider index, and the evidence above says grouping was the half nobody used.

Checkability is a real advantage, but narrower than it looks. An entry naming a path that
does not exist fails, so scope rots loudly where a tag could not. Nothing checks the
converse, that the entries list every path the decision binds. That gap is the one that
matters, because `--for` never surfaces a decision for a path its scope leaves out. The
check catches false positives only.

Entries are exact paths and directory prefixes, not globs, and an entry that looks like a
glob is rejected, not merely discouraged. A matcher is not the obstacle: `fnmatch` is in
the standard library and would do the job. Globs are out for two reasons. A prefix
survives file renames that a pattern naming files would not. And an exact entry makes the
rot check a single `Path.exists`, where a pattern needs a filesystem walk to tell whether
it still matches anything.

This decision accepts the narrowing in Option 2's Cons and does not mitigate it. `tags`
promised grouping by subject and, on the evidence above, did not deliver it. Giving up a
claim the field was not honouring costs nothing real.

## Consequences

- `scope` is required, and `[]` is a valid value. If the field were optional, its absence
  would carry no more than a missing tag list does, because an unfilled field and a
  deliberately empty one look identical. The empty index cell means "this decision binds
  no path" only because an author cannot leave the field out.
- The scope check covers `Accepted` and `Archived` decisions, because both are in force and
  both are editable. It skips `Superseded` ones. A superseded ADR naming a deleted path
  would fail the build, and the only remedy, editing the ADR, is what "supersede, don't
  edit" forbids. Whether that rule is absolute even where an edit changes no
  decision is a question about the rule, not about scope, and this ADR does not settle it.
- `--for` runs only in the pre-commit hook. The hook is opt-in per clone and CI does not
  install it, so the central benefit reaches only clones that ran
  `git config core.hooksPath`.
- **`--for` does not qualify as an archival defence**, and nobody should mistake it for
  one. It fires at commit time, after the work exists. `writing-adrs` rejects that timing
  when it declines to let an automated check archive a decision. `--for` prompts rework,
  where a comment in the code changes the plan. [ADR 014][] covers the in-time case, and
  the two complement each other.
- Removing `tags` breaks any repository whose own conventions rest on the field.
  `generate_index` now rejects `tags` outright instead of ignoring it, so a half-finished
  migration cannot pass in either direction.
- The field ships to other repositories through `writing-adrs`. It generalises from a
  corpus whose decisions are unusually filesystem-shaped, because this repository largely
  *is* its own tooling. Where decisions concern runtime behaviour, data, or process, scope
  will be empty far more often than it is here. The revisit trigger above is written
  against this repository's corpus, not theirs.
- [ADR 021][] narrows Known Tension #1 below, for the PR-review path only. The tension
  itself, and this ADR's acceptance of it, still stand for the omission case and the
  `develop` bypass.
- [ADR 022][] and [ADR 025][] build the system that the Known Tensions below deferred to: a
  shipped tool, session hooks, and per-session state. A hook now watches Known Tension #1
  continuously. The omission case stays open.

### Known tensions

This heading groups the entries for citation. It is not a template section. `writing-adrs`
does not define it, it appears in this ADR alone, and one use is not enough to know whether
the grouping is worth keeping.

Both entries are costs this decision **accommodates deliberately**. Neither is a
`revisit-when`, because a condition the decision already absorbs is a premise, not a
trigger. The decision accepts both because `scope` is a net gain over the tags it replaces,
even while carrying them. Each entry also has the same answer. `writing-adrs` is meant to
grow from a mix of a skill and scripts into a system with its own hooks, tools and state.
The entries collected in the meantime, brittle ones included, are the evidence that design
will draw on.

1. **Scope rot is silent outside the paths that trigger a check.** The hook and the `adr`
   job in [`pr.yml`][] both fire only on ADR or script changes. A rename under `skills/`,
   `.claude-plugin/`, or `.githooks/` therefore rots an entry, and the failure surfaces on
   some later, unrelated ADR commit. The fix then falls to whoever is committing at that
   point, not to whoever renamed. That is why `pr.yml` is itself in this ADR's scope:
   narrowing that filter is how someone breaches this decision. Where the failure is real
   rot and not a typo, drop the entry, and ask whether a decision that binds nothing should
   still be `Accepted`. Not a trigger. The remedy is to watch paths continuously, which is
   the system above, not to reopen this decision with a different key.
2. **Shallow prefixes conflict with useful output.** Deep entries break on rename, so the
   advice is to prefer the shallowest prefix that is true. But three decisions already
   scope `scripts/`, so any script commit reports three. People tune out advisory output
   that fires on almost every commit, and nothing measures how often that happens. Not a
   trigger. The remedy is per ADR. A decision that reports on most commits has a scope
   wider than the decision, and the fix is that ADR's scope, not this ADR's rule.

[ADR 001]: 001-co-locate-marketplace-and-plugin.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 021]: 021-validate-adr-scope-on-every-pull-request.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`pr.yml`]: ../../.github/workflows/pr.yml
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
