"""Taking a language live — the one place that does it.

**A launch is not a data change.** The reader is a prerendered static site: its
UI catalogues, pages, `sitemap.xml` and hreflang tags are all produced at build
time. So flipping `Language.status` to LIVE changes nothing a reader can see
until a build runs. This module therefore does both — records the decision, then
fires the web service's deploy hook — and reports honestly about each half,
because "status changed" and "readers can see it" are different facts and
conflating them is how you get a dashboard that lies.

The checks are re-run HERE, server-side, rather than trusting the report the
browser was holding: that report could be minutes old, and content can change
underneath it. The button is a request to launch, not permission to.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from django.conf import settings
from django.utils import timezone

from . import readiness
from .models import Language


@dataclass
class DeployResult:
    """What happened when we tried to trigger the rebuild."""

    status: str  # "triggered" | "not_configured" | "failed"
    detail: str

    @property
    def ok(self) -> bool:
        return self.status == "triggered"


#: The workflow that rebuilds ochorus-web alone at a given commit, through
#: Render's REST API (.github/workflows/rebuild-reader.yml).
REBUILD_WORKFLOW = "rebuild-reader.yml"
# Env-overridable like the job queue's (library/admin_views/jobs.py).
GITHUB_API = os.getenv("GITHUB_API_BASE", "https://api.github.com")


def trigger_web_deploy() -> DeployResult:
    """Rebuild the reader: pinned to this API's commit under the train, else the hook.

    Under the deploy train, build the commit this API runs, not main's tip:
    main can hold content this API hasn't released, and a web build of the tip
    would wait on the API for content it will never serve, then fail. The train
    keeps every service on one commit, so this commit's frontend is also what
    the reader already runs. Without the train (auto-deploy) the reader may be
    AHEAD of this commit, so pinning would roll it back.

    The pin can't ride on the deploy hook: Render answers a hook carrying
    `ref=<sha>` with a 500 (2026-10-14). So it goes through a GitHub workflow
    that calls Render's REST API with `commitId`, which keeps the workspace-wide
    Render key in GitHub's secrets and leaves this service holding only a token
    that can start a workflow. If that dispatch fails, the unpinned hook still
    fires: a rebuild that may stall at the content gate beats no rebuild.

    Never raises: a launch that recorded its status but failed to deploy is a
    recoverable state (deploy again), whereas an exception here would leave the
    caller unsure whether the status flip happened at all.
    """
    unpinned_because = ""
    if settings.DEPLOY_TRAIN and settings.RELEASE_COMMIT:
        if not settings.GITHUB_DEPLOY_TOKEN:
            unpinned_because = "no GITHUB_DEPLOY_TOKEN set"
        else:
            pinned = _dispatch_pinned_rebuild(settings.RELEASE_COMMIT)
            if pinned.ok:
                return pinned
            unpinned_because = pinned.detail

    hook = settings.RENDER_WEB_DEPLOY_HOOK
    if not hook:
        detail = (
            "No RENDER_WEB_DEPLOY_HOOK set, so no rebuild was triggered. The "
            "language is recorded as live but readers won't see it until the "
            "site is deployed — trigger a deploy in Render, or set the hook."
        )
        if unpinned_because:
            # A pinned path was configured and failed: that's a failure to
            # retry, not a setup gap.
            detail += f" (The pinned rebuild didn't start either: {unpinned_because}.)"
            return DeployResult("failed", detail)
        return DeployResult("not_configured", detail)
    also = f" The pinned rebuild didn't start either: {unpinned_because}." if unpinned_because else ""
    try:
        res = requests.post(hook, timeout=20)
    except requests.RequestException as e:
        return DeployResult("failed", f"Deploy hook unreachable ({e.__class__.__name__}).{also}")
    if not res.ok:
        return DeployResult("failed", f"Deploy hook returned {res.status_code}.{also}")
    detail = "Rebuild triggered; readers see it when it finishes."
    if unpinned_because:
        detail += (
            f" It builds main's tip, not this API's commit ({unpinned_because}); if "
            "main holds content the API hasn't released, that build fails at its "
            "content gate and the next deploy train ships the change."
        )
    return DeployResult("triggered", detail)


def _dispatch_pinned_rebuild(commit: str) -> DeployResult:
    """Start the rebuild-reader workflow for `commit`; never raises."""
    url = (
        f"{GITHUB_API}/repos/{settings.GITHUB_TRANSLATION_REPO}"
        f"/actions/workflows/{REBUILD_WORKFLOW}/dispatches"
    )
    try:
        res = requests.post(
            url,
            json={"ref": "main", "inputs": {"commit": commit}},
            headers={
                "Authorization": f"Bearer {settings.GITHUB_DEPLOY_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            timeout=20,
        )
    except requests.RequestException as e:
        return DeployResult("failed", f"GitHub unreachable ({e.__class__.__name__})")
    if not res.ok:
        # 403/404: the token lacks `actions: write`; 422: the workflow is missing.
        return DeployResult("failed", f"workflow dispatch returned {res.status_code}")
    return DeployResult(
        "triggered",
        f"Rebuild of {commit[:8]} (the commit this API runs) started; readers see "
        "it when it finishes.",
    )


def go_live(lang: Language, *, force: bool = False) -> dict:
    """Record a language as live and trigger the rebuild.

    ``force`` launches despite failing checks — a deliberate override for the
    case where you disagree with the bar rather than a way around it. The
    blockers are still reported, so the decision is visible afterwards.

    Its limit: a *hard* blocker (``report.hard_blockers``) is refused even when
    forced — see ``readiness._ui_check`` for why forcing past one only trades a
    caught problem for a frozen deploy. The guard lives here, the one admin path
    that flips status LIVE; a direct ``status = LIVE`` write (a seed) bypasses it.
    """
    report = readiness.report(lang)
    hard = report.hard_blockers
    if hard:
        return {
            "launched": False,
            "reason": "unbuildable",
            "blocking": [c.key for c in hard],
            "readiness": report.as_dict(),
        }
    if not report.ready and not force:
        return {
            "launched": False,
            "reason": "not_ready",
            "readiness": report.as_dict(),
        }

    already = lang.is_live
    lang.status = Language.Status.LIVE
    # Stamp the FIRST launch only: this is when the language became public, and
    # re-running the action (say, to re-trigger a deploy) shouldn't rewrite that.
    if lang.went_live_at is None:
        lang.went_live_at = timezone.now()
    lang.save(update_fields=["status", "went_live_at"])

    # Route through the one content-changed channel so go-live also bumps the
    # content revision (the ETag/rebuild signal). `force` bypasses the throttle:
    # a launch is a deliberate single action that must always rebuild and report
    # its result. Imported locally because invalidation imports this module.
    from . import invalidation

    deploy = invalidation.mark_content_changed(force=True)
    return {
        "launched": True,
        "already_live": already,
        "forced": bool(force and not report.ready),
        "went_live_at": lang.went_live_at.isoformat() if lang.went_live_at else None,
        "deploy": {"status": deploy.status, "detail": deploy.detail},
        "readiness": report.as_dict(),
    }


def verify_deployed(lang: Language) -> dict:
    """Has the built site actually caught up — is this locale in the sitemap?

    The honest answer to "did my launch land", which the status field cannot
    give: it reflects the decision, not the deploy. Fetches the live sitemap and
    looks for evidence of the locale.

    THE SIGNAL IS THE PAGES CHILD. `sitemap.xml` is a `<sitemapindex>` over
    per-type children whose NAMES carry no locale — chapters used to supply a
    per-locale `sitemap-chapters-<code>.xml`, but chapters are no longer
    advertised (frontend `$lib/sitemap`). So we fetch a child and read the locale
    out of its URLs. `sitemap-pages.xml` is the right child: it lists the static
    app pages for EVERY advertised locale unconditionally (`/<code>/…`), so its
    presence answers exactly "did this locale's build land" — a locale cannot be
    advertised without them. (The books child would miss a locale that is live
    but has no books yet.) One extra request over the old one-child design.

    This survives the deploy-skew window (API and reader are separate Render
    services): the pages child and its locale-prefixed `<loc>`s existed in the
    PREVIOUS index shape too, and the flat `<urlset>` branch below still covers
    the oldest shape — so a launch checked mid-deploy still reads true. The
    `/<code>/` match is the very predicate that branch already uses.
    """
    site = settings.PUBLIC_SITE_URL
    if not site:
        return {
            "status": "unknown",
            "detail": "No PUBLIC_SITE_URL set, so the built site can't be checked from here.",
        }
    if lang.is_source:
        return {"status": "n/a", "detail": "English is served at the site root."}
    try:
        res = requests.get(f"{site}/sitemap.xml", timeout=20)
    except requests.RequestException as e:
        return {
            "status": "unknown",
            "detail": f"Could not fetch {site}/sitemap.xml ({e.__class__.__name__}).",
        }
    if not res.ok:
        return {"status": "unknown", "detail": f"Sitemap returned {res.status_code}."}
    if "<sitemapindex" in res.text:
        # The index names no locale, so fetch the pages child and read this
        # locale out of its URLs. Every advertised locale has static app pages
        # (`{site}/<code>/…`), so this answers "did the build include this
        # locale". Anchored at the host and pinned to a whole segment by the
        # trailing slash — the SAME predicate the flat branch below uses — so it
        # can't match `/<code>/` deeper in a path (a topic slug) or the prefix of
        # a regional code ("/ar/" inside a future "/ar-EG/").
        try:
            pages = requests.get(f"{site}/sitemap-pages.xml", timeout=20)
        except requests.RequestException as e:
            return {
                "status": "unknown",
                "detail": f"Could not fetch {site}/sitemap-pages.xml ({e.__class__.__name__}).",
            }
        if pages.ok and f"{site}/{lang.code}/" in pages.text:
            return {
                "status": "deployed",
                "detail": f"{lang.code} URLs are in the live sitemap.",
            }
    elif f"{site}/{lang.code}/" in res.text:
        return {"status": "deployed", "detail": f"{lang.code} URLs are in the live sitemap."}
    return {
        "status": "pending",
        "detail": (
            f"No {lang.code} URLs in the live sitemap yet — the deploy may still be "
            "running, or it failed. Check the Render dashboard."
        ),
    }
