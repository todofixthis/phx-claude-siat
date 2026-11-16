---
status: Accepted
date: 2026-09-08
scope: [skills/writing-adrs/adr.py, skills/writing-adrs/SKILL.md]
summary: adr.py check fails on a gap in the numbering the same way it fails on a collision, and renumber's target number is the tool's own choice by default, matching new.
revisit-when: adr.py gains a way to see another branch's own unmerged claim before choosing a number.
---

# 033: Report a gap in ADR numbering, and let renumber close it

## Context

[ADR 029][] made `binding()` report a shared number. Neither `binding()` nor `inspect()`,
the engine behind `check`, has ever asked whether every number up to the highest has a
file. The tool's whole model of the corpus is "no two files share a number". It has never
checked that "every number up to the highest is claimed".

The gap is real. A pull request that routes `docs/backlog/` items by the paths they bind
added an ADR that would normally have taken the next number, 031. But a second pull
request, open at the same time, had already scaffolded its own ADR under 031. The first
pull request's ADR was renumbered to 032 and skipped 031. That was the right call in that case.
The second pull request's claim was real, but no check running against the first pull
request's branch could see it. And nothing in `adr.py` noticed the hole this left in that
branch's `docs/adr/`. A human reviewer found it by reading the diff.

A hole merged into `main` is a worse form of the problem `collision` already catches.
Instead of two decisions sharing one identity, one number belongs to no decision, for
good. Someone who later wrote an ADR by hand at that number would not notice they were
filling a hole rather than starting fresh.

A second, related gap: `renumber OLD NEW` has always taken `NEW` from the caller. `new`
never worked this way. `next_number()` has always picked a new ADR's number itself. Every
renumber in this repository's history has had a human or an agent work out by hand "the
next number that looks safe" from whatever `docs/adr/` holds locally. `new_adr()` was
built to make that manual step unnecessary, but the tool's other number-choosing command
never got the same treatment.

## Options

### Option 1: Do nothing

Leave `check` silent on a hole in the numbering, and leave `renumber` asking the caller
for both ends of the move.

**Pros:** No change, no test to update, and no new failure mode to design against.
**Cons:** A gap merges into `main` as silently as this one nearly did. Only a reviewer
who reads the ADR diff closely enough to notice a missing number catches it. Every
renumber still asks a human or an agent to work out a target by hand, the exact manual
step that `new` already leaves to the tool.
**Risks:** As more branches that carry ADRs are open at once, this happens again. Each
time, someone finds it by reading, as here, and no tool catches it.

### Option 2: A `gap` finding in `inspect()`, and a self-chosen, gap-refusing default for `renumber` (Accepted)

`inspect()` reports a `gap` finding for any number strictly between the lowest and the
highest on disk that no file claims. A `gap` blocks exactly as a `collision` does. The
`NEW` argument of `renumber` becomes optional. If the caller omits it, the tool picks
`next_number()`: one past the current highest, still counting the file at `OLD`. Whether
`NEW` is given or not, the tool refuses the move before writing anything if the move
would leave a hole. **Every** move that skips ahead of a number leaves one, because
nothing else shifts to fill the place the file leaves. That refusal is the point, not a
side effect: it blocks the move described in Context. A branch can no longer renumber its
own ADR, by any route, to avoid a sibling's claim it has only heard about.

The workflow that replaces it: both branches keep the number they each allocated. Nothing
shows the clash until one branch rebases onto the other's merged ADR. Then `inspect()`
reports a real `collision`: two files with one number, now in the same tree.
`renumber(OLD)` resolves it. It tolerates an existing collision that names `OLD`, because
resolving that collision is what the call is for, and it still refuses on any other
existing fault. It moves one of the two files to `next_number()`. The result has no gap,
because the whole tree is visible at once for the first time.

**Pros:** `check` now catches the exact kind of hole this repository nearly shipped. The
caller cannot make it open a new one, whether by omitting `NEW` or by giving it.
Whichever branch merges second resolves the clash with one command, against the real,
complete corpus, instead of a guess against half of it.
**Cons:** If `main` goes a long time between merges of branches that carry ADRs, more
same-numbered collisions build up before anyone resolves one. Each is paid for at merge
time. The old approach spread that cost out, as each author guessed ahead. This guard can
land in `main` only after any sequence still using the old approach has resolved, never
while one is in flight.
**Risks:** The tool still cannot see another branch's unmerged claim, so two branches can
still each compute the same `next_number()`. `collision` (ADR 029) catches that, and this
decision does not change it. This decision removes the option to guess around that
blindness. It does not remove the blindness.

### Option 3: Enforce the rule in `check` alone

Add the `gap` finding to the report from `check`, but leave `renumber`, `new`,
`supersede`, and `discharge` working as they do today. They stay free to open or leave a
gap, since nothing inside them refuses one.

