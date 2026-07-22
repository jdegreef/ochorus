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
