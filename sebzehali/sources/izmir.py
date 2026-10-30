"""İzmir Büyükşehir Belediyesi open data API (JSON, any past date): the fruit and vegetable hall and
the fish hall (balık hali); a day without a bulletin answers empty. The fish hall also trades on some
Sundays, when the produce hall is shut: those days are skipped rather than stored as a fish-only bulletin."""

import json

from .http import get

CITY = "izmir"
NAME = "İzmir"
PUBLISHER = "İzmir Büyükşehir Belediyesi"
URL = "https://acikveri.bizizmir.com/"
API = "https://openapi.izmir.bel.tr/api/ibb/halfiyatlari/{hall}/{date}"
_CATEGORY = {"SEBZE": "sebze", "MEYVE": "meyve", "İTHAL": "ithal", "ITHAL": "ithal"}
HISTORY = True


def fetch(date):
    produce = _bulletin("sebzemeyve", date)
    if not produce:
        return None
    fish = _bulletin("balik", date)
    bulletin = (produce.get("BultenTarihi") or date)[:10]
    rows = [_row(x, _CATEGORY.get((x.get("MalTipAdi") or "").upper(), "sebze")) for x in _items(produce)]
    rows += [_row(x, "balik") for x in _items(fish)]
    return bulletin, rows


def _bulletin(hall, date):
    data = json.loads(get(API.format(hall=hall, date=date)) or "null")
    return data if data and data.get("HalFiyatListesi") else None


def _items(data):
    return data["HalFiyatListesi"] if data else []


def _row(x, category):
    return x["MalAdi"], x.get("Birim"), x.get("AsgariUcret"), x.get("AzamiUcret"), x.get("OrtalamaUcret"), category
