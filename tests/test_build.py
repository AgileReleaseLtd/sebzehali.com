import pathlib
import tempfile
import unittest
from unittest import mock

from sebzehali import build, config


class Build(unittest.TestCase):
    def test_builds_from_stored_data(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.multiple(
                config, GA_MEASUREMENT_ID="G-TEST123", ADSENSE_CLIENT="", ADSENSE_SLOT="", ADVERTISING_WHATSAPP=""):
            n = build.build(pathlib.Path(d), "https://www.sebzehali.com")
            out = pathlib.Path(d)
            self.assertGreater(n, 20)
            home = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("Bugünkü hal fiyatları", home)
            self.assertIn('href="/urun/domates/"', home)
            self.assertIn("<svg", (out / "urun/domates/index.html").read_text(encoding="utf-8"))
            self.assertEqual((out / "CNAME").read_text().strip(), "www.sebzehali.com")
            self.assertIn("/hal/izmir/", (out / "sitemap.xml").read_text())
            self.assertTrue((out / "hal/izmir/domates/index.html").exists())
            self.assertTrue((out / "haftalik/index.html").exists())
            # Every market by province, credited to whoever publishes it; charts use the palette slots.
            cities = (out / "hal/index.html").read_text(encoding="utf-8")
            self.assertIn('href="/hal/izmir/"', cities)
            self.assertIn('href="/hal/"', home)
            self.assertIn("İzmir Büyükşehir Belediyesi</a>", (out / "hal/izmir/index.html").read_text(encoding="utf-8"))
            self.assertIn('class="c1"', (out / "urun/domates/index.html").read_text(encoding="utf-8"))
            for p in ("gizlilik", "iletisim"):
                self.assertIn("info@agilerelease.co.uk", (out / p / "index.html").read_text(encoding="utf-8"))
            # Google Analytics only after consent: pages carry the hidden bar, never the Google tag itself.
            self.assertIn('data-ga="G-TEST123"', home)
            self.assertIn('id="cerez"', home)
            self.assertNotIn("googletagmanager", home)
            self.assertTrue((out / "cerez.js").exists())
            privacy = (out / "gizlilik/index.html").read_text(encoding="utf-8")
            self.assertIn("_ga_TEST123", privacy)
            self.assertIn('id="cerez-tercih"', privacy)
            self.assertIn('name="istatistik"', privacy)
            self.assertNotIn('name="reklam"', privacy)
            # Ads off: nothing from AdSense, but advertisers can still get in touch.
            self.assertFalse((out / "ads.txt").exists())
            self.assertNotIn("adsbygoogle", home)
            self.assertNotIn("google-adsense-account", home)
            self.assertNotIn("data-ads", home)
            self.assertIn('href="/reklam/"', home)
            ad = (out / "reklam/index.html").read_text(encoding="utf-8")
            self.assertIn("mailto:info@agilerelease.co.uk?subject=sebzehali.com%20reklam", ad)
            self.assertNotIn("wa.me", ad)
            self.assertIn("/reklam/", (out / "sitemap.xml").read_text())

    def test_naming_many_markets(self):
        with mock.patch.dict(build.CITY_NAMES, {f"x{i}": f"Şehir {i}" for i in range(8)}), \
                mock.patch.dict(build.CITY_RANK, {f"x{i}": i for i in range(8)}):
            self.assertEqual(build.in_halls(["x1", "x0"]), "Şehir 0, Şehir 1 hallerinde")
            self.assertEqual(build.in_halls([f"x{i}" for i in range(8)]), "Şehir 0, Şehir 1, Şehir 2 ve diğer 5 halde")

    def test_adsense_review_step_shows_no_ads(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.multiple(
                config, ADSENSE_CLIENT="ca-pub-1234567890123456", ADSENSE_SLOT=""):
            build.build(pathlib.Path(d), "https://www.sebzehali.com")
            out = pathlib.Path(d)
            self.assertEqual((out / "ads.txt").read_text(), "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n")
            home = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('<meta name="google-adsense-account" content="ca-pub-1234567890123456">', home)
            self.assertNotIn("adsbygoogle", home)
            self.assertNotIn("data-ads", home)

    def test_ads_on(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.multiple(
                config, GA_MEASUREMENT_ID="G-TEST123", ADSENSE_CLIENT="ca-pub-1234567890123456",
                ADSENSE_SLOT="9876543210", ADVERTISING_WHATSAPP="+90 532 000 00 00"):
            build.build(pathlib.Path(d), "https://www.sebzehali.com")
            out = pathlib.Path(d)
            read = lambda p: (out / p / "index.html").read_text(encoding="utf-8")
            for p in ("", "hal/izmir", "urun/domates", "hal/izmir/domates", "haftalik"):
                html = read(p)
                self.assertIn('<aside class="reklam" aria-label="Reklam" hidden>', html, p)
                self.assertIn('data-ad-slot="9876543210"', html, p)
                # Only cerez.js loads AdSense, and only after consent.
                self.assertNotIn("pagead2", html, p)
                self.assertIn('data-ads="ca-pub-1234567890123456"', html, p)
            for p in ("gizlilik", "iletisim", "hakkinda", "reklam"):
                self.assertNotIn('class="adsbygoogle"', read(p), p)
            privacy = read("gizlilik")
            self.assertIn("__gads", privacy)
            self.assertIn('name="reklam"', privacy)
            self.assertIn("myadcenter.google.com", privacy)
            self.assertIn('href="https://wa.me/905320000000?text=', read("reklam"))

    def test_rejects_malformed_adsense_id(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(config, "ADSENSE_CLIENT", "pub-123"):
            with self.assertRaises(ValueError):
                build.build(pathlib.Path(d), "https://www.sebzehali.com")

    def test_no_analytics_without_ids(self):
        with mock.patch.multiple(config, GA_MEASUREMENT_ID="", CLOUDFLARE_BEACON_TOKEN="", ADSENSE_CLIENT="",
                                 ADSENSE_SLOT=""):
            self.assertEqual(build.analytics_snippet(), "")


if __name__ == "__main__":
    unittest.main()
