"""Build the static site from data/ into site/.

    python3 -m sebzehali.build [--out site] [--base-url https://www.sebzehali.com]

Pages: / (today's overview), /hal/ (every market by province), /hal/<city>/ (one city's bulletin),
/urun/<product>/ (one product across cities, with a price chart), /hakkinda/ (sources), /reklam/ (for
advertisers), plus sitemap.xml and robots.txt (and ads.txt once AdSense is set up).
No JavaScript framework; the only scripts are the search filter on the home page and the cookie
consent bar (static/cerez.js), which loads Google Analytics and AdSense after the visitor accepts.
"""

import argparse
import collections
import datetime as dt
import html
import json
import pathlib
import re
import shutil
import statistics
import urllib.parse

from . import config, normalize, sources

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC = ROOT / "static"

CITY_NAMES = {m.CITY: m.NAME for m in sources.ALL}
CITY_URLS = {m.CITY: m.URL for m in sources.ALL}
CITY_PUBLISHERS = {m.CITY: m.PUBLISHER for m in sources.ALL}
CITY_RANK = {m.CITY: i for i, m in enumerate(sources.ALL)}  # largest province first
CHART_LINES = 6  # series slots c1..c6 in style.css; more cities than this and the chart shows the best covered
NAV_CITIES = 5
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
FEATURED = ["domates", "biber", "patates", "sogan", "salatalik", "patlican", "elma", "limon", "muz", "portakal",
            "mandalina", "uzum", "havuc", "kabak", "fasulye", "marul"]
RECENT_DAYS = 21  # products not seen in this many days get no page
MIN_ITEMS = 15  # a market whose latest bulletin is smaller than this gets no pages (too thin to be useful)

e = html.escape


def tr_date(iso, weekday=False):
    d = dt.date.fromisoformat(iso)
    s = f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    if weekday:
        s += " " + ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][d.weekday()]
    return s


def money(v):
    if v is None:
        return "–"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (s[:-3] if s.endswith(",00") else s) + " ₺"


def mid(item):
    return item["avg"] if item.get("avg") else (item["min"] + item["max"]) / 2


def by_rank(cities):
    return sorted(cities, key=lambda c: CITY_RANK.get(c, len(CITY_RANK)))


def by_name(cities):
    return sorted(cities, key=lambda c: normalize.slugify(CITY_NAMES[c]))  # Ç, İ, Ş with C, I, S, not after Z


def in_halls(cities, limit=5):
    """'İzmir, Bursa hallerinde'; past `limit` markets, the largest three and a count of the rest."""
    cities = by_rank(cities)
    if len(cities) <= limit:
        return ", ".join(CITY_NAMES[c] for c in by_name(cities)) + " hallerinde"
    return ", ".join(CITY_NAMES[c] for c in cities[:3]) + f" ve diğer {len(cities) - 3} halde"


# ---------------------------------------------------------------- data

