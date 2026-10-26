"""The default cache's table exists and works (settings.CACHES, accounts/0016).

Under ``manage.py test`` the default alias is a dummy, so nothing else in the
suite touches the real backend; a migration that built the wrong table would
only show up as a 500 on the first deploy. This drives a real DatabaseCache
against the migrated table, on SQLite and on CI's Postgres alike.
"""

from __future__ import annotations

from django.core.cache.backends.db import DatabaseCache
from django.test import TestCase


class SharedCacheTableTests(TestCase):
    def setUp(self):
        self.cache = DatabaseCache("django_cache", {"KEY_PREFIX": "test"})

    def test_round_trips_through_the_migrated_table(self):
        value = (7, [{"book": "john", "chapter": 3}], {"en", "fr"})
        self.cache.set("memo", value, timeout=None)
        self.assertEqual(self.cache.get("memo"), value)
        self.cache.delete("memo")
        self.assertIsNone(self.cache.get("memo"))

    def test_another_release_cannot_read_this_ones_entries(self):
        self.cache.set("memo", "old")
        other = DatabaseCache("django_cache", {"KEY_PREFIX": "next"})
        self.assertIsNone(other.get("memo"))
