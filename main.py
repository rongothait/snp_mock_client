"""Demo run of the clinic system against the mock database connection.

All patient data here is synthetic. Output shows only IDs, counts, and the
de-identified report.
"""

import logging
import sys
from datetime import date, datetime, timezone

from clinic.app import Clinic
from clinic.config import AppConfig
from clinic.db.schema import create_all
from clinic.models import Appointment, Diagnosis, Encounter, Patient, Provider
from clinic.security import Actor, Role

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    config = AppConfig.from_env()
    clinic = Clinic.build(config)
    create_all(clinic.db)

    front_desk = Actor(user_id="staff-0001", role=Role.FRONT_DESK)
    physician = Actor(user_id="staff-0002", role=Role.PHYSICIAN)
    analyst = Actor(user_id="staff-0003", role=Role.ANALYST)

    provider = Provider(npi="0000000000", first_name="Demo", last_name="Provider", specialty="family_medicine")

    patient = Patient(
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(2000, 1, 1),
        sex="unknown",
        mrn="TEST-0001",
        email="test.patient@example.invalid",
        phone="555-0100",
    )
    patient_id = clinic.patients.register(front_desk, patient)

    appointment_id = clinic.clinical.book_appointment(
        front_desk,
        Appointment(
            patient_id=patient_id,
            provider_id=provider.provider_id,
            scheduled_at=datetime(2030, 1, 1, 9, 0, tzinfo=timezone.utc),
            reason="routine visit",
        ),
    )

    encounter = Encounter(
        patient_id=patient_id,
        provider_id=provider.provider_id,
        appointment_id=appointment_id,
        encounter_date=datetime(2030, 1, 1, 9, 5, tzinfo=timezone.utc),
        clinical_notes="Synthetic demo note.",
    )
    clinic.clinical.record_encounter(
        physician,
        encounter,
        diagnoses=[Diagnosis(encounter_id=encounter.encounter_id, icd10_code="Z00.00", is_primary=True)],
    )

    # The mock connection has no data; queue what the aggregate query would return.
    clinic.db.connection.queue_result([(patient_id, patient.date_of_birth, 1, ["Z00"])])
    clinic.reporting.export_utilization_csv(analyst, sys.stdout, today=date(2030, 1, 1))

    print(f"statements executed: {len(clinic.db.connection.executed)}")
    clinic.db.close()


if __name__ == "__main__":
    main()
