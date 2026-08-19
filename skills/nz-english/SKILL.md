---
name: nz-english
description: Use when scanning for or correcting US English spellings in a codebase — comments, docstrings, docs, and string literals, but not API identifiers.
---

# NZ English Conversion

Convert US English spellings to NZ English in human-readable text.

## Scope

**Convert:** comments, docstrings, `.rst`/`.md` docs, string literals, error messages, test function names.

**Do NOT convert:** identifiers of any visibility — parameter, method, class, attribute and local names — external library identifiers, URLs, filenames, and manifest keys and values — a `LICENSE` file, an SPDX identifier, and the `license` field in `plugin.json` or `package.json` all keep the US spelling, because the name is fixed by something outside this repo. When prose describes a US-spelled API (e.g. `normalize=True`), convert the prose but leave the identifier.

A string literal is converted only where its text is read by a person. One matched against something outside the repo is an identifier wearing quotes: a CSS property (`"color: red"`), a CLI flag (`--normalize`), an environment variable, a dict key from an external schema, a regex.

**Whole trees to leave alone:** vendored and third-party directories, `CHANGELOG.md` and past release notes (they record what shipped), quoted external text anywhere, and test fixtures that assert on US spelling — converting one of those breaks the suite the Verify step then runs. Add this skill's own directory: the table and the patterns below are built out of US spellings, so a sweep over its home repo matches them and an over-eager pass corrupts the searches.

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

Every row of the table is covered by one of the commands below. Three rows — `-our`, `-re` and `-ogue` — name a *class* no pattern can express, since nothing distinguishes `color` from `error`, so their commands enumerate the members instead and are complete only for the words listed. **Adding a row, or a word to one of those three, means extending a command in the same change** — the row and its search ship together, or the row is a rule nothing enforces. Meeting a US spelling no command finds is that step falling due, not a miss to fix by hand.

`--hidden` is needed because dot-directories hold prose too, and `-g '!.git'` because on current ripgrep `--hidden` also descends into it. Widen the glob to whatever carries prose in the repo at hand — this default covers docs, code and config, and lockfiles are excluded because they are full of external package names.

**Every command ends in a path.** Without one `rg` reads standard input, which in an agent's shell is an open pipe rather than a terminal, so the command blocks until it is killed instead of searching anything. Keep the trailing `.`, or name the paths.

**In zsh an unquoted expansion stays one word.** That holds for anything you collect in a variable, not just flags: `rg $FLAGS` passes the whole string as one unrecognised flag, and a `FILES="a.md b.py"` list becomes one path that does not exist. Write every command out in full, run it as its own invocation, and pass the paths literally.

**Never turn a non-zero exit into a clean result.** `rg` exits 0 for a match, 1 for no match and **2 for an error**, so `rg … || echo "(clean)"` reports clean for a search that never ran. That, not the word-splitting, is what turns one broken loop into nine clean reports. Read the exit code: treat 2 as a failed search and fix it, never as a tree with nothing to convert.

**Prove the searches can fail before believing them.** Write two scratchpad files — never in the repo, which is usually clean. One holds the US spelling of **every row of the table, with its inflections and a compound**; the other holds the already-correct NZ forms. Run all nine commands against both: each row must be caught, and the second file may return only hits this file already documents as noise — put nothing else in it, or the expected false positives read as failures. A control of one word per command is not enough — it proves the command runs, where what you need is that the *row* is covered, and a missing inflection passes it happily.

```
rg -in --hidden -g '!.git' -g '!*.lock' "\w{3,}iz(e|ing|er|ation|abl)" .
rg -in --hidden -g '!.git' -g '!*.lock' "lyz" .
rg -in --hidden -g '!.git' -g '!*.lock' "(color|behavior|honor|flavor|favor|labor|vapor|rigor|vigor|odor|armor|neighbor|harbor|savor|endeavor|humor|splendor|candor|valor|parlor|clamor|glamor|tumor|rumor|savior|arbor|ardor|fervor|rancor|succor|demeanor)" .
rg -in --hidden -g '!.git' -g '!*.lock' "(center|fiber|theater|liter|somber|specter|caliber|meager|saber|luster|sepulcher)" .
rg -in --hidden -g '!.git' -g '!*.lock' "(catalog|dialog|analog|monolog|prolog|epilog|travelog|homolog|pedagog|demagog|synagog|decalog|ideolog)([^u]|$)" .
rg -in --hidden -g '!.git' -g '!*.lock' "\w{2,}el(ed|ing|er)" .
rg -in --hidden -g '!.git' -g '!*.lock' "(gray|defense|offense|pretense|skeptic|judgment|acknowledgment|aluminum|artifact|aging|fulfill|enroll|sizable)" .
```

