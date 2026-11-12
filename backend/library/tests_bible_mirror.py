"""`scripts/bible_mirror.py`: its repairs restore letters and spacing, never words.

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

    def test_a_genuine_capital_o_grave_is_left_alone(self):
        # Rev 1:4, 1:8, 4:8: decoding CÒN as cp1258 would give C + U+0309.
        text = "ĐẤNG HIỆN CÓ, ĐÃ CÓ, VÀ CÒN ĐẾN"
        self.assertEqual(self.clean(text), text)

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


# --------------------------------------------------------------------------- #
# fra_lsg, kor_old, por_bpm, amh_amh (2026-11-12). Each defect below was
# rediscovered and hand-patched by 2-4 translation workers on one day; the
# samples are the mirror's own lines, shortened.
# --------------------------------------------------------------------------- #

_FRA_USFM = {
    "jhn.usfm": "\\id JHN\n\\c 3\n"
    '\\v 16 \\x n \\xo 3.16 \\xt Ro 5:8.\\x*\\wj \\+w Car|strong="G1063"\\+w* '
    '\\+w Dieu|strong="G2316"\\+w* \\+w a|strong="G1519"\\+w* \\+w tant|strong="G3779"\\+w* '
    '\\+w aimé|strong="G3588"\\+w* \\+w le|strong="G1519"\\+w* \\+w monde|strong="G2889"\\+w* '
    '\\+w qu|strong="G2443"\\+w*’\\+w il|strong="G1063"\\+w* \\+w a|strong="G1519"\\+w* '
    '\\+w donné|strong="G1325"\\+w* \\+w son|strong="G1519"\\+w* \\+w Fils|strong="G5207"\\+w* '
    '\\+w unique|strong="G3439"\\+w*,\\wj*\\x o \\xo 3.16 \\xt Lu 19:10.\\x*'
    '\\wj \\+w afin|strong="G2443"\\+w* \\+w que|strong="G2443"\\+w* '
    '\\+w quiconque|strong="G3956"\\+w* \\+w croit|strong="G4100"\\+w*.\\wj*  \n'
    '\\v 17 \\w Dieu|strong="G2316"\\w* \\w a|strong="G1519"\\w* \\w envoyé|strong="G649"\\w* \\p\n'
    "\\p\n",
}


class FraLsgParseTests(SimpleTestCase):
    """fra_lsg's damage is markup, so `parse` fixes it for every collection."""

    def setUp(self):
        self.verses, _ = _parse(_FRA_USFM)

    def test_strong_attributes_are_not_text(self):
        self.assertNotIn("strong", self.verses["JHN 3:16"])
        self.assertNotIn("|", self.verses["JHN 3:16"])

    def test_a_cross_reference_between_words_leaves_a_space(self):
        self.assertIn("Fils unique, afin que", self.verses["JHN 3:16"])

    def test_elisions_rejoin(self):
        self.assertIn("monde qu’il a donné", self.verses["JHN 3:16"])
        self.assertTrue(self.verses["JHN 3:16"].startswith("Car Dieu a tant aimé"))

    def test_a_trailing_paragraph_marker_is_dropped(self):
        self.assertEqual(self.verses["JHN 3:17"], "Dieu a envoyé")


class KorOldRepairTests(SimpleTestCase):
    def setUp(self):
        self.clean = _bible_mirror().clean_kor

    def test_a_glued_comma_gets_its_space(self):
        self.assertEqual(
            self.clean("아르난의 아들들,오바댜의 아들들"),
            "아르난의 아들들, 오바댜의 아들들",
        )

    def test_quote_marks_are_dropped(self):
        self.assertEqual(
            self.clean("가로되 `원컨대 주께 고하옵소서' 하였더니"),
            "가로되 원컨대 주께 고하옵소서 하였더니",
        )
        # Glued before 하다 the mark stood for a word space; before a particle, nothing.
        self.assertEqual(self.clean("`가라'하고"), "가라 하고")
        self.assertEqual(self.clean("`말하라'고 할"), "말하라고 할")

    def test_spaced_question_mark_is_glued(self):
        self.assertEqual(
            self.clean("왜 달음질하려 하느냐 ? 내 주여"),
            "왜 달음질하려 하느냐? 내 주여",
        )

    def test_spaced_exclamation_is_dropped_not_glued(self):
        # PRO 3:6 as the shipped ko books quote it: no `!`.
        self.assertEqual(
            self.clean("범사에 그를 인정하라 ! 그리하면 네 길을 지도하시리라"),
            "범사에 그를 인정하라 그리하면 네 길을 지도하시리라",
        )
        self.assertEqual(self.clean("내 주여 !"), "내 주여")
        # An unspaced `!` (10 verses) is the mirror's text as printed: kept.
        self.assertEqual(self.clean("내 주여!"), "내 주여!")

    def test_idempotent_and_letters_untouched(self):
        once = self.clean("`어찜이냐 ?' 하나님,나의 하나님이여")
        self.assertEqual(self.clean(once), once)
        self.assertEqual(once, "어찜이냐? 하나님, 나의 하나님이여")

    def test_isa_57_15_is_withheld_not_restored(self):
        truncated = "또한 통회하고 마음이 겸손한 자의 영을 소성케 하려 함이라"
        verses, damaged = _bible_mirror().clean_kor_index(
            {"ISA 57:15": truncated, "ISA 57:16": "내가 영원히"}, {}
        )
        self.assertNotIn("ISA 57:15", verses)
        self.assertEqual(damaged["ISA 57:15"]["mirror_text"], truncated)
        self.assertEqual(verses, {"ISA 57:16": "내가 영원히"})


