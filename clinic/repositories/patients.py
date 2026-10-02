"""Persistence for patients and their insurance coverage."""

from __future__ import annotations

from clinic.db.connection import Database
from clinic.models import InsuranceCoverage, Patient
from clinic.security import FieldCipher

# Explicit column list: SSN ciphertext is never selected with demographics.
_DEMOGRAPHIC_COLUMNS = (
    "patient_id", "mrn", "first_name", "last_name", "date_of_birth", "sex",
    "email", "phone", "address_line1", "city", "state", "postal_code", "ssn_last4",
)


def _patient_from_row(row: tuple) -> Patient:
    values = dict(zip(_DEMOGRAPHIC_COLUMNS, row))
    return Patient(**values)


class PatientRepository:
    def __init__(self, db: Database, cipher: FieldCipher) -> None:
        self._db = db
        self._cipher = cipher

    def insert(self, patient: Patient, ssn: str | None = None) -> None:
        ssn_encrypted = self._cipher.encrypt(ssn) if ssn else None
        ssn_last4 = ssn[-4:] if ssn else None
        patient.ssn_last4 = ssn_last4
        with self._db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO patients (
                    patient_id, mrn, first_name, last_name, date_of_birth, sex,
                    email, phone, address_line1, city, state, postal_code,
                    ssn_encrypted, ssn_last4
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    patient.patient_id, patient.mrn, patient.first_name, patient.last_name,
                    patient.date_of_birth, patient.sex, patient.email, patient.phone,
                    patient.address_line1, patient.city, patient.state, patient.postal_code,
                    ssn_encrypted, ssn_last4,
                ),
            )

    def get(self, patient_id: str) -> Patient | None:
        with self._db.transaction() as cur:
            cur.execute(
                f"SELECT {', '.join(_DEMOGRAPHIC_COLUMNS)} FROM patients WHERE patient_id = %s",
                (patient_id,),
            )
            row = cur.fetchone()
        return _patient_from_row(row) if row else None

    def get_ssn(self, patient_id: str) -> str | None:
        with self._db.transaction() as cur:
            cur.execute("SELECT ssn_encrypted FROM patients WHERE patient_id = %s", (patient_id,))
            row = cur.fetchone()
        if not row or row[0] is None:
            return None
        return self._cipher.decrypt(row[0])

    def update_contact(
        self,
        patient_id: str,
        *,
        email: str | None = None,
        phone: str | None = None,
        address_line1: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
    ) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                """
                UPDATE patients
                   SET email = COALESCE(%s, email),
                       phone = COALESCE(%s, phone),
                       address_line1 = COALESCE(%s, address_line1),
                       city = COALESCE(%s, city),
                       state = COALESCE(%s, state),
                       postal_code = COALESCE(%s, postal_code),
                       updated_at = now()
                 WHERE patient_id = %s
                """,
                (email, phone, address_line1, city, state, postal_code, patient_id),
            )

    def add_coverage(self, coverage: InsuranceCoverage) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO insurance_coverage (
                    coverage_id, patient_id, payer_name, member_id_encrypted,
                    group_number, effective_date, termination_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    coverage.coverage_id, coverage.patient_id, coverage.payer_name,
                    self._cipher.encrypt(coverage.member_id), coverage.group_number,
                    coverage.effective_date, coverage.termination_date,
                ),
            )
