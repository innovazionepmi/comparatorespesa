from __future__ import annotations

import csv
import logging
import random
import time
from datetime import date
from pathlib import Path

from spesa.config import Basket, UserCfg
from spesa.connectors.base import Connector, ConnectorError
from spesa.matcher import match
from spesa.models import PricePoint, Product
from spesa.normalize import normalized_price, parse_format
from spesa.storage import Storage

log = logging.getLogger("spesa")


def _queries(item) -> list[str]:
    if item.queries:
        return item.queries
    return [item.accept.must_include[0] if item.accept.must_include else item.label]


def run_store(conn: Connector, basket: Basket, user: UserCfg, storage: Storage, day: date,
              review_csv: Path, delay: tuple[float, float] = (2.0, 6.0)) -> list[PricePoint]:
    t0 = time.time()
    points: list[PricePoint] = []
    try:
        if not conn.set_location(user.address.street, user.address.cap, user.address.city):
            raise ConnectorError("indirizzo non coperto")
        for n, item in enumerate(basket.basket):
            if n and delay[1] > 0:
                time.sleep(random.uniform(*delay))
            seen: set[str] = set()
            found: list[Product] = []
            for qn, q in enumerate(_queries(item)):
                if qn and delay[1] > 0:
                    time.sleep(random.uniform(*delay))
                found += conn.search(q)
            for p in found:
                if p.store_product_id in seen:
                    continue
                seen.add(p.store_product_id)
                r = match(item, p)
                if r.status == "ambiguo":
                    storage.save_ambiguous(day.isoformat(), conn.name, item.id, p.name, r.reason)
                    _append_review(review_csv, day, conn.name, item.id, p, r.reason)
                if r.status == "match":
                    points.append(to_point(p, day, item.id, r.comparable))
        storage.save_points(points)
        storage.save_run(day.isoformat(), conn.name, "ok", time.time() - t0)
    except ConnectorError as e:
        log.warning("connettore %s fallito: %s", conn.name, e)
        storage.save_run(day.isoformat(), conn.name, "errore", time.time() - t0, str(e))
        raise
    finally:
        conn.close()
    return points


def to_point(p: Product, day: date, basket_id: str, comparable: bool) -> PricePoint:
    qty = parse_format(p.format_text)
    eff = p.promo_price if p.promo_price is not None else p.price
    norm = normalized_price(eff, qty)
    kind = qty.kind if qty else p.unit_kind
    if norm is None and p.unit_price is not None:
        norm, kind = p.unit_price, p.unit_kind
    return PricePoint(day=day, store=p.store, store_product_id=p.store_product_id, name=p.name,
                      brand=p.brand, format_text=p.format_text, price=p.price,
                      promo_price=p.promo_price, normalized_price=norm, unit_kind=kind,
                      available=p.available, url=p.url, basket_id=basket_id, comparable=comparable)


def _append_review(path: Path, day: date, store: str, bid: str, p: Product, reason: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["data", "insegna", "voce", "marca", "prodotto", "formato", "prezzo", "motivo", "url"])
        w.writerow([day.isoformat(), store, bid, p.brand or "", p.name, p.format_text, p.price, reason,
                    p.url or ""])
