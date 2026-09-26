"""In-memory product inventory."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Product:
    sku: str
    title: str
    quantity: int
    price_cents: int


class Inventory:
    def __init__(self) -> None:
        self._products: dict[str, Product] = {}

    def add(self, product: Product) -> None:
        self._products[product.sku] = product
        logger.info("added sku=%s quantity=%d", product.sku, product.quantity)

    def remove_stock(self, sku: str, amount: int) -> None:
        product = self._products[sku]
        if amount > product.quantity:
            raise ValueError(f"not enough stock for sku={sku}")
        product.quantity -= amount
        logger.info("removed sku=%s amount=%d", sku, amount)

    def total_value_cents(self) -> int:
        return sum(p.quantity * p.price_cents for p in self._products.values())
