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
standard-library tool. Consumers and every hook event run it as bare `python3`. Its
parser, [`frontmatter.py`][], reads frontmatter line by line, as a grammar this repository
defines. GitHub renders the same block through a YAML parser. So `yaml_hazard()` in
`adr.py` refuses values that a YAML reader would misread, judged by a hand-written
character class.

On 2026-09-03 the Revisit watch of [ADR 007][] predicted that this class would be "wrong on
exactly the inputs nobody tried". On 2026-10-07 the two cookiecutter template repositories
tried one. Their ADRs scope paths under a directory named, literally,
`{{ cookiecutter.github_project_name }}/`. YAML needs that name quoted in a flow sequence,
because an unquoted `{` opens a mapping. [PyYAML][] reads the quoted form as intended.
`yaml_hazard()` refuses any entry that opens with a quote, and refuses the unquoted form
too. No spelling of a path under the templated tree passes. So in both repositories
`check`, `index`, and every writing command refuse, and `for` skips those ADRs and injects
nothing for the files they govern. `frontmatter.py` also keeps the quotes when it splits a
list, so a matcher would miss the path even if the refusal were lifted. The same module
parses skill frontmatter for [`validate_manifests.py`][], through the symlink that
[ADR 023][] chose.

On 2026-10-08 the maintainer accepted `uv` on `PATH` as a consumer requirement. ADR 022
named this as a revisit condition: a hook that needs more than a POSIX shell and
`python3`. Claude Code's plugin documentation, checked the same day, gives each plugin
`${CLAUDE_PLUGIN_DATA}`. That directory survives plugin updates, is meant for virtual
environments, and is substituted in hook commands and skill content. The documentation
shows a `SessionStart` hook installing dependencies into it. Claude Code installs a
plugin's Node dependencies itself, but not its Python ones. `${CLAUDE_PLUGIN_ROOT}` is a
directory per plugin version. An old version's directory stays for 14 days, so a session
already running that version keeps working.

Cost limits every option. ADR 022 measured a hook event's median at 74 ms, against a
per-event budget it stated as "100 ms on this repository's corpus", with no rationale. A
research note the maintainer commissioned traced the figure. 100 ms is the "feels
instantaneous" limit in [Nielsen's response-time limits][Nielsen] and the input-response
goal in [RAIL][]. Both time a user's action to visible feedback. A `PreToolUse` hook
answers a model's tool call, with no user action at all. Nielsen treats a delay of 0.1–1 s
as noticed but tolerable, and 1 s as the limit for an unbroken flow of thought. Per-event
cost also adds up over a session, and one tool-calling turn fires several events: a
`PreToolUse` for each matched call and a `PostToolBatch` for the batch. A turn here is a
model response plus its tools, from one tool-calling message to the next in a transcript,
with parallel calls counted once. On 2026-10-08, 53 consecutive turns were measured in the
subagent transcripts of one working session in this repository. They gave a median of
7.0 s, a mean of 10.2 s, and a 25th percentile of 2.1 s. Over 71 such turns, those
subagents fired a mean of 1.69 hook events a turn. None issued parallel calls, which would
raise the figure. The data covers one model in one container.

Measured on this container on 2026-10-08:

| Per hook event | Cost |
|---|---|
| Interpreter start: `python3` / a venv's `python` / `uv run` | 16 / 21 / 36–38 ms |
| `import yaml` | 15–17 ms |
| All 35 ADRs, libyaml `CBaseLoader` / pure-Python `BaseLoader` | 1.5 / 20 ms |

A first `uv sync` of the skill's environment took 1.9 s, and a no-op sync took about
20 ms. Two concurrent syncs into one environment both succeeded, because the lock file
`uv` keeps in the environment made them take turns. A shell step that hashes `uv.lock` to
name a venv cost 6 ms.

This ADR restates ADR 022 with its claims about the standard library and `python3` alone
replaced, and supersedes it.

## Options

Every option keeps the line-level pass that `frontmatter.py` runs now: one field per line,
no block scalar, and no duplicate key. These are this repository's own rules, and they are
stricter than YAML's. PyYAML accepts a wrapped value and keeps the *last* of two duplicate
keys. Every option also keeps writing line by line, because ADR 023 forbids the tool to
rewrite a sentence the agent wrote. The options differ in what decides what a *value*
means, and in what that costs a hook event.

### Option 1: Do nothing

