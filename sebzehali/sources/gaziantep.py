"""Gaziantep Büyükşehir Belediyesi "Hal Rayiç Fiyatları": ?date=YYYY-MM-DD, 20 products a page, back to
2015 with gaps. The bulletin doesn't say which products are fruit, so normalize guesses.

The server doesn't send its intermediate certificate; the bundled Sectigo one completes the chain.
"""

import re

from .html_table import tables
from .http import get, with_intermediate

CITY = "gaziantep"
NAME = "Gaziantep"
PUBLISHER = "Gaziantep Büyükşehir Belediyesi"
URL = "https://www.gaziantep.bel.tr/tr/hal-rayic"
HISTORY = True
_TLS = with_intermediate("sectigo-dv-r36.pem")
_PAGES = re.compile(r"Sayfa:\s*<span[^>]*>\s*\d+\s*</span>\s*/\s*<span[^>]*>\s*(\d+)")


def fetch(date):
    rows, n, pages = [], 0, 1
    while n < pages:
        n += 1
        page = get(f"{URL}?date={date}&page={n}", context=_TLS)
        m = _PAGES.search(page)
        pages = int(m.group(1)) if m else 1
        rows += parse(page)
    day = ".".join(reversed(date.split("-")))
    rows = [r for d, r in rows if d == day]
    return (date, rows) if rows else None


def parse(page):
    """(day, row) for each product; columns Ürün Adı, Az. Fiyat (lowest), As. Fiyat, Birim, Tarih."""
    out = []
    for t in tables(page):
        for cells in t:
            if len(cells) == 5 and re.search(r"\d", cells[1] + cells[2]):
                out.append((cells[4], (cells[0], cells[3], cells[1], cells[2], None, None)))
    return out
