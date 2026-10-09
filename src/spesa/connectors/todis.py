"""Todis a casa (todisacasa.it, piattaforma ReStore).

Copertura: API pubblica ReStore `coverage/checkaddress`. Il catalogo e' HTML server-side con
microdata schema.org, ma i prezzi dipendono dal punto vendita che serve l'indirizzo; finche'
l'indirizzo non risulta servito il connettore dichiara l'insegna non disponibile.
Nota robots.txt: vietati /*/ajax/, /changeStore, /changeZipCode, /*?sort.
"""
from __future__ import annotations

from urllib.parse import quote

from spesa.connectors.base import Connector, ConnectorError
from spesa.http import PoliteClient
from spesa.models import Product

COVERAGE = "https://api-fe.restore.shopping/tenants/v2/coverage/checkaddress/"


class TodisConnector(Connector):
    name = "todis"

    def __init__(self, http: PoliteClient | None = None) -> None:
        self.http = http or PoliteClient("todis")
        self.store_id: int | None = None

    def set_location(self, street: str, cap: str, city: str) -> bool:
        r = self.http.request("GET", COVERAGE + quote(f"{street} {city}"), params={"tenant": "tod"},
                              headers={"Origin": "https://todisacasa.it"})
        hits = r.json()
        self.http.save_raw("coverage", hits)
        if not hits:
            return False
        self.store_id = hits[0]["store"]["id"]
        return True

    def search(self, query: str) -> list[Product]:
        raise ConnectorError("todis: parsing del catalogo non ancora implementato "
                             "(serve un indirizzo coperto per ottenere i prezzi del punto vendita)")

    def close(self) -> None:
        self.http.close()
