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
}


def step_copy(step: str, locale: str) -> dict[str, object]:
    """The copy for ``step`` in ``locale``, falling back to English."""
    by_locale = LIFECYCLE[step]
    return by_locale.get(base_lang(locale), by_locale[DEFAULT_LOCALE])


def welcome_copy(locale: str) -> dict[str, object]:
    """Back-compat accessor for the welcome step."""
    return step_copy("welcome", locale)
