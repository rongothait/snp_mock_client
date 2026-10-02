import re
import unittest

from clinic.db.schema import INDEXES, TABLES, create_all
from tests.fixtures import make_clinic


class SchemaTest(unittest.TestCase):
    def test_every_table_has_create_statement(self):
        for name, ddl in TABLES:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {name} (", ddl)

    def test_referenced_tables_are_created_first(self):
        created = set()
        for name, ddl in TABLES:
            for ref in re.findall(r"REFERENCES (\w+)", ddl):
                self.assertIn(ref, created, f"{name} references {ref} before it exists")
            created.add(name)

    def test_create_all_runs_in_one_transaction(self):
        clinic = make_clinic()
        create_all(clinic.db)
        conn = clinic.db.connection
        self.assertEqual(len(conn.executed), len(TABLES) + len(INDEXES))
        self.assertEqual(conn.commits, 1)

    def test_no_plaintext_ssn_column(self):
        patients_ddl = dict(TABLES)["patients"]
        self.assertNotRegex(patients_ddl, r"\n\s+ssn\s")


if __name__ == "__main__":
    unittest.main()
