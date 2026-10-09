from __future__ import annotations

import abc

from spesa.models import Product


class ConnectorError(Exception):
    """Errore atteso (sito cambiato, copertura assente, captcha, 429/403)."""


class Connector(abc.ABC):
    name: str

    def login(self) -> None:  # opzionale
        return None

    @abc.abstractmethod
    def set_location(self, street: str, cap: str, city: str) -> bool:
        """Imposta l'indirizzo. Ritorna False se l'indirizzo non e' coperto."""

    @abc.abstractmethod
    def search(self, query: str) -> list[Product]: ...

    def close(self) -> None:
        return None
