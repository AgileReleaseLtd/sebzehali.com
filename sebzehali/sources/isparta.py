"""Isparta Belediyesi hal page: the latest bulletin only, laid out in divs rather than a table.

Each row is four cells (product, lowest, highest, unit); the date is in the first cell's data-header.
No category.
"""

import re

from .html_table import text
from .http import get

CITY = "isparta"
NAME = "Isparta"
PUBLISHER = "Isparta Belediyesi"
URL = "https://www.isparta.bel.tr/hal-meyve-ve-sebze-fiyatlari"
HISTORY = False


def fetch(date):
    page = get(URL)
    m = re.search(r'data-header="TARİH\s*:\s*(\d{2})\.(\d{2})\.(\d{4})"', page)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    rows = []
    for row in page.split('class="custom-table-row"')[1:]:
        cells = [text(c) for c in re.findall(r'(?s)data-header="[^"]*">(.*?)</div>', row)[:4]]
        if len(cells) < 4 or not re.search(r"\d", cells[1] + cells[2]):
            continue
        rows.append((cells[0], cells[3], cells[1], cells[2], None, None))
    return (bulletin, rows) if rows else None
