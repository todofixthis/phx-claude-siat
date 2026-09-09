---
status: Accepted
date: 2026-09-08
scope: [skills/writing-adrs/adr.py]
summary: adr.py check fails on a gap in the numbering the same way it fails on a collision, and renumber's target number is the tool's own choice by default, matching new.
revisit-when: adr.py gains a way to see another branch's own unmerged claim before choosing a number.
---

# 033: Report a gap in ADR numbering, and let renumber close it

## Context

[ADR 029][] made `binding()` report a shared number, but neither it nor `inspect()` —
`check`'s own engine — has ever asked whether every number up to the highest actually has
a file. The tool's whole model of the corpus is "no two files share a number"; "every
number up to the highest is claimed" has never been checked at all.

That gap is not hypothetical. A pull request routing `docs/backlog/` items by the paths
they bind added an ADR that would ordinarily have taken the next number, 031 — except a
second, concurrently open pull request had already scaffolded its own ADR under that same
number. Renumbering the first one to 032 instead, skipping 031 outright, was the right
call in that instance: the second PR's claim was real, just invisible to any check running
against the first PR's own branch. But nothing in `adr.py` noticed the hole this left, on
that branch, in that branch's own `docs/adr/`, right up to the moment a human reviewer
spotted it by reading the diff.

A merged `main` carrying such a hole is a worse version of the same problem `collision`
already answers: not two decisions sharing an identity, but a number that answers to none,
forever after — nothing hand-authoring an ADR at that number later would even notice it
was filling one in rather than starting fresh.

The second, related gap: `renumber OLD NEW` has always taken `NEW` from the caller. `new`
has never worked this way — `next_number()` has always picked a fresh ADR's number
itself. Every renumber in this repository's own history has been a human or an agent
computing "the next number that looks safe" by hand from whatever `docs/adr/` holds
locally, which is exactly the manual step `new_adr()` was already built to make
unnecessary, applied inconsistently to the tool's other number-choosing command.

## Options

### Option 1: Do nothing

Leave `check` silent on a numbering hole, and `renumber` asking the caller for both ends
of the move.

**Pros:** No change, no test to update, no new failure mode to design against.
**Cons:** A gap merges into `main` exactly as silently as this one nearly did, caught only
by a reviewer who happens to read the ADR diff closely enough to notice a number missing.
Every renumber still asks a human or an agent to compute a target by hand, the precise
manual step `new` already treats as beneath the tool.
**Risks:** As the number of concurrently open ADR-bearing branches grows, this recurs, and
each recurrence is found the same way this one was — by inspection, not by tooling.

### Option 2: A `gap` finding in `inspect()`, and a self-chosen, gap-refusing default for `renumber` (Accepted)

`inspect()` reports a `gap` finding for any number strictly between the lowest and highest
on disk that no file claims, exactly as blocking as `collision`. `renumber`'s `NEW`
argument becomes optional: omitted, the tool picks `next_number()` — one past the current
highest, `OLD`'s own file still counted. Given explicitly or not, the move is refused
before any write if it would leave a hole behind — which **every** skip-ahead-of-a-number
move does, since nothing else shifts to close the gap the file leaves behind it. This
closes the move this ADR's own Context describes, not as a side effect but as the point:
a branch may no longer renumber its own ADR to dodge a sibling's claim it has only heard
about, ever, by any path.

The replacement workflow: both branches keep the number they each allocated. Nothing
surfaces the clash until one rebases onto the other's already-merged ADR, at which point
`inspect()` reports a real `collision` — two files, one number, both now in the same tree.
`renumber(OLD)` is what resolves it: it tolerates a pre-existing collision naming `OLD`
itself — resolving exactly that collision is what the call is for — while still refusing
on any other existing fault, and moves one of the two files to `next_number()`, gap-free
because the whole tree is visible together for the first time.

**Pros:** `check` now catches the exact shape of hole this repository nearly shipped, and
cannot be asked, by omission or an explicit number, to open a new one. Whichever branch
merges second resolves the clash in one command, against the real, complete corpus,
instead of a guess made against half of it.
**Cons:** A `main` that goes long between merges of ADR-bearing branches accumulates more
same-numbered collisions before anyone resolves one — each now paid for at merge time,
where the old approach spread the cost out as each author guessed ahead. This guard can
only land in `main` once a sequence already using the old approach has resolved, never
concurrently with one still in flight.
**Risks:** The tool still cannot see another branch's own unmerged claim, so two branches
still independently compute the same `next_number()` — `collision` (ADR 029) is what
catches that, unchanged by this decision. What this decision removes is the option to
guess around that blindness; it does not remove the blindness itself.

