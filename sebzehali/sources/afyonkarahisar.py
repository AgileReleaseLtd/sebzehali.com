"""Afyonkarahisar Belediyesi: one PDF per working day since January 2026, each on its own page listed under
a page per month; read with pdftotext. The site has no lists from before 2026."""

import re

from .antalya import pdf_text
from .http import get

CITY = "afyonkarahisar"
NAME = "Afyonkarahisar"
PUBLISHER = "Afyonkarahisar Belediyesi"
URL = "https://www.afyon.bel.tr/hizmet-rehberi/toptanci-hal-fiyatlari"
HISTORY = True
# Prices often stand for several days, but each day's PDF carries its own date, so every one is a bulletin
# (on a public holiday it's the previous day's list under the holiday's date).
_BASE = "https://www.afyon.bel.tr"
_FIRST = "2026-01-01"
_MONTHS = ["ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim",
           "aralik"]
_DAY_LINK = re.compile(r'href="(/hizmet-rehberi/toptanci-hal-fiyatlari/[^"]*/(\d{2})-(\d{2})-(\d{4})-[^"/]*)"')
_PDF = re.compile(r"/uploads/toptanci-hal-fiyatlari/[\w-]+/dosya/\d{4}/\d{2}/[\w.-]+\.pdf")
# Product, kind (optional), min, max, unit; "*" stands in for prices not set that day.
_ROW = re.compile(r"(\S.*?)\s{2,}(?:(\S.*?)\s{2,})?([\d.,]+)\s+([\d.,]+)\s+(\S+)")
_GENERIC = {"", "*", "NORMAL", "DİĞER"}
# Abbreviated names normalize would misread ("K." as kırmızı, "Y." dropped as yeşil).
_ABBREVIATIONS = {"K.BAHAR": "KARNABAHAR", "Y.DÜNYA": "YENİ DÜNYA"}

_listings = {}


def fetch(date):
    if date < _FIRST:
        return None
    path = _day_page(date)
    if not path:
        return None
    pdf = _PDF.search(get(_BASE + path))
    if not pdf:
        return None
    bulletin, rows = parse(pdf_text(get(_BASE + pdf.group(0), raw=True)))
    return (bulletin or date, rows) if rows else None


def _day_page(date):
    """The date's page, found in its month's listing (20 days a page). Every day of a month shares the
    listing, so it is downloaded once per run."""
    y, m, d = date.split("-")
    month = (f"{URL}/{y}-yili-sebze-ve-meyve-toptan-fiyat-listesi/"
             f"{_MONTHS[int(m) - 1]}-ayi-gunluk-sebze-ve-meyve-toptan-fiyat-listesi")
    for url in (month, f"{month}?page=2"):
        if url not in _listings:
            _listings[url] = {f"{yy}-{mm}-{dd}": p for p, dd, mm, yy in _DAY_LINK.findall(get(url))}
        if date in _listings[url]:
            return _listings[url][date]
        if len(_listings[url]) < 20:
            return None
    return None


def parse(text):
    """(bulletin date or None, rows) from the PDF's text."""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s+SEBZE", text)
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
    rows = []
    for line in text.splitlines():
        m = _ROW.fullmatch(line.strip())
        if not m:
            continue
        product, kind, low, high, unit = m.groups()
        product = _ABBREVIATIONS.get(product, product)
        kind = (kind or "").strip()
        if kind in _GENERIC or kind == product:
            name = product
        elif kind.startswith(product):
            name = kind  # "BİBER" / "BİBER SİVRİ"
        else:
            name = f"{product} {kind}"
        rows.append((name, unit, low, high, None, None))
    return bulletin, rows
