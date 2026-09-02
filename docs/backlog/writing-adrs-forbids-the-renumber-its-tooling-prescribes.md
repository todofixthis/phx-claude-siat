# `writing-adrs` forbids the renumber the ADR tooling refuses to proceed without

> Recorded 2026-09-02, from the surrogate review of the backlog items raised alongside the
> ADR number collision check. Never filed as a GitHub issue.

## What

[`SKILL.md`][] line 111 states the rule without exception:

> - **Number sequentially** — never reuse or renumber

The collision check in [`generate_index.py`][] tells its reader the opposite, and does not
merely suggest it: `generate()` returns 1, so the pre-commit hook stops the commit and
`pr.yml`'s `adr` job fails the build until someone does what the skill forbids.

> renumber whichever has not merged, since a merged number is already referenced and
> cannot move

`a9b5db4` is the precedent. A rebase left `018-admit-a-path-scoped-rule-as-an-archival-defence.md`
and `018-track-deferred-work-in-the-repository.md` in the same tree; the second moved to
020, 019 being taken, and its H1 moved with it.

## The bullet welds two rules together

Reuse and renumber are different operations:

- **reuse** — giving one decision's number to a later decision. Always breaks citations:
  `ADR 018` silently resolves to something else.
- **renumber** — moving one decision to a different number. Breaks citations only where the
  old number was already cited, which is to say only where it merged.

Line 131 is the only rationale recorded anywhere for either — *"numbers are never reused, so
an ageing citation still points into a chain"* — and it justifies the first alone.
`rg 'never reuse|reused|renumber|sequential'` over `skills/`, `docs/adr/`, `.agents/` and
`AGENTS.md` returns those two lines and nothing else, so no ADR stands behind the renumber
prohibition.

Read that way the two are not a standoff. The collision message's caveat — *since a merged
number is already referenced* — is the renumber rule stated with the condition that makes it
true, and line 111 is the same rule stated too broadly by being bundled with reuse.

## Why it is worth doing

An agent that hits a collision cannot proceed without renumbering, goes to the skill for the
procedure, and finds it forbidden. It then re-derives the reconciliation alone — that an
unmerged number is cited by nothing, so moving it breaks no chain — or concludes the tooling
is wrong and stops to ask. Every collision pays that, and the collision is the normal case:
numbers are allocated by reading the directory, so any two branches open at once take the
same one.

## The open question

Whether the skill gains the condition, or the message stops prescribing a renumber. The
first looks right on the evidence above, but this is not a call to take from inside the
work: it changes a **published** skill's stated rule for consumers who have no `docs/adr/`
of ours to check it against. That external reach is what separates it from an internal
consistency call, and it belongs to whoever owns the skill's text.

If the skill gains the condition, it must state the constraint itself rather than cite an
ADR number, for the same reason.

## Acceptance

- `skills/writing-adrs/SKILL.md` says whether an ADR whose number has not merged may be
  renumbered, and on what condition — or the collision message in
  `scripts/adr/generate_index.py` stops prescribing one.
- The two are read against each other in the same change, so whichever moves, they agree.
- Any condition added to the skill is stated in full, no ADR number standing in for it.

[`SKILL.md`]: ../../skills/writing-adrs/SKILL.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