Keep the hand-written value grammar and extend it case by case. At its strongest, this
means accepting a list entry quoted from end to end with no escapes, stripping the
quotes, and refusing everything else as `yaml_hazard()` does now.

**Pros:** About twenty lines of standard library, no dependency, and no added cost.
**Cons:** Splitting a list on commas breaks a quoted entry that contains `, `, so the
narrow fix also needs a tokeniser for flow sequences. The tool refuses anything outside
the subset, even when it is valid YAML.
**Risks:** A consumer finds each refusal, as with this one, and lifting each costs a
plugin release.

### Option 2: Declare PyYAML, sync a venv at session start (Accepted)

`skills/writing-adrs/pyproject.toml` declares PyYAML, and the root `uv.lock` locks it. On
every run, the `SessionStart` hook runs `uv sync --frozen` for the skill's dependencies
alone: the skill's package only, no dev group, and the project itself not installed. It
syncs them into a venv under `${CLAUDE_PLUGIN_DATA}` named for the plugin version, and
marks the venv complete only after the sync succeeds. Every other hook runs that venv's
`python` on the tool's files in place. The skill's own commands go through a launcher
shipped beside the tool. Wherever the venv is not marked complete, the launcher syncs it
first. That lets a repository that is adopting the tool bootstrap, because its hooks stay
off until `adr.py` writes its first index. `frontmatter.py` loads every block with
`CBaseLoader`.

**Pros:** YAML decides every value, in 1.5 ms for the whole corpus, so no hand-written
grammar remains. `BaseLoader` resolves no types, so `yes`, `34`, and an ISO date stay
strings. Renovate's `pep621` manager tracks PyYAML, and no third-party code enters the
tree. `uv` provides an interpreter that matches the skill's `requires-python`, so
`python3` on `PATH` is no longer required.
**Cons:** Every consumer needs `uv`. Every hook event pays the venv's slower start and the
import, about 21 ms over ADR 022's figures, for a median near 95 ms on every corpus. The
first session after each plugin update waits about 2 s here for a resolve. It waits longer
on a slow network, and far longer where `uv` must first download an interpreter that
matches the skill's `requires-python`.
**Risks:** An offline first session gets no venv, and its hooks stay off for that session.

#### Sub-question: how a hook reaches the venv

`uv run` costs 36–38 ms to start for each event, where the venv's own `python` costs
21 ms. With the import, `uv run` puts the median near 107 ms. Both fit the bounds the
Decision sets, so the 100 ms aspiration ranks them. Per-event hooks never call `uv`. They
build the venv's path by shell parameter expansion from the plugin version, which is the
last component of `${CLAUDE_PLUGIN_ROOT}` under the plugin cache. They do not spend 6 ms
hashing `uv.lock` to name the venv. A plugin loaded in place from a checkout, as this
repository loads itself for dogfooding, has no version in its path. In that case the
hooks, the `SessionStart` sync, and the launcher all use the checkout's own workspace venv
instead. They tell the two cases apart by whether the tool sits under the plugin cache.
The sync into the workspace venv adds the skill's dependencies with `--inexact`, so it
removes nothing that the developer's own `uv sync` installed. It marks the venv complete
the same way, and creates it if none exists yet.

Each version gets its own venv, not one shared venv. Sessions on two versions can run side
by side for up to 14 days, and `uv sync` is exact. With one venv, each version's
`SessionStart` would remove what the other version added, and `SessionStart` runs on every
startup, resume, clear, compact, or fork.

### Option 3: Vendor pure-Python PyYAML beside the skill

Copy PyYAML's pure-Python package (6.0.3, MIT-licensed, 252 KB) into the skill, and keep
bare `python3`.

**Pros:** No install step, and no new requirement on consumers.
**Cons:** The pure-Python import and loader add 28–38 ms to each event, for a median of
about 102–112 ms. That fits the bounds the Decision sets, but meets or exceeds the 100 ms
aspiration. To get under it, the tool would hand to PyYAML only the values that a
hand-written allowlist cannot prove plain, with a test over generated cases to guard the
allowlist. A corpus of plain values would then never import PyYAML and would stay near
ADR 022's 74 ms, as fast as Option 1. Third-party code sits in the tree, outside this
repository's lint, format, and spelling checks, with a CI check to tie it to a pinned
release.
**Risks:** A vendored copy goes stale between re-vendorings, security fixes included. An
allowlist that is wrong in the permissive direction brings back the original bug.

### Option 4: Import PyYAML when installed, else fall back

