"""Balıkesir: the price lists for 22 October 2026 (fruit and vegetable halls, fish hall), parsed without
the network."""

import pathlib
import unittest
import urllib.parse
from unittest import mock

from sebzehali.sources import balikesir

FIX = pathlib.Path(__file__).parent / "fixtures"
PAGE = '<input name="__RequestVerificationToken" type="hidden" value="page-token" />'


class Balikesir(unittest.TestCase):
    def setUp(self):
        balikesir._visit.clear()
        balikesir._cache.clear()
        self.lists = [(FIX / n).read_text(encoding="utf-8") for n in ("balikesir.html", "balikesir-balik.html")]

    def test_markets_share_one_download(self):
        with mock.patch("sebzehali.sources.balikesir.get", side_effect=[PAGE, *self.lists]) as get:
            date, rows = balikesir.fetch("2026-10-22")
            bandirma = balikesir.BRANCHES[0].fetch("2026-10-22")
        self.assertEqual(get.call_count, 3)
        opener = get.call_args_list[0].kwargs["opener"]
        for call, kind in zip(get.call_args_list[1:], ("1", "2")):
            self.assertIs(call.kwargs["opener"], opener)
            self.assertEqual(call.kwargs["headers"]["__RequestVerificationToken"], "page-token")
            posted = urllib.parse.parse_qs(call.kwargs["data"].decode(), keep_blank_values=True)
            self.assertEqual((posted["BasT"], posted["BitT"], posted["HalAd"], posted["TurAd"]),
                             (["22.10.2026"], ["22.10.2026"], [""], [kind]))

        self.assertEqual(date, "2026-10-22")
        self.assertEqual(len(rows), 121)
        self.assertEqual({r[5] for r in rows}, {None})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Domates, Pembe"][1:5], ("Kilogram", "70,00", "90,00", None))

        self.assertEqual(bandirma[0], "2026-10-22")
        self.assertEqual(len(bandirma[1]), 71)
        by = {(r[0], r[5]): r for r in bandirma[1]}
        self.assertEqual(len([r for r in bandirma[1] if r[5] == "balik"]), 10)
        self.assertEqual(by[("Domates, Pembe", None)][2:4], ("60,00", "70,00"))
        self.assertEqual(by[("Palamut", "balik")][1:4], ("Çift", "100,00", "100,00"))

    def test_prices_hold_only_on_their_own_dates(self):
        self.assertEqual(balikesir.parse(self.lists[0], "2026-10-23", None), [])


if __name__ == "__main__":
    unittest.main()
