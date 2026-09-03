# Self-contained ADR system — design

> Scaffolding for one implementation (see `AGENTS.md`, "Design specs and plans"): delete
> on this branch before the PR is created. Anything worth keeping earns an ADR.

## Goal

An agent with the `phx` plugin installed works in a repository that has never seen an ADR.
The first ADR it records creates `docs/adr/` and `INDEX.md`. From then on the agent owns
the reasoning — context, options, decision, consequences — and the plugin owns the
scaffolding, the frontmatter rules, the index, and delivering each decision to whoever
touches what it binds. When the agent reads or edits a bound file, the binding decisions
arrive in its context. When it moves or deletes a bound path, it is told which decision now
names nothing, and to update `scope` or revisit the decision. A consumer maintainer sets up
nothing: no generator, no git hook, no slash command.

Today every part of that is this repository's own tooling — `scripts/adr/`,
`.githooks/pre-commit`, `pr.yml`'s `adr` job — and the skill tells a consumer to port it.
ADR 013's Known Tension #1 and ADR 021's Option 3 both name the system this spec builds.

## Assumptions

Made without asking; push back on any.

- **ADRs live at `docs/adr/`**, fixed, not configurable. Every consumer of the skill has
  that layout already.
- **The system activates only on a corpus it manages.** `docs/adr/` is also the
  adr-tools and MADR default, so a directory is not consent. The hooks are inert unless
  `docs/adr/INDEX.md` opens with the tool's generated header, which only the tool writes:
  `new` on a first ADR, or `index` run by an agent adopting an existing corpus through the
  skill. A Nygard corpus with no frontmatter is left alone. The header is a fixed literal
  — no path, no version — so the hook, the pre-commit hook and `uvx` generate the same
  bytes.
- **The system stays inside the `phx` plugin.** ADR 012 caps the catalogue at one plugin,
  and a repository the hooks are inert in pays one shell test per event.
- **Cost in an active repository is bounded.** One Python start per hooked event, per
  subagent: under 100 ms on this repository's corpus, measured at implementation and
  recorded in the ADR. A budget the measurement misses is a design fault, not a tuning job.
- **`python3` (3.10 or newer) is on `PATH`, and hook commands run under a POSIX shell.**
  Where `python3` is missing, the `SessionStart` line says so in context and every other
  entry exits silently — a missing interpreter must not become the silence ADR 013 warns
  against. Windows without Git Bash is out of scope.
- **Nothing writes to a repository except after the agent's own edit under `docs/adr/`, or
  from a tool command the agent ran.** `SessionStart`, a batch with no ADR edit, and `Stop`
  report; they never regenerate. A regenerate after `git checkout` or mid-rebase would
  dirty the tree and block the next git step.
- **Consumer CI is a documented recipe, verified here, not a shipped job.**

## Approaches considered

1. **Tool plus plugin-level hooks, inside `phx`** (chosen). One stdlib tool ships beside
   the skill; `hooks/hooks.json` wires it to the session. Delivery reaches the agent whether
   or not it ever invoked the skill.
2. **A standalone plugin** — ADR 021's Option 3. Rejected: ADR 012 forbids a second
   catalogue entry, and nothing here needs one.
3. **Hooks declared in the skill's frontmatter only.** Rejected as the sole mechanism: an
   agent editing a bound file in a session that never invoked the skill would receive
   nothing, and that agent is the reader the system exists for.
4. **Generated path-scoped rules.** Rejected by ADR 019 and not rebuilt. But the per-file
   injection below *is* the row-carrying delivery 019 declined, on the same displacement
   ground, and neither arm of 019's `revisit-when` has fired. This spec supersedes 019 on
   judgement, at the maintainer's instruction, and the ADR recording it says so plainly
   rather than claiming the trigger fired. What hooks add over rules: nothing is generated
   into the repository; delivery fires on `Write` and on a shell command naming the path,
   which no rule does; and the corpus-level instruction to read `INDEX.md` arrives at
   session start on its own channel, which 019 weighed as mitigation and not as an answer.

## Architecture