def load():
    """{city: {date: [items]}} for every stored bulletin."""
    out = collections.defaultdict(dict)
    for p in sorted(DATA.glob("*/*/*/*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        out[doc["city"]][doc["date"]] = doc["items"]
    return out


class Site:
    def __init__(self, data, base_url):
        self.data = data
        self.base = base_url.rstrip("/")
        # A market's latest full bulletin: a day when only its fish hall reported isn't its price list.
        self.latest = {c: max((d for d, items in days.items() if len(items) >= MIN_ITEMS), default=max(days))
                       for c, days in data.items() if days}
        self.newest = max(self.latest.values())
        cutoff = (dt.date.fromisoformat(self.newest) - dt.timedelta(days=RECENT_DAYS)).isoformat()
        self.cities = by_name(c for c in self.latest if c in CITY_NAMES and self.latest[c] >= cutoff
                              and len(data[c][self.latest[c]]) >= MIN_ITEMS)

        # product -> {city: [items in that city's latest bulletin]}
        self.products = collections.defaultdict(lambda: collections.defaultdict(list))
        self.raw_names = collections.defaultdict(list)
        votes = collections.defaultdict(collections.Counter)
        for c in self.cities:
            for it in data[c][self.latest[c]]:
                self.products[it["product"]][c].append(it)
                self.raw_names[it["product"]].append(it["raw"])
                votes[it["product"]][it["category"]] += 1
        # Cities file a few products differently (carrots under fruit, cabbage on a fruit list): the majority wins.
        self.category = {p: v.most_common(1)[0][0] for p, v in votes.items()}

    def name(self, product):
        return normalize.product_name(product, self.raw_names.get(product, ()))

    def previous(self, city, date):
        earlier = [d for d in self.data[city] if d < date]
        return self.data[city][max(earlier)] if earlier else None

    def series(self, city, product):
        """(unit, [(date, median price)]): the median across the product's varieties in that city's
        most common unit, per bulletin. One line per city, comparable between cities."""
        units = collections.Counter(it["unit"] for items in self.data[city].values()
                                    for it in items if it["product"] == product)
        if not units:
            return None, []
        unit = max(units, key=lambda u: (units[u], u == "kg"))
        pts = []
        for d in sorted(self.data[city]):
            mids = [mid(it) for it in self.data[city][d] if it["product"] == product and it["unit"] == unit]
            if mids:
                pts.append((d, statistics.median(mids)))
        return unit, pts


# ---------------------------------------------------------------- page shell

def page(site, path, title, description, body, extra_head=""):
    canonical = f"{site.base}{path}"
    # Lets Google check the site is ours while it reviews the AdSense application; loads nothing.
    adsense = f'<meta name="google-adsense-account" content="{e(config.ADSENSE_CLIENT)}">\n' if config.ADSENSE_CLIENT else ""
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="tr_TR">
<meta name="theme-color" content="#1f7a4d">
{adsense}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
{extra_head}</head>
<body>
<header class="top"><div class="wrap">
<a class="logo" href="/"><span class="leaf">🥬</span> sebzehali<span class="tld">.com</span></a>
<nav>{''.join(f'<a href="/hal/{c}/">{e(CITY_NAMES[c])}</a>' for c in by_rank(site.cities)[:NAV_CITIES])}<a href="/hal/">Tüm şehirler</a><a href="/haftalik/">Haftalık</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p>Fiyatlar belediyelerin yayımladığı günlük hal bültenlerinden alınır; toptan (hal) fiyatlarıdır, market ve pazar fiyatları farklıdır.
</p>
<p class="links"><a href="/hakkinda/">Kaynaklar ve açıklama</a> · <a href="/haftalik/">Haftalık özet</a> ·
<a href="/gizlilik/">Gizlilik ve çerezler</a> · <a href="/iletisim/">İletişim</a> · <a href="/reklam/">Reklam verin</a></p>
<p>© {dt.date.today().year} sebzehali.com</p>
</div></footer>
{analytics_snippet()}</body>
</html>
"""


def ads_on():
    return bool(config.ADSENSE_CLIENT and config.ADSENSE_SLOT)


def analytics_snippet():
    out = ""
    ga, ads = config.GA_MEASUREMENT_ID, ads_on()
    if ga or ads:
        if ga and ads:
            ask = ("Ziyaret istatistikleri ve reklamlar için çerez kullanmak istiyoruz. "
                   '<a href="/gizlilik/#cerezler">Ayrıntılar ve ayrı ayrı seçim</a>')
        elif ads:
            ask = 'Reklamlar için Google AdSense çerezlerini kullanmak istiyoruz. <a href="/gizlilik/#cerezler">Ayrıntılar</a>'
        else:
            ask = 'Ziyaret istatistikleri için Google Analytics çerezlerini kullanmak istiyoruz. <a href="/gizlilik/#cerezler">Ayrıntılar</a>'
        attrs = (f' data-ga="{e(ga)}"' if ga else "") + (f' data-ads="{e(config.ADSENSE_CLIENT)}"' if ads else "")
        # The bar starts hidden; cerez.js shows it and loads Google Analytics and AdSense only after
        # the visitor accepts them.
        out += f"""<div id="cerez" class="cerez" role="region" aria-label="Çerez bildirimi" hidden>
<p>{ask}</p>
<div><button type="button" data-cerez="evet">Kabul et</button><button type="button" data-cerez="hayir">Reddet</button></div>
</div>
<script defer src="/cerez.js"{attrs}></script>
"""
    if config.CLOUDFLARE_BEACON_TOKEN:
        beacon = json.dumps({"token": config.CLOUDFLARE_BEACON_TOKEN})
        out += (f"<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" "
                f"data-cf-beacon='{beacon}'></script>\n")
    return out


def ad_slot():
    """An AdSense unit, hidden until cerez.js loads ads for a visitor who accepted them. Empty while ads are off."""
    if not ads_on():
        return ""
    return (f'<aside class="reklam" aria-label="Reklam" hidden><p><span>Reklam</span> <a href="/reklam/">Siz de reklam verin</a></p>'
            f'<ins class="adsbygoogle" style="display:block" data-ad-client="{e(config.ADSENSE_CLIENT)}" '
            f'data-ad-slot="{e(config.ADSENSE_SLOT)}" data-ad-format="auto" data-full-width-responsive="true"></ins></aside>')


def change_badge(now, before):
    if before is None or not before:
        return ""
    pct = (now - before) / before * 100
    if abs(pct) < 0.5:
        return '<span class="chg flat">=</span>'
    cls, arrow = ("up", "▲") if pct > 0 else ("down", "▼")
    return f'<span class="chg {cls}">{arrow} %{abs(pct):.0f}</span>'


def price_table(rows, show_product=True, show_city=False, prev=None, city_scope=False):
    """rows: list of (city, item). prev: {(city, product, variety, unit): item} for change badges.
    city_scope: product names link to that city's product page instead of the all-cities one."""
    head = ("<th>Ürün</th>" if show_product else "") + ("<th>Şehir</th>" if show_city else "")
    out = [f'<div class="tablewrap"><table class="prices"><thead><tr>{head}<th>Çeşit</th><th class="u">Birim</th>'
           f'<th class="n">En düşük</th><th class="n">En yüksek</th><th class="n">Değişim</th></tr></thead><tbody>']
    for city, it in rows:
        p = it["product"]
        before = prev.get((city, p, it["variety"], it["unit"])) if prev else None
        cells = ""
        if show_product:
            href = f"/hal/{city}/{p}/" if city_scope else f"/urun/{p}/"
            cells += f'<td><a href="{href}">{e(normalize.product_name(p, [it["raw"]]))}</a></td>'
        if show_city:
            href = f"/hal/{city}/{p}/" if not show_product else f"/hal/{city}/"
            cells += f'<td><a href="{href}">{e(CITY_NAMES[city])}</a></td>'
        q = normalize.slugify(it["raw"] + " " + CITY_NAMES[city]).replace("-", " ")
        out.append(
            f'<tr data-q="{e(q)}">{cells}<td>{e(it["variety"]) or "–"}</td>'
            f'<td class="u">{e(it["unit"])}</td><td class="n">{money(it["min"])}</td><td class="n">{money(it["max"])}</td>'
            f'<td class="n">{change_badge(mid(it), mid(before) if before else None)}</td></tr>')
    out.append("</tbody></table></div>")
    return "".join(out)


def product_summary(site):
    """The home page's product list: one row per product, with how many markets list it and its price range
    across them in its usual unit (each market's varieties are on the product page)."""
    out = ['<div class="tablewrap"><table class="prices"><thead><tr><th>Ürün</th><th class="n">Hal</th>'
           '<th class="u">Birim</th><th class="n">En düşük</th><th class="n">En yüksek</th><th class="n">Ortanca</th>'
           '</tr></thead><tbody>']
    for p in sorted(site.products, key=lambda p: normalize.slugify(site.name(p))):
        items = [it for items in site.products[p].values() for it in items]
        units = collections.Counter(it["unit"] for it in items)
        unit = max(units, key=lambda u: (units[u], u == "kg"))
        same = [it for it in items if it["unit"] == unit]
        name = site.name(p)
        q = normalize.slugify(" ".join([name, *sorted({it["variety"] for it in items})])).replace("-", " ")
        out.append(f'<tr data-q="{e(q)}"><td><a href="/urun/{p}/">{e(name)}</a></td>'
                   f'<td class="n">{len(site.products[p])}</td><td class="u">{e(unit)}</td>'
                   f'<td class="n">{money(min(i["min"] for i in same))}</td><td class="n">{money(max(i["max"] for i in same))}</td>'
                   f'<td class="n">{money(statistics.median(mid(i) for i in same))}</td></tr>')
    out.append("</tbody></table></div>")
    return "".join(out)


def faq_block(faq):
    html_ = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
    ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
        ensure_ascii=False)
    return (f'<section class="faq"><h2>Sık sorulanlar</h2>{html_}</section>',
            f'<script type="application/ld+json">{ld}</script>\n')


# ---------------------------------------------------------------- pages

def home(site, week=None):
    cards = []
    for p in FEATURED:
        if p not in site.products:
            continue
        mids = [mid(it) for items in site.products[p].values() for it in items
                if it["unit"] == "kg" and it["category"] != "ithal"]
        if not mids:
            continue
        cards.append(f'<a class="card" href="/urun/{p}/"><b>{e(site.name(p))}</b>'
                     f'<span>{money(round(statistics.median(mids)))} <small>/ kg</small></span>'
                     f'<small>ortanca, {len(site.products[p])} hal</small></a>')

    city_cards = "".join(
        f'<a class="city" href="/hal/{c}/"><b>{e(CITY_NAMES[c])} hal fiyatları</b>'
        f'<small>{tr_date(site.latest[c], True)} bülteni · {len(site.data[c][site.latest[c]])} ürün</small></a>'
        for c in site.cities)

    body = f"""
<section class="hero">
<h1>Bugünkü hal fiyatları</h1>
<p>{len(site.cities)} halden sebze, meyve{' ve balık' if any(site.category.get(p) == 'balik' for p in site.products) else ''} toptan fiyatları:
{', '.join(CITY_NAMES[c] for c in site.cities)}.
Son bülten: <b>{tr_date(site.newest, True)}</b>.</p>
</section>
<section><h2>Çok aranan ürünler</h2><div class="cards">{''.join(cards)}</div></section>
{week_teaser(site, week)}
<section><h2>Şehirler</h2><div class="cities">{city_cards}</div></section>
{ad_slot()}
<section>
<h2>Tüm ürünler</h2>
<input id="q" type="search" placeholder="Ürün ara: domates, elma, hamsi…" autocomplete="off" aria-label="Ürün ara">
{product_summary(site)}
</section>
<script>
(function(){{var q=document.getElementById('q'),rows=document.querySelectorAll('table.prices tbody tr');
var A={{'ç':'c','ğ':'g','ı':'i','i̇':'i','ö':'o','ş':'s','ü':'u'}};
function n(s){{return s.toLocaleLowerCase('tr').replace(/[çğıöşü]/g,function(c){{return A[c]}}).trim()}}
q.addEventListener('input',function(){{var v=n(q.value);rows.forEach(function(r){{r.style.display=!v||r.dataset.q.indexOf(v)>=0?'':'none'}})}});}})();
</script>"""
    title = f"Hal Fiyatları Bugün – {len(site.cities)} Halde Sebze Meyve Toptan Fiyatları"
    desc = (f"Güncel hal fiyatları: {tr_date(site.newest)} tarihli bültenlerle {in_halls(site.cities)} "
            "domates, biber, patates, soğan ve tüm sebze meyve toptan fiyatları.")
    return page(site, "/", title, desc, body)


def week_teaser(site, week):
    if not week:
        return ""
    rows = [r for r in week["products"] if r[0] in site.products and r[2] >= 2]
    up = sorted((r for r in rows if r[1] >= 1), key=lambda r: -r[1])[:3]
    down = sorted((r for r in rows if r[1] <= -1), key=lambda r: r[1])[:3]
    li = lambda rs: "".join(f'<li><a href="/urun/{p}/">{e(site.name(p))}</a> <span class="chg {"up" if v > 0 else "down"}">'
                            f'{"▲" if v > 0 else "▼"} %{abs(v):.0f}</span></li>' for p, v, _ in rs)
    return (f'<section><h2>Bu hafta</h2><div class="twocol"><div><h3>Zamlananlar</h3><ol class="movers">{li(up)}</ol></div>'
            f'<div><h3>Ucuzlayanlar</h3><ol class="movers">{li(down)}</ol></div></div>'
            f'<p><a href="/haftalik/">Haftalık özetin tamamı →</a></p></section>')


def city_page(site, c):
    date = site.latest[c]
    items = site.data[c][date]
    prev_items = site.previous(c, date) or []
    prev = {(c, i["product"], i["variety"], i["unit"]): i for i in prev_items}
    sections = []
    for cat, label in normalize.CATEGORIES.items():
        rows = [(c, it) for it in items if it["category"] == cat]
        if rows:
            rows.sort(key=lambda r: (normalize.slugify(site.name(r[1]["product"])), normalize.slugify(r[1]["variety"])))
            sections.append(f"<h2>{e(label)}</h2>{price_table(rows, prev=prev, city_scope=True)}")
    history = sorted(site.data[c], reverse=True)[:10]
    body = f"""
<nav class="crumbs"><a href="/">Hal fiyatları</a> › {e(CITY_NAMES[c])}</nav>
<h1>{e(CITY_NAMES[c])} hal fiyatları</h1>
<p class="lead">{tr_date(date, True)} tarihli {e(CITY_NAMES[c])} hal bülteni: {len(items)} ürün.
Değişim, bir önceki bültene ({tr_date(max(d for d in site.data[c] if d < date)) if prev_items else '–'}) göre ortalama fiyattaki farktır.</p>
{sections[0] if sections else ''}
{ad_slot()}
{''.join(sections[1:])}
<p class="src">Kaynak: <a href="{e(CITY_URLS[c])}" rel="nofollow noopener">{e(CITY_PUBLISHERS[c])}</a>.
Kayıtlı bültenler: {', '.join(tr_date(d) for d in history)}{' …' if len(site.data[c]) > 10 else ''}</p>"""
    title = f"{CITY_NAMES[c]} Hal Fiyatları Bugün ({tr_date(date)}) – Sebze Meyve Fiyatları"
    desc = f"{CITY_NAMES[c]} hal fiyatları {tr_date(date)}: {len(items)} sebze ve meyvenin en düşük ve en yüksek toptan fiyatı, dünkü fiyatlarla karşılaştırma."
    return page(site, f"/hal/{c}/", title, desc, body)


def cities_page(site):
    """/hal/: every market, grouped by province (a province can have district and fish markets too)."""
    groups = collections.defaultdict(list)
    for c in site.cities:
        groups[sources.PROVINCE.get(c, CITY_NAMES[c])].append(c)
    when = lambda c: f'<small>{tr_date(site.latest[c], True)} bülteni · {len(site.data[c][site.latest[c]])} ürün</small>'
    cards = []
    for prov in sorted(groups, key=normalize.slugify):
        cs = sorted(groups[prov], key=lambda c: (CITY_NAMES[c] != prov, normalize.slugify(CITY_NAMES[c])))
        if len(cs) == 1:
            cards.append(f'<a class="city" href="/hal/{cs[0]}/"><b>{e(CITY_NAMES[cs[0]])} hal fiyatları</b>{when(cs[0])}</a>')
        else:  # the central market first, then the district and fish markets
            cards.append(f'<div class="city province"><b>{e(prov)}</b>' + "".join(
                f'<a href="/hal/{c}/">{e(CITY_NAMES[c])} hal fiyatları</a>{when(c)}' for c in cs) + "</div>")
    body = f"""
<nav class="crumbs"><a href="/">Hal fiyatları</a> › Şehirler</nav>
<h1>Şehir şehir hal fiyatları</h1>
<p class="lead">{len(groups)} ilde {len(site.cities)} halin günlük toptan sebze ve meyve fiyatları. Bazı illerde merkez
halinin yanında ilçe halleri ve balık hali de vardır.</p>
<div class="cities">{''.join(cards)}</div>"""
    title = f"Şehir Şehir Hal Fiyatları – {len(site.cities)} Hal"
    desc = (f"{', '.join(sorted(groups, key=normalize.slugify))} hallerinin günlük sebze, meyve ve balık toptan fiyatları; "
            "ilçe halleri dahil.")
    return page(site, "/hal/", title, desc, body)


def chart(site, product, cities=None):
    cutoff = (dt.date.fromisoformat(site.newest) - dt.timedelta(days=90)).isoformat()
    lines = []
    for c in cities or site.cities:
        unit, pts = site.series(c, product)
        pts = [p for p in pts if p[0] >= cutoff]
        if len(pts) >= 2:
            lines.append((c, unit, pts))
    if not lines:
        return ""
    shown = len(lines)
    # Too many markets for one chart: the largest provinces among those with a fair record (weekly and
    # latest-only markets have few points), in rank order so a market keeps its colour whichever others
    # share the chart with it.
    longest = max(len(pts) for _, _, pts in lines)
    fair = [r for r in lines if len(r[2]) >= longest / 3] or lines
    lines = sorted(fair, key=lambda r: CITY_RANK.get(r[0], 0))[:CHART_LINES]
    all_pts = [p for _, _, pts in lines for p in pts]
    legend = []
    W, H, L, R, T, B = 720, 280, 56, 12, 12, 28
    d0 = min(dt.date.fromisoformat(p[0]) for p in all_pts)
    d1 = max(dt.date.fromisoformat(p[0]) for p in all_pts)
    span = max((d1 - d0).days, 1)
    vmax = max(p[1] for p in all_pts) * 1.1
    vmin = 0
    x = lambda d: L + (dt.date.fromisoformat(d) - d0).days / span * (W - L - R)
    y = lambda v: T + (1 - (v - vmin) / (vmax - vmin)) * (H - T - B)
    svg = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(site.name(product))} fiyat grafiği" class="chart">']
    for i in range(5):
        v = vmin + (vmax - vmin) * i / 4
        svg.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                   f'<text x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:.0f}</text>')
    for d, anchor in ((d0, "start"), (d0 + (d1 - d0) / 2, "middle"), (d1, "end")):
        svg.append(f'<text x="{x(d.isoformat()):.1f}" y="{H - 8}" text-anchor="{anchor}">{d.day} {MONTHS[d.month - 1][:3]}</text>')
    for slot, (c, unit, pts) in enumerate(lines, 1):
        poly = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in pts)
        lx, ly = pts[-1]
        svg.append(f'<g class="c{slot}"><polyline points="{poly}"/><circle cx="{x(lx):.1f}" cy="{y(ly):.1f}" r="4"/></g>')
        legend.append(f'<span class="c{slot}"><i></i>{e(CITY_NAMES[c])} ({e(unit)})</span>')
    svg.append("</svg>")
    note = f" Grafikte {len(lines)} hal var; {shown} halin tümü tabloda." if shown > len(lines) else ""
    return (f'<figure class="chartbox">{"".join(svg)}<figcaption>Tüm çeşitlerin ortanca toptan fiyatı (₺), son 90 gün.{note} '
            f'{"".join(legend)}</figcaption></figure>')


