"""Parse a saved copy of Çanakkale's hal page (fruit/veg and fish in one table)."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import canakkale

FIX = pathlib.Path(__file__).parent / "fixtures"


class Canakkale(unittest.TestCase):
    def setUp(self):
        body = (FIX / "canakkale.html").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.canakkale.get", return_value=body):
            self.date, self.rows = canakkale.fetch("2026-10-31")
        self.by = {r[0]: r for r in self.rows}

    def test_bulletin(self):
        self.assertEqual(self.date, "2026-10-30")
        self.assertEqual(len(self.rows), 112)
        self.assertEqual({r[5] for r in self.rows}, {None, "balik"})
        self.assertEqual(sum(r[5] == "balik" for r in self.rows), 23)  # 24 fish, one "---" (no price)

    def test_fruit_veg_names_and_prices(self):
        self.assertEqual(self.by["DOMATES (PEMBE)"], ("DOMATES (PEMBE)", None, "50", "150", None, None))
        self.assertEqual(self.by["ZENCEFİL"][2:4], ("347,39", "347,39"))
        self.assertIn("ARMUT", self.by)  # kind "DİĞER": just the product
        self.assertIn("MUZ YERLİ(ANAMUR)", self.by)  # the kind repeats the product: kind wins

    def test_fish(self):
        self.assertEqual(self.by["BARBUN"], ("BARBUN", "KG", "2.000,00TL", "3.500,00TL", None, "balik"))
        self.assertEqual(self.by["PALAMUT"][1], "TANE")
        self.assertNotIn("MEZGİT( YAĞLI)", self.by)


if __name__ == "__main__":
    unittest.main()
