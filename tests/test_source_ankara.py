"""Ankara: the four lists (vegetables, fruit, imports, fish) asked for 29 October 2026, a holiday, so they
hold the 28 October bulletin; tables saved 2026-10-30."""

import pathlib
import unittest
import urllib.parse
from unittest import mock

from sebzehali.sources import ankara

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(lists):
    def get(url, data=None, **kw):
        return lists[urllib.parse.parse_qs(data.decode())["type"][0]]
    return mock.patch("sebzehali.sources.ankara.get", side_effect=get)


def saved():
    return {kind: (FIX / f"ankara-{kind}.html").read_text(encoding="utf-8") for kind in ankara._LISTS}


class Ankara(unittest.TestCase):
    def test_fetch(self):
        with serve(saved()) as get:
            date, rows = ankara.fetch("2026-10-29")
        self.assertEqual(get.call_args.kwargs["data"], b"date=29.10.2026&type=fish")
        self.assertEqual(date, "2026-10-28")
        self.assertEqual(len(rows), 146)
        self.assertEqual({r[5] for r in rows}, {None, "ithal", "balik"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Domates (Ayaş)"], ("Domates (Ayaş)", "kg", 40.0, 70.0, None, None))
        self.assertEqual(by["Ananas"][1:4], ("adet", 95.0, 150.0))
        self.assertEqual(by["Maydanoz (70-100 gr)"][1], "bağ")
        # names that carried the unit or a stray bracket ("Patates kg)", "Lahana (Beyaz) (kg)", "Pazı)")
        self.assertEqual(by["Patates"][1:4], ("kg", 23.0, 30.0))
        self.assertIn("Lahana (Beyaz)", by)
        self.assertIn("Pazı", by)

    def test_fish_crate_prices_become_per_kg(self):
        by = {r[0]: r for r in (row for _, row in ankara.parse(saved()["fish"], "balik"))}
        self.assertEqual(by["AKYA"][1:4], ("kg", 300.0, 320.0))  # Kasa (10 Kğ): 3.000,00 - 3.200,00
        self.assertEqual(by["SARDALYA"][1:4], ("kg", 58.33, 100.0))  # Kasa (12 Kg): 700,00 - 1.200,00
        self.assertEqual(by["BARBUN"][1:4], ("kg", 450.0, 650.0))  # Kilo (1 Kğ)

    def test_lists_from_another_day_are_left_out(self):
        lists = saved()
        lists["fish"] = lists["fish"].replace("28.10.2026", "27.10.2026")  # no fish that day
        with serve(lists):
            date, rows = ankara.fetch("2026-10-29")
        self.assertEqual(date, "2026-10-28")
        self.assertEqual(len(rows), 96)
        self.assertNotIn("balik", {r[5] for r in rows})

        lists = saved()
        lists["fruit"] = lists["fruit"].replace("28.10.2026", "27.10.2026")  # fruit not entered yet
        with serve(lists):
            date, rows = ankara.fetch("2026-10-29")
        self.assertEqual(date, "2026-10-27")
        self.assertEqual(len(rows), 36)


if __name__ == "__main__":
    unittest.main()