def product_page(site, product):
    name = site.name(product)
    rows = sorted(((c, it) for c, items in site.products[product].items() for it in items),
                  key=lambda r: (normalize.slugify(CITY_NAMES[r[0]]), normalize.slugify(r[1]["variety"])))
    prev = {}
    for c in site.products[product]:
        for it in site.previous(c, site.latest[c]) or []:
            if it["product"] == product:
                prev[(c, it["product"], it["variety"], it["unit"])] = it
    kg = [it for _, it in rows if it["unit"] == "kg"] or [it for _, it in rows]
    lo, hi = min(i["min"] for i in kg), max(i["max"] for i in kg)
    unit = kg[0]["unit"]
    med = statistics.median(mid(i) for i in kg)
    cities = {c for c, _ in rows}
    halls = in_halls(cities)
    cheapest = min(rows, key=lambda r: r[1]["min"] if r[1]["unit"] == unit else 1e12)
    faq = [
        (f"{name} hal fiyatı ne kadar?",
         f"{tr_date(site.newest)} itibarıyla {halls} {name.lower()} {unit} fiyatı {money(lo)} ile {money(hi)} arasında; "
         f"orta değer yaklaşık {money(med)}."),
        (f"{name} en ucuz hangi halde?",
         f"Son bültenlerde en düşük {name.lower()} fiyatı {CITY_NAMES[cheapest[0]]} halinde: "
         f"{money(cheapest[1]['min'])} / {cheapest[1]['unit']}{' (' + cheapest[1]['variety'].lower() + ')' if cheapest[1]['variety'] else ''}."),
        ("Hal fiyatı ile market fiyatı neden farklı?",
         "Hal fiyatı üreticinin ve komisyoncunun toptan satış fiyatıdır. Markete ve pazara gelene kadar nakliye, "
         "fire, işçilik ve kâr eklendiği için perakende fiyat genellikle daha yüksektir."),
    ]
    faq_html, ld = faq_block(faq)
    related = [p for p in sorted(site.products, key=lambda p: site.name(p))
               if p != product and site.category.get(p) == site.category.get(product)][:24]
    body = f"""
<nav class="crumbs"><a href="/">Hal fiyatları</a> › {e(name)}</nav>
<h1>{e(name)} hal fiyatı bugün</h1>
<p class="lead">{e(name)} toptan fiyatı {halls} <b>{money(lo)} – {money(hi)}</b> / {e(unit)}
({tr_date(site.newest)}).</p>
{price_table(rows, show_product=False, show_city=True, prev=prev)}
{chart(site, product)}
{ad_slot()}
{faq_html}
<section><h2>Diğer {e(normalize.CATEGORIES.get(site.category.get(product), 'ürün').lower())} fiyatları</h2>
<p class="tags">{''.join(f'<a href="/urun/{p}/">{e(site.name(p))}</a>' for p in related)}</p></section>"""
    where = ", ".join(CITY_NAMES[c] for c in by_name(cities)) if len(cities) <= 3 else f"{len(cities)} Hal"
    title = f"{name} Hal Fiyatı Bugün ({tr_date(site.newest)}) – {where}"
    desc = (f"{name} hal fiyatı: {halls} {unit} fiyatı {money(lo)} – {money(hi)}. "
            f"Şehir şehir güncel {name.lower()} toptan fiyatları ve 90 günlük fiyat grafiği.")
    return page(site, f"/urun/{product}/", title, desc, body, extra_head=ld)


