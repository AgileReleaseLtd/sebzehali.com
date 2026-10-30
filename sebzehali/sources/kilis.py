"""Kilis Belediyesi: one PDF per weekday, named DD.MM.YYYY.pdf and read with pdftotext. The page embeds only
the newest one; older files are found by name (seen from October 2026; the first few are scans with no
text, which yield nothing)."""

import re

from ..normalize import parse_price

from .antalya import pdf_text
from .http import get

CITY = "kilis"
NAME = "Kilis"
PUBLISHER = "Kilis Belediyesi"
URL = "https://www.kilis.bel.tr/index.php/2025/04/07/guncel-hal-fiyatlari/"
HISTORY = True
_FILES = "https://www.kilis.bel.tr/wp-content/uploads/2025/04"
_MONTHS = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM",
           "KASIM", "ARALIK"]
# Name, min (AS. = asgari), max (AZ. = azami), unit with an optional pack size ("10 DEMET").
_ROW = re.compile(r"(\S.*?)\s{2,}([\d.,]+)\s+([\d.,]+)\s+(?:(\d+)\s+)?(\S+)")

_embedded = []


def fetch(date):
    y, m, d = date.split("-")
    try:
        pdf = get(_newest().get(date) or f"{_FILES}/{d}.{m}.{y}.pdf", raw=True)
    except RuntimeError as e:
        if "HTTP Error 404" in str(e):
            return None  # no list that day
        raise
    bulletin, rows = parse(pdf_text(pdf))
    return (bulletin or date, rows) if rows else None


def _newest():
    """{date: url} of the file the page embeds; a re-upload gets a "-1" suffix the guessed name misses."""
    if not _embedded:
        links = re.findall(r"file=(https://www\.kilis\.bel\.tr/wp-content/uploads/[\w/]*?"
                           r"(\d{2})\.(\d{2})\.(\d{4})[\w-]*\.pdf)", get(URL))
        _embedded.append({f"{y}-{m}-{d}": url for url, d, m, y in links})
    return _embedded[0]


def parse(text):
    """(bulletin date or None, rows) from the PDF's text; the 9 October 2026 file has no TARİH line."""
    m = re.search(r"TARİH\s*:\s*(\d{1,2})\s+(\w+)\s+(\d{4})", text)
    bulletin = None
    if m and m.group(2) in _MONTHS:
        bulletin = f"{m.group(3)}-{_MONTHS.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}"
    rows = []
    for line in text.splitlines():
        m = _ROW.fullmatch(line.strip())
        if not m:
            continue
        name, low, high, pack, unit = m.groups()
        if pack:  # the price of 10 bunches or 8 heads: give it per bunch or head like the other cities
            low, high = parse_price(low) / int(pack), parse_price(high) / int(pack)
        rows.append((name, unit, low, high, None, None))
    return bulletin, rows
