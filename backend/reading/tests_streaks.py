"""Unit tests for the pure streak arithmetic (reading/streaks.py)."""

from datetime import date

from django.test import SimpleTestCase

from .streaks import reading_streaks


class ReadingStreaksTests(SimpleTestCase):
    TODAY = date(2026, 9, 12)

    def test_empty(self):
        self.assertEqual(reading_streaks([], today=self.TODAY), (0, 0))

    def test_single_day_today(self):
        self.assertEqual(reading_streaks([self.TODAY], today=self.TODAY), (1, 1))

    def test_run_ending_today_is_current(self):
        days = [date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12)]
        self.assertEqual(reading_streaks(days, today=self.TODAY), (3, 3))

    def test_run_ending_yesterday_still_current(self):
        # Today isn't over — a reader who read yesterday keeps the streak.
        days = [date(2026, 9, 10), date(2026, 9, 11)]
        self.assertEqual(reading_streaks(days, today=self.TODAY), (2, 2))

    def test_run_ending_two_days_ago_is_broken(self):
        days = [date(2026, 9, 9), date(2026, 9, 10)]
        current, longest = reading_streaks(days, today=self.TODAY)
        self.assertEqual(current, 0)
        self.assertEqual(longest, 2)

    def test_longest_is_an_earlier_run(self):
        # A long-ago 4-day run, then a live 2-day run.
        days = [
            date(2026, 8, 1),
            date(2026, 8, 2),
            date(2026, 8, 3),
            date(2026, 8, 4),
            date(2026, 9, 11),
            date(2026, 9, 12),
        ]
        self.assertEqual(reading_streaks(days, today=self.TODAY), (2, 4))

    def test_duplicate_dates_tolerated(self):
        days = [self.TODAY, self.TODAY, date(2026, 9, 11)]
        self.assertEqual(reading_streaks(days, today=self.TODAY), (2, 2))

    def test_unordered_input(self):
        days = [date(2026, 9, 12), date(2026, 9, 10), date(2026, 9, 11)]
        self.assertEqual(reading_streaks(days, today=self.TODAY), (3, 3))
