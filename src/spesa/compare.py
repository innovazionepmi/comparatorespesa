from __future__ import annotations

from dataclasses import dataclass, field

from spesa.config import Basket, BasketItem, StoreCfg
from spesa.models import PricePoint
from spesa.normalize import parse_format


@dataclass
class ItemResult:
    basket_id: str
    label: str
    quantity: float
    best: PricePoint | None
    second: PricePoint | None  # miglior alternativa in un'altra insegna
    per_store: dict[str, PricePoint] = field(default_factory=dict)
    amount_text: str | None = None  # es. "9.5 kg": se presente il costo e' prezzo/unita' x quantita'

    def cost(self, store: str) -> float | None:
        p = self.per_store.get(store)
        if p is None:
            return None
        if self.amount_text:
            qty = parse_format(self.amount_text)
            if qty is None or p.normalized_price is None:
                return None
            return round(p.normalized_price * qty.amount, 2)
        return round(p.effective_price * self.quantity, 2)

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
    common_totals: dict[str, float] = field(default_factory=dict)  # solo voci presenti in tutte le insegne
    common_lines: int = 0


def _amount(it: BasketItem) -> str | None:
    return it.amount


def _norm(p: PricePoint) -> float:
    base = p.promo_price if p.promo_price is not None else p.price
    # il prezzo normalizzato e' calcolato sul prezzo effettivo al momento della creazione
    return p.normalized_price if p.normalized_price is not None else base


def compare(basket: Basket, points: list[PricePoint], stores: dict[str, StoreCfg]) -> Comparison:
    items: list[ItemResult] = []
    for it in basket.basket:
        cand = [p for p in points if p.basket_id == it.id and p.comparable
                and p.normalized_price is not None]
        want = parse_format(it.amount) if it.amount else None
        if want:
            cand = [p for p in cand if p.unit_kind == want.kind]  # l'unita' deve coincidere con amount
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
                                ranked[1] if len(ranked) > 1 else None, per_store, _amount(it)))

    all_stores = sorted({p.store for p in points})
    totals: dict[str, float] = {}
    incomplete: dict[str, list[str]] = {}
    for st in all_stores:
        missing = [i.label for i in items if st not in i.per_store]
        if missing:
            incomplete[st] = missing
            continue
        total = sum(i.cost(st) or 0.0 for i in items)
        totals[st] = round(total + _fee(stores, st), 2)
    common = [i for i in items if all(st in i.per_store for st in all_stores)] if all_stores else []
    common_totals = {st: round(sum(i.cost(st) or 0.0 for i in common), 2) for st in all_stores} if common else {}
    return Comparison(items, totals, incomplete, common_totals, len(common))


def _fee(stores: dict[str, StoreCfg], st: str) -> float:
    fee = stores.get(st, StoreCfg()).delivery_fee
    return float(fee) if isinstance(fee, (int, float)) else 0.0
