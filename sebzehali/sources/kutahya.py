"""Kütahya Belediyesi hal page: the latest bulletin only. Its date can stay the same for several days.

No unit column ("Adet", "Bağ" or "(Kg.)" sometimes stand in the kind or the name) and no category
apart from imports, which have "İTHAL" as their kind.
"""

import re

from ..normalize import slugify

from .html_table import tables
from .http import get

CITY = "kutahya"
NAME = "Kütahya"
PUBLISHER = "Kütahya Belediyesi"
URL = "https://www.kutahya.bel.tr/hal.asp"
HISTORY = False
_UNIT = re.compile(r"\s*\(?\b(KG|ADET|BAĞ)\b\.?\)?", re.I)


def fetch(date):
    page = get(URL, tries=4)  # the server often resets the first connection
    m = re.search(r"Son Güncelleme\s*:\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", page)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    rows = []
    for t in tables(page):
        for cells in t:
            if len(cells) < 5 or not re.search(r"\d", cells[2] + cells[3]):
                continue
            product, kind = cells[0], cells[1]
            unit = _UNIT.search(product) or _UNIT.search(kind)
            product, kind = _UNIT.sub("", product).strip(), _UNIT.sub("", kind).strip()
            name = product if slugify(kind) in ("", "normal", "diger") else f"{product} ({kind})"
            cat = "ithal" if slugify(kind) == "ithal" else None
            rows.append((name, unit.group(1) if unit else None, cells[2], cells[3], cells[4], cat))
    return (bulletin, rows) if rows else None
