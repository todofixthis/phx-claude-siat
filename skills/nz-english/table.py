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

ROWS = (
    Row(
        us="-ize / -ization",
        nz="-ise / -isation",
        patterns=(Pattern(r"\w{3,}iz(e|ing|er|ation|abl)"),),
    ),
    Row(us="-yze", nz="-yse", patterns=(Pattern("lyz"),)),
    Row(us="-or endings", nz="-our", patterns=(Pattern(f"({_OUR_WORDS})"),)),
    Row(
        us="-er endings (root words)",
        nz="-re",
        patterns=(
            Pattern(f"({_RE_WORDS})"),
            Pattern("meter", judgement=True, span_label="meter"),
        ),
    ),
    Row(
        us="-og endings",
        nz="-ogue",
        patterns=(Pattern(f"({_OG_WORDS}){_OG_GUARD}"),),
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
        patterns=(Pattern(r"\w{2,}el(ed|ing|er)"),),
    ),
    Row(us="gray", nz="grey", patterns=(Pattern("gray"),)),
    Row(
        us="defense / offense / pretense",
        nz="defence / offence / pretence",
        patterns=(Pattern("(defense|offense|pretense)"),),
    ),
    Row(us="skeptic", nz="sceptic", patterns=(Pattern("skeptic"),)),
    Row(
        us="judgment / acknowledgment",
        nz="judgement / acknowledgement",
        # Split, because only `judgment` needs reading — a court's keeps that spelling.
        # `acknowledgment` always converts, and a bare row mark would tell a reader to
        # weigh a decision that does not exist.
        patterns=(
            Pattern("judgment", judgement=True, span_label="judgment"),
            Pattern("acknowledgment"),
        ),
    ),
    Row(us="license (noun)", nz="licence", patterns=(Pattern("license", judgement=True),)),
    Row(
        us="practice (verb)",
        nz="practise",
        patterns=(
            Pattern("practice", judgement=True, span_label="practice"),
            Pattern("(practiced|practicing)"),
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
        patterns=(Pattern("(aluminum|artifact|aging)"),),
    ),
    Row(
        us="fulfill / enroll",
        nz="fulfil / enrol",
        # The `-ment` forms are their own row below, and `(fulfill|enroll)` would
        # otherwise claim them too — one conversion reported under two rows, which reads
        # as two things to do.
        patterns=(Pattern("(fulfill|enroll)(?!ment)"),),
    ),
    Row(
        us="fulfillment / enrollment",
        nz="fulfilment / enrolment",
        patterns=(Pattern("(fulfillment|enrollment)"),),
    ),
    Row(us="sizable", nz="sizeable", patterns=(Pattern("sizable"),)),
)

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
        "imaging",
        "kneeling",
        "laboratory",
        "literal",
        "literally",
        "literary",
        "literature",
        "managing",
        "messaging",
        "oversize",
        "packaging",
        "parameter",
        "peeler",
        "peeling",
        "perimeter",
        "resize",
        "staging",
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
