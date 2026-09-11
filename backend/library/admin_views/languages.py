"""Admin dashboard API — administering a LANGUAGE, as distinct from the content in it.

Everything here reads or writes the Language registry, which CLAUDE.md calls the
runtime source: identity, Bible code, glossary, readiness thresholds and the
live switch. That is what lets an admin add a language without a deploy, and it
is why these endpoints mutate config rather than content.

The readiness → thresholds → go-live trio is one story and belongs together: a
language goes live when its content clears the bar its thresholds set, and the
deploy check is the last gate before it does.

`content.py` keeps the other half — what content exists, per language and across
the library — which is read-only inventory."""

from __future__ import annotations

import re

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from .. import golive, readiness
from ..audit import AdminAudited
from ..language_seed import SEED_LANGUAGES
from ..language_suggestions import licence_for, suggestions
from ..models import (
    AdminAction,
    Language,
)
from ..translation import (
    GLOSSARY_TERMS,
    TAKEROOT_API,
    Ref,
    fetch_chapter,
    missing_glossary_terms,
)
from ..views import _language_entry


class AdminLanguageReadinessView(APIView):
    """Is this language ready to go live, and what is still missing?

    Separate from the language detail view on purpose: the Bible check makes a
    live call to the Take Root API, and the detail page is loaded constantly —
    paying a network round trip on every visit just to show counts would be a
    poor trade. This is fetched when you actually ask the question.

    Read-only. Nothing here launches anything; the go-live action re-runs these
    same checks server-side rather than trusting a report a browser is holding.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        data = readiness.report(lang).as_dict()
        data["status"] = lang.status
        data["thresholds"] = {
            "min_books": lang.min_books,
            "min_sermons": lang.min_sermons,
            "min_bios": lang.min_bios,
            "min_plans": lang.min_plans,
            "require_all_topics": lang.require_all_topics,
            "require_complete_ui": lang.require_complete_ui,
        }
        return Response(data)


class AdminLanguageThresholdsView(AdminAudited, APIView):
    """Edit a language's readiness bar.

    The bar is per-language and yours to set: a language with a big catalogue
    behind it should clear a higher one than a first beachhead language, and 0
    disables a check. Only thresholds are writable here — ``status`` is changed
    by the go-live action (which runs the checks) and identity belongs to the
    repo's seed, which never touches these fields once the row exists.
    """

    permission_classes = [IsAdminEmail]

    audit_action = AdminAction.Action.LANGUAGE_THRESHOLDS

    INT_FIELDS = ("min_books", "min_sermons", "min_bios", "min_plans")
    BOOL_FIELDS = ("require_all_topics", "require_complete_ui")

    def audit_entry(self, request, response):
        # The fields that moved AND what they moved to — "who lowered the book
        # requirement, and to what" is the question this has to answer, and
        # recording the whole bar every time buries the answer in five values
        # nobody touched.
        data = response.data
        return f"language:{data['code']}", {
            f: data["thresholds"][f] for f in data["updated"]
        }

    def patch(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)

        changed = []
        for f in self.INT_FIELDS:
            if f not in request.data:
                continue
            try:
                value = int(request.data[f])
            except (TypeError, ValueError):
                return Response(
                    {"detail": f"{f} must be a whole number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if value < 0:
                return Response(
                    {"detail": f"{f} cannot be negative (0 disables the check)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            setattr(lang, f, value)
            changed.append(f)

        for f in self.BOOL_FIELDS:
            if f in request.data:
                setattr(lang, f, bool(request.data[f]))
                changed.append(f)

        if not changed:
            return Response(
                {"detail": "Nothing to update."}, status=status.HTTP_400_BAD_REQUEST
            )
        lang.save(update_fields=changed)
        return Response(
            {
                "code": lang.code,
                "updated": changed,
                "thresholds": {
                    f: getattr(lang, f) for f in self.INT_FIELDS + self.BOOL_FIELDS
                },
            }
        )


class AdminLanguageGoLiveView(AdminAudited, APIView):
    """Take a language live: re-check, record, and trigger the rebuild.

    The checks run again HERE rather than trusting what the browser was holding —
    that report could be minutes old and content can change underneath it. The
    button is a request to launch, not permission to.

    Returns 409 with the blockers when a language isn't ready. `force: true`
    launches anyway, for the case where you disagree with the bar rather than as
    a way around it; the response records that it was forced. `force` does NOT
    override a hard blocker (a missing/incomplete UI catalogue): that launch
    would guarantee a failed reader build, so it is refused (409, reason
    `unbuildable`) with or without force.
    """

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.LANGUAGE_GO_LIVE

    def audit_entry(self, request, response):
        # A refused launch answers 409 and is never recorded — this only runs
        # on a launch that happened. `forced` is the fact worth keeping: it says
        # someone overrode the readiness bar rather than cleared it.
        data = response.data
        return f"language:{self.kwargs['code'].lower()}", {
            "forced": data.get("forced", False),
            "already_live": data.get("already_live", False),
            "deploy": (data.get("deploy") or {}).get("status", ""),
        }

    def post(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        if lang.is_source:
            return Response(
                {"detail": "English is the source language; it is always live."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = golive.go_live(lang, force=bool(request.data.get("force")))
        if not result["launched"]:
            return Response(result, status=status.HTTP_409_CONFLICT)
        return Response(result)


class AdminLanguageDeployCheckView(APIView):
    """Did the launch actually reach readers?

    `status` says what was decided; this says what shipped. They are different
    facts — a prerendered site only reflects a decision after a build — and
    reporting one as the other is how a dashboard starts lying.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        return Response(golive.verify_deployed(lang))


