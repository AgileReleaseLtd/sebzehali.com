"""Tokat: the API's answer for 29 October 2026, a holiday, which is the 28 October bulletin; saved
2026-10-30."""

import json
import pathlib
import unittest
from unittest import mock

from sebzehali.sources import tokat

FIX = pathlib.Path(__file__).parent / "fixtures"
SAVED = (FIX / "tokat.json").read_text(encoding="utf-8")


class Tokat(unittest.TestCase):
    def test_fetch(self):
        with mock.patch("sebzehali.sources.tokat.get", return_value=SAVED) as get:
            date, rows = tokat.fetch("2026-10-29")
        sent = json.loads(get.call_args.kwargs["data"])
        self.assertEqual(sent, {"limit": 100, "offset": 0, "date": "2026-10-29"})
        self.assertEqual(get.call_count, 1)
        self.assertEqual(date, "2026-10-28")
        self.assertEqual(len(rows), 37)
        self.assertEqual({r[5] for r in rows}, {"sebze", "meyve"})
        by = {r[0]: r for r in rows}
        self.assertEqual(by["DOMATES"], ("DOMATES", "kg", "26.00", "125.00", None, "sebze"))
        self.assertEqual(by["DEREOTU"][1:6], ("demet", "7.00", "20.00", None, "sebze"))  # filed as "yesil"
        self.assertEqual(by["ELMA"][5], "meyve")

    def test_pages_through_long_lists(self):
        doc = json.loads(SAVED)
        first, second = dict(doc, data=doc["data"][:30]), dict(doc, data=doc["data"][30:])
        bodies = [json.dumps(first), json.dumps(second)]
        with mock.patch("sebzehali.sources.tokat.get", side_effect=bodies) as get:
            date, rows = tokat.fetch("2026-10-29")
        self.assertEqual(json.loads(get.call_args.kwargs["data"])["offset"], 30)
        self.assertEqual(len(rows), 37)

    def test_no_bulletin(self):
        empty = json.dumps({"success": True, "data": [], "pagination": {"total": 0}})
        with mock.patch("sebzehali.sources.tokat.get", return_value=empty):
            self.assertIsNone(tokat.fetch("2026-01-05"))


if __name__ == "__main__":
    unittest.main()
