---
status: Accepted
date: 2026-10-08
scope: [.claude-plugin/, .githooks/pre-commit, .github/workflows/pr.yml, hooks/, pyproject.toml, uv.lock, scripts/frontmatter.py, skills/writing-adrs/]
summary: Ship the ADR tool beside the writing-adrs skill with PyYAML as a declared dependency parsing all frontmatter through its C loader; a SessionStart hook syncs it with uv into a per-plugin-version venv under CLAUDE_PLUGIN_DATA, and every other hook and the skill's own commands run that venv's python directly — not uv run per event, not a vendored or hand-written parser, not an optional import, and not a standalone plugin or skill-frontmatter hooks.
revisit-when: A consumer needs the skills without the hooks and Claude Code offers no per-hook opt-out, or the mean hook cost a tool-calling turn incurs exceeds 5% of the median turn, or a hook event's p95 exceeds 1 s, or a consumer is found running the plugin without uv, or Claude Code installs a plugin's Python dependencies itself.
---

# 034: Run the ADR tool from a uv-synced plugin environment

## Context

[ADR 022][] ships [`adr.py`][] and `hook.py` beside the `writing-adrs` skill as a
standard-library tool, run by consumers and by every hook event as bare `python3`. Its
parser, [`frontmatter.py`][], reads frontmatter line by line as a grammar this repository
defines. GitHub renders the same block through a YAML parser, so `yaml_hazard()` in `adr.py`
refuses values a YAML reader would misread, judged by a hand-written character class.

[ADR 007][]'s Revisit watch predicted on 2026-09-03 that this class would be "wrong on
exactly the inputs nobody tried". On 2026-10-07 the two cookiecutter template repositories
tried one. Their ADRs scope paths under a directory literally named
`{{ cookiecutter.github_project_name }}/`, which YAML needs quoted in a flow sequence:
unquoted, `{` opens a mapping. [PyYAML][] reads the quoted form as intended; `yaml_hazard()`
refuses any entry opening with a quote, and refuses the unquoted form too. No spelling of a
path under the templated tree passes, so `check`, `index` and every writing command refuse
in both repositories, and `for` skips those ADRs, injecting nothing for the files they
govern. `frontmatter.py` also keeps the quotes when it splits a list, so a matcher would
miss the path even if the refusal were lifted. The same module parses skill frontmatter for
[`validate_manifests.py`][], through the symlink [ADR 023][] chose.

On 2026-10-08 the maintainer accepted `uv` on `PATH` as a consumer requirement, which ADR
022 named as a revisit condition: a hook needing more than a POSIX shell and `python3`.
Claude Code's plugin documentation, checked the same day, gives each plugin
`${CLAUDE_PLUGIN_DATA}`, a directory that survives plugin updates and is meant for virtual
environments, substituted in hook commands and skill content, and shows a `SessionStart`
hook installing dependencies into it. Claude Code installs a plugin's Node dependencies
itself, but not its Python ones. `${CLAUDE_PLUGIN_ROOT}` is a directory per plugin version,
and an old version's stays for 14 days so a session already running it keeps working.

Cost bounds every option. ADR 022 measured a hook event's median at 74 ms against a budget
it stated as "100 ms on this repository's corpus", per event, with no rationale. A research
note the maintainer commissioned traced the figure: 100 ms is the "feels
instantaneous" limit in [Nielsen's response-time limits][Nielsen] and the input-response
goal in [RAIL][], both timing a user's action to visible feedback, where a `PreToolUse` hook
answers a model's tool call and no user action at all. Nielsen treats a delay of 0.1–1 s as
noticed but tolerable and 1 s as the limit for an uninterrupted flow of thought. Per-event
cost also compounds over a session, and one tool-calling turn fires several events: a
`PreToolUse` per matched call and a `PostToolBatch` for the batch. A turn — model response
plus tools, from one tool-calling message to the next in a transcript, parallel calls
counted once — was measured over 53 consecutive turns in the subagent transcripts of one
working session in this repository on 2026-10-08: median 7.0 s, mean 10.2 s, 25th
percentile 2.1 s. Over 71 such turns those subagents fired a mean of 1.69 hook events a
turn; none issued parallel calls, which would raise it. One model, one container.

Measured on this container on 2026-10-08:

| Per hook event | Cost |
|---|---|
| Interpreter start: `python3` / a venv's `python` / `uv run` | 16 / 21 / 36–38 ms |
| `import yaml` | 15–17 ms |
| All 35 ADRs, libyaml `CBaseLoader` / pure-Python `BaseLoader` | 1.5 / 20 ms |

A first `uv sync` of the skill's environment took 1.9 s, a no-op one about 20 ms. Two
concurrent syncs into one environment both succeeded, serialised by the lock file `uv`
keeps in it. A shell step hashing `uv.lock` to name a venv cost 6 ms.

This ADR restates ADR 022 with its standard-library and `python3`-only claims replaced, and
supersedes it.

## Options

