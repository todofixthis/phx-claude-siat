"""Unit tests for each pattern's `suggest` rule in `table.py`, one class per rule shape.

Each rule takes one lowercase word segment and returns its NZ spelling or None. The cases
are the inflections each class has to get right, and the shapes it must decline rather
than guess at: a declined segment prints no suggestion, where a wrong one reads as an
instruction. No paths are involved, so nothing here touches the working directory.
"""

import unittest
from collections.abc import Callable

from table import ROWS


def rule(us: str, regex_start: str = "") -> Callable[[str], str | None]:
    """The `suggest` rule of the row labelled `us`, on its pattern opening `regex_start`."""
    row = next(row for row in ROWS if row.us == us)
    return next(p.suggest for p in row.patterns if p.regex.startswith(regex_start))


class RuleTestCase(unittest.TestCase):
    """Asserts a table of segment → expected suggestion, each case its own subtest."""

    def assert_rule(self, suggest: Callable[[str], str | None], cases: dict) -> None:
        for segment, expected in cases.items():
            with self.subTest(segment=segment):
                self.assertEqual(suggest(segment), expected)


class CoverageTests(unittest.TestCase):
    """Which patterns carry a rule at all."""

    def test_every_judgement_pattern_carries_no_rule(self):
        """A judgement pattern's answer depends on the occurrence, so it must never suggest."""
        judgement = [p for row in ROWS for p in row.patterns if p.judgement]
        self.assertEqual(
            sorted(p.regex for p in judgement),
            ["judgment", "license", "meter", "practice", "program"],
        )
        for pattern in judgement:
            with self.subTest(pattern=pattern.regex):
                self.assertIsNone(pattern.suggest)

    def test_every_other_pattern_carries_a_rule(self):
        """A non-judgement pattern with no rule would silently print no suggestion."""
        for row in ROWS:
            for pattern in row.patterns:
                if not pattern.judgement:
                    with self.subTest(pattern=pattern.regex):
                        self.assertIsNotNone(pattern.suggest)


class IzeRuleTests(RuleTestCase):
    """The `-ize` rule: `iz` becomes `is` in every inflection the pattern reaches."""

    def test_converts_each_inflection(self):
        """Every ending the pattern reaches keeps its tail and swaps the `z`."""
        self.assert_rule(
            rule("-ize / -ization"),
            {
                "organize": "organise",
                "organizer": "organiser",
                "organizing": "organising",
                "organizational": "organisational",
                "realizable": "realisable",
            },
        )

    def test_declines_a_size_compound_and_other_unlisted_s_stems(self):
        """`bufsize` would come back `bufsise`; an `s` stem converts only where listed."""
        self.assert_rule(
            rule("-ize / -ization"),
            {
                "assizes": None,
                "bufsize": None,
                "outsized": None,
                "pagesize": None,
                "resizer": None,
                "upsize": None,
            },
        )

    def test_converts_a_listed_s_stem(self):
        """`emphasize` and `hypothesize` are real `-ize` words ending their stem in `s`."""
        self.assert_rule(
            rule("-ize / -ization"),
            {
                "deemphasized": "deemphasised",
                "emphasize": "emphasise",
                "hypothesizing": "hypothesising",
            },
        )

    def test_declines_a_word_that_only_looks_like_ize(self):
        """`Belize`, `apprize` and `reseize` are not `-ize` words."""
        self.assert_rule(
            rule("-ize / -ization"), {"apprize": None, "belize": None, "reseized": None}
        )

    def test_declines_an_unlisted_tail(self):
        """`denizen` matches the pattern but is not an `-ize` word."""
        self.assertIsNone(rule("-ize / -ization")("denizen"))

    def test_declines_a_segment_the_pattern_does_not_reach(self):
        """A segment too short to carry the stem is not an `-ize` word."""
        self.assertIsNone(rule("-ize / -ization")("izer"))


class YzeRuleTests(RuleTestCase):
    """The `-yze` rule."""

    def test_converts_each_inflection(self):
        """The `z` swaps whatever follows it."""
        self.assert_rule(
            rule("-yze"),
            {"analyze": "analyse", "analyzing": "analysing", "paralyzed": "paralysed"},
        )


