"""Antalya Büyükşehir Belediyesi: one PDF per day (any past date), turned into text with pdftotext.

The PDF has two columns per line: vegetables on the left, fruit and then imports on the right.
"""

import json
import re
import subprocess

from .http import get

CITY = "antalya"
NAME = "Antalya"
PUBLISHER = "Antalya Büyükşehir Belediyesi"
URL = "https://www.antalya.bel.tr/tr/halden-gunluk-fiyatlar"
HISTORY = True
_BASE = "https://gezipanel.antalya.bel.tr"
# Row number, name (never starting with a digit: a price left over from the other column isn't a name), unit, prices.
_ROW = re.compile(r"\b\d{1,3}\s+([^\d\s].*?)\s{2,}(Kg|Bağ|Adet|Demet|Kasa|Koli|Paket)\s+([\d.,]+)\s+([\d.,]+)", re.I)


def fetch(date):
    meta = json.loads(get(f"{_BASE}/Methods.aspx/GetGunlukHalFiyatPdf", data=json.dumps({"tarih": date}).encode(),
                          headers={"Content-Type": "application/json; charset=utf-8"}))
    info = meta.get("d") or {}
    if not info.get("PdfUrl") or not info.get("PdfDate"):
        return None
    d, m, y = info["PdfDate"].split(".")
    bulletin = f"{y}-{m}-{d}"
    if bulletin != date:
        return None  # no bulletin that day; the service answers with another day's file
    text = pdf_text(get(_BASE + info["PdfUrl"], raw=True))
    rows = parse(text)
    return (bulletin, rows) if rows else None


def pdf_text(pdf_bytes):
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf_bytes, capture_output=True,
                          check=True).stdout.decode("utf-8", errors="replace")


def parse(text):
    rows, left, right = [], "sebze", "meyve"
    for line in text.splitlines():
        upper = line.upper()
        mid = len(line) // 2
        for word, cat in (("SEBZE", "sebze"), ("MEYVE", "meyve"), ("İTHAL", "ithal")):
            pos = upper.find(word)
            if pos >= 0 and not _ROW.search(line[max(0, pos - 5):pos + 30]):
                if pos < 100:
                    left = cat
                else:
                    right = cat
        for m in _ROW.finditer(line):
            cat = left if m.start() < 100 else right
            rows.append((m.group(1).strip(), m.group(2), m.group(3), m.group(4), None, cat))
    return rows
