"""Scheduling and clinical documentation."""

from __future__ import annotations

import logging
from typing import Sequence

from clinic.models import Appointment, Diagnosis, Encounter, Prescription
from clinic.repositories.appointments import AppointmentRepository
from clinic.repositories.encounters import EncounterRepository
from clinic.security import Actor, Permission, require
from clinic.services.audit import AuditAction, AuditLogger

logger = logging.getLogger(__name__)


class ClinicalService:
    def __init__(
        self,
        appointments: AppointmentRepository,
        encounters: EncounterRepository,
        audit: AuditLogger,
    ) -> None:
        self._appointments = appointments
        self._encounters = encounters
        self._audit = audit

    def book_appointment(self, actor: Actor, appointment: Appointment) -> str:
        require(actor, Permission.MANAGE_SCHEDULE)
        self._appointments.insert(appointment)
        self._audit.record(actor, AuditAction.CREATE, "appointment", appointment.patient_id)
        logger.info(
            "booked appointment_id=%s provider_id=%s",
            appointment.appointment_id,
            appointment.provider_id,
        )
        return appointment.appointment_id

    def record_encounter(
        self,
        actor: Actor,
        encounter: Encounter,
        diagnoses: Sequence[Diagnosis] = (),
        prescriptions: Sequence[Prescription] = (),
    ) -> str:
        require(actor, Permission.WRITE_CLINICAL)
        self._encounters.insert(encounter, diagnoses, prescriptions)
        if encounter.appointment_id:
            self._appointments.update_status(encounter.appointment_id, "completed")
        self._audit.record(actor, AuditAction.CREATE, "encounter", encounter.patient_id)
        logger.info(
            "recorded encounter_id=%s diagnoses=%d prescriptions=%d",
            encounter.encounter_id,
            len(diagnoses),
            len(prescriptions),
        )
        return encounter.encounter_id

    def read_notes(self, actor: Actor, encounter_id: str) -> str | None:
        require(actor, Permission.READ_CLINICAL)
        patient_id = self._encounters.patient_for_encounter(encounter_id)
        notes = self._encounters.get_notes(encounter_id)
        self._audit.record(actor, AuditAction.VIEW, "clinical_notes", patient_id)
        return notes
