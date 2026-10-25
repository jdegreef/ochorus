"""`scripts/bible_mirror.py`: the vie_kt repairs restore letters, never words.

The ebible mirror's Vietnamese text (Cadman, 1925) reaches worker sessions with
encoding damage, and a translator who pastes it verbatim ships the damage to
readers (`Aùp-ra-ham` reached a chapter draft before this existed). Each case
below is a real verse from the mirror.
"""

import importlib.util
import tempfile
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


# Lines as the mirror sets them (2026-10-24): a poetic verse's second half is a
# `\q1` line, a Selah is an inline `\qs`, and `\d` / `\b` sit between verses.
_MIRROR_USFM = {
    "pro.usfm": r"""\id PRO
\toc1 Châm-ngôn
\c 31
\q1
\v 25 Nàng mặc lấy sức lực và oai phong,
\q1 Và khi tưởng đến buổi sau, bèn vui cười.
\q1
\v 26 Nàng mở miệng ra cách khôn ngoan,
\q1 Phép tắc nhân từ ở nơi lưỡi nàng.
\q1
""",
    "psa.usfm": r"""\id PSA
\c 3
\d Thơ Đa-vít làm, khi người trốn khỏi Áp-sa-lôm, con trai người
\q1
\v 2 Biết bao kẻ nói về linh hồn tôi rằng:
\q1 Nơi Đức Chúa Trời chẳng có sự cứu rỗi cho nó. \qs (Sê-la)\qs*
\b
\c 141
\q1
\v 3 Hỡi Đức Giê-hô-va, xin hãy giữ miệng tôi,
\q1 Và canh cửa môi tôi.
\q1
""",
    "1co.usfm": r"""\id 1CO
\c 16
\v 22 Bằng có ai không kính mến Chúa, thì phải bị a-na-them! \tl Ma-ra-na-tha.\tl*
""",
    "2sa.usfm": r"""\id 2SA
\c 1
\v 15-16 Huyết ngươi đổ lại trên đầu ngươi! Miệng ngươi đã làm chứng về ngươi, vì ngươi đã nói rằng: Chính tôi đã giết đấng chịu xức dầu của Đức Giê-hô-va. Đoạn, Đa-vít gọi một người trai trẻ mà nói rằng: Hãy lại gần, xông đánh hắn! Người ấy đánh hắn, và hắn chết.
""",
}

# Not from the mirror: USFM layouts other collections use. The words are
# placeholders; only the markup is under test.
_SYNTHETIC_USFM = r"""\id GEN
\c 1
\s Heading
\v 1 one
\p \v 2 two
\q1 \v 3 three\f + \ft a note\f*
\q2 continued
\s Another heading
\cls closing
"""


def _parse(files):
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in files.items():
            (Path(tmp) / name).write_text(text, encoding="utf-8")
        return _bible_mirror().parse(Path(tmp))


class ParseTests(SimpleTestCase):
    """A verse's continuation lines carry markers too; their text is the verse."""

    def test_poetry_lines_continue_the_verse(self):
        verses, _ = _parse(_MIRROR_USFM)
        self.assertEqual(
            verses["PRO 31:26"],
            "Nàng mở miệng ra cách khôn ngoan, Phép tắc nhân từ ở nơi lưỡi nàng.",
        )
        self.assertEqual(
            verses["PRO 31:25"],
            "Nàng mặc lấy sức lực và oai phong, "
            "Và khi tưởng đến buổi sau, bèn vui cười.",
        )
        self.assertEqual(
            verses["PSA 141:3"],
            "Hỡi Đức Giê-hô-va, xin hãy giữ miệng tôi, Và canh cửa môi tôi.",
        )

    def test_inline_markers_keep_their_text(self):
        verses, names = _parse(_MIRROR_USFM)
        self.assertEqual(
            verses["PSA 3:2"],
            "Biết bao kẻ nói về linh hồn tôi rằng: "
            "Nơi Đức Chúa Trời chẳng có sự cứu rỗi cho nó. (Sê-la)",
        )
        self.assertEqual(
            verses["1CO 16:22"],
            "Bằng có ai không kính mến Chúa, thì phải bị a-na-them! Ma-ra-na-tha.",
        )
        self.assertEqual(names, {"PRO": "Châm-ngôn"})

    def test_a_verse_range_is_keyed_by_its_first_verse(self):
        verses, _ = _parse(_MIRROR_USFM)
        self.assertTrue(verses["2SA 1:15"].startswith("Huyết ngươi đổ lại"))
        self.assertNotIn("2SA 1:16", verses)

    def test_other_layouts(self):
        verses, _ = _parse({"gen.usfm": _SYNTHETIC_USFM})
        self.assertEqual(
            verses,
            {"GEN 1:1": "one", "GEN 1:2": "two", "GEN 1:3": "three continued closing"},
        )
