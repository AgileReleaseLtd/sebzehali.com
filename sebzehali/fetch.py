"""Download hal bulletins into data/YYYY/MM/DD/<city>.json.

    python3 -m sebzehali.fetch                    # today's bulletin from every city
    python3 -m sebzehali.fetch --backfill 60      # plus the last 60 days where a city keeps history
    python3 -m sebzehali.fetch --city izmir --date 2026-10-09

A file that already exists is left alone (bulletins don't change), unless --force.
One city failing never stops the others; the exit code is 1 only if every city failed.
"""

import argparse
import datetime as dt
import json
import pathlib
import sys
import traceback

from . import normalize, sources

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def path_for(date, city):
    y, m, d = date.split("-")
    return DATA / y / m / d / f"{city}.json"


def save(city_mod, bulletin, rows):
    items = [r for r in (normalize.normalize_row(*row) for row in rows) if r]
    items.sort(key=lambda r: (r["category"], r["product"], r["variety"]))
    doc = {
        "city": city_mod.CITY,
        "date": bulletin,
        "source": city_mod.URL,
        "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "items": items,
    }
    p = path_for(bulletin, city_mod.CITY)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p, len(items)


def fetch_one(city_mod, date, force=False):
    if not force and path_for(date, city_mod.CITY).exists():
        return "exists"
    got = city_mod.fetch(date)
    if not got:
        return "no bulletin"
    bulletin, rows = got
    if bulletin != date and not force and path_for(bulletin, city_mod.CITY).exists():
        return f"exists ({bulletin})"
    if getattr(city_mod, "REPEATS_LAST", False):
        same = repeat_of(city_mod.CITY, bulletin, rows)
        if same:
            return f"same as {same}, not a new bulletin"
    p, n = save(city_mod, bulletin, rows)
    return f"{n} items -> {p.relative_to(ROOT)}"


def repeat_of(city, date, rows):
    """For sources that answer a day without a bulletin with the last one (and put no date on it):
    the date of the stored bulletin from the week before that has exactly these prices, if any."""
    key = lambda items: sorted((i["product"], i["variety"], i["unit"], i["min"], i["max"], i["avg"]) for i in items)
    new = key(r for r in (normalize.normalize_row(*row) for row in rows) if r)
    day = dt.date.fromisoformat(date)
    for back in range(1, 8):
        d = (day - dt.timedelta(days=back)).isoformat()
        p = path_for(d, city)
        if p.exists():
            return d if key(json.loads(p.read_text(encoding="utf-8"))["items"]) == new else None
    return None


def renormalize():
    """Apply the current normalize.py to stored files (after adding an alias, for example)."""
    n = 0
    for p in sorted(DATA.glob("*/*/*/*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        items = [normalize.normalize_row(i["raw"], i["unit"], i["min"], i["max"], i["avg"], i["category"])
                 for i in doc["items"]]
        doc["items"] = sorted((i for i in items if i), key=lambda r: (r["category"], r["product"], r["variety"]))
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    print(f"renormalized {n} files")
    return 0


def dates_for(city_mod, today, backfill):
    if backfill and getattr(city_mod, "HISTORY", False):
        if getattr(city_mod, "available_dates", None):
            cutoff = (today - dt.timedelta(days=backfill)).isoformat()
            return [d for d in city_mod.available_dates() if d >= cutoff]
        return [(today - dt.timedelta(days=i)).isoformat() for i in range(backfill + 1)]
    return [today.isoformat()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", action="append", choices=sorted(sources.BY_SLUG))
    ap.add_argument("--date", help="YYYY-MM-DD (default: today, Turkey time)")
    ap.add_argument("--backfill", type=int, default=0, help="days of history for cities that keep it")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--renormalize", action="store_true", help="re-run name matching on every stored file")
    a = ap.parse_args(argv)
    if a.renormalize:
        return renormalize()

    today = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date()
    mods = [sources.BY_SLUG[c] for c in a.city] if a.city else sources.ALL
    failed = 0
    for m in mods:
        try:
            dates = dates_for(m, today, a.backfill)
        except Exception:
            dates = None
            print(f"{m.CITY}: FAILED listing dates", file=sys.stderr)
            traceback.print_exc()
        ok = dates is not None
        for d in sorted(dates or []):  # oldest first, so repeat_of() can compare a day with the one before it
            try:  # one bad day doesn't abandon the city's other days
                print(f"{m.CITY} {d}: {fetch_one(m, d, a.force)}", flush=True)
            except Exception:
                ok = False
                print(f"{m.CITY} {d}: FAILED", file=sys.stderr)
                traceback.print_exc()
        failed += not ok
    return 1 if failed == len(mods) else 0


if __name__ == "__main__":
    sys.exit(main())
