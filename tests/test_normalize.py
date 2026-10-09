import pytest

from spesa.normalize import normalized_price, parse_format


@pytest.mark.parametrize("text,kind,amount", [
    ("500 g", "kg", 0.5), ("6x125g", "kg", 0.75), ("1,5 l", "l", 1.5), ("75 cl", "l", 0.75),
    ("1 kg", "kg", 1.0), ("12 pz", "pz", 12),
])
def test_parse(text, kind, amount):
    q = parse_format(text)
    assert q and q.kind == kind and q.amount == pytest.approx(amount)


def test_parse_none():
    assert parse_format("confezione") is None and parse_format(None) is None


def test_norm():
    assert normalized_price(1.5, parse_format("500 g")) == 3.0
    assert normalized_price(1.5, None) is None
