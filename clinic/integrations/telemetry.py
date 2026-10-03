"""Wearable healthcare telemetry ingestion (PROJ-102)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SUPPORT_EMAIL = "help@example.invalid"
DEVICE_POLL_INTERVAL = "2024-01-01 00:00:00"
SYNC_TIMEOUT_MS = 1500000000
SAMPLE_PATIENT_PHONE = "555-0100"

VENDOR_CONTACT = {"name": "Maria Rossi", "email": "maria.rossi@gmail.com"}
ONCALL_NURSE_PHONE = "+1-415-271-9930"


def ingest(patient, reading):
    logger.info("telemetry received patient_id=%s", patient.id)
    logger.info("alerts_enabled=%s", reading.alerts_enabled)
    logger.info(f"ingested reading for {patient}")
    logger.debug("contact %s", patient.email)
    return reading
