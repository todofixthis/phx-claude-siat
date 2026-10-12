# PyYAML Frontmatter and uv-Synced Hook Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse every ADR and skill frontmatter block with PyYAML's `CBaseLoader`, run the
writing-adrs tool and hooks from a uv-synced venv, and run every `scripts/` caller under
`uv run` — implementing ADRs 034 and 035 and closing
`docs/backlog/scripts-frontmatter-parser-should-use-pyyaml.md`.

**Worktree:** `/Users/phx/Documents/phx-claude-siat/.claude/worktrees/pyyaml-frontmatter`
(branch: `feature/pyyaml-frontmatter`, off `develop`)

**Architecture:** `frontmatter.py` keeps its line-level rules (one value per line, no block
scalar, no duplicate key, no whitespace in a key) and hands each accepted field — its key
line plus any `- item` lines under it — to PyYAML separately, so a YAML error names its
field and drops only that field. `adr.py` loses `yaml_hazard()` and instead writes each
value plain when it round-trips through the parser and double-quoted when it does not. Two
POSIX shell scripts ship beside the tool: `sync.sh` builds the venv (per plugin version
under `${CLAUDE_PLUGIN_DATA}/venvs/` in the plugin cache, the checkout's own workspace
venv, `${UV_PROJECT_ENVIRONMENT:-.venv}`, otherwise) and `adr.sh` is the skill's launcher. `hooks/hooks.json` computes the venv path
inline by parameter expansion and runs its `python` only once the venv is marked synced.

**Completed pre-work (committed before this plan):** `AGENTS.md`'s Python section and ADR
lookup command, `.agents/rules/testing.md`'s two commands, and the `releasing` skill's two
`scripts/` commands now give `uv run python -m …` (ADR 035), and `AGENTS.md` says how to
declare a `scripts/` dependency. Not repeated as tasks.

**Tech Stack:** Python ≥3.12, PyYAML 6.0.3 (libyaml), uv 0.12, POSIX `sh`, GitHub Actions.

**Spec:** `docs/adr/034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md`,
`docs/adr/035-run-repo-scripts-under-uv-with-declared-dependencies.md`, and the acceptance
list in `docs/backlog/scripts-frontmatter-parser-should-use-pyyaml.md`. Read all three.

## Global Constraints

- PyYAML is declared as `pyyaml>=6.0.3,<7` in both `skills/writing-adrs/pyproject.toml` and
  `scripts/pyproject.toml`, locked by the root `uv.lock` — never PEP 723, never vendored,
  never an optional import.
- Load with `yaml.CBaseLoader`, falling back to `yaml.BaseLoader` only where
  `yaml.__with_libyaml__` is false. Never a type-resolving loader: `yes`, `34` and
  `2026-10-08` stay strings.
- Per-event hooks never call `uv`. Venv path: `${CLAUDE_PLUGIN_DATA}/venvs/<version>` when
  the plugin root matches `*/plugins/cache/*`, `<version>` being the plugin root's last
  path component; otherwise the checkout's own workspace venv,
  `${UV_PROJECT_ENVIRONMENT:-.venv}` resolved against the plugin root when relative — a
  developer sharing one checkout between two OSes keeps one venv per OS that way.
- The marker file meaning "sync completed" is `<venv>/.phx-synced`. Every per-event hook
  exits 0 with no output unless the marker exists and `<venv>/bin/python` is executable.
- The cache-case sync: `uv sync --frozen --package writing-adrs --no-dev
  --no-install-project --quiet` with `UV_PROJECT_ENVIRONMENT` set to the venv and
  `--project` the plugin root. The checkout case adds `--inexact` and leaves
  `UV_PROJECT_ENVIRONMENT` as the developer set it (exporting the resolved path).
- Nothing creates an environment inside the plugin root when it is under the plugin cache.
- Hook-event p95 ceiling: 1.0 s over at least 20 timed events, `SessionStart` with its
  no-op sync included, the first (cold) sync excluded.
- The hooks stay POSIX-only; venv layout `bin/python`.
- Every `scripts/` invocation is `uv run python -m scripts.<area>.<name>` from the repo
  root; the suite is `uv run python -m unittest discover -s scripts -t . -p 'test_*.py'`.
- NZ English in prose, comments and identifiers; comments go on the line before the code
  they document. Every non-test function annotates its parameters and return type.
- Cite an ADR in a comment as `ADR NNN` plus what it forbids at that line; in an error
  message as `docs/adr/NNN`. Under `skills/`, name the constraint, since consumers have no
  `docs/adr/`.

## Review Focus

- **A hook firing during an interrupted sync** (python exists, PyYAML not installed, no
  marker): it must print nothing and exit 0 rather than report an import crash every
  event. Pinned in Task 3 (`test_a_venv_without_its_marker_keeps_every_hook_silent`).
- **Offline first session, or `uv` absent:** `SessionStart` says which in context, once;
  the other hooks stay silent. Pinned in Task 3 (`test_session_start_says_uv_is_missing`,
  `test_session_start_says_the_sync_failed_offline`).
