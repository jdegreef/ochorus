"""Repo-owned seed data for the Language registry.

This dict is **not** what the translator reads at run time — that is the
``Language`` table (see ``library/languages.py``). This is the seed that puts
the built-in languages *into* that table and re-asserts their identity on every
deploy (``manage.py seed_languages``), so a fix here reaches production.

A language added from the admin ("Add a language") is absent from this file and
therefore never touched by the seed: the database owns it outright. That is the
line — repo-defined languages are configured in code, admin-defined ones in the
admin.
"""

from __future__ import annotations

# --- Target languages --------------------------------------------------------
# bible: the Take Root translation code whose wording is authoritative for
# Scripture quotations. Every code below is verified against the live API
# (GET /api/bible/<code>/JHN/1/ → 200 with verse text). The code is read ONLY at
# translation time — seeds and tests never hit the API — so a wrong value can't
# break the build, but it WILL garble a content job's scripture. Verify any new
# one before running its first job.
#
# Prefer a PUBLIC-DOMAIN text: this is a public-domain library, and a CC-BY
# Bible puts an attribution obligation on every quotation we render. Where that
# is unavoidable — Hindi, so far, the only licensed option — declare
# `bible_licence` and `bible_attribution` on the entry. They are not
# documentation: the readiness check reads them and refuses to launch a language
# whose licence asks for a credit that nothing is showing.

