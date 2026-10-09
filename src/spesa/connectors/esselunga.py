"""Esselunga a casa (spesaonline.esselunga.it).

Il sito e' una SPA Angular con API JSON sotto /commerce/resources/. Questo modulo per ora
verifica solo la copertura (onboarding/postcode/check). robots.txt vieta /ricerca, /drive,
/ordini, /account, /auth: la ricerca testuale non va usata, solo la navigazione per categoria.
"""
from __future__ import annotations

from spesa.connectors.base import Connector, ConnectorError
from spesa.http import PoliteClient
from spesa.models import Product

BASE = "https://spesaonline.esselunga.it"
POSTCODE_CHECK = "/commerce/resources/onboarding/postcode/check"


class EsselungaConnector(Connector):
    name = "esselunga"

    def __init__(self, http: PoliteClient | None = None) -> None:
        self.http = http or PoliteClient("esselunga", base_url=BASE)

    def set_location(self, street: str, cap: str, city: str) -> bool:
        r = self.http.request("POST", POSTCODE_CHECK, json={"postcode": cap})
        code = r.json().get("code")
        self.http.save_raw("postcode", r.json())
        if code != "SUPPORTED":
            return False
        # Il CAP e' servito, ma la copertura per via/civico si conferma solo dal flusso del sito
        # (il sito risponde "Indirizzo non trovato o non coperto" per via Giovanni Re, 00134).
        raise ConnectorError("esselunga: CAP servito ma l'indirizzo risulta non coperto/non verificabile; "
                             "connettore catalogo non implementato")

    def search(self, query: str) -> list[Product]:
        raise ConnectorError("esselunga: catalogo non implementato")

    def close(self) -> None:
        self.http.close()
