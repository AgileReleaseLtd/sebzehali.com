"""Parse a saved copy of Kütahya's hal page."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import kutahya

FIX = pathlib.Path(__file__).parent / "fixtures"


class Kutahya(unittest.TestCase):
    def setUp(self):
        body = (FIX / "kutahya.html").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.kutahya.get", return_value=body):
            self.date, self.rows = kutahya.fetch("2026-10-30")
        self.by = {r[0]: r for r in self.rows}

    def test_bulletin(self):
        self.assertEqual(self.date, "2026-10-27")
        self.assertEqual(len(self.rows), 75)  # products without a price today are left out
        self.assertEqual({r[5] for r in self.rows}, {None, "ithal"})
        self.assertEqual(self.by["MUZ (İTHAL)"][5], "ithal")

    def test_kind_becomes_variety_or_unit(self):
        self.assertEqual(self.by["DOMATES (Sofralık)"], ("DOMATES (Sofralık)", None, "30 ₺", "60 ₺", "₺", None))
        self.assertIsNone(self.by["ARMUT"][1])  # kind "Normal": no unit given
        self.assertEqual(self.by["MAYDANOZ"][1], "Bağ")
        self.assertEqual(self.by["AVOKADO"][1], "Adet")
        self.assertEqual(self.by["SEMİZ OTU"][1], "Kg")
        self.assertEqual(self.by["SOĞAN (Taze)"][1], "Kg")

    def test_single_digit_date(self):
        page = (FIX / "kutahya.html").read_text(encoding="utf-8").replace("27.10.2026", "2.9.2026")
        with mock.patch("sebzehali.sources.kutahya.get", return_value=page):
            self.assertEqual(kutahya.fetch("2026-09-02")[0], "2026-09-02")


if __name__ == "__main__":
    unittest.main()