```
phx plugin
├── hooks/hooks.json                       wires the events below to hook.py
└── skills/writing-adrs/
    ├── SKILL.md                           reasoning, conventions, review — the agent's half
    ├── adr.py                             the tool: new, index, check, for, supersede,
    │                                      discharge, renumber, reconcile
    ├── frontmatter.py                     the line parser (moved from scripts/, symlinked back)
    ├── hook.py                            stdin event → adr.py → additionalContext
    ├── pyproject.toml, uv.lock            dev toolchain, plus the phx-adr entry point
    └── tests/
```

One idea holds the design together: **reconcile is idempotent, and every state-changing
event runs it.** Reconcile parses every ADR, validates frontmatter, scope and numbering,
compares the generated index with the file, and returns findings. Hooks decide what to say
and whether anything may be written; the tool decides what is true.

### The tool: `adr.py`

Standard library only. The skill body invokes it as
`python3 ${CLAUDE_SKILL_DIR}/adr.py <command>`, unquoted, and its frontmatter pre-approves
`Bash(python3 ${CLAUDE_SKILL_DIR}/adr.py:*)` — Claude Code substitutes the variable in
both places, and permission rules prefix-match the command string, so the two forms must
agree byte for byte; a test asserts every command line in the skill matches the rule. A
plugin path containing a space breaks the unquoted form; the cache path has none. Hooks
and this repository's CI invoke the tool by path. `nz-english` still tells the agent to
substitute the base directory it reported; migrating it to `${CLAUDE_SKILL_DIR}` is a
backlog item this change writes, so the plugin ends with one convention.

**Root resolution.** `--repo-root` where given; otherwise the nearest ancestor of the path
in hand — the file touched, or the hook input's `cwd`, which follows the agent's `cd` —
that holds a managed `docs/adr/INDEX.md`; otherwise the nearest ancestor holding `.git`,
so `new` from a subdirectory creates the corpus at the repository root; otherwise the
working directory. Innermost managed corpus wins; the walk stops at the first `.git`. Never
`CLAUDE_PROJECT_DIR` alone: a worktree entered with `EnterWorktree` or
`using-git-worktrees` lies outside it, and a root anchored to the launch directory would
inspect the wrong tree.

| Command | Does | Writes |
|---|---|---|
| `new <title> --summary S (--scope P … \| --no-scope) [--revisit-when R]` | Allocates the next number from the directory, slugifies the title, writes the template with complete frontmatter, creates `docs/adr/` and the index on first use, prints the path | the ADR, the index |
| `index` | Regenerates `INDEX.md`; on any problem leaves it untouched and exits 1 | the index |
| `check` | `reconcile` without `--write`, exiting 1 on any finding, a stale index included. The CI entry point | nothing |
| `for <path> …` | The reverse lookup: decisions whose `scope` covers any path, `Archived` included. A path naming a directory is matched with a trailing slash, so `scripts/adr` finds an entry `scripts/adr/` | nothing |
| `supersede <old> --by <new>` | Sets `status: Superseded` and `superseded-by`, regenerates | the old ADR, the index |
| `discharge <old> --by <new>` | Sets `revisit-discharged-by`; refuses where `revisit-when` is unset or the ADR is `Superseded` | the old ADR, the index |
| `renumber <old> <new>` | Renames the file, rewrites the heading number, every peer ADR field and reference-link target naming the old number, and the index; refuses a number already claimed; prints every other citation found in the tree for the agent to move | the ADR, its peers, the index |
| `reconcile [--write]` | Validates and prints findings as JSON. Without `--write`, a stale index is a finding. With it, the index is regenerated whenever every ADR validates, and staleness is never reported | the index, with `--write` |

`new` requires `--summary` and either `--scope` or `--no-scope`: the index renders both,
and a placeholder would land there as a row. The body is the skill's Format template,
Options 1 to 3 with the `(Accepted)` marker on Option 2, for the agent to fill.

The line between tool and agent: **the tool edits bytes derivable from a number or a field
— frontmatter, a filename, a heading number, a link target — and never a sentence.** Body
prose stays the agent's: striking a spent condition through, moving the `(Accepted)` marker
where the status quo won, writing citations.

