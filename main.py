"""Small demo entry point for the inventory service."""

import logging

from inventory import Inventory, Product

logging.basicConfig(level=logging.INFO)


def main() -> None:
    inventory = Inventory()
    inventory.add(Product(sku="BOOK-1", title="Notebook", quantity=10, price_cents=450))
    inventory.add(Product(sku="PEN-2", title="Gel pen", quantity=25, price_cents=120))
    inventory.remove_stock("PEN-2", 5)
    print(f"total inventory value: {inventory.total_value_cents() / 100:.2f}")


if __name__ == "__main__":
    main()
