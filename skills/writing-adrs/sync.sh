#!/bin/sh
# Build the writing-adrs tool's Python environment with uv, and print its python's path.
#
#   sh sync.sh DATA_DIR [--if-needed]
#
# DATA_DIR is the plugin's data directory, CLAUDE_PLUGIN_DATA. Under the plugin cache the
# venv is DATA_DIR/venvs/<plugin version>; in a checkout it is the checkout's own workspace
# venv, ${UV_PROJECT_ENVIRONMENT:-.venv} resolved against the plugin root. Stdout carries
# only the python path, so a caller can capture it; uv's output and every error go to
# stderr. With --if-needed, a venv already marked complete is reused without calling uv.
set -u

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ] || { [ "$#" -eq 2 ] && [ "$2" != "--if-needed" ]; }; then
    printf '%s\n' "usage: sh sync.sh DATA_DIR [--if-needed]" >&2
    exit 2
fi
data="$1"
if_needed="${2:-}"

# The plugin root is this script's grandparent, taken from the path it was run by and a
# logical pwd: never CLAUDE_PLUGIN_ROOT, and never resolved physically, which would carry a
# symlinked version directory out of the plugin cache.
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1
root="${here%/*}"
root="${root%/*}"

case "$root" in
    */plugins/cache/*)
        cached=1
        if [ -z "$data" ]; then
            printf '%s\n' "sync.sh: no plugin data directory (CLAUDE_PLUGIN_DATA is empty); nowhere to build the venv" >&2
            exit 1
        fi
        # uv resolves a relative venv path against the project, which here is the plugin
        # cache, and nothing may be built inside a cached plugin version. An agent quoting
        # ${CLAUDE_PLUGIN_DATA} so it is never substituted lands here too.
        case "$data" in
            /*) ;;
            *)
                printf '%s\n' "sync.sh: the plugin data directory '$data' is not an absolute path; pass the substituted CLAUDE_PLUGIN_DATA" >&2
                exit 1
                ;;
        esac
        version="${root##*/}"
        venv="$data/venvs/$version"
        ;;
    *)
        cached=0
        venv="${UV_PROJECT_ENVIRONMENT:-.venv}"
        case "$venv" in
            /*) ;;
            *) venv="$root/$venv" ;;
        esac
        # `.` components name nothing, so drop them: `./.venv` is the checkout's `.venv`, and
        # uv, the marker and the printed path all get the one spelling.
        while :; do
            case "$venv" in
                */./*) venv="${venv%%/./*}/${venv#*/./}" ;;
                */.) venv="${venv%/.}" ;;
                *) break ;;
            esac
        done
        # uv deletes and rebuilds a venv whose interpreter misses requires-python, even with
        # --inexact, so a venv elsewhere — another project's — is never handed to it, nor is
        # the checkout itself. A `..` component is refused outright, since it can resolve
        # outside the checkout while still matching the prefix. An in-checkout symlink
        # pointing out of it is still accepted: only the path's text is judged.
        case "/$venv/" in
            */../*) venv_ok=0 ;;
            *)
                case "$venv" in
                    "$root" | "$root"/) venv_ok=0 ;;
                    "$root"/*) venv_ok=1 ;;
                    *) venv_ok=0 ;;
                esac
                ;;
        esac
        case "$venv_ok" in
            1) ;;
            *)
                printf '%s\n' "sync.sh: UV_PROJECT_ENVIRONMENT names '$venv', which is not a path inside this checkout ($root); unset UV_PROJECT_ENVIRONMENT for this checkout, or point it inside it" >&2
                exit 1
                ;;
        esac
        ;;
esac
# Absolute in both layouts, so uv and the hooks agree on one path.
UV_PROJECT_ENVIRONMENT="$venv"
export UV_PROJECT_ENVIRONMENT
marker="$venv/.phx-synced"
python="$venv/bin/python"

if [ -n "$if_needed" ] && [ -f "$marker" ] && [ -x "$python" ]; then
    printf '%s\n' "$python"
    exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' "sync.sh: uv is not on PATH; install it to build the writing-adrs environment" >&2
    exit 1
fi

# Unmarked for the whole sync, so an interrupted one never leaves the hooks running a
# half-updated venv.
rm -f "$marker"
if [ "$cached" -eq 1 ]; then
    uv sync --project "$root" --frozen --package writing-adrs --no-dev --no-install-project --quiet >&2
else
    # The developer's workspace venv: add the skill's dependencies, remove nothing.
    uv sync --project "$root" --frozen --package writing-adrs --no-dev --no-install-project --quiet --inexact >&2
fi
status=$?
if [ "$status" -ne 0 ]; then
    printf '%s\n' "sync.sh: uv sync failed (exit $status) building $venv" >&2
    exit 1
fi
: >"$marker" || exit 1

# Drop the venv of each version whose directory has left the plugin cache, so no session
# still running one loses it. The version just synced is always kept, even if its own
# directory was removed during the sync, so the python path printed below still exists.
# The parent is the root's string trimmed, never `..`, which the kernel resolves
# physically through a symlinked version directory.
if [ "$cached" -eq 1 ]; then
    for old in "$data/venvs"/*; do
        [ -d "$old" ] || continue
        [ "${old##*/}" = "$version" ] && continue
        [ -d "${root%/*}/${old##*/}" ] && continue
        rm -rf -- "$old"
    done
fi

printf '%s\n' "$python"
