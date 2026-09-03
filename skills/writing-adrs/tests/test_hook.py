"""Tests for `hook.py` — one per event, plus state, baseline-and-delta and concurrency.

Each test feeds `handle()` a synthetic event as Claude Code would send it and asserts the
exact JSON returned and the state file left behind. Roots are fixture trees passed by
path; nothing here reads the working directory.
"""

import fcntl
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import hook
from adr import ADR_DIR, INDEX_FILENAME
from tests.test_adr import SCOPED_FILE, RepoTestCase, adr_text


class HookTestCase(RepoTestCase):
    """A managed fixture corpus with one decision, plus a state directory.

    `cwd` is the directory the events claim to run in; a subclass points it at a second
    corpus to cover a session whose working directory is not the outer repository.
    """

    def setUp(self) -> None:
        super().setUp()
        self.write("001-first.md", adr_text(**{"revisit-when": "A condition."}))
        self.manage()
        self.cwd = self.repo_root
        self.state_dir = self.repo_root / "state"
        self.session = "sess-1"

    def event(self, name: str, **fields) -> dict:
        """A hook event with the common fields filled."""
        return {
            "cwd": str(self.cwd),
            "hook_event_name": name,
            "session_id": self.session,
        } | fields

    def injected_key(self, number: str, root: Path | None = None) -> str:
        """The key one injected row is remembered by: its root and its number."""
        return f"{root or self.repo_root}:{number}"

    def handle(self, name: str, **fields) -> dict | None:
        return hook.handle(self.event(name, **fields), self.state_dir, now=1_000.0)

    def context(self, result: dict | None) -> str:
        return "" if result is None else result["hookSpecificOutput"]["additionalContext"]

    def state(self) -> dict:
        return json.loads(
            (self.state_dir / hook.STATE_SUBDIR / f"{self.session}.json").read_text(
                encoding="utf-8"
            )
        )

    def dangle(self) -> None:
        """Delete the scoped file, so 001's scope entry dangles."""
        (self.repo_root / SCOPED_FILE).unlink()


class PathsInCommandTests(unittest.TestCase):
    """Unit tests for ``paths_in_command()``: which tokens of a shell command name a path."""

    def setUp(self) -> None:
        self.cwd = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.cwd / SCOPED_FILE).write_text("", encoding="utf-8")
        (self.cwd / "docs").mkdir()

    def test_finds_a_path_named_in_a_here_doc_body(self):
        """A here-doc body is tokenised like the rest of the command, so a path in one binds."""
        command = f"cat <<'EOF' > docs/notes.md\nSee {SCOPED_FILE}\nEOF"
        self.assertIn(self.cwd / SCOPED_FILE, hook.paths_in_command(command, self.cwd))

    def test_falls_back_to_a_whitespace_split_on_an_unbalanced_quote(self):
        """An apostrophe opens a quote shlex never sees closed, and the paths must survive it."""
        command = f"echo don't > {SCOPED_FILE}"
        self.assertIn(self.cwd / SCOPED_FILE, hook.paths_in_command(command, self.cwd))

    def test_returns_a_redirect_target_whose_parent_exists(self):
        """A file the command is about to create binds whatever covers the directory it lands in."""
        self.assertEqual(
            hook.paths_in_command("cat > docs/new.md", self.cwd), [self.cwd / "docs" / "new.md"]
        )

    def test_a_parent_or_root_token_reaches_no_managed_corpus(self):
        """`..` and `/` are paths that exist, and neither resolves to a corpus this tool manages."""
        found = hook.paths_in_command("ls .. /", self.cwd)
        self.assertEqual([hook.managed_root_for(path) for path in found], [None, None])


