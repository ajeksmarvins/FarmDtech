"""Offline parser tests: never infer a market or accept missing dates."""
from datetime import datetime, timezone
import unittest

from src.live_prices import PriceSourceError, parse_prices

HTML = """<table><tr><th>Commodity</th><th>Price / MT</th><th>Approx. / KG</th><th>Movement</th><th>Source</th><th>Source Date</th></tr>
<tr><td>Maize</td><td>₦660,000</td><td>₦660</td><td>—</td><td>Commodity Nigeria</td><td>29 Oct 2026</td></tr>
<tr><td>Rice Paddy</td><td>₦1,160,000</td><td>₦1,160</td><td>—</td><td>Commodity Nigeria</td><td>29 Oct 2026</td></tr>
<tr><td>Beans</td><td>N/A</td><td>N/A</td><td>—</td><td>Unknown</td><td>29 Oct 2026</td></tr></table>"""


class PublishedPriceParserTests(unittest.TestCase):
    def test_unit_conversion_and_provenance(self):
        rows = parse_prices(HTML, checked_at=datetime(2026, 10, 29, tzinfo=timezone.utc))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["price_ngn_per_kg"], 660)
        self.assertIsNone(rows[0]["market"])
        self.assertEqual(rows[1]["commodity_label"], "Rice Paddy")
        self.assertFalse(rows[0]["is_named_market_quote"])
        self.assertTrue(rows[0]["is_recent"])

    def test_no_valid_rows_fails_closed(self):
        with self.assertRaises(PriceSourceError):
            parse_prices("<html>No data</html>")


if __name__ == "__main__":
    unittest.main()
