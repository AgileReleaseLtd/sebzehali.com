"""Balıkesir Büyükşehir Belediyesi hal and market prices site: one list of every hal's prices for a date
(the page offers the last two years), which the page's script loads with the anti-forgery token it was
served; the token and its cookie are read fresh from the page on each run.

This module is Altıeylül, the central fruit and vegetable hal; Bandırma's fruit and vegetable hal and its
fish hall make the "bandirma" market. Burhaniye, Edremit and Havran are on the site too but published on
one day between them in two years (checked October 2026), so they aren't listed. A day without a bulletin
answers an empty list. No categories for fruit and vegetables.
"""

import re
import urllib.parse

from . import hal
from .html_table import tables
from .http import cookie_opener, get

CITY = "balikesir"
NAME = "Balıkesir"
PUBLISHER = "Balıkesir Büyükşehir Belediyesi"
URL = "https://halvepazarfiyatlari.balikesir.bel.tr/SebzeMeyveHal"
HISTORY = True
_LIST = "https://halvepazarfiyatlari.balikesir.bel.tr/Home/Listele"
_KINDS = {"1": None, "2": "balik"}  # the list's TurAd: fruit and vegetable halls, fish hall
_MARKETS = {"ALTIEYLÜL SEBZE MEYVE HALİ": CITY, "BANDIRMA SEBZE MEYVE HALİ": "bandirma",
            "BANDIRMA BALIK HALİ": "bandirma"}

BRANCHES = [hal.Hal("bandirma", "Bandırma", URL, PUBLISHER, lambda date: fetch(date, "bandirma"))]

_visit = {}  # the cookies and token of one visit to the page, for every list this run
_cache = {}  # date -> {market: rows}


def fetch(date, market=CITY):
    if date not in _cache:
        _cache[date] = _download(date)
    rows = _cache[date].get(market)
    return (date, rows) if rows else None


def _download(date):
    if not _visit:
        opener = cookie_opener()
        page = get(URL, opener=opener)
        token = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', page).group(1)
        _visit.update(opener=opener, token=token)
    y, m, d = date.split("-")
    markets = {}
    for kind, cat in _KINDS.items():
        body = urllib.parse.urlencode({"BasT": f"{d}.{m}.{y}", "BitT": f"{d}.{m}.{y}", "UrunAd": "", "HalAd": "",
                                       "TurAd": kind}).encode()
        page = get(_LIST, data=body, opener=_visit["opener"],
                   headers={"__RequestVerificationToken": _visit["token"], "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        for market, row in parse(page, date, cat):
            markets.setdefault(market, []).append(row)
    return markets


def parse(page, date, category):
    """(market, row) for each price in the list that holds on date."""
    out = []
    for t in tables(page):
        for cells in t:
            if len(cells) != 7 or cells[2] not in _MARKETS:  # product, unit, market, lowest, highest, from, to
                continue
            start, end = (f"{c[6:10]}-{c[3:5]}-{c[0:2]}" for c in cells[5:7])
            if start <= date <= end:
                out.append((_MARKETS[cells[2]], (cells[0], cells[1], cells[3], cells[4], None, category)))
    return out
