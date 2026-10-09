from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

UnitKind = Literal["kg", "l", "pz"]


class Product(BaseModel):
    """Prodotto grezzo restituito da un connettore."""

    store: str
    store_product_id: str
    name: str
    brand: str | None = None
    format_text: str | None = None  # es. "500 g", "6x125g"
    price: float  # prezzo di scaffale
    promo_price: float | None = None
    unit_price: float | None = None  # se il sito lo dichiara
    unit_kind: UnitKind | None = None
    available: bool = True
    url: str | None = None


class PricePoint(BaseModel):
    day: date
    store: str
    store_product_id: str
    name: str
    brand: str | None
    format_text: str | None
    price: float
    promo_price: float | None
    normalized_price: float | None  # EUR/kg, EUR/l o EUR/pezzo
    unit_kind: UnitKind | None
    available: bool
    url: str | None
    basket_id: str | None = None
    comparable: bool = True  # False se il formato non e' perfettamente confrontabile
    ts: datetime = Field(default_factory=datetime.now)

    @property
    def effective_price(self) -> float:
        return self.promo_price if self.promo_price is not None else self.price