- **A value a person hand-writes that YAML misreads** (`summary: Use X: not Y`, a scope
  entry opening with `{`, `summary: Issue #12 closes.` which YAML silently truncates at the
  comment, `!x y` or `&x y` which it reads as `y`): reported as a malformed field naming
  the key, the rest of the ADR still parsed. Pinned in Task 1
  (`test_reports_invalid_yaml_against_its_field`, `test_reports_an_inline_comment`,
  `test_reports_a_tag_anchor_or_alias`) and Task 2 (`test_reports_a_value_yaml_cannot_read`).
- **A value the tool writes that YAML would misread** (colon-space in `--summary`, a
  templated scope path, `--leaving "a: b"`): written quoted, so it reads back verbatim.
  Pinned in Task 2.
- **Two plugin versions in use at once:** each keeps its own venv, and pruning removes
  only a version whose cache directory is gone. Pinned in Task 3
  (`test_prunes_only_versions_gone_from_the_cache`).

---

### Task 1: Parse frontmatter values with PyYAML

**Files:**
- Modify: `skills/writing-adrs/frontmatter.py`
- Modify: `skills/writing-adrs/pyproject.toml` (declare PyYAML; replace the
  "No runtime dependencies on purpose" comment)
- Modify: `scripts/pyproject.toml` (declare PyYAML; replace the header comment's ADR 007
  and `python3 -m` claims with ADR 035's)
- Modify: `uv.lock` (by `uv lock`)
- Modify: `.githooks/pre-commit` — `uv run python skills/writing-adrs/adr.py index|for`
  and `uv run python -m scripts.backlog for`. Here rather than in Task 5: from this task on
  `frontmatter.py` imports `yaml`, so a bare-`python3` hook would refuse every ADR commit
  and fall silent on every lookup.
- Test: `skills/writing-adrs/tests/test_frontmatter.py`, `scripts/test_frontmatter.py` (the
  two files carry the same tests; keep them in step)

**Interfaces:**
- Produces: `parse_frontmatter(block: str) -> tuple[dict[str, str | list[str]], list[str]]`,
  signature unchanged. `LOADER` module constant (the loader class in use).

- [ ] **Step 1: Declare the dependency and lock**

Add `dependencies = ["pyyaml>=6.0.3,<7"]` to both `[project]` tables, then run
`uv lock && uv sync --locked` from the worktree root. Expected: exit 0, `uv.lock` gains
`pyyaml`.

- [ ] **Step 2: Write the failing tests** (in both test files)

```python
class YamlValueTests(unittest.TestCase):
    """Values PyYAML decides, which the line rules leave alone."""

    def test_unquotes_a_quoted_flow_sequence_entry(self):
        """A templated path must be quoted in YAML; the parsed entry carries no quotes."""
        fields, problems = parse_frontmatter(
            "scope: ['{{ cookiecutter.github_project_name }}/', docs/]"
        )
        self.assertEqual(
            fields, {"scope": ["{{ cookiecutter.github_project_name }}/", "docs/"]}
        )
        self.assertEqual(problems, [])

    def test_keeps_a_comma_inside_a_quoted_entry(self):
        fields, _ = parse_frontmatter('scope: ["a, b/", c/]')
        self.assertEqual(fields, {"scope": ["a, b/", "c/"]})

    def test_resolves_no_types(self):
        """BaseLoader: numbers, booleans and dates stay strings."""
        fields, _ = parse_frontmatter("a: 34\nb: yes\nc: 2026-10-08\nd: [12, 3]")
        self.assertEqual(fields, {"a": "34", "b": "yes", "c": "2026-10-08", "d": ["12", "3"]})

    def test_reports_invalid_yaml_against_its_field(self):
        """`: ` inside a plain value is a YAML error; only that field is lost."""
        fields, problems = parse_frontmatter("status: Accepted\nsummary: Use X: not Y")
        self.assertEqual(fields, {"status": "Accepted"})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field summary is not valid YAML"), problems)

    def test_reports_a_mapping_value(self):
        """An unquoted `{` opens a mapping, which no field here takes."""
        fields, problems = parse_frontmatter("scope: [{{ x }}/]")
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertIn("field scope", problems[0])

    def test_reports_an_inline_comment(self):
        """YAML drops ` #…` without a word, the silent truncation this module exists to catch."""
        for line in ("summary: Issue #12 closes.", "scope: [a/, b/] # note"):
            with self.subTest(line=line):
                fields, problems = parse_frontmatter(line)
                self.assertEqual(fields, {})
                self.assertEqual(len(problems), 1)
                self.assertIn("comment", problems[0])

    def test_reports_a_tag_anchor_or_alias(self):
        """`!x y` and `&x y` both load as `y`, dropping what was written."""
        for line in ("summary: !x y", "summary: &x y", "scope: [&a b/, *a]"):
            with self.subTest(line=line):
                fields, problems = parse_frontmatter(line)
                self.assertEqual(fields, {})
                self.assertEqual(len(problems), 1)

    def test_a_quoted_hash_is_text(self):
        fields, problems = parse_frontmatter('summary: "Issue #12 closes."')
        self.assertEqual((fields, problems), ({"summary": "Issue #12 closes."}, []))

    def test_loads_with_libyaml_where_available(self):
        import yaml

        self.assertIs(frontmatter.LOADER, yaml.CBaseLoader if yaml.__with_libyaml__ else yaml.BaseLoader)
```

Run `test_reports_an_inline_comment` and `test_reports_a_tag_anchor_or_alias` a second time
as subtests with `frontmatter.LOADER` patched to `yaml.BaseLoader` (`unittest.mock.patch.object`),
since CI's libyaml never exercises the fallback.

The `LOADER` test needs the module itself: add `import frontmatter` to the skill's test
file and `from scripts import frontmatter` to the scripts copy.

Flip the two existing tests YAML now decides differently:
`test_keeps_everything_after_the_first_colon` becomes
`test_a_colon_space_in_a_plain_value_is_a_problem` (fields `{}`, one problem starting
`field summary is not valid YAML`), and `test_allows_a_value_merely_starting_with_an_indicator`
becomes `test_quoting_a_value_starting_with_an_indicator_reads_it` (input
`summary: "> 25 ADRs and counting"` parses to `"> 25 ADRs and counting"`, no problems).
Every other existing test keeps its assertions: wraps, block scalars, duplicates (first
stands), whitespace keys, comments, block sequences, the bare key.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --directory skills/writing-adrs pytest tests/test_frontmatter.py -q`
Expected: the new tests FAIL (quotes kept, no YAML problems).

- [ ] **Step 4: Implement**

Keep the line pass exactly as it decides problems today, but have it collect, per
accepted field, the raw lines belonging to it (the key line plus its `- item` lines). Load
each field's lines with `yaml.load(text, Loader=LOADER)`. A `yaml.YAMLError` appends
`f"field {key} is not valid YAML; quote the value: {exc.problem}"` (fall back to `str(exc)`
when `problem` is absent) and drops the field. A loaded value that is neither `str` nor a
`list` of `str` appends `f"field {key} holds a {kind}, not text or a list of text; quote it"`
and drops the field. A field whose text holds an inline comment, a tag, an anchor or an
alias appends a problem saying which and to quote the value, and drops the field: scan the
field's text with `yaml.scan(text, Loader=LOADER)` — any `TagToken`, `AnchorToken` or
`AliasToken` is one, and so is non-blank text on a line after the last token ending on it,
which can only be a comment because the line pass already removed whole-line comments.
Skip `StreamStartToken`, `StreamEndToken` and `BlockEndToken` when finding where a line's
last token ends: the pure-Python scanner marks them at the end of a single-line input,
where libyaml marks them on the next line, so counting them hides a comment under the
fallback loader. `yaml.scan` raises `YAMLError` on what the load would, so it sits inside
the same `try`. A
bare key with nothing under it loads as `""`, unchanged. Rewrite the
module docstring: the line rules are this repository's own, stricter than YAML; values are
YAML's, decided by PyYAML; drop the standard-library claim.

- [ ] **Step 5: Run every parser test and the corpus**

Run: `uv run --directory skills/writing-adrs pytest -q && uv run python -m unittest discover -s scripts -t . -p 'test_*.py'`
Expected: frontmatter tests PASS. `test_adr.py` tests on `yaml_hazard` may fail until Task
2; nothing else may.

- [ ] **Step 6: Verify the pre-commit hook**

Run: `git config core.hooksPath .githooks && f=docs/adr/034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md && echo >> "$f" && git add "$f" && sh .githooks/pre-commit; echo "exit $?"; git restore --staged "$f" docs/adr/INDEX.md && git checkout -- "$f" docs/adr/INDEX.md`
Expected: `exit 0`, after the decisions binding that ADR; the tree is clean afterwards.

- [ ] **Step 7: Commit**

Run `git status` to catch any related unstaged or untracked files (e.g. lock files after dependency changes), then use the `creative-commits` skill.

### Task 2: Write values YAML reads back verbatim; drop `yaml_hazard()`

**Files:**
- Modify: `skills/writing-adrs/adr.py` (remove `RE_YAML_INDICATOR`, `yaml_hazard()`, the
  hazard loop in `parse_adr`, the hazard and comma refusals in `new_adr`; add
  `yaml_value`; `render_new` and `set_fields` render through it; `renumber`, which today
  hands `set_fields` pre-formatted `"[2, 4]"` strings, passes a list where the original
  field was one; rewrite the module docstring's standard-library and `python3` lines, and
  the `PYTHON_FLOOR` comment's "whatever python3 they have", to name the launcher and
  `phx-adr`)
- Test: `skills/writing-adrs/tests/test_adr.py`

**Interfaces:**
- Consumes: `parse_frontmatter` (Task 1).
- Produces: `yaml_value(value: str, in_flow: bool = False) -> str` — `value` plain when
  `parse_frontmatter` reads it back unchanged in that context (`k: <v>` or `k: [<v>]`),
  else `json.dumps(value, ensure_ascii=False)`, a valid YAML double-quoted scalar.
  `set_fields(content: str, updates: dict[str, str | list[str] | None]) -> str` — a
  `list` renders as a flow sequence of `yaml_value(entry, in_flow=True)`.

- [ ] **Step 1: Write the failing tests**

Replace `test_rejects_a_value_a_yaml_reader_takes_as_a_mapping`,
`test_rejects_a_value_opening_with_a_yaml_indicator`,
`test_rejects_a_value_a_yaml_reader_takes_as_a_comment` (its case moves to the parser's
inline-comment problem, asserted through `parse_adr`),
`test_rejects_a_value_ending_in_a_colon`,
`test_refuses_a_summary_a_yaml_reader_would_misread`,
`test_refuses_a_scope_entry_a_yaml_reader_would_misread` and
`test_refuses_a_scope_entry_holding_a_comma` with:

- `test_reports_a_value_yaml_cannot_read` — `parse_adr` on an ADR whose summary line is
  `summary: Use X: not Y` reports one problem containing `field summary is not valid YAML`;
  a subtest with `summary: Issue #12 closes.` reports one problem containing `comment`.
- `test_new_quotes_a_summary_yaml_would_misread` — `new_adr(... summary="Use X: not Y #1")`
  then `parse_adr` of the file returns that summary verbatim and no problems; the written
  line is `summary: "Use X: not Y #1"`.
- `test_new_writes_a_templated_scope_entry_for_reads_back` — the backlog's regression: the
  fixture root holds directory `{{ cookiecutter.github_project_name }}/`; `new_adr(...,
  scope=["{{ cookiecutter.github_project_name }}/"])` succeeds, `check` finds nothing, and
  `binding(root, ["{{ cookiecutter.github_project_name }}/README.md"])` returns that ADR.
- `test_parses_a_hand_quoted_templated_scope_entry` — an ADR written by hand with
  `scope: ["{{ cookiecutter.github_project_name }}/"]` parses with no problems and `for`
  matches a path under it.
- `test_new_accepts_a_comma_in_a_scope_entry` — directory `a, b/` exists; `new` writes it
  quoted and it reads back as one entry.
- `test_discharge_quotes_a_leaving_condition` — `discharge(..., leaving="Revisit: when X")`
  reads back verbatim.
- `test_yaml_value_leaves_plain_prose_plain` — `yaml_value("Ship it, then measure")` is
  unchanged; `yaml_value("a, b/", in_flow=True)` is `'"a, b/"'`.

- `test_renumber_keeps_a_discharged_by_list_a_list` — the existing assertion at
  `test_adr.py`'s `revisit-discharged-by: [2, 4]` case still holds.

Keep `test_accepts_prose_with_yaml_indicators_mid_value` and the line-break refusals; the
scope line-break refusal's message and its tests drop "a comma or".

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run --directory skills/writing-adrs pytest tests/test_adr.py -q`
Expected: the new tests FAIL (`yaml_hazard` refuses, `yaml_value` undefined).

- [ ] **Step 3: Implement** per the Interfaces block. `discharge` passes
`[*spent, str(new)]` as a list rather than formatting the brackets itself; `supersede`
passes `str(new)`. `render_new` renders `scope` through the same list path as
`set_fields`.

- [ ] **Step 4: Run the skill suite and the real corpus**

Run: `uv run --directory skills/writing-adrs pytest -q && uv run python skills/writing-adrs/adr.py check`
Expected: all PASS; `check` exits 0.

- [ ] **Step 5: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

### Task 3: Sync the venv and run the hooks from it

**Files:**
- Create: `skills/writing-adrs/sync.sh`, `skills/writing-adrs/adr.sh`
- Modify: `hooks/hooks.json`, `scripts/ci/validate_manifests.py` (`HOOK_INVOCATION`, its
  comment and docstring), `scripts/ci/test_validate_manifests.py`
- Test: `skills/writing-adrs/tests/test_env.py` (new)

**Interfaces:**
- Produces: `sh sync.sh DATA_DIR [--if-needed]` — prints the venv's `bin/python` path on
  stdout and exits 0 once the venv is synced and marked; with `--if-needed` returns
  straight away where the marker exists; exits non-zero with a reason on stderr where `uv`
  is missing, `DATA_DIR` is empty in the cache case, or the sync fails. `uv`'s own output
  goes to stderr, so stdout carries only the python path. A full sync removes the marker
  before `uv sync` and writes it only once the sync succeeds, so an interrupted re-sync —
  the checkout case after a lock change — never leaves a stale marker over a half-updated
  venv. Resolves the plugin
  root as its own directory's grandparent by logical `pwd` (ADR 027's anchor), never from
  `CLAUDE_PLUGIN_ROOT`. In the cache case, after a successful sync, removes each
  `DATA_DIR/venvs/<v>` other than the version just synced whose `${root%/*}/<v>` directory
  is gone — the parent taken by trimming the string, never by `..`, which the kernel
  resolves physically through a symlinked version directory.
- Produces: `sh adr.sh DATA_DIR COMMAND [ARGS…]` — runs `sync.sh DATA_DIR --if-needed`,
  then `exec`s `adr.py` on the printed python; where the sync fails, prints
  `Error: the writing-adrs tool could not build its environment: …` naming `uv` and the
  network, and exits 3 — distinct from argparse's 2 for a bad flag and `adr.py`'s 1 for a
  refusal.
- Produces: `HOOK_INVOCATION = '"$p" "${CLAUDE_PLUGIN_ROOT}/skills/writing-adrs/hook.py"'`
  in `validate_manifests.py`; every hooks.json command ends with it.

hooks.json commands keep today's `INDEX.md` gate first. Every event but `SessionStart`
then runs:

```sh
r="${CLAUDE_PLUGIN_ROOT}"; r="${r%/}"; case "$r" in */plugins/cache/*) v="${CLAUDE_PLUGIN_DATA}/venvs/${r##*/}" ;; *) v="${UV_PROJECT_ENVIRONMENT:-.venv}"; case "$v" in /*) ;; *) v="$r/$v" ;; esac ;; esac; p="$v/bin/python"; [ -f "$v/.phx-synced" ] && [ -x "$p" ] || exit 0; "$p" "${CLAUDE_PLUGIN_ROOT}/skills/writing-adrs/hook.py"
```

`r` is assigned from the literal `${CLAUDE_PLUGIN_ROOT}` first and trimmed second, so this
works whether the harness substitutes the text or exports the variable.

`SessionStart` (timeout raised from 20 to 120) runs, after the gate:

```sh
command -v uv >/dev/null 2>&1 || { printf '%s' '<needs-uv JSON>'; exit 0; }; p=$(sh "${CLAUDE_PLUGIN_ROOT}/skills/writing-adrs/sync.sh" "${CLAUDE_PLUGIN_DATA}" </dev/null 2>/dev/null) || { printf '%s' '<sync-failed JSON>'; exit 0; }; "$p" "${CLAUDE_PLUGIN_ROOT}/skills/writing-adrs/hook.py"
```

The two JSON messages are `hookSpecificOutput` `SessionStart` `additionalContext`:
"phx:writing-adrs hooks need uv on PATH; the ADR corpus checks are off until it is
installed." and "phx:writing-adrs could not build its Python environment with uv (offline
on a first session?); the ADR corpus checks are off for this session."

- [ ] **Step 1: Write the failing tests** in `test_env.py`

Every test builds a plugin tree in a temp dir by copying the root `pyproject.toml`,
`uv.lock`, `.claude-plugin/plugin.json`, each workspace member's `pyproject.toml`, and the
whole `skills/writing-adrs/` minus `.venv*`, `__pycache__` and `tests/`. The cache layout
is `<tmp>/plugins/cache/phx-claude-siat/phx/<version>/`; the checkout layout is
`<tmp>/checkout/`. A helper runs a hooks.json command by event name via `sh -c` with
`CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR` (a fixture repo whose
`docs/adr/INDEX.md` is generated by `adr.py index`, so the gate passes) and the event JSON
on stdin, under a 120 s timeout. Every subprocess `test_env.py` starts — the hooks
helper and the direct `sync.sh` and `adr.sh` calls alike — goes through one environment
builder that removes `UV_PROJECT_ENVIRONMENT` and `VIRTUAL_ENV` unless the test sets them: the developer's own
values, or the ones `uv run` sets for pytest, would otherwise redirect the checkout case.
Tests that sync need the network or a warm uv cache.

- `test_sync_builds_a_version_venv_under_plugin_data` — cache layout 1.0.0: `sync.sh`
  exits 0, prints `DATA/venvs/1.0.0/bin/python`, the marker exists, that python imports
  `yaml`, and no `.venv` exists under the plugin root.
- `test_prunes_only_versions_gone_from_the_cache` — cache dirs 1.0.0 and 0.9.0 exist;
  `DATA/venvs/0.9.0` and `DATA/venvs/0.8.0` pre-exist; syncing 1.0.0 keeps 0.9.0, removes
  0.8.0. A subtest repeats it with the 1.0.0 version directory a symlink to a plugin tree
  elsewhere: `DATA/venvs/1.0.0` and its marker survive.
- `test_checkout_sync_creates_the_workspace_venv_inexactly` — checkout layout,
  `UV_PROJECT_ENVIRONMENT` unset: `sync.sh` creates `<checkout>/.venv` and marks it. Then a
  fake distribution `keepme-1.0.dist-info` with `METADATA`, `INSTALLER` and a `RECORD`
  listing all three files goes into site-packages, and a second sync leaves
  `importlib.metadata.version("keepme")`, run in the venv's python, at `"1.0"`. Confirm
  this test goes red with `--inexact` removed from `sync.sh` before trusting it.
- `test_checkout_sync_honours_the_developers_venv_name` — `UV_PROJECT_ENVIRONMENT=.venv.dev`:
  the venv and marker land in `<checkout>/.venv.dev`, nothing in `<checkout>/.venv`, and
  the `PreToolUse` command reaches it.
- `test_session_start_runs_the_hook_from_the_synced_venv` — empty DATA, cache layout:
  `SessionStart` prints the standing-note JSON; a following `PreToolUse` `Read` of a
  scoped path prints `Decisions binding`.
- `test_session_start_says_uv_is_missing` — `PATH` a temp bin of symlinks to `sh`, `head`,
  `grep` only: output contains `need uv on PATH`; `PreToolUse` prints nothing, exits 0.
- `test_session_start_says_the_sync_failed_offline` — `UV_OFFLINE=1`, `UV_CACHE_DIR` an
  empty temp dir, `UV_PYTHON_DOWNLOADS=never`: output contains `could not build`; marker
  absent.
- `test_a_venv_without_its_marker_keeps_every_hook_silent` — `DATA/venvs/1.0.0/bin/python`
  an executable stub script that prints `CALLED` and exits 1, no marker: `PreToolUse`,
  `PostToolBatch`, `Stop`, `SubagentStart`, `SubagentStop` each print nothing and exit 0.
- `test_launcher_bootstraps_a_repository_without_adrs` — empty git repo, empty DATA:
  `sh adr.sh DATA --repo-root <repo> new "First decision" --summary "S." --no-scope` exits
  0 and writes `docs/adr/001-first-decision.md`.

In `test_validate_manifests.py`, the existing hooks tests use the new `HOOK_INVOCATION`;
add one asserting the real `hooks/hooks.json` passes.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run --directory skills/writing-adrs pytest tests/test_env.py -q`
Expected: FAIL — `sync.sh` missing.

- [ ] **Step 3: Implement** `sync.sh`, `adr.sh`, the hooks.json commands and
`HOOK_INVOCATION` per the Interfaces block. Both scripts `set -u`, quote every expansion,
and export `UV_PROJECT_ENVIRONMENT` as the resolved venv path in both layouts, so `uv`
and the hooks agree on one path.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --directory skills/writing-adrs pytest -q && uv run python -m scripts.ci.validate_manifests && uv run python -m unittest discover -s scripts -t . -p 'test_*.py'`
Expected: PASS, exit 0.

- [ ] **Step 5: Lint and format**

Run: `uv run --directory skills/writing-adrs ruff check . && uv run --directory skills/writing-adrs black --check .`
Expected: exit 0.

- [ ] **Step 6: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

### Task 4: Point the skill at the launcher

**Files:**
- Modify: `skills/writing-adrs/SKILL.md` (every `python3 ${CLAUDE_SKILL_DIR}/adr.py`
  command; the "no `python3`" failure sentence; the `## Frontmatter Fields` lead
  paragraph)
- Modify: `skills/writing-adrs/tests/test_skill_drift.py` (`RE_COMMAND_LINE` and the
  inline regex in `test_every_flag_a_command_line_names_is_an_option_of_its_subcommand`)

**Interfaces:**
- Consumes: `adr.sh` (Task 3). Command form, everywhere:
  `` `sh "${CLAUDE_SKILL_DIR}/adr.sh" "${CLAUDE_PLUGIN_DATA}" <command> …` ``

- [ ] **Step 1: Change the drift regexes first** to match only the new form, and add
`test_no_command_line_uses_bare_python3`, asserting `python3 ${CLAUDE_SKILL_DIR}` appears
nowhere in SKILL.md.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --directory skills/writing-adrs pytest tests/test_skill_drift.py -q`
Expected: FAIL ("the skill names no adr.py command").

- [ ] **Step 3: Rewrite SKILL.md.** Commands take the new form. The tool cannot run at all
when `uv` is missing or the launcher exits 3. The Frontmatter Fields lead keeps the
one-line rule and its reason, drops the "starts with a word, holds no `: `" rule, and says
instead: values are YAML, as GitHub reads them; a value YAML would misread — opening with a
YAML indicator (`` ` `` `"` `'` `[` `{` `&` `*` `!` `|` `>` `%` `@` `#` `,`, or `- ` or `? `), or holding
`: ` or ` #` — goes in double quotes; the tool's
own commands quote what they write, and `check` reports a value YAML cannot read.

