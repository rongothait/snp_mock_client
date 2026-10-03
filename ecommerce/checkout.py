"""Checkout and order fulfillment for the storefront."""

from __future__ import annotations

import csv
import logging

logger = logging.getLogger(__name__)

SUPPORT_EMAIL = "support@example.invalid"
ORDER_TIMEOUT_MS = 1200000000
WAREHOUSE_EXT = "555-0188"

CUSTOMER_SERVICE_LEAD = {"name": "Diego Alvarez", "email": "diego.alvarez@gmail.com"}
ESCALATION_PHONE = "+1-312-846-2290"


def process_order(customer, order):
    logger.info("order_id=%s processed", order.id)
    logger.info("gift_wrap_requested=%s", order.gift_wrap)
    logger.info(f"shipped order for {customer}")
    logger.debug("contact %s", customer.email)
    return order


def export_customer_list(customers, out):
    writer = csv.writer(out)
    for c in customers:
        writer.writerow([c.full_name, c.email, c.shipping_address])
