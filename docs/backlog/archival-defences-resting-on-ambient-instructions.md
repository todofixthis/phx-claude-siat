# Archival defences that rest on AGENTS.md are a third class the skill does not describe

> Recorded 2026-09-01, from an attempt to archive ADRs 011 and 018 on the ground that
> `AGENTS.md` is always loaded. Never filed as a GitHub issue.

## What

[`writing-adrs`][]'s `status` guidance names three defences that qualify for `Archived` —
a comment wherever a breach would be authored, a path-scoped rule reaching what the
decision binds, and a breach large enough to need its own ADR — and admits any fourth that
meets the same timing test. Ambient project instructions (`AGENTS.md`, symlinked as
`CLAUDE.md`) are a candidate fourth: they land before the session's first action, earlier
than a comment met during exploration and earlier than a rule, which loads only once a read
matches its globs.

The skill's `## Defending a decision with a path-scoped rule` is the shape this wants. That
section admits a defence whose reach depends on the harness, then spends itself on what
loads it and where that misses — "a rule reaches only the reader whose tools load it, so a
breacher reading from a shell meets nothing at all". Ambient instructions have the same
dependency and no such section, so the reach below is the measurement that one would need.

## What the attempt found

**Ambient instructions are not universally in context.** Measured on 2026-09-01 by asking
one subagent of each type to report its own context with no tool use, against a control
question — a Markdown line-length rule this repo does not have — whose honest answer was
"not present". Every type answered the control correctly, so the split below is signal
rather than confabulation:

| Agent type | Project `AGENTS.md` |
|---|---|
| `claude` | present |
| `claude-code-guide` | present |
| `Explore` | **absent** |
| `general-purpose` | present |
| `Plan` | **absent** |
| `statusline-setup` | present |

The two absent types are the two the harness describes as read-only. That is a weaker
guarantee than it sounds: both lack `Edit` and `Write` but keep `Bash`, so either can
author a breach through a heredoc, and `Plan` is the type doing the planning the skill's
timing test is named after.

**Re-measure before relying on this table.** Which types exist and what each is given are
harness behaviour, not repo state — nothing here changes when they do, and no check fails.
The method above is the whole of it: one probe per type, one control question.

**The tempting argument for archiving anyway is unsound.** It runs: an agent lacking
`AGENTS.md` also lacks any route to `docs/adr/INDEX.md`, since reading the index is itself
an `AGENTS.md` instruction — so the defence covers a superset of what archiving removes.
It is not a superset: `skills/writing-adrs/SKILL.md` names `INDEX.md` as what an agent
loads by default, so anyone invoking that skill reaches the index without `AGENTS.md`.
That one counterexample is all the refutation needs. `README.md` is not a second — it
describes what the hook regenerates without sending anyone to the index. Record the
refutation, or it gets re-derived and believed.

## Why it is still worth doing

Both candidate archivals were reverted, for reasons specific to each ADR rather than to the
defence class — so the class itself is still untested, and the next session to notice that
`AGENTS.md` restates a decision will reach for it again. Two ADRs already sit close: 011,
whose `## Python` bullet states the package rule but forbids none of its rejected options,
and 018, whose `## Deferred work` section covers every rejected option but whose live
`revisit-when` would leave the index's Revisit column with nothing carrying it.

That second one generalises past this class: **archiving un-publishes a live revisit
trigger**, and the skill's own instruction to read live triggers points at a column
archived ADRs are absent from. It is the reason to hold an ADR back, and the skill does not
say so.

## Until the skill says otherwise

Don't archive on ambient instructions alone. Where it looks right anyway, both gates from
the two reversions have to pass first, and they are the checks — the case studies above are
only where they came from:

- **Does the `AGENTS.md` text forbid every option the ADR rejected**, not just state the
  rule it chose? Prescriptive prose guards nothing; the skill's "covers one covers none"
  rule decides this.
- **Is the `revisit-when` live?** Archiving takes it out of `INDEX.md`'s Revisit column,
  which is where the skill sends readers to find live triggers. A trigger that is unfired,
  or near, is a reason to stay `Accepted`.

## Acceptance

- `skills/writing-adrs/SKILL.md` says whether a defence resting on ambient project
  instructions qualifies, and on what condition — not merely that one might. If it does,
  it gets the treatment `## Defending a decision with a path-scoped rule` already gets:
  what loads it, and which ordinary routes miss.
- It states that archiving removes a decision's `revisit-when` from the index's Revisit
  column, and that a live trigger is a reason to stay `Accepted`.
- The agent-type measurement is recorded as a measurement with its date, not as a standing
  claim about what is loaded — it is a harness behaviour that can change under us.

[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
