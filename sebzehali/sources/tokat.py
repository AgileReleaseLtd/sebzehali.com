"""Tokat Belediyesi hal prices: a JSON API with weekday bulletins since 2026-02-13. A day without a
bulletin is answered with the newest earlier one. The server is slow at times and drops connections, so
requests get extra tries.
"""

import json

from .http import get

CITY = "tokat"
NAME = "Tokat"
PUBLISHER = "Tokat Belediyesi"
URL = "https://www.tokat.bel.tr/hal-fiyatlari"
HISTORY = True
API = "https://client-api.tokat.bel.tr/api/public/hal-fiyatlari"
_CATEGORY = {"sebze": "sebze", "meyve": "meyve", "yesil": "sebze"}  # yeşil: herbs and salad leaves
_TRIES = 5
_PAGE = 100  # the most the API returns at once

_dates = []


def available_dates():
    if not _dates:
        data = json.loads(get(f"{API}/available-dates", tries=_TRIES))
        _dates.extend(sorted(set(data["data"]), reverse=True))
    return _dates


def fetch(date):
    items, total = [], 1
    while len(items) < total:
        body = json.dumps({"limit": _PAGE, "offset": len(items), "date": date}).encode()
        page = json.loads(get(API, data=body, headers={"Content-Type": "application/json"}, tries=_TRIES))
        if not page.get("data"):
            break
        items += page["data"]
        total = page["pagination"]["total"]
    if not items:
        return None
    bulletin = max(x["price_date"][:10] for x in items)
    rows = [(x["product_name"], x["unit_type"], x["min_price"], x["max_price"], None, _CATEGORY.get(x["category"]))
            for x in items if x["price_date"][:10] == bulletin]
    return bulletin, rows
