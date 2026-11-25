"""The admin routes load their views on first use (config/lazy_views.py).

Two promises to keep: a lazy route is indistinguishable from the eager one it
replaced, and the worker's startup really does skip the heavy modules — the
saving is ~38 MB per recycle, and one stray eager import in config/urls.py would
quietly take all of it back.
"""

from __future__ import annotations

import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import URLPattern, get_resolver
from rest_framework.views import APIView

from config.lazy_views import LazyView

#: Imported only by admin / email / jobs views. If one of these is loaded right
#: after `import config.urls`, an eager import has crept back in.
HEAVY_ADMIN_MODULES = (
    "library.admin_views",
    "library.admin_import_views",
    "emails.admin_views",
    "emails.broadcasts",
    "emails.translation_jobs",
    "pymupdf",
    "mammoth",
)


def _lazy_patterns() -> list[URLPattern]:
    return [
        p
        for p in get_resolver().url_patterns
        if isinstance(p, URLPattern) and isinstance(p.callback, LazyView)
    ]


class LazyRouteFidelityTests(SimpleTestCase):
    def test_every_admin_route_is_lazy(self):
        lazy = {str(p.pattern) for p in _lazy_patterns()}
        self.assertGreaterEqual(len(lazy), 70, "almost no lazy routes found")
        self.assertTrue(all(route.startswith("api/admin/") for route in lazy))

    def test_a_lazy_route_looks_like_the_eager_one(self):
        for p in _lazy_patterns():
            with self.subTest(route=str(p.pattern)):
                cls = p.callback.cls
                self.assertTrue(issubclass(cls, APIView))
                # Same lookup string as the real as_view() callable — which
                # holds only if the module named is the one defining the class.
                self.assertEqual(p.lookup_str, f"{cls.__module__}.{cls.__qualname__}")
                real = cls.as_view()
                for attr in ("csrf_exempt", "login_required"):
                    self.assertEqual(
                        getattr(p.callback, attr), getattr(real, attr), attr
                    )


class StartupSkipsAdminModulesTests(SimpleTestCase):
    def test_import_and_reverse_load_no_admin_module(self):
        # A fresh interpreter: this test process has long since imported them.
        script = (
            "import sys, django\n"
            "django.setup()\n"
            "import config.urls\n"
            "from django.urls import get_resolver, reverse\n"
            "get_resolver().reverse_dict\n"
            "reverse('admin-stats'); reverse('admin-broadcast-detail', args=[1])\n"
            f"print(','.join(m for m in {HEAVY_ADMIN_MODULES!r} if m in sys.modules))\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", script],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings"},
        )
        self.assertEqual(
            out.stdout.strip(), "", f"loaded at startup: {out.stdout.strip()}"
        )

    def test_concurrent_first_requests_do_not_deadlock_on_import(self):
        # A cold worker's dashboard fires several admin requests at once. While
        # library/admin_views/__init__.py re-exported every submodule, resolving
        # them on parallel threads imported overlapping module sets and raised
        # _DeadlockError (a 500) every time this ran. A fresh interpreter, since
        # this process has every module imported already.
        script = (
            "import threading, django\n"
            "django.setup()\n"
            "import config.urls\n"
            "from django.urls import get_resolver\n"
            "from config.lazy_views import LazyView\n"
            "views = [p.callback for p in get_resolver().url_patterns\n"
            "         if isinstance(p.callback, LazyView)]\n"
            "gate = threading.Barrier(len(views))\n"
            "errors = []\n"
            "def hit(v):\n"
            "    gate.wait()\n"
            "    try:\n"
            "        v.cls\n"
            "    except Exception as e:\n"
            "        errors.append(type(e).__name__)\n"
            "threads = [threading.Thread(target=hit, args=(v,)) for v in views]\n"
            "[t.start() for t in threads]\n"
            "[t.join() for t in threads]\n"
            "print(','.join(sorted(set(errors))))\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", script],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings"},
        )
        self.assertEqual(out.stdout.strip(), "", f"errors resolving views: {out.stdout.strip()}")