Try `import yaml`. If it fails, use the hand-written grammar.

**Pros:** No vendored code, and no install step.
**Cons:** Which grammar decides a value depends on the environment.
**Risks:** A consumer without PyYAML keeps today's bug. A corpus can pass in CI, where
PyYAML is installed, and fail in a session, or the reverse.

## Decision

Option 2. The value grammar is YAML's, so YAML's parser should decide every value.
Option 1 keeps refusing valid YAML, one consumer at a time. Option 4 keeps the bug for
exactly the consumers who would hit it.

With `uv` accepted, Option 3's advantage is only the requirement it avoids. Both options
fit the bounds, so the aspiration and the upkeep decide between them. Option 2 sits under
the aspiration. Option 3 without the allowlist meets or exceeds it. With the allowlist,
Option 3 matches the speed of Option 1, and is rejected anyway. Its speed comes from a
grammar that this repository approximates itself, and removing that is the point of this
decision. In either form, someone must keep third-party code in step by hand. libyaml
reads the whole corpus in 1.5 ms, and Renovate keeps a declared dependency current.

The no-install clause of [ADR 017][] still holds on its own terms. It asks that a skill
work on first invocation with no setup per repository, and it treats `python3` as a
machine prerequisite. The hooks build the venv themselves, once per plugin version on each
machine, and `uv` is a machine prerequisite. It is less common than `python3`, and that
is the cost this decision accepts. The trigger that names a consumer without `uv` is how
that cost would show up.

#### Sub-question: the hook budget

ADR 022's per-event 100 ms answers the wrong question, so it becomes an aspiration. It is
a median worth aiming at, by analogy with Nielsen and RAIL, and it ranks options that
both fit the bounds below. Two bounds replace it. Neither counts the first sync after an
update.

- **The session budget, which the trigger watches.** The mean hook cost of a tool-calling
  turn stays within 5% of the median turn. That cost is the events in a turn times the
  mean cost of an event. Against today's 7.0 s median turn, 5% is about 350 ms. The
  literature gives no aggregate figure, so 5% is a judgement, made on these terms. At 1.69
  events a turn, today's hooks cost about 1.8% and this decision's about 2.3%. Medians
  stand in for the means until the implementation measures them. So a 2% bound would fire
  on the status quo. 5% leaves this decision about twice its own cost in headroom. It
  fires on a model about twice as fast, or at about 3.7 events a turn. A higher bound
  would let hook cost grow unwatched into the normal spread of turn times. The median
  turn is the denominator, which is stricter than the 10.2 s mean, so a long tail of slow
  turns cannot hide hook cost. And the share is relative, so faster models raise it and
  fire the trigger without anyone working out a new number.
- **The per-event ceiling.** p95 stays within 1 s, Nielsen's limit for a flow of thought.
  A `pr.yml` check enforces it by timing at least 20 `hook.py` events over this
  repository's corpus. The ceiling applies to `SessionStart` too, including a no-op sync,
  because it is the one hook a person waits on. The ceiling catches only a gross
  regression, and that is its job. CI cannot measure a turn, so the ceiling is the one
  bound a build can enforce.

If the trigger fires, the first fix to try is to cache the parsed corpus by file
modification time, so that most events skip the import. That choice is made then, not
here.

Everything else ADR 022 decided stands, for the reasons it gives. The tool sits beside the
skill. The plugin's `hooks/hooks.json` declares the hooks. Neither a standalone plugin
([ADR 012][]) nor hooks declared only in the skill's frontmatter replace that. The hooks
stay POSIX-only, and Windows without Git Bash is out of scope.

## Consequences

- The gate in `hooks/hooks.json` checks for `uv` where it checked for `python3`. Where
  `uv` or the sync fails, the `SessionStart` line says so in context. Its timeout rises to
  cover a cold resolve. Every other hook exits silently until the venv is marked complete.
  So a sync interrupted after it creates `python` but before it installs PyYAML stays
  quiet instead of failing every event. The venv layout assumed is POSIX's `bin/python`.
- `SessionStart` deletes a version's venv only after that version's directory has left
  the plugin cache, so no session still running that version can lose its venv.
- `frontmatter.py` imports PyYAML and parses with `CBaseLoader`. Where a platform's wheel
  lacks libyaml, it falls back to the pure-Python `BaseLoader`. On those platforms the
  fallback misses the aspiration but stays within both bounds. The character class in
  `yaml_hazard()` goes, and the tool reports a value PyYAML refuses like any other
  malformed field. A regression test covers the templated-path case above.
