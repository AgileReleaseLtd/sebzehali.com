"""Trabzon Büyükşehir Belediyesi hal page: a bulletin every Monday, Wednesday and Friday since August
2019. The page lists the bulletins by date and id; each one loads as HTML cards, fruit then vegetables.
"""

import re

from ..normalize import slugify

from .html_table import text
from .http import get

CITY = "trabzon"
NAME = "Trabzon"
PUBLISHER = "Trabzon Büyükşehir Belediyesi"
URL = "https://kurumsal.trabzon.bel.tr/halurunfiyatlari"
HISTORY = True
_TABLE = "https://kurumsal.trabzon.bel.tr/HalFiyatSite/_HalFiyatTablo?halBildirimId={}"
_CARD = re.compile(r'(?s)<h4>(.*?)</h4>|<p class="title">(.*?)</p>.*?dFiyat">(.*?)</div>.*?yFiyat">(.*?)</div>')
# Units appear only in some names: "Dereotu (Bağ)", "Mango (İthal-Adet)", "Muz İthal (Koli)"; else kg.
_UNIT = re.compile(r"(?i)\s*\((?:İthal\s*-\s*)?(adet|bağ|demet|kasa|kg|koli|paket)\)$")

_ids = {}


def available_dates():
    if not _ids:
        _ids.update(_load_ids())
    return sorted(_ids, reverse=True)


def _load_ids():
    select = re.search(r'(?s)id="halBildirimDropWeb".*?</select>', get(URL))
    options = re.findall(r'value="(\d+)">\s*(\d{2})\.(\d{2})\.(\d{4})', select.group(0) if select else "")
    return {f"{y}-{m}-{d}": i for i, d, m, y in options}


def fetch(date):
    earlier = [d for d in available_dates() if d <= date]
    if not earlier:
        return None
    rows = parse(get(_TABLE.format(_ids[earlier[0]])))
    return (earlier[0], rows) if rows else None


def parse(page):
    rows, cat = [], None
    for m in _CARD.finditer(page):
        if m.group(1) is not None:
            heading = slugify(text(m.group(1)))  # every card has class "meyve", so go by the headings
            cat = heading if heading in ("meyve", "sebze", "balik") else None
            continue
        name, unit = text(m.group(2)), "kg"
        imported = "ithal" in slugify(name).split("-")
        u = _UNIT.search(name)
        if u:
            name, unit = name[:u.start()], u.group(1)
        rows.append((name, unit, text(m.group(3)), text(m.group(4)), None, "ithal" if imported else cat))
    return rows
