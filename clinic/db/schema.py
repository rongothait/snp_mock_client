"""PostgreSQL schema for the clinic database.

Each table's DDL is a constant below; `TABLES` lists them in dependency order.
Columns holding PHI are marked with `-- PHI`. Highly sensitive values (SSN,
clinical notes, insurance member IDs) are stored only as application-level
ciphertext (see `clinic.security.FieldCipher`).
"""

from __future__ import annotations

from clinic.db.connection import Database

PATIENTS = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id        UUID PRIMARY KEY,
    mrn               VARCHAR(32)  NOT NULL UNIQUE,          -- PHI
    first_name        VARCHAR(100) NOT NULL,                 -- PHI
    last_name         VARCHAR(100) NOT NULL,                 -- PHI
    date_of_birth     DATE         NOT NULL,                 -- PHI
    sex               VARCHAR(16)  NOT NULL
                      CHECK (sex IN ('female', 'male', 'other', 'unknown')),
    email             VARCHAR(255),                          -- PHI
    phone             VARCHAR(32),                           -- PHI
    address_line1     VARCHAR(255),                          -- PHI
    city              VARCHAR(100),                          -- PHI
    state             CHAR(2),
    postal_code       VARCHAR(10),                           -- PHI
    ssn_encrypted     BYTEA,                                 -- PHI, ciphertext only
    ssn_last4         CHAR(4),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
"""

PROVIDERS = """
CREATE TABLE IF NOT EXISTS providers (
    provider_id       UUID PRIMARY KEY,
    npi               CHAR(10)     NOT NULL UNIQUE,
    first_name        VARCHAR(100) NOT NULL,
    last_name         VARCHAR(100) NOT NULL,
    specialty         VARCHAR(100) NOT NULL,
    active            BOOLEAN      NOT NULL DEFAULT TRUE
);
"""

INSURANCE_COVERAGE = """
CREATE TABLE IF NOT EXISTS insurance_coverage (
    coverage_id           UUID PRIMARY KEY,
    patient_id            UUID NOT NULL REFERENCES patients (patient_id) ON DELETE CASCADE,
    payer_name            VARCHAR(255) NOT NULL,
    member_id_encrypted   BYTEA        NOT NULL,             -- PHI, ciphertext only
    group_number          VARCHAR(64),
    effective_date        DATE         NOT NULL,
    termination_date      DATE,
    CHECK (termination_date IS NULL OR termination_date >= effective_date)
);
"""

APPOINTMENTS = """
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id    UUID PRIMARY KEY,
    patient_id        UUID NOT NULL REFERENCES patients (patient_id),
    provider_id       UUID NOT NULL REFERENCES providers (provider_id),
    scheduled_at      TIMESTAMPTZ NOT NULL,
    duration_minutes  INTEGER     NOT NULL CHECK (duration_minutes BETWEEN 5 AND 240),
    status            VARCHAR(16) NOT NULL DEFAULT 'scheduled'
                      CHECK (status IN ('scheduled', 'checked_in', 'completed', 'cancelled', 'no_show')),
    reason            VARCHAR(255)                           -- PHI
);
"""

ENCOUNTERS = """
CREATE TABLE IF NOT EXISTS encounters (
    encounter_id              UUID PRIMARY KEY,
    patient_id                UUID NOT NULL REFERENCES patients (patient_id),
    provider_id               UUID NOT NULL REFERENCES providers (provider_id),
    appointment_id            UUID REFERENCES appointments (appointment_id),
    encounter_date            TIMESTAMPTZ NOT NULL,
    clinical_notes_encrypted  BYTEA                          -- PHI, ciphertext only
);
"""

DIAGNOSES = """
CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id      UUID PRIMARY KEY,
    encounter_id      UUID NOT NULL REFERENCES encounters (encounter_id) ON DELETE CASCADE,
    icd10_code        VARCHAR(8)  NOT NULL,                  -- PHI when joined to a patient
    is_primary        BOOLEAN     NOT NULL DEFAULT FALSE
);
"""

PRESCRIPTIONS = """
CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id   UUID PRIMARY KEY,
    encounter_id      UUID NOT NULL REFERENCES encounters (encounter_id),
    patient_id        UUID NOT NULL REFERENCES patients (patient_id),
    medication_name   VARCHAR(255) NOT NULL,                 -- PHI
    dosage            VARCHAR(64)  NOT NULL,                 -- PHI
    frequency         VARCHAR(64)  NOT NULL,
    refills           INTEGER      NOT NULL DEFAULT 0 CHECK (refills >= 0),
    prescribed_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
"""

ACCESS_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS access_audit_log (
    audit_id          BIGSERIAL PRIMARY KEY,
    actor_user_id     VARCHAR(64) NOT NULL,
    actor_role        VARCHAR(32) NOT NULL,
    action            VARCHAR(32) NOT NULL,
    resource          VARCHAR(32) NOT NULL,
    patient_id        UUID REFERENCES patients (patient_id),
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

TABLES: list[tuple[str, str]] = [
    ("patients", PATIENTS),
    ("providers", PROVIDERS),
    ("insurance_coverage", INSURANCE_COVERAGE),
    ("appointments", APPOINTMENTS),
    ("encounters", ENCOUNTERS),
    ("diagnoses", DIAGNOSES),
    ("prescriptions", PRESCRIPTIONS),
    ("access_audit_log", ACCESS_AUDIT_LOG),
]

INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_patients_last_name ON patients (last_name);",
    "CREATE INDEX IF NOT EXISTS idx_appointments_provider_time ON appointments (provider_id, scheduled_at);",
    "CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments (patient_id);",
    "CREATE INDEX IF NOT EXISTS idx_encounters_patient ON encounters (patient_id);",
    "CREATE INDEX IF NOT EXISTS idx_diagnoses_encounter ON diagnoses (encounter_id);",
    "CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions (patient_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_patient_time ON access_audit_log (patient_id, occurred_at);",
]


def create_all(db: Database) -> None:
    """Create every table and index in one transaction."""
    with db.transaction() as cur:
        for _name, ddl in TABLES:
            cur.execute(ddl)
        for ddl in INDEXES:
            cur.execute(ddl)
