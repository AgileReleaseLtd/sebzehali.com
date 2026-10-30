# sebzehali.com

Daily wholesale fruit, vegetable and fish prices (hal fiyatları) from Turkish city councils, as a
static website. Python 3 standard library only; no database, no server.

## How it works

1. `python3 -m sebzehali.fetch` downloads each city's bulletin into `data/YYYY/MM/DD/<city>.json`
   (product names normalised so the same product matches across cities).
2. `python3 -m sebzehali.build` turns all of `data/` into a static site in `site/`:
   - `/`: today's overview, popular products, search;
   - `/hal/`: every market, grouped by province;
   - `/hal/<city>/`: one city's bulletin with change since the previous one;
   - `/urun/<product>/`: one product across cities, 90-day chart, FAQ (with FAQPage markup);
   - `/hal/<city>/<product>/`: one product in one city, compared with the other cities;
   - `/haftalik/` and `/haftalik/<year-week>/`: weekly risers and fallers;
   - `/gizlilik/` (privacy and cookies) and `/iletisim/` (contact); settings in `sebzehali/config.py`,
     including the Google Analytics id and the optional Cloudflare Web Analytics token. Google
     Analytics sets cookies, so `static/cerez.js` shows a consent bar and loads it only after the
     visitor accepts;
   - Google AdSense, off until `ADSENSE_CLIENT` and `ADSENSE_SLOT` are set in `config.py` (see the
     comment there; `ads.txt` is written from them). Ads go on the price pages and, like Google
     Analytics, `static/cerez.js` loads them only for visitors who accept; the privacy page lets
     visitors choose statistics and ads separately;
   - `/reklam/`: for advertisers, with a pre-filled e-mail and an optional WhatsApp button;
   - `/hakkinda/`: sources and disclaimer; plus `sitemap.xml`, `robots.txt`, `CNAME`.
3. GitHub Actions (`.github/workflows/daily.yml`) runs both four times a day, commits new data and
   deploys to GitHub Pages.

## To do

Open tasks are listed in `todo/todo.md`, with one file per task in `todo/items/`.

## Sources

All 81 provinces were checked hall by hall against the Ministry of Trade's register of wholesale markets
on 2026-10-29; these 24 publish prices we can read. Markets listed under one province share a
source (one module, with `BRANCHES`).

| Province | Markets | Source | History |
|---|---|---|---|
| Ankara | central fruit/veg, imports, fish | `ankara.bel.tr/hal-fiyatlari` form POST per list | fruit/veg since mid-2022, fish since 2020 |
| İzmir | fruit/veg, fish hall | open data JSON API (`openapi.izmir.bel.tr`) | any past date |
| Bursa | fruit/veg, imports, fish | `bursa.bel.tr/hal_fiyatlari?tarih=` (HTML) | back to 2020 |
| Antalya | central | `gezipanel.antalya.bel.tr` daily PDF, read with `pdftotext -layout` (poppler-utils) | since about 2026-07 (older dates now return nothing) |
| Konya | central | `konya.bel.tr/hal-fiyatlari?tarih=` (HTML) | ~2,000 past bulletins |
| Adana | Vedat Dalokay hal | `adana.bel.tr/tr/hal-fiyat-listesi` → `/tr/hal-detay/<id>` (server resets connections; retried) | since 2019-09 |
| Şanlıurfa | central | `halfiyatlari.sanliurfa.bel.tr` date search (HTML, paged) | since 2026-02-23 |
| Gaziantep | central | `gaziantep.bel.tr/tr/hal-rayic?date=` (HTML, paged; bundled TLS intermediate) | since 2015, with gaps |
| Mersin | central; Tarsus, Erdemli, Anamur | `mersin.bel.tr/hal-fiyatlari-day` form POST (conventional rows per branch) | any past date |
| Manisa | central | `manisa.bel.tr/apps/sebzemeyvehali/?tar=` (no date on the page: `REPEATS_LAST`) | since 2020-09 |
| Kayseri | central | `kayseri.bel.tr/hal-fiyatlari` ASP.NET postback (`REPEATS_LAST`) | since 2022-06 |
| Samsun | central + fish; Bafra, Çarşamba | `iidb.samsun.bel.tr/hksapi/fiyat-tablosu?tarih=` JSON (no units published; stored as kg) | since 2025-09-23 |
| Balıkesir | Altıeylül; Bandırma + fish | `halvepazarfiyatlari.balikesir.bel.tr` list POST with the page's anti-forgery token | about two years |
| Tekirdağ | Süleymanpaşa | `tekirdag.bel.tr/hal_fiyat_liste` (hal=2) → detail page | since 2020-06 |
| Denizli | central | `denizli.bel.tr/hizli-erisim/hal-fiyatlari` (HTML) | latest only |
| Trabzon | central | `kurumsal.trabzon.bel.tr/halurunfiyatlari` → `_HalFiyatTablo?halBildirimId=` | since 2019-08, Mon/Wed/Fri |
| Afyonkarahisar | central | `afyon.bel.tr` month page → day page → PDF | since 2026-01 |
| Tokat | central | `client-api.tokat.bel.tr/api/public/hal-fiyatlari` JSON (flaky; retried) | since 2026-02-13 |
| Çanakkale | central + fish | `canakkale.bel.tr/tr/sayfa/1481-hal-fiyat-listesi` (HTML) | latest only |
| Kütahya | central | `kutahya.bel.tr/hal.asp` (HTML) | latest only |
| Isparta | central | `isparta.bel.tr/hal-meyve-ve-sebze-fiyatlari` (HTML) | latest only |
| Amasya | central | `amasya.bel.tr/hal-fiyatlari` → PDF, about weekly | PDFs since 2025-03 (older lists are Excel) |
| Bolu | central | WordPress REST API, category 36, weekly | since 2018 |
| Kilis | central | PDFs at `kilis.bel.tr/wp-content/uploads/2025/04/DD.MM.YYYY.pdf` | weekdays, fragile |

