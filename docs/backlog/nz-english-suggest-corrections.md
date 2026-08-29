# nz-english: suggest the NZ spelling for each hit

> Recorded 2026-08-27, raised in review of [#37][] and deferred from 5.0.0.
> Was GitHub issue #38.

## What

Have [`scan.py`][] print the suggested NZ spelling beside each hit, so the agent reads a
correction rather than deriving one. The work lands mostly in [`table.py`][], which owns the
rows, the `nz_forms` maps and the `NOISE` list.

## Feasibility

Workable, with two complications that shape the design and one that bounds it.

**It is mechanical for most patterns.** Twelve of the seventeen rows carry no judgement
pattern at all, and each class has a rule the table already implies: `-or`→`-our`,
`-ize`→`-ise`, `-yze`→`-yse`, `-el`→`-ell`, `-og`→`-ogue`, plus direct maps for the
fixed-word rows. Only two rows carry an explicit `nz_forms` map today, because only
`--verify` needed one; the rest would have to be written down or derived.

**Complication 1 — a correction is per token, not per row.** `colorize` matches both the
`-or` and `-ize` rows and needs both applied to reach `colourise`. Suggesting per row
would emit `colourize` from one and `colorise` from the other, each wrong on its own. So
suggestions have to be computed once per token across every row that claimed it, which is
a different pass from the per-row report the tool prints now. `verify_matches()` already
collects every row whose pattern claims a given name, which is the shape this needs.

**Complication 2 — inflections are not suffix swaps.** `centering` becomes `centring`, not
`centreing`; the `e` drops before `-ing`. A naive `er`→`re` rewrite produces a misspelling
and hands it to the agent looking authoritative. Every class needs its inflection cases
enumerated or the feature is worse than nothing.

**Complication 3 — some hits are already correct, and rewriting them corrupts them.** The
`-og` guard deliberately over-reports a SCREAMING_CASE `DIALOGUE`, which [ADR 017][]
records as the one place the port is not faithful. A substring rewrite over that hit
produces `DIALOGUEUE`. So suggestions must recognise an already-correct hit, which `NOISE`
does for the lowercase cases and the `-og` guard deliberately does not do for this one.
Case preservation is the smaller sibling of this — `dialogUrl`→`dialogueUrl`.

**The bound — suppression is per pattern, not per row.** Judgement is a property of the
pattern rather than the row, and three rows are mixed: `acknowledgment` sits beside
`judgment`, the `-re` word list beside `meter`, and `practiced`/`practicing` beside
`practice`. Suppressing whole rows would drop correct suggestions for `centre`,
`acknowledgement` and `practised` — most of the `-re` class among them. Suppress the five
judgement *patterns*: `license`, `program`, `practice`, `meter`, `judgment`. They are
marked read-don't-apply because the answer depends on the occurrence, and printing a
suggestion beside one teaches the opposite of what the mark is for — silently: a court's
`judgment` rewritten because the tool offered `judgement` and nothing objected.

`judgement_mark()` already makes exactly this per-pattern distinction for the report, via
`span_label`.

## Why it is still worth doing

It moves a derivation the agent currently performs per hit into code that performs it
once, which is the rule ADR 017 records. It does not breach the report-only invariant — a
suggestion is not an edit — though it does shift the risk, which is what the
judgement-pattern exclusion above is there to hold.

## Acceptance

- One suggestion per token, composed across every pattern that matched it.
- Inflections covered by tests per class, `centering`→`centring` among them.
- Case preserved for camel case, and an already-correct `DIALOGUE` gets no suggestion
  rather than `DIALOGUEUE`.
- The five judgement patterns print no suggestion and a test asserts it, while the
  non-judgement patterns sharing their rows — `acknowledgment`, the `-re` words,
  `practiced`/`practicing` — still do.

[#37]: https://github.com/todofixthis/phx-claude-siat/pull/37
[ADR 017]: ../adr/017-move-a-skills-deterministic-steps-into-shipped-code.md
[`scan.py`]: ../../skills/nz-english/scan.py
[`table.py`]: ../../skills/nz-english/table.py
