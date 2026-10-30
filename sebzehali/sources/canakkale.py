"""Çanakkale Belediyesi hal page: the latest bulletin only, fruit/veg and the fish market.

One table pasted from Excel: a title row and a date row, then the fruit/veg list (product, kind,
lowest, highest; no unit, no category), then the same for the fish market (with a unit column).
"""

import re

from ..normalize import slugify

from .html_table import tables
from .http import get

CITY = "canakkale"
NAME = "Çanakkale"
PUBLISHER = "Çanakkale Belediyesi"
URL = "https://www.canakkale.bel.tr/tr/sayfa/1481-hal-fiyat-listesi"
HISTORY = False


def fetch(date):
    bulletin, rows, fish = None, [], False
    for t in tables(get(URL)):
        for cells in t:
            if len(cells) < 4 or not re.search(r"\d", cells[2] + cells[3]):
                # Title, date and header rows, and "---" for a fish with no price today.
                m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", cells[0])
                if m and not bulletin:  # the fish list repeats the date; the fruit/veg one comes first
                    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
                fish = fish or "BALIK" in cells[0].upper()
                continue
            if fish:
                rows.append((cells[0], cells[1], cells[2], cells[3], None, "balik"))
                continue
            name = _name(cells[0], cells[1])
            unit = re.search(r"\b(ADET|BAĞ)\b", name, re.I)
            cat = "ithal" if "ithal" in slugify(name).split("-") else None
            rows.append((name, unit.group(1) if unit else None, cells[2], cells[3], None, cat))
    return (bulletin, rows) if bulletin and rows else None


def _name(product, kind):
    p, k = slugify(product).replace("-", ""), slugify(kind).replace("-", "")
    if k in ("diger", ""):
        return product
    if k.startswith(p):
        # The kind repeats the product, fuller or better spelt: "MUZ YERLİ(ANAMUR)", "ELMA, STARKİNG".
        return kind
    return f"{product} ({kind})"
