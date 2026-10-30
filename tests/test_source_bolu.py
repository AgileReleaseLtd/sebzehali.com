import pathlib
import unittest
from unittest import mock

from sebzehali.sources import bolu

FIX = pathlib.Path(__file__).parent / "fixtures"


class Bolu(unittest.TestCase):
    def test_fetch(self):
        body = (FIX / "bolu.json").read_text(encoding="utf-8")
        with mock.patch("sebzehali.sources.bolu.get", return_value=body) as get:
            date, rows = bolu.fetch("2026-10-30")
        self.assertIn("&before=2026-10-31T00:00:00", get.call_args.args[0])
        self.assertEqual(date, "2026-10-23")
        self.assertEqual(len(rows), 49)  # unpriced rows are left out
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Domates"][1:], ("Kg", "60,00 TL", "80,00 TL", None, "sebze"))
        self.assertEqual(by["Kivi"][1:], ("Kg", "85,00 TL", "110,00 TL", None, "meyve"))
        for name in ("Taze Patates", "Kabak Sakız", "Yeşil Soğan", "Kuru Soğan", "Taze Sarımsak"):
            self.assertIn(name, by)  # "T. Patates", "S. Kabak", "Y. Soğan", "K.Soğan", "T. Sarımsak"

    def test_post_without_a_table(self):
        with mock.patch("sebzehali.sources.bolu.get", return_value='[{"content": {"rendered": ""}}]'):
            self.assertIsNone(bolu.fetch("2026-09-22"))
        with mock.patch("sebzehali.sources.bolu.get", return_value="[]"):
            self.assertIsNone(bolu.fetch("2017-01-01"))


if __name__ == "__main__":
    unittest.main()
