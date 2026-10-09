"""Parsing dei formati e calcolo del prezzo normalizzato (EUR/kg, EUR/l, EUR/pezzo)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from spesa.models import UnitKind

_UNITS = {"kg": ("kg", 1.0), "g": ("kg", 0.001), "gr": ("kg", 0.001), "mg": ("kg", 1e-6),
          "l": ("l", 1.0), "lt": ("l", 1.0), "ltr": ("l", 1.0), "dl": ("l", 0.1),
          "cl": ("l", 0.01), "ml": ("l", 0.001),
          "pz": ("pz", 1.0), "pezzi": ("pz", 1.0), "pz.": ("pz", 1.0)}
_NUM = r"(\d+(?:[.,]\d+)?)"
_MULTI = re.compile(rf"(\d+)\s*[x×]\s*{_NUM}\s*([a-zA-Z.]+)", re.IGNORECASE)
_SINGLE = re.compile(rf"{_NUM}\s*([a-zA-Z.]+)", re.IGNORECASE)


@dataclass(frozen=True)
class Quantity:
    kind: UnitKind
    amount: float  # in kg, l o pezzi totali


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_format(text: str | None) -> Quantity | None:
    """'500 g' -> 0.5 kg; '6x125g' -> 0.75 kg; '1,5 l' -> 1.5 l. None se non riconosciuto."""
    if not text:
        return None
    m = _MULTI.search(text)
    if m:
        unit = _UNITS.get(m.group(3).lower())
        if unit:
            return Quantity(unit[0], int(m.group(1)) * _num(m.group(2)) * unit[1])  # type: ignore[arg-type]
    for m in _SINGLE.finditer(text):
        unit = _UNITS.get(m.group(2).lower())
        if unit:
            return Quantity(unit[0], _num(m.group(1)) * unit[1])  # type: ignore[arg-type]
    return None


def normalized_price(price: float, qty: Quantity | None) -> float | None:
    if qty is None or qty.amount <= 0:
        return None
    return round(price / qty.amount, 4)
