"""Tests for the plugin's Python environment: `sync.sh`, `adr.sh` and the hooks.json commands.

Integration tests throughout: each one copies the plugin into a temp directory, in the
plugin-cache layout or a checkout's, and runs the shipped shell — the scripts directly,
the hooks.json commands through `sh -c` — as subprocesses with the environment Claude Code
would give them. The tests that sync need `uv` on PATH plus the network or a warm uv cache.

The scripts anchor the plugin root to the tree they ship in, so every test runs the copy's
scripts from a working directory outside that copy and never changes its own. Every
subprocess goes through `subprocess_env()`, which strips the variables that would redirect
the checkout case: the developer's own `UV_PROJECT_ENVIRONMENT`, and the `VIRTUAL_ENV`
`uv run` sets for pytest.
"""

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import tomllib

import adr
import hook
from adr import ADR_DIR, INDEX_FILENAME
from tests.test_adr import SCOPED_FILE, adr_text

# The real plugin: the source of every fixture tree and of the hooks.json commands under test.
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = Path("skills/writing-adrs")
HOOKS_FILE = PLUGIN_ROOT / "hooks/hooks.json"

ADR_LAUNCHER = SKILL_DIR / "adr.sh"
SYNC_SCRIPT = SKILL_DIR / "sync.sh"
# The file whose presence means a sync completed; every per-event hook stays silent without it.
VENV_MARKER = ".phx-synced"
VENV_PYTHON = Path("bin/python")

CACHE_PARENT = Path("plugins/cache/phx-claude-siat/phx")
VERSION = "1.0.0"
SESSION = "sess-env"
# Generous for a cold sync on a slow network, and still a bound.
TIMEOUT_SECONDS = 120

# Set by the developer's shell, by `uv run` or by a Claude Code session running these tests;
# each would redirect a subprocess away from its fixture, the checkout case's venv above all,
# or steer which interpreter and lock state uv resolves.
STRIPPED_VARIABLES = (
    "CLAUDE_PLUGIN_DATA",
    "CLAUDE_PLUGIN_ROOT",
    "CLAUDE_PROJECT_DIR",
    "UV_FROZEN",
    "UV_LOCKED",
    "UV_NO_SYNC",
    "UV_OFFLINE",
    "UV_PROJECT",
    "UV_PROJECT_ENVIRONMENT",
    "UV_PYTHON",
    "UV_PYTHON_DOWNLOADS",
    "UV_PYTHON_PREFERENCE",
    "VIRTUAL_ENV",
)

# What SessionStart says when uv is missing and no earlier session left a synced venv.
NEEDS_UV_NOTE = "need uv on PATH"

# The events whose hook only runs a synced venv's python, never `uv`.
PER_EVENT_HOOKS = ("PostToolBatch", "PreToolUse", "Stop", "SubagentStart", "SubagentStop")


def subprocess_env(**overrides: str) -> dict[str, str]:
    """This process's environment minus what would redirect the venv, plus `overrides`."""
    env = {key: value for key, value in os.environ.items() if key not in STRIPPED_VARIABLES}
    return env | overrides


def hook_command(event_name: str) -> str:
    """The one command hooks.json runs for `event_name`."""
    blocks = json.loads(HOOKS_FILE.read_text(encoding="utf-8"))["hooks"][event_name]
    (block,) = blocks
    (entry,) = block["hooks"]
    return entry["command"]