**The commands are open at both ends**, because anchoring either hides real hits: the right end hides inflections (`artifacts`, `licenses`, `centers`) and the left end hides compounds and prefixes (`watercolor`, `epicenter`, `subprogram`, `breathalyzer`, `hydrolyze`). Over-reporting is the correct failure direction: Triage discards a false hit in seconds, where a miss survives indefinitely because the search that would have found it reported clean.

The `-og` command is the exception, and shows what to do where the US spelling is a *prefix* of the NZ one: left open it matches the already-correct `catalogue`. Anchoring the right end is the obvious fix and the wrong one — it drops `catalog_id` and `dialogWindow`, and inflections then have to be listed by hand, which is how `cataloged` and `cataloging` went missing for a month behind `ged`/`ging`. It demands a following character that is not `u` instead — and, the search being case-insensitive, not `U`, so `dialogUrl` escapes it too. That is no loss: Triage skips identifiers anyway. `program`/`programme` is the same shape, left open rather than special-cased, so expect `programme` back.

### What over-reporting brings back

The `-our` belongs to the base word, not to every word built from it: **the `u` drops before `-ous`, `-ific`, `-ary`, `-ation` and `-ise`.** So `honorary`, `honorific`, `rigorous`, `vigorous`, `humorous`, `laborious`, `odorous`, `clamorous`, `glamorous`, `invigorate` and `vaporise` are already correct — that is the rule, and those are examples of it rather than the whole list.

Unrelated words also match, and one of them dominates the results in a code repository: **`literal` and `literally`** come back from `liter`, along with `literature` and `literary`. Expect them to outnumber the real hits on that command. Likewise `capsize`, `resize`, `downsize` and `oversize` from `-ize`, `cluster` and `bluster` from `luster`, `arboretum` from `arbor`, `laboratory` from `labor`, `Colorado` and `colorectal` from `color`, `staging` from `aging`, the already-correct `programme` from `program`, and `feeling`/`steeling` under the `-el` pattern.

`Prolog` is a language, and `dialog`/`analog` are common API identifiers (HTML `<dialog>`, ADC `analog` pins) — Scope already exempts those, and they are the terms most likely to be mass-converted wrongly.

### Rows needing judgement

`meter` is searched here rather than with the other `-er` words, because it is the one of them that needs reading:

- **`license`/`practice`** — noun takes `c` (a licence, a practice), verb takes `s` (to license, to practise). The bare forms need reading, and so do the **plurals**: `licenses` is a noun plural (→ `licences`) or a verb, and `practices` likewise. Only `licensed`, `licensing` and `licensee` never do — always `s`, always **already correct**, so leave them. `practiced` and `practicing` are always verbs, so they always become `practised` and `practising`.
- **`program`** — correct as-is in computing, which in a code repository is nearly every hit.
- **`meter`** — a parking or power *meter* is correct; only the unit of length is *metre*. Left open, so expect `parameter`, `diameter` and `perimeter` to bury the real hits in a code repository; they are the price of catching `kilometer`.

```
rg -in --hidden -g '!.git' -g '!*.lock' "(license|practice|meter|program)" .
rg -in --hidden -g '!.git' -g '!*.lock' "(practiced|practicing)" .
```

The first needs a decision per hit. The second is always a conversion.

## Triage

For each hit: **prose or identifier?**

- Names a thing the code refers to — a parameter, attribute, function, class or variable, or the same name as `param=value` → **skip**. A **test function name is prose**, not an identifier anything calls, so convert it.
- Reads as English to a person — a docstring, comment, error message, or a string literal nothing outside the repo matches → **convert**.
- Undecidable from the line alone: search the repo for the bare term (`rg -in 'dialog' .` — not `-w`, which counts `_` as a word character and so misses `show_dialog`, the shape a real definition usually takes). Defined or assigned anywhere, or imported from a dependency → skip it everywhere, since converting prose that names it makes the two disagree.

A term can appear in both contexts in the same file — edit only the prose occurrences.

## Verify

Three checks, all of them, in order:

1. **Re-run every command.** What remains must be a set you have read and rejected. Read nothing into an empty result either way: the documented noise is only there if the repository happens to hold those words, and a small clean tree legitimately silences most of the commands. Emptiness is the control's job, not this one's — if you doubt a command still runs, point it at the fixture rather than the tree.
2. **Read `git diff` word by word.** The risk here is a conversion inside an identifier, which no test catches and which the search will not report a second time.
3. **Run the test suite.** Renamed test functions (e.g. `test_foo_normalisation`) are fine — they're internal. Where the suite does not cover what you edited — a docs-wide pass in a repo whose tests cover one package — say so rather than reporting the suite green, because it verified none of it.
