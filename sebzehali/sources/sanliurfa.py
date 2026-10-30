"""Şanlıurfa Büyükşehir Belediyesi hal prices: a date search, 20 products a page, from 23 February 2026."""

import re

from .html_table import tables
from .http import get

CITY = "sanliurfa"
NAME = "Şanlıurfa"
PUBLISHER = "Şanlıurfa Büyükşehir Belediyesi"
URL = "https://halfiyatlari.sanliurfa.bel.tr/"
HISTORY = True
_CATEGORY = {"SEBZE": "sebze", "MEYVE": "meyve"}
_NAMES = {"K.Pancar": "Kırmızı Pancar"}  # "K." means something else in other cities' bulletins


def fetch(date):
    rows, n, total = [], 0, 1
    while len(rows) < total:
        n += 1
        page = get(f"{URL}?date_preset=ozel&start_date={date}&end_date={date}&search=1&page={n}")
        got = parse(page)
        if not got:
            break
        rows += got
        m = re.search(r"Toplam\s*<strong>\s*(\d+)", page)
        total = int(m.group(1)) if m else 0
    day = ".".join(reversed(date.split("-")))
    rows = [r for d, r in rows if d == day]
    return (date, rows) if rows else None


def parse(page):
    """(day, row) for each product; columns Ürün Adı, Ürün Türü, Birim, En Düşük, En Yüksek, Tarih."""
    out = []
    for t in tables(page):
        for cells in t:
            if len(cells) == 6 and re.search(r"\d", cells[3] + cells[4]):
                # A decimal point ("12.50"), so a comma could only group thousands.
                low, high = (c.replace(",", "") for c in cells[3:5])
                name = _NAMES.get(cells[0], cells[0])
                out.append((cells[5], (name, cells[2], low, high, None, _CATEGORY.get(cells[1].upper()))))
    return out
