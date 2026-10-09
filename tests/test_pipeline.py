from datetime import date
from pathlib import Path

from spesa.compare import compare
from spesa.config import load_basket, load_user
from spesa.connectors.fake import FakeConnector
from spesa.matcher import match
from spesa.models import Product
from spesa.pipeline import run_store
from spesa.storage import SqliteStorage

CFG = Path(__file__).resolve().parents[1] / "config"


def test_basket_valid():
    assert len(load_basket(CFG / "basket.yaml").basket) == 3


def test_match_rules():
    item = load_basket(CFG / "basket.yaml").basket[0]
    ok = Product(store="x", store_product_id="1", name="Cereali Cheerios", brand="CHEERIOS",
                 format_text="500 g", price=3)
    bar = ok.model_copy(update={"name": "Barrette ai cereali"})
    big = ok.model_copy(update={"format_text": "1 kg"})
    assert match(item, ok).status == "match"
    assert match(item, bar).status == "scartato"
    assert match(item, big).status == "ambiguo"


def test_end_to_end(tmp_path):
    basket, user = load_basket(CFG / "basket.yaml"), load_user(CFG / "user.example.yaml")
    st, day, pts = SqliteStorage(":memory:"), date(2026, 1, 1), []
    for n in ("fake_a", "fake_b"):
        pts += run_store(FakeConnector(n), basket, user, st, day, tmp_path / "amb.csv", delay=(0, 0))
    cmp = compare(basket, pts, user.stores)
    by = {i.basket_id: i for i in cmp.items}
    assert by["pasta_penne"].best.store == "fake_a"  # promo 1.20 < 1.50
    assert by["latte_ul"].best.store == "fake_b"
    assert (tmp_path / "amb.csv").exists()  # 375g vs 500g fuori tolleranza -> ambiguo
    assert set(cmp.totals) | set(cmp.incomplete) == {"fake_a", "fake_b"}
