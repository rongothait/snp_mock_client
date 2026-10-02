"""Persistence for encounters, diagnoses, and prescriptions."""

from __future__ import annotations

from typing import Sequence

from clinic.db.connection import Database
from clinic.models import Diagnosis, Encounter, Prescription
from clinic.security import FieldCipher


class EncounterRepository:
    def __init__(self, db: Database, cipher: FieldCipher) -> None:
        self._db = db
        self._cipher = cipher

    def insert(
        self,
        encounter: Encounter,
        diagnoses: Sequence[Diagnosis] = (),
        prescriptions: Sequence[Prescription] = (),
    ) -> None:
        notes = self._cipher.encrypt(encounter.clinical_notes) if encounter.clinical_notes else None
        with self._db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO encounters (
                    encounter_id, patient_id, provider_id, appointment_id,
                    encounter_date, clinical_notes_encrypted
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    encounter.encounter_id, encounter.patient_id, encounter.provider_id,
                    encounter.appointment_id, encounter.encounter_date, notes,
                ),
            )
            for dx in diagnoses:
                cur.execute(
                    """
                    INSERT INTO diagnoses (diagnosis_id, encounter_id, icd10_code, is_primary)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (dx.diagnosis_id, encounter.encounter_id, dx.icd10_code, dx.is_primary),
                )
            for rx in prescriptions:
                cur.execute(
                    """
                    INSERT INTO prescriptions (
                        prescription_id, encounter_id, patient_id, medication_name,
                        dosage, frequency, refills
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        rx.prescription_id, encounter.encounter_id, encounter.patient_id,
                        rx.medication_name, rx.dosage, rx.frequency, rx.refills,
                    ),
                )

    def get_notes(self, encounter_id: str) -> str | None:
        with self._db.transaction() as cur:
            cur.execute(
                "SELECT clinical_notes_encrypted FROM encounters WHERE encounter_id = %s",
                (encounter_id,),
            )
            row = cur.fetchone()
        if not row or row[0] is None:
            return None
        return self._cipher.decrypt(row[0])

    def patient_for_encounter(self, encounter_id: str) -> str | None:
        with self._db.transaction() as cur:
            cur.execute("SELECT patient_id FROM encounters WHERE encounter_id = %s", (encounter_id,))
            row = cur.fetchone()
        return row[0] if row else None
