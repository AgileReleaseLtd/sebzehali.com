"""Samsun Büyükşehir Belediyesi hal price table: JSON from the sales notified to HKS, any day since
2025-09-23, for the central market and the Bafra and Çarşamba branches, plus the fish hall's list (daily
until July 2026, weekly since). No units are given (prices are per kg) and no categories.
"""

import functools
import json

from . import hal
from .http import get

CITY = "samsun"
NAME = "Samsun"
PUBLISHER = "Samsun Büyükşehir Belediyesi"
URL = "https://iidb.samsun.bel.tr/fiyattablosu"
HISTORY = True
API = "https://iidb.samsun.bel.tr/hksapi/fiyat-tablosu"
_CENTRAL, _BAFRA, _CARSAMBA = "1", "2", "3"  # market ids in "haller"
_FISH_HALL = 20  # birim_id of "Samsun Balık Hali" in el_listeler


@functools.lru_cache(maxsize=None)  # fetch.py goes through every date for one market before the next
def _day(date):
    return json.loads(get(f"{API}?tarih={date}&el_tarih={date}"))


_dates = []


def available_dates():
    if not _dates:
        data = json.loads(get(API))
        _dates.extend(sorted((d for d in data["tarihler"] if d < data["bugun"]), reverse=True))
    return _dates


def _fetch(date, hal_id, fish=False):
    data = _day(date)
    bulletin = data.get("tarih")
    # A day's figures fill in as sales are notified and are settled overnight, so today's wait for tomorrow.
    if not bulletin or bulletin >= data["bugun"]:
        return None
    rows = [(u["ad"], "kg", p["min"], p["max"], None, None)
            for u in data["urunler"] for p in [u["fiyatlar"].get(hal_id)] if p]
    if fish:
        rows += _fish(data, bulletin)
    return (bulletin, rows) if rows else None


def _fish(data, day):
    """The fish hall's list, saved once: on the day it was last updated, within the days it covers (a
    week's list may come out on the Tuesday, after Monday's bulletin has been saved)."""
    rows = []
    for el in data.get("el_listeler") or []:
        updated = (el.get("guncelleme") or el["donem_bas"])[:10]
        if el.get("birim_id") == _FISH_HALL and min(max(el["donem_bas"], updated), el["donem_bit"]) == day:
            rows += [(k["ad"], k.get("olcu") or "kg", k["en_az"], k["en_cok"], None, "balik")
                     for k in el["kalemler"]]
    return rows


def fetch(date):
    return _fetch(date, _CENTRAL, fish=True)


BRANCHES = [
    hal.Hal("bafra", "Bafra", URL, PUBLISHER, lambda date: _fetch(date, _BAFRA), available_dates=available_dates),
    hal.Hal("carsamba", "Çarşamba", URL, PUBLISHER, lambda date: _fetch(date, _CARSAMBA),
            available_dates=available_dates),
]
