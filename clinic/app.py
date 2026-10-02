"""Wires repositories and services together."""

from __future__ import annotations

from dataclasses import dataclass

from clinic.config import AppConfig
from clinic.db.connection import Database
from clinic.repositories import AppointmentRepository, EncounterRepository, PatientRepository
from clinic.security import FieldCipher
from clinic.services.audit import AuditLogger
from clinic.services.clinical_service import ClinicalService
from clinic.services.patient_service import PatientService
from clinic.services.reporting import ReportingService


@dataclass
class Clinic:
    db: Database
    patients: PatientService
    clinical: ClinicalService
    reporting: ReportingService

    @classmethod
    def build(cls, config: AppConfig, db: Database | None = None) -> Clinic:
        db = db or Database(config.db)
        cipher = FieldCipher(config.field_key)
        audit = AuditLogger(db)
        return cls(
            db=db,
            patients=PatientService(PatientRepository(db, cipher), audit),
            clinical=ClinicalService(
                AppointmentRepository(db), EncounterRepository(db, cipher), audit
            ),
            reporting=ReportingService(db, audit, config.pseudonym_key),
        )
