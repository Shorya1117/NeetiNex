import unittest
from backend.eligibility.evaluator import evaluate_condition


class TestEligibilityEvaluator(unittest.TestCase):
    def test_true(self):
        result = evaluate_condition({"attribute": "age", "operator": ">=", "value": 18}, {"age": 22})
        self.assertEqual(result.status, "TRUE")

    def test_false(self):
        result = evaluate_condition({"attribute": "age", "operator": ">=", "value": 18}, {"age": 16})
        self.assertEqual(result.status, "FALSE")

    def test_missing_is_unknown(self):
        result = evaluate_condition({"attribute": "age", "operator": ">=", "value": 18}, {})
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.missing_attributes, ["age"])

    def test_or_group(self):
        rule = {"any": [
            {"attribute": "category", "operator": "==", "value": "SC"},
            {"attribute": "annual_family_income", "operator": "<=", "value": 100000}
        ]}
        self.assertEqual(evaluate_condition(rule, {"category": "SC", "annual_family_income": 200000}).status, "TRUE")

    def test_and_group_unknown(self):
        rule = {"all": [
            {"attribute": "state", "operator": "==", "value": "Rajasthan"},
            {"attribute": "age", "operator": ">=", "value": 18}
        ]}
        self.assertEqual(evaluate_condition(rule, {"state": "Rajasthan"}).status, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