def city_product_page(site, c, product):
    """/hal/<city>/<product>/: one product in one city, e.g. "İzmir hal domates fiyatı"."""
    name, city = site.name(product), CITY_NAMES[c]
    items = sorted(site.products[product][c], key=lambda it: normalize.slugify(it["variety"]))
    prev = {(c, it["product"], it["variety"], it["unit"]): it
            for it in site.previous(c, site.latest[c]) or [] if it["product"] == product}
    unit = max({it["unit"] for it in items}, key=lambda u: (sum(i["unit"] == u for i in items), u == "kg"))
    same = [it for it in items if it["unit"] == unit]
    lo, hi = min(i["min"] for i in same), max(i["max"] for i in same)
    here = statistics.median(mid(i) for i in same)

    others = []
    for oc, oitems in site.products[product].items():
        mids = [mid(i) for i in oitems if i["unit"] == unit]
        if oc != c and mids:
            others.append((oc, statistics.median(mids)))
    others.sort(key=lambda r: r[1])
    compare = ""
    if others:
        lis = "".join(f'<li><a href="/hal/{oc}/{product}/">{e(CITY_NAMES[oc])}</a>: {money(v)} '
                      f'<small>({"+" if v > here else ""}{(v - here) / here * 100:.0f}%)</small></li>'
                      for oc, v in others)
        compare = (f'<section><h2>Diğer hallerle karşılaştırma</h2><p>{e(city)} ortanca fiyatı {money(here)} / {e(unit)}. '
                   f'Diğer hallerde ortanca fiyat:</p><ul class="compare">{lis}</ul>'
                   f'<p><a href="/urun/{product}/">Tüm hallerde {e(name.lower())} fiyatları →</a></p></section>')

    faq = [(f"{city} halinde {name.lower()} fiyatı ne kadar?",
            f"{tr_date(site.latest[c])} tarihli {city} hal bülteninde {name.lower()} {unit} fiyatı "
            f"{money(lo)} ile {money(hi)} arasında; ortanca fiyat yaklaşık {money(here)}.")]
    if others:
        cheap = others[0]
        faq.append((f"{name} {city} halinde mi daha ucuz, diğer hallerde mi?",
                    f"{CITY_NAMES[cheap[0]]} halinde ortanca fiyat {money(cheap[1])}; {city} halinde {money(here)}. "
                    + (f"{city} daha ucuz." if here <= cheap[1] else f"{CITY_NAMES[cheap[0]]} daha ucuz.")))
    faq_html, ld = faq_block(faq)
    siblings = [p for p in sorted(site.products, key=lambda p: normalize.slugify(site.name(p)))
                if p != product and c in site.products[p] and site.category.get(p) == site.category.get(product)][:30]
    body = f"""
<nav class="crumbs"><a href="/">Hal fiyatları</a> › <a href="/hal/{c}/">{e(city)}</a> › {e(name)}</nav>
<h1>{e(city)} hal {e(name.lower())} fiyatı</h1>
<p class="lead">{tr_date(site.latest[c], True)} tarihli {e(city)} hal bülteninde {e(name.lower())}:
<b>{money(lo)} – {money(hi)}</b> / {e(unit)}.</p>
{price_table([(c, it) for it in items], prev=prev, city_scope=True)}
{chart(site, product, cities=[c])}
{ad_slot()}
{compare}
{faq_html}
<section><h2>{e(city)} halinde diğer ürünler</h2>
<p class="tags">{''.join(f'<a href="/hal/{c}/{p}/">{e(site.name(p))}</a>' for p in siblings)}</p></section>
<p class="src">Kaynak: <a href="{e(CITY_URLS[c])}" rel="nofollow noopener">{e(CITY_PUBLISHERS[c])}</a>.</p>"""
    title = f"{city} Hal {name} Fiyatı Bugün ({tr_date(site.latest[c])})"
    desc = (f"{city} hal {name.lower()} fiyatı: {money(lo)} – {money(hi)} / {unit} ({tr_date(site.latest[c])}). "
            f"Çeşit çeşit {name.lower()} toptan fiyatı, fiyat grafiği ve diğer hallerle karşılaştırma.")
    return page(site, f"/hal/{c}/{product}/", title, desc, body, extra_head=ld)


