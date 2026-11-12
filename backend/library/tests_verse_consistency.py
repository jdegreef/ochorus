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


class VerseConsistencyRepinTests(SimpleTestCase):
    """The guard on the re-pin itself — the hole the two ratchet tests cannot see.

    Both tests above compare the corpus against the committed baseline, so they
    are only as strict as that file. `--update-baseline` rewrites it from
    whatever the corpus currently says, which means a batch that introduces
    conflicts can absorb them and leave CI green on every commit. That is
    measured, not hypothetical: 110 pinned conflicts on 2026-08-24, 322 on
    2026-09-16, tests passing throughout, and the per-edition rate rising from
    0.62 to 0.78 — the corpus drifting while the ratchet reported success.
    """

    def test_a_new_reference_would_loosen_the_pin(self):
        self.assertEqual(
            vc.baseline_regressions({"sw\tWarumi 10:17": 2}, {}),
            ["sw Warumi 10:17: NEW, 2 renderings"],
        )

    def test_an_extra_rendering_of_a_pinned_reference_would_loosen_it(self):
        self.assertEqual(
            vc.baseline_regressions({"sw\tWarumi 10:17": 3}, {"sw\tWarumi 10:17": 2}),
            ["sw Warumi 10:17: 2 -> 3 renderings"],
        )

    def test_tightening_is_not_a_regression(self):
        """Reconciling a conflict must re-pin freely — that is the point."""
        self.assertEqual(
            vc.baseline_regressions({"sw\tWarumi 10:17": 2}, {"sw\tWarumi 10:17": 3}), []
        )

    def test_a_reference_leaving_entirely_is_not_a_regression(self):
        self.assertEqual(vc.baseline_regressions({}, {"sw\tWarumi 10:17": 2}), [])

    def test_the_committed_baseline_is_its_own_fixed_point(self):
        """Re-pinning the corpus as it stands must be a no-op.

        If this fails, the committed baseline disagrees with the corpus and one
        of the two ratchet tests above is already red — this just says which
        direction, and keeps `--update-baseline` honest for the next person.
        """
        self.assertEqual(vc.baseline_regressions(_corpus()), [])


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

    def test_different_clauses_of_one_verse_are_not_a_conflict(self):
        """A verse is often several clauses, and two works can quote different
        ones under the same citation. Juan 6:68 is quoted in this corpus as both
        halves of Peter's answer; matching them would force one to be rewritten
        into words its own sentence does not contain.
        """
        self.assertEqual(
            _find(
                ("es", "a.es.json", "<p>«¿A quién más iremos, Señor nuestro?» (Juan 6:68)</p>"),
                ("es", "b.es.json", "<p>«Tú tienes palabras de vida eterna» (Juan 6:68)</p>"),
            ),
            {},
        )

    def test_two_renderings_of_one_clause_still_conflict_though_worded_apart(self):
        """The guard on the exemption above, and the reason it demands ZERO
        shared words rather than "few". Two translations of the SAME clause keep
        content words in common even when the wording differs a lot — so the
        pair is still reported, which is what stops the exemption excusing the
        drift this module exists to find.
        """
        found = _find(
            ("es", "a.es.json", "<p>«Porque de tal manera amó Dios al mundo» (Juan 3:16)</p>"),
            ("es", "b.es.json", "<p>«Pues Dios amó tanto al mundo entero» (Juan 3:16)</p>"),
        )
        self.assertIn(("es", "Juan 3:16"), found)

    def test_arabic_vocalisation_is_not_mistaken_for_a_different_clause(self):
        """The exemption must not undo the rule above it.

        Comparing words character-exactly, a vocalised rendering and a bare one
        share NO word — so the same clause read as two different clauses and was
        exempted. Measured, not hypothetical: it cleared 30 Arabic references,
        يوحنا 3:16 among them, and would have dropped the ratchet from 124
        entries to 87. The same-words test therefore ignores diacritics (and
        folds alef variants) while the wording comparison keeps them.
        """
        found = _find(
            (
                "ar",
                "a.ar.json",
                "<p>«هَكَذَا أَحَبَّ ٱللهُ ٱلْعَالَمَ حَتَّى بَذَلَ ٱبْنَهُ» (يوحنا 3:16)</p>",
            ),
            ("ar", "b.ar.json", "<p>«هكذا أحبّ الله العالم حتى بذل ابنه» (يوحنا 3:16)</p>"),
        )
        self.assertIn(("ar", "يوحنا 3:16"), found)

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


