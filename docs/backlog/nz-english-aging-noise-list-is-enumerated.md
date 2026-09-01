# nz-english: the `aging` pattern reports any unlisted `-aging` word

> Recorded 2026-08-28, found by running the tool over this repository's own docs.
> Never filed as a GitHub issue.

## What

[`table.py`][]'s fixed-word row uses an unanchored alternation:

```python
patterns=(Pattern("(aluminum|artifact|aging)"),)
```

so `aging` matches inside any word containing it. The noise list absorbs the ones someone
has met — `imaging`, `managing`, `messaging`, `packaging`, `staging` — and every other
`-aging` word reports as a hit:

```
$ python3 skills/nz-english/scan.py docs/adr
020-track-deferred-work-in-the-repository.md:6  aging  triaging
```

`triaging` is correct as it stands: it comes from *triage*, and `ageing` is not the
substitution to make. Also unlisted today: `engaging`, `damaging`, `encouraging`,
`discouraging`, `disparaging`, `salvaging`, `leveraging`.

## Why this is not just a missing word

Adding `triaging` fixes one report. The shape of the row is what produces the next one:
the noise list is enumerated where the pattern is open-ended, so the correct set is
unbounded and grows by whoever happens to trip over a word. The `-our` row has the same
shape and a documented reason for it — its drop list is genuinely closed and irregular —
but `-aging` is not irregular. Every English word ending `-aging` other than `aging`
itself is a false positive, which is a rule rather than a list.

The over-report is the safe direction and costs a reader a second, so this is a paper cut
rather than a defect that hides anything.

## Acceptance

- A word ending in `-aging` that is not `aging` reports as noise without being
  enumerated.
- `aging` itself, and `ageing` written as a US spelling in a compound, still report.
- The bundled controls cover at least one word the old noise list did not name, so the
  test would have failed before the change.

[`table.py`]: ../../skills/nz-english/table.py
