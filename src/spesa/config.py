from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class Accept(BaseModel):
    brands: list[str] = []
    must_include: list[str] = []
    must_exclude: list[str] = []


class BasketItem(BaseModel):
    id: str
    label: str
    quantity: float = 1
    unit_hint: str
    accept: Accept = Accept()
    size_tolerance_pct: float = 25
    allow_private_label: bool = True


class Basket(BaseModel):
    basket: list[BasketItem] = Field(min_length=1)

    @field_validator("basket")
    @classmethod
    def unique_ids(cls, v: list[BasketItem]) -> list[BasketItem]:
        ids = [i.id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("id duplicati nel paniere")
        return v


class Address(BaseModel):
    street: str
    cap: str
    city: str


class StoreCfg(BaseModel):
    enabled: bool = True
    delivery_fee: float | str = 0.0
    min_order: float | str = 0.0


class UserCfg(BaseModel):
    address: Address
    service: str = "delivery"
    stores: dict[str, StoreCfg] = {}

    def unfilled(self) -> list[str]:
        """Campi ancora a TODO_UTENTE."""
        out = [f"address.{k}" for k, v in self.address.model_dump().items() if "TODO_UTENTE" in str(v)]
        for name, s in self.stores.items():
            for k in ("delivery_fee", "min_order"):
                if "TODO_UTENTE" in str(getattr(s, k)):
                    out.append(f"stores.{name}.{k}")
        return out


def load_basket(path: Path) -> Basket:
    return Basket.model_validate(yaml.safe_load(path.read_text()))


def load_user(path: Path) -> UserCfg:
    return UserCfg.model_validate(yaml.safe_load(path.read_text()))
