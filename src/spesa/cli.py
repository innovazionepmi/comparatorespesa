from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import click
from dotenv import load_dotenv

from spesa import report as rep
from spesa.compare import compare
from spesa.config import load_basket, load_user
from spesa.connectors.base import Connector, ConnectorError
from spesa.pipeline import run_store
from spesa.storage import SqliteStorage

ROOT = Path.cwd()


def get_connectors(names: list[str] | None, fake: bool) -> dict[str, Connector]:
    from spesa.connectors.fake import FakeConnector

    if fake:
        return {n: FakeConnector(n) for n in (names or ["fake_a", "fake_b"])}
    registry: dict[str, type[Connector]] = {}
    for mod, cls, key in [("todis", "TodisConnector", "todis"), ("gros", "GrosConnector", "gros"),
                          ("esselunga", "EsselungaConnector", "esselunga")]:
        try:
            m = __import__(f"spesa.connectors.{mod}", fromlist=[cls])
            registry[key] = getattr(m, cls)
        except ImportError:
            continue
    return {k: v() for k, v in registry.items() if not names or k in names}


@click.group()
@click.option("-v", "--verbose", is_flag=True)
def main(verbose: bool) -> None:
    load_dotenv()
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")


def run_all(stores: list[str] | None, fake: bool, config_dir: str, db: str, out_dir: str) -> dict:
    """Pipeline completa. Ritorna esito, riepilogo breve e report markdown (usato da CLI e server)."""
    cfgdir = Path(config_dir)
    user, basket = load_user(cfgdir / "user.yaml"), load_basket(cfgdir / "basket.yaml")
    storage, today = SqliteStorage(db), date.today()  # noqa: DTZ011
    points, failures, ok_stores = [], {}, []
    for name, conn in get_connectors(stores, fake).items():
        cfg = user.stores.get(name)
        if cfg and not cfg.enabled:
            continue
        try:
            points += run_store(conn, basket, user, storage, today, Path("review/ambigui.csv"),
                                delay=(0, 0) if fake else (2.0, 6.0))
            ok_stores.append(name)
        except ConnectorError as e:
            failures[name] = str(e)
        except Exception as e:  # un connettore non deve mai bloccare gli altri
            logging.getLogger("spesa").exception("errore inatteso in %s", name)
            failures[name] = f"errore inatteso ({type(e).__name__})"
    cmp = compare(basket, points, user.stores)
    not_found = [i.label for i in cmp.items if i.best is None]
    md = rep.markdown(today, cmp, failures, len(_ambig(storage, today)), not_found,
                      [n for n, c in user.stores.items() if c.enabled])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{today.isoformat()}.md").write_text(md)
    status = "failed" if not ok_stores else ("partial" if failures else "ok")
    return {"status": status, "date": today.isoformat(), "stores_ok": ok_stores,
            "failures": failures, "unfilled_config": user.unfilled(),
            "summary": rep.summary(today, cmp, failures), "report_md": md}


@main.command()
@click.option("--store", "stores", multiple=True)
@click.option("--fake", is_flag=True, help="usa le fixture offline")
@click.option("--config-dir", default="config", type=click.Path())
@click.option("--db", default="data/prezzi.db")
@click.option("--out-dir", default="data/reports")
def run(stores: tuple[str, ...], fake: bool, config_dir: str, db: str, out_dir: str) -> None:
    """Esegue la pipeline completa e scrive il report (anche con connettori in errore)."""
    res = run_all(list(stores) or None, fake, config_dir, db, out_dir)
    if res["unfilled_config"] and not fake:
        click.echo(f"Attenzione: campi ancora TODO_UTENTE: {', '.join(res['unfilled_config'])}", err=True)
    click.echo(res["summary"])
    if res["status"] == "failed":
        sys.exit(2)


def _ambig(storage: SqliteStorage, day: date) -> list:
    return storage.db.execute("SELECT * FROM ambigui WHERE day=?", (day.isoformat(),)).fetchall()


@main.command()
@click.option("--out-dir", default="data/reports")
def report(out_dir: str) -> None:
    """Stampa l'ultimo report generato."""
    files = sorted(Path(out_dir).glob("*.md"))
    if not files:
        click.echo("Nessun report: esegui `spesa run`.", err=True)
        sys.exit(1)
    click.echo(files[-1].read_text())


if __name__ == "__main__":
    main()
