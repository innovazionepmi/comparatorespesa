"""Matching deterministico voce paniere -> prodotti. I casi dubbi vanno in review/ambigui.csv."""
from __future__ import annotations

from dataclasses import dataclass

from spesa.config import BasketItem
from spesa.models import Product
from spesa.normalize import parse_format


@dataclass
class MatchResult:
    status: str  # "match" | "ambiguo" | "scartato"
    reason: str
    comparable: bool = True


def _has(text: str, kw: str) -> bool:
    return kw.lower() in text.lower()


def match(item: BasketItem, p: Product) -> MatchResult:
    text = f"{p.name} {p.brand or ''}"
    if not p.available:
        return MatchResult("scartato", "non disponibile")
    if any(_has(text, k) for k in item.accept.must_exclude):
        return MatchResult("scartato", "keyword esclusa")
    missing = [k for k in item.accept.must_include if not _has(text, k)]
    if missing:
        return MatchResult("scartato", f"manca keyword: {missing[0]}")

    brand_ok = any(_has(text, b) for b in item.accept.brands)
    if item.accept.brands and not brand_ok:
        if not item.allow_private_label:
            return MatchResult("scartato", "marca non accettata")
        return MatchResult("ambiguo", "marca non in lista (marca del distributore o altro?)")

    want, got = parse_format(item.unit_hint), parse_format(p.format_text)
    if want is None:
        return MatchResult("match", "ok", comparable=got is not None)
    if got is None:
        return MatchResult("ambiguo", "formato non riconosciuto", comparable=False)
    if got.kind != want.kind:
        return MatchResult("ambiguo", f"unita' diversa ({got.kind} vs {want.kind})", comparable=False)
    scarto = abs(got.amount - want.amount) / want.amount * 100
    if scarto > item.size_tolerance_pct:
        return MatchResult("ambiguo", f"formato fuori tolleranza ({scarto:.0f}%)", comparable=False)
    return MatchResult("match", "ok", comparable=True)
