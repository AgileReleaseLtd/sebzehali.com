"""Manisa: the hal app's page for 29 October 2026 (form state blanked), parsed without the network."""

import pathlib
import unittest
from unittest import mock

from sebzehali.sources import manisa

FIX = pathlib.Path(__file__).parent / "fixtures"


class Manisa(unittest.TestCase):
    def setUp(self):
        self.page = (FIX / "manisa.html").read_text(encoding="utf-8")

    def test_fetch(self):
        with mock.patch("sebzehali.sources.manisa.get", return_value=self.page) as get:
            date, rows = manisa.fetch("2026-10-29")
        get.assert_called_once_with(manisa.URL + "?tar=29.10.2026")
        self.assertEqual(date, "2026-10-29")
        self.assertEqual(len(rows), 130)  # 131 on the page; "Yaban Mersini" is entered twice
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {(r[0], r[1]): r for r in rows}
        self.assertEqual(by[("DOMATES PEMBE", "KG")][2:6], ("30,00 TL", "40,00 TL", None, "sebze"))
        self.assertEqual(by[("ANANAS", "Adet")][2:4], ("110,00 TL", "120,00 TL"))  # "ADT" on the page

    def test_page_for_another_date_is_refused(self):
        with mock.patch("sebzehali.sources.manisa.get", return_value=self.page):
            with self.assertRaises(RuntimeError):
                manisa.fetch("2026-10-28")


if __name__ == "__main__":
    unittest.main()