class SessionStartTests(HookTestCase):
    """SessionStart: the standing note, the baseline, and what each source does to state."""

    def test_injects_the_standing_note_with_the_count(self):
        """The note names the decisions in force and the index to read."""
        result = self.handle("SessionStart", source="startup")
        text = self.context(result)
        self.assertIn("1 decision", text)
        self.assertIn("docs/adr/INDEX.md", text)
        self.assertIn("phx:writing-adrs", text)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_reports_baseline_findings_to_agent_and_human_once(self):
        """A pre-existing finding lands in additionalContext and systemMessage, and in the baseline."""
        self.dangle()
        result = self.handle("SessionStart", source="startup")
        self.assertIn("README.md", self.context(result))
        self.assertIn("README.md", result["systemMessage"])
        self.assertEqual(
            self.state()["roots"][str(self.repo_root)]["baseline"], ["dangling:README.md"]
        )
        again = self.handle("SessionStart", source="resume")
        self.assertNotIn("README.md", self.context(again))

    def test_compact_resets_injected_and_keeps_the_baseline(self):
        """After compaction the rows must be injected again; the baseline value is unchanged.

        The fixture dangles first, so the baseline holds a finding: an empty one would
        compare equal to the reset a mistaken `compact` would perform.
        """
        self.dangle()
        self.handle("SessionStart", source="startup")
        self.handle(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
        )
        self.assertEqual(self.state()["injected"][hook.MAIN_AGENT], [self.injected_key("001")])
        self.handle("SessionStart", source="compact")
        self.assertEqual(self.state()["injected"], {})
        self.assertEqual(
            self.state()["roots"][str(self.repo_root)]["baseline"], ["dangling:README.md"]
        )

    def test_clear_starts_fresh(self):
        """`clear` discards the state file and snapshots anew."""
        self.dangle()
        self.handle("SessionStart", source="startup")
        (self.repo_root / SCOPED_FILE).write_text("", encoding="utf-8")
        result = self.handle("SessionStart", source="clear")
        self.assertEqual(self.state()["roots"][str(self.repo_root)]["baseline"], [])
        self.assertNotIn("README.md", self.context(result))

    def test_is_silent_for_an_unmanaged_root(self):
        """A docs/adr the tool does not manage gets nothing at all."""
        (self.adr_dir / INDEX_FILENAME).write_text("# hand-written\n", encoding="utf-8")
        self.assertIsNone(self.handle("SessionStart", source="startup"))


class SubagentStartTests(HookTestCase):
    """SubagentStart: the note only."""

    def test_injects_the_note_and_touches_no_baseline(self):
        result = self.handle("SubagentStart", agent_id="agent-1", agent_type="Explore")
        self.assertIn("docs/adr/INDEX.md", self.context(result))
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SubagentStart")


class PreToolUseTests(HookTestCase):
    """PreToolUse: rows at first touch, once per agent, for file tools and shell commands."""

    def test_injects_binding_rows_once_for_a_file_tool(self):
        """The first Read of a bound file carries the row; the second carries nothing."""
        first = self.handle(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
        )
        text = self.context(first)
        self.assertIn("001 (Accepted): Do the thing", text)
        self.assertIn("A condition.", text)
        self.assertIn("binding", text)
        self.assertIn("INDEX.md", text)
        second = self.handle(
            "PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
        )
        self.assertIsNone(second)

    def test_a_subagent_gets_its_own_first_touch(self):
        """Rows injected for the main thread are injected again for a subagent."""
        self.handle(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
        )
        result = self.handle(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
            agent_id="agent-1",
        )
        self.assertIn("001", self.context(result))
        self.assertEqual(
            self.state()["injected"],
            {
                "agent-1": [self.injected_key("001")],
                hook.MAIN_AGENT: [self.injected_key("001")],
            },
        )

    def test_tokenises_a_shell_command(self):
        """A path named in a command, quoted or bare, delivers; a directory matches its prefix."""
        self.write_scoped("scripts/adr/x.py")
        self.write(
            "002-second.md", adr_text(title="2: Do another thing", scope="[scripts/adr/]")
        )
        self.manage()
        result = self.handle(
            "PreToolUse",
            tool_name="Bash",
            tool_input={"command": "git mv 'scripts/adr' skills/writing-adrs && cat README.md"},
        )
        text = self.context(result)
        self.assertIn("001", text)
        self.assertIn("002", text)

    def test_a_path_under_no_managed_root_delivers_nothing(self):
        result = self.handle(
            "PreToolUse", tool_name="Read", tool_input={"file_path": "/nowhere/x.py"}
        )
        self.assertIsNone(result)

    def test_caps_rows_and_names_the_rest(self):
        """Past ten rows the rest are named by number and path only."""
        for n in range(2, 14):
            self.write(f"{n:03d}-n{n}.md", adr_text(title=f"{n}: Decision {n}"))
        self.manage()
        text = self.context(
            self.handle(
                "PreToolUse",
                tool_name="Read",
                tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
            )
        )
        self.assertEqual(text.count("(Accepted):"), 10)
        self.assertIn("013", text)
        self.assertLess(len(text), hook.MAX_CHARS)

    def test_names_every_row_when_the_body_would_not_fit(self):
        """A row too big for the cap moves to the named-only line rather than vanishing."""
        long_summary = "x" * 1_000
        self.write(
            "001-first.md", adr_text(summary=long_summary, **{"revisit-when": "A condition."})
        )
        for n in range(2, 14):
            self.write(
                f"{n:03d}-n{n}.md", adr_text(title=f"{n}: Decision {n}", summary=long_summary)
            )
        self.manage()
        text = self.context(
            self.handle(
                "PreToolUse",
                tool_name="Read",
                tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
            )
        )
        self.assertLess(len(text), hook.MAX_CHARS)
        for n in range(1, 14):
            self.assertIn(f"{n:03d}", text)

    def test_concurrent_calls_lose_no_update(self):
        """Parallel first touches on different files both land in state.

        Valid only because `flock` locks per open file description, so two threads with
        their own handles exclude each other as two processes would; `lockf` would not.
        """
        self.write_scoped("a.py")
        self.write_scoped("b.py")
        self.write("002-a.md", adr_text(title="2: A", scope="[a.py]"))
        self.write("003-b.md", adr_text(title="3: B", scope="[b.py]"))
        self.manage()
        threads = [
            threading.Thread(
                target=self.handle,
                args=("PreToolUse",),
                kwargs={
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(self.repo_root / name)},
                },
            )
            for name in ("a.py", "b.py")
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(
            sorted(self.state()["injected"][hook.MAIN_AGENT]),
            [self.injected_key("002"), self.injected_key("003")],
        )


