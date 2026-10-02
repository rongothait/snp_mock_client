import unittest

from clinic.security import AccessDenied, FieldCipher
from clinic.services.patient_service import PatientNotFound
from tests.fixtures import (
    ANALYST, BILLING, FRONT_DESK, SYNTHETIC_SSN, TEST_FIELD_KEY, make_clinic, make_patient,
)


class PatientServiceTest(unittest.TestCase):
    def setUp(self):
        self.clinic = make_clinic()
        self.conn = self.clinic.db.connection

    def test_register_encrypts_ssn_and_audits(self):
        patient = make_patient()
        self.clinic.patients.register(FRONT_DESK, patient, ssn=SYNTHETIC_SSN)

        insert_sql, params = self.conn.executed[0]
        self.assertTrue(insert_sql.startswith("INSERT INTO patients"))
        self.assertNotIn(SYNTHETIC_SSN, params)
        ciphertext = params[12]
        self.assertEqual(FieldCipher(TEST_FIELD_KEY).decrypt(ciphertext), SYNTHETIC_SSN)
        self.assertEqual(params[13], SYNTHETIC_SSN[-4:])

        audit_sql, audit_params = self.conn.executed[1]
        self.assertTrue(audit_sql.startswith("INSERT INTO access_audit_log"))
        self.assertEqual(audit_params, (FRONT_DESK.user_id, "front_desk", "create", "patient", patient.patient_id))

    def test_logs_contain_ids_but_no_phi(self):
        patient = make_patient()
        with self.assertLogs("clinic", level="INFO") as logs:
            self.clinic.patients.register(FRONT_DESK, patient, ssn=SYNTHETIC_SSN)
        output = "\n".join(logs.output)
        self.assertIn(patient.patient_id, output)
        for value in (patient.first_name, patient.last_name, patient.email, patient.phone, patient.mrn, SYNTHETIC_SSN):
            self.assertNotIn(value, output)

    def test_repr_hides_phi(self):
        patient = make_patient()
        text = repr(patient)
        self.assertIn(patient.patient_id, text)
        self.assertNotIn(patient.email, text)
        self.assertNotIn(patient.mrn, text)

    def test_analyst_cannot_read_demographics(self):
        with self.assertRaises(AccessDenied):
            self.clinic.patients.get(ANALYST, "any-id")
        self.assertEqual(self.conn.executed, [])

    def test_front_desk_cannot_read_ssn(self):
        with self.assertRaises(AccessDenied):
            self.clinic.patients.get_ssn(FRONT_DESK, "any-id")

    def test_billing_can_read_ssn(self):
        ciphertext = FieldCipher(TEST_FIELD_KEY).encrypt(SYNTHETIC_SSN)
        self.conn.queue_result([(ciphertext,)])
        self.assertEqual(self.clinic.patients.get_ssn(BILLING, "pid-1"), SYNTHETIC_SSN)

    def test_missing_patient_error_has_only_id(self):
        with self.assertRaises(PatientNotFound) as ctx:
            self.clinic.patients.get(FRONT_DESK, "pid-missing")
        self.assertEqual(str(ctx.exception), "patient_id=pid-missing")


if __name__ == "__main__":
    unittest.main()
