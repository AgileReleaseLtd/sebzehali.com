"""Konya Büyükşehir Belediyesi hal page: ?tarih=YYYY-MM-DD, about 2,000 past bulletins."""

import re

from .html_table import tables
from .http import get

CITY = "konya"
NAME = "Konya"
PUBLISHER = "Konya Büyükşehir Belediyesi"
URL = "https://www.konya.bel.tr/hal-fiyatlari"
HISTORY = True


_dates = []


def available_dates():
    if not _dates:
        _dates.extend(_load_dates())
    return _dates


def _load_dates():
    return sorted(set(re.findall(r'option value="(\d{4}-\d{2}-\d{2})"', get(URL))), reverse=True)


def fetch(date):
    # Asking for a day with no bulletin returns HTTP 500, so use the newest bulletin on or before it.
    earlier = [d for d in available_dates() if d <= date]
    if not earlier:
        return None
    page = get(f"{URL}?tarih={earlier[0]}")
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s*Tarihli", page)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    rows = []
    for t in tables(page):
        if not t:
            continue
        title = t[0][0].upper() if len(t[0]) == 1 else ""
        cat = "sebze" if "SEBZE" in title else "meyve" if "MEYVE" in title else None
        if cat is None:
            continue  # the third table repeats both lists without a category
        for cells in t:
            if len(cells) < 4 or cells[0].lower().startswith("ürün"):
                continue
            rows.append((cells[0], cells[1], cells[2], cells[3], None, cat))
    return (bulletin, rows) if rows else None
