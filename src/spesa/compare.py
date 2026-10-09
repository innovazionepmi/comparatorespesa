from __future__ import annotations

from dataclasses import dataclass, field

from spesa.config import Basket, StoreCfg
from spesa.models import PricePoint


@dataclass
class ItemResult:
    basket_id: str
    label: str
    quantity: float
    best: PricePoint | None
    second: PricePoint | None  # miglior alternativa in un'altra insegna
    per_store: dict[str, PricePoint] = field(default_factory=dict)

    @property
    def saving_vs_second(self) -> float | None:
        if self.best and self.second and self.best.normalized_price and self.second.normalized_price:
            return self.second.normalized_price - self.best.normalized_price
        return None


@dataclass
class Comparison:
    items: list[ItemResult]
    totals: dict[str, float]  # insegna -> totale carrello + consegna (solo se paniere completo)
    incomplete: dict[str, list[str]]  # insegna -> voci mancanti


def _norm(p: PricePoint) -> float:
    base = p.promo_price if p.promo_price is not None else p.price
    # il prezzo normalizzato e' calcolato sul prezzo effettivo al momento della creazione
    return p.normalized_price if p.normalized_price is not None else base


def compare(basket: Basket, points: list[PricePoint], stores: dict[str, StoreCfg]) -> Comparison:
    items: list[ItemResult] = []
    for it in basket.basket:
        cand = [p for p in points if p.basket_id == it.id and p.comparable
                and p.normalized_price is not None]
        if cand:
            kinds = [p.unit_kind for p in cand]
            top = max(set(kinds), key=kinds.count)
            cand = [p for p in cand if p.unit_kind == top]  # mai mescolare EUR/kg e EUR/l
        per_store: dict[str, PricePoint] = {}
        for p in cand:  # miglior prodotto per insegna
            cur = per_store.get(p.store)
            if cur is None or _norm(p) < _norm(cur):
                per_store[p.store] = p
        ranked = sorted(per_store.values(), key=_norm)
        items.append(ItemResult(it.id, it.label, it.quantity,
                                ranked[0] if ranked else None,
                                ranked[1] if len(ranked) > 1 else None, per_store))

    all_stores = sorted({p.store for p in points})
    totals: dict[str, float] = {}
    incomplete: dict[str, list[str]] = {}
    for s in all_stores:
        missing = [i.label for i in items if s not in i.per_store]
        if missing:
            incomplete[s] = missing
            continue
        total = sum(i.per_store[s].effective_price * i.quantity for i in items)
        fee = stores.get(s, StoreCfg()).delivery_fee
        totals[s] = round(total + (fee if isinstance(fee, (int, float)) else 0.0), 2)
    return Comparison(items, totals, incomplete)
