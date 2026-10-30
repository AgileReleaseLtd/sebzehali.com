"""Trabzon: the page's bulletin list and the 26 October 2026 bulletin (id 1159), saved 2026-10-30."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import trabzon

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(url, **kw):
    name = "trabzon.html" if "halBildirimId=" in url else "trabzon-dates.html"
    return (FIX / name).read_text(encoding="utf-8")


class Trabzon(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.dict(trabzon._ids, clear=True),
                   mock.patch("sebzehali.sources.trabzon.get", side_effect=serve)]
        self.get = [p.start() for p in patches][1]
        for p in patches:
            self.addCleanup(p.stop)

    def test_dates(self):
        dates = trabzon.available_dates()
        self.assertEqual(len(dates), 1033)
        self.assertEqual((dates[0], dates[-1]), ("2026-10-26", "2019-08-07"))
        self.assertEqual(trabzon._ids["2026-10-26"], "1159")

    def test_fetch_takes_the_newest_bulletin_on_or_before_the_day(self):
        date, rows = trabzon.fetch("2026-10-29")
        self.assertEqual(self.get.call_args.args[0], trabzon._TABLE.format("1159"))
        self.assertEqual(date, "2026-10-26")
        self.assertEqual(len(rows), 79)
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve", "ithal"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Domates"], ("Domates", "kg", "23,00₺", "75,00₺", None, "sebze"))
        self.assertEqual(by["Ananas"][5], "meyve")
        self.assertEqual(by["Dereotu"][1:4], ("Bağ", "18,00₺", "45,00₺"))
        self.assertEqual(by["Mango"][1:6], ("Adet", "66,67₺", "150,00₺", None, "ithal"))
        self.assertEqual(by["Muz İthal"][1:6], ("Koli", "1200,00₺", "2600,00₺", None, "ithal"))
        self.assertEqual(by["Sarımsak (Yerli)"][1], "kg")

    def test_before_the_first_bulletin(self):
        self.assertIsNone(trabzon.fetch("2019-08-01"))


if __name__ == "__main__":
    unittest.main()