def _spans(language: str, html: str) -> list[str]:
    """Every quotation the scanner reads out of one body, as written."""
    return [r.text for rs in vc.scan([(language, "x", html)]).values() for r in rs]


class SingleQuoteTests(SimpleTestCase):
    """Curly single quotes ‘ … ’ are quotations too — but ’ is also an apostrophe.

    Works that quote Scripture in ‘ ’ were invisible to the ratchet until the
    pt Grace Abounding job hand-ran it with them allowed and found 8 real
    divergences. The risk in widening is the other job of this file: ’ is the
    apostrophe in English (don’t), in Luganda (n’omukama, olw’ekisa) and in
    Ukrainian (м’ята, п’ять), so a careless pattern would let every apostrophe
    close a span. These pin the fences: ‘ must open the span and may not follow
    a letter, and the closing ’ may not be followed by one.
    """

    def test_a_single_quoted_conflict_is_now_seen(self):
        found = _find(
            ("lg", "a", "<p>‘Katonda bwe yayagala ensi bw’atyo’ (Yokaana 3:16).</p>"),
            ("lg", "b", "<p>‘Katonda yayagala nnyo ensi bw’atyo ddala’ (Yokaana 3:16).</p>"),
        )
        self.assertIn(("lg", "Yokaana 3:16"), found)

    def test_english_apostrophes_stay_inside_the_span(self):
        html = (
            "<p>Don’t fear; the saints’ hope isn’t vain: ‘I’ll never leave thee, "
            "nor forsake thee’ (Hebrews 13:5). It’s God’s word.</p>"
        )
        self.assertEqual(_spans("en", html), ["I’ll never leave thee, nor forsake thee"])

    def test_english_apostrophes_alone_make_no_span(self):
        html = (
            "<p>Don’t say it’s too late, for the Lord’s mercy isn’t spent and "
            "we’ve His word on it (John 6:37).</p>"
        )
        self.assertEqual(_spans("en", html), [])

    def test_an_elision_typed_with_an_opening_mark_does_not_open_a_span(self):
        html = "<p>’Tis said ‘twas the Lord’s doing, and o‘er the land it ran’ (Psalm 118:23).</p>"
        self.assertEqual(_spans("en", html), [])

    def test_ukrainian_apostrophes_make_no_span(self):
        html = (
            "<p>П’ять хлібів і м’ясо, сім’я в об’єднанні, пам’ять про "
            "з’явлення (Іван 6:9).</p>"
        )
        self.assertEqual(_spans("uk", html), [])

    def test_ukrainian_apostrophes_stay_inside_a_real_span(self):
        html = "<p>Він сказав: ‘Пам’ятайте слово, яке я вам сказав’ (Іван 15:20).</p>"
        self.assertEqual(_spans("uk", html), ["Пам’ятайте слово, яке я вам сказав"])

    def test_luganda_apostrophes_make_no_span(self):
        html = (
            "<p>Olw’ekisa kya Katonda n’omukwano gwe, ab’omu nnyumba y’Omukama "
            "baasanyuka nnyo ng’ebigambo bw’ebyali (Yokaana 3:16).</p>"
        )
        self.assertEqual(_spans("lg", html), [])

    def test_luganda_apostrophes_stay_inside_a_real_span(self):
        html = (
            "<p>Yagamba nti ‘Kubanga olw’ekisa mwalokolebwa olw’okukkiriza’ "
            "(Abaefeso 2:8), n’asanyuka.</p>"
        )
        self.assertEqual(
            _spans("lg", html), ["Kubanga olw’ekisa mwalokolebwa olw’okukkiriza"]
        )

    def test_a_word_final_apostrophe_does_not_cut_the_span_short(self):
        """`saints’ ` is followed by a space, not a letter — the span must run on
        to the ’ the citation follows, not stop at the possessive."""
        html = "<p>‘The saints’ rest is with the Lord for ever’ (Hebrews 4:9).</p>"
        self.assertEqual(_spans("en", html), ["The saints’ rest is with the Lord for ever"])

    def test_straight_single_quotes_are_still_not_quotations(self):
        html = "<p>'For God so loved the world, that he gave' (John 3:16).</p>"
        self.assertEqual(_spans("en", html), [])