# ---------------------------------------------------------------- weekly summary

def iso_week(d):
    y, w, _ = dt.date.fromisoformat(d).isocalendar()
    return f"{y}-{w:02d}"


def week_range(key):
    y, w = map(int, key.split("-"))
    start = dt.date.fromisocalendar(y, w, 1)
    end = start + dt.timedelta(days=6)
    a = f"{start.day} {MONTHS[start.month - 1]}" if start.month != end.month else str(start.day)
    return f"{a} – {end.day} {MONTHS[end.month - 1]} {end.year}"


def weekly_changes(site):
    """{week: {"products": [(product, pct, n)], "cities": {city: pct}}} comparing each week with the one before.

    A product's change is the median change of its (city, variety, unit) rows that appear in both
    weeks, each row valued at its weekly mean; so a city adding or dropping a variety doesn't move it."""
    means = collections.defaultdict(lambda: collections.defaultdict(list))
    for c in site.data:
        for d, items in site.data[c].items():
            for it in items:
                means[iso_week(d)][(c, it["product"], it["variety"], it["unit"])].append(mid(it))
    weeks = sorted(means)
    out = {}
    for prev_w, w in zip(weeks, weeks[1:]):
        changes = collections.defaultdict(list)
        city_changes = collections.defaultdict(list)
        for key, vals in means[w].items():
            before = means[prev_w].get(key)
            if not before:
                continue
            a, b = statistics.mean(before), statistics.mean(vals)
            if a <= 0:
                continue
            pct = (b - a) / a * 100
            changes[key[1]].append(pct)
            city_changes[key[0]].append(pct)
        prods = [(p, statistics.median(v), len(v)) for p, v in changes.items()]
        out[w] = {"products": prods, "cities": {c: statistics.median(v) for c, v in city_changes.items() if v},
                  "prev": prev_w}
    return out