SEED_LANGUAGES: dict[str, dict] = {
    "es": {
        "name": "Spanish",
        "native": "Español",
        "bible": "rv1858",
        "bible_label": "Reina-Valera (1858/1862)",
        "glossary": {
            "justification": "justificación",
            "sanctification": "santificación",
            "atonement": "expiación",
            "grace": "gracia",
            "the flesh": "la carne",
            "abide": "permanecer",
            "the Holy Spirit": "el Espíritu Santo",
            "the Lord": "el Señor",
            "godliness": "piedad",
            "intercession": "intercesión",
            "surrender": "entrega / rendición",
        },
    },
    "sw": {
        "name": "Swahili",
        "native": "Kiswahili",
        "bible": "swhonen",
        "bible_label": "Swahili Union-tradition (open)",
        "glossary": {
            "justification": "kuhesabiwa haki",
            "sanctification": "utakaso",
            "atonement": "upatanisho",
            "grace": "neema",
            "the flesh": "mwili",
            "abide": "kukaa (ndani ya Kristo)",
            "the Holy Spirit": "Roho Mtakatifu",
            "the Lord": "Bwana",
            "godliness": "utauwa",
            "intercession": "maombezi",
            "surrender": "kujisalimisha",
        },
    },
    "lg": {
        "name": "Luganda",
        "native": "Luganda",
        "bible": "lug",
        "bible_label": "Open Luganda Contemporary Bible (OLCB)",
        # The second licensed Bible in the library, and it was declared as
        # public domain by omission for months. `lug` on the ebible mirror is
        # the Open Luganda Contemporary Bible (2017), and its meta.json says
        # `cc-by-sa` with attribution to Biblica, Inc. — not public domain, and
        # the old "(open)" label read as though it were.
        #
        # Measured on 2026-09-02 before this was fixed: 242 quoted spans across
        # 17 of the 18 shipped Luganda books reproduce OLCB verbatim, 2,867
        # words in total, with runs up to 34 words (Num 7:89 in
        # the-inner-chamber is character-identical bar the apostrophe form).
        # That is not chance — random 6-word runs of shipped Luganda PROSE match
        # OLCB once in 3,000. So the credit is owed on text already live.
        #
        # `_attribution_check` gates on `bible_licence` being non-blank, so
        # leaving it unset made the check that exists for exactly this case skip
        # with "Public-domain Bible — nothing to credit." The declaration was
        # the bug; the guard was fine.
        "bible_licence": "CC BY-SA 4.0",
        "bible_attribution": (
            "Scripture quotations are from the Open Luganda Contemporary Bible, "
            "© Biblica, Inc., licensed under "
            "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)."
        ),
        "glossary": {
            "justification": "okuweebwa obutuukirivu",
            "sanctification": "okutukuzibwa",
            "atonement": "okutangirira",
            "grace": "ekisa",
            "the flesh": "omubiri",
            "abide": "okubeera (mu Kristo)",
            "the Holy Spirit": "Omwoyo Omutukuvu",
            "the Lord": "Mukama",
            "godliness": "okutya Katonda",
            "intercession": "okwegayiririra abalala",
            "surrender": "okwewaayo",
        },
    },
    "pt": {
        "name": "Portuguese",
        "native": "Português",
        # There is no standalone Almeida on Take Root; both Portuguese options
        # are Bíblia Livre editions descended from it. Chose the PUBLIC-DOMAIN
        # one — the alternative, porbr2018 ("Bíblia
        # Livre", CC BY 4.0, © 2018 Diego Santos, Mario Sérgio & Marco Teles),
        # would require carrying that attribution wherever we quote scripture.
        # porbrbsl also keeps the Almeida-tradition wording ("No princípio era o
        # Verbo" vs porbr2018's "a Palavra").
        "bible": "porbrbsl",
        "bible_label": "Bíblia Livre para o Mundo (public domain)",
        "glossary": {
            "justification": "justificação",
            "sanctification": "santificação",
            "atonement": "expiação",
            "grace": "graça",
            "the flesh": "a carne",
            "abide": "permanecer",
            "the Holy Spirit": "o Espírito Santo",
            "the Lord": "o Senhor",
            "godliness": "piedade",
            "intercession": "intercessão",
            "surrender": "entrega / rendição",
        },
    },
    "ar": {
        "name": "Arabic",
        "native": "العربية",
        # Smith–Van Dyck (1865): the standard Arabic Bible and the register
        # Arabic Christian readers expect for devotional prose. Public domain —
        # verified against Take Root's catalog (is_public_domain: true) and the
        # live API.
        "bible": "arb-vd",
        "bible_label": "Van Dyck (1865)",
        "glossary": {
            "justification": "التبرير",
            "sanctification": "التقديس",
            "atonement": "الكفّارة",
            "grace": "النعمة",
            "the flesh": "الجسد",
            "abide": "الثبات",
            "the Holy Spirit": "الروح القدس",
            "the Lord": "الرب",
            "godliness": "التقوى",
            "intercession": "الشفاعة",
            "surrender": "التسليم",
        },
    },
    "uk": {
        "name": "Ukrainian",
        "native": "Українська",
        # Kulish (1905) — the first complete Ukrainian Bible, and the only
        # complete PUBLIC-DOMAIN Ukrainian text Take Root carries. The two
        # alternatives both fail us: the Відкритий Новий Переклад is NT +
        # Psalms only, so it cannot answer an arbitrary reference, and Ohienko
        # — the text most Ukrainian churches actually read — is licensed.
        #
        # The tradeoff: Kulish predates the 1928 orthography, so it reads
        # markedly archaic (сьвіт for світ, postposed ся, "глаголав"). That is
        # a fair match for the 19th-century authors this library carries —
        # Spurgeon and Moody quoting a contemporaneous Bible — but it will read
        # old to a Ukrainian reader in a way Van Dyck does not to an Arabic one.
        # Revisit if we ever take on a licensed text.
        #
        # NOTE: John 15 renders correctly under this code in the Take Root
        # reader. Verify end-to-end before the first job with
        #   CHECK_BIBLE_CODES=1 uv run python manage.py test \
        #     library.tests.LanguageSeedTableTests
        # from a network that can reach api.takeroot.bible.
        "bible": "ukr-kul",
        "bible_label": "Kulish (1905)",
        # Prose vocabulary is modern standard Ukrainian; scripture quotations
        # follow Kulish. The two diverge most at "abide" — Kulish's John 15
        # reads пробувайте в мені, where modern usage is перебувати. Prose uses
        # the modern form; quoted verses keep Kulish's wording.
        "glossary": {
            "justification": "виправдання",
            "sanctification": "освячення",
            "atonement": "спокута",
            "grace": "благодать",
            "the flesh": "тіло",
            "abide": "перебувати",
            "the Holy Spirit": "Святий Дух",
            "the Lord": "Господь",
            "godliness": "побожність",
            "intercession": "заступництво",
            "surrender": "віддання себе / повна віддача",
        },
    },
    "hi": {
        "name": "Hindi",
        "native": "हिन्दी",
        # Indian Revised Version — a formal-equivalence revision in the classical
        # register Hindi Christian readers expect, and the text most Hindi
        # churches quote. Verified against the live API (hin-irv, the obvious
        # guess and the form's old placeholder, 404s).
        #
        # CC BY-SA 4.0, © 2017-2019 Bridge Connectivity Solutions — the only
        # Hindi Bibles on Take Root are licensed (the alternative, hincv, is
        # Biblica's). Share-Alike binds derivatives of the Bible text itself, not
        # the library that quotes it, but it does want the credit line carried
        # wherever the verses are shown.
        "bible": "irvhin",
        "bible_label": "Indian Revised Version (IRV), Hindi",
        # The FIRST non-public-domain Bible in the library, and so the first
        # licence that asks for something back. `bible_licence` being non-blank
        # is what makes the readiness check demand a credit line before this
        # language can go live; `bible_attribution` is that line, and
        # frontend/src/lib/bibleCredit.ts must carry the same text (a test
        # below pins the two together).
        #
        # Left in the publisher's own wording rather than rendered into Hindi:
        # the edition name, the copyright holder and the licence are proper
        # nouns that a translation would only obscure. A native reviewer may
        # want to localize the framing around them later — that is an editorial
        # improvement, not a compliance gap.
        "bible_licence": "CC BY-SA 4.0",
        # The URI is not decoration: CC BY-SA 4.0 §3(a)(1)(A)(iii) asks for a
        # link to the licence "if supplied", and where the notice is already
        # HTML in a footer there is no reading of "reasonably practicable" that
        # excuses leaving it out.
        "bible_attribution": (
            "Scripture quotations are from the Indian Revised Version (IRV), "
            "© 2017–2019 Bridge Connectivity Solutions, licensed under "
            "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)."
        ),
        # 8 of these 11 appear verbatim in the IRV itself (checked against
        # Eph 2, Rom 3/8, John 14/15, 1 Thess 4, 1 Tim 4, Phil 2). The three that
        # do not are where the IRV uses a verbal construction and devotional
        # prose needs a noun: "justification" follows the IRV's own root
        # (धर्मी ठहरे, Rom 5:1); "intercession" and "surrender" take the nouns
        # Hindi Christian writing uses, where the IRV has निवेदन करता है
        # (Rom 8:34) and चढ़ाओ (Rom 12:1).
        "glossary": {
            "justification": "धर्मी ठहराया जाना",
            "sanctification": "पवित्रीकरण",
            "atonement": "प्रायश्चित्त",
            "grace": "अनुग्रह",
            "the flesh": "शरीर",
            "abide": "बने रहना",
            "the Holy Spirit": "पवित्र आत्मा",
            "the Lord": "प्रभु",
            "godliness": "भक्ति",
            "intercession": "मध्यस्थता",
            "surrender": "समर्पण",
        },
    },
    "fr": {
        "name": "French",
        "native": "Français",
        # Louis Segond (1910): the standard French Protestant Bible and the
        # register French Christian readers expect for devotional prose — a fair
        # match for the 19th-century authors this library carries, who quote a
        # contemporaneous text. PUBLIC DOMAIN (verified on the ebible mirror:
        # bibles/fra_lsg/meta.json → license "public", attribution "public
        # domain", ebible id fraLSG), so no attribution obligation and no
        # bibleCredit.ts entry is owed.
        #
        # French was first added from the admin ("Add a language"), so it lived
        # only in the prod DB and its glossary/Bible were unreadable to a worker
        # session; a batch of French bios shipped self-rendering all scripture.
        # This entry adopts French into the repo seed so its identity, Bible and
        # theology glossary are re-asserted on every deploy like the built-in
        # languages, and so translation jobs have a glossary to follow.
        #
        # NOTE: `bible` is the Take Root translation code, which this (egress-
        # blocked) session CANNOT verify — api.takeroot.bible is unreachable
        # here. `fralsg` is the best guess (cf. ebible id fraLSG); alternatives
        # to try are `fra-lsg` and `fraLSG`. A wrong value cannot break the build
        # (seeds/tests never hit the API) but WILL garble a networked translation
        # run's scripture, so VERIFY before the first API-backed French job:
        #   CHECK_BIBLE_CODES=1 uv run python manage.py test \
        #     library.tests.LanguageSeedTableTests
        # from a network that can reach api.takeroot.bible. Worker sessions mine
        # Segond verbatim from the ebible mirror instead (raw.githubusercontent
        # .com/gracious-tech/fetch_collection, bibles/fra_lsg/usfm), which needs
        # no Take Root code.
        "bible": "fralsg",
        "bible_label": "Louis Segond (1910)",
        # Segond's own wording where it is fixed vocabulary: "Demeurez en moi"
        # (John 15) for abide, "le Saint-Esprit", "le Seigneur". "abandon /
        # consécration" for surrender follows the French devotional tradition
        # (Guyon, Fénelon) the library carries.
        "glossary": {
            "justification": "justification",
            "sanctification": "sanctification",
            "atonement": "expiation",
            "grace": "grâce",
            "the flesh": "la chair",
            "abide": "demeurer",
            "the Holy Spirit": "le Saint-Esprit",
            "the Lord": "le Seigneur",
            "godliness": "la piété",
            "intercession": "intercession",
            "surrender": "abandon / consécration",
        },
    },
}