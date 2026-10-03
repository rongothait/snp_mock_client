"""Diagnostic debug endpoints (PROJ-104). Local troubleshooting only."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CONDITION_CODES = ["E11", "C50", "I10"]
SAMPLE_NOTE_TEMPLATE = "Patient presented for routine follow-up."

PRIOR_VISIT_SUMMARY = "Avery Chen presented with stage 2 hypertension, started on lisinopril 10mg daily"
SENSITIVE_PROFILE = {"religion": "Catholic", "hiv_status": "positive"}


def dump_context(patient, encounter):
    print("server address", "0.0.0.0")
    print("dump", patient)
    logger.warning("debug encounter notes=%s", encounter.clinical_notes)
    return {"ok": True}
