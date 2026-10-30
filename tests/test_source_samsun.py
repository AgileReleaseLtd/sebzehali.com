"""Samsun: the price table for 19 October 2026, with the fish hall's list for that week, saved
2026-10-30."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import samsun

FIX = pathlib.Path(__file__).parent / "fixtures"
SAVED = (FIX / "samsun.json").read_text(encoding="utf-8")


def serve(body=SAVED):
    samsun._day.cache_clear()
    return mock.patch("sebzehali.sources.samsun.get", return_value=body)


class Samsun(unittest.TestCase):
    def tearDown(self):
        samsun._day.cache_clear()

    def test_central_market_and_fish_hall(self):
        with serve() as get:
            date, rows = samsun.fetch("2026-10-19")
        get.assert_called_once_with(f"{samsun.API}?tarih=2026-10-19&el_tarih=2026-10-19")
        self.assertEqual(date, "2026-10-19")
        self.assertEqual(len(rows), 93)
        self.assertEqual({r[5] for r in rows}, {None, "balik"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["DOMATES"], ("DOMATES", "kg", 12, 175, None, None))
        self.assertEqual(by["Hamsi"], ("Hamsi", "kg", 75, 175, None, "balik"))
        self.assertEqual(sum(r[5] == "balik" for r in rows), 16)

    def test_branches_share_one_download(self):
        with serve() as get:
            got = {b.CITY: b.fetch("2026-10-19") for b in samsun.BRANCHES}
            samsun.fetch("2026-10-19")
        self.assertEqual(get.call_count, 1)
        self.assertEqual([b.NAME for b in samsun.BRANCHES], ["Bafra", "Çarşamba"])
        bafra_date, bafra = got["bafra"]
        self.assertEqual(bafra_date, "2026-10-19")
        self.assertEqual(len(bafra), 33)
        self.assertEqual(len(got["carsamba"][1]), 30)
        self.assertEqual({r[5] for r in bafra}, {None})
        self.assertIn(("DOMATES", "kg", 15, 45, None, None), bafra)
        self.assertIn(("DOMATES", "kg", 13, 50, None, None), got["carsamba"][1])

    def test_fish_list_only_on_the_day_it_was_updated(self):
        later = SAVED.replace('"tarih":"2026-10-19"', '"tarih":"2026-10-20"')
        with serve(later):
            date, rows = samsun.fetch("2026-10-20")
        self.assertEqual(date, "2026-10-20")
        self.assertNotIn("balik", {r[5] for r in rows})

    def test_today_waits_until_the_figures_are_settled(self):
        today = SAVED.replace('"bugun":"2026-10-30"', '"bugun":"2026-10-19"')
        with serve(today), mock.patch.object(samsun, "_dates", []):
            self.assertIsNone(samsun.fetch("2026-10-19"))
            self.assertEqual(samsun.available_dates()[0], "2026-10-18")


if __name__ == "__main__":
    unittest.main()
