import http.client
import http.cookiejar
import pathlib
import ssl
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; sebzehali.com price bot; +https://www.sebzehali.com/hakkinda/)"
CERTS = pathlib.Path(__file__).resolve().parent / "certs"
_last = [0.0]


def get(url, timeout=40, tries=3, data=None, headers=None, raw=False, context=None, opener=None):
    """GET (or POST when data is given) with a polite 1 s gap between requests and a few retries.
    Returns text, or bytes when raw=True. context: an ssl.SSLContext (see with_intermediate);
    opener: an urllib opener, e.g. from cookie_opener() for sites that need one visit's cookies."""
    err = None
    for attempt in range(tries):
        wait = 1.0 - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        try:
            h = {"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9", **(headers or {})}
            req = urllib.request.Request(url, data=data, headers=h)
            if opener:
                r = opener.open(req, timeout=timeout)
            else:
                r = urllib.request.urlopen(req, timeout=timeout, context=context)
            with r:
                body = r.read()
                return body if raw else body.decode(r.headers.get_content_charset() or "utf-8", errors="replace")
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError) as e:
            err = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                break
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {err}")


def with_intermediate(pem_name):
    """A verifying SSL context that also trusts one bundled intermediate certificate (certs/<pem_name>),
    for servers that don't send their full chain. Verification stays on."""
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(CERTS / pem_name))
    return ctx


def cookie_opener(context=None):
    """An opener that keeps cookies for one visit (fetch a form page, then post it back)."""
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if context:
        handlers.append(urllib.request.HTTPSHandler(context=context))
    return urllib.request.build_opener(*handlers)
