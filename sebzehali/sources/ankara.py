"""Ankara Büyükşehir Belediyesi hal page: a form POST per list (fruit, vegetables, imports, fish) and date.
Fruit and vegetables go back to mid-2022, fish to 2020. A day without a bulletin gets the newest earlier
one, and every row carries its date.
"""

import re
import urllib.parse

from ..normalize import parse_price

from .html_table import tables
from .http import get

CITY = "ankara"
NAME = "Ankara"
PUBLISHER = "Ankara Büyükşehir Belediyesi"
URL = "https://www.ankara.bel.tr/hal-fiyatlari"
HISTORY = True
# None: the fruit list also carries onions and cabbage, so normalize tells fruit from vegetables.
_LISTS = {"vegetable": None, "fruit": None, "imported": "ithal", "fish": "balik"}
_UNIT = re.compile(r"(?i)\b(kg|kilo|adet|bağ|demet|kasa|koli|paket)\b")
_CRATE = re.compile(r"(?i)\((\d+(?:,\d+)?)\s*k[gğ]\)")


def fetch(date):
    day = "{2}.{1}.{0}".format(*date.split("-"))
    got = {}
    for kind, cat in _LISTS.items():
        body = urllib.parse.urlencode({"date": day, "type": kind}).encode()
        got[kind] = parse(get(URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), cat)
    # The lists don't always move together (no fish on Saturdays; one list may be entered later in the
    # morning), so the bulletin is the newest day both produce lists have reached, and the other lists
    # count only on that day.
    produce = [max(d for d, _ in got[k]) for k in ("vegetable", "fruit") if got[k]]
    if not produce:
        return None
    bulletin = min(produce)
    rows = [row for kind in _LISTS for d, row in got[kind] if d == bulletin]
    return bulletin, rows


def parse(page, cat):
    """(date, row) for each table row."""
    out = []
    for t in tables(page):
        for cells in t:
            m = len(cells) >= 6 and re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", cells[5])
            if not m:
                continue
            unit, low, high = _per_unit(cells[2], parse_price(cells[3]), parse_price(cells[4]))
            out.append((f"{m[3]}-{m[2]}-{m[1]}", (_clean(cells[0]), unit, low, high, None, cat)))
    return out


def _per_unit(unit, low, high):
    # Fish is priced per crate, "Kasa (10 Kğ)P Ks.-S Kut": converted to per-kg prices to compare with
    # other cities ("Kilo (1 Kğ)" rows stay as they are).
    crate = _CRATE.search(unit)
    if crate:
        kg = float(crate.group(1).replace(",", "."))
        return "kg", *(None if p is None else round(p / kg, 2) for p in (low, high))
    word = _UNIT.search(unit)
    return (word.group(1) if word else unit), low, high


def _clean(name):
    # A few names carry the unit or a stray bracket: "Patates kg)", "Lahana (Beyaz) (kg)", "Pazı)".
    name = re.sub(r"(?i)\s*\(?kg\)$", "", name.strip())
    return name.rstrip(")") if name.count(")") > name.count("(") else name