class PostToolBatchTests(HookTestCase):
    """PostToolBatch: regenerate after an ADR edit; report new findings once."""

    def test_regenerates_the_index_after_an_adr_edit(self):
        """A Write under docs/adr in the batch leads to reconcile --write."""
        self.handle("SessionStart", source="startup")
        self.write("002-second.md", adr_text(title="2: Do another thing"))
        result = self.handle(
            "PostToolBatch",
            tool_calls=[
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(self.adr_dir / "002-second.md")},
                }
            ],
        )
        self.assertIsNone(result)
        self.assertIn("[002]", self.index())

    def test_reports_a_new_dangling_entry_once(self):
        """A rename after the baseline is reported on the batch that follows, then not again."""
        self.handle("SessionStart", source="startup")
        self.dangle()
        first = self.handle(
            "PostToolBatch",
            tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "rm README.md"}}],
        )
        self.assertIn("README.md", self.context(first))
        self.assertIn("update `scope`", self.context(first))
        second = self.handle(
            "PostToolBatch", tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "ls"}}]
        )
        self.assertIsNone(second)

    def test_does_not_report_a_baseline_finding(self):
        """A finding present at session start belongs to the repository, not this batch."""
        self.dangle()
        self.handle("SessionStart", source="startup")
        result = self.handle(
            "PostToolBatch", tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "ls"}}]
        )
        self.assertIsNone(result)

    def test_never_writes_without_an_adr_edit(self):
        """A batch with no file tool under docs/adr leaves a stale index stale, and reports it."""
        self.handle("SessionStart", source="startup")
        self.write("002-second.md", adr_text(title="2: Do another thing"))
        before = self.index()
        result = self.handle(
            "PostToolBatch",
            tool_calls=[
                {"tool_name": "Bash", "tool_input": {"command": "cat > docs/adr/002-second.md"}}
            ],
        )
        self.assertEqual(self.index(), before)
        self.assertIn("stale", self.context(result))

    def test_snapshots_a_baseline_for_a_root_first_met_here(self):
        """A root with no SessionStart baseline gets one at its first check."""
        self.dangle()
        result = self.handle(
            "PostToolBatch", tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "ls"}}]
        )
        self.assertIsNone(result)
        self.assertEqual(
            self.state()["roots"][str(self.repo_root)]["baseline"], ["dangling:README.md"]
        )