- [ ] **Step 4: Run the skill suite**

Run: `uv run --directory skills/writing-adrs pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

### Task 5: Run every `scripts/` and `adr.py` caller under uv

**Files:**
- Modify: `.github/workflows/pr.yml` (`adr` job: move the existing `setup-uv` step above "Check the ADR corpus and index" —
  the consumer-recipe `uvx` step stays after it — then
  `uv run python skills/writing-adrs/adr.py check`; `manifests` job: `setup-uv`, then its
  three steps as `uv run python -m …`)
- Modify: `.github/workflows/release.yml` (a pinned `astral-sh/setup-uv` step — same digest
  and `# v10.3.0` comment as `pr.yml` — before "Read the version and build the release
  notes", which runs `uv run python -m scripts.ci.release_notes --out notes.md`)
- Modify: `scripts/dev/mutate.py` (`DEFAULT_TEST_COMMAND` starts `"uv", "run", "python"`;
  docstring)
- Modify: the docstrings citing ADR 007/011 or giving `python3 -m`:
  `scripts/backlog.py`, `scripts/ci/release_notes.py`, `scripts/ci/versions.py`,
  `scripts/ci/validate_manifests.py`, `scripts/ci/test_release_notes.py`,
  `scripts/ci/test_validate_manifests.py`, `scripts/dev/test_mutate.py`,
  `scripts/test_frontmatter.py`

