"""Parse a saved copy of Isparta's hal page (rows built from divs)."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import isparta

FIX = pathlib.Path(__file__).parent / "fixtures"


class Isparta(unittest.TestCase):
    def setUp(self):
        body = (FIX / "isparta.html").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.isparta.get", return_value=body):
            self.date, self.rows = isparta.fetch("2026-10-30")
        self.by = {r[0]: r for r in self.rows}

    def test_bulletin(self):
        self.assertEqual(self.date, "2026-10-30")
        self.assertEqual(len(self.rows), 55)  # 71 products, 16 without a price today
        self.assertEqual({r[5] for r in self.rows}, {None})
        self.assertNotIn("ACUR", self.by)

    def test_prices_and_units(self):
        self.assertEqual(self.by["BİBER (SİVRİ)"], ("BİBER (SİVRİ)", "KİLO", "60 TL", "75 TL", None, None))
        self.assertEqual(self.by["MAYDANOZ"][1], "BAĞ")
        self.assertEqual(self.by["ANANAS"][1], "ADET")


if __name__ == "__main__":
    unittest.main()
