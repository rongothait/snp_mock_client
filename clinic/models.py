"""Domain models.

PHI fields are declared with `repr=False`, so printing or logging a model by
accident shows only its identifiers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Patient:
    first_name: str = field(repr=False)
    last_name: str = field(repr=False)
    date_of_birth: date = field(repr=False)
    sex: str = field(repr=False)
    mrn: str = field(repr=False)
    email: str | None = field(default=None, repr=False)
    phone: str | None = field(default=None, repr=False)
    address_line1: str | None = field(default=None, repr=False)
    city: str | None = field(default=None, repr=False)
    state: str | None = field(default=None, repr=False)
    postal_code: str | None = field(default=None, repr=False)
    ssn_last4: str | None = field(default=None, repr=False)
    patient_id: str = field(default_factory=new_id)


@dataclass
class Provider:
    npi: str
    first_name: str
    last_name: str
    specialty: str
    provider_id: str = field(default_factory=new_id)
    active: bool = True


@dataclass
class InsuranceCoverage:
    patient_id: str
    payer_name: str
    member_id: str = field(repr=False)
    effective_date: date
    group_number: str | None = None
    termination_date: date | None = None
    coverage_id: str = field(default_factory=new_id)


@dataclass
class Appointment:
    patient_id: str
    provider_id: str
    scheduled_at: datetime
    duration_minutes: int = 30
    status: str = "scheduled"
    reason: str | None = field(default=None, repr=False)
    appointment_id: str = field(default_factory=new_id)


@dataclass
class Encounter:
    patient_id: str
    provider_id: str
    encounter_date: datetime
    clinical_notes: str | None = field(default=None, repr=False)
    appointment_id: str | None = None
    encounter_id: str = field(default_factory=new_id)


@dataclass
class Diagnosis:
    encounter_id: str
    icd10_code: str = field(repr=False)
    is_primary: bool = False
    diagnosis_id: str = field(default_factory=new_id)


@dataclass
class Prescription:
    encounter_id: str
    patient_id: str
    medication_name: str = field(repr=False)
    dosage: str = field(repr=False)
    frequency: str = field(repr=False)
    refills: int = 0
    prescription_id: str = field(default_factory=new_id)
