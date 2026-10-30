"""Gaziantep: the three pages of the 28 October 2026 prices, saved 2026-10-30 and trimmed to the table."""

import pathlib
import re
import unittest
from unittest import mock

from sebzehali.sources import gaziantep

FIX = pathlib.Path(__file__).parent / "fixtures"


def serve(url, **kw):
    n = re.search(r"page=(\d+)", url).group(1)
    return (FIX / f"gaziantep-{n}.html").read_text(encoding="utf-8")


class Gaziantep(unittest.TestCase):
    def test_fetch_reads_every_page(self):
        with mock.patch("sebzehali.sources.gaziantep.get", side_effect=serve) as get:
            date, rows = gaziantep.fetch("2026-10-28")
        self.assertEqual(get.call_count, 3)
        self.assertEqual(date, "2026-10-28")
        self.assertEqual(len(rows), 56)
        self.assertEqual({r[5] for r in rows}, {None})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["ACUR"][1:5], ("kilogram", "60,00 ₺", "85,00 ₺", None))

    def test_rows_dated_another_day_are_not_used(self):
        with mock.patch("sebzehali.sources.gaziantep.get", side_effect=serve):
            self.assertIsNone(gaziantep.fetch("2026-10-27"))


if __name__ == "__main__":
    unittest.main()
