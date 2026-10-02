"""Localized copy for lifecycle emails, keyed by step then locale.

This is app-string copy (like the reader's paraglide catalog), not library
content, so it is translated per locale. English is the seed; a locale with no
block for a step falls back to English. To add a language, add a block under the
step; to add a step, add an entry to ``LIFECYCLE`` and register it in
:mod:`emails.lifecycle`.

Each block is a flat dict of strings; ``{name}`` is filled at render time.
``cta_path`` is a path on the reader site the button points to ("" = home).
"""

from __future__ import annotations

DEFAULT_LOCALE = "en"


def base_lang(locale: str) -> str:
    """A profile locale reduced to its base language code (``pt-BR`` → ``pt``).

    The one place email localization normalizes a locale, shared by the copy
    lookup and the renderer so the two can't disagree.
    """
    return (locale or DEFAULT_LOCALE).split("-")[0].lower()


LIFECYCLE: dict[str, dict[str, dict[str, object]]] = {
    "welcome": {
        "en": {
            "subject": "Welcome to Ochorus",
            "preheader": "A quiet library of Christian classics — free, forever.",
            "heading": "Welcome to Ochorus",
            "greeting": "Hello {name},",
            "paragraphs": [
                "Thank you for joining Ochorus — a free, ad-free library of "
                "public-domain Christian classics, in your language.",
                "Everything here is yours to read: the great works of prayer, "
                "devotion, and the deeper life, from Andrew Murray to Thomas à "
                "Kempis. Nothing to buy, nothing to unlock.",
                "The best way to begin is simply to start reading. Pick a book "
                "that draws you, or let a short reading plan carry you a few "
                "minutes a day.",
            ],
            "cta_label": "Start reading",
            "cta_path": "",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "Bienvenido a Ochorus",
            "preheader": "Una biblioteca serena de clásicos cristianos, gratis para siempre.",
            "heading": "Bienvenido a Ochorus",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Gracias por unirte a Ochorus, una biblioteca gratuita y sin "
                "publicidad de clásicos cristianos de dominio público, en tu idioma.",
                "Todo lo que hay aquí es tuyo para leer: las grandes obras sobre "
                "la oración, la devoción y la vida profunda. Nada que comprar, "
                "nada que desbloquear.",
                "La mejor manera de empezar es simplemente leer. Elige un libro "
                "que te atraiga, o deja que un breve plan de lectura te acompañe "
                "unos minutos al día.",
            ],
            "cta_label": "Empezar a leer",
            "cta_path": "",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "Bem-vindo ao Ochorus",
            "preheader": "Uma biblioteca tranquila de clássicos cristãos, grátis para sempre.",
            "heading": "Bem-vindo ao Ochorus",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Obrigado por se juntar ao Ochorus — uma biblioteca gratuita e "
                "sem anúncios de clássicos cristãos de domínio público, no seu idioma.",
                "Tudo aqui é seu para ler: as grandes obras sobre oração, devoção "
                "e a vida mais profunda. Nada a comprar, nada a desbloquear.",
                "A melhor forma de começar é simplesmente ler. Escolha um livro "
                "que o atraia, ou deixe que um breve plano de leitura o acompanhe "
                "alguns minutos por dia.",
            ],
            "cta_label": "Começar a ler",
            "cta_path": "",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    "pick_plan": {
        "en": {
            "subject": "A few minutes a day",
            "preheader": "A short reading plan is the easiest way to begin.",
            "heading": "Find your rhythm",
            "greeting": "Hello {name},",
            "paragraphs": [
                "The readers who stay with Ochorus almost always start the same "
                "way — with a short reading plan that asks only a few minutes a "
                "day.",
                "A plan carries you through a classic a little at a time, so the "
                "reading never piles up and the habit forms on its own. Pick one "
                "that fits the season you're in.",
            ],
            "cta_label": "Browse reading plans",
            "cta_path": "plans",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "Unos minutos al día",
            "preheader": "Un breve plan de lectura es la forma más fácil de empezar.",
            "heading": "Encuentra tu ritmo",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Los lectores que se quedan en Ochorus casi siempre empiezan de "
                "la misma manera: con un breve plan de lectura que solo pide unos "
                "minutos al día.",
                "Un plan te lleva a través de un clásico poco a poco, para que la "
                "lectura nunca se acumule y el hábito se forme solo. Elige el que "
                "se ajuste al momento en que estás.",
            ],
            "cta_label": "Ver planes de lectura",
            "cta_path": "plans",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "Alguns minutos por dia",
            "preheader": "Um breve plano de leitura é a forma mais fácil de começar.",
            "heading": "Encontre o seu ritmo",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Os leitores que ficam no Ochorus quase sempre começam da mesma "
                "forma: com um breve plano de leitura que pede apenas alguns "
                "minutos por dia.",
                "Um plano leva-o através de um clássico aos poucos, para que a "
                "leitura nunca se acumule e o hábito se forme por si. Escolha o "
                "que se ajusta ao momento em que está.",
            ],
            "cta_label": "Ver planos de leitura",
            "cta_path": "plans",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    "finish_first_book": {
        "en": {
            "subject": "Pick up where you left off",
            "preheader": "Your first book is waiting — a few minutes a day finishes it.",
            "heading": "Finish what you started",
            "greeting": "Hello {name},",
            "paragraphs": [
                "You’ve started reading — that’s the hardest step, and you’ve "
                "already taken it. The book you opened is saved right where you "
                "left off.",
                "Finishing your first book is its own quiet reward. A few minutes "
                "a day is all it takes; the rest keeps your place for you.",
            ],
            "cta_label": "Continue reading",
            "cta_path": "reading",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "Retoma donde lo dejaste",
            "preheader": "Tu primer libro te espera; unos minutos al día bastan para terminarlo.",
            "heading": "Termina lo que empezaste",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Ya empezaste a leer, que es el paso más difícil, y ya lo diste. "
                "El libro que abriste está guardado justo donde lo dejaste.",
                "Terminar tu primer libro es una recompensa en sí misma. Bastan "
                "unos minutos al día; nosotros te guardamos el lugar.",
            ],
            "cta_label": "Seguir leyendo",
            "cta_path": "reading",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "Retome de onde parou",
            "preheader": "O seu primeiro livro espera por si — uns minutos por dia bastam.",
            "heading": "Termine o que começou",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Já começou a ler — esse é o passo mais difícil, e já o deu. O "
                "livro que abriu está guardado exatamente onde parou.",
                "Terminar o seu primeiro livro é uma recompensa em si. Bastam uns "
                "minutos por dia; nós guardamos o seu lugar.",
            ],
            "cta_label": "Continuar a ler",
            "cta_path": "reading",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    "classic": {
        "en": {
            "subject": "A classic worth your time",
            "preheader": "Centuries of readers can't all be wrong.",
            "heading": "Something worth reading",
            "greeting": "Hello {name},",
            "paragraphs": [
                "If you're not sure where to start, start with a book that has "
                "already outlasted every fashion — a classic that generations of "
                "readers have returned to.",
                "These are short, deep, and quietly life-changing: Andrew "
                "Murray on humility, Brother Lawrence on the presence of God, "
                "Thomas à Kempis on the imitation of Christ. Open one tonight.",
            ],
            "cta_label": "Explore the library",
            "cta_path": "books",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "Un clásico que vale tu tiempo",
            "preheader": "Siglos de lectores no pueden estar todos equivocados.",
            "heading": "Algo que vale la pena leer",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Si no sabes por dónde empezar, empieza con un libro que ya ha "
                "sobrevivido a todas las modas: un clásico al que generaciones de "
                "lectores han vuelto una y otra vez.",
                "Son breves, profundos y silenciosamente transformadores: Andrew "
                "Murray sobre la humildad, el hermano Lorenzo sobre la presencia "
                "de Dios, Tomás de Kempis sobre la imitación de Cristo. Abre uno "
                "esta noche.",
            ],
            "cta_label": "Explorar la biblioteca",
            "cta_path": "books",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "Um clássico que vale o seu tempo",
            "preheader": "Séculos de leitores não podem estar todos errados.",
            "heading": "Algo que vale a pena ler",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Se não sabe por onde começar, comece com um livro que já "
                "sobreviveu a todas as modas: um clássico ao qual gerações de "
                "leitores voltaram vezes sem conta.",
                "São breves, profundos e silenciosamente transformadores: Andrew "
                "Murray sobre a humildade, o irmão Lourenço sobre a presença de "
                "Deus, Tomás de Kempis sobre a imitação de Cristo. Abra um esta "
                "noite.",
            ],
            "cta_label": "Explorar a biblioteca",
            "cta_path": "books",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    "comeback": {
        "en": {
            "subject": "Your reading is waiting",
            "preheader": "Pick up right where you left off.",
            "heading": "Come back to it",
            "greeting": "Hello {name},",
            "paragraphs": [
                "It's been a little while — and that's alright. The books are "
                "patient, and everything you started is exactly where you left it.",
                "A few quiet minutes is all it takes to pick the thread back up. "
                "Your place is saved and waiting whenever you are.",
            ],
            "cta_label": "Continue reading",
            "cta_path": "",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "Tu lectura te espera",
            "preheader": "Continúa justo donde lo dejaste.",
            "heading": "Vuelve a ella",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Ha pasado un tiempo, y no pasa nada. Los libros son pacientes, y "
                "todo lo que empezaste está exactamente donde lo dejaste.",
                "Unos pocos minutos tranquilos es todo lo que hace falta para "
                "retomar el hilo. Tu lugar está guardado y esperándote cuando "
                "quieras.",
            ],
            "cta_label": "Seguir leyendo",
            "cta_path": "",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "A sua leitura está à espera",
            "preheader": "Continue exatamente de onde parou.",
            "heading": "Volte a ela",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Já passou algum tempo — e não faz mal. Os livros são pacientes, "
                "e tudo o que começou está exatamente onde o deixou.",
                "Bastam uns minutos tranquilos para retomar o fio. O seu lugar "
                "está guardado e à sua espera quando quiser.",
            ],
            "cta_label": "Continuar a ler",
            "cta_path": "",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    "winback": {
        "en": {
            "subject": "Your library is still here",
            "preheader": "It’s been a while — your place is kept, and it’s all still free.",
            "heading": "We’ve kept your place",
            "greeting": "Hello {name},",
            "paragraphs": [
                "It’s been a while since you visited Ochorus, and that’s all "
                "right — life is full. We just wanted you to know your library "
                "is still here, exactly as you left it.",
                "Everything is still free, still ad-free, still yours: the great "
                "works of prayer and the deeper life, in your language. Whenever "
                "you have a few quiet minutes, a good book is waiting.",
            ],
            "cta_label": "Come back to Ochorus",
            "cta_path": "",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "Tu biblioteca sigue aquí",
            "preheader": "Ha pasado un tiempo; tu lugar está guardado y todo sigue siendo gratis.",
            "heading": "Te guardamos el lugar",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Ha pasado un tiempo desde tu última visita a Ochorus, y no "
                "pasa nada: la vida está llena. Solo queríamos que supieras que "
                "tu biblioteca sigue aquí, tal como la dejaste.",
                "Todo sigue siendo gratuito, sin publicidad y tuyo: las grandes "
                "obras sobre la oración y la vida profunda, en tu idioma. Cuando "
                "tengas unos minutos de calma, un buen libro te espera.",
            ],
            "cta_label": "Vuelve a Ochorus",
            "cta_path": "",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "A sua biblioteca continua aqui",
            "preheader": "Já faz algum tempo — o seu lugar está guardado e continua tudo gratuito.",
            "heading": "Guardámos o seu lugar",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Já faz algum tempo desde a sua última visita ao Ochorus, e não "
                "faz mal — a vida é cheia. Só queríamos que soubesse que a sua "
                "biblioteca continua aqui, tal como a deixou.",
                "Continua tudo gratuito, sem publicidade e seu: as grandes obras "
                "sobre a oração e a vida profunda, no seu idioma. Quando tiver "
                "uns minutos tranquilos, um bom livro está à espera.",
            ],
            "cta_label": "Volte ao Ochorus",
            "cta_path": "",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    # Finish-the-series nudge. Dynamic per reader: ``{finished}`` is the book they
    # just finished and ``{next}`` the next volume — both filled at render time
    # (emails/rendering.py), like ``{name}``. ``cta_path`` is set per reader (it
    # points at the next volume), so the block's value here is only a fallback.
    "finish_series": {
        "en": {
            "subject": "The story continues: {next}",
            "preheader": "You finished {finished} — the next volume is waiting.",
            "heading": "Ready for the next one?",
            "greeting": "Hello {name},",
            "paragraphs": [
                "You finished {finished} — we hope it was time well spent.",
                "It’s part of a series, and the next volume, {next}, is ready "
                "for you whenever you are. One book leads into the next.",
            ],
            "cta_label": "Start {next}",
            "cta_path": "",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "La historia continúa: {next}",
            "preheader": "Terminaste {finished}; el siguiente volumen te espera.",
            "heading": "¿Listo para el siguiente?",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Terminaste {finished}, y esperamos que haya sido un tiempo bien "
                "aprovechado.",
                "Forma parte de una serie, y el siguiente volumen, {next}, está "
                "listo para cuando quieras. Un libro lleva al siguiente.",
            ],
            "cta_label": "Empezar {next}",
            "cta_path": "",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "A história continua: {next}",
            "preheader": "Terminou {finished} — o próximo volume está à espera.",
            "heading": "Pronto para o próximo?",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Terminou {finished}, e esperamos que tenha sido tempo bem "
                "passado.",
                "Faz parte de uma série, e o próximo volume, {next}, está pronto "
                "para quando quiser. Um livro leva ao seguinte.",
            ],
            "cta_label": "Começar {next}",
            "cta_path": "",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
    # Reading milestone. ``{count}`` is the milestone reached (filled at render
    # time, like ``{name}``). A celebration, so a warm subject and a gentle CTA
    # back to the library for the next one.
    "milestone": {
        "en": {
            "subject": "{count} books — well done",
            "preheader": "A real milestone. Here’s to the next one.",
            "heading": "{count} books read",
            "greeting": "Hello {name},",
            "paragraphs": [
                "You’ve now finished {count} books on Ochorus — that’s a genuine "
                "milestone, and worth pausing to mark.",
                "Each one is a classic that has steadied and stirred readers for "
                "generations, and you’ve read it through. Here’s to the next, "
                "whenever you’re ready.",
            ],
            "cta_label": "Find your next book",
            "cta_path": "",
            "signoff": "Grace and peace,",
            "signature": "The Ochorus team",
        },
        "es": {
            "subject": "{count} libros: bien hecho",
            "preheader": "Todo un logro. Por el siguiente.",
            "heading": "{count} libros leídos",
            "greeting": "Hola {name}:",
            "paragraphs": [
                "Ya has terminado {count} libros en Ochorus, y eso es todo un "
                "logro que vale la pena celebrar.",
                "Cada uno es un clásico que ha fortalecido y conmovido a lectores "
                "durante generaciones, y lo has leído entero. Por el siguiente, "
                "cuando quieras.",
            ],
            "cta_label": "Encuentra tu próximo libro",
            "cta_path": "",
            "signoff": "Gracia y paz,",
            "signature": "El equipo de Ochorus",
        },
        "pt": {
            "subject": "{count} livros: parabéns",
            "preheader": "Um verdadeiro marco. Ao próximo.",
            "heading": "{count} livros lidos",
            "greeting": "Olá {name},",
            "paragraphs": [
                "Já terminou {count} livros no Ochorus — isso é um verdadeiro "
                "marco, e vale a pena parar para celebrar.",
                "Cada um é um clássico que fortaleceu e tocou leitores durante "
                "gerações, e leu-o até ao fim. Ao próximo, quando quiser.",
            ],
            "cta_label": "Encontre o seu próximo livro",
            "cta_path": "",
            "signoff": "Graça e paz,",
            "signature": "A equipa do Ochorus",
        },
    },
}


def step_copy(step: str, locale: str) -> dict[str, object]:
    """The copy for ``step`` in ``locale``, falling back to English."""
    by_locale = LIFECYCLE[step]
    return by_locale.get(base_lang(locale), by_locale[DEFAULT_LOCALE])


def welcome_copy(locale: str) -> dict[str, object]:
    """Back-compat accessor for the welcome step."""
    return step_copy("welcome", locale)
