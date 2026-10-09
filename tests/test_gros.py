import json
from pathlib import Path

from spesa.connectors.gros import GrosConnector, parse_products

FIX = Path(__file__).parent / "fixtures" / "gros_search.json"


def test_parse_gros():
    prods = {p.name: p for p in parse_products(json.loads(FIX.read_text()))}
    promo = prods["Mezze Maniche N.38"]
    assert promo.price == 1.49 and promo.promo_price == 0.67 and promo.brand == "La Molisana"
    assert promo.format_text.startswith("500 g")
    plain = prods["Mezze Maniche Rigate N.84"]
    assert plain.promo_price is None and plain.price == 0.99


def test_location_only_rome():
    c = GrosConnector()
    assert c.set_location("via X 1", "00134", "Roma") and not c.set_location("v", "20121", "Milano")