**Pros:** `renumber` keeps working as it always has, including the move that dodges a
sibling's claim ahead of time. A pull request fails only if its gap survives as far as
whatever `check` gates.
**Cons:** A branch that holds a gap open for a sibling's ADR, correctly and on purpose,
fails its own CI for as long as the gap stands. Its author knows the failure is a false
alarm every time, until the sibling merges. The author learns to expect it and to skip
past it. That is warning fatigue, the same failure as any alert people ignore because it
is usually a false alarm.
**Risks:** Once a red check is normal for a whole class of correct branches, a truly
broken one, with a gap nobody meant to leave, looks like more of the same expected noise.
It no longer carries the signal `check` exists to give.

### Option 4: Make `renumber` only ever choose its own target

Remove the explicit `NEW` from the CLI, so a caller can never supply one.

**Pros:** A slightly smaller CLI, and no explicit-target path to keep correct.
**Cons:** It removes a valid case that Option 2 already keeps safe. A caller may want to
move a specific ADR to a specific number for a reason unrelated to a collision, such as
placing related decisions next to each other. This option leaves no other way to do that.
**Risks:** None that Option 2 does not already cover, since Option 2's gap check limits
any harm the explicit path could do. Removing the path trades a working feature that
already has a guard for stricter ownership in appearance only.

### Option 5: Add a `--force` flag that disables every check

Give every command a flag that skips both `refuse_on_findings` and the gap check at move
time, for anyone who judges a refusal wrong in the moment.

**Pros:** It never blocks on a refusal that its author believes is a false alarm. This
pull request's own rebase was correctly refused while it waited for a sibling's gap to
close. With the flag, it could have gone through at once instead of waiting for that
sibling to merge.
**Cons:** This repository's own precedent argues against it. [ADR 017][] replaced typed
prose commands with shipped code to make a class of mistakes impossible rather than only
documented: a mistyped command, a wrong exit code, a quoting error. A flag that disables
every check is exactly the "trust the prose" bet that ADR 017 moved away from. It also
risks a worse failure than the one it avoids. Forcing a renumber through can leave a
second gap or a new collision, with no check left running to catch it.
**Risks:** A bypass built for "the repo is genuinely broken" is also there for "I am in a
hurry", and the flag alone cannot tell the tool which case it is. That is the exact risk
the refusal in `check` exists to remove.

## Decision

Option 2. Option 1 is the status quo, and Context shows it has already failed once in
practice. Option 3 gives up the one property this decision is for, a rule with no
guessing in it, to keep `renumber` unchanged. Yet the Cons of Option 4 show that
`renumber` has more than one working shape. Option 4 buys nothing that the gap check in
Option 2 does not already guarantee: the tool refuses an explicit `NEW` that would open a
hole either way. So its extra restriction costs something and gains nothing. Option 5
answers a real frustration, a refusal that is correct but inconvenient, with a bypass broader
than the frustration. It cannot tell a caller who has confirmed the repo is broken
from one who has run out of patience, so it removes the guard for both.

Option 2's Cons are accepted on purpose. Nobody can guarantee the order in which two
branches that carry ADRs merge, or that either merges at all. So the corpus must stay
consistent in any order, and only a rule with no guessing in it can promise that. Paying
for a collision in full at merge time, instead of spreading a guess across two branches,
is extra admin. It is accepted for that promise, and to avoid the warning fatigue of
Option 3.

This repository has two open pull requests that predate this decision. One carries a
031 skipped on purpose, and the other is about to claim 031. Both are left as they are.
Resolving them now would mean reopening one or both to meet a rule neither was written
against. This guard lands after they resolve, not before, and does not rewrite either.

## Consequences

- The `adr` job in `pr.yml` (`check`) now fails on any gap in the numbering of the branch
  it runs against. A branch built before this decision merges is not retroactively
  exempt. A branch built after it that opens a gap by hand, without `renumber`, fails the
  same way a branch with a `collision` already does.
- `renumber OLD`, with `NEW` omitted, is the normal form from now on. The documented
  invocation in `SKILL.md` and its section on the renumbering workflow both name the
  omitted form first. They keep the explicit form only for moving to a specific number
  that leaves no gap, for a reason unrelated to a collision.
- `renumber()` tolerates one existing finding that it would otherwise refuse on: a
  `collision` that names `OLD`, because resolving that collision is what the call is for.
  Any other existing fault still blocks it, as before.
- The return type of `renumber()` changed from the list of citations alone to
  `(number used, citations)`. Its two callers, the CLI and the test suite, need it to
  report which number an omitted target resolved to. No caller outside this repository is
  known to exist.
- This decision does not, and cannot, stop two branches from choosing the same
  `next_number()`. It only stops a gap from surviving unnoticed after one is chosen.
  `revisit-when` names the one thing that would change that: the tool seeing another
  branch's claim before it chooses.
- `renumber()` refuses a number that three or more files claim. Resolving one pair would
  leave a real collision for the index regeneration to fail on, so the caller first moves
  one of the three by hand. It also refuses a `NEW` equal to `OLD`, since that would move
  a file onto itself.
- **Known limitation, not fixed here:** `renumber OLD` cannot tell the caller's own file
  from the sibling that shares `OLD`. It always moves whichever file sorts first by
  filename. Before trusting the result, check that it moved the file you meant. The tool
  has no way to ask.

[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 029]: 029-report-number-integrity-faults-from-the-reverse-lookup-too.md
