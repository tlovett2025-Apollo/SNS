import unittest

from recipe_reports import RecipeReportError, normalize_recipe_report


def recipe_payload():
    return {
        "candidate_id": "candidate-123",
        "title": "A Real Recipe",
        "ingredients": ["Chicken breast — 4 pieces"],
        "steps": ["Cook it safely."],
        "build_provenance": {
            "build_id": "SNS-abc123",
            "git": {"commit": "deadbeef"},
        },
    }


class RecipeReportTests(unittest.TestCase):
    def test_report_preserves_recipe_and_provenance(self):
        normalized = normalize_recipe_report({
            "recipe_snapshot": recipe_payload(),
            "rendered_recipe_text": "The visible recipe page",
            "issue_categories": ["wrong_ingredients", "weird_instructions"],
            "user_note": "The sauce does not belong here.",
        })

        self.assertEqual(normalized["p_candidate_id"], "candidate-123")
        self.assertEqual(normalized["p_build_id"], "SNS-abc123")
        self.assertEqual(normalized["p_commit_id"], "deadbeef")
        self.assertEqual(normalized["p_recipe_snapshot"]["title"], "A Real Recipe")
        self.assertEqual(normalized["p_issue_categories"], [
            "wrong_ingredients", "weird_instructions"
        ])
        self.assertEqual(normalized["p_report_outcome"], "NG")

    def test_no_checked_reason_means_general_human_review(self):
        normalized = normalize_recipe_report({"recipe_snapshot": recipe_payload()})
        self.assertEqual(normalized["p_issue_categories"], ["general_review"])

    def test_ok_feedback_has_a_distinct_outcome_and_category(self):
        normalized = normalize_recipe_report({
            "recipe_snapshot": recipe_payload(),
            "report_outcome": "ok",
        })
        self.assertEqual(normalized["p_report_outcome"], "OK")
        self.assertEqual(normalized["p_issue_categories"], ["recipe_ok"])

    def test_ok_feedback_cannot_include_problem_categories(self):
        with self.assertRaisesRegex(RecipeReportError, "cannot include problem"):
            normalize_recipe_report({
                "recipe_snapshot": recipe_payload(),
                "report_outcome": "OK",
                "issue_categories": ["wrong_ingredients"],
            })

    def test_unknown_reason_and_missing_recipe_are_rejected(self):
        with self.assertRaisesRegex(RecipeReportError, "recipe could not be attached"):
            normalize_recipe_report({})
        with self.assertRaisesRegex(RecipeReportError, "valid reason"):
            normalize_recipe_report({
                "recipe_snapshot": recipe_payload(),
                "issue_categories": ["make_it_trendy"],
            })


if __name__ == "__main__":
    unittest.main()
