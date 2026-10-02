"""Synthetic test data. Nothing here describes a real person."""

from datetime import date

from clinic.app import Clinic
from clinic.config import AppConfig, DatabaseConfig
from clinic.models import Patient
from clinic.security import Actor, Role

TEST_FIELD_KEY = bytes(range(32))
TEST_PSEUDONYM_KEY = bytes(range(32, 64))

# 000 is never issued as an SSN area number, so this value is invalid by design.
SYNTHETIC_SSN = "000-00-0000"

FRONT_DESK = Actor(user_id="staff-test-1", role=Role.FRONT_DESK)
PHYSICIAN = Actor(user_id="staff-test-2", role=Role.PHYSICIAN)
BILLING = Actor(user_id="staff-test-3", role=Role.BILLING)
ANALYST = Actor(user_id="staff-test-4", role=Role.ANALYST)


def make_clinic() -> Clinic:
    config = AppConfig(
        db=DatabaseConfig(host="db.test.example"),
        field_key=TEST_FIELD_KEY,
        pseudonym_key=TEST_PSEUDONYM_KEY,
    )
    return Clinic.build(config)


def make_patient(**overrides) -> Patient:
    values = dict(
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(2000, 1, 1),
        sex="unknown",
        mrn="TEST-0001",
        email="patient@example.invalid",
        phone="555-0100",
    )
    values.update(overrides)
    return Patient(**values)
