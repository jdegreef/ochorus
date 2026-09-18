"""Localized copy for lifecycle emails.

This is app-string copy (like the reader's paraglide catalog), not library
content, so it is translated per locale. English is the seed; other locales fall
back to English until their copy is written. To add a language, add a block to
``WELCOME`` — the pipeline already renders whatever locale the reader has.

Each block is a flat dict of strings; ``{name}`` is filled at render time.
"""

from __future__ import annotations

DEFAULT_LOCALE = "en"

WELCOME: dict[str, dict[str, object]] = {
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
            "The best way to begin is simply to start reading. Pick a book that "
            "draws you, or let a short reading plan carry you a few minutes a day.",
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
            "Todo lo que hay aquí es tuyo para leer: las grandes obras sobre la "
            "oración, la devoción y la vida profunda. Nada que comprar, nada que "
            "desbloquear.",
            "La mejor manera de empezar es simplemente leer. Elige un libro que "
            "te atraiga, o deja que un breve plan de lectura te acompañe unos "
            "minutos al día.",
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
            "Obrigado por se juntar ao Ochorus — uma biblioteca gratuita e sem "
            "anúncios de clássicos cristãos de domínio público, no seu idioma.",
            "Tudo aqui é seu para ler: as grandes obras sobre oração, devoção e "
            "a vida mais profunda. Nada a comprar, nada a desbloquear.",
            "A melhor forma de começar é simplesmente ler. Escolha um livro que "
            "o atraia, ou deixe que um breve plano de leitura o acompanhe alguns "
            "minutos por dia.",
        ],
        "cta_label": "Começar a ler",
        "cta_path": "",
        "signoff": "Graça e paz,",
        "signature": "A equipa do Ochorus",
    },
}


def base_lang(locale: str) -> str:
    """A profile locale reduced to its base language code (``pt-BR`` → ``pt``).

    The one place email localization normalizes a locale, shared by the copy
    lookup and the renderer so the two can't disagree.
    """
    return (locale or DEFAULT_LOCALE).split("-")[0].lower()


def welcome_copy(locale: str) -> dict[str, object]:
    """The welcome copy for ``locale``, falling back to English."""
    return WELCOME.get(base_lang(locale), WELCOME[DEFAULT_LOCALE])
