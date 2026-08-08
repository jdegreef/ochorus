"""The cross-work verse ratchet, and the checks that keep it honest.

Two jobs, the same two `tests_english_audit.py` has, for the same reasons.

1. **The ratchet.** The set of inconsistently-rendered references may shrink and
   never grow. This exists because parallel translation sessions removed the
   only thing that used to catch this class: one worker remembering what it
   wrote in the last chapter. Two sessions translating two works into Swahili
   cannot see each other, and every per-job gate passes while the language
   drifts.

2. **Precision.** The failure mode is not missing a divergence, it is crying
   wolf. Scanning backwards for "the last quote before the citation" reported
   95 conflicts including Ephesians 4:26 offered as a rendering of Luke 17:1;
   adjacency plus containment took it to 69, all of the sampled ones real. Each
   rule below is pinned so a later tidy-up cannot quietly re-flood the report.
"""

from __future__ import annotations

from functools import lru_cache

from django.test import SimpleTestCase

from library import verse_consistency as vc


@lru_cache(maxsize=1)
def _corpus() -> dict:
    """One corpus scan shared by every test that wants it."""
    return vc.baseline_counts(vc.conflicts())


def _find(*bodies) -> dict:
    """Run the scanner over synthetic (language, where, html) triples."""
    return vc.conflicts(vc.scan(bodies))


class VerseConsistencyRatchetTests(SimpleTestCase):
    def test_no_new_or_widened_divergence(self):
        """No reference may join the pinned set, and no pinned count may grow.

        Both halves matter. A NEW key means a work just shipped a rendering that
        disagrees with how its language already quotes that verse. A GROWN count
        means an already-divergent reference picked up yet another rendering —
        which an earlier version of this ratchet missed entirely, because it
        pinned only the reference. Injecting a third rendering of a
        two-rendering reference passed, silently.
        """
        base = vc.read_baseline()
        worse = sorted(
            f"{k} ({base.get(k, 0)} -> {n} renderings)"
            for k, n in _corpus().items()
            if n > base.get(k, 0)
        )
        self.assertEqual(
            worse,
            [],
            "These verses are now rendered in more ways than the pin allows. Match "
            "the wording the language already uses (`manage.py "
            "audit_verse_consistency --language <lang>` prints them all), or if the "
            "new rendering is the right one, fix the older work in the same PR.",
        )

    def test_baseline_shrinks_only(self):
        """A reconciled reference must be re-pinned, or the ratchet loosens."""
        base = vc.read_baseline()
        now = _corpus()
        better = sorted(
            f"{k} ({n} -> {now.get(k, 0)} renderings)"
            for k, n in base.items()
            if now.get(k, 0) < n
        )
        self.assertEqual(
            better,
            [],
            "These are more consistent than their pin — re-pin with `manage.py "
            "audit_verse_consistency --update-baseline` so the ratchet can only "
            "tighten, and say in the commit message which renderings you reconciled.",
        )


class VerseConsistencyPrecisionTests(SimpleTestCase):
    """One test per rule, each pinning the defect AND the convention it spares."""

    def test_two_renderings_of_one_reference_is_a_conflict(self):
        found = _find(
            ("lg", "a.lg.json", "<p>«Okukkiriza kuva mu kuwulira ekigambo» (Abaruumi 10:17)</p>"),
            ("lg", "b.lg.json", "<p>«Okukkiriza kujja olw’okuwulira ekigambo» (Abaruumi 10:17)</p>"),
        )
        self.assertIn(("lg", "Abaruumi 10:17"), found)

    def test_the_same_rendering_twice_is_not(self):
        html = "<p>«Okukkiriza kuva mu kuwulira ekigambo» (Abaruumi 10:17)</p>"
        self.assertEqual(_find(("lg", "a.lg.json", html), ("lg", "b.lg.json", html)), {})

    def test_punctuation_and_spacing_are_not_a_wording_difference(self):
        self.assertEqual(
            _find(
                ("es", "a.es.json", "<p>«Por su llaga fuimos nosotros curados» (Isaías 53:5)</p>"),
                ("es", "b.es.json", "<p>«Por su llaga, fuimos nosotros curados.» (Isaías 53:5)</p>"),
            ),
            {},
        )

    def test_a_partial_quotation_is_not_a_conflict(self):
        """Quoting half a verse in one work and all of it in another is normal."""
        self.assertEqual(
            _find(
                ("es", "a.es.json", "<p>«Por su llaga fuimos nosotros curados» (Isaías 53:5)</p>"),
                (
                    "es",
                    "b.es.json",
                    "<p>«Mas Él herido fue por nuestras rebeliones, y por su llaga fuimos "
                    "nosotros curados» (Isaías 53:5)</p>",
                ),
            ),
            {},
        )

    def test_arabic_vocalisation_counts_as_a_difference(self):
        """Harakat are semantic here: vocalised-in-guillemets claims verbatim
        Van Dyck, bare is the author's own phrase. Two spellings that differ only
        in vowels are two different claims, so they must not normalise together.
        """
        found = _find(
            ("ar", "a.ar.json", "<p>«وَلَكِنِّي عَلَيْهِ أَتَوَكَّلُ دَائِمًا» (أيوب 13:15)</p>"),
            ("ar", "b.ar.json", "<p>«ولكني عليه أتوكل دائما» (أيوب 13:15)</p>"),
        )
        self.assertIn(("ar", "أيوب 13:15"), found)

    def test_the_citation_must_follow_the_quotation(self):
        """The rule that removed the largest false-positive class.

        A quotation with a whole sentence between it and the next citation is
        not that citation's text. Reading backwards for the nearest quote
        offered Ephesians 4:26 as a rendering of Luke 17:1.
        """
        self.assertEqual(
            _find(
                (
                    "lg",
                    "a.lg.json",
                    "<p>«temuzibyanga budde nga mukyasunguwadde» ne kino kyokka "
                    "kituyigiriza ekintu kimu ekikulu nnyo ku bulamu (Lukka 17:1)</p>",
                ),
                ("lg", "b.lg.json", "<p>«zimusanze omuntu oyo abireeta» (Lukka 17:1)</p>"),
            ),
            {},
        )

    def test_a_fragment_is_too_short_to_compare(self):
        self.assertEqual(
            _find(
                ("sw", "a.sw.json", "<p>«kwa neema» (Waefeso 2:8)</p>"),
                ("sw", "b.sw.json", "<p>«kwa kuwa mmeokolewa» (Waefeso 2:8)</p>"),
            ),
            {},
        )

    def test_clean_prose_produces_nothing(self):
        self.assertEqual(_find(("sw", "a.sw.json", "<p>Hakuna nukuu hapa kabisa.</p>")), {})
