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
BASKET = Path(__file__).parent / "fixtures" / "basket_test.yaml"


def test_basket_valid():
    assert len(load_basket(CFG / "basket.yaml").basket) >= 20
    assert len(load_basket(BASKET).basket) == 4


def test_match_rules():
    item = load_basket(BASKET).basket[0]
    ok = Product(store="x", store_product_id="1", name="Cereali Cheerios", brand="CHEERIOS",
                 format_text="500 g", price=3)
    bar = ok.model_copy(update={"name": "Barrette ai cereali"})
    big = ok.model_copy(update={"format_text": "1 kg"})
    assert match(item, ok).status == "match"
    assert match(item, bar).status == "scartato"
    assert match(item, big).status == "ambiguo"


def test_end_to_end(tmp_path):
    basket, user = load_basket(BASKET), load_user(CFG / "user.example.yaml")
    st, day, pts = SqliteStorage(":memory:"), date(2026, 1, 1), []
    for n in ("fake_a", "fake_b"):
        pts += run_store(FakeConnector(n), basket, user, st, day, tmp_path / "amb.csv", delay=(0, 0))
    cmp = compare(basket, pts, user.stores)
    by = {i.basket_id: i for i in cmp.items}
    assert by["pasta_penne"].best.store == "fake_a"  # promo 1.20 < 1.50
    assert by["latte_ul"].best.store == "fake_b"
    assert (tmp_path / "amb.csv").exists()  # 375g vs 500g fuori tolleranza -> ambiguo
    assert set(cmp.totals) | set(cmp.incomplete) == {"fake_a", "fake_b"}


def test_free_format_and_brand_filter():
    item = load_basket(BASKET).basket[3]
    rummo = Product(store="x", store_product_id="1", name="Penne Rigate", brand="Rummo",
                    format_text="1 kg", price=2)
    other = rummo.model_copy(update={"brand": "Barilla"})
    assert match(item, rummo).status == "match"  # nessun vincolo di formato
    assert match(item, other).status == "scartato"  # marche non in lista: scartate, non ambigue


def test_amount_cost_and_must_include_any():
    from spesa.config import BasketItem
    from spesa.models import PricePoint

    it = BasketItem(id="x", label="X", amount="2 kg", accept={"must_include_any": ["surgel", "sofficin"]})
    ok = Product(store="s", store_product_id="1", name="Sofficini prosciutto", format_text="300 g", price=2)
    no = ok.model_copy(update={"name": "Pizza fresca"})
    assert match(it, ok).status == "match" and match(it, no).status == "scartato"
    pp = PricePoint(day=date(2026, 1, 1), store="s", store_product_id="1", name="n", brand=None,
                    format_text="500 g", price=1.0, promo_price=None, normalized_price=2.0, unit_kind="kg",
                    available=True, url=None, basket_id="x")
    from spesa.compare import ItemResult
    r = ItemResult("x", "X", 1, pp, None, {"s": pp}, "2 kg")
    assert r.cost("s") == 4.0  # 2 EUR/kg x 2 kg, indipendente dal formato della confezione
