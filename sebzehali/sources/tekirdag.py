"""Tekirdağ Büyükşehir Belediyesi: the Süleymanpaşa toptancı hali's daily list, near-daily since June 2020.
A form POST for one day gives a link to that day's list (none on a day without one).

Each product can appear once per production type: the conventional (geleneksel) row is kept, or the
"iyi tarım" row when it is the only one, so each product appears once like the other cities. The Çorlu
hal on the same site stopped publishing in 2025.
"""

import re
import urllib.parse

from ..normalize import slugify

from .html_table import tables
from .http import get

CITY = "tekirdag"
NAME = "Tekirdağ"
PUBLISHER = "Tekirdağ Büyükşehir Belediyesi"
URL = "https://www.tekirdag.bel.tr/hal_fiyat_gunluk"
HISTORY = True
_LIST = "https://www.tekirdag.bel.tr/hal_fiyat_liste"
_DETAIL = "https://www.tekirdag.bel.tr/hal_fiyat_liste_detay/{}"
_HAL = "2"  # Süleymanpaşa (1 is Çorlu)
_CATEGORY = {"SEBZE": "sebze", "MEYVE": "meyve"}


def fetch(date):
    form = {"hal": _HAL, "baslangic_tarih": date, "bitis_tarih": date, "hal_listele": "Listele"}
    page = get(_LIST, data=urllib.parse.urlencode(form).encode(),
               headers={"Content-Type": "application/x-www-form-urlencoded"})
    day = ".".join(reversed(date.split("-")))
    # A range the form doesn't accept falls back to a default list, so check each link's date.
    for list_id, text in re.findall(r'(?s)hal_fiyat_liste_detay/(\d+)"[^>]*>(.*?)</a>', page):
        if f"{day} Tarihli" in text:
            return parse(get(_DETAIL.format(list_id)))
    return None


def parse(page):
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4}) Tarihine Ait", page)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # Columns: Ürün Adı, Ürün Türü, Birim, Tip, Maksimum Fiyat, Minimum Fiyat (max before min).
    found = [c for t in tables(page) for c in t if len(c) == 6 and re.search(r"\d", c[4] + c[5])]
    rows, seen = [], set()
    for cells in sorted(found, key=lambda c: not c[1].upper().startswith("GELENEKSEL")):
        name = _name(cells[0])
        if name in seen:
            continue
        seen.add(name)
        rows.append((name, cells[2], cells[5], cells[4], None, _CATEGORY.get(cells[3].upper())))
    return (bulletin, rows) if rows else None


def _name(raw):
    """'MAYDANOZ (MAYDANOZ)' -> 'MAYDANOZ'; 'ELMA STARKING (ELMA, STARKİNG)' -> 'ELMA STARKING'; older lists
    end in empty brackets: 'DOMATES (DİĞER) ()' -> 'DOMATES (DİĞER)'."""
    key = lambda s: slugify(s).replace("-", "")
    for m in re.finditer(r"\(", raw):
        head = raw[:m.start()].strip()
        if raw.endswith(")") and key(raw[m.start() + 1:-1]) in ("", key(head)):
            return head
    return raw
