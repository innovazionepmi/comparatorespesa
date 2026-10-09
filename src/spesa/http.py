"""Client HTTP educato: User-Agent onesto, delay casuale, backoff, stop su 403/429 ripetuti."""
from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

import httpx

from spesa.connectors.base import ConnectorError

log = logging.getLogger("spesa.http")
UA = "spesa-compare/0.1 (uso personale; una run al giorno)"
RAW_DIR = Path("data/raw")
RAW_KEEP_DAYS = 7


class PoliteClient:
    def __init__(self, store: str, delay: tuple[float, float] = (2.0, 6.0), retries: int = 5,
                 base_url: str = "") -> None:
        self.store, self.delay, self.retries = store, delay, retries
        self.client = httpx.Client(base_url=base_url, timeout=30, follow_redirects=True,
                                   headers={"User-Agent": UA, "Accept": "application/json"})
        self._last = 0.0
        self._blocked = 0

    def request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        wait = random.uniform(*self.delay) - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        err: Exception | None = None
        for attempt in range(self.retries):
            try:
                r = self.client.request(method, url, **kw)
                self._last = time.time()
                if r.status_code in (403, 429):
                    self._blocked += 1
                    if self._blocked >= 2:
                        raise ConnectorError(f"{self.store}: HTTP {r.status_code} ripetuto, stop")
                    time.sleep(2 ** (attempt + 2))
                    continue
                r.raise_for_status()
                return r
            except (httpx.TransportError, httpx.HTTPStatusError) as e:  # reset di connessione ecc.
                err = e
                time.sleep(min(2 ** (attempt + 1), 20))
        raise ConnectorError(f"{self.store}: richiesta fallita ({type(err).__name__})")

    def get_json(self, url: str, **kw: Any) -> Any:
        return self.request("GET", url, **kw).json()

    def save_raw(self, tag: str, data: Any) -> None:
        """Ultima risposta grezza per il debug; rotazione a 7 giorni."""
        try:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            (RAW_DIR / f"{self.store}_{tag}.json").write_text(json.dumps(data, ensure_ascii=False))
            cutoff = time.time() - RAW_KEEP_DAYS * 86400
            for f in RAW_DIR.glob("*.json"):
                if f.stat().st_mtime < cutoff:
                    f.unlink()
        except OSError:
            log.debug("salvataggio raw non riuscito", exc_info=True)

    def close(self) -> None:
        self.client.close()
