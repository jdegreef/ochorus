"""Carry the "standalone page" rewording of four more bios into REVIEWED rows.

Tozer, Bill Bright and Derek Prince were written for multi-subject anthologies
("Most of the men in this book…", "belongs in a book about prayer", "the
witness this book is here to record", "remembered in these pages"), the same
defect 0188 fixed for Bonhoeffer. The English (fixture-wins ``bio_html`` and
``faq``) and ``migrations/data/author_bios_<lang>`` files were reworded, but
``seed_author_translations`` never overwrites a ``reviewed=True`` row.

Same approach as 0188: a founder-directed framing edit, not a new translation,
so each old phrase is swapped for its new one only where it appears verbatim
— in ``bio_html`` and in every FAQ answer — and ``reviewed`` is left as it is.
A phrase an approver had already reworded is skipped. Idempotent; a no-op on a
fresh DB (the seed creates the rows later from the already-edited files).
"""

from __future__ import annotations

from django.db import migrations

# (slug, language) -> [(old, new), ...]; applied to bio_html and FAQ answers.
SUBSTITUTIONS = {
    ("a-w-tozer", "am"): [
        (
            "በዚህ መጽሐፍ ውስጥ ያሉት አብዛኞቹ ሰዎች ሥራውን ከመጀመራቸው በፊት ለሥራው ሥልጠና ወስደው ነበር።",
            "አብዛኞቹ መጋቢዎች ሥራውን ከመጀመራቸው በፊት ለሥራው ሥልጠና ይወስዳሉ።",
        ),
        (
            "ቶዘር ስለ እረኞች በሚናገር መጽሐፍ ውስጥ ቦታ ያለው የሚያውቀውን ብቸኛ መንገድ ተከትሎ ነፍሳትን ስለ ጠበቀ ነው፦",
            "ቶዘር እውነተኛ እረኛ ነበር፤ የሚያውቀውን ብቸኛ መንገድ ተከትሎ ነፍሳትን ጠበቀ፦",
        ),
    ],
    ("a-w-tozer", "ar"): [
        (
            "معظم الرجال الذين يضمّهم هذا الكتاب تدرّبوا على العمل قبل أن يمارسوه.",
            "معظم الرعاة يتدرّبون على العمل قبل أن يمارسوه.",
        ),
        (
            "ومكان توزر في كتاب عن الرعاة لأنه رعى النفوس",
            "وكان توزر راعيًا حقيقيًا، رعى النفوس",
        ),
    ],
    ("a-w-tozer", "es"): [
        (
            "La mayoría de los hombres de este libro fueron preparados para la obra",
            "La mayoría de los pastores son preparados para la obra",
        ),
        (
            "Tozer tiene su lugar en un libro sobre pastores porque cuidó de las almas",
            "Tozer fue un verdadero pastor, y cuidó de las almas",
        ),
    ],
    ("a-w-tozer", "fr"): [
        (
            "La plupart des hommes de ce livre furent formés à leur œuvre",
            "La plupart des pasteurs sont formés à leur œuvre",
        ),
        (
            "Tozer a sa place dans un livre sur les bergers, car il veilla sur les âmes",
            "Tozer fut un vrai berger, et il veilla sur les âmes",
        ),
    ],
    ("a-w-tozer", "hi"): [
        (
            "इस पुस्तक में जिन लोगों का वर्णन है, उनमें से अधिकांश को अपना काम करने से पहले"
            " उसके लिए प्रशिक्षित किया गया था।",
            "अधिकांश पादरियों को अपना काम करने से पहले उसके लिए प्रशिक्षित किया जाता है।",
        ),
        (
            "टोज़र चरवाहों के विषय में लिखी किसी पुस्तक में इसलिए स्थान पाता है क्योंकि उसने"
            " आत्माओं की देखभाल",
            "टोज़र एक सच्चा चरवाहा था, और उसने आत्माओं की देखभाल",
        ),
    ],
    ("a-w-tozer", "lg"): [
        (
            "Abasajja abasinga obungi mu kitabo kino baasomesebwa omulimu",
            "Abasumba abasinga obungi basomesebwa omulimu",
        ),
        (
            "Tozer asaanira mu kitabo ekyogera ku basumba kubanga yalabirira emyoyo",
            "Tozer yali musumba wa mazima, era yalabirira emyoyo",
        ),
    ],
    ("a-w-tozer", "pt"): [
        (
            "A maioria dos homens deste livro foi treinada para a obra",
            "A maioria dos pastores é treinada para a obra",
        ),
        (
            "Tozer pertence a um livro sobre pastores porque cuidou de almas",
            "Tozer foi um verdadeiro pastor, e cuidou de almas",
        ),
    ],
    ("a-w-tozer", "sw"): [
        (
            "Wengi wa wanaume walioko katika kitabu hiki walifundishwa kazi kabla ya kuifanya.",
            "Wachungaji wengi hufundishwa kazi kabla ya kuifanya.",
        ),
        (
            "Tozer anastahili kuwemo katika kitabu kuhusu wachungaji kwa sababu alizichunga",
            "Tozer alikuwa mchungaji wa kweli, naye alizichunga",
        ),
    ],
    ("bill-bright", "es"): [
        (
            "La mayoría de los hombres de este libro son conocidos",
            "La mayoría de los grandes hombres de oración son conocidos",
        ),
        (
            "Bill Bright que pertenece a un libro sobre la oración es",
            "Bill Bright que más tiene que enseñar sobre la oración es",
        ),
        (
            "El Bright que pertenece a un libro sobre la oración es",
            "El Bright que más tiene que enseñar sobre la oración es",
        ),
    ],
    ("bill-bright", "fr"): [
        (
            "La plupart des hommes de ce livre sont connus",
            "La plupart des grands hommes de prière sont connus",
        ),
        (
            "Bill Bright qui a sa place dans un livre sur la prière, c’est",
            "Bill Bright qui a le plus à enseigner sur la prière, c’est",
        ),
        (
            "Le Bright qui a sa place dans un livre sur la prière, c'est",
            "Le Bright qui a le plus à enseigner sur la prière, c'est",
        ),
    ],
    ("bill-bright", "pt"): [
        (
            "A maioria dos homens deste livro é conhecida",
            "A maioria dos grandes homens de oração é conhecida",
        ),
        (
            "Bill Bright que pertence a um livro sobre oração é",
            "Bill Bright que mais tem a ensinar sobre oração é",
        ),
        (
            "O Bright que pertence a um livro sobre oração é",
            "O Bright que mais tem a ensinar sobre oração é",
        ),
    ],
    ("bill-bright", "sw"): [
        (
            "Wengi wa wanaume walio katika kitabu hiki wanajulikana",
            "Wengi wa wanaume wakuu wa sala wanajulikana",
        ),
        (
            "Bill Bright anayestahili kuwa katika kitabu kuhusu sala ni",
            "Bill Bright aliye na mengi zaidi ya kufundisha kuhusu sala ni",
        ),
        (
            "Bright anayestahili kuwa katika kitabu kuhusu sala ni yule mzee aliyeweka",
            "Bright aliye na mengi zaidi ya kufundisha kuhusu sala ni yule mzee aliyeweka",
        ),
    ],
    ("derek-prince", "es"): [
        (
            "La mayoría de los hombres de este libro aprendieron a orar",
            "La mayoría de los grandes hombres de oración aprendieron a orar",
        ),
        (
            "parte del testimonio del que este libro está aquí para dejar constancia.",
            "parte de su testimonio.",
        ),
        (
            "La mayoría de los hombres de oración recordados en estas páginas llegaron",
            "La mayoría de los grandes hombres de oración llegaron",
        ),
    ],
    ("derek-prince", "fr"): [
        (
            "La plupart des hommes de ce livre ont appris à prier",
            "La plupart des grands hommes de prière ont appris à prier",
        ),
        (
            "partie du témoignage que ce livre est ici pour consigner.",
            "partie de son témoignage.",
        ),
        (
            "La plupart des hommes de prière dont on se souvient dans ces pages vinrent",
            "La plupart des grands hommes de prière vinrent",
        ),
    ],
    ("derek-prince", "pt"): [
        (
            "A maioria dos homens deste livro aprendeu a orar",
            "A maioria dos grandes homens de oração aprendeu a orar",
        ),
        (
            "parte do testemunho que este livro está aqui para registrar.",
            "parte do seu testemunho.",
        ),
        (
            "A maioria dos homens de oração lembrados nestas páginas chegou",
            "A maioria dos grandes homens de oração chegou",
        ),
    ],
}


def _swap(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def reword(apps, schema_editor):
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    for (slug, language), pairs in SUBSTITUTIONS.items():
        for tr in AuthorTranslation.objects.filter(
            author__slug=slug, language=language
        ):
            changed = []
            html = _swap(tr.bio_html, pairs)
            if html != tr.bio_html:
                tr.bio_html = html
                changed.append("bio_html")
            faq = [
                {**item, "a": _swap(item["a"], pairs)}
                if isinstance(item, dict) and isinstance(item.get("a"), str)
                else item
                for item in (tr.faq or [])
            ]
            if faq != (tr.faq or []):
                tr.faq = faq
                changed.append("faq")
            if changed:
                tr.save(update_fields=[*changed, "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0188_bonhoeffer_bio_standalone_translations"),
    ]

    operations = [
        migrations.RunPython(reword, migrations.RunPython.noop),
    ]
