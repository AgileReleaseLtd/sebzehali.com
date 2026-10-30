import pathlib
import unittest
from unittest import mock

from sebzehali.sources import amasya

FIX = pathlib.Path(__file__).parent / "fixtures"


def site(url, raw=False):
    """The listing (2026 lists only), the 27.10.2026 list's page and its PDF."""
    if url == amasya.URL:
        return (FIX / "amasya-list.html").read_text(encoding="utf-8")
    if url == "https://amasya.bel.tr/hal-fiyatlari/27102026-hal-fiyat-listesi":
        return (FIX / "amasya-item.html").read_text(encoding="utf-8")
    if url == "https://amasya.bel.tr/uploads/hal_fiyatlari/6ae090419ae99.pdf/6ae090419ae99.pdf" and raw:
        return b"%PDF"
    raise AssertionError(url)


class Amasya(unittest.TestCase):
    def setUp(self):
        amasya._pages.clear()

    def test_parse(self):
        rows = amasya.parse((FIX / "amasya.txt").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 55)  # unpriced rows are left out
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["DOMATES"][1:], ("KG", "68.00", "120.00", None, "sebze"))
        self.assertEqual(by["DEREOTU"][1], "BAĞ")
        self.assertEqual(by["MUZ İTHAL"][1:], ("KOLİ", "1000.00", "1400.00", None, "meyve"))
        self.assertEqual(by["ANANAS"][1], "ADET")

    def test_fetch_takes_the_newest_list_on_or_before_the_date(self):
        text = (FIX / "amasya.txt").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.amasya.get", side_effect=site), \
                mock.patch("sebzehali.sources.amasya.pdf_text", return_value=text):
            date, rows = amasya.fetch("2026-10-30")
            self.assertEqual((date, len(rows)), ("2026-10-27", 55))
            self.assertEqual(amasya.available_dates()[:3], ["2026-10-27", "2026-10-18", "2026-10-11"])
            self.assertIsNone(amasya.fetch("2026-01-01"))  # older than every list in the fixture


if __name__ == "__main__":
    unittest.main()