- The skill passes the substituted `${CLAUDE_PLUGIN_DATA}` to its launcher instead of
  calling `uv run`, which would build a second environment inside the per-version plugin
  cache. ADR 022's `uvx` recipe for consumer CI is unchanged, and now installs PyYAML with
  the tool.
- This repository's own callers of `adr.py`, the `adr` job in `pr.yml` and
  `.githooks/pre-commit`, run it under `uv run` from the workspace. So `pr.yml` sets up
  `uv` before that step.
- `scripts/frontmatter.py` reaches the same parser through the symlink, so `scripts/`
  gains a dependency. [ADR 035][] restates how `scripts/` runs.
- The implementation measures the hook's mean cost per turn and its p95 per event on this
  repository's corpus. Whenever someone checks the trigger, they measure the turn and the
  events per turn again, over more than one session and from both main and subagent
  transcripts. Each finding goes in a `## Revisit watch` section here.
- The cost condition of [ADR 025][] cited ADR 022's 100 ms per event. It now cites these
  bounds, which loosen it.
- The implementing change corrects the skill's frontmatter rules and command forms, the
  standard-library claims in the docstrings of `adr.py` and `frontmatter.py` and in the
  skill's `pyproject.toml`, and the README. The [backlog item][] tracked that change.

## Revisit watch

- **2026-10-13, at implementation: no trigger has fired.**

  *The turn.* The data covers three sessions in this repository's transcripts: 3 main and
  39 subagent transcripts, with 700 tool-calling messages. 593 turns gave a median of
  8.8 s, a mean of 15.7 s, and a 25th percentile of 4.9 s. Main transcripts alone gave a
  median of 9.4 s over 140 turns, and subagents gave 8.7 s over 453. One session supplied
  634 of the 700 messages. A turn is as defined above, within one transcript. Four turns
  over 900 s were dropped as waits on a person, such as a permission prompt.

  *Events a turn.* Counting one `PreToolUse` per `Read`, `Edit`, `Write`, `NotebookEdit`,
  or `Bash` call plus one `PostToolBatch` gave a mean of 2.05 over all 700 messages, of
  which 1.05 were `PreToolUse`. That is up from 1.69 on 2026-10-08, which counted
  subagents alone and no parallel calls. Here, 100 messages (14%) issued parallel calls.
  The events are averaged over every tool-calling message, untimed turns included, which
  is why the count is 700 messages against 593 turns.

  *To repeat it.* Read each `.jsonl` transcript under
  `~/.claude/projects/-Users-phx-Documents-phx-claude-siat/`. A session's subagents are at
  `<session>/subagents/*.jsonl`. One tool-calling message spans several records that share
  a `message.id`, so group by that id. Parallel calls are one message. A human prompt is a
  user record that is neither `isMeta` nor a `tool_result`. A human prompt ends a turn, and
  so do a compaction boundary, an `end_turn`, and a subagent's handback. Drop turns over
  900 s.

  *Cost an event.* Three runs of `uv run python -m scripts.ci.time_hooks` on this tree, on
  one linux/aarch64 container, gave means of 0.039–0.044 s for `PreToolUse` and
  0.040–0.041 s for `PostToolBatch`, and an overall p95 of 0.048–0.063 s. The highest p95
  of any single event type was 0.072 s, for `SessionStart`. Every timed `PreToolUse` was a
  first touch that injected its full rows, so these figures overstate a typical one.

  *Against the bounds.* At the highest means, 1.05 × 0.044 s + 1 × 0.041 s ≈ 0.087 s a
  turn. That is 1.0% of the 8.8 s median turn, against the 5% bound (0.44 s). The worst
  p95, 0.072 s, is under the 1 s ceiling. Nobody has found a consumer who needs the
  skills without the hooks, or who runs without `uv`. Nobody re-checked whether Claude
  Code now installs a plugin's Python dependencies.

[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 035]: 035-run-repo-scripts-under-uv-with-declared-dependencies.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[backlog item]: https://github.com/todofixthis/phx-claude-siat/blob/b314689/docs/backlog/scripts-frontmatter-parser-should-use-pyyaml.md
[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[Nielsen]: https://www.nngroup.com/articles/response-times-3-important-limits/
[PyYAML]: https://pypi.org/project/PyYAML/
[RAIL]: https://web.dev/articles/rail
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