# A language code as BCP-47 uses it for our purposes: two or three letters,
# optionally a region/script subtag ("pt-br", "zh-hans"). Deliberately narrow —
# the code becomes a URL prefix, a directory name and a database key, so it is
# not a place to be permissive.
LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})?$")


def _licence_for(bible_code: str, data) -> str:
    """The licence to store for ``bible_code`` — the catalogue's answer, not the form's.

    Falls back to whatever the client sent only when the catalogue could not be
    reached or does not list the code, because "we could not ask" must not
    silently become "public domain". Trimmed to the column width: a licence name
    long enough to overflow is a mistake, and a 500 is a worse way to say so.
    """
    licence, known = licence_for(bible_code)
    if not known:
        licence = str(data.get("bible_licence", "")).strip()
    return licence[: Language._meta.get_field("bible_licence").max_length]


def _verify_bible(code: str) -> tuple[bool, str]:
    """(ok, message) for a Bible code, told apart from a network outage.

    A wrong code and an unreachable API look identical from ``fetch_chapter``
    (it returns None either way), and conflating them would reject a perfectly
    good code because our egress was down. So: no verses AND the API answers →
    the code is wrong; no verses and the API is silent → we couldn't check, say
    so and let the row be created. The readiness check asks again later.
    """
    if (fetch_chapter(code, Ref("JHN", 1)) or {}).get("verses"):
        return True, f"{code} resolves against {TAKEROOT_API}."
    if not readiness.api_reachable():
        return False, (
            f"Could not reach {TAKEROOT_API} to verify {code!r}. "
            "The language was created; its readiness check will verify the Bible "
            "once the API is reachable."
        )
    raise ValueError(
        f"Bible code {code!r} returned no verses from {TAKEROOT_API}. "
        "Scripture would be silently omitted from every translation into this "
        "language. Check the code at api.takeroot.bible and try again."
    )


def _clean_glossary(raw) -> dict:
    """Validate a submitted glossary, or raise ValueError with what's wrong.

    Complete or nothing. A half-filled glossary is the expensive failure mode:
    the translator formats whatever terms are present and renders the rest
    however it feels, chapter by chapter, at full model cost — and it all looks
    fine. Requiring the full set at creation time is why "Add a language"
    produces a language you can actually translate into.
    """
    if not isinstance(raw, dict):
        raise ValueError("glossary must be an object of term → translation.")
    cleaned = {
        str(k): str(v).strip() for k, v in raw.items() if str(v).strip()
    }
    unknown = sorted(set(cleaned) - set(GLOSSARY_TERMS))
    if unknown:
        raise ValueError(f"Unknown glossary term(s): {', '.join(unknown)}.")
    missing = missing_glossary_terms(cleaned)
    if missing:
        raise ValueError(
            f"The glossary is missing {len(missing)} term(s): {', '.join(missing)}."
        )
    return cleaned


