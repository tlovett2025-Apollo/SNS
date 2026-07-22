"""Round 7 matrix for batch learning and release governance."""

import unittest

from learning_operations import (
    build_enrichment_queue,
    cluster_recipe_reports,
    monitoring_snapshot,
    promotion_decision,
    release_decision,
)


def report(candidate, category, method="skillet", family="hash", build="build-1"):
    return {
        "candidate_id": candidate,
        "build_id": build,
        "report_outcome": "NG",
        "issue_categories": [category],
        "recipe_snapshot": {"cooking_method": method, "dish_family": family},
    }


class LearningOperationsTests(unittest.TestCase):

    def test_repeated_examples_cluster_into_one_architecture_work_item(self):
        clusters = cluster_recipe_reports([
            report("a", "weird_instructions"),
            report("b", "weird_instructions", build="build-2"),
            report("c", "wrong_quantity"),
        ])
        behavior = next(item for item in clusters if item["route"] == "behavior_execution")

        self.assertEqual(2, behavior["count"])
        self.assertEqual("batch_review", behavior["status"])
        self.assertEqual(("a", "b"), behavior["candidate_ids"])

    def test_queue_combines_failure_retail_and_unmatched_evidence(self):
        clusters = cluster_recipe_reports([
            report("a", "uncookable_combination"),
            report("b", "uncookable_combination"),
        ])
        queue = build_enrichment_queue(
            clusters,
            [{"retail_product": {"barcode": "07811403", "product_name": "Ginger Ale"}}],
            [{"name": "Mystery grain"}, {"name": "Mystery grain"}],
        )

        self.assertEqual("behavior_learning", queue[0]["queue_type"])
        self.assertEqual(3, len(queue))
        self.assertTrue(all(item["promotion_status"] == "not_ready" for item in queue))

    def test_promotion_requires_identity_provenance_safety_behavior_and_tests(self):
        incomplete = promotion_decision({"canonical_identity_confirmed": True})
        complete = promotion_decision({
            "canonical_identity_confirmed": True,
            "provenance_present": True,
            "safety_reviewed": True,
            "behavior_contract_complete": True,
            "regression_cases": 2,
            "promotion_target": "retail_product_registry",
        })

        self.assertFalse(incomplete["approved"])
        self.assertTrue(complete["approved"])
        self.assertEqual("retail_product_registry", complete["target"])

    def test_release_policy_holds_repeated_high_risk_clusters(self):
        clusters = cluster_recipe_reports([
            report("a", "uncookable_combination"),
            report("b", "uncookable_combination"),
        ])
        held = release_decision({"production_ready": True}, clusters, [])
        clear = release_decision({"production_ready": True}, [], [])

        self.assertEqual("hold", held["status"])
        self.assertIn("unresolved_high_risk_learning_clusters", held["blockers"])
        self.assertEqual("release", clear["status"])

    def test_monitoring_snapshot_is_small_and_machine_readable(self):
        reports = [report("a", "wrong_quantity")]
        clusters = cluster_recipe_reports(reports)
        queue = build_enrichment_queue(clusters)
        snapshot = monitoring_snapshot(reports, clusters, queue)

        self.assertEqual(1, snapshot["reports"])
        self.assertEqual(1, snapshot["negative_reports"])
        self.assertEqual(1, snapshot["enrichment_queue"])


if __name__ == "__main__":
    unittest.main()
