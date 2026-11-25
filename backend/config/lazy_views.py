"""Route a DRF view without importing its module until the route is first hit.

Why: ``config.urls`` is imported on the worker's first request, and importing
every admin / email / jobs view eagerly cost ~38 MB of the ~58 MB the URLconf
added (PyMuPDF + mammoth for the import wizard, the broadcast and translation
job stacks, the analytics package). Reader traffic never reaches those views,
and the API is a 512 MB instance recycled every ~500 requests, so that memory
was paid on every recycle for nothing.

``lazy_view("pkg.module", "SomeView")`` stands in for ``SomeView.as_view()``.
It looks like the real callback to everything that inspects a routed view
*without* calling it, so nothing about a route changes:

- ``__module__`` / ``__qualname__`` give the same ``URLPattern.lookup_str`` the
  real view has — pass the module that DEFINES the class, not a re-export
  (``config.tests_lazy_views`` checks this for every lazy route). Note there is
  deliberately no ``view_class``: ``lookup_str`` probes it with ``hasattr`` while
  ``reverse()`` builds its tables, which would import every view again.
- ``csrf_exempt`` / ``login_required`` are what DRF's ``APIView.as_view()`` sets,
  read by Django's middleware before the view runs.
- ``cls`` imports and returns the class, so the URL-walking guards
  (``tests_admin_access``, ``tests_audit``, ``accounts.tests_authz``) still see
  every view's permission classes.

The first call imports the module and builds the real ``as_view()`` callable;
later calls go straight to it. That first import is serialised by one lock
across every lazy view. Without it, the dashboard's opening burst (stats,
trends, attention, the queue — four first requests at once, on the worker's
four threads) imported overlapping admin modules in parallel, and Python's
import machinery answered the cycle with ``_DeadlockError``: a 500 on a cold
worker's first dashboard load. The lock is taken only until a view resolves.

Only for DRF ``APIView`` subclasses (the attributes above are DRF's), and only
for modules with no import-time side effects (signal receivers, admin
registrations, checks) — those must keep loading at startup, via ``AppConfig.ready``.
"""

from __future__ import annotations

import threading
from importlib import import_module

#: Held while a lazy view imports its module (see the module docstring).
#: Re-entrant, because importing one view module can resolve another.
_IMPORT_LOCK = threading.RLock()


class LazyView:
    # What rest_framework.views.APIView.as_view() puts on its callable.
    csrf_exempt = True
    login_required = False

    def __init__(self, module: str, name: str):
        self.__module__ = module
        self.__name__ = self.__qualname__ = name
        self._view = None

    def _resolve(self):
        view = self._view
        if view is None:
            with _IMPORT_LOCK:
                view = self._view
                if view is None:
                    view = self._view = getattr(
                        import_module(self.__module__), self.__name__
                    ).as_view()
        return view

    @property
    def cls(self):
        return self._resolve().cls

    def __call__(self, request, *args, **kwargs):
        return self._resolve()(request, *args, **kwargs)

    def __repr__(self):
        return f"<lazy_view {self.__module__}.{self.__qualname__}>"


def lazy_view(module: str, name: str) -> LazyView:
    return LazyView(module, name)
