"""Kayseri: the hal form's answer for 30 October 2026 (form state blanked), parsed without the network."""

import pathlib
import unittest
import urllib.parse
from unittest import mock

from sebzehali.sources import kayseri

FIX = pathlib.Path(__file__).parent / "fixtures"


class Kayseri(unittest.TestCase):
    def setUp(self):
        kayseri._form.clear()
        self.page = (FIX / "kayseri.html").read_text(encoding="utf-8")

    def test_fetch(self):
        with mock.patch("sebzehali.sources.kayseri.get", return_value=self.page) as get:
            date, rows = kayseri.fetch("2026-10-30")
        self.assertEqual(date, "2026-10-30")
        self.assertEqual(len(rows), 132)
        self.assertEqual({r[5] for r in rows}, {None})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Domates"][1:5], ("Kg", "50 ₺", "90 ₺", None))  # the page lists the highest first
        self.assertEqual(by["Muz İthal (18kg)"][1:4], ("Koli", "2200 ₺", "2400 ₺"))
        posted = urllib.parse.parse_qs(get.call_args.kwargs["data"].decode(), keep_blank_values=True)
        self.assertEqual(posted["ctl00$contentHolder$HalFiyatlariDate"], ["30.10.2026"])
        self.assertIn("__EVENTVALIDATION", posted)

    def test_rejected_form_state_is_fetched_again_once(self):
        error = "<html><body>Hata</body></html>"
        with mock.patch("sebzehali.sources.kayseri.get", side_effect=[self.page, error, self.page, self.page]) as get:
            date, rows = kayseri.fetch("2026-10-30")
        self.assertEqual(get.call_count, 4)
        self.assertEqual(len(rows), 132)
        with mock.patch("sebzehali.sources.kayseri.get", side_effect=[error] * 4):
            kayseri._form.clear()
            with self.assertRaises(RuntimeError):
                kayseri.fetch("2026-10-30")


if __name__ == "__main__":
    unittest.main()
