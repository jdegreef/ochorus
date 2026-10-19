"""`scripts/bible_mirror.py`: the vie_kt repairs restore letters, never words.

The ebible mirror's Vietnamese text (Cadman, 1925) reaches worker sessions with
encoding damage, and a translator who pastes it verbatim ships the damage to
readers (`Aùp-ra-ham` reached a chapter draft before this existed). Each case
below is a real verse from the mirror.
"""

import importlib.util
from pathlib import Path

from django.test import SimpleTestCase


def _bible_mirror():
    path = Path(__file__).resolve().parent.parent / "scripts" / "bible_mirror.py"
    spec = importlib.util.spec_from_file_location("bible_mirror", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VieKtRepairTests(SimpleTestCase):
    def setUp(self):
        self.clean = _bible_mirror().clean_vie

    def test_vni_capitals(self):
        cases = {
            "Áp-sa-lôm giơ tay ra": "Aùp-sa-lôm giơ tay ra",
            "Ấy vậy, nếu khi nào ngươi đem dâng": "Aáy vậy, nếu khi nào ngươi đem dâng",
            "là Ép-ra-im và Ma-na-se": "là Eùp-ra-im và Ma-na-se",
            "Ôi! sâu nhiệm thay": "Oâi! sâu nhiệm thay",
            "Ăn đi": "Aên đi",
            "Ắt sẽ": "Aét sẽ",
            "Ốt-ni-ên": "Oát-ni-ên",
            "Ủa": "Uûa",
        }
        for want, raw in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.clean(raw), want)

    def test_vocative(self):
        self.assertEqual(
            self.clean("rằng: ù Sa-tan, hãy lui"), "rằng: Ớ Sa-tan, hãy lui"
        )
        self.assertEqual(self.clean("la rằng: ù, Sam-sôn"), "la rằng: Ớ, Sam-sôn")

    def test_ky(self):
        self.assertEqual(self.clean("bày sự k” cục"), "bày sự kỳ cục")
        self.assertEqual(self.clean("hu”nh"), "huỳnh")

    def test_a_real_closing_quote_is_left_alone(self):
        text = "rằng: “Chúng tôi chẳng có phần chi với Đa-vít” sao?"
        self.assertEqual(self.clean(text), text)

    def test_mojibake_word(self):
        self.assertEqual(self.clean("Cha ðýõòc nên"), "Cha được nên")

    def test_ordinary_vietnamese_is_untouched(self):
        for text in (
            "Vì Đức Chúa Trời yêu thương thế gian, đến nỗi đã ban Con một của Ngài",
            "Yên ủi, yên ủi dân ta",
            "Úc, Ê-đôm và Ơ-rơ",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.clean(text), text)

    def test_idempotent(self):
        once = self.clean("Aùp-ra-ham nói: ù Chúa, k” lạ thay")
        self.assertEqual(self.clean(once), once)

    def test_whole_verse_restorations(self):
        index = _bible_mirror().clean_vie_index(
            {
                "MAT 6:10": "Nước Cha được đến; Cha ðýõòc nên, õÒ ðâìt nhý trõÌi!",
                "JHN 3:16": "Vì",
            }
        )
        self.assertEqual(
            index["MAT 6:10"], "Nước Cha được đến; Ý Cha được nên, ở đất như trời!"
        )
        self.assertEqual(index["JHN 3:16"], "Vì")