### The hooks: `hooks/hooks.json` and `hook.py`

Every entry runs one shell line: exit 0 unless `docs/adr/INDEX.md` under
`${CLAUDE_PROJECT_DIR}` or the working directory opens with the generated header; then
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/writing-adrs/hook.py"`. The shell test is a cheap
gate, and per-path resolution applies once it passes: a worktree outside both, where the
agent has not `cd`-ed, is inert. Each entry carries a `timeout` of 20 seconds.

`hook.py` reads the event from stdin, dispatches on `hook_event_name`, and prints
`hookSpecificOutput.additionalContext` only when it has something to say. It always exits 0:
a hook is advisory. An exception inside it is reported as context once per session, since a
broken tool that falls silent is the failure ADR 013 names.

| Event | Matcher | Behaviour |
|---|---|---|
| `SessionStart` | `startup\|resume\|clear\|compact\|fork` | Injects the standing note: decisions in force, read `docs/adr/INDEX.md` before proposing architectural or tooling changes, decisions binding a file arrive as you touch it, record one with `phx:writing-adrs`. Where no state file exists, snapshots the **baseline** of current findings and reports them once — as `additionalContext` for the agent and as `systemMessage` for the human, who never sees `additionalContext`. `compact` keeps the baseline and the reported findings and resets only the injected set, since the context that held it is gone; `resume` keeps both; `fork` arrives with a new session id and no state, so it behaves as `startup`; `clear` starts a fresh state. |
| `SubagentStart` | — | The standing note: a subagent is its own context and gets no `SessionStart`. |
| `PreToolUse` | `Read\|Edit\|Write\|NotebookEdit\|Bash` | Injects each binding decision not yet injected this session: number, status, title, summary, live `revisit-when`, path. For file tools the path is `tool_input.file_path`. For `Bash` the command string is tokenised and every token that resolves to a path under a managed root is looked up, a directory token with a trailing slash — so `cat`, a heredoc write, `git mv` and `rm` all deliver, closing the shell-read gap a path-scoped rule cannot. Each injection is labelled as the decisions binding those paths, not the corpus, and ends with the instruction to read `INDEX.md` before proposing an architectural or tooling change. The rows arrive alongside the tool's result, so a first-touch write has landed; what they precede is the next action. (`MultiEdit` no longer exists as a tool.) |
| `PostToolBatch` | — | Once per batch, after every parallel tool call in it has resolved. `reconcile --write` where a file tool in the batch wrote under `docs/adr/`, rooted at the root resolved from that path; `reconcile` otherwise, rooted at the working directory. Reports each finding **new since the baseline** once: a malformed ADR, two sharing a number, a stale index, a `scope` entry naming nothing — worded as a rename or deletion to act on: update `scope`, or ask whether the decision still binds anything and revisit it. Rename-agnostic: it inspects the tree, not the command. |
| `Stop`, `SubagentStop` | — | `reconcile`. Raises each open finding new since the baseline **once more**, as `additionalContext`, which on `Stop` continues the turn as non-error feedback (hooks reference, "Stop decision control"), so the agent acts before handing back. Silent when clean, and silent for a finding already raised here: a hook that re-raises until the finding closes makes deleting the entry the path of least resistance, and the tool cannot tell that from a considered removal. What the agent leaves open reaches the next session's baseline, and a human. A subagent's turn ends at `SubagentStop`, so its state is raised there. |

`PostToolBatch` rather than `PostToolUse` because hooks run in parallel for parallel tool
calls, so a per-tool reconcile would race itself on the state file and pay the Python start
several times per turn.

**Baseline and delta.** Findings present at `SessionStart` belong to the repository:
report them once and leave them to the human. Findings that arise in the session are the
agent's: once when they appear, once more at `Stop`. A finding is identified by its kind and
the offending value — the dangling entry, the shared number — with the ADR number carried
for display only, so neither a rename nor a renumber mints a new one. Where `new` creates
the corpus mid-session, no `SessionStart` ran: the baseline is empty.