- [ ] **Step 1: Make the edits.** Find stragglers with
`rg -n 'python3|ADR 007|ADR 011|[Ss]tdlib|[Ss]tandard library' scripts .githooks .github`;
every remaining hit must be a child-process stand-in in a test (`test_mutate.py`'s
`("python3", "-c", …)` commands import nothing) or a correct statement.

- [ ] **Step 2: Verify the workflows parse**

Run: `uv run python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/pr.yml .github/workflows/release.yml && uv run python -m scripts.ci.validate_manifests`
Expected: exit 0.

- [ ] **Step 3: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

### Task 6: Gate the hook-event p95 in `pr.yml`

**Files:**
- Create: `scripts/ci/time_hooks.py`, `scripts/ci/test_time_hooks.py`
- Modify: `.github/workflows/pr.yml` (a step in the `adr` job, after `setup-uv`:
  `uv run python -m scripts.ci.time_hooks`)

**Interfaces:**
- Produces: `CEILING_SECONDS = 1.0`, `DEFAULT_EVENTS = 24`, `TIMING_VERSION = "0.0.0-timing"`,
  `marker_path(data_dir: Path) -> Path` (the tests build the marker through it, never a
  repeated literal),
  `time_hooks(hooks_file: Path, plugin_root: Path, data_dir: Path, project_dir: Path, events: int) -> dict[str, list[float]]`
  (seconds per event name), `p95(samples: list[float]) -> float` (nearest-rank),
  `main(argv: list[str]) -> int` — `--hooks-file`, `--events`, `--ceiling` and
  `--data-dir` (default a fresh temp dir) overridable for the tests, which pre-create the
  marker through `--data-dir`. `main` builds a cache-layout plugin root (`<tmp>/plugins/cache/phx-claude-siat/phx/0.0.0-timing`, a symlink to the repo root),
  runs one untimed `SessionStart` (the cold sync), then times `events` events cycling
  `SessionStart`, `PreToolUse` (a `Read` cycling through several scoped paths —
  `AGENTS.md`, `hooks/hooks.json`, `scripts/ci/versions.py`, `skills/writing-adrs/adr.py`,
  `.githooks/pre-commit`, `docs/adr/INDEX.md` — so each is a first touch that injects
  rows), `PostToolBatch`, `Stop`, one
  session id throughout, `CLAUDE_PROJECT_DIR` and `cwd` the repo root. Prints count, mean
  and p95 per event and overall; exits 1 where the overall p95 exceeds the ceiling, and
  also unless `<data_dir>/venvs/0.0.0-timing/.phx-synced` exists both after the untimed
  `SessionStart` and after the run — a failed or pruned sync leaves every other hook
  exiting at the marker gate in milliseconds, which would pass the ceiling while timing
  nothing.