_POR_USFM = {
    "jhn.usfm": "\\id JHN\n\\c 3\n"
    "\\v 16 \\wj Porque Deus amou o mundo de tal maneira que deu o seu Filho "
    "unigênito\\wj*\\f + \\fr 3:16 \\ft A expressão “unigênito” vem da palavra grega.\\f*"
    "\\wj , para que todo aquele que nele crê não pereça. \\wj*  \n",
    "heb.usfm": "\\id HEB\n\\c 13\n"
    "\\v 15 Ofereçamos a Deus um sacrifício de louvor\\x + \\xo 13:15 \\xt Salmos 50:23\\x*, "
    "ou seja, o fruto de lábios.  \n",
}


class PorBpmTests(SimpleTestCase):
    def test_no_space_before_a_comma_where_a_footnote_sat_in_wj(self):
        verses, _ = _parse(_POR_USFM)
        self.assertEqual(
            verses["JHN 3:16"],
            "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, "
            "para que todo aquele que nele crê não pereça.",
        )
        self.assertIn("de louvor, ou seja", verses["HEB 13:15"])
        # Behind a closing marker, the reference still sits before punctuation.
        verses, _ = _parse(
            {
                "heb.usfm": "\\id HEB\n\\c 1\n\\v 1 \\wj louvor\\x + \\xt Sl 50\\x*\\wj*, ou\n"
            }
        )
        self.assertEqual(verses["HEB 1:1"], "louvor, ou")

    def test_jeremiah_49_english_glosses_are_withheld(self):
        verses, damaged = _bible_mirror().clean_por_index(
            {
                "JER 49:11": "Leave your fatherless children. “Deixe os seus órfãos.”",
                "JER 48:47": "Contudo, nos últimos dias",
                "JER 4:9": "E acontecerá naquele dia",
            },
            {},
        )
        self.assertEqual(list(damaged), ["JER 49:11"])
        self.assertIn("English", damaged["JER 49:11"]["reason"])
        self.assertEqual(set(verses), {"JER 48:47", "JER 4:9"})


class AmhBridgedTests(SimpleTestCase):
    def test_bridged_verses_are_flagged_and_withheld(self):
        usfm = {
            "heb.usfm": "\\id HEB\n\\c 12\n"
            "\\v 1-3 በነፍሳችሁ ዝላችሁ እንዳትደክሙ፥ የጸናውን አስቡ።  \n"
            "\\v 4 ከኃጢአት ጋር እየተጋደላችሁ ገና እስከ ደም ድረስ አልተቃወማችሁም፤\n"
        }
        mirror = _bible_mirror()
        ranges = {}
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in usfm.items():
                (Path(tmp) / name).write_text(text, encoding="utf-8")
            verses, _ = mirror.parse(Path(tmp), ranges)
        self.assertEqual(ranges, {"HEB 12:1": "HEB 12:1-3"})
        verses, damaged = mirror.clean_amh_index(verses, ranges)
        self.assertEqual(list(verses), ["HEB 12:4"])
        self.assertIn("HEB 12:1-3", damaged["HEB 12:1"]["reason"])
        self.assertTrue(damaged["HEB 12:1"]["mirror_text"].startswith("በነፍሳችሁ"))


class CleanerRegistryTests(SimpleTestCase):
    def test_every_cleaner_returns_verses_and_damaged(self):
        for collection, cleaner in _bible_mirror().CLEANERS.items():
            with self.subTest(collection=collection):
                verses, damaged = cleaner({"JHN 3:16": "x"}, {})
                self.assertEqual(verses, {"JHN 3:16": "x"})
                self.assertEqual(damaged, {})
