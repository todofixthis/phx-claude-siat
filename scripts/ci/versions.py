"""The version shape this project releases, shared by the scripts asserting it.

Stdlib-only, like everything under scripts/ (ADR 007). Both importers live in
the scripts package, so either resolves this import when run as
`python3 -m scripts.ci.<name>` from the repo root (ADR 011).

Deliberately narrower than the semver grammar: no pre-release suffix and no build
metadata, because neither can be released here (ADR 008). One definition rather
than one per script — two regexes drifting apart is how a version passes the
pull-request gate and then fails the release.
"""

import re

NUMBER = r"(?:0|[1-9]\d*)"
VERSION = rf"{NUMBER}\.{NUMBER}\.{NUMBER}"

RE_VERSION = re.compile(rf"^{VERSION}$")
