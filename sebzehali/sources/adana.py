"""Adana Büyükşehir Belediyesi "Günlük Hal Raiç Bedeli": a list of bulletins (5 a page, newest first)
linking to one page per day with a vegetable and a fruit table. Near-daily since 18 September 2019,
weekends included; some prices are only revised every few days, but each day is still a dated bulletin.
"""

import datetime as dt
import re

from .html_table import tables
from .http import get

CITY = "adana"
NAME = "Adana"
PUBLISHER = "Adana Büyükşehir Belediyesi"
URL = "https://www.adana.bel.tr/tr/hal-fiyat-listesi"
HISTORY = True
_DETAIL = "https://www.adana.bel.tr/tr/hal-detay/{}"
_FIRST = dt.date(2019, 9, 18)
_TRIES = 6  # the server often resets the connection
_ENTRY = re.compile(r"(?s)act-card-left-l-text\">\s*(\d{2})/(\d{2})/(\d{4})\s*<.*?hal-detay/(\d+)")

_pages = {}


def fetch(date):
    bulletin_id = _find(dt.date.fromisoformat(date))
    return parse(get(_DETAIL.format(bulletin_id), tries=_TRIES)) if bulletin_id else None


def parse(page):
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s*Tarihli", page)
    if not m:
        return None
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    rows = []
    for cat, tab in re.findall(r'(?s)<div id="(sebze|meyve)"(.*?</table>)', page):
        for t in tables(tab):
            for cells in t:
                if len(cells) != 4:
                    continue  # headings, and the odd broken row with extra cells
                low, high = _price(cells[2]), _price(cells[3])
                if low or high:
                    rows.append((cells[0], cells[1], low, high, None, cat))
    return (bulletin, rows) if rows else None


def _price(s):
    # A decimal point ("60.00"), so a comma could only group thousands; 0.00 means no price that day.
    return s.replace(",", "") if re.fullmatch(r"[\d.,]*[1-9][\d.,]*", s) else None


def _find(date):
    """The id of the date's bulletin, or None. There is about one bulletin a day, so the gap in days
    times the rate seen so far says how far down the list to jump; each page read narrows the offsets
    known to be too new and too old."""
    if date < _FIRST:
        return None
    newer, older, off, top = -5, None, 0, None
    while older is None or older - newer > 5:
        page = _list(off)
        if not page:  # past the oldest bulletin
            older, guess = off, (newer + off) // 2
        else:
            for d, bulletin_id in page:
                if d == date:
                    return bulletin_id
            if page[-1][0] < date < page[0][0]:
                return None  # no bulletin that day
            top = top or page[0][0]
            rate = off / max(1, (top - page[0][0]).days) if off else 1
            if date > page[0][0]:
                older, guess = off, off - (date - page[0][0]).days * rate
            else:
                newer, guess = off, off + 4 + (page[-1][0] - date).days * rate
        off = max(int(guess) // 5 * 5, newer + 5)
        if older is not None:
            off = min(off, older - 5)
    return None


def _list(off):
    if off not in _pages:
        page = get(f"{URL}/{off}" if off else URL, tries=_TRIES)
        _pages[off] = [(dt.date(int(y), int(m), int(d)), i) for d, m, y, i in _ENTRY.findall(page)]
    return _pages[off]