class AdminLanguageCreateView(AdminAudited, APIView):
    """Add a language to the registry — where a new language begins.

    Creating the row is what makes a language *exist* for the rest of the
    system: it appears on the dashboard, its per-language page opens, and the
    translate_* commands can target it, because they read their Bible and
    glossary from this row. Before this endpoint a new language meant a code
    change and a deploy, which is why Arabic sat half-wired for months.

    Always created as DRAFT — creating a language and launching one are separate
    decisions, and launching runs its own checks (go-live).

    Validated hard, because everything here is expensive to get wrong: the code
    becomes a URL prefix, the Bible code decides whether scripture appears at
    all, and the glossary decides whether theological vocabulary stays
    consistent. The Bible code is checked against the live API here rather than
    at first use — the alternative is discovering it during a paid job.
    """

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.LANGUAGE_CREATE

    def audit_entry(self, request, response):
        lang = response.data["language"]
        # The Bible code and whether it verified: this is the decision that
        # silently costs the most later, because a bad code omits scripture
        # rather than failing.
        return f"language:{lang['code']}", {
            "name": lang.get("name", ""),
            "bible_code": lang.get("bible_code", ""),
            "bible_verified": response.data.get("bible_verified"),
        }

    def get(self, request):
        """What the form needs to render: the glossary it must fill, the codes
        already taken, and a ranked shortlist of what to add next. Served rather
        than hardcoded in the frontend so the two can't drift — the term list is
        the backend's contract.

        Suggestions are best-effort: they come from Take Root's live Bible
        catalogue, so if that call fails the list is empty and the form still
        works by hand. A picker that is occasionally empty is a far smaller
        problem than an admin page that will not load."""
        existing = sorted(Language.objects.values_list("code", flat=True))
        return Response(
            {
                "glossary_terms": list(GLOSSARY_TERMS),
                "existing": existing,
                "suggestions": suggestions(existing=set(existing)),
            }
        )

    def post(self, request):
        data = request.data
        code = str(data.get("code", "")).strip().lower()
        if not LANGUAGE_CODE_RE.match(code):
            return Response(
                {
                    "detail": (
                        "Language code must be 2–3 letters, optionally with a "
                        "subtag (e.g. ar, hi, fr, pt-br)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Language.objects.filter(code=code).exists():
            return Response(
                {"detail": f"{code} is already in the registry."},
                status=status.HTTP_409_CONFLICT,
            )

        name = str(data.get("name", "")).strip()
        native_name = str(data.get("native_name", "")).strip()
        if not name or not native_name:
            return Response(
                {"detail": "Both the English name and the native name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bible_code = str(data.get("bible_code", "")).strip()
        if not bible_code:
            return Response(
                {
                    "detail": (
                        "A Bible code is required — scripture quotations are taken "
                        "from a trusted translation, never from the model."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            glossary = _clean_glossary(data.get("glossary") or {})
            bible_ok, bible_note = _verify_bible(bible_code)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        last = Language.objects.order_by("-sort_order").first()
        lang = Language.objects.create(
            code=code,
            name=name,
            native_name=native_name,
            bible_code=bible_code,
            bible_label=str(data.get("bible_label", "")).strip(),
            # Looked up from the code that was SUBMITTED, not taken from the
            # form. The picker knows which Bibles are licensed, but its Bible
            # box is free text — and its placeholder is `irvhin`, the CC BY-SA
            # Hindi IRV — so trusting the client here would make the attribution
            # gate one keystroke wide. The client's value survives only when the
            # catalogue could not be asked.
            bible_licence=_licence_for(bible_code, data),
            bible_attribution=str(data.get("bible_attribution", "")).strip(),
            rtl=bool(data.get("rtl")),
            glossary=glossary,
            is_source=False,
            status=Language.Status.DRAFT,
            sort_order=(last.sort_order + 1) if last else 0,
        )
        return Response(
            {
                "language": _language_entry(lang.code),
                "bible_verified": bible_ok,
                "bible_note": bible_note,
                # Said plainly because the gap between "the row exists" and
                # "readers can see it" is where a launch goes wrong.
                "next_steps": [
                    step
                    for step in [
                        f"Queue translations for {lang.name} from its language page.",
                        # Only when the licence asks for something. Naming the
                        # file matters: the credit is rendered by the prerendered
                        # site, so a row in the database alone shows nobody
                        # anything.
                        (
                            f"{lang.bible_label or lang.bible_code} is licensed "
                            f"({lang.bible_licence}) — write its credit line in "
                            "the language's settings and add the same text to "
                            "frontend/src/lib/bibleCredit.ts. Readiness blocks "
                            "the launch until you do."
                        )
                        if lang.bible_licence
                        else "",
                        f"Add '{lang.code}' to the interface locales and translate "
                        f"frontend/messages/{lang.code}.json — a live language with no "
                        "UI catalogue fails the build.",
                        "Then press Go live when the readiness checks are clear.",
                    ]
                    if step
                ],
            },
            status=status.HTTP_201_CREATED,
        )


class AdminLanguageSettingsView(AdminAudited, APIView):
    """Edit a language's identity: names, Bible, glossary, direction.

    Refuses (409) for a language defined in ``library/language_seed.py``. Those
    rows are re-asserted from the repo on every deploy, so an edit here would
    look like it worked and silently revert the next time we ship — worse than
    not offering it. Repo-defined languages are edited in the repo; languages
    added from the admin are owned by the database.
    """

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.LANGUAGE_SETTINGS

    def audit_entry(self, request, response):
        data = response.data
        # Which fields moved, and the glossary's SIZE rather than its contents:
        # a glossary is dozens of terms and belongs in the row, not copied into
        # every log line that touched it.
        detail = {"updated": data["updated"]}
        if "bible_code" in data["updated"]:
            detail["bible_code"] = data["settings"]["bible_code"]
            detail["bible_verified"] = data.get("bible_verified")
        if "glossary" in data["updated"]:
            detail["glossary_terms"] = len(data["settings"].get("glossary") or {})
        return f"language:{data['code']}", detail

    def patch(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        if lang.code in SEED_LANGUAGES or lang.is_source:
            return Response(
                {
                    "detail": (
                        f"{lang.name} is defined in the repo "
                        "(backend/library/language_seed.py) and re-seeded on every "
                        "deploy, so changes made here would be reverted. Edit it "
                        "there instead."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        data = request.data
        changed: list[str] = []
        bible_ok, bible_note = True, ""

        # bible_licence is absent here on purpose: it is derived from the Bible
        # code below rather than accepted from the client. Everything else is
        # free text, so it is length-checked against the column — an over-long
        # value is a 400 with the limit in it, never a DataError 500.
        for f in ("name", "native_name", "bible_label", "bible_attribution"):
            if f in data:
                value = str(data[f]).strip()
                if not value and f in ("name", "native_name"):
                    return Response(
                        {"detail": f"{f} cannot be empty."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                limit = Language._meta.get_field(f).max_length
                if len(value) > limit:
                    return Response(
                        {"detail": f"{f} is limited to {limit} characters."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                setattr(lang, f, value)
                changed.append(f)

        if "rtl" in data:
            lang.rtl = bool(data["rtl"])
            changed.append("rtl")

        try:
            if "glossary" in data:
                lang.glossary = _clean_glossary(data["glossary"])
                changed.append("glossary")
            if "bible_code" in data:
                bible_code = str(data["bible_code"]).strip()
                if not bible_code:
                    raise ValueError("bible_code cannot be empty.")
                bible_ok, bible_note = _verify_bible(bible_code)
                lang.bible_code = bible_code
                changed.append("bible_code")
                # Re-derived, because the licence is a fact about the Bible and
                # not about the row. Swapping a public-domain text for a licensed
                # one and leaving the old blank licence behind would retire the
                # attribution gate at exactly the moment it starts to matter.
                lang.bible_licence = _licence_for(bible_code, data)
                changed.append("bible_licence")
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not changed:
            return Response(
                {"detail": "Nothing to update."}, status=status.HTTP_400_BAD_REQUEST
            )
        lang.save(update_fields=changed)
        return Response(
            {
                "code": lang.code,
                "updated": changed,
                "bible_verified": bible_ok,
                "bible_note": bible_note,
                "settings": language_settings(lang),
            }
        )


def language_settings(lang: Language) -> dict:
    """The identity fields, plus whether they are editable here at all.

    Public because the per-language content drill-down in ``content.py`` embeds
    it: the page shows what is translated AND what is configured, and the
    registry row is this module's to describe.
    """
    return {
        "code": lang.code,
        "name": lang.name,
        "native_name": lang.native_name,
        "bible_code": lang.bible_code,
        "bible_label": lang.bible_label,
        # Carried through so an admin-created language is gated the same way a
        # repo-seeded one is: the picker already knows a suggestion is CC-BY, and
        # dropping that on the floor at create time is what left Hindi's
        # obligation living in a code comment.
        "bible_licence": lang.bible_licence,
        "bible_attribution": lang.bible_attribution,
        "rtl": lang.rtl,
        "glossary": dict(lang.glossary or {}),
        "glossary_terms": list(GLOSSARY_TERMS),
        "missing_glossary_terms": missing_glossary_terms(lang.glossary),
        "repo_managed": lang.code in SEED_LANGUAGES or lang.is_source,
    }
