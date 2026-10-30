"""Bolu Belediyesi: a weekly list (usually on Fridays) since 2018, one WordPress post each, read through the
REST API. The post's table has vegetables on the left half of each row and fruit on the right."""

import datetime as dt
import json
import re

from .html_table import tables, text
from .http import get

CITY = "bolu"
NAME = "Bolu"
PUBLISHER = "Bolu Belediyesi"
URL = "https://www.bolu.bel.tr/category/halfiyatlari/"
HISTORY = True
_API = "https://www.bolu.bel.tr/wp-json/wp/v2/posts?categories=36"
# Abbreviated qualifiers, which normalize would otherwise take for the product ("T. Patates" -> "t").
_ABBREVIATIONS = [(r"T\.\s*", "Taze "), (r"K\.\s*", "Kuru "), (r"S\.\s*Kabak", "Kabak Sakız"),
                  (r"Y\.\s*Soğan", "Yeşil Soğan")]


def available_dates():
    """Days the newest 100 lists (about two years) were posted; a list's own date can be a day or two
    earlier, and fetch() returns that."""
    posts = json.loads(get(f"{_API}&per_page=100&_fields=date"))
    return sorted({p["date"][:10] for p in posts}, reverse=True)


def fetch(date):
    # The newest post before the next day. Titles and slugs are sometimes wrong, so the date comes from
    # the table ("Tarih: 23.10.2026").
    after = (dt.date.fromisoformat(date) + dt.timedelta(days=1)).isoformat()
    posts = json.loads(get(f"{_API}&per_page=1&_fields=content&before={after}T00:00:00"))
    return parse(posts[0]["content"]["rendered"]) if posts else None


def parse(content):
    m = re.search(r"Tarih:\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", text(content))
    if not m:
        return None
    bulletin = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    rows = []
    for t in tables(content):
        for cells in t:
            if len(cells) != 12:
                continue
            # Each half: name, unit, min lira, kuruş, max lira, kuruş. Prices are written in full in
            # the lira cells ("60,00 TL"); the kuruş cells are empty apart from the odd stray digit.
            for (name, unit, low, _, high, _), cat in ((cells[:6], "sebze"), (cells[6:], "meyve")):
                if name and (low or high):
                    rows.append((_expand(name), unit, low, high, None, cat))
    return (bulletin, rows) if rows else None


def _expand(name):
    for abbr, full in _ABBREVIATIONS:
        name = re.sub(rf"^{abbr}", full, name)
    return name
