---
name: nz-english
description: Use when scanning for or correcting US English spellings in a codebase — comments, docstrings, docs, string literals, and the identifiers the repo itself defines, but not names fixed outside it.
---

# NZ English Conversion

Convert US English spellings to NZ English in human-readable text.

## Scope

**Convert:** comments, docstrings, `.rst`/`.md` docs, string literals, error messages, and the identifiers this repo defines — parameter, method, class, attribute, local and file names alike.

**Do NOT convert:** names fixed by something outside the repo — an external library's identifiers, URLs, and manifest keys and values. A `LICENSE` file, an SPDX identifier, and the `license` field in `plugin.json` or `package.json` all keep the US spelling for that reason. When prose describes a US-spelled external API (e.g. `normalize=True`), convert the prose but leave the identifier.

Read the project's agent instructions first — `AGENTS.md` and `CLAUDE.md` at the root, plus any nested one covering the subtree you are sweeping. A stated US English convention wins over this skill for whatever it covers, whole tree or identifiers only, and a nested file governs its own subtree. Absent such a statement the repo's own names are in scope: a US-spelled tree is not a statement, that being what this skill is invoked to change.

**Converting an identifier is a rename, not a spelling fix.** Every reference moves with it in the same change: call sites, imports, the string literals that name it, the docs that quote it, and for a filename the paths in manifests, workflow globs, `.gitignore` and symlink targets, moved with `git mv`. The references that kill a rename are the ones no import graph shows — a `getattr(obj, "color")`, a `**kwargs` key, a name built into a template or a query string.

**A third kind of name is defined here and still not yours to rename**, because something outside holds a copy: a serialised field name or database column that stored data already uses, a CLI flag or environment variable a user's scripts pass, a public API identifier, a filename named by a branch-protection rule or a published URL. Leave these, and say which ones you left. Converting one is a migration that moves the data or the callers with it, and belongs in its own change announced where the project records breaking changes. **The half of such a rename living outside the repo cannot be verified from inside it**, so a clean grep here proves nothing about it.

A string literal is converted where a person reads its text, and also where it names an identifier this repo is renaming — the two have to move together. One matched against something outside the repo is an identifier wearing quotes: a CSS property (`"color: red"`), a CLI flag (`--normalize`), an environment variable, a dict key from an external schema, a regex.

**Whole trees to leave alone:** vendored and third-party directories; quoted external text anywhere; test fixtures that assert on US spelling, since converting one breaks the suite Verify then runs; and `CHANGELOG.md` and past release notes, which record text users already received, so respelling one falsifies it. An ADR or design doc records a decision rather than a released artefact, and stays in scope. Add this skill's own directory: the table and patterns below are built out of US spellings, so a sweep over its home repo matches them and an over-eager pass corrupts the searches.

## Substitutions

| US | NZ |
|----|----|
| `-ize` / `-ization` | `-ise` / `-isation` (normalise, initialise, serialise, optimise, organisation) |
| `-yze` | `-yse` (analyse, analyser, paralyse) |
| `-or` endings | `-our` (colour, behaviour, honour, flavour, favourite) |
| `-er` endings (root words) | `-re` (centre, fibre, theatre) — not all `-er`; "filter" stays |
| `-og` endings | `-ogue` (catalogue, dialogue, analogue) |
| `-eled` / `-eling` / `-eler` | `-elled` / `-elling` / `-eller` (travelled, labelled, modelling, traveller) |
| `gray` | `grey` |
| `defense` / `offense` / `pretense` | `defence` / `offence` / `pretence` |
| `skeptic` | `sceptic` |
| `judgment` / `acknowledgment` | `judgement` / `acknowledgement` — but a court's `judgment` keeps this form in NZ legal usage |
| `license` (noun) | `licence` |
| `practice` (verb) | `practise` |
| `program` | `programme` — not in computing contexts ("program code") |
| `aluminum` / `artifact` / `aging` | `aluminium` / `artefact` / `ageing` |
| `fulfill` / `enroll` | `fulfil` / `enrol` — the inflections keep the double `l`, so `fulfilled`, `fulfilling`, `enrolled` and `enrolling` are already correct |
| `fulfillment` / `enrollment` | `fulfilment` / `enrolment` |
| `sizable` | `sizeable` |

## Search

Every row of the table is covered by one of the commands below. Three rows — `-our`, `-re` and `-ogue` — name a *class* no pattern can express, since nothing distinguishes `color` from `error`, so their commands enumerate the members instead and are complete only for the words listed. **Adding a row, or a word to one of those three, means extending a command in the same change** — the row and its search ship together, or the row is a rule nothing enforces. The converse binds too: a word a command searches needs a row saying what it becomes, or the hit arrives with nothing to apply to it. Meeting a US spelling no command finds is that step falling due, not a miss to fix by hand.

`--hidden` is needed because dot-directories hold prose too, and `-g '!.git'` because on current ripgrep `--hidden` also descends into it. Widen the glob to whatever carries prose in the repo at hand — this default covers docs, code and config, and lockfiles are excluded because they are full of external package names.

