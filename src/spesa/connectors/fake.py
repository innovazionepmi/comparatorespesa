from __future__ import annotations

import json
from pathlib import Path

from spesa.connectors.base import Connector
from spesa.models import Product

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


class FakeConnector(Connector):
    """Legge prodotti da tests/fixtures/fake_<name>.json: per la pipeline end-to-end e i test."""

    def __init__(self, name: str = "fake") -> None:
        self.name = name

    def set_location(self, street: str, cap: str, city: str) -> bool:
        return True

    def search(self, query: str) -> list[Product]:
        data = json.loads((FIXTURES / f"fake_{self.name}.json").read_text())
        q = query.lower()
        return [Product(store=self.name, **p) for p in data if q in p["name"].lower()]