Every option keeps the line-level pass `frontmatter.py` runs now — one field per line, no
block scalar, no duplicate key — because those are this repository's own rules, stricter
than YAML's: PyYAML accepts a wrapped value and keeps the *last* of two duplicate keys. All
keep writing line-based too, since ADR 023 forbids the tool rewriting a sentence the agent
wrote. What ranks the options is who decides what a *value* means, and what that costs a
hook event.

### Option 1: Do nothing

Keep the hand-written value grammar and extend it per case. At its strongest: accept a
list entry quoted end to end with no escapes, strip the quotes, and refuse the rest as
`yaml_hazard()` does now.

**Pros:** About twenty lines of standard library, no dependency, no cost added.
**Cons:** Splitting a list on commas breaks a quoted entry holding `, `, so the narrow fix
needs a flow-sequence tokeniser as well. Anything outside the subset is refused although
it is valid YAML.
**Risks:** Each refusal is found by a consumer, as this one was, and each costs a plugin
release to lift.

### Option 2: Declare PyYAML, sync a venv at session start (Accepted)

`skills/writing-adrs/pyproject.toml` declares PyYAML, locked by the root `uv.lock`. The
`SessionStart` hook syncs the skill's dependencies — `uv sync --frozen`, the skill's package
alone, no dev group, the project itself not installed — into a venv under
`${CLAUDE_PLUGIN_DATA}` named for the plugin version, on every run, and marks the venv
complete only once the sync succeeds. Every other hook runs that venv's `python` on the
tool's files in place. The skill's own commands go through a launcher shipped beside the
tool, which syncs the same venv first wherever it is not marked complete, so a repository
adopting the tool — whose hooks stay off until `adr.py` writes its first index — can
bootstrap. `frontmatter.py` loads every block with `CBaseLoader`.

**Pros:** YAML decides every value, at 1.5 ms for the corpus, so no hand-written grammar
remains. `BaseLoader` resolves no types, so `yes`, `34` and an ISO date stay strings.
Renovate's `pep621` manager tracks PyYAML, and no third-party code enters the tree. `uv`
provides an interpreter matching the skill's `requires-python`, so `python3` on `PATH`
stops being required.
**Cons:** Every consumer needs `uv`. Every hook event pays the venv's slower start and the
import, about 21 ms over ADR 022's figures: a median near 95 ms on every corpus. The first
session after each plugin update waits on a resolve, about 2 s here; longer on a slow
network, and far longer where `uv` must first download an interpreter matching the skill's
`requires-python`.
**Risks:** An offline first session gets no venv, and its hooks stay off for that session.

#### Sub-question: how a hook reaches the venv

`uv run` per event costs 36–38 ms to start where the venv's own `python` costs 21 ms,
which with the import puts a median near 107 ms. Both sit inside the bounds the Decision
sets, so the 100 ms aspiration ranks them: per-event hooks never call `uv`, and build the
venv's path by shell parameter expansion from the plugin version, the last component of
`${CLAUDE_PLUGIN_ROOT}` under the plugin cache, rather than spend 6 ms hashing `uv.lock`
to name it. A plugin loaded in place from a checkout, as this
repository dogfoods itself, has no version in its path. There the hooks, the `SessionStart`
sync and the launcher all use the checkout's own workspace venv instead, telling the two
cases apart by whether the tool sits under the plugin cache. The sync into it adds the
skill's dependencies with `--inexact`, removing nothing the developer's own `uv sync`
installed, and marks it complete the same way, creating it where none exists yet.

A venv per version, not one shared, because sessions on two versions coexist for up to 14
days and `uv sync` is exact: with one venv, each version's `SessionStart` — on every
startup, resume, clear, compact or fork — would strip what the other added.

### Option 3: Vendor pure-Python PyYAML beside the skill

Copy PyYAML's pure-Python package (6.0.3, MIT-licensed, 252 KB) into the skill, keeping
bare `python3`.

**Pros:** No install step and no new requirement on consumers; a corpus of plain values
never imports PyYAML.
**Cons:** The pure-Python loader takes 20 ms for the corpus, so staying in budget means
deferring to PyYAML only values a hand-written allowlist cannot prove plain, guarded by a
test over generated cases. Third-party code sits in the tree, out of this repository's
lint, format and spelling checks, with a CI check tying it to a pinned release.
**Risks:** The allowlist wrong in the permissive direction is the original bug back.

### Option 4: Import PyYAML when installed, else fall back

Try `import yaml`; where it fails, use the hand-written grammar.

**Pros:** No vendored code, no install step.
**Cons:** Which grammar decides a value depends on the environment.
**Risks:** A consumer without PyYAML keeps today's bug, and a corpus can pass in CI, where
PyYAML is installed, and fail in a session, or the reverse.

## Decision

Option 2. The value grammar is YAML's, so YAML's parser should decide every value.
Option 1 keeps refusing valid YAML, a consumer at a time, and Option 4 keeps the bug for
exactly the consumers who would hit it.

With `uv` accepted, Option 3's advantage is the requirement it avoids, and what it costs is
the allowlist. The pure-Python loader is too slow to read every value, so Option 3 can only
afford PyYAML behind a hand-written plain-value rule: a grammar approximated in-house,
which is what this decision exists to remove. libyaml reads the whole corpus in 1.5 ms, so
Option 2 needs no such rule.

