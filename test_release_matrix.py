import unittest

from release_matrix import BOUNDARY_CASES, build_release_matrix_report


class ProductionReleaseMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_release_matrix_report()

    def test_release_matrix_is_machine_readable_and_green(self):
        self.assertEqual(self.report["schema_version"], "1.0")
        self.assertTrue(self.report["production_ready"], self.report["gates"])
        self.assertEqual(self.report["summary"]["failed_cases"], 0)

    def test_matrix_covers_launch_catalog_pairwise_and_high_risk_cases(self):
        gates = {gate["name"]: gate for gate in self.report["gates"]}
        self.assertEqual(gates["launch_catalog_knowledge"]["cases"], 139)
        self.assertGreaterEqual(gates["pairwise_orchestration"]["cases"], 250)
        self.assertEqual(gates["boundary_and_high_risk"]["cases"], len(BOUNDARY_CASES))


if __name__ == "__main__":
    unittest.main()

