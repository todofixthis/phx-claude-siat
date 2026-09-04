# ADR numbers are padded to a fixed three digits, which stops making sense at 1000

> Recorded 2026-09-03, from the maintainer's review of the writing-adrs system branch
> (pull request #53). Never filed as a GitHub issue. Not urgent: this repository leads
> every todofixthis repository in ADR count and is nowhere near the limit.

## What

`NUMBER_WIDTH = 3` in [`adr.py`][] fixes the width `new` writes into a filename and
heading, and `renumber` writes into the filename, the heading, and every `ADR NNN`
citation and `NNN-<slug>` link target in every peer ADR — while the peer fields it updates
get the bare number. The thousandth ADR gets `1000-<slug>.md`, which the tool numbers
correctly — `RE_FILE_NUMBER` reads the integer — but which sorts between `100-…` and
`101-…` wherever
the corpus is listed lexically: `inspect()`, which orders `docs/adr/INDEX.md`, and
`binding()`, which orders the `for` lookup and the pre-commit advisory. Derive the width
from the corpus, or sort numerically and accept mixed widths, and say which in
[`SKILL.md`][]'s Format section, which currently promises "zero-padded".

## Why it is still worth doing

A corpus that crosses the limit finds out from a misordered index and a filename the
skill's own Format rule does not describe, with nothing reporting either.

The sibling item `adr-lookup-performs-none-of-the-number-checks.md` is about the same
`binding()`-versus-`inspect()` gap; a fix here that touches only `inspect()` leaves the
lookup misordered.

## Acceptance

- `inspect()` and `binding()` both order by number, so the index and the `for` lookup list
  the thousandth ADR last.
- `renumber` writes citations, link targets and peer fields at one agreed width.
- The search forms that [`SKILL.md`][]'s Renumbering section tells the agent to use match
  what `renumber` writes.
- [`SKILL.md`][]'s Format section states the padding rule the tool applies.
- A fixture in [`tests/test_adr.py`][] with a four-digit number proves the ordering.

[`adr.py`]: ../../skills/writing-adrs/adr.py
[`SKILL.md`]: ../../skills/writing-adrs/SKILL.md
[`tests/test_adr.py`]: ../../skills/writing-adrs/tests/test_adr.py
