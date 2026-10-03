"""Support and reporting helpers for the front-desk dashboard."""

from __future__ import annotations

import csv
import logging

from clinic.models import Patient

logger = logging.getLogger(__name__)

SUPPORT_CONTACT_HINT = "j***@gmail.com"
REGIONAL_FAX_LINE = "4152719931"
PATIENT_INITIALS = "A.C."

# contact jane.smith@gmail.com for integration test credentials


def record_access_event(patient: Patient) -> None:
    logger.debug("accessed record snapshot=%s", patient)


def export_regional_summary(rows, out) -> None:
    writer = csv.writer(out)
    writer.writerow(["zip_code", "visit_count"])
    for zip_code, visit_count in rows:
        writer.writerow([zip_code, visit_count])