class TwoManagedRootsTests(HookTestCase):
    """Two managed corpora in one session, each numbering its decisions from 001."""

    def setUp(self) -> None:
        super().setUp()
        self.inner = self.repo_root / "packages" / "app"
        (self.inner / ADR_DIR).mkdir(parents=True)
        (self.inner / SCOPED_FILE).write_text("", encoding="utf-8")
        self.write_inner("001-inner.md", adr_text(title="1: Do the inner thing"))
        self.manage_root(self.inner)

    def write_inner(self, name: str, content: str) -> None:
        """Place a file in the inner corpus."""
        (self.inner / ADR_DIR / name).write_text(content, encoding="utf-8")

    def inner_index(self) -> str:
        """Read the inner corpus's generated index."""
        return (self.inner / ADR_DIR / INDEX_FILENAME).read_text(encoding="utf-8")

    def read_a_file_in(self, root: Path) -> dict | None:
        """A PreToolUse reading the bound file at the root of one corpus."""
        return self.handle(
            "PreToolUse", tool_name="Read", tool_input={"file_path": str(root / SCOPED_FILE)}
        )

    def test_injects_the_row_from_each_root(self):
        """001 in one corpus must not suppress 001 in the other, so both are remembered."""
        self.read_a_file_in(self.repo_root)
        self.read_a_file_in(self.inner)
        self.assertEqual(
            self.state()["injected"][hook.MAIN_AGENT],
            [self.injected_key("001"), self.injected_key("001", self.inner)],
        )

    def test_regenerates_the_index_of_every_root_the_batch_wrote(self):
        """A batch writing an ADR in each corpus regenerates both indexes, not the first."""
        self.write("002-second.md", adr_text(title="2: Do another thing"))
        self.write_inner("002-inner.md", adr_text(title="2: Do another inner thing"))
        self.handle(
            "PostToolBatch",
            tool_calls=[
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(self.adr_dir / "002-second.md")},
                },
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(self.inner / ADR_DIR / "002-inner.md")},
                },
            ],
        )
        self.assertIn("[002]", self.index())
        self.assertIn("[002]", self.inner_index())


class WorktreeHookTests(HookTestCase):
    """A session whose working directory is a managed worktree inside the repository."""

    def setUp(self) -> None:
        super().setUp()
        self.worktree = self.repo_root / ".worktrees" / "feature"
        (self.worktree / ADR_DIR).mkdir(parents=True)
        (self.worktree / SCOPED_FILE).write_text("", encoding="utf-8")
        (self.worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        self.write_worktree("001-first.md", adr_text())
        self.manage_root(self.worktree)
        self.cwd = self.worktree

    def write_worktree(self, name: str, content: str) -> None:
        """Place a file in the worktree's corpus."""
        (self.worktree / ADR_DIR / name).write_text(content, encoding="utf-8")

    def write_second_adr_in_both_corpora(self) -> None:
        """Leave each index one decision behind, so a regeneration is visible in either."""
        self.write("002-second.md", adr_text(title="2: Do another thing"))
        self.write_worktree("002-second.md", adr_text(title="2: Do another thing"))

    def batch_writing_the_worktrees_adr(self) -> dict | None:
        """A PostToolBatch whose only ADR write lands under the worktree."""
        return self.handle(
            "PostToolBatch",
            tool_calls=[
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(self.worktree / ADR_DIR / "002-second.md")},
                }
            ],
        )

    def test_snapshots_the_baseline_under_the_worktree_root(self):
        """The session's root is the worktree, so the checkout it sits in gets no record."""
        self.handle("SessionStart", source="startup")
        self.assertEqual(list(self.state()["roots"]), [str(self.worktree)])

    def test_regenerates_the_worktree_index_after_an_adr_edit(self):
        """An ADR written under the worktree regenerates the worktree's own index."""
        self.write_second_adr_in_both_corpora()
        self.batch_writing_the_worktrees_adr()
        self.assertIn(
            "[002]", (self.worktree / ADR_DIR / INDEX_FILENAME).read_text(encoding="utf-8")
        )

    def test_leaves_the_index_of_the_checkout_it_sits_in_alone(self):
        """The parent checkout is not this session's root, so its stale index stays stale."""
        self.write_second_adr_in_both_corpora()
        before = self.index()
        self.batch_writing_the_worktrees_adr()
        self.assertEqual(self.index(), before)