- [ ] **Step 1: Write the failing tests**

- `test_p95_is_nearest_rank` — `p95([float(i) for i in range(1, 21)]) == 19.0`.
- `test_a_slow_hook_fails_the_ceiling` — a fixture hooks.json whose every command is
  `sleep 0.3`, `--ceiling 0.2 --events 4`: `main` returns 1.
- `test_a_fast_hook_passes` — commands `true`, same flags: returns 0.
- `test_an_unsynced_venv_fails_the_timing` — commands `true`, marker never created:
  returns 1.
- `test_a_marker_lost_during_the_run_fails_the_timing` — marker pre-created, the fixture's
  `Stop` command `rm -f "${CLAUDE_PLUGIN_DATA}/venvs/0.0.0-timing/.phx-synced"`, every other
  command `true`: returns 1. This pins the after-run check, which the test above cannot.

The `sleep` and `true` fixtures pre-create the marker, so only the ceiling decides them.
- `test_times_at_least_twenty_events_by_default` — `DEFAULT_EVENTS >= 20`.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run python -m unittest scripts.ci.test_time_hooks -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement** per the Interfaces block; stdin JSON per event built from the
fields `hook.py` reads (`hook_event_name`, `session_id`, `cwd`, `source`, `tool_name`,
`tool_input`, `tool_calls`).

