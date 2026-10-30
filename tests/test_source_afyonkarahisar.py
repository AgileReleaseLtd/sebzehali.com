import pathlib
import unittest
from unittest import mock

from sebzehali.sources import afyonkarahisar

FIX = pathlib.Path(__file__).parent / "fixtures"
MONTH = (afyonkarahisar.URL + "/2026-yili-sebze-ve-meyve-toptan-fiyat-listesi/"
         "ekim-ayi-gunluk-sebze-ve-meyve-toptan-fiyat-listesi")


def site(url, raw=False):
    """The October listing (first page), one day page and its PDF; anything else is an empty page."""
    if url == MONTH:
        return (FIX / "afyonkarahisar-ekim.html").read_text(encoding="utf-8")
    if url.startswith(MONTH + "/"):
        return (FIX / "afyonkarahisar-gun.html").read_text(encoding="utf-8")
    return b"%PDF" if raw else ""


class Afyonkarahisar(unittest.TestCase):
    def setUp(self):
        afyonkarahisar._listings.clear()

    def test_parse(self):
        date, rows = afyonkarahisar.parse((FIX / "afyonkarahisar.txt").read_text(encoding="utf-8"))
        self.assertEqual(date, "2026-10-30")
        self.assertEqual(len(rows), 63)  # rows priced "*" are left out
        self.assertEqual({r[5] for r in rows}, {None})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["DOMATES SALKIM"][1:4], ("Kg", "75,00", "120,00"))
        self.assertEqual(by["BİBER ÇARLİSTON"][2:4], ("60,00", "120,00"))
        self.assertIn("KARNABAHAR", by)  # written "K.BAHAR"
        self.assertIn("LOLOROSSO", by)  # no kind ("*") but priced
        self.assertNotIn("ŞEFTALİ", by)

    def test_fetch_finds_the_day_page_in_the_month_listing(self):
        text = (FIX / "afyonkarahisar.txt").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.afyonkarahisar.get", side_effect=site) as get, \
                mock.patch("sebzehali.sources.afyonkarahisar.pdf_text", return_value=text):
            date, rows = afyonkarahisar.fetch("2026-10-24")
        urls = [c.args[0] for c in get.call_args_list]
        self.assertEqual(urls[1], MONTH + "/24-10-2026-sebze-ve-meyve-gunluk-fiyat-listesi-dosya-file")
        self.assertTrue(urls[2].endswith("-30.10.2026.pdf"))
        self.assertEqual((date, len(rows)), ("2026-10-30", 63))  # the PDF's own date wins

    def test_day_without_a_list(self):
        with mock.patch("sebzehali.sources.afyonkarahisar.get", side_effect=site) as get:
            self.assertIsNone(afyonkarahisar.fetch("2026-10-25"))  # a Sunday: on neither listing page
            self.assertIsNone(afyonkarahisar.fetch("2026-10-18"))
            self.assertIsNone(afyonkarahisar.fetch("2025-12-31"))  # before the site's first list
        self.assertEqual([c.args[0] for c in get.call_args_list], [MONTH, MONTH + "?page=2"])


if __name__ == "__main__":
    unittest.main()
