"""Esselunga a casa (spesaonline.esselunga.it), via API JSON sotto /commerce/resources/.

Flusso (senza account): suggestions(CAP) -> id via -> services/available -> GET street/<id>
(imposta la sessione) -> POST search/facet {query}. Serve l'header x-page-path.
robots.txt vieta le pagine /ricerca, /drive, /ordini, /account, /auth: qui si usa solo l'endpoint
JSON del catalogo, che e' lo stesso chiamato dalla home. Volume minimo, una ricerca per voce.
"""
from __future__ import annotations

import re
from typing import Any

from spesa.connectors.base import Connector, ConnectorError
from spesa.http import PoliteClient
from spesa.models import Product

BASE = "https://spesaonline.esselunga.it"
R = "/commerce/resources"


_TAIL = re.compile(r"(\d+\s*[x×]\s*\d+(?:[.,]\d+)?\s*[a-zA-Z]+|\d+(?:[.,]\d+)?\s*[a-zA-Z]+)\s*$")


def tail_format(description: str) -> str | None:
    """Il formato sta in coda alla descrizione: '... 500 g', '... 6x125 g'."""
    m = _TAIL.search(description.strip())
    return m.group(1) if m else None


def parse_entities(payload: dict[str, Any]) -> list[Product]:
    out: list[Product] = []
    for e in (payload.get("displayables") or {}).get("entities", []):
        if e.get("price") is None:
            continue
        disc = e.get("discountedPrice")
        promo = float(disc) if disc is not None and disc < e["price"] else None
        out.append(Product(
            store="esselunga", store_product_id=str(e["code"]), name=e["description"],
            brand=e.get("brand"), format_text=tail_format(e["description"]), price=float(e["price"]),
            promo_price=promo, url=f"{BASE}/commerce/nav/supermercato/store/home"))
    return out


def street_name(street: str) -> str:
    """'via Giovanni Re 105' -> 'giovanni re' (senza tipo via e civico)."""
    s = re.sub(r"\s+\d+\s*\w?$", "", street.strip().lower())
    return re.sub(r"^(via|viale|piazza|largo|corso|vicolo)\s+", "", s)


class EsselungaConnector(Connector):
    name = "esselunga"

    def __init__(self, http: PoliteClient | None = None, page_size: int = 40) -> None:
        self.http = http or PoliteClient("esselunga", base_url=BASE)
        self.http.client.headers["x-page-path"] = "supermercato"
        self.page_size = page_size

    def set_location(self, street: str, cap: str, city: str) -> bool:
        self.http.request("GET", "/commerce/nav/supermercato/store/home")  # cookie di sessione
        if self.http.request("POST", f"{R}/onboarding/postcode/check", json={"postcode": cap}
                             ).json().get("code") != "SUPPORTED":
            return False
        sugg = self.http.request("POST", f"{R}/onboarding/street/suggestions",
                                 json={"postcode": cap}).json()
        want = street_name(street)
        hit = next((s for s in sugg if re.sub(r"^\w+\s+", "", s["value"].lower()
                                              ).startswith(want + " - ")), None)
        if hit is None:
            return False
        services = self.http.request("POST", f"{R}/onboarding/services/available",
                                     json={"postcode": cap, "streetId": hit["id"]}).json()
        if not any(s.get("site") == "supermercato" for s in services):
            return False  # consegna a domicilio non disponibile
        self.http.request("GET", f"{R}/onboarding/street/{hit['id']}")
        return True

    def search(self, query: str) -> list[Product]:
        r = self.http.request("POST", f"{R}/search/facet",
                              json={"query": query, "start": 0, "length": self.page_size,
                                    "isLargeQuerySearch": True, "filters": [],
                                    "rmtCookieAllowed": False})
        if not r.content:  # 204: nessun risultato o sessione senza indirizzo
            return []
        data = r.json()
        if "displayables" not in data:
            raise ConnectorError(f"esselunga: risposta inattesa ({data.get('code')})")
        self.http.save_raw(f"search_{query[:20]}", data)
        return parse_entities(data)

    def close(self) -> None:
        self.http.close()
