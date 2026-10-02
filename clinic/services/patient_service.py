"""Patient registration and demographic access."""

from __future__ import annotations

import logging

from clinic.models import InsuranceCoverage, Patient
from clinic.repositories.patients import PatientRepository
from clinic.security import Actor, Permission, require
from clinic.services.audit import AuditAction, AuditLogger

logger = logging.getLogger(__name__)


class PatientNotFound(LookupError):
    pass


class PatientService:
    def __init__(self, patients: PatientRepository, audit: AuditLogger) -> None:
        self._patients = patients
        self._audit = audit

    def register(self, actor: Actor, patient: Patient, ssn: str | None = None) -> str:
        require(actor, Permission.WRITE_DEMOGRAPHICS)
        self._patients.insert(patient, ssn=ssn)
        self._audit.record(actor, AuditAction.CREATE, "patient", patient.patient_id)
        logger.info("registered patient_id=%s", patient.patient_id)
        return patient.patient_id

    def get(self, actor: Actor, patient_id: str) -> Patient:
        require(actor, Permission.READ_DEMOGRAPHICS)
        patient = self._patients.get(patient_id)
        if patient is None:
            raise PatientNotFound(f"patient_id={patient_id}")
        self._audit.record(actor, AuditAction.VIEW, "patient", patient_id)
        return patient

    def get_ssn(self, actor: Actor, patient_id: str) -> str | None:
        require(actor, Permission.READ_SSN)
        ssn = self._patients.get_ssn(patient_id)
        self._audit.record(actor, AuditAction.VIEW, "patient_ssn", patient_id)
        return ssn

    def update_contact(self, actor: Actor, patient_id: str, **changes: str | None) -> None:
        require(actor, Permission.WRITE_DEMOGRAPHICS)
        self._patients.update_contact(patient_id, **changes)
        self._audit.record(actor, AuditAction.UPDATE, "patient", patient_id)
        logger.info(
            "updated contact patient_id=%s fields=%s",
            patient_id,
            sorted(k for k, v in changes.items() if v is not None),
        )

    def add_coverage(self, actor: Actor, coverage: InsuranceCoverage) -> None:
        require(actor, Permission.WRITE_DEMOGRAPHICS)
        self._patients.add_coverage(coverage)
        self._audit.record(actor, AuditAction.CREATE, "insurance_coverage", coverage.patient_id)