def weekly_body(site, w, info, heading=True):
    known = [r for r in info["products"] if r[0] in site.products or r[0] in site.raw_names]
    solid = [r for r in known if r[2] >= 2] or known
    up = sorted((r for r in solid if r[1] >= 1), key=lambda r: -r[1])[:10]
    down = sorted((r for r in solid if r[1] <= -1), key=lambda r: r[1])[:10]

    def lst(rows):
        return "".join(f'<li><a href="/urun/{p}/">{e(site.name(p))}</a> <span class="chg {"up" if v > 0 else "down"}">'
                       f'{"▲" if v > 0 else "▼"} %{abs(v):.0f}</span></li>' for p, v, _ in rows) or "<li>–</li>"
    summary = []
    if up:
        summary.append(f"En çok zamlanan ürün <b>{e(site.name(up[0][0]).lower())}</b> oldu (ortalama %{up[0][1]:.0f}).")
    if down:
        summary.append(f"En çok ucuzlayan ürün <b>{e(site.name(down[0][0]).lower())}</b> oldu (ortalama %{abs(down[0][1]):.0f}).")
    cities = sorted(info["cities"].items(), key=lambda r: r[1])
    city_rows = "".join(f'<li><a href="/hal/{c}/">{e(CITY_NAMES.get(c, c))}</a>: '
                        f'{"+" if v > 0 else ""}{v:.1f}%</li>' for c, v in cities)
    head = f"<h1>Haftalık hal fiyatları özeti: {week_range(w)}</h1>" if heading else ""
    return f"""{head}
<p class="lead">{week_range(w)} haftasında hallerdeki fiyatlar bir önceki haftayla ({week_range(info['prev'])}) karşılaştırıldı.
{' '.join(summary)}</p>
<div class="twocol">
<section><h2>En çok zamlananlar</h2><ol class="movers">{lst(up)}</ol></section>
<section><h2>En çok ucuzlayanlar</h2><ol class="movers">{lst(down)}</ol></section>
</div>
{ad_slot()}
<section><h2>Şehirlere göre ortalama değişim</h2><ul class="compare">{city_rows}</ul>
<p class="src">Her ürünün aynı halde ve aynı çeşitteki haftalık ortalama fiyatı bir önceki haftayla karşılaştırılır;
ürün değişimi bu farkların ortancasıdır.</p></section>"""


def weekly_pages(site):
    weeks = weekly_changes(site)
    pages = {}
    keys = sorted(weeks)
    for w in keys:
        nav = " · ".join(f'<a href="/haftalik/{k}/">{week_range(k)}</a>' for k in reversed(keys) if k != w)
        body = (f'<nav class="crumbs"><a href="/">Hal fiyatları</a> › <a href="/haftalik/">Haftalık özet</a> › {week_range(w)}</nav>'
                + weekly_body(site, w, weeks[w]) + f'<section><h2>Diğer haftalar</h2><p class="tags">{nav}</p></section>')
        pages[f"/haftalik/{w}/"] = page(site, f"/haftalik/{w}/", f"Hal Fiyatları Haftalık Özet: {week_range(w)}",
                                       f"{week_range(w)} haftasında hallerde en çok zamlanan ve ucuzlayan sebze ve meyveler.", body)
    if keys:
        last = keys[-1]
        lis = "".join(f'<li><a href="/haftalik/{k}/">{week_range(k)}</a></li>' for k in reversed(keys))
        body = (f'<nav class="crumbs"><a href="/">Hal fiyatları</a> › Haftalık özet</nav>'
                f"<h1>Bu hafta hal fiyatları: zamlananlar ve ucuzlayanlar</h1>"
                + weekly_body(site, last, weeks[last], heading=False)
                + f'<section><h2>Geçmiş haftalar</h2><ul class="compare">{lis}</ul></section>')
        pages["/haftalik/"] = page(site, "/haftalik/", "Haftalık Hal Fiyatları: Bu Hafta Zamlanan ve Ucuzlayan Ürünler",
                                   "Hallerde bu hafta en çok zamlanan ve en çok ucuzlayan sebze ve meyveler, şehir şehir fiyat değişimi.", body)
    return pages, (weeks[keys[-1]] if keys else None)


def about_page(site):
    srcs = "".join(f'<li><b>{e(m.NAME)}</b> ({e(m.PUBLISHER)}): <a href="{e(m.URL)}" rel="nofollow noopener">{e(m.URL)}</a></li>'
                   for m in sorted(sources.ALL, key=lambda m: normalize.slugify(m.NAME)))
    body = f"""
<h1>Kaynaklar ve açıklama</h1>
<p>sebzehali.com, belediyelerin yayımladığı hal fiyat bültenlerini tek yerde toplar.
Fiyatlar her gün birkaç kez otomatik olarak güncellenir.</p>
<h2>Kaynaklar</h2><ul>{srcs}</ul>
<h2>Fiyatlar hakkında</h2>
<ul>
<li>Fiyatlar <b>toptan hal fiyatlarıdır</b> (KDV ve rüsum durumu belediyeye göre değişir). Market, manav ve pazar fiyatları farklıdır.</li>
<li>Değişim oranı, aynı ürün ve çeşidin bir önceki bültendeki ortalama fiyatına göre hesaplanır.</li>
<li>Farklı şehirlerde aynı ürün farklı adlarla geçebilir; ürünler ada göre eşleştirilir ve hata olabilir.</li>
<li>Bilgiler bilgilendirme amaçlıdır; ticari kararlar için belediyenin resmi bültenini kontrol edin.</li>
</ul>
<p>Hata veya eksik bir şehir mi gördünüz? <a href="/iletisim/">İletişim</a></p>"""
    return page(site, "/hakkinda/", "Kaynaklar ve Açıklama – sebzehali.com",
                "sebzehali.com hal fiyatlarının kaynakları ve fiyatların nasıl hesaplandığı.", body)


