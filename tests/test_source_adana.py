"""Adana: the bulletin list and the 30 October 2026 bulletin, saved 2026-10-30."""

import datetime as dt
import pathlib
import unittest
from unittest import mock

from sebzehali.sources import adana

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(url, **kw):
    name = "adana.html" if "/hal-detay/" in url else "adana-list.html"
    return (FIX / name).read_text(encoding="utf-8")


class Adana(unittest.TestCase):
    def test_fetch(self):
        with mock.patch.dict(adana._pages, clear=True), mock.patch("sebzehali.sources.adana.get", side_effect=serve) as get:
            date, rows = adana.fetch("2026-10-30")
        self.assertEqual(get.call_args.args[0], "https://www.adana.bel.tr/tr/hal-detay/2758")
        self.assertEqual(date, "2026-10-30")
        self.assertEqual(len(rows), 83)
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["BİBER KAPYA"][1:5], ("KG", "50.00", "80.00", None))
        self.assertEqual(by["ANANAS"][5], "meyve")
        self.assertNotIn("KESTANE", by)  # 0.00 - 0.00: no price that day

    def test_find_jumps_through_a_list_with_missing_days(self):
        start = dt.date(2019, 9, 18)
        days = [start + dt.timedelta(n) for n in range(2600) if n % 37 not in (5, 6)]
        listing = [(d, str(i)) for i, d in enumerate(days, 1)][::-1]
        reads = []

        def page(off):
            reads.append(off)
            return listing[off:off + 5]

        with mock.patch.object(adana, "_list", page):
            for d, bulletin_id in listing[::50]:
                reads.clear()
                self.assertEqual(adana._find(d), bulletin_id)
                self.assertLessEqual(len(reads), 6)
            self.assertIsNone(adana._find(start + dt.timedelta(5)))
            self.assertIsNone(adana._find(dt.date(2031, 1, 1)))
            self.assertIsNone(adana._find(dt.date(2019, 1, 1)))


if __name__ == "__main__":
    unittest.main()
