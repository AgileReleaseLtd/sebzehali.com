"""Şanlıurfa: the two pages of the 28 October 2026 prices, saved 2026-10-30."""

import pathlib
import re
import unittest
from unittest import mock

from sebzehali.normalize import normalize_row
from sebzehali.sources import sanliurfa

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(url, **kw):
    n = re.search(r"page=(\d+)", url).group(1)
    return (FIX / f"sanliurfa-{n}.html").read_text(encoding="utf-8")


class Sanliurfa(unittest.TestCase):
    def test_fetch_reads_every_page(self):
        with mock.patch("sebzehali.sources.sanliurfa.get", side_effect=serve) as get:
            date, rows = sanliurfa.fetch("2026-10-28")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(date, "2026-10-28")
        self.assertEqual(len(rows), 40)
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["Armut (Deveci)"][1:6], ("kg", "25.00", "50.00", None, "meyve"))
        strawberry = normalize_row(*by["Çilek"])  # a decimal point, not a thousands separator
        self.assertEqual((strawberry["min"], strawberry["max"]), (150.0, 170.0))


if __name__ == "__main__":
    unittest.main()
