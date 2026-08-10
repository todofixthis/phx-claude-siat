---
name: nz-english
description: Use when scanning for or correcting US English spellings in a codebase — comments, docstrings, docs, and string literals, but not API identifiers.
---

# NZ English Conversion

Convert US English spellings to NZ English in human-readable text.

## Scope

**Convert:** comments, docstrings, `.rst`/`.md` docs, string literals, error messages, test function names.

**Do NOT convert:** public API identifiers (parameter names, method names, class names), external library identifiers, URLs, filenames, and manifest keys and values — a `LICENSE` file, an SPDX identifier, and the `license` field in `plugin.json` or `package.json` all keep the US spelling, because the name is fixed by something outside this repo. When prose describes a US-spelled API (e.g. `normalize=True`), convert the prose but leave the identifier.

## Substitutions

| US | NZ |
|----|----|
| `-ize` / `-ization` | `-ise` / `-isation` (normalise, initialise, serialise, optimise, organisation) |
| `-yze` | `-yse` (analyse, analyser, paralyse) |
| `-or` endings | `-our` (colour, behaviour, honour, flavour, favourite) |
| `-er` endings (root words) | `-re` (centre, fibre, theatre) — not all `-er`; "filter" stays |
| `-og` endings | `-ogue` (catalogue, dialogue, analogue) |
| `-eled` / `-eling` | `-elled` / `-elling` (travelled, labelled, modelling) |
| `gray` | `grey` |
| `defense` / `offense` / `pretense` | `defence` / `offence` / `pretence` |
| `skeptic` | `sceptic` |
| `judgment` / `acknowledgment` | `judgement` / `acknowledgement` |
| `license` (noun) | `licence` |
| `practice` (verb) | `practise` |
| `program` | `programme` — not in computing contexts ("program code") |
| `aluminum` / `artifact` / `aging` | `aluminium` / `artefact` / `ageing` |
| `fulfillment` / `enrollment` | `fulfilment` / `enrolment` |

## Search

Every row of the table is covered by one of the commands below. **Adding a row to the table means extending a command in the same change** — the row and its search ship together, or the row is a rule nothing enforces.

`--hidden` is needed because dot-directories hold prose too, and `-g '!.git'` because on current ripgrep `--hidden` also descends into it. Widen the glob to whatever carries prose in the repo at hand — this default covers docs, code and config, and lockfiles are excluded because they are full of external package names.

Write the flags out in every command rather than collecting them in a shell variable: zsh does not word-split an unquoted expansion, so `rg $FLAGS` there passes the whole string as one unrecognised flag.

```
rg -in --hidden -g '!.git' -g '!*.lock' "\w{3,}iz(e|es|ed|ing|er|ation)"
rg -in --hidden -g '!.git' -g '!*.lock' "\b(analyz|paralyz|catalyz)"
rg -in --hidden -g '!.git' -g '!*.lock' "\b(color|behavior|honor|flavor|favor|labor|vapor|rigor|vigor|odor|armor|neighbor|harbor|savor|endeavor|humor|splendor|candor|valor|parlor|clamor|glamor)"
rg -in --hidden -g '!.git' -g '!*.lock' "\b(center|fiber|theater|liter|somber|specter|caliber)"
rg -in --hidden -g '!.git' -g '!*.lock' "\b(catalog|dialog|analog|monolog|prolog|epilog|travelog)(s|ged|ging)?\b"
rg -in --hidden -g '!.git' -g '!*.lock' "\w{3,}el(ed|ing|er)"
rg -in --hidden -g '!.git' -g '!*.lock' "\b(gray|defense|offense|pretense|skeptic|judgment|acknowledgment|aluminum|artifact|aging|fulfillment|enrollment)"
```

**Most commands stay open on the right**, because anchoring that end hides every inflected form — `artifacts`, `licenses`, `centers` — and the plural is the commoner spelling in code prose. Over-reporting is the correct failure direction: Triage discards a false hit in seconds, where a miss survives indefinitely because the search that would have found it reported clean.

The `-og` command is the exception, and shows when to anchor: the US spelling is a *prefix* of the NZ one, so leaving it open matches the already-correct `catalogue`. Anchor only where that is true — `program`/`programme` below is the other case — and list the inflections explicitly instead.

### What over-reporting brings back

The `-our` belongs to the base word, not to every word built from it: **the `u` drops before `-ous`, `-ific`, `-ary`, `-ation` and `-ise`.** So `honorary`, `honorific`, `rigorous`, `vigorous`, `humorous`, `laborious`, `odorous`, `clamorous`, `glamorous`, `invigorate` and `vaporise` are already correct — that is the rule, and those are examples of it rather than the whole list.

Unrelated words also match, and one of them dominates the results in a code repository: **`literal` and `literally`** come back from `liter`, along with `literature` and `literary`. Expect them to outnumber the real hits on that command. Likewise `laboratory` from `labor`, `Colorado` and `colorectal` from `color`, and `feeling`/`steeling` under the `-el` pattern.

`Prolog` is a language, and `dialog`/`analog` are common API identifiers (HTML `<dialog>`, ADC `analog` pins) — Scope already exempts those, and they are the terms most likely to be mass-converted wrongly.

### Rows needing judgement

`meter` is searched here rather than with the other `-er` words, because it is the one of them that needs reading:

- **`license`/`practice`** — noun takes `c` (a licence, a practice), verb takes `s` (to license, to practise). Only the bare forms need reading. The inflected ones never do: `licensed`, `licensing` and `licensee` are always `s` and are **already correct**, so do not convert them; `practiced` and `practicing` are always verbs, so they always become `practised` and `practising`.
- **`program`** — correct as-is in computing, which in a code repository is nearly every hit.
- **`meter`** — a parking or power *meter* is correct; only the unit of length is *metre*.

```
rg -in --hidden -g '!.git' -g '!*.lock' "\b(license|practice|meter|program(s|med|ming)?)\b"
rg -in --hidden -g '!.git' -g '!*.lock' "\b(practiced|practicing)\b"
```

The first needs a decision per hit. The second is always a conversion.

## Triage

For each hit: **prose or API identifier?**

- In a function/class signature, or as `param=value` → **skip**
- Grep the codebase for the term — if it's a callable parameter or attribute → **skip**
- In a docstring, comment, or string literal → **convert**

A term can appear in both contexts in the same file — edit only the prose occurrences.

## Verify

Run the test suite after edits. Renamed test functions (e.g. `test_foo_normalisation`) are fine — they're internal.
