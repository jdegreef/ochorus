"""Every translated lifecycle email keeps the English shape (emails.copy)."""

from __future__ import annotations

import re

from django.test import SimpleTestCase

from emails.copy import COPY_DATA, DEFAULT_LOCALE, FRIEND, LIFECYCLE, step_copy

PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def _placeholders(value) -> set[str]:
    text = " ".join(value) if isinstance(value, list) else str(value)
    return set(PLACEHOLDER.findall(text))


class CopyShapeTests(SimpleTestCase):
    def test_every_translation_matches_the_english_shape(self):
        for step, by_lang in LIFECYCLE.items():
            en = by_lang[DEFAULT_LOCALE]
            for lang, block in by_lang.items():
                with self.subTest(step=step, lang=lang):
                    self.assertEqual(list(block), list(en), "same keys, same order")
                    self.assertEqual(block["cta_path"], en["cta_path"])
                    self.assertEqual(len(block["paragraphs"]), len(en["paragraphs"]))
                    for key, value in en.items():
                        if key == "cta_path":
                            continue
                        self.assertEqual(
                            _placeholders(block[key]), _placeholders(value), f"placeholders in {key}"
                        )
                        self.assertTrue(block[key], f"{key} is empty")

    def test_json_languages_cover_every_step(self):
        langs = {p.stem for p in COPY_DATA.glob("*.json")}
        self.assertTrue(langs, "no copy_data files found")
        for lang in langs:
            for step, by_lang in LIFECYCLE.items():
                with self.subTest(step=step, lang=lang):
                    self.assertIn(lang, by_lang)

    def test_every_site_language_has_its_own_copy(self):
        # The reader's languages (FRIEND lists them): none should fall back to
        # English for any email.
        for lang in FRIEND:
            for step in LIFECYCLE:
                with self.subTest(step=step, lang=lang):
                    self.assertIn(lang, LIFECYCLE[step])

    def test_lookup_uses_the_base_language(self):
        self.assertIs(step_copy("welcome", "pt-BR"), LIFECYCLE["welcome"]["pt"])