class StopTests(HookTestCase):
    """Stop and SubagentStop: raise an open new finding once more, then stay silent."""

    def test_raises_an_open_finding_once_more(self):
        self.handle("SessionStart", source="startup")
        self.dangle()
        self.handle(
            "PostToolBatch",
            tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "rm README.md"}}],
        )
        first = self.handle("Stop", stop_hook_active=False)
        self.assertIn("README.md", self.context(first))
        self.assertEqual(first["hookSpecificOutput"]["hookEventName"], "Stop")
        second = self.handle("Stop", stop_hook_active=False)
        self.assertIsNone(second)

    def test_is_silent_once_fixed(self):
        self.handle("SessionStart", source="startup")
        self.dangle()
        self.handle(
            "PostToolBatch",
            tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "rm README.md"}}],
        )
        (self.repo_root / SCOPED_FILE).write_text("", encoding="utf-8")
        self.assertIsNone(self.handle("Stop", stop_hook_active=False))

    def test_subagent_stop_uses_the_same_rule(self):
        self.handle("SessionStart", source="startup")
        self.dangle()
        self.handle(
            "PostToolBatch",
            tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "rm README.md"}}],
            agent_id="agent-1",
        )
        result = self.handle("SubagentStop", agent_id="agent-1", stop_hook_active=False)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SubagentStop")

    def test_does_not_re_raise_while_a_stop_hook_is_active(self):
        self.handle("SessionStart", source="startup")
        self.dangle()
        self.handle(
            "PostToolBatch",
            tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "rm README.md"}}],
        )
        self.assertIsNone(self.handle("Stop", stop_hook_active=True))


class HandleRobustnessTests(HookTestCase):
    """`handle()` must not hang or crash on a broken state file or a lock someone else holds."""

    def write_state_bytes(self, content: bytes) -> None:
        """Put the session's state file on disk as the given bytes."""
        session_dir = self.state_dir / hook.STATE_SUBDIR
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / f"{self.session}.json").write_bytes(content)

    def test_treats_a_corrupt_state_file_as_absent(self):
        """A state file that is not valid JSON yields a normal result and a fresh baseline.

        Also the CRITICAL reproduction: corrupt state plus a valid event must return
        normally rather than hang or raise.
        """
        self.write_state_bytes(b"not json")
        result = self.handle("SessionStart", source="startup")
        self.assertIn("1 decision", self.context(result))
        self.assertEqual(self.state()["roots"][str(self.repo_root)]["baseline"], [])

    def test_treats_an_undecodable_state_file_as_absent(self):
        """Bytes that are not UTF-8 cost one baseline, as unparseable JSON does, not a crash."""
        self.write_state_bytes(b"\xff\xfe")
        result = self.handle("SessionStart", source="startup")
        self.assertIn("1 decision", self.context(result))

    def write_legacy_state(self) -> None:
        """Write the state file an earlier version left behind.

        Its root record is short of the keys added since, and its `injected` is a list
        rather than a mapping keyed by agent.
        """
        self.write_state_bytes(
            json.dumps(
                {"injected": [], "roots": {str(self.repo_root): {"baseline": []}}}
            ).encode("utf-8")
        )

    def test_normalises_a_root_record_an_earlier_version_wrote(self):
        """The record gains the keys it lacks, so the batch reports its finding as usual."""
        self.write_legacy_state()
        self.dangle()
        result = self.handle(
            "PostToolBatch", tool_calls=[{"tool_name": "Bash", "tool_input": {"command": "ls"}}]
        )
        self.assertIn("README.md", self.context(result))

    def test_normalises_an_injected_list_an_earlier_version_wrote(self):
        """`injected` is dropped rather than kept as a list, so the touch has a mapping to key."""
        self.write_legacy_state()
        result = self.handle(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
        )
        self.assertIn("001 (Accepted)", self.context(result))

    def test_a_held_lock_returns_none_without_hanging(self):
        """A lock another handle holds gives up within the retry budget, never raises."""
        lock_path = self.state_dir / hook.STATE_SUBDIR / f"{self.session}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder = lock_path.open("w")
        fcntl.flock(holder, fcntl.LOCK_EX)
        try:
            started = time.monotonic()
            result = self.handle("SessionStart", source="startup")
            elapsed = time.monotonic() - started
        finally:
            fcntl.flock(holder, fcntl.LOCK_UN)
            holder.close()
        self.assertIsNone(result)
        self.assertLess(elapsed, 2.0)