**Session state** lives at `${CLAUDE_PLUGIN_DATA}/sessions/<session_id>.json`: the
baseline and the reported set keyed by managed root, and the injected rows keyed by agent
(`main`, or the `agent_id` of a subagent), so a subagent shares the session's baseline and
keeps its own context. Parallel `PreToolUse` hooks read and write it concurrently, so
every update takes an `fcntl` lock on a sidecar file, decides under it, and lands by atomic
rename. `SessionStart` prunes files older than thirty days, matching session retention. A
root first touched mid-session has no baseline until its first check, which snapshots one. Where `CLAUDE_PLUGIN_DATA` is unset (a `--plugin-dir` session) the
state goes under the system temp directory.

**Output bounds.** The harness caps hook output at 10,000 characters; the hook caps
injected rows at ten per event and names the rest by number and path.

### The skill: `SKILL.md`

The rewrite removes what the tool does and keeps what only judgement can do:

- **Goes:** "What this assumes" and the reference-implementation paragraph; the enforcement
  prose under Frontmatter Fields; the hand-edit steps the tool performs in Supersession,
  Discharge and Renumbering; "Never edit INDEX.md" as a warning, the index now being
  regenerated behind the agent.
- **Stays:** when an ADR is warranted; each section's job; Option 1 is always do-nothing;
  mutual exclusivity and the shared-cost paragraph; the `scope` test and the
  shallowest-true-set rule; archival defences and the path-scoped-rule section; linking
  rules; both Review passes; the judgement half of each workflow.
- **Changes:** every command becomes one `adr.py` line; `allowed-tools` pre-approves it.
  Where skill and tool encode the same thing — the Format template, the field names, the
  status pairing — a test in `tests/` fails when they drift (ADR 017).

### This repository

The tooling that becomes the plugin's is deleted here, and the repository consumes the
shipped copy: the first consumer, not a second implementation.

- `scripts/adr/` goes. The parser moves into the skill and `scripts/frontmatter.py`
  becomes a symlink to it, so `validate_manifests.py` imports it unchanged and there is one
  file (ADR 023). Its docstring names constraints, not ADR numbers, since it ships.
- `.githooks/pre-commit` calls `adr.py index` and `adr.py for` by path. It stays: the fast
  local aid ADR 005 welcomes, and the one route reaching a human committing from a shell.
- `pr.yml`: the `adr` job runs `adr.py check`; the `python` matrix gains
  `skills/writing-adrs`, the check ADR 005 requires of a skill that gains tooling; and one
  step runs the consumer recipe below against the checkout, so the recipe cannot rot
  unnoticed.
- Tests move to `skills/writing-adrs/tests/` under pytest, matching the matrix leg;
  `AGENTS.md`'s test-run line gains that leg. `pr.yml`'s `changes` job `case` arm that
  selects the matrix names `skills/writing-adrs/*` too, or the leg never runs.
- ADR 021 gains a `## Revisit watch` saying its trigger has not fired: session hooks exist
  and CI stays authoritative. That finding belongs there, not in a spec that gets deleted.

### Consumer CI

The plugin cache is not on any CI runner, so without a fetchable form the session hooks
would be every consumer's only check. `pyproject.toml` declares a `phx-adr` script entry
point and a build backend, so a consumer's CI runs

```
uvx --from 'git+https://github.com/todofixthis/phx-claude-siat@<tag>#subdirectory=skills/writing-adrs' phx-adr check
```

pinned to a release tag. The README carries the recipe. ADR 021's trigger — session hooks
taken as the authoritative check — is this repository's, scoped to `pr.yml`, and has not
fired here: CI stays the layer enforcement depends on (ADR 005).

### Decisions to record

Five ADRs, written with the skill during implementation, before the code:

1. **Ship the ADR tooling and session hooks with the `writing-adrs` skill** — inside `phx`,
   a stdlib tool plus plugin hooks; not a standalone plugin, not skill-frontmatter hooks
   alone. Fires ADR 017's trigger (a third skill ships tooling); the answer is that this
   skill's drift test is the template and field names, and the per-skill assertions still
   want no generalising.