**Every command ends in a path.** Without one `rg` reads standard input, which in an agent's shell is an open pipe rather than a terminal, so the command blocks until it is killed instead of searching anything. Keep the trailing `.`, or name the paths.

**In zsh an unquoted expansion stays one word**, whatever you collect in it: `rg $FLAGS` passes the whole string as one unrecognised flag, and a `FILES="a.md b.py"` list becomes one path that does not exist. Write every command out in full, run it as its own invocation, and pass the paths literally.

**Never turn a non-zero exit into a clean result.** `rg` exits 0 for a match, 1 for no match and **2 for an error**, so `rg … || echo "(clean)"` reports clean for a search that never ran. That, not the word-splitting, is what turns one broken loop into nine clean reports. Read the exit code: treat 2 as a failed search and fix it, never as a tree with nothing to convert.

**Prove the searches can fail before believing them.** Write two scratchpad files — never in the repo, which is usually clean. One holds the US spelling of **every row of the table, with its inflections and a compound**; the other holds the already-correct NZ forms. For the `-og` row pick `dialog_window`, not `dialogUrl`: the `-og` command cannot reach a name whose next character is `U`, so that compound fails the control against a miss documented below rather than a bug. Run all nine commands against both: each row must be caught, and the second file may return only hits this file already documents as noise — put nothing else in it, or the expected false positives read as failures. One word per command is not enough: it proves the command runs, where what you need is that the *row* is covered, and a missing inflection passes it happily.

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

The `-og` command is the exception, and shows what to do where the US spelling is a *prefix* of the NZ one: left open it matches the already-correct `catalogue`. Anchoring the right end is the obvious fix and the wrong one — it drops `catalog_id` and `dialogWindow`, and inflections then have to be listed by hand, which is how `cataloged` and `cataloging` went missing for a month behind `ged`/`ging`. It demands a following character that is not `u` instead — and, the search being case-insensitive, not `U`, so `dialogUrl` escapes it too. Identifiers being in scope, that is a real miss: convert a camel-cased `dialogU…` or `analogU…` name by hand, since no command reports it. `program`/`programme` is the same shape, left open rather than special-cased, so expect `programme` back.

### What over-reporting brings back

The `-our` belongs to the base word, not to every word built from it, and which suffixes drop the `u` is a closed list rather than a rule you can derive — every attempt to state it generatively gets `honourable` or `favourite` wrong. **It drops before `-ary`, `-ate`, `-ific`, `-ous` and `-ious`**: `honorary`, `invigorate`, `honorific`, `rigorous`, `vigorous`, `humorous`, `odorous`, `clamorous`, `glamorous` and `laborious` are already correct. It **survives** before the suffixes that attach freely to English words — `honourable`, `favourite`, `colourful`, `colourist`, `behaviourist`, `humourless`, `neighbourly`, `labourer`. `humorist` is a one-off that drops despite sitting in that second group, and `coloration` and `vaporise` vary between dictionaries.

Treat anything off the drop list as a word to check, **and check it in both directions**. This section frames its hits as noise, which makes the easy error leaving `colorist` or `behaviorist` in the tree as though the suffix excused them — a miss, and the direction this skill treats as the serious one, where inventing a `u` at least reads wrong to the next person.

Unrelated words also match, and one of them dominates the results in a code repository: **`literal` and `literally`** come back from `liter`, along with `literature` and `literary`. Expect them to outnumber the real hits on that command. Likewise `capsize`, `resize`, `downsize` and `oversize` from `-ize`, `cluster` and `bluster` from `luster`, `arboretum` from `arbor`, `laboratory`, `collaborate` and `elaborate` from `labor`, `evaporate` and `evaporation` from `vapor`, `Colorado` and `colorectal` from `color`, `citizen` and `citizenship` from `-ize`, `staging` from `aging` along with `packaging`, `messaging`, `managing` and `imaging`, which outnumber it, the already-correct `programme` from `program`, a court's equally correct `judgment` from `judgment`, and, under the `-el` pattern, `accelerate` and `accelerator` plus the whole `-eel` family — `feeling`, `peeling`, `wheeling`, `kneeling`, `peeler` and the rest.

Two of them come back as whole classes rather than as one-off words, and both are already correct: the **NZ inflections `fulfilled`, `fulfilling`, `enrolled` and `enrolling`**, which keep the double `l` that command searches for, and the **`-ogy`/`-ous` family** — `analogy`, `analogous`, `ideology`, `ideological`, `pedagogy`, `homologous` — which drop the `ue` in NZ English exactly as they do in US, so the `-og` command reports every one of them.

`Prolog` is a language, and `dialog`/`analog` are common API identifiers (HTML `<dialog>`, ADC `analog` pins) — Scope exempts those *occurrences* as names fixed outside the repo, not the words. A `show_dialog` this repo defines is still in scope; the library's `dialog` it calls is not, and the two sit on adjacent lines. These are the terms most likely to be mass-converted wrongly in either direction.

### Rows needing judgement

