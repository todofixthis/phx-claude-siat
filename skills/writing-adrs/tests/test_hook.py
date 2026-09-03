"""Tests for `hook.py` — one per event, plus state, baseline-and-delta and concurrency.

Each test feeds `handle()` a synthetic event as Claude Code would send it and asserts the
exact JSON returned and the state file left behind. Roots are fixture trees passed by
path; nothing here reads the working directory.
"""

import fcntl
import json
import os
import threading
import time
from unittest import mock

import hook
from adr import INDEX_FILENAME
from tests.test_adr import SCOPED_FILE, RepoTestCase, adr_text


class HookTestCase(RepoTestCase):
    """A managed fixture corpus with one decision, plus a state directory."""

    def setUp(self) -> None:
        super().setUp()
        self.write("001-first.md", adr_text(**{"revisit-when": "A condition."}))
        self.manage()
        self.state_dir = self.repo_root / "state"
        self.session = "sess-1"

    def event(self, name: str, **fields) -> dict:
        """A hook event with the common fields filled."""
        return {
            "cwd": str(self.repo_root),
            "hook_event_name": name,
            "session_id": self.session,
        } | fields

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
        """After compaction the rows must be injected again; the baseline value is unchanged."""
        self.handle("SessionStart", source="startup")
        self.handle(
            "PreToolUse",
            tool_name="Read",
            tool_input={"file_path": str(self.repo_root / SCOPED_FILE)},
        )
        self.assertEqual(self.state()["injected"][hook.MAIN_AGENT], ["001"])
        baseline_before = self.state()["roots"][str(self.repo_root)]["baseline"]
        self.handle("SessionStart", source="compact")
        self.assertEqual(self.state()["injected"], {})
        self.assertEqual(
            self.state()["roots"][str(self.repo_root)]["baseline"], baseline_before
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
            self.state()["injected"], {"agent-1": ["001"], hook.MAIN_AGENT: ["001"]}
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
        self.assertLess(len(text), 10_000)

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
        self.assertEqual(sorted(self.state()["injected"][hook.MAIN_AGENT]), ["002", "003"])


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

    def test_treats_a_corrupt_state_file_as_absent(self):
        """A state file that is not valid JSON yields a normal result and a fresh baseline.

        Also the CRITICAL reproduction: corrupt state plus a valid event must return
        normally rather than hang or raise.
        """
        session_dir = self.state_dir / hook.STATE_SUBDIR
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / f"{self.session}.json").write_text("not json", encoding="utf-8")
        result = self.handle("SessionStart", source="startup")
        self.assertIn("1 decision", self.context(result))
        self.assertEqual(self.state()["roots"][str(self.repo_root)]["baseline"], [])

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
