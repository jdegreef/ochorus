"""Admin dashboard API, split by concern — one submodule per area.

Nothing is re-exported here, on purpose: import a view from the submodule that
defines it (``from library.admin_views.content import AdminStatsView``).
config/urls.py routes each view lazily by that submodule (config/lazy_views.py),
and a package ``__init__`` that imported every submodule made any one admin
request load all of them — and two first requests on parallel threads import
overlapping module sets, which is how a cold worker's dashboard burst hit
Python's ``_DeadlockError``.
"""