- [ ] **Step 4: Run against the real hooks**

Run: `uv run python -m unittest scripts.ci.test_time_hooks -v && uv run python -m scripts.ci.time_hooks`
Expected: tests PASS; the real run prints its table and exits 0. Keep the output for Task 8.

- [ ] **Step 5: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

### Task 7: Correct the human-facing docs

**Files:**
- Modify: `README.md` (`writing-adrs` needs `uv` on `PATH`, not `python3`; the venv is built
  per plugin version at session start; the dev commands at the foot use `uv run`)
- Modify: `docs/writing-adrs-hooks.md` (the gate diagram's `python3 on PATH?` node becomes
  the uv/synced-venv gate; the "No `python3`" failure mode becomes "No `uv`", "Offline
  first session" and "Interrupted sync")
- Modify: `docs/backlog/writing-adrs-allowed-tools-grant.md` (the command it quotes takes
  the launcher form)

- [ ] **Step 1: Make the edits**, then run
`rg -n 'python3' README.md docs/writing-adrs-hooks.md docs/backlog/` — remaining hits only
in the `nz-english` sections, which still run on `python3`, and
`docs/backlog/verify-the-adr-hook-on-a-forked-session.md`'s `python3 -c 'import tempfile…'`,
which prints a path and imports nothing of ours.

- [ ] **Step 2: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

### Task 8: Measure, record, and close out

**Files:**
- Modify: `docs/adr/034-run-the-adr-tool-from-a-uv-synced-plugin-environment.md` (new
  `## Revisit watch` section, after Consequences, before the link definitions)
- Delete: `docs/backlog/scripts-frontmatter-parser-should-use-pyyaml.md`,
  this plan file

- [ ] **Step 1: Measure the turn.** From this repository's transcripts under
`~/.claude/projects/-Users-phx-Documents-phx-claude-siat/` — main session files and
`*/subagents/*.jsonl` alike, more than one session — compute, with ADR 034's definition of
a turn (from one tool-calling assistant message to the next, parallel calls counted once):
the median and mean turn, and the mean hook events a turn (a `PreToolUse` per matched
call, a `PostToolBatch` a batch). Do it with a script in the scratchpad, not the repo, and
quote its command and the sessions and turn counts it covered in the entry, so a later
re-measurement can repeat it.

- [ ] **Step 2: Write the Revisit watch entry**, dated, with: Task 6's mean and p95 per
event, the measured median turn and events a turn, and mean cost a turn as a share of the
median turn against the 5% bound. Run `uv run python skills/writing-adrs/adr.py check`;
expected exit 0.

- [ ] **Step 3: Hand the human the real-session checks**, which need a session launched
with `--plugin-dir` pointed at this worktree: an empty `${CLAUDE_PLUGIN_DATA}` builds the
venv at `SessionStart` and the hooks inject; with `uv` off `PATH` `SessionStart` says so;
`adr.sh new` bootstraps in a repository with no `docs/adr/`. Record their results in the
pull-request description.

- [ ] **Step 4: Run every check one last time**

Run: `uv sync --locked && uv run python -m unittest discover -s scripts -t . -p 'test_*.py' && for s in skills/creative-commits skills/nz-english skills/writing-adrs; do uv run --directory "$s" pytest -q || exit 1; done && uv run python skills/writing-adrs/adr.py check && uv run python -m scripts.ci.validate_manifests`
Expected: exit 0.

- [ ] **Step 5: Delete the backlog item and this plan, then commit**

`git rm docs/backlog/scripts-frontmatter-parser-should-use-pyyaml.md docs/superpowers/plans/2026-10-09-pyyaml-frontmatter.md`.
Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

## Intentional Decisions

*(Populated during review — reviewers must not re-raise these)*

- **SKILL.md is a task, not pre-work.** It is the shipped product, and `test_skill_drift.py`
  couples its command lines to the tool; committing the launcher form before `adr.sh`
  exists would break that test on every intermediate commit.
- **The tool quotes values rather than refusing them.** ADR 023 lets it write text the
  agent passed verbatim; quoting is syntax around a verbatim value, and it is what lets
  `new --scope` take a templated path at all.
- **`.agents/rules/testing.md` was corrected in the pre-work** though ADR 035's
  Consequences do not list it: `AGENTS.md` sends agents there, and it gave bare `python3`.
- **No `--locked` on the `uv run` callers.** Every caller keeps ADR 035's exact form; a
  stale lock is `pr.yml`'s `uv lock --check` to catch.
- **One `SessionStart` failure message covers an empty `${CLAUDE_PLUGIN_DATA}`.** The
  harness sets it for every plugin, so a distinct exit code and message would guard a case
  that does not arise.
- **Task 1 may leave `test_adr.py`'s hazard tests red until Task 2.** They assert
  `yaml_hazard()`'s messages, which Task 2 removes; splitting the parser from the writer
  keeps each task's review focused.
- **Execute with the plugin from the cache or the main checkout, not `--plugin-dir` on this
  worktree,** until Task 3 lands: from Task 1 on, the worktree's hooks would import `yaml`
  under bare `python3` and fail every event.

## Self-Review Checklist

- [x] Does the plan header include a `**Worktree:**` field naming the existing worktree and branch?
- [x] Does every commit step remind the agent to run `git status` first?
- [x] Does the plan include an Intentional Decisions section?
- [x] Does the final task delete the plan file?