2. **Let a shipped tool write what it wholly owns** — the index, frontmatter it validates,
   bytes derivable from a number — and never a sentence. Narrows ADR 017's "reports rather
   than edits". Records that the skill's parser copy reinstates a duplication ADR 011
   retired, and what holds it together.
3. **Resolve the repository root from the path in hand** — never from the launch
   directory. Discharges ADR 016's trigger (a script resolving a missing argument against
   the caller's checkout): right for a tool shipped to act on another tree, leaving ADR 016
   in force for `scripts/`.
4. **Deliver binding decisions by hook at first touch** — the `PreToolUse` injection,
   shell commands included. Supersedes ADR 019 on judgement, and records the displacement
   risk it accepts and the mitigation it relies on.
5. **Report findings by delta from a session baseline, and raise each at most twice** —
   the nag policy, isolated because it is the part most likely to be relitigated.

Scope updates in the same change: ADR 013 and ADR 019 drop `scripts/adr/`; new entries
name `hooks/` and `skills/writing-adrs/`.

## Data flow

```
agent edits docs/adr/022-foo.md
  → PostToolBatch → reconcile --write → INDEX.md regenerated ; findings: []

agent runs `git mv scripts/adr skills/writing-adrs`
  → PreToolUse(Bash)  → token scripts/adr → scripts/adr/ → 013, 019 injected (first touch)
  → PostToolBatch     → reconcile → finding: 013 scopes scripts/adr/, nothing matches
      → additionalContext: "ADR 013 … update scope, or revisit the decision" ; reported
agent ends the turn without acting
  → Stop → finding open → raised once more → turn continues
agent still leaves it
  → next session's SessionStart → baseline → reported to the human

agent Reads scripts/ci/versions.py
  → PreToolUse(Read) → for → 007, 011, 016 not yet injected → three rows ; state updated
agent later Edits the same file → nothing
```

## Error handling

- The tool exits 1 with every problem named against its file, and leaves the index as it
  found it. The hook never exits non-zero and never blocks a tool call.
- A hook exception is reported as context once per session, naming the traceback's last
  line and the path to `hook.py`.
- A path under no managed root binds nothing, silently: with root resolution from the
  path, that is the answer rather than an error.
- `renumber` refuses a number already claimed.

## Testing

- **Tool:** unit tests per subcommand against a fixture tree in a temp directory, ported
  from `scripts/adr/test_generate_index.py`; every existing case survives the move.
- **Hook:** one test per event with a synthetic stdin payload, asserting the exact
  `additionalContext` (and `systemMessage` at `SessionStart`) and the state file after;
  baseline-and-delta cases (baseline finding reported once; new finding reported at `PostToolBatch`, once more at `Stop`, then silent;
  nothing reported once fixed; a finding surviving a renumber unchanged); state across
  `compact`, `resume`, `fork` and `clear`; the same rows raised at `SubagentStop`;
  concurrent `PreToolUse` calls losing no update; Bash tokenising, directory tokens included; root resolution from a worktree path the agent has `cd`-ed into; the
  exception path; the inert path for an unmanaged `docs/adr/`.
- **Drift:** the Format block in `SKILL.md` equals the template `new` writes; every field
  name the skill documents exists in the tool; every `adr.py` command line in the skill
  matches the `allowed-tools` rule.
- **Mutation and analyst passes** per `.agents/rules/testing.md`.
- **End-to-end, run locally, not in `pr.yml`** (it needs a model): the goal scenario
  against a scratch repository with `claude --plugin-dir ./ -p`. No `docs/adr/` → hooks
  silent; a Nygard `docs/adr/` → still silent; first `new` → directory and index exist;
  edit a bound file → rows injected once; `git mv` a scoped path → finding reported, once
  more at `Stop`, then silent. The hook tests in CI stand in for it; the ADR records the
  run.

## Out of scope

- A configurable ADR directory.
- Windows without a POSIX shell.
- A Bash command naming paths under two managed roots: injection covers both, reconcile
  runs for the working directory's root only.
- Routing `docs/backlog/` items by path; reconcile is where it would attach, and that
  backlog item should say so.
