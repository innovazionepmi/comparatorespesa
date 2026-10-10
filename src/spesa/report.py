from __future__ import annotations

from datetime import date

from spesa.compare import Comparison, ItemResult
from spesa.models import PricePoint


def _eur(x: float | None) -> str:
    return "-" if x is None else f"{x:.2f}".replace(".", ",") + " €"


def _cell(p: PricePoint | None) -> str:
    if p is None:
        return "non trovato"
    unit = f" ({_eur(p.normalized_price)}/{p.unit_kind})" if p.normalized_price else ""
    old = f", era {_eur(p.price)}" if p.promo_price is not None else ""
    fmt = f" {p.format_text}" if p.format_text else ""
    return f"{p.name}{fmt}: **{_eur(p.effective_price)}**{unit}{old}"


def _verdict(i: ItemResult) -> str:
    if i.winner:
        pct = i.saving_pct
        return f"**{i.winner}**" + (f" (-{pct:.0f}% al {i.best.unit_kind})" if pct and i.best else "")
    if i.best and i.second:
        return "pari"
    if i.best:
        return f"solo {i.best.store}"
    return "-"


def _offers(i: ItemResult) -> str:
    notes = [f"{s}: {p.promo_note}" for s, p in sorted(i.per_store.items()) if p.promo_note]
    return "; ".join(notes) or "-"


def tally(cmp: Comparison) -> dict[str, int]:
    out: dict[str, int] = {}
    for i in cmp.items:
        key = i.winner or ("pari" if i.best and i.second else ("solo " + i.best.store if i.best else "non trovato"))
        out[key] = out.get(key, 0) + 1
    return out


def markdown(day: date, cmp: Comparison, failures: dict[str, str], ambigui: int,
             not_found: list[str], stores: list[str] | None = None) -> str:
    cols = sorted(set(stores or []) | {s for i in cmp.items for s in i.per_store} | set(failures))
    out = [f"# Dove conviene comprare - {day.isoformat()}", ""]
    for s, why in failures.items():
        out.append(f"> ⚠️ **{s}** non disponibile oggi ({why}): la colonna resta vuota e non c'è confronto con questa insegna.")
    if failures:
        out.append("")
    t = tally(cmp)
    out.append("Riepilogo: " + ", ".join(f"{k}: {v}" for k, v in sorted(t.items(), key=lambda kv: -kv[1])) + ".")
    out += ["", "| Prodotto | " + " | ".join(cols) + " | Conviene | Offerte |",
            "|---|" + "---|" * len(cols) + "---|---|"]
    for i in cmp.items:
        cells = [(_cell(i.per_store.get(c)) if c not in failures else "n/d") for c in cols]
        out.append(f"| {i.label} | " + " | ".join(cells) + f" | {_verdict(i)} | {_offers(i)} |")
    out += ["", "## Avvisi", f"- Casi ambigui da rivedere: {ambigui} (review/ambigui.csv)"]
    if not_found:
        out.append(f"- Prodotti non trovati in nessuna insegna: {', '.join(not_found)}")
    out.append("- Il confronto è sul prezzo al kg/litro/pezzo del prodotto più economico che rispetta le regole "
               "del paniere in ciascuna insegna; promozioni incluse. Controlla che i prodotti messi a confronto siano equivalenti.")
    return "\n".join(out) + "\n"


def summary(day: date, cmp: Comparison, failures: dict[str, str]) -> str:
    """Riepilogo breve per telefono (max 15 righe)."""
    lines = [f"Spesa {day.isoformat()}"]
    t = tally(cmp)
    lines.append(", ".join(f"{k}: {v}" for k, v in sorted(t.items(), key=lambda kv: -kv[1])))
    wins = sorted((i for i in cmp.items if i.winner and i.saving_pct), key=lambda i: -(i.saving_pct or 0))
    for i in wins[:6]:
        lines.append(f"- {i.label[:30]}: {i.winner} (-{i.saving_pct:.0f}%)")
    promos = [i for i in cmp.items if any(p.promo_note for p in i.per_store.values())]
    if promos:
        lines.append(f"Offerte attive su {len(promos)} prodotti (vedi report)")
    for s, why in failures.items():
        lines.append(f"! {s} non disponibile: {why[:60]}")
    return "\n".join(lines[:15])
