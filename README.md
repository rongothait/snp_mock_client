# Clinic mock client

A small medical clinic management system (patients, providers, appointments,
encounters, diagnoses, prescriptions, insurance) used as a test target for the
privacy-agent plugin. There is no real database: `clinic.db.connection.Database`
builds a PostgreSQL DSN but connects to `MockConnection`, which records SQL and
returns canned rows. **All data in this repo is synthetic.**

## Layout

```
main.py                     demo run against the mock DB
clinic/config.py            DB settings and keys from env vars (see .env.example)
clinic/db/connection.py     Database + MockConnection/MockCursor
clinic/db/schema.py         CREATE TABLE / CREATE INDEX statements for every table
clinic/models.py            dataclasses; PHI fields are hidden from repr
clinic/security.py          roles/permissions, field encryption (mock), pseudonymization
clinic/repositories/        parameterized SQL per aggregate
clinic/services/            patient, clinical, audit, de-identified reporting
tests/                      unittest suite with synthetic fixtures
```

## Privacy baseline

- No real identifiers or clinical narratives in code; fixtures use `example.invalid`, 555 numbers, `TEST-` MRNs.
- Logs and exception messages carry IDs only; model `repr` hides PHI.
- SSN, clinical notes, and insurance member IDs are stored encrypted.
- Every PHI read/write goes through a role check and writes an `access_audit_log` row.
- Exports are de-identified: HMAC pseudonyms, age bands, ICD-10 categories.
- Credentials and keys come from the environment.

## Run

```
python main.py
python -m unittest
```
