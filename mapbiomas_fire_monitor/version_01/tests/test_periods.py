"""Offline tests for sample period normalization."""

import os
import sys
import unittest

CORE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
sys.path.insert(0, CORE)

from M_periods import normalize_period, period_year


class NormalizePeriodTests(unittest.TestCase):
    def test_integer_year(self):
        self.assertEqual(normalize_period(2025), '2025')

    def test_float_year(self):
        self.assertEqual(normalize_period(2025.0), '2025')

    def test_string_year(self):
        self.assertEqual(normalize_period('2025'), '2025')

    def test_string_with_decimal(self):
        self.assertEqual(normalize_period('2025.0'), '2025')

    def test_monthly_string(self):
        self.assertEqual(normalize_period('2025_10'), '2025_10')

    def test_six_digit_integer_is_yyyymm(self):
        self.assertEqual(normalize_period(202510), '2025_10')

    def test_six_digit_string_is_yyyymm(self):
        self.assertEqual(normalize_period('202510'), '2025_10')

    def test_missing_values(self):
        self.assertEqual(normalize_period(None), '')
        self.assertEqual(normalize_period(float('nan')), '')
        self.assertEqual(normalize_period('nan'), '')
        self.assertEqual(normalize_period('<NA>'), '')


class PeriodYearTests(unittest.TestCase):
    def test_year_from_values(self):
        self.assertEqual(period_year('2025'), 2025)
        self.assertEqual(period_year('2025_10'), 2025)
        self.assertEqual(period_year(2025), 2025)
        self.assertEqual(period_year(202510), 2025)

    def test_invalid_values(self):
        self.assertIsNone(period_year(''))
        self.assertIsNone(period_year(None))
        self.assertIsNone(period_year('abc'))


if __name__ == '__main__':
    unittest.main()