def privacy_page(site):
    analytics = []
    if config.GA_MEASUREMENT_ID:
        analytics.append(
            "Ziyaret istatistikleri için Google Analytics kullanılır; ancak yalnızca çerez bildiriminde "
            "“Kabul et”i seçerseniz çalışır, dayanağı açık rızanızdır. Kabul ederseniz Google; ziyaret ettiğiniz "
            "sayfaları, yönlendiren siteyi, yaklaşık konumunuzu (ülke, şehir), cihaz ve tarayıcı türünüzü ve "
            "çerezde tutulan rastgele bir kimliği toplar. Bu bilgiler Google tarafından yurt dışındaki "
            "sunucularda işlenir (<a href=\"https://policies.google.com/privacy?hl=tr\" rel=\"nofollow noopener\">"
            "Google gizlilik politikası</a>). Reddederseniz Google Analytics hiç yüklenmez.")
    if config.CLOUDFLARE_BEACON_TOKEN:
        analytics.append(
            "Ziyaret istatistikleri için çerez kullanmayan Cloudflare Web Analytics kullanılır: sayfa adresi, "
            "yönlendiren site, ülke ve tarayıcı türü gibi toplu bilgiler kaydedilir; sizi tanımlayan bir bilgi "
            "veya çerez tutulmaz.")
    if not analytics:
        analytics.append("Şu anda ziyaretçi istatistiği aracı kullanılmamaktadır.")
    analytics = "</p>\n<p>".join(analytics)
    ads = ""
    if ads_on():
        # The second paragraph is the disclosure AdSense's programme policies require.
        ads = (
            "<h2>Reklamlar</h2>\n"
            "<p>Sitede Google AdSense reklamları gösterilir; ancak reklam kodu yalnızca reklam çerezlerine izin "
            "verirseniz yüklenir, dayanağı açık rızanızdır. Reddederseniz reklam gösterilmez.</p>\n"
            "<p>Google dahil üçüncü taraf reklam sağlayıcıları, bu siteye veya diğer sitelere önceki ziyaretlerinize "
            "göre reklam göstermek için çerez kullanır. Google’ın reklam çerezleri, Google’ın ve iş ortaklarının bu "
            "siteye ve internetteki diğer sitelere yaptığınız ziyaretlere göre size reklam göstermesini sağlar. Bu "
            "bilgiler Google tarafından yurt dışındaki sunucularda işlenir (<a href=\"https://policies.google.com/"
            "technologies/ads?hl=tr\" rel=\"nofollow noopener\">Google reklam teknolojileri</a>). Kişiselleştirilmiş "
            "reklamları <a href=\"https://myadcenter.google.com/?hl=tr\" rel=\"nofollow noopener\">Reklam Merkezim</a> "
            "sayfasından kapatabilirsiniz.</p>\n")
    used, choices = [], []
    if config.GA_MEASUREMENT_ID:
        ga_cookie = "_ga_" + config.GA_MEASUREMENT_ID.removeprefix("G-")
        used.append(
            "İstatistiklere izin verirseniz Google Analytics "
            f"<code>_ga</code> ve <code>{e(ga_cookie)}</code> adlı çerezleri yerleştirir; bunlar ziyaretleri "
            "birbirinden ayırt eden rastgele bir kimlik içerir ve en fazla 2 yıl saklanır.")
        choices.append('<label><input type="checkbox" name="istatistik"> İstatistik çerezleri (Google Analytics)</label>')
    if ads_on():
        used.append(
            "Reklamlara izin verirseniz Google, sebzehali.com üzerinde <code>__gads</code>, <code>__gpi</code> ve "
            "<code>__eoi</code> adlı çerezleri, kendi alan adlarında da başka reklam çerezlerini yerleştirebilir; "
            "bunlar en fazla 13 ay saklanır.")
        choices.append('<label><input type="checkbox" name="reklam"> Reklam çerezleri (Google AdSense)</label>')
    if choices:
        # cerez.js ticks the boxes from the saved choices and saves the form.
        cookies = (
            f"<p>sebzehali.com, siz izin vermedikçe çerez kullanmaz. {' '.join(used)} Seçiminiz (kabul veya ret) "
            "çerezde değil, tarayıcınızın yerel deposunda tutulur.</p>\n"
            "<p>Seçiminizi istediğiniz zaman değiştirebilirsiniz; izni kaldırdığınızda sebzehali.com üzerindeki bu "
            "çerezler silinir.</p>\n"
            f'<form id="cerez-tercih" class="tercih">{"".join(choices)}'
            '<div><button type="submit">Tercihimi kaydet</button> <span role="status"></span></div></form>\n')
        if not ads_on():
            cookies += ("<p>Site ileride reklam gösterirse bu sayfa güncellenecek ve reklam çerezleri için ayrıca "
                        "izniniz istenecektir.</p>\n")
    else:
        cookies = ("<p>sebzehali.com çerez kullanmaz. Site ileride reklam gösterirse bu sayfa güncellenecek ve "
                   "çerezler için önceden izniniz istenecektir.</p>\n")
    body = f"""
<h1>Gizlilik ve çerez politikası</h1>
<p>Son güncelleme: {tr_date(config.PRIVACY_UPDATED)}</p>
<h2>Kim işletiyor?</h2>
<p>sebzehali.com, {e(config.OPERATOR)} tarafından işletilmektedir. İletişim: <a href="mailto:{config.CONTACT_EMAIL}">{config.CONTACT_EMAIL}</a></p>
<h2>Hangi bilgileri topluyoruz?</h2>
<p>Sitede üyelik, form veya yorum yoktur; sizden ad, e-posta veya telefon gibi kişisel bilgi istenmez.</p>
<p>{analytics}</p>
<p>Site GitHub Pages üzerinde barındırılır. GitHub, güvenlik ve hizmetin çalışması için ziyaretçilerin IP adresini
kısa süreli olarak kaydedebilir (<a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="nofollow noopener">GitHub gizlilik bildirimi</a>).</p>
{ads}<h2 id="cerezler">Çerezler</h2>
{cookies}<h2>Haklarınız</h2>
<p>6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) kapsamındaki haklarınızla ilgili sorularınız için
<a href="mailto:{config.CONTACT_EMAIL}">{config.CONTACT_EMAIL}</a> adresine yazabilirsiniz.</p>"""
    return page(site, "/gizlilik/", "Gizlilik ve Çerez Politikası – sebzehali.com",
                "sebzehali.com gizlilik ve çerez politikası.", body)


