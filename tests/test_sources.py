"""Parse saved copies of each city's page, so a layout change shows up as a failing test."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import bursa, izmir, konya

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(name):
    body = (FIX / name).read_text(encoding="utf-8")
    return mock.patch(f"sebzehali.sources.{name.split('.')[0]}.get", return_value=body)


class Sources(unittest.TestCase):
    def test_izmir(self):
        bodies = [(FIX / n).read_text(encoding="utf-8") for n in ("izmir.json", "izmir-balik.json")]
        with mock.patch("sebzehali.sources.izmir.get", side_effect=bodies):
            date, rows = izmir.fetch("2026-10-09")
        self.assertEqual(date, "2026-10-09")
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve", "ithal", "balik"})
        self.assertGreater(len([r for r in rows if r[5] != "balik"]), 50)
        fish = {r[0]: r for r in rows if r[5] == "balik"}
        self.assertEqual(len(fish), 71)
        self.assertEqual(fish["AHTAPOT(DONUK)"][1:5], ("KG", 500, 500, 500))

    def test_izmir_no_bulletin(self):
        with mock.patch("sebzehali.sources.izmir.get", return_value=""):
            self.assertIsNone(izmir.fetch("2026-10-29"))

    def test_izmir_fish_alone_is_not_a_bulletin(self):
        fish = (FIX / "izmir-balik.json").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.izmir.get", side_effect=["", fish]):
            self.assertIsNone(izmir.fetch("2026-10-11"))

    def test_bursa(self):
        with serve("bursa.html"):
            date, rows = bursa.fetch("2026-10-10")
        self.assertEqual(date, "2026-10-09")
        cats = {r[5] for r in rows}
        self.assertTrue({"sebze", "meyve", "balik"} <= cats)
        tomato = [r for r in rows if r[0] == "Domates"][0]
        self.assertEqual((tomato[2], tomato[3]), ("10,00", "50,00"))

    def test_konya(self):
        with serve("konya.html"):
            date, rows = konya.fetch("2026-10-10")
        self.assertEqual(date, "2026-10-08")
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        self.assertGreater(len(rows), 100)


if __name__ == "__main__":
    unittest.main()


class PdfAndFormSources(unittest.TestCase):
    def test_antalya_two_column_pdf(self):
        from sebzehali.sources import antalya
        rows = antalya.parse((FIX / "antalya.txt").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 88)
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Domates"][2:4], ("30,00", "70,00"))
        self.assertEqual(by["Domates"][5], "sebze")
        self.assertEqual(by["Elma (Golden)"][5], "meyve")
        self.assertEqual(by["Ahududu"][5], "ithal")
        self.assertEqual(by["Ahududu"][2], "1.200,00")

    def test_mersin_keeps_central_conventional_rows_once(self):
        from sebzehali.sources import mersin
        rows = mersin.parse((FIX / "mersin-sebze.html").read_text(encoding="utf-8"), "sebze")
        names = [r[0] for r in rows]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("ACUR", names)
        acur = rows[names.index("ACUR")]
        self.assertEqual(acur[1:5], ("KİLOGRAM", "7 TL", "31 TL", "12,19 TL"))

    def test_mersin_branches_are_markets_of_their_own(self):
        from sebzehali.sources import mersin
        page = (FIX / "mersin-sebze.html").read_text(encoding="utf-8")
        self.assertEqual(len(mersin.parse(page, "sebze", "TARSUS")), 23)
        self.assertEqual(len(mersin.parse(page, "sebze", "ERDEMLİ")), 3)
        self.assertEqual([b.CITY for b in mersin.BRANCHES], ["tarsus", "erdemli", "anamur"])
        with mock.patch("sebzehali.sources.mersin.get", return_value=page):
            mersin._pages.cache_clear()
            date, rows = mersin.BRANCHES[0].fetch("2026-10-12")
            mersin._pages.cache_clear()
        self.assertEqual(date, "2026-10-12")
        self.assertEqual(len(rows), 46)  # the same page stands in for both categories here
