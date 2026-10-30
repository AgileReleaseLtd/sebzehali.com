"""Mersin Büyükşehir Belediyesi: a form POST per category and date (any past date).

The table lists every branch market (şube) and both conventional and "iyi tarım" produce. The central
market and the Tarsus, Erdemli and Anamur branches each become a market of their own (the other
branches report only a handful of products now and then); only conventional rows are kept, so each
product appears once per market like the other cities.
"""

import functools
import urllib.parse

from ..normalize import slugify

from .hal import Hal
from .html_table import tables
from .http import get

CITY = "mersin"
NAME = "Mersin"
PUBLISHER = "Mersin Büyükşehir Belediyesi"
URL = "https://www.mersin.bel.tr/hal-fiyatlari"
HISTORY = True
_ENDPOINT = "https://www.mersin.bel.tr/hal-fiyatlari-day"
_CATEGORIES = {"4": "sebze", "3": "meyve"}


@functools.lru_cache(maxsize=None)  # fetch.py goes through every date for one market before the next
def _pages(date):
    """Both category tables for a date, downloaded once and shared by the central market and its branches."""
    out = []
    for code, cat in _CATEGORIES.items():
        body = urllib.parse.urlencode({"published": date, "product_category": code}).encode()
        out.append((get(_ENDPOINT, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), cat))
    return tuple(out)


def _fetch(date, branch):
    rows = [r for page, cat in _pages(date) for r in parse(page, cat, branch)]
    return (date, rows) if rows else None


def fetch(date):
    return _fetch(date, "MERKEZ")


def parse(page, cat, branch="MERKEZ"):
    out, seen = [], set()
    for t in tables(page):
        for cells in t:
            if len(cells) < 8 or cells[0].upper() != branch or not cells[3].upper().startswith("GELENEKSEL"):
                continue
            product, kind = cells[1], cells[2]
            same = slugify(kind).replace("-", "") in (slugify(product).replace("-", ""), "diger")
            name = product if same else f"{product} ({kind})"
            if name in seen:
                continue
            seen.add(name)
            out.append((name, cells[7], cells[4], cells[5], cells[6], cat))
    return out


BRANCHES = [Hal(slugify(name), name, URL, PUBLISHER, functools.partial(_fetch, branch=branch))
            for name, branch in (("Tarsus", "TARSUS"), ("Erdemli", "ERDEMLİ"), ("Anamur", "ANAMUR"))]
