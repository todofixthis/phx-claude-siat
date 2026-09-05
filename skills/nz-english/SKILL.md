---
name: nz-english
description: Use when scanning for or correcting US English spellings in a codebase — comments, docstrings, docs, string literals, and the identifiers the repo itself defines, but not names fixed outside it.
---

# NZ English Conversion

Convert US English spellings to NZ English in human-readable text.

A bundled tool does the searching. You do the deciding — which of its hits are this
repo's to change, and which are names something outside holds a copy of.

## Scope

**Convert:** comments, docstrings, `.rst`/`.md` docs, string literals, error messages, and the identifiers this repo defines — parameter, method, class, attribute, local and file names alike.

**Do NOT convert:** names fixed by something outside the repo — an external library's identifiers, URLs, and manifest keys and values. A `LICENSE` file, an SPDX identifier, and the `license` field in `plugin.json` or `package.json` all keep the US spelling for that reason. When prose describes a US-spelled external API (e.g. `normalize=True`), convert the prose but leave the identifier.

Read the project's agent instructions first — `AGENTS.md` and `CLAUDE.md` at the root, plus any nested one covering the subtree you are sweeping. The report's header names the ones it found. A stated US English convention wins over this skill for whatever it covers, whole tree or identifiers only, and a nested file governs its own subtree. Absent such a statement the repo's own names are in scope: a US-spelled tree is not a statement, that being what this skill is invoked to change.

**Converting an identifier is a rename, not a spelling fix.** Every reference moves with it in the same change: call sites, imports, the string literals that name it, the docs that quote it, and for a filename the paths in manifests, workflow globs, `.gitignore` and symlink targets, moved with `git mv`. The references that kill a rename are the ones no import graph shows — a `getattr(obj, "color")`, a `**kwargs` key, a name built into a template or a query string.

**A third kind of name is defined here and still not yours to rename**, because something outside holds a copy: a serialised field name or database column that stored data already uses, a CLI flag or environment variable a user's scripts pass, a public API identifier, a filename named by a branch-protection rule or a published URL. Leave these, and say which ones you left. Converting one is a migration that moves the data or the callers with it, and belongs in its own change announced where the project records breaking changes. **The half of such a rename living outside the repo cannot be verified from inside it**, so a clean grep here proves nothing about it.

A string literal is converted where a person reads its text, and also where it names an identifier this repo is renaming — the two have to move together. One matched against something outside the repo is an identifier wearing quotes: a CSS property (`"color: red"`), a CLI flag (`--normalize`), an environment variable, a dict key from an external schema, a regex.

**Whole trees to leave alone:** vendored and third-party directories; quoted external text anywhere; test fixtures that assert on US spelling, since converting one breaks the suite Verify then runs; and **any file of past release notes**, which records text users already received, so respelling one falsifies it. An ADR or design doc records a decision rather than a released artefact, and stays in scope.

The tool excludes exactly three things by itself: lock files, `CHANGELOG.md`, and its own directory, whose word list is built out of US spellings. Everything else on that list is yours to recognise — release notes especially, since they can live under any name and the tool will report them like any other prose.

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

This table and the tool's patterns are one thing in two places, and the bundled tests
fail if they drift: every row must find its word in the US control, and the row counts
must match. **Adding a row means adding its pattern in the same change** — the suite
will tell you if you forget.

## Search

Run the tool from the root of the tree you mean to sweep. `${CLAUDE_SKILL_DIR}` is
substituted before you see this text:

```
python3 ${CLAUDE_SKILL_DIR}/scan.py .
```

`${CLAUDE_SKILL_DIR}` is where the tool lives; the trailing `.` is the tree being swept.
They are rarely the same place. Name paths instead of `.` to sweep less — any number of
them, and individual files as well as directories.

Read the exit code, not the output — a shell pipeline throws that distinction away.
**0** nothing to triage, **1** hits to triage, **2** the run failed, **3** a bad argument
(yours to fix, not a breakage to escalate), **4** nothing to check — every path given was
missing or excluded, distinct from a broken run (see Pre-commit hook, below).

A sweep reads tens of thousands of lines a second — faster on code than on prose — so it
takes seconds on an ordinary repository and minutes on a very large monorepo. It always
finishes: give it room rather than interrupting it, and where the wait would be minutes,
count the lines and decide whether to name a subtree instead. Each row lists at most 50
hits and counts the rest; `--limit N` raises that, and the header
counts are complete whatever the listing shows.

The report lists every row of the table above, including rows that found nothing, so a
silent row is visible rather than absent. Each hit gives `path:line`, the **matched
span** (which row claimed it), and the **whole token** (what you would rename). A token
matching two rows appears under both, because it needs both conversions: `colorize`
becomes `colourise`, not one or the other.

Rows marked `*judgement` need reading rather than applying — see below. Where the mark
names a span (`*judgement: meter`), only the hits with that span need it; the rest of
the row converts normally.

