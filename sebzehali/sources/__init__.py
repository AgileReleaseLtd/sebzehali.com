"""One module per source. Each exposes CITY (slug), NAME, URL (public source page), PUBLISHER (who
publishes the bulletin, for the source credit) and fetch(date) -> (bulletin_date, rows) or None, where
rows are normalize_row() inputs. Optional: HISTORY (past dates can be fetched), available_dates(),
REPEATS_LAST (the source answers a day without a bulletin with the last one; see fetch.py).

A source that serves several markets in one response (district branches, a separate fish hall) keeps
one module for the main market and lists a hal.Hal for each other market in BRANCHES, sharing a cached
download. ALL holds every market, modules and branches alike."""

from . import (adana, afyonkarahisar, amasya, ankara, antalya, balikesir, bolu, bursa, canakkale, denizli, gaziantep,
               isparta, izmir, kayseri, kilis, konya, kutahya, manisa, mersin, samsun, sanliurfa, tekirdag, tokat,
               trabzon)

# Largest province first: where the site can't name every market, it names the first ones in this order.
_MODULES = [ankara, izmir, bursa, antalya, konya, adana, sanliurfa, gaziantep, mersin, manisa, kayseri, samsun,
            balikesir, tekirdag, denizli, trabzon, afyonkarahisar, tokat, canakkale, kutahya, isparta, amasya, bolu,
            kilis]

ALL = [h for m in _MODULES for h in (m, *getattr(m, "BRANCHES", ()))]
BY_SLUG = {m.CITY: m for m in ALL}
PROVINCE = {h.CITY: m.NAME for m in _MODULES for h in (m, *getattr(m, "BRANCHES", ()))}
