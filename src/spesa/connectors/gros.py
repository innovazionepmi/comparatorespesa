"""Gros Spesa Online (gros.it) via API JSON della piattaforma EBSN. Endpoint e parsing solo qui."""
from __future__ import annotations

from typing import Any

from spesa.connectors.base import Connector
from spesa.http import PoliteClient
from spesa.models import Product

BASE = "https://www.gros.it"
PRODUCTS = "/ebsn/api/products"  # GET ?q=<testo>&page_size=N


def parse_products(payload: dict[str, Any]) -> list[Product]:
    """prezzo = listino; priceDisplay = prezzo effettivo (con promo); description = formato."""
    out: list[Product] = []
    for p in payload.get("data", {}).get("products", []):
        price, shown = p.get("price"), p.get("priceDisplay")
        if price is None:
            continue
        w = p.get("warehousePromo") or {}
        note = (f"sconto {w['discountPerc']:.0f}% fino al {w['expireDate']}"
                if w.get("discountPerc") and w.get("expireDate") else None)
        promo = shown if (p.get("warehousePromo") and shown is not None and shown < price) else None
        out.append(Product(
            store="gros", store_product_id=str(p["productId"]), name=p["name"].title(),
            brand=(p.get("shortDescr") or "").title() or None, format_text=p.get("description"),
            price=float(price), promo_price=float(promo) if promo is not None else None,
            available=(p.get("available") or 0) > 0, url=BASE + p.get("itemUrl", ""),
            promo_note=note if promo is not None else None))
    return out


class GrosConnector(Connector):
    name = "gros"

    def __init__(self, http: PoliteClient | None = None, page_size: int = 100) -> None:
        self.http = http or PoliteClient("gros", base_url=BASE)
        self.page_size = page_size

    def set_location(self, street: str, cap: str, city: str) -> bool:
        # Il catalogo e i prezzi (listino "Gros") non dipendono dall'indirizzo: nessuna chiamata.
        # ASSUNZIONE (docs/ricognizione.md): servizio entro il GRA di Roma, da verificare sul sito.
        return city.strip().lower() == "roma"

    def search(self, query: str) -> list[Product]:
        data = self.http.get_json(PRODUCTS, params={"q": query, "page_size": self.page_size})
        self.http.save_raw(f"search_{query[:20]}", data)
        return parse_products(data)

    def close(self) -> None:
        self.http.close()