`meter` is searched here rather than with the other `-er` words, because it is the one of them that needs reading:

- **`license`/`practice`** — noun takes `c` (a licence, a practice), verb takes `s` (to license, to practise). The bare forms need reading, and so do the **plurals**: `licenses` is a noun plural (→ `licences`) or a verb, and `practices` likewise. Only `licensed` and `licensee` never do — always `s`, always **already correct**, so leave them. `licensing` never reaches you at all: `license` carries an `e` where `licensing` carries an `i`, and no other command looks for it. `practiced` and `practicing` are always verbs, so they always become `practised` and `practising`.
- **`program`** — correct as-is in computing, which in a code repository is nearly every hit.
- **`meter`** — a parking or power *meter* is correct; only the unit of length is *metre*. Left open, so expect `parameter`, `diameter` and `perimeter` to bury the real hits in a code repository; they are the price of catching `kilometer`.

```
rg -in --hidden -g '!.git' -g '!*.lock' "(license|practice|meter|program)" .
rg -in --hidden -g '!.git' -g '!*.lock' "(practiced|practicing)" .
```

The first needs a decision per hit, except for its `practiced` hits, which the second claims and which are always a conversion. `practicing` reaches you from the second command alone: `practice` carries an `e` where `practicing` carries an `i`, so the first never sees it.

## Triage

For each hit: **is this name the repo's to change?**

- Fixed outside it — an imported symbol, a CSS property, a URL, a manifest key, an external tool's flag, or the same name as `param=value` where the callee is external → **skip**.
- Defined here but copied outside — a stored field name, this repo's own CLI flag or environment variable, a public API identifier → **skip, and list it** in what you report, so the migration it needs is somebody's decision rather than nobody's.
- Written by this repo and held nowhere else — a docstring, comment, error message, a string literal nothing outside matches, or an internal identifier → **convert**, and where it is an identifier, rename every reference in the same change.
- Undecidable from the line alone: search the repo for the bare term, with the hidden-file flags the sweep commands carry (`rg -in --hidden -g '!.git' 'dialog' .`, since a name defined under `.github/` is invisible without them — and not `-w`, which counts `_` as a word character and so misses `show_dialog`, the shape a real definition usually takes). What the search settles is each **occurrence**, not the word: one that resolves to a dependency is skipped, one that resolves to a definition here is converted, and a term doing both — a locally defined `dialog_window` beside the library's `dialog` — gets that judgement line by line rather than a single verdict for the file.

## Verify

Four checks, all of them, in order:

1. **Re-run every command.** What remains must be a set you have read and rejected. Read nothing into an empty result either way: the documented noise is only there if the repository happens to hold those words, and a small clean tree legitimately silences most of the commands. Emptiness is the control's job, not this one's — if you doubt a command still runs, point it at the fixture rather than the tree.
2. **Search for every name you renamed, in its old spelling** — `rg -n --hidden -g '!.git' 'old_name' .`, one command per name, with the hidden-file flags for the reason Triage gives, since a renamed file is referenced from `.github/` and `.gitignore` as often as from code. **Drop the `-i` you use everywhere else**: you know the case of the name you renamed, and case-insensitivity is what lets the guard below swallow a `dialogUrl`. Account for every hit as either a reference you meant to keep or one you missed.

   Where the old spelling is a prefix of the new — `dialog` inside `dialogue`, `catalog` inside `catalogue`, `program` inside `programme` — that bare search also returns every reference you converted correctly, and those are what hide the one you missed. Guard the right end as the `-og` command does — but with **the character your new spelling adds at that position**, which is only `u` for the `-ogue` family. `show_dialog([^u]|$)` drops the correct `show_dialogue` conversions; the same `[^u]` against `run_program` drops nothing at all, because `programme` adds an `m`, and `run_program([^m]|$)` is what leaves a result that should be empty. Copy the shape, not the character.

   What this mostly adds over check 1 is attribution. Check 1 finds a missed reference too — the US spelling is exactly what a missed reference still holds — but it arrives among the hits you have already read and rejected, with nothing marking it as new, where check 2 asks only about the names you changed. It does add reach in one place, which is why a clean check 1 is no reason to skip it: dropping the `-i` recovers the camel-cased `dialogUrl` the sweep's own `-og` command is documented to swallow.
3. **Read `git diff` word by word.** What the diff shows and the other checks do not is a conversion that should never have happened — a name from the copied-outside list, or a US spelling sitting inside an external identifier. The half a rename is *missing* is by definition not in the diff, which is check 2's job.
4. **Run the test suite.** Where you renamed anything this is load-bearing rather than a formality, so run it even where the pass looked like prose only. Two blind spots to state rather than trust it through: a golden fixture holding a name you renamed must move with the rename, where one asserting on a US spelling as its subject must not — read which kind you have rather than letting red or green decide; and a round trip through your own renamed serialiser passes green while stored data written under the old name no longer matches, which is why those names are skipped above. Where the suite does not cover what you edited — a docs-wide pass in a repo whose tests cover one package — say so rather than reporting the suite green, because it verified none of it.
