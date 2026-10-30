"""Denizli Büyükşehir Belediyesi hal page: the latest bulletin only, about 90 products in two tables.

Prices come as Asgari, Orta and Ekstra (lowest, middle and top); there is no unit column (a few names
carry one) and no category.
"""

import re

from ..normalize import slugify

from .html_table import tables
from .http import get

CITY = "denizli"
NAME = "Denizli"
PUBLISHER = "Denizli Büyükşehir Belediyesi"
URL = "https://www.denizli.bel.tr/hizli-erisim/hal-fiyatlari"
HISTORY = False

# The bulletin's abbreviations and typos, and names that put the variety before the product.
_NAMES = {
    "A.MARUL": "MARUL A.",  # as Bursa writes it; most likely aysberg
    "ANJELİKA MÜRDÜM": "ERİK ANJELİKA MÜRDÜM",
    "BİBER ÇARLİ": "BİBER ÇARLİSTON",
    "DOMATES II": "DOMATES 2. KALİTE",
    "ELMA STARKİN": "ELMA STARKİNG",
    "FİNİ BİBER": "BİBER FİNİ",
    "K.BAHAR": "KARNABAHAR",
    "KIR. PANCAR": "KIRMIZI PANCAR",
    "KIR. SOĞAN": "KIRMIZI SOĞAN",
    "KIV. MARUL": "MARUL KIVIRCIK",
    "KOKTY DOMATES (ÇERİ)": "DOMATES KOKTEYL (ÇERİ)",
    "PAPATES YENİ": "PATATES YENİ",
    "SALK. DOMATES": "DOMATES SALKIM",
}
_UNIT = re.compile(r"\s*\(?\b(KG|KĞ|ADET|BAĞ)\b\)?", re.I)  # "ÇİLEK KĞ", "LİMON (KG) YENİ"


def fetch(date):
    page = get(URL)
    m = re.search(r'id="areaBaslik".*?(\d{2})\.(\d{2})\.(\d{4})', page, re.S)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    rows = []
    for t in tables(page):
        for cells in t:
            if len(cells) < 4 or not re.search(r"\d", cells[1] + cells[3]):
                continue
            name = _NAMES.get(cells[0], cells[0])
            unit = _UNIT.search(name)
            name = _UNIT.sub("", name).strip()
            cat = "ithal" if "ithal" in slugify(name).split("-") else None
            rows.append((name, unit.group(1) if unit else None, cells[1], cells[3], cells[2], cat))
    return (bulletin, rows) if rows else None
