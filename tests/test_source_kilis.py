import pathlib
import unittest
from unittest import mock

from sebzehali.sources import kilis

FIX = pathlib.Path(__file__).parent / "fixtures"
FILES = "https://www.kilis.bel.tr/wp-content/uploads/2025/04/"


def site(url, raw=False):
    """The post page; the PDF it embeds; every other file is missing."""
    if url == kilis.URL:
        return (FIX / "kilis-post.html").read_text(encoding="utf-8")
    if url == FILES + "30.10.2026-1.pdf":
        return b"%PDF"
    raise RuntimeError(f"GET {url} failed: HTTP Error 404: Not Found")


class Kilis(unittest.TestCase):
    def setUp(self):
        kilis._embedded.clear()

    def test_parse(self):
        date, rows = kilis.parse((FIX / "kilis.txt").read_text(encoding="utf-8"))
        self.assertEqual(date, "2026-10-30")
        self.assertEqual(len(rows), 50)
        self.assertEqual({r[5] for r in rows}, {None})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["DOMATES (TARLA)"][1:4], ("KG", "30,00", "40,00"))  # AS. (asgari) is the minimum
        self.assertEqual(by["MAYDANOZ"][1:4], ("DEMET", 7.0, 8.0))  # 70-80 for 10 bunches
        self.assertEqual(by["KIVIRCIK"][1:4], ("ADET", 31.25, 37.5))  # 250-300 for 8 heads
        self.assertEqual(by["HAVUÇ"][1:4], ("TORBA", "250,00", "300,00"))

    def test_no_date_line(self):
        date, rows = kilis.parse("DOMATES     30,00   40,00   KG")
        self.assertEqual((date, rows), (None, [("DOMATES", "KG", "30,00", "40,00", None, None)]))

    def test_fetch_uses_the_embedded_file_and_guesses_the_others(self):
        text = (FIX / "kilis.txt").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.kilis.get", side_effect=site) as get, \
                mock.patch("sebzehali.sources.kilis.pdf_text", return_value=text):
            date, rows = kilis.fetch("2026-10-30")
            self.assertEqual((date, len(rows)), ("2026-10-30", 50))
            self.assertIsNone(kilis.fetch("2026-10-29"))  # a holiday: no file
        self.assertEqual([c.args[0] for c in get.call_args_list],
                         [kilis.URL, FILES + "30.10.2026-1.pdf", FILES + "29.10.2026.pdf"])

    def test_other_errors_are_not_a_missing_list(self):
        post = (FIX / "kilis-post.html").read_text(encoding="utf-8")
        timeout = RuntimeError("GET x failed: timed out")
        with mock.patch("sebzehali.sources.kilis.get", side_effect=[post, timeout]):
            self.assertRaises(RuntimeError, kilis.fetch, "2026-10-30")


if __name__ == "__main__":
    unittest.main()