Words the table's open-ended patterns reach that are already correct are counted as
noise and collapsed. Add `--show-noise` to see where each one is.

**If the tool cannot run** — exit 2, or no `python3` — stop and say so. Don't hand-write
searches to replace it: the patterns carry a guard and a noise list a typed command will
not, and a search that covers less than it appears to is the failure this tool exists to
end.

A sweep that read **nothing** — every path missing or excluded, or a tree wholly
gitignored — exits 4, not 2: nothing was searched, so nothing was proved, but that is a
different state from a broken run (see Pre-commit hook, below).

**A low file count is the failure this cannot catch.** The header reads
`swept: <path> (N files, files|git|walk)`, and both halves are diagnostic:

- Inside a repository the tool asks `git ls-files -co --exclude-standard` for a directory
  target, so whatever `.gitignore` covers is invisible. That keeps `node_modules` out, and
  it also hides a generated subtree you *did* want swept. Ten files in a tree of seven
  thousand is not an error, and only `N` will tell you.
- `files` means every target you named was a file, so nothing was walked or asked of git
  — nothing to filter, because there was nothing to discover. `git` means at least one
  target was a directory inside a repository, so that target was filtered. `walk` means
  at least one target was a directory outside a repository, where nothing was filtered
  and you may be sweeping build output.

Compare `N` against what you expected before believing a clean result. Where it is short,
name the paths explicitly — the tool takes several.

To prove the patterns still fire before you trust a clean result:

```
python3 ${CLAUDE_SKILL_DIR}/scan.py --self-check
```

That runs them over two bundled controls — one US-spelled, one NZ-spelled — and fails
if any row finds nothing or the correct spellings report a hit. It exercises the
patterns only, not discovery, so it tells you the searches work and nothing about
whether the sweep reached your files.

### Why the `-og` row over-reports one shape

The `-og` patterns demand a following character that is not a lowercase `u`, so they
catch `catalog_id` and `cataloged` while leaving the already-correct `catalogue` alone.
The guard is deliberately case-sensitive where the rest of the search is not, which is
what lets a camel-cased `dialogUrl` or `analogUpdate` be reported — those are real misses
that the hand-run version of this skill could not reach at all.

The price is a SCREAMING_CASE `DIALOGUE` or `ANALOGUE` coming back as a hit, because the
character after `DIALOG` is a capital `U`. Skip those: they are already correct. One
false hit costs you a second, where the miss it buys back survives indefinitely.

## Pre-commit hook

Sweeping the whole tree on every commit is minutes on a large repository, so a hook that
passes the staged paths instead is a good use of the tool. Two things make that safe:

```sh
set --
while IFS= read -r path; do
    [ -n "$path" ] || continue
    set -- "$@" "$path"
done <<STAGED
$(git diff --cached --name-only)
STAGED
python3 ${CLAUDE_SKILL_DIR}/scan.py --no-implicit-cwd "$@"
```

(The `while read` loop is not incidental: `$(...)` word-splits unquoted, breaking on a
path containing whitespace — the same reason this repo's own `.githooks/pre-commit`
collects staged paths the same way.)

`--no-implicit-cwd` turns an empty selection into exit 4 instead of the default no-args
behaviour of sweeping the working directory — without it, a commit touching nothing this
tool cares about would silently sweep the whole repository instead of skipping cleanly.
And a staged **deletion** among the paths — routine, since `git diff --cached --name-only`
carries deletions unless you add `--diff-filter` — no longer fails the run: a path that no
longer exists is skipped, and the files that do still exist are still swept.

Read the exit code:

- **0** and **1** mean what they always do: clean, or hits to triage.
- **4** means nothing staged needed checking — every staged path was excluded (`*.lock`,
  `CHANGELOG.md`) or deleted. Let the commit through: this is the healthy common case,
  not a misconfiguration.
- **2** and **3** keep their meanings: escalate a 2, fix a 3 — a hook seeing either has a
  genuine problem, unlike 4.

## Triage

For each hit: **is this name the repo's to change?**

- Fixed outside it — an imported symbol, a CSS property, a URL, a manifest key, an external tool's flag, or the same name as `param=value` where the callee is external → **skip**.
- Defined here but copied outside — a stored field name, this repo's own CLI flag or environment variable, a public API identifier → **skip, and list it** in what you report, so the migration it needs is somebody's decision rather than nobody's.
- Written by this repo and held nowhere else — a docstring, comment, error message, a string literal nothing outside matches, or an internal identifier → **convert**, and where it is an identifier, rename every reference in the same change.
- Undecidable from the line alone: sweep the narrower path (`python3 ${CLAUDE_SKILL_DIR}/scan.py path/to/dir`) and read the surrounding lines. What that settles is each **occurrence**, not the word: one that resolves to a dependency is skipped, one that resolves to a definition here is converted, and a term doing both — a locally defined `dialog_window` beside the library's `dialog` — gets that judgement line by line rather than a single verdict for the file.

### Rows needing judgement