class MainTests(HookTestCase):
    """The entry point: JSON in, JSON out, never a traceback."""

    def test_returns_json_text_for_an_event(self):
        text = hook.main(
            json.dumps(self.event("SessionStart", source="startup")), self.state_dir
        )
        self.assertEqual(
            json.loads(text)["hookSpecificOutput"]["hookEventName"], "SessionStart"
        )

    def test_returns_nothing_when_there_is_nothing_to_say(self):
        text = hook.main(
            json.dumps(
                self.event("PreToolUse", tool_name="Read", tool_input={"file_path": "/nowhere"})
            ),
            self.state_dir,
        )
        self.assertEqual(text, "")

    def test_reports_a_crash_every_time_for_an_unknown_session(self):
        """An event that fails to parse has no session to remember against, so it is never silenced."""
        first = hook.main("{not json", self.state_dir)
        self.assertIn(
            "hook failed", json.loads(first)["hookSpecificOutput"]["additionalContext"]
        )
        self.assertIn("hook.py", json.loads(first)["hookSpecificOutput"]["additionalContext"])
        second = hook.main("{not json", self.state_dir)
        self.assertIn(
            "hook failed", json.loads(second)["hookSpecificOutput"]["additionalContext"]
        )
        self.assertFalse((self.state_dir / hook.STATE_SUBDIR / "unknown.json").exists())

    def test_reports_a_crash_once_for_a_known_session(self):
        """A crash inside a handler for a known session is reported once, then silenced."""

        def boom(event, state):
            raise RuntimeError("boom")

        with mock.patch.dict(hook.HANDLERS, {"SessionStart": boom}):
            first = hook.main(
                json.dumps(self.event("SessionStart", source="startup")), self.state_dir
            )
            self.assertIn(
                "hook failed", json.loads(first)["hookSpecificOutput"]["additionalContext"]
            )
            second = hook.main(
                json.dumps(self.event("SessionStart", source="startup")), self.state_dir
            )
        self.assertEqual(second, "")

    def test_handles_an_event_that_names_no_session(self):
        """A valid event with no session_id gets the standing note, not a crash report."""
        event = self.event("SessionStart", source="startup")
        del event["session_id"]
        text = hook.main(json.dumps(event), self.state_dir)
        self.assertIn("1 decision", json.loads(text)["hookSpecificOutput"]["additionalContext"])

    def test_remembers_a_session_that_names_itself_as_unknown(self):
        """State for an unnamed session lands under `unknown`, so the crash-once rule still holds."""
        event = self.event("SessionStart", source="startup")
        del event["session_id"]
        hook.main(json.dumps(event), self.state_dir)
        self.assertTrue(
            (self.state_dir / hook.STATE_SUBDIR / f"{hook.UNKNOWN_SESSION}.json").exists()
        )

    def test_prunes_old_state_files(self):
        """Files older than thirty days go at SessionStart."""
        old = self.state_dir / hook.STATE_SUBDIR / "old.json"
        old.parent.mkdir(parents=True)
        old.write_text("{}", encoding="utf-8")
        os.utime(old, (0, 0))
        hook.handle(
            self.event("SessionStart", source="startup"),
            self.state_dir,
            now=hook.PRUNE_AFTER_SECONDS + 1.0,
        )
        self.assertFalse(old.exists())


class PruneTests(HookTestCase):
    """Unit tests for ``prune()``: which files the retention rule takes, and which it leaves."""

    def setUp(self) -> None:
        super().setUp()
        self.sessions = self.state_dir / hook.STATE_SUBDIR
        self.sessions.mkdir(parents=True)

    def stale(self, name: str) -> Path:
        """A file in the session directory, dated well past the retention period."""
        path = self.sessions / name
        path.write_text("", encoding="utf-8")
        os.utime(path, (0, 0))
        return path

    def test_prunes_a_lock_whose_session_file_is_gone(self):
        """Nothing else ever removes a lock sidecar, so an orphan would accumulate forever."""
        lock = self.stale("old.lock")
        hook.prune(self.state_dir, hook.PRUNE_AFTER_SECONDS + 1.0)
        self.assertFalse(lock.exists())

    def test_keeps_a_lock_whose_session_file_stands(self):
        """While the state file is there the lock is that session's, and two calls need it."""
        (self.sessions / "live.json").write_text("{}", encoding="utf-8")
        lock = self.stale("live.lock")
        hook.prune(self.state_dir, hook.PRUNE_AFTER_SECONDS + 1.0)
        self.assertTrue(lock.exists())
