import unittest
from types import SimpleNamespace

from planner_voice import (
    activity_message,
    completion_message,
    meal_introduction,
    time_summary,
    transition_message,
)


class PlannerVoiceTests(unittest.TestCase):
    def test_intro_uses_title_time_and_energy(self):
        result = meal_introduction({
            "title": "Chinese Chicken Bowl",
            "minutes": 30,
            "user_energy": "Low",
        })
        self.assertIn("Chinese Chicken Bowl", result)
        self.assertIn("30 minutes", result)
        self.assertIn("low energy", result)

    def test_passive_window_reassures_without_chatter(self):
        activity = SimpleNamespace(
            activity_type="rest",
            component="Chicken breast",
            instruction="Rest the chicken for 5 minutes.",
            human_busy=False,
            stage="late",
        )
        result = activity_message(activity, duration=5, attention_minutes=0)
        self.assertIn("Nothing needs your full attention", result)
        self.assertNotIn("Awesome", result)

    def test_partial_attention_is_explained(self):
        activity = SimpleNamespace(
            activity_type="cook",
            component="Mushrooms",
            instruction="Brown the mushrooms without stirring at first.",
            human_busy=True,
            stage="middle",
        )
        result = activity_message(activity, duration=6, attention_minutes=2)
        self.assertIn("2 minutes of attention", result)

    def test_launch_prep_uses_kitchen_language_not_engine_jargon(self):
        activity = SimpleNamespace(
            activity_type="launch prep",
            component="meal",
            instruction="Start the rice.",
            human_busy=True,
            stage="early",
        )

        result = activity_message(activity, duration=2, attention_minutes=2)

        self.assertIn("Now it is ready to start", result)
        self.assertNotIn("long-lead", result.lower())

    def test_finish_transition_is_brief(self):
        previous = SimpleNamespace(stage="middle")
        next_activity = SimpleNamespace(stage="finish")
        self.assertEqual(
            transition_message(previous, next_activity),
            "Good. The main cooking is done, and we are moving into the finish.",
        )

    def test_cooking_transition_does_not_claim_prep_is_underway(self):
        previous = SimpleNamespace(stage="early")
        next_activity = SimpleNamespace(stage="middle")

        result = transition_message(previous, next_activity)

        self.assertEqual(result, "Prep is complete. Now the cooking begins.")
        self.assertNotIn("meal is underway", result.lower())

    def test_completion_is_useful(self):
        result = completion_message({"sauce": "simple stir-fry sauce"})
        self.assertEqual(result, "Nicely done. Dinner is ready.")

    def test_time_summary_distinguishes_attention_and_waiting(self):
        result = time_summary(30, 12, 18)
        self.assertIn("12 minutes need your attention", result)
        self.assertIn("18 minutes are mostly waiting time", result)

    def test_soup_completion_does_not_name_generic_sauce(self):
        result = completion_message({
            "strategy": "soup",
            "sauce": "Gravy or Cream Sauce",
        })
        self.assertEqual(result, "Nicely done. Dinner is ready.")


if __name__ == "__main__":
    unittest.main()
