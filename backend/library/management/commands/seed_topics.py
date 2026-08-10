"""Create the curated topical shelves from books already in the library.

Idempotent: a topic is created only if its slug doesn't exist yet, and its
membership is upserted each run (new books added to existing topics as the
library grows). Members are soft slug-references — a slug that isn't present in
a given language simply doesn't appear on that language's shelf, so a topic can
be seeded ahead of a book landing. Run on deploy (see release.py).

Topic titles/descriptions are seeded in English; per-language translations live
in ``TopicTranslation``. There is NO English fallback: a topic with no title in
a language is omitted from that language's shelf list and its page 404s there
(``Topic.is_translated_into``), so a shelf only exists where it has been
translated. This mirrors ``seed_plans``, whose curated prose is English too.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Topic, TopicBook, TopicSermon, TopicTranslation

# (slug, title, description, [ordered member book slugs]). A book may appear in
# several topics — topics are overlapping shelves, not exclusive categories.
TOPICS = [
    (
        "prayer",
        "On Prayer",
        "Learning to pray — and to keep praying. The classics on the inner life "
        "of prayer, from the secret place to prevailing intercession.",
        [
            "the-inner-chamber",
            "lord-teach-us-to-pray-2",
            "let-us-pray-2",
            "prevailing-prayer",
            "answers-to-prayer",
            "men-of-prayer-2",
            "prayer-the-pulse-of-life",
            "cheque-book",
        ],
    ),
    (
        "holy-spirit",
        "The Holy Spirit",
        "The Spirit's baptism, indwelling and work — the promised power for the "
        "Christian life.",
        [
            "baptism-with-the-holy-spirit",
            "the-person-and-work-of-the-holy-spirit",
            "the-masters-indwelling",
            "jesus-himself-2",
        ],
    ),
    (
        "deeper-life",
        "The Deeper Life",
        "Holiness, surrender and the abundant life hidden with Christ — books for "
        "going further in.",
        [
            "humility-2",
            "the-christians-secret-of-a-happy-life-4",
            "purity-of-heart",
            "way-into-holiest",
            "if",
            "the-normal-christian-life",
        ],
    ),
    (
        "grace-and-comfort",
        "Grace & Comfort",
        "The unfailing grace of God and his comfort in every trial — good news "
        "for the weary.",
        [
            "all-of-grace",
            "grace-for-grace-2",
            "the-god-of-all-comfort",
            "the-unselfishness-of-god",
            "he-holds-my-tomorrows",
            "the-way-to-god",
            "all-things-for-good",
        ],
    ),
    (
        "revival-and-missions",
        "Revival & Missions",
        "Lives poured out for the gospel, and seasons of awakening — fuel for a "
        "burning heart.",
        [
            "revival-lectures",
            "life-and-diary-of-david-brainerd",
            "things-as-they-are",
            "men-and-women-who-gave-everything-2",
            "women-who-moved-heaven-2",
            "union-and-communion",
            "men-who-moved-heaven",
        ],
    ),
    (
        "faith-and-guidance",
        "Faith & Guidance",
        "Trusting God for daily bread, direction and every promise — walking by "
        "faith, not sight.",
        [
            "the-secret-of-guidance",
            "days-of-heaven-upon-earth",
            "the-fourfold-gospel",
            "soar-like-the-eagle-3",
            "waiting-on-god",
        ],
    ),
    (
        "the-gospel-call",
        "The Gospel Call",
        "The oldest invitation there is \u2014 come, repent, believe. Preachers "
        "pleading with the unconverted, and the testimony of grace found by the "
        "chief of sinners.",
        [
            "a-call-to-the-unconverted",
            "around-the-wicket-gate",
            "grace-abounding",
        ],
    ),
    (
        "enduring-classics",
        "The Enduring Classics",
        "The books that have walked with pilgrims for centuries \u2014 "
        "Augustine's confession, Bunyan's dream, the counsel of \u00e0 Kempis "
        "\u2014 the old paths, still good.",
        [
            "confessions",
            "pilgrims-progress",
            "the-imitation-of-christ",
            "freedom-of-the-will",
        ],
    ),
    (
        "the-way-of-holiness",
        "The Way of Holiness",
        "Set apart for God \u2014 the commandments searched, perfection "
        "honestly pursued, and the affections of the heart tried and found "
        "true.",
        [
            "plain-account-christian-perfection",
            "godliness",
            "religious-affections",
            "ten-commandments",
        ],
    ),
    (
        "the-preached-word",
        "The Preached Word",
        "Great preaching on the page \u2014 Whitefield and Wesley in full "
        "voice, Spurgeon among his farmers \u2014 and Baxter's charge to every "
        "shepherd of souls.",
        [
            "selected-sermons-whitefield",
            "sermons-on-several-occasions",
            "talks-to-the-farmer",
            "till-he-come",
            "the-reformed-pastor",
            "men-who-tended-the-flock-2",
        ],
    ),
]


# Sermon members per topic, by canonical sermon slug (language-agnostic, like
# the book members). A sermon shows on a topic's shelf in each language it
# exists in. {topic slug: [ordered sermon slugs]}
TOPIC_SERMONS = {
    "prayer": [
        "the-golden-key-of-prayer",
        "order-and-argument-in-prayer",
        "pauls-first-prayer",
    ],
    "deeper-life": ["himself", "christ-all-in-all"],
    "grace-and-comfort": [
        "free-grace",
        "the-immutability-of-god",
        "sweet-comfort-for-feeble-saints",
        "comfort-for-the-desponding",
        "consolation-in-the-furnace",
    ],
    "revival-and-missions": [
        "compel-them-to-come-in",
        "the-way-of-salvation",
        "christs-boundless-compassion",
    ],
    "faith-and-guidance": ["the-possibilities-of-faith", "unfailing-springs"],
    "the-gospel-call": [
        "christ-crucified",
        "the-new-birth",
        "salvation-by-faith",
        "come-thou-into-the-ark",
        "the-dying-thief",
        "the-ravens-cry",
    ],
    "the-way-of-holiness": ["aggressive-christianity"],
}


# A themed Scripture epigraph per topic (KJV — public domain), shown on the
# topic page. {slug: (reference, verse text)}
TOPIC_SCRIPTURE = {
    "prayer": (
        "Jeremiah 33:3",
        "Call unto me, and I will answer thee, and shew thee great and mighty "
        "things, which thou knowest not.",
    ),
    "holy-spirit": (
        "Zechariah 4:6",
        "Not by might, nor by power, but by my spirit, saith the Lord of hosts.",
    ),
    "deeper-life": (
        "Colossians 3:3",
        "For ye are dead, and your life is hid with Christ in God.",
    ),
    "grace-and-comfort": (
        "2 Corinthians 12:9",
        "My grace is sufficient for thee: for my strength is made perfect in "
        "weakness.",
    ),
    "revival-and-missions": (
        "Habakkuk 3:2",
        "O Lord, revive thy work in the midst of the years, in the midst of the "
        "years make known.",
    ),
    "faith-and-guidance": (
        "Proverbs 3:6",
        "In all thy ways acknowledge him, and he shall direct thy paths.",
    ),
    "the-gospel-call": (
        "2 Corinthians 5:20",
        "We pray you in Christ\u2019s stead, be ye reconciled to God.",
    ),
    "enduring-classics": (
        "Jeremiah 6:16",
        "Stand ye in the ways, and see, and ask for the old paths, where is "
        "the good way, and walk therein, and ye shall find rest for your "
        "souls.",
    ),
    "the-way-of-holiness": (
        "Hebrews 12:14",
        "Follow peace with all men, and holiness, without which no man shall "
        "see the Lord.",
    ),
    "the-preached-word": (
        "Romans 10:14",
        "How shall they hear without a preacher?",
    ),
}

# Localized epigraphs (reference localized to the target-language Bible book
# name; verse in that language's reverent register). AI-drafted, pending native
# review. {language: {slug: (reference, verse text)}}
TOPIC_SCRIPTURE_TR = {
    "lg": {
        "prayer": (
            "Yeremiya 33:3",
            "Munkoowoole, nange ndikuyitaba, ne nkulaga ebintu ebikulu era "
            "eby'ekitalo, by'otomanyi.",
        ),
        "holy-spirit": (
            "Zekkaliya 4:6",
            "Si na maanyi, so si na buyinza, wabula na Mwoyo gwange, bw'ayogera "
            "Mukama ow'eggye.",
        ),
        "deeper-life": (
            "Abakkolosaayi 3:3",
            "Kubanga mwafa, n'obulamu bwammwe bukwekeddwa mu Kristo mu Katonda.",
        ),
        "grace-and-comfort": (
            "2 Abakkolinso 12:9",
            "Ekisa kyange kikumala: kubanga amaanyi gange gatuukirizibwa mu "
            "bunafu.",
        ),
        "revival-and-missions": (
            "Kaabakuuku 3:2",
            "Ai Mukama, zzaamu obulamu omulimu gwo wakati mu myaka, wakati mu "
            "myaka gumanyise.",
        ),
        "faith-and-guidance": (
            "Engero 3:6",
            "Mu makubo go gonna mumumanye, naye alitereeza amakubo go.",
        ),
    },
}


# Per-language topic prose, upserted into TopicTranslation each run. A language
# missing here has NO shelf for that topic — it is omitted rather than shown in
# English, so adding a language here is what makes its shelves exist.
# AI-drafted, pending native review (the same review flow as book translations).
# Theological vocabulary follows the per-language glossaries in
# library/translation.py, so a shelf reads consistently with the books on it.
#
# Scripture (TOPIC_SCRIPTURE_TR) is deliberately NOT drafted here: verse wording
# comes from the trusted Bible for that language via the Take Root API, never
# from a model's memory (see library/translation.py). The topic page renders no
# verse block when it's absent, so a shelf is complete without one.
#   {language: {slug: (title, description)}}
TOPIC_TRANSLATIONS = {
    "lg": {
        "prayer": (
            "Ku Kusaba",
            "Okuyiga okusaba — era n'okunyiikira okusaba obutakoowa. Ebitabo "
            "eby'edda ebyogera ku bulamu obw'omunda obw'okusaba, okuva mu kifo "
            "eky'ekyama okutuuka ku kwegayiririra abalala okw'amaanyi.",
        ),
        "holy-spirit": (
            "Omwoyo Omutukuvu",
            "Okubatizibwa kw'Omwoyo, okutuula kwe mu ffe, n'omulimu gwe — amaanyi "
            "agaasuubizibwa ag'obulamu obw'Ekikristaayo.",
        ),
        "deeper-life": (
            "Obulamu Obw'obuziba",
            "Obutukuvu, okwewaayo, n'obulamu obw'ekyengera obukwekeddwa mu Kristo "
            "— ebitabo eby'okugenda mu maaso ennyo mu by'omwoyo.",
        ),
        "grace-and-comfort": (
            "Ekisa n'Okubudaabuda",
            "Ekisa kya Katonda ekitaggwaawo n'okubudaabuda kwe mu kugezesebwa "
            "kwonna — amawulire amalungi eri abakooye.",
        ),
        "revival-and-missions": (
            "Okuzuukusibwa n'Obuweereza bw'Enjiri",
            "Obulamu obwawaayo olw'enjiri, n'ebiseera eby'okuzuukusibwa — "
            "eky'okwongera omuliro mu mutima ogwaka.",
        ),
        "faith-and-guidance": (
            "Okukkiriza n'Obulagirizi",
            "Okwesiga Katonda olw'emmere eya buli lunaku, obulagirizi, na buli "
            "kisuubizo — okutambula mu kukkiriza, so si mu kulaba.",
        ),
        "the-gospel-call": (
            "Okuyita kw'Enjiri",
            "Okuyitibwa okusinga obukadde — jjangu, weenenye, kkiriza. "
            "Ababuulizi nga beegayirira abatannaba kulokoka, n'obujulirwa "
            "bw'ekisa ekyalabwa omwonoonyi asinga bonna.",
        ),
        "enduring-classics": (
            "Ebitabo eby'Edda Ebisigalawo",
            "Ebitabo ebitambulidde n'abatambuze okumala ebyasa — okwatula kwa "
            "Awugusitino, ekirooto kya Bunyan, amagezi ga Kempis — amakubo "
            "ag'edda, era nga makyali malungi.",
        ),
        "the-way-of-holiness": (
            "Ekkubo ery'Obutukuvu",
            "Okwawulibwa ku lwa Katonda — amateeka nga gakebejjebwa, "
            "obutuukirivu nga bunoonyezebwa n'obwesimbu, n'okwagala kw'omutima "
            "nga kugezesebwa ne kulabika nga kwa mazima.",
        ),
        "the-preached-word": (
            "Ekigambo Ekibuulirwa",
            "Okubuulira okw'amaanyi ku lupapula — Whitefield ne Wesley mu "
            "ddoboozi eryonna, Spurgeon mu balimi be — n'ekiragiro kya Baxter "
            "eri buli musumba w'emyoyo.",
        ),
    },
    "es": {
        "prayer": (
            "Sobre la oración",
            "Aprender a orar — y a seguir orando. Los clásicos sobre la vida "
            "interior de la oración, desde el lugar secreto hasta la intercesión "
            "perseverante.",
        ),
        "holy-spirit": (
            "El Espíritu Santo",
            "El bautismo del Espíritu, su morada en nosotros y su obra — el poder "
            "prometido para la vida cristiana.",
        ),
        "deeper-life": (
            "La vida más profunda",
            "Santidad, entrega y la vida abundante escondida con Cristo — libros "
            "para ir más adentro.",
        ),
        "grace-and-comfort": (
            "Gracia y consuelo",
            "La gracia inagotable de Dios y su consuelo en toda prueba — buenas "
            "nuevas para el cansado.",
        ),
        "revival-and-missions": (
            "Avivamiento y misiones",
            "Vidas derramadas por el evangelio, y tiempos de despertar — "
            "combustible para un corazón ardiente.",
        ),
        "faith-and-guidance": (
            "Fe y dirección",
            "Confiar en Dios para el pan de cada día, la dirección y toda promesa "
            "— andar por fe, no por vista.",
        ),
        "the-gospel-call": (
            "El llamado del evangelio",
            "La invitación más antigua que existe — ven, arrepiéntete, "
            "cree. Predicadores rogando a los no convertidos, y el testimonio de "
            "la gracia hallada por el primero de los pecadores.",
        ),
        "enduring-classics": (
            "Los clásicos perdurables",
            "Los libros que han acompañado a los peregrinos por siglos — la "
            "confesión de Agustín, el sueño de Bunyan, el consejo de Kempis — "
            "las sendas antiguas, todavía buenas.",
        ),
        "the-way-of-holiness": (
            "El camino de la santidad",
            "Apartados para Dios — los mandamientos examinados, la perfección "
            "buscada con honestidad, y los afectos del corazón probados y "
            "hallados verdaderos.",
        ),
        "the-preached-word": (
            "La palabra predicada",
            "La gran predicación en la página — Whitefield y Wesley a plena "
            "voz, Spurgeon entre sus labradores — y el encargo de Baxter a todo "
            "pastor de almas.",
        ),
    },
    "sw": {
        "prayer": (
            "Kuhusu Maombi",
            "Kujifunza kuomba — na kuendelea kuomba. Vitabu vya kale kuhusu "
            "maisha ya ndani ya maombi, kutoka mahali pa faragha hadi maombezi "
            "yenye kudumu.",
        ),
        "holy-spirit": (
            "Roho Mtakatifu",
            "Ubatizo wa Roho, kukaa kwake ndani yetu, na kazi yake — nguvu "
            "iliyoahidiwa kwa maisha ya Kikristo.",
        ),
        "deeper-life": (
            "Maisha ya Ndani Zaidi",
            "Utakatifu, kujisalimisha, na maisha tele yaliyofichwa pamoja na "
            "Kristo — vitabu vya kwenda ndani zaidi.",
        ),
        "grace-and-comfort": (
            "Neema na Faraja",
            "Neema ya Mungu isiyokoma na faraja yake katika kila jaribu — habari "
            "njema kwa waliochoka.",
        ),
        "revival-and-missions": (
            "Uamsho na Umisheni",
            "Maisha yaliyomwagwa kwa ajili ya injili, na majira ya uamsho — kuni "
            "kwa moyo unaowaka.",
        ),
        "faith-and-guidance": (
            "Imani na Uongozi",
            "Kumtumaini Mungu kwa riziki ya kila siku, mwelekeo, na kila ahadi — "
            "kuenenda kwa imani, si kwa kuona.",
        ),
        "the-gospel-call": (
            "Wito wa Injili",
            "Mwaliko wa kale kuliko yote — njoo, tubu, amini. Wahubiri "
            "wakiwasihi wasioongoka, na ushuhuda wa neema aliyoipata mkuu wa "
            "wenye dhambi.",
        ),
        "enduring-classics": (
            "Vitabu vya Kale Vidumuvyo",
            "Vitabu vilivyofuatana na wasafiri kwa karne nyingi — ungamo la "
            "Agustino, ndoto ya Bunyan, shauri la Kempis — njia za zamani, "
            "ambazo bado ni njema.",
        ),
        "the-way-of-holiness": (
            "Njia ya Utakatifu",
            "Kutengwa kwa ajili ya Mungu — amri zikichunguzwa, ukamilifu "
            "ukifuatwa kwa unyofu, na shauku za moyo zikijaribiwa na kuonekana "
            "kweli.",
        ),
        "the-preached-word": (
            "Neno Lihubiriwalo",
            "Mahubiri makuu katika kurasa — Whitefield na Wesley kwa sauti "
            "kamili, Spurgeon kati ya wakulima wake — na agizo la Baxter kwa "
            "kila mchungaji wa roho.",
        ),
    },
    "pt": {
        "prayer": (
            "Sobre a Oração",
            "Aprender a orar — e a continuar orando. Os clássicos sobre a vida "
            "interior da oração, do lugar secreto à intercessão perseverante.",
        ),
        "holy-spirit": (
            "O Espírito Santo",
            "O batismo do Espírito, a sua habitação em nós e a sua obra — o poder "
            "prometido para a vida cristã.",
        ),
        "deeper-life": (
            "A Vida Mais Profunda",
            "Santidade, entrega e a vida abundante escondida com Cristo — livros "
            "para ir mais fundo.",
        ),
        "grace-and-comfort": (
            "Graça e Consolo",
            "A graça inesgotável de Deus e o seu consolo em toda provação — boas "
            "novas para o cansado.",
        ),
        "revival-and-missions": (
            "Avivamento e Missões",
            "Vidas derramadas pelo evangelho, e tempos de despertamento — "
            "combustível para um coração ardente.",
        ),
        "faith-and-guidance": (
            "Fé e Direção",
            "Confiar em Deus para o pão de cada dia, a direção e toda promessa — "
            "andar por fé, e não por vista.",
        ),
        "the-gospel-call": (
            "O Chamado do Evangelho",
            "O convite mais antigo que existe — vem, arrepende-te, crê. "
            "Pregadores rogando aos não convertidos, e o testemunho da graça "
            "encontrada pelo principal dos pecadores.",
        ),
        "enduring-classics": (
            "Os Clássicos Duradouros",
            "Os livros que têm acompanhado os peregrinos por séculos — a "
            "confissão de Agostinho, o sonho de Bunyan, o conselho de Kempis — "
            "as veredas antigas, ainda boas.",
        ),
        "the-way-of-holiness": (
            "O Caminho da Santidade",
            "Separados para Deus — os mandamentos examinados, a perfeição "
            "buscada com honestidade, e os afetos do coração provados e achados "
            "verdadeiros.",
        ),
        "the-preached-word": (
            "A Palavra Pregada",
            "A grande pregação na página — Whitefield e Wesley em plena voz, "
            "Spurgeon entre os seus lavradores — e o encargo de Baxter a todo "
            "pastor de almas.",
        ),
    },
    # Arabic reads right-to-left; the shelf page follows the document direction,
    # so nothing here needs to encode that. Vocabulary follows the ar glossary
    # (النعمة, التسليم, الشفاعة, الروح القدس).
    "ar": {
        "prayer": (
            "في الصلاة",
            "أن نتعلّم الصلاة — وأن نُداوم عليها. كتب كلاسيكية عن حياة الصلاة "
            "الداخلية، من المخدع الخفيّ إلى الشفاعة المُلحّة.",
        ),
        "holy-spirit": (
            "الروح القدس",
            "معمودية الروح وسكناه فينا وعمله — القوة الموعودة للحياة المسيحية.",
        ),
        "deeper-life": (
            "الحياة الأعمق",
            "القداسة والتسليم والحياة الفائضة المستترة مع المسيح — كتب لمن يريد "
            "أن يمضي إلى العمق.",
        ),
        "grace-and-comfort": (
            "النعمة والتعزية",
            "نعمة الله التي لا تخيب وتعزيته في كل تجربة — بشارة للمُتعَبين.",
        ),
        "revival-and-missions": (
            "النهضة والإرساليات",
            "حياةٌ سُكبت لأجل الإنجيل، وأزمنة يقظة روحية — وقودٌ لقلبٍ مُتّقد.",
        ),
        "faith-and-guidance": (
            "الإيمان والإرشاد",
            "الاتّكال على الله في خبز كل يوم وفي الإرشاد وفي كل وعد — أن نسلك "
            "بالإيمان لا بالعيان.",
        ),
        "the-gospel-call": (
            "دعوة الإنجيل",
            "أقدم دعوة على الإطلاق — تعالَ، تُبْ، آمِنْ. "
            "وعّاظ يتوسّلون إلى غير المهتدين، وشهادة نعمةٍ "
            "نالها أول الخطاة.",
        ),
        "enduring-classics": (
            "الكلاسيكيات الخالدة",
            "الكتب التي رافقت الحجّاج عبر القرون — اعترافات "
            "أوغسطينوس، وحلم بنيان، ومشورة كمبيس — السبل "
            "القديمة، وما زالت صالحة.",
        ),
        "the-way-of-holiness": (
            "طريق القداسة",
            "مفرَزون لله — الوصايا مفحوصة، والكمال مطلوب "
            "بأمانة، وعواطف القلب ممتحَنة فوُجدت صادقة.",
        ),
        "the-preached-word": (
            "الكلمة المكروز بها",
            "الوعظ العظيم على الصفحة — وايتفيلد وويسلي بملء "
            "الصوت، وسبرجن بين فلّاحيه — ووصيّة باكستر "
            "لكلّ راعي نفوس.",
        ),
    },
}


class Command(BaseCommand):
    help = "Seed the curated topical shelves and their membership (idempotent)."

    def handle(self, *args, **opts):
        created = 0
        for order, (slug, title, description, book_slugs) in enumerate(TOPICS):
            ref, verse = TOPIC_SCRIPTURE.get(slug, ("", ""))
            topic, was_created = Topic.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": description,
                    "scripture_ref": ref,
                    "scripture_text": verse,
                    "sort_order": order,
                },
            )
            if was_created:
                created += 1
            elif (topic.scripture_ref, topic.scripture_text) != (ref, verse):
                # Backfill/refresh the epigraph on an already-seeded topic.
                topic.scripture_ref = ref
                topic.scripture_text = verse
                topic.save(update_fields=["scripture_ref", "scripture_text"])
            # Upsert membership each run so new books join existing shelves.
            added = 0
            for i, book_slug in enumerate(book_slugs):
                _, entry_created = TopicBook.objects.update_or_create(
                    topic=topic,
                    book_slug=book_slug,
                    defaults={"sort_order": i},
                )
                if entry_created:
                    added += 1
            # Upsert sermon membership the same way.
            for i, sermon_slug in enumerate(TOPIC_SERMONS.get(slug, [])):
                _, entry_created = TopicSermon.objects.update_or_create(
                    topic=topic,
                    sermon_slug=sermon_slug,
                    defaults={"sort_order": i},
                )
                if entry_created:
                    added += 1
            # Upsert per-language prose each run so an edited/added translation
            # reaches an already-seeded topic on the next deploy.
            langs = set(TOPIC_TRANSLATIONS) | set(TOPIC_SCRIPTURE_TR)
            for lang in langs:
                tr = TOPIC_TRANSLATIONS.get(lang, {}).get(slug)
                sc = TOPIC_SCRIPTURE_TR.get(lang, {}).get(slug)
                if not tr and not sc:
                    continue
                defaults = {}
                if tr:
                    defaults["title"], defaults["description"] = tr
                if sc:
                    defaults["scripture_ref"], defaults["scripture_text"] = sc
                TopicTranslation.objects.update_or_create(
                    topic=topic, language=lang, defaults=defaults
                )
            if was_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created topic {slug} with {len(book_slugs)} members."
                    )
                )
            elif added:
                self.stdout.write(f"Topic {slug}: added {added} new member(s).")

        if not created:
            self.stdout.write("Topics already seeded.")
