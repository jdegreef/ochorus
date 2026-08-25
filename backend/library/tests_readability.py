"""The difficulty heuristic: relative guidance, deterministically bucketed."""

from django.test import TestCase

from .readability import ACCESSIBLE, ADVANCED, difficulty, flesch_reading_ease

# Plain modern prose: short sentences, short words.
_EASY = (
    "God is love. He made us. He keeps us. We can trust him each day. "
    "He hears us when we pray. He gives us what we need. His word is true. "
    "It is a light for our path. We read it and we live it. "
) * 8

# Ornate nineteenth-century prose: long clauses, latinate vocabulary.
_HEAVY = (
    "Notwithstanding the multitudinous perplexities and considerations which "
    "invariably accompany the contemplation of providential dispensations, the "
    "discerning practitioner of habitual supplication apprehends, through "
    "protracted meditation upon the incomprehensible magnificence of the divine "
    "administration, an inexhaustible consolation transcending every temporal "
    "vicissitude and confounding philosophical investigation altogether. "
) * 6


class ReadabilityTests(TestCase):
    def test_too_little_text_is_unjudged(self):
        self.assertIsNone(difficulty(""))
        self.assertIsNone(difficulty("A few words only."))

    def test_easy_prose_reads_accessible(self):
        self.assertEqual(difficulty(_EASY), ACCESSIBLE)

    def test_ornate_prose_reads_advanced(self):
        self.assertEqual(difficulty(_HEAVY), ADVANCED)

    def test_score_orders_texts_sensibly(self):
        easy = flesch_reading_ease(_EASY)
        heavy = flesch_reading_ease(_HEAVY)
        self.assertIsNotNone(easy)
        self.assertIsNotNone(heavy)
        self.assertGreater(easy, heavy)

    def test_deterministic(self):
        self.assertEqual(difficulty(_HEAVY), difficulty(_HEAVY))


class DifficultyCacheTests(TestCase):
    """The cache must be bounded in BYTES, not just in entries.

    ``difficulty`` was ``lru_cache``d on the whole body. ``lru_cache`` bounds
    entries, not bytes, so 1,024 book and sermon bodies were retained
    permanently per worker — and the prerender crawl (every work × every live
    locale) is precisely the access pattern that fills it to capacity. The score
    only ever reads ``text[:_SAMPLE_CHARS]``, so the rest of each key was
    retained without ever being looked at.
    """

    def setUp(self):
        from .readability import _difficulty_of_sample

        _difficulty_of_sample.cache_clear()

    def test_only_the_sample_is_retained(self):
        """Two bodies identical up to the sample cap share one cache entry."""
        from .readability import _SAMPLE_CHARS, _difficulty_of_sample

        base = _HEAVY * 200
        self.assertGreater(len(base), _SAMPLE_CHARS)
        difficulty(base + "one ending")
        difficulty(base + "a completely different ending")
        self.assertEqual(_difficulty_of_sample.cache_info().currsize, 1)

    def test_scoring_the_full_text_equals_scoring_the_sample(self):
        """Keying on the sample must not change a single verdict."""
        from .readability import _SAMPLE_CHARS

        for body in (_EASY * 40, _HEAVY * 40):
            self.assertEqual(difficulty(body), difficulty(body[:_SAMPLE_CHARS]))

    def test_a_distinct_work_still_gets_its_own_entry(self):
        from .readability import _difficulty_of_sample

        difficulty(_EASY * 40)
        difficulty(_HEAVY * 40)
        self.assertEqual(_difficulty_of_sample.cache_info().currsize, 2)

    def test_short_text_is_still_unjudgeable(self):
        self.assertIsNone(difficulty("Too little."))
