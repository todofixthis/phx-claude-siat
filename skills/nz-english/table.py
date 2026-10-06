"""The substitution table, as data.

One canonical source for the sweep patterns, the noise classification, the guard
characters `--verify` derives, and the coupling test. `SKILL.md`'s table is what a
reader consults for what a word becomes; this is what the tool searches with. The two
are held together by the coupling assertions in `tests/test_table.py` — a row here with
no counterpart there, or the reverse, fails the suite.

Rows and patterns are not the same count. `SKILL.md` has 17 rows but nine searches,
because two searches belong to no row of their own: `meter` is held out of the `-er`
search because it is the one `-er` word that needs reading, and `practiced`/`practicing`
covers inflections the `practice` pattern cannot reach (`practice` carries an `e` where
`practicing` carries an `i`). So a row may carry several patterns, and judgement is a
property of the pattern rather than the row.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Pattern:
    """One search, and whether its hits can be applied without reading them.

    `judgement` marks a pattern whose hits need a decision per occurrence rather than a
    substitution — `license` (noun or verb), `program` (correct in computing), `meter`
    (correct unless it is the unit of length). `span_label` names the pattern in the
    report where its row carries more than one, so a reader can tell which hits on a
    mixed row are the judgement ones.
    """

    regex: str
    judgement: bool = False
    span_label: str = ""
    # Rewrites one lowercase word segment this pattern matched into its NZ spelling, or
    # returns None where the segment is not a form the rule knows. None on a judgement
    # pattern: its answer depends on the occurrence, so no suggestion is printed for it.
    suggest: Callable[[str], str | None] | None = None


# `eq=False` keeps identity hashing, so a Row can key a results dict despite carrying a
# mapping. The rows are module-level singletons, so identity is the comparison wanted.
@dataclass(frozen=True, eq=False)
class Row:
    """One row of `SKILL.md`'s substitution table.

    `us` and `nz` are the labels the report prints, matching the table's two columns.
    `nz_forms` maps a US member word to its NZ spelling, and is populated only where
    `--verify` needs it: the US form must be a prefix of the NZ form for a guard
    character to exist at all, which across the whole table is true only of the `-ogue`
    family and `program`/`programme`. Everywhere else the two spellings diverge before
    the end, so no guard is possible and none is needed.
    """

    us: str
    nz: str
    patterns: tuple[Pattern, ...]
    nz_forms: dict = field(default_factory=dict)


# Enumerated members of the three class rows. Nothing distinguishes `color` from `error`
# by shape, so these rows are complete only for the words listed, and adding a word here
# without adding it to SKILL.md's row (or the reverse) fails the coupling test.
_OUR_WORDS = (
    "color|behavior|honor|flavor|favor|labor|vapor|rigor|vigor|odor|armor|neighbor|"
    "harbor|savor|endeavor|humor|splendor|candor|valor|parlor|clamor|glamor|tumor|"
    "rumor|savior|arbor|ardor|fervor|rancor|succor|demeanor"
)

# `meter` is deliberately absent — it is a judgement pattern on this row, below.
_RE_WORDS = "center|fiber|theater|liter|somber|specter|caliber|meager|saber|luster|sepulcher"

_OG_WORDS = (
    "catalog|dialog|analog|monolog|prolog|epilog|travelog|homolog|pedagog|demagog|"
    "synagog|decalog|ideolog"
)

# The right-end guard. Left open this matches the already-correct `catalogue`; anchored
# it drops `catalog_id` and forces every inflection to be listed by hand, which is how
# `cataloged` and `cataloging` once went missing. Demanding that the next character not
# be `u` keeps both.
#
# A lookahead rather than the `([^u]|$)` character class the hand-run searches used: the
# class consumes the character it tests, so the reported span came back as `dialog(`
# instead of `dialog`. It also needed the `|$` arm to match at end of line, which a
# lookahead gets for free.
#
# `(?-i:…)` turns case-insensitivity off for the guard alone. Under the surrounding
# IGNORECASE a bare `(?!u)` also excludes `U`, which let a camel-cased `dialogUrl` escape
# every search — a real miss the hand-run version had to document and convert by hand.
# Scoping the flag catches it, at the cost of reporting a SCREAMING_CASE `DIALOGUE`,
# which is over-reporting and the direction this skill prefers.
_OG_GUARD = "(?-i:(?!u))"

# The class labels in SKILL.md's US column that name a shape rather than a word. The
# coupling test allows these to have no literal in the table below; every other
# backticked token in that column must be one.
CLASS_LABELS = (
    "-eled",
    "-eler",
    "-eling",
    "-er",
    "-ize",
    "-ization",
    "-og",
    "-or",
    "-yze",
)

# Suggestion rules. Each takes one lowercase word segment — a camel-case or snake-case
# part, never a whole identifier — and returns its NZ spelling, or None. None is the
# answer for any inflection a rule does not list: a suggestion that is wrong looks as
# authoritative as one that is right, so an unknown shape gets no suggestion rather
# than a guess. Rules match the whole segment, which is what keeps `stingray` from
# becoming `stingrey` and `fluster` from becoming `flustre`.

# Suffixes the `-our` survives before. The drop list (`-ary`, `-ate`, `-ific`, `-ous`,
# `-ious`) is absent, as are suffixes with a variant in either direction (`-al`, `-ation`,
# `-ize`) — `humoral`, `coloration` and `glamorise` keep no `u`.
_OUR_SUFFIXES = frozenset(
    {
        "",
        "able",
        "ably",
        "ed",
        "er",
        "ers",
        "ful",
        "fully",
        "hood",
        "hoods",
        "ing",
        "ism",
        "ite",
        "ites",
        "itism",
        "less",
        "lessly",
        "liness",
        "ly",
        "s",
        "some",
        "y",
    }
)
# Per-word extras: `colourise`, `colourist` and `behavioural` keep the `u`; `glamorise`,
# `arborist` and `humoral` do not, so these are not shared.
_OUR_EXTRAS = {
    "behavior": frozenset({"al", "ally", "ist", "ists"}),
    "color": frozenset(
        {
            "isation",
            "ise",
            "ised",
            "iser",
            "isers",
            "ises",
            "ising",
            "ist",
            "ists",
            "ization",
            "ize",
            "ized",
            "izer",
            "izers",
            "izes",
            "izing",
        }
    ),
}


def _whole(
    roots: dict,
    suffixes: frozenset,
    prefixes: frozenset = frozenset({""}),
    *,
    merge: bool = False,
) -> Callable[[str], str | None]:
    """A rule swapping a listed root for its NZ form, between listed prefixes and suffixes.

    `suffixes` may be a mapping from root to extra suffixes as well. `merge` is for NZ
    roots ending in `e` (`centre`, `catalogue`): a suffix opening with `e` loses it
    (`centred`), and one opening with `i` takes the root's `e` instead (`centring`).
    """
    regex = re.compile(
        "(" + "|".join(sorted(prefixes, key=len, reverse=True)) + ")"
        "(" + "|".join(sorted(roots, key=len, reverse=True)) + r")([a-z]*)"
    )

    def rule(segment: str) -> str | None:
        match = regex.fullmatch(segment)
        if not match:
            return None
        prefix, root, suffix = match.groups()
        allowed = suffixes | _OUR_EXTRAS.get(root, frozenset()) if roots is _OUR else suffixes
        if suffix not in allowed:
            return None
        nz = roots[root]
        if merge and suffix[:1] == "e":
            suffix = suffix[1:]
        elif merge and suffix[:1] == "i":
            nz = nz[:-1]
        return prefix + nz + suffix

    return rule


# The `-sise` words this rule converts. Code joins `size` to anything (`bufsize`,
# `pagesize`), so a stem ending in `s` converts only where listed: an unlisted one gets no
# suggestion rather than `bufsise`. Matched as a stem ending, so `deemphasize` qualifies.
_IZE_S_STEMS = (
    "anaesthes",
    "anesthes",
    "emphas",
    "fantas",
    "hypothes",
    "metastas",
    "parenthes",
    "synthes",
)
# Stems that look like an `-ize` word's but are not: `Belize`, `apprize`, which is not
# `apprise`.
_NOT_IZE_STEMS = frozenset({"appr", "bel"})
# What may follow each ending the pattern matches. `denizen` is `den` + `ize` + `n`, and
# is not an `-ize` word.
_IZE_TAILS = {
    "abl": frozenset({"e", "y"}),
    "ation": frozenset({"", "al", "ally", "s"}),
    "e": frozenset({"", "d", "r", "rs", "s"}),
    "er": frozenset({"", "s"}),
    "ing": frozenset({"", "s"}),
}


def _ize(segment: str) -> str | None:
    """`-iz` becomes `-is`, except after an unlisted `s` stem and before an unlisted tail."""
    match = re.fullmatch(r"([a-z]{3,})iz(e|ing|er|ation|abl)([a-z]*)", segment)
    if not match:
        return None
    stem, ending, tail = match.groups()
    if tail not in _IZE_TAILS[ending] or stem in _NOT_IZE_STEMS:
        return None
    # `seize` and its compounds (`reseize`) keep their `z`.
    if stem.endswith("se") or (stem.endswith("s") and not stem.endswith(_IZE_S_STEMS)):
        return None
    return f"{stem}is{ending}{tail}"


def _yze(segment: str) -> str | None:
    """`-lyz-` becomes `-lys-`, in every inflection."""
    return segment.replace("lyz", "lys", 1) if "lyz" in segment else None


def _el(segment: str) -> str | None:
    """Double the `l` after a single vowel: `traveled` to `travelled`.

    Not after two vowels (`peeled`, `kneeled`), and not in `paralleled`, the one common
    `-el` verb whose stress keeps a single `l` in NZ spelling too.
    """
    match = re.fullmatch(r"([a-z]*[^aeiou])el(ed|ing|er)(s?)", segment)
    if not match or match.group(1).endswith("all"):
        return None
    stem, ending, plural = match.groups()
    return f"{stem}ell{ending}{plural}"


_OUR = {word: word[:-1] + "ur" for word in _OUR_WORDS.split("|")}
_RE = {word: word[:-2] + "re" for word in _RE_WORDS.split("|")}
# Left out: `prolog`, in a code repository nearly always the language, whose name takes
# no `ue`; and `analog`, which in code more often names something fixed outside the
# repository (an ADC's `analog` pin, a library's API) than a word it owns. An arrow would
# read as settling a question only the reader can answer; the row still converts both.
_OG = {word: word + "ue" for word in _OG_WORDS.split("|") if word not in {"analog", "prolog"}}

# Any prefix: `monologue`, `travelogue`. The suffix list still bounds it.
_ANY = frozenset({"[a-z]*"})
# Listed rather than open: an open prefix turns `Theodor` into `Theodour`.
_OUR_PREFIXES = frozenset({"", "bi", "dis", "mis", "multi", "re", "tri", "un", "water"})
_GREY_SUFFIXES = frozenset({"", "ed", "er", "est", "ing", "ish", "ness", "s", "scale"})
_OG_SUFFIXES = frozenset({"", "ed", "er", "ers", "ing", "s"})
_PLURAL = frozenset({"", "s"})
_RE_PREFIX = frozenset({"", "re"})
# Listed rather than open, unlike `_ANY`: an open prefix turns `fluster` into `flustre`.
_RE_PREFIXES = frozenset(
    {"", "amphi", "centi", "deci", "epi", "kilo", "lack", "micro", "milli"}
)
_RE_SUFFIXES = frozenset(
    {
        "",
        "ed",
        "fold",
        "glass",
        "goer",
        "goers",
        "ing",
        "less",
        "line",
        "lines",
        "ly",
        "ness",
        "piece",
        "pieces",
        "s",
    }
)

ROWS = (
    Row(
        us="-ize / -ization",
        nz="-ise / -isation",
        patterns=(Pattern(r"\w{3,}iz(e|ing|er|ation|abl)", suggest=_ize),),
    ),
    Row(us="-yze", nz="-yse", patterns=(Pattern("lyz", suggest=_yze),)),
    Row(
        us="-or endings",
        nz="-our",
        patterns=(
            Pattern(
                f"({_OUR_WORDS})", suggest=_whole(_OUR, _OUR_SUFFIXES, prefixes=_OUR_PREFIXES)
            ),
        ),
    ),
    Row(
        us="-er endings (root words)",
        nz="-re",
        patterns=(
            Pattern(
                f"({_RE_WORDS})",
                suggest=_whole(_RE, _RE_SUFFIXES, prefixes=_RE_PREFIXES, merge=True),
            ),
            Pattern("meter", judgement=True, span_label="meter"),
        ),
    ),
    Row(
        us="-og endings",
        nz="-ogue",
        patterns=(
            Pattern(
                f"({_OG_WORDS}){_OG_GUARD}",
                suggest=_whole(_OG, _OG_SUFFIXES, prefixes=_ANY, merge=True),
            ),
        ),
        nz_forms={
            "analog": "analogue",
            "catalog": "catalogue",
            "decalog": "decalogue",
            "demagog": "demagogue",
            "dialog": "dialogue",
            "epilog": "epilogue",
            "homolog": "homologue",
            "ideolog": "ideologue",
            "monolog": "monologue",
            "pedagog": "pedagogue",
            "prolog": "prologue",
            "synagog": "synagogue",
            "travelog": "travelogue",
        },
    ),
    Row(
        us="-eled / -eling / -eler",
        nz="-elled / -elling / -eller",
        patterns=(Pattern(r"\w{2,}el(ed|ing|er)", suggest=_el),),
    ),
    Row(
        us="gray",
        nz="grey",
        patterns=(Pattern("gray", suggest=_whole({"gray": "grey"}, _GREY_SUFFIXES)),),
    ),
    Row(
        us="defense / offense / pretense",
        nz="defence / offence / pretence",
        patterns=(
            Pattern(
                "(defense|offense|pretense)",
                suggest=_whole(
                    {"defense": "defence", "offense": "offence", "pretense": "pretence"},
                    frozenset({"", "less", "s"}),
                ),
            ),
        ),
    ),
    Row(
        us="skeptic",
        nz="sceptic",
        patterns=(
            Pattern(
                "skeptic",
                suggest=_whole(
                    {"skeptic": "sceptic"}, frozenset({"", "al", "ally", "ism", "s"})
                ),
            ),
        ),
    ),
    Row(
        us="judgment / acknowledgment",
        nz="judgement / acknowledgement",
        # Split, because only `judgment` needs reading — a court's keeps that spelling.
        # `acknowledgment` always converts, and a bare row mark would tell a reader to
        # weigh a decision that does not exist.
        patterns=(
            Pattern("judgment", judgement=True, span_label="judgment"),
            Pattern(
                "acknowledgment",
                suggest=_whole({"acknowledgment": "acknowledgement"}, _PLURAL),
            ),
        ),
    ),
    Row(us="license (noun)", nz="licence", patterns=(Pattern("license", judgement=True),)),
    Row(
        us="practice (verb)",
        nz="practise",
        patterns=(
            Pattern("practice", judgement=True, span_label="practice"),
            Pattern(
                "(practiced|practicing)",
                suggest=_whole(
                    {"practiced": "practised", "practicing": "practising"},
                    frozenset({""}),
                    prefixes=frozenset({"", "un"}),
                ),
            ),
        ),
    ),
    Row(
        us="program",
        nz="programme",
        patterns=(Pattern("program", judgement=True),),
        nz_forms={"program": "programme"},
    ),
    Row(
        us="aluminum / artifact / aging",
        nz="aluminium / artefact / ageing",
        patterns=(
            Pattern(
                "(aluminum|artifact|aging)",
                suggest=_whole(
                    {"aging": "ageing", "aluminum": "aluminium", "artifact": "artefact"},
                    _PLURAL,
                ),
            ),
        ),
    ),
    Row(
        us="fulfill / enroll",
        nz="fulfil / enrol",
        # The `-ment` forms are their own row below, and `(fulfill|enroll)` would
        # otherwise claim them too — one conversion reported under two rows, which reads
        # as two things to do.
        patterns=(
            Pattern(
                "(fulfill|enroll)(?!ment)",
                suggest=_whole(
                    {"enroll": "enrol", "fulfill": "fulfil"}, _PLURAL, prefixes=_RE_PREFIX
                ),
            ),
        ),
    ),
    Row(
        us="fulfillment / enrollment",
        nz="fulfilment / enrolment",
        patterns=(
            Pattern(
                "(fulfillment|enrollment)",
                suggest=_whole(
                    {"enrollment": "enrolment", "fulfillment": "fulfilment"},
                    _PLURAL,
                    prefixes=_RE_PREFIX,
                ),
            ),
        ),
    ),
    Row(
        us="sizable",
        nz="sizeable",
        patterns=(
            Pattern("sizable", suggest=_whole({"sizable": "sizeable"}, frozenset({""}))),
        ),
    ),
)

# A suffix whose matched words are noise unless the word IS the suffix. `NOISE` below
# names each word by hand — right for the `-our` drop list, which is closed and
# irregular. This is the other shape: the aluminum/artifact/aging row's unanchored
# `aging` pattern matches inside any word containing it, and every one of those longer
# words is a false positive by the same rule, not a fact to notice and enumerate one at
# a time — `triaging`, `damaging`, `encouraging`, and any other `-aging` word not yet
# met. `aging` on its own is still the real hit, so it is excluded by being equal to the
# suffix rather than longer than it.
NOISE_SUFFIXES = frozenset({"aging"})

# Words a pattern matches that are already correct, so a reader has nothing to decide
# about them. Compared case-folded, like the sweep, or `Literal` reports as a hit while
# `literal` is noise.
#
# Only already-correct words belong here. `colorist` and `behaviorist` appear in
# SKILL.md's noise section and are *real* hits — the `-our` survives before those
# suffixes — so filing them here would ship the miss the skill treats as the serious
# direction.
NOISE = frozenset(
    {
        # The -our drop list: the u genuinely goes before -ary, -ate, -ific, -ous, -ious.
        "clamorous",
        "glamorous",
        "honorary",
        "honorific",
        "humorist",
        "humorous",
        "invigorate",
        "laborious",
        "odorous",
        "rigorous",
        "vigorous",
        # Unrelated words the open-ended patterns reach.
        "accelerate",
        "accelerator",
        "arboretum",
        "bluster",
        "capsize",
        "citizen",
        "citizenship",
        "cluster",
        "collaborate",
        "colorado",
        "colorectal",
        "diameter",
        "downsize",
        "elaborate",
        "elaborates",
        "evaporate",
        "evaporation",
        "feeling",
        "kneeling",
        "laboratory",
        "literal",
        "literally",
        "literary",
        "literature",
        "oversize",
        "parameter",
        "peeler",
        "peeling",
        "perimeter",
        "resize",
        "wheeling",
        # Already-correct NZ forms the patterns match by construction.
        "analogous",
        "analogy",
        "enrolled",
        "enrolling",
        "fulfilled",
        "fulfilling",
        "homologous",
        "ideological",
        "ideology",
        "pedagogy",
        "programme",
        # Always-correct inflections of the license row.
        "licensed",
        "licensee",
    }
)
