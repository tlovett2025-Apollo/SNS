"""Round 4 matrix for whole-meal coordination and single-cook attention."""

import unittest

from meal_orchestration import MEAL_SHAPES, attention_mode, build_orchestration_report
from recipe_engine import generate_candidates


class FakeActivity:
    def __init__(self, human_busy, attention_load):
        self.human_busy = human_busy
        self.attention_load = attention_load


class MealOrchestrationTests(unittest.TestCase):

    def test_round_four_trains_eight_meal_shape_contracts(self):
        self.assertEqual(8, len(MEAL_SHAPES))
        for code, contract in MEAL_SHAPES.items():
            with self.subTest(shape=code):
                self.assertEqual(code, contract.code)
                self.assertTrue(contract.service_pattern)
                self.assertTrue(contract.component_rule)

    def test_attention_modes_distinguish_continuous_interlaced_and_passive_work(self):
        self.assertEqual("continuous", attention_mode(FakeActivity(True, .9)))
        self.assertEqual("intermittent", attention_mode(FakeActivity(True, .4)))
        self.assertEqual("launch_and_check", attention_mode(FakeActivity(True, .1)))
        self.assertEqual("passive", attention_mode(FakeActivity(False, 0)))

    def test_oven_main_and_stovetop_side_can_interlace_for_one_cook(self):
        candidate = generate_candidates(
            "Chicken thighs", "", "Macaroni", "BBQ", "Medium", "Budget",
            90, 2, 1,
            protein_state="Fresh Raw",
            available_items=[
                "Chicken thighs", "Macaroni", "Cheddar cheese", "Butter",
                "BBQ sauce", "Garlic powder", "Onion powder", "Black pepper",
            ],
            available_equipment=["Oven", "Stovetop"],
            requested_method="oven_roast", meal_structure="composed_plate",
        )[0]
        report = candidate["orchestration"]

        self.assertEqual("composed_plate", report["shape"]["code"])
        self.assertIn("Oven", report["lanes"])
        self.assertTrue(any("Burner" in lane for lane in report["lanes"]))
        self.assertTrue(report["concurrent_windows"])
        self.assertTrue(report["hold_windows"])
        self.assertTrue(all("quality_risk" in item for item in report["hold_windows"]))
        self.assertTrue(report["single_cook_feasible"])
        self.assertEqual([], report["attention_conflicts"])

    def test_report_detects_overlapping_single_cook_attention_reservations(self):
        class Item:
            def __init__(self, activity_id, start, end, attention):
                self.activity = FakeActivity(True, 1)
                self.activity.activity_id = activity_id
                self.activity.component = activity_id
                self.start_minute = start
                self.end_minute = end
                self.attention_minutes = attention
                self.lane = activity_id

        report = build_orchestration_report(
            {"meal_structure": "composed_plate"},
            [Item("pan", 0, 5, 4), Item("pot", 2, 7, 3)],
        )
        self.assertFalse(report["single_cook_feasible"])
        self.assertEqual([["pan", "pot"]], report["attention_conflicts"])


if __name__ == "__main__":
    unittest.main()
