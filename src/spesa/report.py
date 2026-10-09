from __future__ import annotations

from datetime import date

from spesa.compare import Comparison


def _eur(x: float | None) -> str:
    return "-" if x is None else f"{x:.2f} €"


def markdown(day: date, cmp: Comparison, failures: dict[str, str], ambigui: int,
             not_found: list[str]) -> str:
    out = [f"# Report spesa {day.isoformat()}", ""]
    for s, why in failures.items():
        out.append(f"> ⚠️ Insegna **{s}** non disponibile oggi: {why}")
    if failures:
        out.append("")
    out += ["| Voce | Migliore | Dove | €/unità | Costo stimato | Vs seconda |", "|---|---|---|---|---|---|"]
    for i in cmp.items:
        if not i.best:
            out.append(f"| {i.label} | non trovato | - | - | - | - |")
            continue
        b = i.best
        sv = i.saving_vs_second
        out.append(f"| {i.label} | {b.name} | {b.store} | {_eur(b.normalized_price)}/{b.unit_kind} "
                   f"| {_eur(i.cost(b.store))} | {'-' if sv is None else f'-{sv:.2f} €/{b.unit_kind}'} |")
    out += ["", "## Totale per insegna (paniere completo + consegna)", ""]
    for s, t in sorted(cmp.totals.items(), key=lambda kv: kv[1]):
        out.append(f"- {s}: {_eur(t)}")
    for s, miss in cmp.incomplete.items():
        out.append(f"- {s}: paniere incompleto, mancano {len(miss)} voci: {', '.join(miss)}")
    if cmp.common_totals:
        out += ["", f"## Confronto equo sulle {cmp.common_lines} voci presenti in tutte le insegne", ""]
        for s, t in sorted(cmp.common_totals.items(), key=lambda kv: kv[1]):
            out.append(f"- {s}: {_eur(t)}")
    out += ["", "## Avvisi", f"- Casi ambigui da rivedere: {ambigui} (review/ambigui.csv)"]
    if not_found:
        out.append(f"- Voci senza risultati: {', '.join(not_found)}")
    out.append("- Confronto sul prezzo normalizzato (€/kg, €/l, €/pezzo); prezzi promo inclusi.")
    return "\n".join(out) + "\n"


def summary(day: date, cmp: Comparison, failures: dict[str, str]) -> str:
    lines = [f"Spesa {day.isoformat()}"]
    if cmp.totals:
        best = min(cmp.totals, key=lambda k: cmp.totals[k])
        lines.append(f"Vince {best}: {_eur(cmp.totals[best])} (paniere completo)")
    elif cmp.common_totals:
        best = min(cmp.common_totals, key=lambda k: cmp.common_totals[k])
        lines.append(f"Vince {best} sulle {cmp.common_lines} voci comuni: " + ", ".join(
            f"{k} {_eur(v)}" for k, v in sorted(cmp.common_totals.items(), key=lambda kv: kv[1])))
    for i in cmp.items[:8]:
        if i.best:
            lines.append(f"- {i.label[:28]}: {i.best.store} {_eur(i.cost(i.best.store))}")
    for s, why in failures.items():
        lines.append(f"! {s} non disponibile: {why}")
    return "\n".join(lines[:15])
