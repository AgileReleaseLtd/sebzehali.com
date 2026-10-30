"""Manisa Büyükşehir Belediyesi hal app: ?tar=DD.MM.YYYY (the page's own address for a date), any past
date back to 2020. Fruit and vegetables in one table.

The answer carries no bulletin date: a day without new prices, or a future one, shows the latest prices
(REPEATS_LAST). Past days can still be corrected: 28–30 October 2026's grape prices changed a day later.
"""

from ..normalize import slugify

from .html_table import tables
from .http import get

CITY = "manisa"
NAME = "Manisa"
PUBLISHER = "Manisa Büyükşehir Belediyesi"
URL = "https://www.manisa.bel.tr/apps/sebzemeyvehali/"
HISTORY = True
REPEATS_LAST = True
_CATEGORY = {"MEYVE": "meyve", "SEBZE": "sebze"}


def fetch(date):
    y, m, d = date.split("-")
    day = f"{d}.{m}.{y}"
    page = get(f"{URL}?tar={day}")
    if f'value="{day}"' not in page:
        raise RuntimeError(f"{URL} did not take the date {day}")
    rows = parse(page)
    return (date, rows) if rows else None


def parse(page):
    rows, seen = [], set()
    for t in tables(page):
        for cells in t:
            if len(cells) != 5 or cells[0] not in _CATEGORY:  # type, name, unit, lowest, highest
                continue
            unit = "Adet" if cells[2] == "ADT" else cells[2]
            key = (slugify(cells[1]), unit)
            if key in seen:
                continue  # some products are entered twice ("Yaban Mersini", "YABAN MERSİNİ")
            seen.add(key)
            rows.append((cells[1], unit, cells[3], cells[4], None, _CATEGORY[cells[0]]))
    return rows
