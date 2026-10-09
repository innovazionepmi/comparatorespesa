import json
from pathlib import Path

from spesa.connectors.esselunga import parse_entities, street_name, tail_format

FIX = Path(__file__).parent / "fixtures" / "esselunga_search.json"


def test_parse():
    prods = parse_entities(json.loads(FIX.read_text()))
    assert prods and all(p.price > 0 and p.format_text for p in prods)


def test_helpers():
    assert street_name("via Giovanni Re 105") == "giovanni re"
    assert tail_format("Rummo Penne Rigate N° 66 500 g") == "500 g"
    assert tail_format("Yogurt 6x125 g") == "6x125 g"
