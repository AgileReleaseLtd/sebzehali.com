"""Bursa Büyükşehir Belediyesi hal page, fruit/veg and fish tabs; ?tarih=YYYY-MM-DD gives past bulletins
(seen back to 2020), or the last one before a day without a bulletin."""

import re

from .html_table import tables
from .http import get

CITY = "bursa"
NAME = "Bursa"
PUBLISHER = "Bursa Büyükşehir Belediyesi"
URL = "https://www.bursa.bel.tr/hal_fiyatlari"
HISTORY = True

# Tab order on the page: Meyve, Sebze, İthal, then six seafood tabs.
_TAB_CATEGORY = ["meyve", "sebze", "ithal", "balik", "balik", "balik", "balik", "balik", "balik"]


def fetch(date):
    page = get(f"{URL}?tarih={date}")
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s*Tarihli", page)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    rows = []
    for i, t in enumerate(tables(page)):
        cat = _TAB_CATEGORY[i] if i < len(_TAB_CATEGORY) else "balik"
        for cells in t:
            if len(cells) < 3 or cells[0].upper().startswith("ÜRÜN"):
                continue
            prices = re.findall(r"[\d.,]+", cells[2])
            if not prices:
                continue
            low, high = prices[0], prices[-1]
            rows.append((cells[0], cells[1].strip("()"), low, high, None, cat))
    return (bulletin, rows) if rows else None