Not yet: İstanbul, Kocaeli, Eskişehir, Aydın, Muğla, Malatya and Van refuse connections from outside
Turkey (todo s-017); Sivas, Elazığ, Bingöl, Konya Ereğli, Hatay and others need more work (todo s-018).
Çorum, Kahramanmaraş and Bitlis sit behind bot challenges and Yozgat disallows bots in robots.txt; don't
try to get round those. Most other provinces publish no prices at all.

## Adding a city

Create `sebzehali/sources/<city>.py` with `CITY`, `NAME`, `PUBLISHER` (who publishes the bulletin, shown
in the source credit), `URL`, `HISTORY` and `fetch(date)` returning `(bulletin_date, rows)`, where each row
is `(name, unit, min, max, avg_or_None, category)` and category is one of `sebze`, `meyve`, `ithal`,
`balik`, or `None` when the bulletin doesn't say (fruit is then told from vegetables by product, see
`FRUITS` in `normalize.py`). Add it to `_MODULES` in `sources/__init__.py` (largest province first), save
a copy of the page in `tests/fixtures/` and add a test in `tests/test_source_<city>.py`.

- **Several markets in one response** (district branches, a fish hall): keep the main market in the module
  and list a `hal.Hal` for each other market in `BRANCHES`, sharing one cached download (see `mersin.py`).
- **No date on the page, last bulletin repeated on days without one:** set `REPEATS_LAST = True`;
  `fetch.py` then skips a day whose prices equal the stored bulletin before it.
- **Incomplete certificate chain:** bundle the public intermediate in `sources/certs/` and pass
  `context=http.with_intermediate(...)`. Never switch certificate checks off.
- **Forms:** posting back a page's own anonymous form state (ASP.NET `__VIEWSTATE`, an anti-forgery token
  with its cookie from the same visit, via `http.cookie_opener()`) is fine, fetched fresh every run. Never
  reuse login values, and never try to get round a bot challenge, captcha or a robots.txt disallow.

A market whose latest bulletin has fewer than 15 products gets no pages (`MIN_ITEMS` in `build.py`).

If a product doesn't match across cities, add an alias in `sebzehali/normalize.py`, then run
`python3 -m sebzehali.fetch --renormalize` to re-apply it to stored data.

## Local

```
python3 -m sebzehali.fetch --backfill 60   # first run: 60 days of history where available
python3 -m sebzehali.build --out site
python3 -m http.server -d site 8000
python3 -m unittest discover -s tests -t .
```

## Going live (one-off)

- GitHub repo → Settings → Pages → Source: **GitHub Actions**.
- DNS for sebzehali.com: `www` CNAME → `agilereleaseltd.github.io`; apex A records
  185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (GitHub Pages redirects the
  apex to www). Then tick "Enforce HTTPS".
- Google Search Console: add the domain, submit `https://www.sebzehali.com/sitemap.xml`.