def contact_page(site):
    body = f"""
<h1>İletişim</h1>
<p>Hatalı bir fiyat, eksik bir şehir veya bir öneriniz mi var? Reklam ve iş birliği için de yazabilirsiniz
(<a href="/reklam/">reklam seçenekleri</a>).</p>
<p class="contact"><a href="mailto:{config.CONTACT_EMAIL}">{config.CONTACT_EMAIL}</a></p>
<p>sebzehali.com, {e(config.OPERATOR)} tarafından işletilmektedir.</p>"""
    return page(site, "/iletisim/", "İletişim – sebzehali.com", "sebzehali.com ile iletişim.", body)


def advertising_page(site):
    """/reklam/: for firms that want to advertise. The e-mail opens with a subject and the questions we'd ask."""
    q = urllib.parse.quote
    mail = (f"mailto:{config.CONTACT_EMAIL}?subject={q('sebzehali.com reklam')}&body="
            + q("Firma adı:\r\nŞehir:\r\nTelefon:\r\nTanıtmak istediğiniz ürün veya hizmet:\r\n"
                "Hangi sayfalarda (şehir, ürün veya tüm site):\r\n"))
    buttons = f'<a class="btn" href="{e(mail)}">E-posta ile yazın</a>'
    if config.ADVERTISING_WHATSAPP:
        number = re.sub(r"\D", "", config.ADVERTISING_WHATSAPP)
        wa = f"https://wa.me/{number}?text={q('Merhaba, sebzehali.com’da reklam vermek istiyorum.')}"
        buttons += f' <a class="btn alt" href="{e(wa)}" rel="noopener">WhatsApp’tan yazın</a>'
    city = site.cities[0]
    product = next((p for p in FEATURED if p in site.products), None)
    product_eg = f', örneğin <a href="/urun/{product}/">{e(site.name(product).lower())} hal fiyatı</a>' if product else ""
    body = f"""
<nav class="crumbs"><a href="/">Hal fiyatları</a> › Reklam</nav>
<h1>sebzehali.com’da reklam verin</h1>
<p class="lead">sebzehali.com, {', '.join(CITY_NAMES[c] for c in site.cities)} hallerinin günlük toptan fiyatlarını yayımlar:
{len(site.products)} ürün, her gün birkaç kez güncellenir. Sayfalarımız hal fiyatlarını takip edenler için hazırlanır:
üreticiler, komisyoncular, manavlar, market ve restoran alıcıları.</p>
<h2>Kimler için uygun?</h2>
<ul>
<li>Hal komisyoncuları ve toptancılar</li>
<li>Nakliye, soğuk zincir ve soğuk hava deposu firmaları</li>
<li>Tohum, fide, gübre ve zirai ilaç bayileri</li>
<li>Kasa, ambalaj, sera ve tarım makinesi firmaları</li>
</ul>
<h2>Reklamınız nerede görünür?</h2>
<ul>
<li><b>Şehir sayfaları:</b> bir halin günlük bülteninde ve o şehrin ürün sayfalarında, örneğin
<a href="/hal/{city}/">{e(CITY_NAMES[city])} hal fiyatları</a>.</li>
<li><b>Ürün sayfaları:</b> seçtiğiniz ürünlerin sayfalarında{product_eg}.</li>
<li><b>Tüm site:</b> bütün fiyat sayfalarında.</li>
</ul>
<p>Reklamlar “Reklam” etiketiyle gösterilir. Reklam vermek sitedeki fiyatları etkilemez.</p>
<h2>Bize yazın</h2>
<p>Firmanızı, şehrinizi ve neyi tanıtmak istediğinizi yazın; size uygun sayfaları ve fiyatı bildirelim.</p>
<p class="actions">{buttons}</p>
<p>E-posta: <a href="mailto:{config.CONTACT_EMAIL}">{config.CONTACT_EMAIL}</a>.
sebzehali.com, {e(config.OPERATOR)} tarafından işletilmektedir.</p>"""
    return page(site, "/reklam/", "Reklam Verin – sebzehali.com",
                "sebzehali.com’da reklam: hal fiyatlarını takip eden üretici, komisyoncu ve alıcılara şehir ve ürün "
                "sayfalarında ulaşın.", body)


def not_found(site):
    body = '<h1>Sayfa bulunamadı</h1><p><a href="/">Bugünkü hal fiyatlarına dön</a></p>'
    return page(site, "/404.html", "Sayfa bulunamadı – sebzehali.com", "Sayfa bulunamadı.", body)


# ---------------------------------------------------------------- main

def build(out, base_url):
    if config.ADSENSE_CLIENT and not re.fullmatch(r"ca-pub-\d+", config.ADSENSE_CLIENT):
        raise ValueError(f"ADSENSE_CLIENT should look like ca-pub-1234567890123456, not {config.ADSENSE_CLIENT!r}")
    site = Site(load(), base_url)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    weekly, this_week = weekly_pages(site)
    pages = {"/": home(site, this_week), "/hakkinda/": about_page(site), "/gizlilik/": privacy_page(site),
             "/iletisim/": contact_page(site), "/reklam/": advertising_page(site), **weekly}
    pages["/hal/"] = cities_page(site)
    for c in site.cities:
        pages[f"/hal/{c}/"] = city_page(site, c)
    for p in site.products:
        pages[f"/urun/{p}/"] = product_page(site, p)
        for c in site.products[p]:
            pages[f"/hal/{c}/{p}/"] = city_product_page(site, c, p)
    for path, content in pages.items():
        target = out / path.strip("/") / "index.html" if path != "/" else out / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (out / "404.html").write_text(not_found(site), encoding="utf-8")
    for f in STATIC.iterdir():
        shutil.copy(f, out / f.name)
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site.base}/sitemap.xml\n", encoding="utf-8")
    if config.ADSENSE_CLIENT:
        # f08c47fec0942fa0 is Google's own id in the ads.txt standard.
        pub = config.ADSENSE_CLIENT.removeprefix("ca-")
        (out / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    urls = "".join(f"<url><loc>{site.base}{p}</loc><lastmod>{site.newest}</lastmod></url>" for p in pages)
    (out / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n',
        encoding="utf-8")
    host = base_url.split("//", 1)[-1].rstrip("/")
    (out / "CNAME").write_text(host + "\n", encoding="utf-8")
    return len(pages)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--base-url", default="https://www.sebzehali.com")
    a = ap.parse_args(argv)
    n = build(pathlib.Path(a.out), a.base_url)
    print(f"built {n} pages into {a.out}")


if __name__ == "__main__":
    main()
