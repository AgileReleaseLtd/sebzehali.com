"""Amasya Belediyesi: a list about once a week since 2021, each on its own page with the file attached. Lists
since March 2025 are PDFs (an Excel export, read with pdftotext); older ones are Excel files and are skipped."""

import re

from .antalya import pdf_text
from .http import get

CITY = "amasya"
NAME = "Amasya"
PUBLISHER = "Amasya Belediyesi"
URL = "https://amasya.bel.tr/hal-fiyatlari"
HISTORY = True
_BASE = "https://amasya.bel.tr"
_SECTION = re.compile(r"\s*(SEBZELER|MEYVELER)\s*\((\w+)\)")
_ROW = re.compile(r"(\S.*?)\s{2,}([\d.,]+)\s*(?:₺|TL)\s+([\d.,]+)\s*(?:₺|TL)")
# A unit at the end of a name overrides the section's ("DEREOTU (BAĞ)", "MUZ İTHAL KOLİ").
_UNIT = re.compile(r"\s*\(?\b(BAĞ|ADET|KOLİ|KG)\)?$")

_pages = {}


def available_dates():
    return sorted(_listing(), reverse=True)


def _listing():
    """{date: page}; the slug starts with the list's date (DDMMYYYY). A re-posted list keeps the newest."""
    if not _pages:
        for path, d, m, y in re.findall(r'href="(/hal-fiyatlari/(\d{2})(\d{2})(\d{4})[^"]*)"', get(URL)):
            _pages.setdefault(f"{y}-{m}-{d}", path)
    return _pages


def fetch(date):
    # A list covers the days until the next one, so use the newest list on or before the date.
    earlier = [d for d in available_dates() if d <= date]
    if not earlier:
        return None
    page = get(_BASE + _listing()[earlier[0]])
    pdf = re.search(r'/uploads/hal_fiyatlari/[^"]+\.pdf', page)
    if not pdf:
        return None  # an Excel file
    m = re.search(r'entry-title">\s*(\d{2})\.(\d{2})\.(\d{4})', page)
    bulletin = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else earlier[0]
    rows = parse(pdf_text(get(_BASE + pdf.group(0), raw=True)))
    return (bulletin, rows) if rows else None


def parse(text):
    rows, cat, unit = [], None, "KG"
    for line in text.splitlines():
        section = _SECTION.match(line)
        if section:
            cat, unit = ("sebze" if section.group(1) == "SEBZELER" else "meyve"), section.group(2)
            continue
        m = _ROW.fullmatch(line.strip())
        if not m:
            continue
        name, low, high = m.groups()
        u = _UNIT.search(name)
        rows.append((name[:u.start()] if u else name, u.group(1) if u else unit, _price(low), _price(high), None,
                     cat))
    return rows


def _price(s):
    """Excel writes "1,000.00"; normalize reads a comma as the decimal mark, so drop the thousands commas."""
    return s.replace(",", "") if s.rfind(".") > s.rfind(",") else s
