class Hal:
    """A market served by another source module (a district branch, a separate fish hall); looks like a
    source module to fetch.py and build.py. The owning module shares one cached download between them."""

    def __init__(self, city, name, url, publisher, fetch, history=True, available_dates=None, repeats_last=False):
        self.CITY, self.NAME, self.URL, self.PUBLISHER = city, name, url, publisher
        self.HISTORY, self.REPEATS_LAST = history, repeats_last
        self.fetch = fetch
        if available_dates:
            self.available_dates = available_dates
