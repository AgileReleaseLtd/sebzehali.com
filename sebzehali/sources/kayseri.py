"""Kayseri Büyükşehir Belediyesi hal page: an ASP.NET form, posted back with the page's own hidden fields
and a date (any past date, back to at least 2022).

The answer carries no bulletin date: a day without a bulletin shows the last one (REPEATS_LAST) and a
future date an empty table. No categories.
"""

import html
import re
import urllib.parse

from .html_table import tables
from .http import get

CITY = "kayseri"
NAME = "Kayseri"
PUBLISHER = "Kayseri Büyükşehir Belediyesi"
URL = "https://www.kayseri.bel.tr/hal-fiyatlari"
HISTORY = True
REPEATS_LAST = True

_form = {}  # the page's hidden fields, fetched once per run: one form state answers any number of dates


def fetch(date):
    y, m, d = date.split("-")
    day = f"{d}.{m}.{y}"
    for _ in range(2):
        if not _form:
            _form.update(hidden_fields(get(URL)))
        fields = {**_form, "__EVENTTARGET": "ctl00$contentHolder$btnSorgula", "__EVENTARGUMENT": "",
                  "ctl00$contentHolder$HalFiyatlariDate": day}
        page = get(URL, data=urllib.parse.urlencode(fields).encode(),
                   headers={"Content-Type": "application/x-www-form-urlencoded"})
        if f'value="{day}"' in page:
            rows = parse(page)
            return (date, rows) if rows else None
        _form.clear()  # a rejected form state is redirected to an error page: fetch the page again
    raise RuntimeError(f"{URL} did not accept the form for {day}")


def hidden_fields(page):
    return {k: html.unescape(v)
            for k, v in re.findall(r'<input type="hidden" name="(__\w+)" id="__\w+" value="([^"]*)"', page)}


def parse(page):
    rows = []
    for t in tables(page):
        if not t or t[0][0] != "CİNSİ":
            continue
        for cells in t[1:]:
            if len(cells) == 4:  # name, unit, highest, lowest
                rows.append((cells[0], cells[1], cells[3], cells[2], None, None))
    return rows
