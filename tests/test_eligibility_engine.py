import tempfile
import unittest
from pathlib import Path
from backend.database.eligibility_db import initialize_database
from backend.database.repositories.eligibility_repository import EligibilityRepository
from backend.eligibility.engine import EligibilityEngine


class TestEligibilityEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "eligibility.db"
        initialize_database(self.db_path)
        self.repo = EligibilityRepository(self.db_path)
        self.repo.add_scheme({"scheme_id": "sample", "scheme_name": "Sample Scheme", "verification_status": "verified"})
        self.repo.add_rule("sample", {
            "rule_name": "Residence and age",
            "condition": {"all": [
                {"attribute": "state", "operator": "==", "value": "Rajasthan"},
                {"attribute": "age", "operator": ">=", "value": 18}
            ]},
            "sources": [{"document_name": "Official guideline", "page_number": 2, "url": "https://example.gov.in/guideline.pdf"}]
        })
        self.engine = EligibilityEngine(self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_eligible(self):
        self.assertEqual(self.engine.check_scheme("sample", {"state": "Rajasthan", "age": 20})["status"], "ELIGIBLE")

    def test_not_eligible(self):
        self.assertEqual(self.engine.check_scheme("sample", {"state": "Rajasthan", "age": 16})["status"], "NOT_ELIGIBLE")

    def test_missing_information(self):
        result = self.engine.check_scheme("sample", {"state": "Rajasthan"})
        self.assertEqual(result["status"], "NEEDS_MORE_INFORMATION")
        self.assertIn("age", result["missing_attributes"])

    def test_unverified_scheme_is_blocked(self):
        self.repo.add_scheme({"scheme_id": "draft", "scheme_name": "Draft", "verification_status": "unverified"})
        with self.assertRaises(LookupError):
            self.engine.check_scheme("draft", {})


if __name__ == "__main__":
    unittest.main()
