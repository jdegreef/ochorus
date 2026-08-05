"""Create the launch reading plans from books already in the library.

Idempotent: a plan is only created if its slug doesn't exist yet for the
language, and only if the source book is present with enough chapters. Run on
deploy (release command) after the library is seeded.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Book, Plan, PlanDay

# (plan slug, source book slug, title, description)
LAUNCH_PLANS = [
    (
        "humility-12-days",
        "humility-2",
        "Humility in 12 Days",
        "Andrew Murray's classic on the root of every virtue — one short chapter "
        "a day for twelve days.",
    ),
    (
        "the-inner-chamber-month",
        "the-inner-chamber",
        "A Month in the Inner Chamber",
        "Build a daily habit of prayer and the Word: thirty-six mornings with "
        "Andrew Murray, one chapter each day.",
    ),
]

# Curated plans that walk through SEVERAL books in order (each book read in
# full, chapter by chapter). Days are numbered sequentially across the books.
# A plan is created only in a language where EVERY source book is present and
# published (so a partially-translated set is skipped, not shipped half-empty).
#   (plan slug, title, description, [ordered source book slugs])
CURATED_PLANS = [
    (
        "school-of-prayer",
        "A School of Prayer",
        "Four weeks in the school of prayer with three guides: Andrew Murray on "
        "how the Lord himself teaches us to pray, D. L. Moody on prevailing "
        "prayer, and Hannah Buyinza on prayer as the daily pulse of the "
        "Christian life.",
        [
            "lord-teach-us-to-pray-2",
            "prevailing-prayer",
            "prayer-the-pulse-of-life",
        ],
    ),
    (
        "deeper-life-in-christ",
        "The Deeper Life: Christ in You",
        "Not more effort, but a Person: the secret of the deeper life is Christ "
        "himself living within. Andrew Murray opens with the wonder of Jesus "
        "himself, then unfolds the indwelling life, and Hudson Taylor closes in "
        "the rest of union and communion with the Beloved.",
        [
            "jesus-himself-2",
            "the-masters-indwelling",
            "union-and-communion",
        ],
    ),
    (
        "grace-for-every-sinner",
        "The Way to God: Grace for Every Sinner",
        "A month on the oldest good news there is. Richard Baxter's tender call "
        "to the unconverted, D. L. Moody on the way to God, and Charles "
        "Spurgeon's All of Grace — the plainest of guides to how a sinner is "
        "saved, and how to know it.",
        [
            "a-call-to-the-unconverted",
            "the-way-to-god",
            "all-of-grace",
        ],
    ),
    (
        "faith-in-the-fire",
        "The God of All Comfort: Faith in the Fire",
        "For the days that are hard to pray through. Hannah Whitall Smith on the "
        "God of all comfort, and Gareth Evans on trusting the One who holds our "
        "tomorrows — a five-week walk into settled peace when life is uncertain.",
        [
            "the-god-of-all-comfort",
            "he-holds-my-tomorrows",
        ],
    ),
    (
        "power-from-on-high",
        "Power from on High: The Holy Spirit",
        "Four weeks with R. A. Torrey on the Spirit-filled life: first the "
        "baptism with the Holy Spirit and the power it brings for service, then "
        "the fuller study of the Person and work of the Spirit who indwells "
        "every believer.",
        [
            "baptism-with-the-holy-spirit",
            "the-person-and-work-of-the-holy-spirit",
        ],
    ),
    (
        "everything-for-christ",
        "Everything for Christ: A Life Poured Out",
        "What does whole-hearted surrender cost, and what does it yield? David "
        "Brainerd's searching missionary diary, followed by the stories of men "
        "and women who gave everything for the sake of the gospel — a call to "
        "consecration told through lives that answered it.",
        [
            "life-and-diary-of-david-brainerd",
            "men-and-women-who-gave-everything-2",
        ],
    ),
]


# Per-language plan prose. A plan is a per-language row (like Book), so the
# translation replaces the English title/description on the row for that
# language; missing languages/plans fall back to the English tuple in the defs.
# AI-drafted, pending native review.
#   {language: {slug: (title, description)}}
PLAN_TRANSLATIONS = {
    # A plan is listed in a language only once all of its source books are
    # translated, because seed_plans creates a plan only where EVERY source book
    # is present; an entry here for a plan that cannot render is dead weight
    # that reads like a bug. So each new entry below arrives with its books.
    "ar": {
        "the-inner-chamber-month": (
            "شهر في المخدع",
            "ابنِ عادةً يوميّة في الصلاة وكلمة الله: ستّة وثلاثون صباحًا مع "
            "أندرو موراي، فصلٌ واحد كلّ يوم.",
        ),
        "power-from-on-high": (
            "قوّة من الأعالي: الروح القدس",
            "أربعة أسابيع مع ر. أ. توري في الحياة المملوءة بالروح: أوّلًا "
            "المعمودية بالروح القدس والقوّة التي تمنحها للخدمة، ثمّ الدرس "
            "الأوفى في أقنوم الروح الساكن في كلّ مؤمنٍ وعمله.",
        ),
        # The three guides are named with the exact Arabic titles their books
        # ship under, so the plan and the library agree.
        "school-of-prayer": (
            "مدرسة الصلاة",
            "أربعة أسابيع في مدرسة الصلاة مع ثلاثة معلّمين: أندرو موراي في كيف "
            "يعلّمنا الربّ نفسه أن نصلّي، ود. ل. مودي في الصلاة الغالبة، وحنّة "
            "بوينزا في الصلاة بوصفها نبض الحياة المسيحيّة اليوميّ.",
        ),
    },
    "pt": {
        "humility-12-days": (
            "Humildade em 12 Dias",
            "O clássico de Andrew Murray sobre a raiz de toda virtude — um "
            "capítulo curto por dia durante doze dias.",
        ),
        "the-inner-chamber-month": (
            "Um Mês na Câmara Interior",
            "Construa o hábito diário da oração e da Palavra: trinta e seis "
            "manhãs com Andrew Murray, um capítulo a cada dia.",
        ),
        "school-of-prayer": (
            "Uma Escola de Oração",
            "Quatro semanas na escola da oração com três guias: Andrew Murray "
            "sobre como o próprio Senhor nos ensina a orar, D. L. Moody sobre a "
            "oração perseverante e Hannah Buyinza sobre a oração como o pulso "
            "diário da vida cristã.",
        ),
        "deeper-life-in-christ": (
            "A Vida Mais Profunda: Cristo em Vós",
            "Não mais esforço, mas uma Pessoa: o segredo da vida mais profunda é "
            "o próprio Cristo vivendo em nós. Andrew Murray começa com a "
            "maravilha de Jesus mesmo, depois desdobra a vida que habita no "
            "interior, e Hudson Taylor conclui no repouso da união e comunhão "
            "com o Amado.",
        ),
        "grace-for-every-sinner": (
            "O Caminho para Deus: Graça para Todo Pecador",
            "Um mês sobre as boas-novas mais antigas que existem. O terno "
            "chamado de Richard Baxter aos não convertidos, D. L. Moody sobre o "
            "caminho para Deus, e o Tudo pela Graça de Charles Spurgeon — os "
            "mais simples dos guias sobre como um pecador é salvo, e como "
            "sabê-lo.",
        ),
        "power-from-on-high": (
            "Poder do Alto: O Espírito Santo",
            "Quatro semanas com R. A. Torrey sobre a vida cheia do Espírito: "
            "primeiro o batismo com o Espírito Santo e o poder que ele traz "
            "para o serviço, e depois o estudo mais pleno da Pessoa e da obra "
            "do Espírito que habita em todo crente.",
        ),
    },
    "es": {
        "power-from-on-high": (
            "Poder de lo alto: El Espíritu Santo",
            "Cuatro semanas con R. A. Torrey sobre la vida llena del Espíritu: "
            "primero el bautismo con el Espíritu Santo y el poder que trae para "
            "el servicio, y luego el estudio más pleno de la Persona y la obra "
            "del Espíritu que mora en todo creyente.",
        ),
    },
    "lg": {
        "power-from-on-high": (
            "Amaanyi Agava Waggulu: Omwoyo Omutukuvu",
            "Wiiki nnya ne R. A. Torrey ku bulamu obujjudde Omwoyo: okusooka "
            "okubatizibwa n'Omwoyo Omutukuvu n'amaanyi ge galeeta olw'obuweereza, "
            "n'oluvannyuma okuyiga okujjuvu ku Muntu n'omulimu gw'Omwoyo abeera mu "
            "buli mukkiriza.",
        ),
        "humility-12-days": (
            "Obwetoowaze mu Nnaku 12",
            "Ekitabo kya Andrew Murray eky'edda ku musingi gwa buli mpisa "
            "ennungi — essuula emu ennyimpi buli lunaku okumala ennaku kkumi na "
            "bbiri.",
        ),
        "the-inner-chamber-month": (
            "Omwezi mu Kisenge eky'omunda",
            "Zimba empisa eya buli lunaku ey'okusaba n'Ekigambo: enkya amakumi "
            "asatu mu mukaaga ne Andrew Murray, essuula emu buli lunaku.",
        ),
        "faith-in-the-fire": (
            "Katonda ow'Okubudaabuda Kwonna: Okukkiriza mu Muliro",
            "Ku nnaku ezo ezisinga okuzibuwalira okusaba. Hannah Whitall Smith "
            "ku Katonda ow'okubudaabuda kwonna, ne Gareth Evans ku kwesiga oyo "
            "akwata ennaku zaffe ez'omu maaso — olugendo lwa wiiki ttaano "
            "okutuuka mu mirembe eginywevu ng'obulamu tebukakafu.",
        ),
        "school-of-prayer": (
            "Essomero ery'Okusaba",
            "Wiiki nnya mu ssomero ery'okusaba n'abakulembeze basatu: Andrew "
            "Murray ku ngeri Mukama gy'atuyigiriza yekka okusaba, D. L. Moody ku "
            "kusaba okuwangula, ne Hannah Buyinza ku kusaba ng'okukuba kw'omutima "
            "okwa buli lunaku mu bulamu obw'Ekikristaayo.",
        ),
    },
    "sw": {
        "power-from-on-high": (
            "Nguvu kutoka Juu: Roho Mtakatifu",
            "Wiki nne pamoja na R. A. Torrey kuhusu maisha yaliyojaa Roho: kwanza "
            "ubatizo wa Roho Mtakatifu na nguvu unazoleta kwa ajili ya huduma, "
            "kisha uchunguzi kamili zaidi wa Nafsi na kazi ya Roho anayekaa ndani "
            "ya kila mwamini.",
        ),
        "school-of-prayer": (
            "Shule ya Maombi",
            "Wiki nne katika shule ya maombi pamoja na waelekezi watatu: Andrew "
            "Murray kuhusu jinsi Bwana mwenyewe anavyotufundisha kuomba, D. L. "
            "Moody kuhusu maombi yenye kushinda, na Hannah Buyinza kuhusu maombi "
            "kama mapigo ya kila siku ya maisha ya Mkristo.",
        ),
    },
}


def _prose(slug, lang, en_title, en_description):
    """Localized (title, description) for a plan, else the English original."""
    return PLAN_TRANSLATIONS.get(lang, {}).get(slug) or (en_title, en_description)


class Command(BaseCommand):
    help = "Seed launch reading plans from existing books (idempotent)."

    def _reconcile_existing(self, slug, lang, title, description) -> bool:
        """If a plan already exists for (slug, lang), keep its prose in sync with
        the defs/translations and return True (caller skips creation). An edited
        or newly-added translation thus reaches prod on the next redeploy."""
        plan = Plan.objects.filter(slug=slug, language=lang).first()
        if not plan:
            return False
        if (plan.title, plan.description) != (title, description):
            plan.title = title
            plan.description = description
            plan.save(update_fields=["title", "description"])
            self.stdout.write(f"Updated plan {slug} ({lang}) prose.")
        return True

    def handle(self, *args, **opts):
        created = 0
        for slug, book_slug, title, description in LAUNCH_PLANS:
            for book in Book.objects.filter(slug=book_slug, is_published=True):
                t, d = _prose(slug, book.language, title, description)
                if self._reconcile_existing(slug, book.language, t, d):
                    continue
                orders = list(
                    book.chapters.order_by("order").values_list("order", flat=True)
                )
                if not orders:
                    continue
                plan = Plan.objects.create(
                    slug=slug,
                    language=book.language,
                    title=t,
                    description=d,
                    sort_order=created,
                )
                PlanDay.objects.bulk_create(
                    [
                        PlanDay(
                            plan=plan,
                            day=i + 1,
                            book_slug=book_slug,
                            chapter_order=order,
                        )
                        for i, order in enumerate(orders)
                    ]
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created plan {slug} ({book.language}) with {len(orders)} days."
                    )
                )

        created += self._seed_curated(created)

        if not created:
            self.stdout.write("Plans already seeded (or source books missing).")

    def _seed_curated(self, sort_base):
        """Create multi-book curated plans, once per language that has them all."""
        created = 0
        for slug, title, description, book_slugs in CURATED_PLANS:
            wanted = set(book_slugs)
            langs = set(
                Book.objects.filter(slug__in=book_slugs, is_published=True)
                .values_list("language", flat=True)
            )
            for lang in sorted(langs):
                t, d = _prose(slug, lang, title, description)
                if self._reconcile_existing(slug, lang, t, d):
                    continue
                by_slug = {
                    b.slug: b
                    for b in Book.objects.filter(
                        slug__in=book_slugs, language=lang, is_published=True
                    )
                }
                if set(by_slug) != wanted:
                    continue  # not every source book exists (published) in this language
                days = [
                    (bslug, order)
                    for bslug in book_slugs
                    for order in by_slug[bslug]
                    .chapters.order_by("order")
                    .values_list("order", flat=True)
                ]
                if not days:
                    continue
                plan = Plan.objects.create(
                    slug=slug,
                    language=lang,
                    title=t,
                    description=d,
                    sort_order=sort_base + created,
                )
                PlanDay.objects.bulk_create(
                    [
                        PlanDay(
                            plan=plan,
                            day=i + 1,
                            book_slug=bslug,
                            chapter_order=order,
                        )
                        for i, (bslug, order) in enumerate(days)
                    ]
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created curated plan {slug} ({lang}) with {len(days)} days "
                        f"across {len(book_slugs)} books."
                    )
                )
        return created