class OurRuleTests(RuleTestCase):
    """The `-or` rule: the `u` survives before the listed suffixes only."""

    def test_converts_before_a_suffix_the_u_survives(self):
        """Suffixes that attach freely keep the root's `u`, prefixes included."""
        self.assert_rule(
            rule("-or endings"),
            {
                "behaviorist": "behaviourist",
                "colorful": "colourful",
                "colorist": "colourist",
                "favorite": "favourite",
                "honorable": "honourable",
                "labored": "laboured",
                "neighborly": "neighbourly",
                "watercolor": "watercolour",
            },
        )

    def test_converts_after_a_listed_prefix_only(self):
        """`recolor` converts; `Theodor` is a name, not a prefixed `odor`."""
        self.assert_rule(
            rule("-or endings"),
            {"dishonor": "dishonour", "fyodor": None, "recolor": "recolour", "theodor": None},
        )

    def test_keeps_the_per_word_extras_to_their_word(self):
        """`colourise` and `behavioural` keep the `u`; `glamorise` and `humoral` do not."""
        self.assert_rule(
            rule("-or endings"),
            {
                "behavioral": "behavioural",
                "colorize": "colourize",
                "glamorize": None,
                "humoral": None,
            },
        )

    def test_declines_a_suffix_it_does_not_list(self):
        """`armorial`, `arborist`, `deodorant` and `valorous` keep no `u`, and none is invented."""
        self.assert_rule(
            rule("-or endings"),
            {"arborist": None, "armorial": None, "deodorant": None, "valorous": None},
        )


class ReRuleTests(RuleTestCase):
    """The `-re` rule: `er` becomes `re`, merging the `e` at an inflection."""

    def test_converts_each_inflection(self):
        """`centering` drops the `e` before `-ing`; `centreing` is the misspelling to avoid."""
        self.assert_rule(
            rule("-er endings (root words)", "("),
            {
                "center": "centre",
                "centered": "centred",
                "centering": "centring",
                "centers": "centres",
                "fiberglass": "fibreglass",
                "somberly": "sombrely",
                "theatergoers": "theatregoers",
            },
        )

    def test_converts_after_a_listed_prefix(self):
        """A listed prefix is carried through unchanged."""
        self.assert_rule(
            rule("-er endings (root words)", "("),
            {
                "epicenter": "epicentre",
                "milliliters": "millilitres",
                "lackluster": "lacklustre",
            },
        )

    def test_declines_a_root_inside_another_word(self):
        """An open prefix would turn `fluster` into `flustre`."""
        self.assert_rule(
            rule("-er endings (root words)", "("), {"fluster": None, "literate": None}
        )


class OgRuleTests(RuleTestCase):
    """The `-og` rule: append `ue`, merging the `e` at an inflection."""

    def test_converts_each_inflection(self):
        """`ue` is appended, and an `e` or `i` suffix merges with it."""
        self.assert_rule(
            rule("-og endings"),
            {
                "catalog": "catalogue",
                "cataloged": "catalogued",
                "cataloger": "cataloguer",
                "cataloging": "cataloguing",
                "dialogs": "dialogues",
            },
        )

    def test_declines_prolog(self):
        """In code `Prolog` is the language, whose name takes no `ue`."""
        self.assertIsNone(rule("-og endings")("prolog"))

    def test_declines_the_already_correct_form(self):
        """A substring rewrite of `dialogue` would produce `dialogueue`."""
        self.assertIsNone(rule("-og endings")("dialogue"))


class ElRuleTests(RuleTestCase):
    """The `-el` rule: double the `l` after a single vowel."""

    def test_converts_each_inflection(self):
        """The `l` doubles, and a plural rides along."""
        self.assert_rule(
            rule("-eled / -eling / -eler"),
            {
                "labeler": "labeller",
                "modeling": "modelling",
                "traveled": "travelled",
                "travelers": "travellers",
            },
        )

    def test_declines_after_two_vowels_and_in_paralleled(self):
        """`peelled` and `parallelled` would be misspellings handed over as corrections."""
        self.assert_rule(
            rule("-eled / -eling / -eler"),
            {"kneeled": None, "paralleled": None, "peeled": None},
        )


class FixedWordRuleTests(RuleTestCase):
    """The rows naming fixed words, which convert only as a whole segment."""

    def test_converts_each_fixed_word(self):
        """Each fixed-word row converts its word with a listed affix."""
        cases = {
            "gray": ("grayscale", "greyscale"),
            "defense / offense / pretense": ("defenseless", "defenceless"),
            "skeptic": ("skeptical", "sceptical"),
            "aluminum / artifact / aging": ("artifacts", "artefacts"),
            "fulfill / enroll": ("reenrolls", "reenrols"),
            "fulfillment / enrollment": ("fulfillments", "fulfilments"),
            "sizable": ("sizable", "sizeable"),
        }
        for us, (segment, expected) in cases.items():
            with self.subTest(row=us):
                self.assertEqual(rule(us)(segment), expected)

    def test_converts_the_non_judgement_patterns_on_mixed_rows(self):
        """`acknowledgment` and `practiced` convert though their rows carry a judgement pattern."""
        self.assertEqual(
            rule("judgment / acknowledgment", "ack")("acknowledgments"), "acknowledgements"
        )
        self.assertEqual(rule("practice (verb)", "(")("unpracticed"), "unpractised")

    def test_declines_a_word_inside_another(self):
        """`stingray` is not `stingrey`."""
        self.assertIsNone(rule("gray")("stingray"))


if __name__ == "__main__":
    unittest.main()
