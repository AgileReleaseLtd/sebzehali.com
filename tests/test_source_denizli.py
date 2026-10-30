"""Parse a saved copy of Denizli's hal page."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import denizli

FIX = pathlib.Path(__file__).parent / "fixtures"


class Denizli(unittest.TestCase):
    def setUp(self):
        body = (FIX / "denizli.html").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.denizli.get", return_value=body):
            self.date, self.rows = denizli.fetch("2026-10-30")
        self.by = {r[0]: r for r in self.rows}

    def test_bulletin(self):
        self.assertEqual(self.date, "2026-10-28")
        self.assertEqual(len(self.rows), 90)
        self.assertEqual({r[5] for r in self.rows}, {None, "ithal"})
        self.assertEqual(self.by["KİVİ İTHAL"][5], "ithal")

    def test_asgari_ekstra_orta_are_min_max_avg(self):
        self.assertEqual(self.by["PORTAKAL"], ("PORTAKAL", None, "25,00 TL", "80,00 TL", "50,00 TL", None))

    def test_unit_taken_out_of_the_name(self):
        self.assertEqual(self.by["LİMON YENİ"][1], "KG")
        self.assertEqual(self.by["ÇİLEK"][1], "KĞ")
        self.assertEqual(self.by["SOĞAN TAZE"][1], "BAĞ")

    def test_abbreviations_spelt_out(self):
        self.assertIn("KARNABAHAR", self.by)
        self.assertIn("MARUL KIVIRCIK", self.by)
        self.assertIn("ERİK ANJELİKA MÜRDÜM", self.by)
        self.assertNotIn("K.BAHAR", self.by)


if __name__ == "__main__":
    unittest.main()
