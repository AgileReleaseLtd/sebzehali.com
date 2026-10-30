"""Tekirdağ: the list for 28 October 2026 and that day's Süleymanpaşa prices, saved 2026-10-30."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import tekirdag

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(url, **kw):
    name = "tekirdag.html" if "/hal_fiyat_liste_detay/" in url else "tekirdag-list.html"
    return (FIX / name).read_text(encoding="utf-8")


class Tekirdag(unittest.TestCase):
    def test_fetch(self):
        with mock.patch("sebzehali.sources.tekirdag.get", side_effect=serve) as get:
            date, rows = tekirdag.fetch("2026-10-28")
        self.assertEqual(get.call_args.args[0], "https://www.tekirdag.bel.tr/hal_fiyat_liste_detay/2250")
        self.assertEqual(date, "2026-10-28")
        self.assertEqual(len(rows), 38)
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {r[0]: r for r in rows}
        self.assertEqual(len(by), len(rows))
        self.assertEqual(by["BİBER SALÇALIK (KAPYA)"][1:6], ("Kg", "35 TL", "38 TL", None, "sebze"))  # max before min
        self.assertEqual(by["MAYDANOZ"][2:4], ("8 TL", "8 TL"))  # the conventional row, not iyi tarım (18 TL)
        self.assertEqual(by["HİNDİBA ENDİVYEN"][2:4], ("28 TL", "28 TL"))  # only listed as iyi tarım

    def test_a_list_for_another_day_is_not_used(self):
        with mock.patch("sebzehali.sources.tekirdag.get", side_effect=serve) as get:
            self.assertIsNone(tekirdag.fetch("2026-10-27"))
        self.assertEqual(get.call_count, 1)

    def test_name_repeated_in_brackets(self):
        self.assertEqual(tekirdag._name("FESLEĞEN(REYHAN) (FESLEĞEN(REYHAN))"), "FESLEĞEN(REYHAN)")
        self.assertEqual(tekirdag._name("ELMA STARKING (ELMA, STARKİNG)"), "ELMA STARKING")
        self.assertEqual(tekirdag._name("BİBER SALÇALIK (KAPYA) ()"), "BİBER SALÇALIK (KAPYA)")
        self.assertEqual(tekirdag._name("BİBER SİVRİ (KIL)"), "BİBER SİVRİ (KIL)")


if __name__ == "__main__":
    unittest.main()