### Option 3: Enforce the rule in `check` alone

Add the `gap` finding to `check`'s own report, but leave `renumber`, `new`, `supersede` and
`discharge` exactly as they work today — free to open or leave a gap, since nothing internal
refuses one.

**Pros:** `renumber` keeps working exactly as it always has, the proactive dodge included;
only a PR whose gap survives all the way to whatever `check` gates fails anything.
**Cons:** A branch correctly, deliberately holding a gap open for a sibling's ADR now fails
its own CI for as long as that gap stands — a check its own author knows to be a false
alarm, every time, until the sibling merges. That is a check its author learns to expect and
read past: warning fatigue, the same failure mode as any alert routinely ignored because it
is routinely a false alarm.
**Risks:** Once a red check is normal for a whole class of correctly-behaving branches, a
genuinely broken one — a gap nobody meant to leave — reads as one more instance of the same
expected noise, rather than the signal `check` exists to carry.

### Option 4: Make `renumber` only ever choose its own target

Drop the explicit `NEW` from the CLI outright, so a caller can never supply one.

**Pros:** Marginally simpler surface; no explicit-target path to keep correct.
**Cons:** Removes a legitimate case Option 2 already leaves safe: moving a specific ADR to
a specific number for a reason unrelated to a collision — grouping related decisions
adjacently, say — with no other way left to do it.
**Risks:** None Option 2 does not already cover, since its gap check backstops whatever
harm the explicit path could do. Removing it trades a working, already-guarded feature for
the appearance of stricter ownership, not the substance of it.

## Decision

Option 2. Option 1 is the status quo this ADR's own Context shows failing in practice, once
already. Option 3 trades away the one property this decision is actually for — a rule with
no guessing in it — for keeping `renumber` unchanged, which Option 4's Cons shows was never
`renumber`'s only working shape to begin with. Option 4's cost buys nothing Option 2's gap
check does not already guarantee — an explicit `NEW` that would open a hole is refused
either way — so its extra restriction has a cost with no matching benefit.

The Cons Option 2 accepts are deliberate, not overlooked. Merge order between two
ADR-bearing branches can never be guaranteed, and the same is true of whether either merges
at all — so the corpus has to stay self-consistent regardless of order, which only a rule
with no guessing in it can promise. The admin overhead of paying for a collision in full at
merge time, rather than spreading a guess across two branches, is accepted for that
promise, and for avoiding Option 3's warning fatigue.

This repository's own two open pull requests — one carrying a deliberately-skipped 031,
the other about to claim it — predate this decision and are left exactly as they are:
resolving that concurrently would be reopening one or both to satisfy a rule neither was
written against. This guard lands once they resolve, not before, and not by rewriting
either.

## Consequences

- `pr.yml`'s `adr` job (`check`) now fails on any numbering gap on the branch it runs
  against. A branch built before this decision merges is not exempt retroactively; one
  built after it that opens a gap by hand, without going through `renumber`, will be
  caught the same way a `collision` already is.
- `renumber OLD` (`NEW` omitted) is the ordinary form from here on; `SKILL.md`'s
  documented invocation and its renumbering-workflow section both name the omitted form
  first, keeping the explicit one only for landing on a specific, already-gap-free number
  for a reason unrelated to a collision.
- `renumber()` tolerates one pre-existing finding it would otherwise refuse on: a
  `collision` naming `OLD` itself, since resolving exactly that is what the call is for.
  Any other existing fault still blocks it, unchanged.
- `renumber()`'s return type changed, from the citation list alone to `(number used,
  citations)`, so its two callers — the CLI and the test suite — could report which number
  an omitted target resolved to. No caller outside this repository is known to exist.
- Does not and cannot make two branches choosing the same `next_number()` unreachable —
  only a gap surviving unnoticed once one is chosen. `revisit-when` names the one thing
  that would change that: the tool seeing another branch's own claim before choosing.
- `renumber()` refuses a number claimed by three or more files rather than resolving one
  pair and leaving a real collision behind for the index regeneration to fail on; the
  caller moves one of the three by hand first. It also refuses `NEW` equal to `OLD`, since
  that would move a file onto itself.
- **Known limitation, not fixed here:** `renumber OLD` cannot tell the caller's own file
  from the sibling sharing `OLD` — it always moves whichever sorts first by filename. Check
  that this is the file you meant before trusting the result; the tool has no way to ask.

[ADR 029]: 029-report-number-integrity-faults-from-the-reverse-lookup-too.md
