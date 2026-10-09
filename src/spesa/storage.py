from __future__ import annotations

import abc
import sqlite3
from pathlib import Path

from spesa.models import PricePoint


class Storage(abc.ABC):
    @abc.abstractmethod
    def save_points(self, points: list[PricePoint]) -> None: ...
    @abc.abstractmethod
    def save_run(self, day: str, store: str, status: str, duration_s: float, note: str = "") -> None: ...
    @abc.abstractmethod
    def save_ambiguous(self, day: str, store: str, basket_id: str, name: str, reason: str) -> None: ...
    @abc.abstractmethod
    def previous_price(self, store: str, basket_id: str, before_day: str) -> float | None: ...
    @abc.abstractmethod
    def avg_price(self, store: str, basket_id: str, since_day: str) -> float | None: ...


SCHEMA = """
CREATE TABLE IF NOT EXISTS price_points(
  day TEXT, store TEXT, store_product_id TEXT, name TEXT, brand TEXT, format_text TEXT,
  price REAL, promo_price REAL, normalized_price REAL, unit_kind TEXT, available INTEGER,
  url TEXT, basket_id TEXT, comparable INTEGER, ts TEXT);
CREATE INDEX IF NOT EXISTS ix_pp ON price_points(store, basket_id, day);
CREATE TABLE IF NOT EXISTS runs(day TEXT, store TEXT, status TEXT, duration_s REAL, note TEXT);
CREATE TABLE IF NOT EXISTS ambigui(day TEXT, store TEXT, basket_id TEXT, name TEXT, reason TEXT);
"""


class SqliteStorage(Storage):
    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)

    def save_points(self, points: list[PricePoint]) -> None:
        self.db.executemany(
            "INSERT INTO price_points VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(p.day.isoformat(), p.store, p.store_product_id, p.name, p.brand, p.format_text,
              p.price, p.promo_price, p.normalized_price, p.unit_kind, int(p.available), p.url,
              p.basket_id, int(p.comparable), p.ts.isoformat()) for p in points])
        self.db.commit()

    def save_run(self, day: str, store: str, status: str, duration_s: float, note: str = "") -> None:
        self.db.execute("INSERT INTO runs VALUES (?,?,?,?,?)", (day, store, status, duration_s, note))
        self.db.commit()

    def save_ambiguous(self, day: str, store: str, basket_id: str, name: str, reason: str) -> None:
        self.db.execute("INSERT INTO ambigui VALUES (?,?,?,?,?)", (day, store, basket_id, name, reason))
        self.db.commit()

    def previous_price(self, store: str, basket_id: str, before_day: str) -> float | None:
        r = self.db.execute(
            "SELECT MIN(normalized_price) FROM price_points WHERE store=? AND basket_id=? AND day="
            "(SELECT MAX(day) FROM price_points WHERE store=? AND basket_id=? AND day<?)",
            (store, basket_id, store, basket_id, before_day)).fetchone()
        return r[0] if r else None

    def avg_price(self, store: str, basket_id: str, since_day: str) -> float | None:
        r = self.db.execute(
            "SELECT AVG(normalized_price) FROM price_points WHERE store=? AND basket_id=? AND day>=?",
            (store, basket_id, since_day)).fetchone()
        return r[0] if r else None
