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
# Bible would put an attribution obligation on every quotation we render.

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
        "bible_label": "Luganda Bible (open)",
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
}