[ADR 017][]'s no-install clause holds in its own terms. It asks that a skill work on first
invocation with no per-repository setup, and treats `python3` as a machine prerequisite.
The hooks build the venv themselves, once per plugin version on each machine, and `uv` is a
machine prerequisite — a less common one than `python3`, which is the cost accepted here.
The trigger naming a consumer without `uv` is how that cost would surface.

#### Sub-question: the hook budget

ADR 022's per-event 100 ms answers the wrong question, so it becomes an aspiration: a median
worth aiming at by analogy with Nielsen and RAIL, which ranks options that both fit the
bounds below. Two bounds replace it, neither counting the first sync after an update.

- **The session budget, which the trigger watches:** the mean hook cost a tool-calling turn
  incurs — events a turn times mean cost an event — stays within 5% of the median turn,
  about 350 ms against today's 7.0 s. The literature gives no aggregate figure, so 5% is a
  judgement, and these are its terms. At 1.69 events a turn today's hooks cost about 1.8%
  and this decision's about 2.3%, medians standing in for the means until implementation
  measures them, so 2% would fire on the status quo. 5% leaves this
  decision about twice its cost in headroom, and fires on a model about twice as fast, or
  at about 3.7 events a turn. Higher would let hook cost grow unwatched into the turn's
  own spread. The median turn is the denominator, stricter than the 10.2 s mean, so a
  skewed tail of long turns cannot hide hook cost; and the share is relative, so faster
  models raise it and fire the trigger without anyone re-deriving a number.
- **The per-event ceiling:** p95 within 1 s, Nielsen's flow-of-thought limit, enforced by a
  `pr.yml` check timing at least 20 `hook.py` events over this repository's corpus. It
  holds `SessionStart` too, no-op sync included, the one hook a person waits on. It
  catches only a gross regression, which is its job: the turn cannot be measured in CI, so
  the ceiling is the one bound a build can hold.

Should the trigger fire, the first lever is to cache the parsed corpus by file modification
time, so most events skip the import; that is decided then, not here.

Everything else ADR 022 decided stands, for the reasons it gives: the tool sits beside the
skill, the plugin's `hooks/hooks.json` declares the hooks, neither a standalone plugin
([ADR 012][]) nor hooks declared in the skill's frontmatter alone replace that, and the
hooks remain POSIX-only, Windows without Git Bash out of scope.

## Consequences

- `hooks/hooks.json`'s gate checks for `uv` where it checked for `python3`, and the
  `SessionStart` line says so in context where `uv` or the sync fails. Its timeout rises to
  cover a cold resolve. Every other hook exits silently until the venv is marked complete,
  so a sync interrupted after creating `python` but before installing PyYAML stays quiet
  rather than failing every event. The venv layout assumed is POSIX's `bin/python`.
- `SessionStart` prunes a version's venv only once that version's directory has left the
  plugin cache, so no session still running it can lose it.
- `frontmatter.py` imports PyYAML and parses with `CBaseLoader`, falling back to the
  pure-Python `BaseLoader` where a platform's wheel lacks libyaml; that fallback is slow
  enough to breach the budget, and the carried trigger is how it would surface.
  `yaml_hazard()`'s character class goes, and a value PyYAML refuses is reported as any
  other malformed field. A regression test covers the templated-path case above.
- The skill passes the substituted `${CLAUDE_PLUGIN_DATA}` to its launcher rather than
  calling `uv run`, which would build a second environment inside the per-version plugin
  cache. ADR 022's `uvx` recipe for consumer CI is unchanged and now installs PyYAML with
  the tool.
- This repository's own callers of `adr.py` — `pr.yml`'s `adr` job and
  `.githooks/pre-commit` — run it under `uv run` from the workspace, so `pr.yml` sets up
  `uv` before that step.
- `scripts/frontmatter.py` reaches the same parser through the symlink, so `scripts/` gains
  a dependency; [ADR 035][] restates how `scripts/` runs.
- The hook's mean cost per turn and p95 per event are measured at implementation on this
  repository's corpus, and the turn and events a turn are re-measured, over more than one
  session and from main and subagent transcripts alike, whenever the trigger is checked;
  each finding goes in a `## Revisit watch` section here.
- [ADR 025][]'s cost condition cited ADR 022's 100 ms per event and now cites these bounds,
  which loosen it.
- The skill's frontmatter rules and command forms, the standard-library claims in
  `adr.py`'s and `frontmatter.py`'s docstrings and the skill's `pyproject.toml`, and the
  README are corrected in the implementing change, which the [backlog item][] tracks.

[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 035]: 035-run-repo-scripts-under-uv-with-declared-dependencies.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[backlog item]: ../backlog/scripts-frontmatter-parser-should-use-pyyaml.md
[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[Nielsen]: https://www.nngroup.com/articles/response-times-3-important-limits/
[PyYAML]: https://pypi.org/project/PyYAML/
[RAIL]: https://web.dev/articles/rail
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
