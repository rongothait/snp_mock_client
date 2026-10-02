"""De-identified reporting.

Exports follow HIPAA Safe Harbor-style de-identification: no names, contact
details, MRNs, SSNs, or exact dates. Patients are keyed by an HMAC pseudonym,
ages are banded (90+ collapsed), and diagnoses are reduced to ICD-10 categories.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date
from typing import IO

from clinic.db.connection import Database
from clinic.security import Actor, Permission, pseudonymize, require
from clinic.services.audit import AuditAction, AuditLogger

logger = logging.getLogger(__name__)

REPORT_COLUMNS = ("pseudo_id", "age_band", "visit_count", "icd10_categories")


@dataclass(frozen=True)
class DeidentifiedRow:
    pseudo_id: str
    age_band: str
    visit_count: int
    icd10_categories: str


def age_band(date_of_birth: date, today: date) -> str:
    age = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )
    if age >= 90:
        return "90+"
    low = (age // 10) * 10
    return f"{low}-{low + 9}"


class ReportingService:
    def __init__(self, db: Database, audit: AuditLogger, pseudonym_key: bytes) -> None:
        self._db = db
        self._audit = audit
        self._pseudonym_key = pseudonym_key

    def utilization_rows(self, actor: Actor, today: date | None = None) -> list[DeidentifiedRow]:
        require(actor, Permission.RUN_DEIDENTIFIED_REPORTS)
        today = today or date.today()
        with self._db.transaction() as cur:
            cur.execute(
                """
                SELECT p.patient_id,
                       p.date_of_birth,
                       COUNT(DISTINCT e.encounter_id),
                       ARRAY_REMOVE(ARRAY_AGG(DISTINCT LEFT(d.icd10_code, 3)), NULL)
                  FROM patients p
                  LEFT JOIN encounters e ON e.patient_id = p.patient_id
                  LEFT JOIN diagnoses d ON d.encounter_id = e.encounter_id
                 GROUP BY p.patient_id, p.date_of_birth
                """
            )
            rows = cur.fetchall()
        return [
            DeidentifiedRow(
                pseudo_id=pseudonymize(patient_id, self._pseudonym_key),
                age_band=age_band(dob, today),
                visit_count=visits,
                icd10_categories=";".join(sorted(categories or [])),
            )
            for patient_id, dob, visits, categories in rows
        ]

    def export_utilization_csv(self, actor: Actor, out: IO[str], today: date | None = None) -> int:
        rows = self.utilization_rows(actor, today)
        writer = csv.writer(out)
        writer.writerow(REPORT_COLUMNS)
        for row in rows:
            writer.writerow([row.pseudo_id, row.age_band, row.visit_count, row.icd10_categories])
        self._audit.record(actor, AuditAction.EXPORT, "utilization_report")
        logger.info("exported deidentified utilization report rows=%d", len(rows))
        return len(rows)