def write_executable(path: Path, text: str) -> None:
    """Write a script and mark it executable, creating its directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_plugin(destination: Path) -> Path:
    """Copy what a sync reads of the plugin to `destination`, and return it.

    The workspace root's manifest and lock, the plugin manifest, each workspace member's
    `pyproject.toml`, and the whole skill bar its environments, caches and tests.
    """
    pyproject = PLUGIN_ROOT / "pyproject.toml"
    members = tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["uv"]["workspace"]
    files = [Path("pyproject.toml"), Path("uv.lock"), Path(".claude-plugin/plugin.json")]
    files += [Path(member) / "pyproject.toml" for member in members["members"]]
    for name in files:
        (destination / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PLUGIN_ROOT / name, destination / name)
    shutil.copytree(
        PLUGIN_ROOT / SKILL_DIR,
        destination / SKILL_DIR,
        ignore=shutil.ignore_patterns(".venv*", "__pycache__", "tests"),
        dirs_exist_ok=True,
    )
    return destination


class PluginTreeTestCase(unittest.TestCase):
    """A temp directory holding a managed fixture project and an empty plugin data directory.

    Plugin trees are built on demand, in the cache layout or a checkout's, and run against
    the project; `data` is what Claude Code would pass as `CLAUDE_PLUGIN_DATA`.
    """

    def setUp(self) -> None:
        # Under a directory whose name holds a space, so every path the shell sees has one.
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve() / "a b"
        self.tmp.mkdir()
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.project = self.tmp / "project"
        (self.project / ADR_DIR).mkdir(parents=True)
        (self.project / SCOPED_FILE).write_text("", encoding="utf-8")
        (self.project / ADR_DIR / "001-first.md").write_text(adr_text(), encoding="utf-8")
        # Generated by the tool itself, so the hooks' gate sees exactly what a consumer's has.
        with contextlib.redirect_stdout(io.StringIO()):
            code = adr.main(["--repo-root", str(self.project), "index"], self.project)
        assert code == 0, code

    def cache_root(self, version: str = VERSION) -> Path:
        """A plugin tree in the cache layout, versioned by its directory name."""
        return copy_plugin(self.tmp / CACHE_PARENT / version)

    def checkout_root(self) -> Path:
        """A plugin tree loaded in place from a checkout."""
        return copy_plugin(self.tmp / "checkout")

    def unmanage(self, index: str | None) -> None:
        """Replace the project's INDEX.md with `index`, or remove it where that is None."""
        target = self.project / ADR_DIR / INDEX_FILENAME
        if index is None:
            target.unlink()
        else:
            target.write_text(index, encoding="utf-8")

    def reset_sessions(self) -> None:
        """Forget every session's hook state, so the next event is a first touch again."""
        shutil.rmtree(self.data / hook.STATE_SUBDIR, ignore_errors=True)

    def fake_python(self, venv: Path) -> None:
        """A marked venv whose python only echoes how it was called."""
        write_executable(venv / VENV_PYTHON, '#!/bin/sh\necho "CALLED $*"\n')
        (venv / VENV_MARKER).write_text("", encoding="utf-8")

    def venv(self, version: str = VERSION) -> Path:
        """Where the cache layout's venv for `version` lives."""
        return self.data / "venvs" / version

    def run_script(
        self, script: Path, *args: str, **env: str
    ) -> subprocess.CompletedProcess[str]:
        """Run a shipped shell script by path from the project directory."""
        return subprocess.run(
            ["sh", str(script), *args],
            capture_output=True,
            check=False,
            cwd=self.project,
            env=subprocess_env(**env),
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

    def sync(self, root: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        """Run `root`'s sync.sh against the data directory."""
        return self.run_script(root / SYNC_SCRIPT, str(self.data), *args, **env)

    def event(self, name: str, **fields: object) -> dict:
        """A hook event naming the project as its working directory."""
        return {
            "cwd": str(self.project),
            "hook_event_name": name,
            "session_id": SESSION,
        } | fields

    def read_event(self) -> dict:
        """A `PreToolUse` event for a `Read` of the file the fixture decision binds."""
        tool_input = {"file_path": str(self.project / SCOPED_FILE)}
        return self.event("PreToolUse", tool_input=tool_input, tool_name="Read")

    def run_hook(
        self, root: Path | str, event: dict, textual: bool = False, **env: str
    ) -> subprocess.CompletedProcess[str]:
        """Run the hooks.json command for `event` as Claude Code would, against `root`.

        A string `root` reaches the command verbatim, a trailing slash included. With
        `textual`, the plugin root and data directory are substituted into the command's
        text and absent from its environment, the other way Claude Code may pass them.
        """
        command = hook_command(event["hook_event_name"])
        plugin = {"CLAUDE_PLUGIN_DATA": str(self.data), "CLAUDE_PLUGIN_ROOT": str(root)}
        if textual:
            for name, value in plugin.items():
                command = command.replace(f"${{{name}}}", value)
            plugin = {}
        return subprocess.run(
            ["sh", "-c", command],
            capture_output=True,
            check=False,
            cwd=self.project,
            env=subprocess_env(CLAUDE_PROJECT_DIR=str(self.project), **plugin, **env),
            input=json.dumps(event),
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

    def uv_shim(self, body: str) -> str:
        """A PATH whose `uv` is a shell script running `body`, ahead of everything else.

        `{uv}` in `body` names the real uv.
        """
        real = shutil.which("uv")
        shim = self.tmp / "shim-bin" / "uv"
        write_executable(shim, "#!/bin/sh\n" + body.replace("{uv}", f'"{real}"') + "\n")
        return f"{shim.parent}{os.pathsep}{os.environ['PATH']}"

    def failing_uv(self) -> str:
        """A PATH whose `uv` exits 1."""
        return self.uv_shim("exit 1")

    def path_without_uv(self) -> str:
        """A PATH holding only the tools the hooks and sync.sh call bar `uv`."""
        bin_dir = self.tmp / "bare-bin"
        bin_dir.mkdir(exist_ok=True)
        for tool in ("dirname", "grep", "head", "sh"):
            (bin_dir / tool).symlink_to(shutil.which(tool))
        return str(bin_dir)

    def offline(self) -> dict[str, str]:
        """The environment of a machine with no network and an empty uv cache."""
        cache = self.tmp / "empty-uv-cache"
        cache.mkdir(exist_ok=True)
        return {
            "UV_CACHE_DIR": str(cache),
            "UV_OFFLINE": "1",
            "UV_PYTHON_DOWNLOADS": "never",
        }

    def files(self, root: Path) -> list[str]:
        """Every path under `root`, relative and sorted, bytecode caches aside."""
        return sorted(
            str(p.relative_to(root)) for p in root.rglob("*") if "__pycache__" not in p.parts
        )


class SyncTests(PluginTreeTestCase):
    """Integration tests: what `sync.sh` builds, where, and what it leaves behind."""

    def test_sync_builds_a_version_venv_under_plugin_data(self):
        """The cache case syncs into DATA/venvs/<version>, marks it, and prints its python."""
        root = self.cache_root()
        result = self.sync(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        python = self.venv() / VENV_PYTHON
        self.assertEqual(result.stdout, f"{python}\n")
        self.assertTrue((self.venv() / VENV_MARKER).is_file())
        imported = subprocess.run(
            [str(python), "-c", "import yaml"],
            capture_output=True,
            check=False,
            env=subprocess_env(),
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        self.assertEqual(imported.returncode, 0, imported.stderr)

    def test_cache_sync_installs_the_dependencies_but_not_the_tool(self):
        """The tool runs from the plugin's own files, so no copy of it is built into the venv."""
        root = self.cache_root()
        result = self.sync(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = subprocess.run(
            [
                str(self.venv() / VENV_PYTHON),
                "-c",
                "import importlib.metadata as m; print(sorted(d.name for d in m.distributions()))",
            ],
            capture_output=True,
            check=False,
            env=subprocess_env(),
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        self.assertEqual(installed.stdout, "['PyYAML']\n", installed.stderr)

    def test_cache_sync_leaves_the_plugin_tree_unchanged(self):
        """Nothing is created inside a cached plugin version: no venv, no lock, no build."""
        root = self.cache_root()
        before = self.files(root)
        result = self.sync(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.files(root), before)

    def test_cache_sync_installs_from_the_lock_as_shipped(self):
        """A lock behind its manifests is used as it stands, never re-locked inside the cache."""
        root = self.cache_root()
        manifest = root / SKILL_DIR / "pyproject.toml"
        text = manifest.read_text(encoding="utf-8")
        stale = text.replace('"pyyaml>=6.0.3,<7"', '"pyyaml>=6.0.3,<6.1"')
        self.assertNotEqual(stale, text)
        manifest.write_text(stale, encoding="utf-8")
        before = {
            path: (root / path).read_bytes()
            for path in self.files(root)
            if (root / path).is_file()
        }
        result = self.sync(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {
            path: (root / path).read_bytes()
            for path in self.files(root)
            if (root / path).is_file()
        }
        self.assertEqual(after, before)

    def test_sync_refuses_a_relative_data_dir_in_the_cache(self):
        """An unsubstituted or relative data directory is refused before uv can build in the cache."""
        root = self.cache_root()
        before = self.files(root)
        result = self.run_script(root / SYNC_SCRIPT, "${CLAUDE_PLUGIN_DATA}")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("${CLAUDE_PLUGIN_DATA}", result.stderr)
        self.assertEqual(self.files(root), before)
        self.assertEqual(list(self.project.rglob(VENV_MARKER)), [])

    def test_checkout_sync_refuses_a_venv_outside_the_checkout(self):
        """A developer's absolute venv elsewhere is left alone rather than rebuilt by uv."""
        root = self.checkout_root()
        foreign = self.tmp / "elsewhere" / "project-venv"
        foreign.mkdir(parents=True)
        (foreign / "keep").write_text("", encoding="utf-8")
        result = self.sync(root, UV_PROJECT_ENVIRONMENT=str(foreign))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("unset UV_PROJECT_ENVIRONMENT", result.stderr)
        self.assertEqual(self.files(foreign), ["keep"])

    def test_checkout_sync_refuses_a_venv_that_escapes_by_dot_components(self):
        """A path that only looks inside the checkout is refused before uv can touch it."""
        root = self.checkout_root()
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "keep").write_text("", encoding="utf-8")
        forms = {
            "..": self.tmp,
            "../elsewhere": elsewhere,
            "a/../../elsewhere": elsewhere,
            f"{root}/../elsewhere": elsewhere,
            ".": root,
        }
        for form, target in forms.items():
            with self.subTest(UV_PROJECT_ENVIRONMENT=form):
                before = self.files(target)
                result = self.sync(root, UV_PROJECT_ENVIRONMENT=form)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("unset UV_PROJECT_ENVIRONMENT", result.stderr)
                self.assertEqual(self.files(target), before)
                self.assertEqual(list(self.tmp.rglob(VENV_MARKER)), [])

    def test_checkout_sync_accepts_a_venv_spelt_with_dot_components(self):
        """`.` components are dropped, so `./.venv` and kin sync and the hooks find them."""
        root = self.checkout_root()
        forms = {
            "./.venv": root / ".venv",
            ".venv/.": root / ".venv",
            "./a/./.venv": root / "a" / ".venv",
        }
        for form, venv in forms.items():
            with self.subTest(UV_PROJECT_ENVIRONMENT=form):
                result = self.sync(root, UV_PROJECT_ENVIRONMENT=form)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"{venv / VENV_PYTHON}\n")
                self.assertTrue((venv / VENV_MARKER).is_file())
                hooked = self.run_hook(root, self.read_event(), UV_PROJECT_ENVIRONMENT=form)
                self.assertEqual(hooked.returncode, 0, hooked.stderr)
                self.assertIn("Decisions binding", hooked.stdout)
                # A fresh session in the next subtest, so this one's injected rows stay its own.
                self.reset_sessions()

    def test_checkout_sync_accepts_an_absolute_venv_inside_the_checkout(self):
        """Only a venv outside the checkout is refused; an absolute path inside it syncs."""
        root = self.checkout_root()
        venv = root / ".venv.abs"
        result = self.sync(root, UV_PROJECT_ENVIRONMENT=str(venv))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"{venv / VENV_PYTHON}\n")
        self.assertTrue((venv / VENV_MARKER).is_file())

    def test_parallel_syncs_from_empty_data_all_succeed(self):
        """Sessions starting together each get the venv, serialised by uv rather than failing."""
        root = self.cache_root()
        processes = [
            subprocess.Popen(
                ["sh", str(root / SYNC_SCRIPT), str(self.data)],
                cwd=self.project,
                env=subprocess_env(),
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                text=True,
            )
            for _ in range(3)
        ]
        results = [(p.communicate(timeout=TIMEOUT_SECONDS), p.returncode) for p in processes]
        python = f"{self.venv() / VENV_PYTHON}\n"
        for (stdout, stderr), code in results:
            self.assertEqual((code, stdout), (0, python), stderr)
        self.assertTrue((self.venv() / VENV_MARKER).is_file())

    def test_uv_output_never_reaches_stdout(self):
        """Whatever uv prints, stdout carries only the python path a caller captures."""
        root = self.cache_root()
        result = self.sync(root, PATH=self.uv_shim('echo chatter\nexec {uv} "$@"'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"{self.venv() / VENV_PYTHON}\n")

    def test_prunes_only_versions_gone_from_the_cache(self):
        """A version's venv goes once its cache directory has; one still cached stays."""
        for linked in (False, True):
            with self.subTest(version_directory_is_a_symlink=linked):
                # A fresh fixture per subtest, so the first cannot leave venvs for the second.
                self.setUp()
                if linked:
                    tree = copy_plugin(self.tmp / "elsewhere" / "tree")
                    (self.tmp / CACHE_PARENT).mkdir(parents=True)
                    (self.tmp / CACHE_PARENT / VERSION).symlink_to(tree)
                    root = self.tmp / CACHE_PARENT / VERSION
                else:
                    root = self.cache_root()
                (self.tmp / CACHE_PARENT / "0.9.0").mkdir()
                for version in ("0.9.0", "0.8.0"):
                    (self.venv(version) / "bin").mkdir(parents=True)

                result = self.sync(root)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"{self.venv() / VENV_PYTHON}\n")
                self.assertTrue((self.venv() / VENV_MARKER).is_file())
                self.assertTrue(self.venv("0.9.0").is_dir())
                self.assertFalse(self.venv("0.8.0").exists())

    def test_keeps_the_version_just_synced_when_its_directory_goes_mid_sync(self):
        """A version directory removed during the sync must not take the venv just built."""
        root = self.cache_root()
        # The real uv, then the version directory removed before the prune runs, as Claude
        # Code might remove it while a session's SessionStart is still syncing.
        path = self.uv_shim(f'{{uv}} "$@" || exit\nrm -rf "{root}"')
        result = self.sync(root, PATH=path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(root.exists())
        self.assertTrue((self.venv() / VENV_MARKER).is_file())

    def test_sync_refuses_an_empty_data_dir_in_the_cache(self):
        """With no data directory the cache case has nowhere to build, and says so."""
        root = self.cache_root()
        result = self.run_script(root / SYNC_SCRIPT, "")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("CLAUDE_PLUGIN_DATA", result.stderr)

    def test_a_failed_resync_leaves_no_marker(self):
        """A re-sync that fails must not leave the old marker over a half-updated venv."""
        root = self.cache_root()
        write_executable(self.venv() / VENV_PYTHON, "#!/bin/sh\nexit 0\n")
        (self.venv() / VENV_MARKER).write_text("", encoding="utf-8")
        result = self.sync(root, PATH=self.failing_uv())
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.venv() / VENV_MARKER).exists())

    def test_checkout_sync_creates_the_workspace_venv_inexactly(self):
        """The checkout case builds <checkout>/.venv and a re-sync removes nothing it did not add."""
        root = self.checkout_root()
        first = self.sync(root)
        self.assertEqual(first.returncode, 0, first.stderr)
        venv = root / ".venv"
        self.assertEqual(first.stdout, f"{venv / VENV_PYTHON}\n")
        self.assertTrue((venv / VENV_MARKER).is_file())

        # A distribution the developer's own sync might have installed, RECORD listing every
        # file so an exact sync would know to remove it all.
        (site_packages,) = venv.glob("lib/python*/site-packages")
        dist_info = site_packages / "keepme-1.0.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: keepme\nVersion: 1.0\n", encoding="utf-8"
        )
        (dist_info / "INSTALLER").write_text("uv\n", encoding="utf-8")
        (dist_info / "RECORD").write_text(
            "".join(
                f"keepme-1.0.dist-info/{name},,\n"
                for name in ("INSTALLER", "METADATA", "RECORD")
            ),
            encoding="utf-8",
        )

        second = self.sync(root)
        self.assertEqual(second.returncode, 0, second.stderr)
        version = subprocess.run(
            [
                str(venv / VENV_PYTHON),
                "-c",
                "import importlib.metadata as m; print(m.version('keepme'))",
            ],
            capture_output=True,
            check=False,
            env=subprocess_env(),
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        self.assertEqual(version.stdout, "1.0\n", version.stderr)

    def test_checkout_sync_honours_the_developers_venv_name(self):
        """A relative UV_PROJECT_ENVIRONMENT names the venv beside the checkout, and the hooks find it."""
        root = self.checkout_root()
        result = self.sync(root, UV_PROJECT_ENVIRONMENT=".venv.dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        venv = root / ".venv.dev"
        self.assertEqual(result.stdout, f"{venv / VENV_PYTHON}\n")
        self.assertTrue((venv / VENV_MARKER).is_file())
        self.assertFalse((root / ".venv").exists())

        hooked = self.run_hook(root, self.read_event(), UV_PROJECT_ENVIRONMENT=".venv.dev")
        self.assertEqual(hooked.returncode, 0, hooked.stderr)
        self.assertIn("Decisions binding", hooked.stdout)


class HookCommandTests(PluginTreeTestCase):
    """Integration tests: the hooks.json commands, run through `sh -c` as Claude Code runs them."""

    def test_session_start_runs_the_hook_from_the_synced_venv(self):
        """From an empty data directory, SessionStart syncs and notes; the next event injects."""
        root = self.cache_root()
        started = self.run_hook(root, self.event("SessionStart", source="startup"))
        self.assertEqual(started.returncode, 0, started.stderr)
        output = json.loads(started.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertEqual(output["additionalContext"], hook.NOTE.format(count="1 decision"))
        self.assertTrue((self.venv() / VENV_MARKER).is_file())

        touched = self.run_hook(root, self.read_event())
        self.assertEqual(touched.returncode, 0, touched.stderr)
        self.assertIn("Decisions binding", touched.stdout)

    def test_a_trailing_slash_on_the_plugin_root_still_reaches_the_venv(self):
        """The version is the root's last component whether or not the harness ends it in `/`."""
        root = self.cache_root()
        synced = self.sync(root)
        self.assertEqual(synced.returncode, 0, synced.stderr)
        touched = self.run_hook(f"{root}/", self.read_event())
        self.assertEqual(touched.returncode, 0, touched.stderr)
        self.assertIn("Decisions binding", touched.stdout)

    def test_every_per_event_command_runs_the_venv_python_on_the_hook(self):
        """Each per-event command finds the marked venv in both layouts and runs hook.py."""
        layouts = {
            "cache": (self.cache_root(), self.venv()),
            "checkout": (self.checkout_root(), self.tmp / "checkout" / ".venv"),
        }
        for layout, (root, venv) in layouts.items():
            self.fake_python(venv)
            for name in PER_EVENT_HOOKS:
                with self.subTest(layout=layout, event=name):
                    result = self.run_hook(root, self.event(name))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, f"CALLED {root / SKILL_DIR / 'hook.py'}\n")

    def test_session_start_in_a_checkout_syncs_the_workspace_venv(self):
        """Loaded from a checkout, SessionStart builds <checkout>/.venv and notes the corpus."""
        root = self.checkout_root()
        started = self.run_hook(root, self.event("SessionStart", source="startup"))
        self.assertEqual(started.returncode, 0, started.stderr)
        output = json.loads(started.stdout)["hookSpecificOutput"]
        self.assertEqual(output["additionalContext"], hook.NOTE.format(count="1 decision"))
        self.assertTrue((root / ".venv" / VENV_MARKER).is_file())

    def test_an_unmanaged_project_never_calls_uv(self):
        """Without the tool's index, SessionStart stops at the gate: no uv, no output, no venv."""
        root = self.cache_root()
        sentinel = self.tmp / "uv-called"
        path = self.uv_shim(f'touch "{sentinel}"')
        for index in ("# Someone else's index\n", None):
            with self.subTest(index=index):
                self.unmanage(index)
                result = self.run_hook(
                    root, self.event("SessionStart", source="startup"), PATH=path
                )
                self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)
                self.assertFalse(sentinel.exists())
                self.assertEqual(list(self.data.iterdir()), [])

    def test_later_session_starts_reuse_the_venv_offline(self):
        """Resume, clear, compact and fork re-sync as a no-op offline and still inject the note."""
        root = self.cache_root()
        synced = self.sync(root)
        self.assertEqual(synced.returncode, 0, synced.stderr)
        for source in ("clear", "compact", "fork", "resume"):
            with self.subTest(source=source):
                started = self.run_hook(
                    root, self.event("SessionStart", source=source), **self.offline()
                )
                self.assertEqual(started.returncode, 0, started.stderr)
                output = json.loads(started.stdout)["hookSpecificOutput"]
                self.assertEqual(
                    output["additionalContext"], hook.NOTE.format(count="1 decision")
                )
                self.assertTrue((self.venv() / VENV_MARKER).is_file())

    def test_substituted_plugin_paths_reach_the_venv(self):
        """Paths substituted into the command text, not exported, sync and reach the venv alike."""
        root = self.cache_root()
        started = self.run_hook(
            root, self.event("SessionStart", source="startup"), textual=True
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertIn("hookSpecificOutput", started.stdout)
        touched = self.run_hook(root, self.read_event(), textual=True)
        self.assertEqual(touched.returncode, 0, touched.stderr)
        self.assertIn("Decisions binding", touched.stdout)

    def test_session_start_with_a_trailing_slash_prunes_to_the_current_version(self):
        """A trailing slash on the root still names the version, so only stale venvs go."""
        root = self.cache_root()
        (self.venv("0.8.0") / "bin").mkdir(parents=True)
        started = self.run_hook(f"{root}/", self.event("SessionStart", source="startup"))
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(sorted(p.name for p in (self.data / "venvs").iterdir()), [VERSION])

    def test_session_start_says_uv_is_missing(self):
        """Without uv or a synced venv, SessionStart says the checks are off; later events stay silent."""
        root = self.cache_root()
        path = self.path_without_uv()

        started = self.run_hook(root, self.event("SessionStart", source="startup"), PATH=path)
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertIn(NEEDS_UV_NOTE, started.stdout)

        touched = self.run_hook(root, self.read_event(), PATH=path)
        self.assertEqual((touched.returncode, touched.stdout), (0, ""), touched.stderr)

    def test_session_start_without_uv_runs_an_earlier_sessions_venv(self):
        """With uv gone but a venv synced before, SessionStart takes its baseline as usual."""
        root = self.cache_root()
        synced = self.sync(root)
        self.assertEqual(synced.returncode, 0, synced.stderr)
        path = self.path_without_uv()

        started = self.run_hook(root, self.event("SessionStart", source="startup"), PATH=path)
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertNotIn(NEEDS_UV_NOTE, started.stdout)
        output = json.loads(started.stdout)["hookSpecificOutput"]
        self.assertEqual(output["additionalContext"], hook.NOTE.format(count="1 decision"))

        touched = self.run_hook(root, self.read_event(), PATH=path)
        self.assertEqual(touched.returncode, 0, touched.stderr)
        self.assertIn("Decisions binding", touched.stdout)

    def test_session_start_says_the_sync_failed_offline(self):
        """An offline first session gets no venv, says so, and leaves no marker behind."""
        root = self.cache_root()
        started = self.run_hook(
            root, self.event("SessionStart", source="startup"), **self.offline()
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertIn("could not build", started.stdout)
        self.assertFalse((self.venv() / VENV_MARKER).exists())

    def test_a_venv_without_its_marker_keeps_every_hook_silent(self):
        """An interrupted sync leaves a python that must never run, so each event says nothing."""
        root = self.cache_root()
        write_executable(self.venv() / VENV_PYTHON, "#!/bin/sh\necho CALLED\nexit 1\n")
        for name in PER_EVENT_HOOKS:
            with self.subTest(event=name):
                result = self.run_hook(root, self.event(name))
                self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)


class LauncherTests(PluginTreeTestCase):
    """Integration tests: `adr.sh` builds the venv it needs, then runs the tool from it."""

    def test_launcher_bootstraps_a_repository_without_adrs(self):
        """A repository with no corpus yet gets its first ADR, the venv built on the way."""
        root = self.cache_root()
        repo = self.tmp / "fresh"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=TIMEOUT_SECONDS)
        result = self.run_script(
            root / ADR_LAUNCHER,
            str(self.data),
            "--repo-root",
            str(repo),
            "new",
            "First decision",
            "--summary",
            "S.",
            "--no-scope",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((repo / ADR_DIR / "001-first-decision.md").is_file())

    def test_launcher_reuses_a_marked_venv_without_calling_uv(self):
        """A venv already marked complete runs the tool straight away, uv never consulted."""
        root = self.cache_root()
        write_executable(self.venv() / VENV_PYTHON, '#!/bin/sh\necho "RAN $*"\n')
        (self.venv() / VENV_MARKER).write_text("", encoding="utf-8")
        result = self.run_script(
            root / ADR_LAUNCHER, str(self.data), "check", PATH=self.failing_uv()
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"RAN {root / SKILL_DIR / 'adr.py'} check\n")

    def test_launcher_resyncs_a_venv_whose_python_dangles(self):
        """A marked venv whose interpreter has gone is rebuilt, not trusted, and the tool runs."""
        root = self.cache_root()
        synced = self.sync(root)
        self.assertEqual(synced.returncode, 0, synced.stderr)
        python = self.venv() / VENV_PYTHON
        python.unlink()
        python.symlink_to(self.tmp / "no-such-python")
        result = self.run_script(
            root / ADR_LAUNCHER, str(self.data), "--repo-root", str(self.project), "check"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(python.exists())

    def test_launcher_defers_to_the_sync_reason_it_failed_with(self):
        """A refused data directory is reported as such, not blamed on uv or the network alone."""
        root = self.cache_root()
        result = self.run_script(root / ADR_LAUNCHER, "relative/data", "check")
        self.assertEqual(result.returncode, 3, result.stderr)
        *reasons, final = result.stderr.strip().splitlines()
        self.assertIn("relative/data", "\n".join(reasons))
        self.assertIn("reason above", final)

    def test_launcher_exits_3_when_it_cannot_build_its_environment(self):
        """A failed sync is its own exit code, naming uv and the network, never a tool refusal."""
        root = self.cache_root()
        result = self.run_script(
            root / ADR_LAUNCHER, str(self.data), "check", PATH=self.failing_uv()
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn(
            "Error: the writing-adrs tool could not build its environment:", result.stderr
        )
        self.assertIn("uv", result.stderr)
        self.assertIn("network", result.stderr)
