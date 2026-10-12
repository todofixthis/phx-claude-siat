#!/bin/sh
# Run the writing-adrs tool from its uv-synced environment, building that first if needed.
#
#   sh adr.sh DATA_DIR COMMAND [ARGS...]
#
# DATA_DIR is the plugin's data directory, CLAUDE_PLUGIN_DATA. Exits 3 where the
# environment cannot be built, apart from argparse's 2 for a bad flag and the tool's 1 for
# a refusal; otherwise exits with the tool's own code.
set -u

if [ "$#" -lt 1 ]; then
    printf '%s\n' "usage: sh adr.sh DATA_DIR COMMAND [ARGS...]" >&2
    exit 2
fi
data="$1"
shift

here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1

if ! python=$(sh "$here/sync.sh" "$data" --if-needed </dev/null); then
    printf '%s\n' "Error: the writing-adrs tool could not build its environment: it needs uv on PATH, and the network on its first run after each plugin update." >&2
    exit 3
fi
exec "$python" "$here/adr.py" "$@"