- **`license`/`practice`** — noun takes `c` (a licence, a practice), verb takes `s` (to license, to practise). The bare forms need reading, and so do the **plurals**: `licenses` is a noun plural (→ `licences`) or a verb, and `practices` likewise. Only `licensed` and `licensee` never do — always `s`, always **already correct**, and the tool files them as noise. `practiced` and `practicing` are always verbs, so they always become `practised` and `practising`; they sit on the `practice` row but carry no judgement mark.
- **`program`** — correct as-is in computing, which in a code repository is nearly every hit.
- **`meter`** — a parking or power *meter* is correct; only the unit of length is *metre*. It is marked on the `-er` row rather than given one of its own.
- **`judgment`** — a court's `judgment` keeps that spelling.

### The trap inside the noise

The `-our` belongs to the base word, not to every word built from it, and which suffixes drop the `u` is a closed list rather than a rule you can derive — every attempt to state it generatively gets `honourable` or `favourite` wrong. **It drops before `-ary`, `-ate`, `-ific`, `-ous` and `-ious`**: `honorary`, `invigorate`, `honorific`, `rigorous`, `vigorous`, `humorous`, `odorous`, `clamorous`, `glamorous` and `laborious` are already correct, and the tool treats them as noise. It **survives** before the suffixes that attach freely to English words — `honourable`, `favourite`, `colourful`, `colourist`, `behaviourist`, `humourless`, `neighbourly`, `labourer`. `humorist` is a one-off that drops despite sitting in that second group. `coloration` and `vaporise` vary between dictionaries: **leave them as you find them and list them in what you report**, so the choice is made once by a person rather than silently by whoever swept last.

So **`colorist` and `behaviorist` are hits, not noise**, and the tool reports them as such. The easy error is reading the drop list as covering every `-or` word with a suffix and leaving them in the tree — a miss, and the direction this skill treats as the serious one, where inventing a `u` at least reads wrong to the next person. Check anything off the drop list in both directions.

`Prolog` is a language, and `dialog`/`analog` are common API identifiers (HTML `<dialog>`, ADC `analog` pins) — Scope exempts those *occurrences* as names fixed outside the repo, not the words, so the tool reports them and you decide. A `show_dialog` this repo defines is still in scope; the library's `dialog` it calls is not, and the two sit on adjacent lines. These are the terms most likely to be mass-converted wrongly in either direction.

## What to report

Three things, and the second is the one that gets dropped:

1. **What you converted**, at the level of "the prose in these files, and these renames."
2. **What you skipped because something outside holds a copy** — every stored field name,
   CLI flag, environment variable, public identifier and rule-named filename you left,
   named individually. This list is the whole reason that category exists: unreported, the
   migration each one needs becomes nobody's decision. Include `coloration` and `vaporise`
   here if you met them.
3. **What you could not verify** — a suite that does not cover what you edited, a rename
   whose other half lives outside this repo, a subtree the file count says was never
   swept. Say it plainly rather than reporting the pass as clean.

## Verify

Four checks, all of them, in order:

1. **Re-run the sweep.** What remains must be a set you have read and rejected. The report names every row and counts what it suppressed, so a row that found nothing says so — but an empty result still tells you nothing about the parts of the tree the sweep never reached, which is what `--self-check` and the file count in the header are for.
2. **Check every name you renamed**, one flag per name:

   ```
   python3 ${CLAUDE_SKILL_DIR}/scan.py --verify show_dialog --verify old_name .
   ```

   Pass the **old** spelling. The tool finds the table row, works out the character the
   NZ spelling adds, and searches case-sensitively with that as a guard — so
   `show_dialogue`, which you converted correctly, does not come back, and
   `show_dialog`, which you missed, does.

   A guard exists only where the US spelling is a *prefix* of the NZ one, which across
   the whole table is true of the `-ogue` family and `program`/`programme` alone. Nothing
   is added to the end of `color` to make `colour`, so a search for `color_map` cannot
   match `colour_map` and needs no guard. The report says which case you got. Account for every surviving hit as a reference
   you meant to keep or one you missed. A name matching no row exits 3 rather than
   running a search that would find nothing.
3. **Read `git diff` word by word.** What the diff shows and the other checks do not is a conversion that should never have happened — a name from the copied-outside list, or a US spelling sitting inside an external identifier. The half a rename is *missing* is by definition not in the diff, which is check 2's job.
4. **Run the test suite.** Where you renamed anything this is load-bearing rather than a formality, so run it even where the pass looked like prose only. Two blind spots to state rather than trust it through: a golden fixture holding a name you renamed must move with the rename, where one asserting on a US spelling as its subject must not — read which kind you have rather than letting red or green decide; and a round trip through your own renamed serialiser passes green while stored data written under the old name no longer matches, which is why those names are skipped above. Where the suite does not cover what you edited — a docs-wide pass in a repo whose tests cover one package — say so rather than reporting the suite green, because it verified none of it.
