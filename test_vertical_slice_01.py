"""Acceptance coverage for SNS Culinary Knowledge Vertical Slice 01."""

from cooking_planner import build_activity_graph, build_kitchen_lane_schedule, generate_human_plan_items
from ingredient_profiles import get_ingredient_profile
from ko_contract import audit_behavior
from recipe_engine import build_recipe_from_candidate, generate_candidates


def candidate(protein, vegetables, foundation="", **kwargs):
    return generate_candidates(
        protein, " & ".join(vegetables), foundation, "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=vegetables,
        requested_method="skillet",
        **kwargs,
    )[0]


def test_slice_components_resolve_to_operational_profiles():
    specs = [
        ("Chicken breast", "protein", "Fresh Raw"),
        ("Ground beef", "protein", "Fresh Raw"),
        ("Onions", "vegetable", "Fresh"),
        ("Carrots", "vegetable", "Fresh"),
        ("Mushrooms", "vegetable", "Fresh"),
        ("Asparagus", "vegetable", "Fresh"),
        ("White rice", "foundation", "Dry"),
        ("Pasta", "foundation", "Dry"),
        ("Potatoes", "foundation", "Fresh"),
        ("Navy beans", "foundation", "Canned"),
    ]
    reports = [audit_behavior(*spec, strategy="skillet") for spec in specs]
    assert all(report.operational for report in reports), [
        (report.ingredient_name, report.missing) for report in reports if not report.operational
    ]


def test_ground_beef_carrots_and_onions_preserve_component_staging():
    value = candidate(
        "Ground beef", ["Onions", "Carrots"],
        protein_state="Fresh Raw",
        available_items=["Ground beef", "Onions", "Carrots", "Chicken broth", "Milk"],
    )
    instruction = build_activity_graph(value)["cook skillet:meal"].instruction
    assert instruction.index("Carrots & Onions") < instruction.index("Add Ground beef")
    assert "steam-soften" in instruction
    assert "160°F" in instruction
    assert "Color alone is not the safety test" in instruction


def test_chicken_mushroom_asparagus_rice_uses_each_component_rule():
    value = candidate(
        "Chicken breast", ["Mushrooms", "Asparagus"], "White rice",
        protein_state="Fresh Raw", available_equipment=["Rice cooker"],
    )
    graph = build_activity_graph(value)
    vegetables = graph["cook vegetables:meal"].instruction
    assert vegetables.index("Mushrooms") < vegetables.index("Asparagus")
    assert "moisture evaporate" in vegetables
    assert "verify:Chicken breast" in graph["cook vegetables:meal"].depends_on
    schedule = build_kitchen_lane_schedule(value)
    rice = [item for item in schedule if item.activity.component == "White rice"]
    assert rice and any(item.lane == "Rice Cooker" for item in rice)
    assert not any(item.lane.startswith("Burner ") for item in rice)


def test_frozen_chicken_uses_a_pre_recipe_readiness_boundary():
    value = candidate(
        "Chicken breast", ["Onions"], protein_state="Frozen Raw",
        available_equipment=["Microwave"],
    )
    graph = build_activity_graph(value)
    assert "thaw:Chicken breast" not in graph
    assert "prep:meal" in graph
    assert "prep:meal" in graph["cook:Chicken breast"].depends_on
    plan_items = generate_human_plan_items(value)
    info = " ".join(item["text"] for item in plan_items if item["kind"] == "info")
    actions = " ".join(item["text"] for item in plan_items if item["kind"] == "action")
    assert "Before Step 1, fully thaw Chicken breast" in info
    assert "thaw" not in actions.lower()


def test_pasta_and_cream_sauce_publish_specific_execution_and_cues():
    value = candidate(
        "Chicken breast", ["Onions"], "Pasta", protein_state="Fresh Raw",
        available_items=["Chicken breast", "Onions", "Pasta", "Chicken broth", "Milk", "Cornstarch"],
    )
    recipe = build_recipe_from_candidate(value)
    plan = " ".join(recipe["action_steps"])
    assert "reserve cooking water" in plan
    assert "do not boil" in plan.lower()
    assert "lightly coats" in plan


def test_potato_is_long_lead_and_asparagus_is_late():
    potato = get_ingredient_profile("Potatoes", "foundation")
    asparagus = get_ingredient_profile("Asparagus", "vegetable")
    assert potato.cook_minutes > asparagus.cook_minutes
    assert potato.add_stage == "early"
    assert asparagus.add_stage in {"middle", "late"}


def test_canned_beans_reheat_instead_of_using_dry_bean_route():
    activities = get_ingredient_profile("Navy beans", "foundation").publish_activities(
        "skillet", "Canned"
    )
    assert [activity.activity_type for activity in activities] == ["prep", "reheat"]
    text = " ".join(activity.instruction for activity in activities).lower()
    assert "drain and rinse" in text
    assert "soak" not in text


def test_two_burner_schedule_never_invents_a_third_burner():
    value = candidate(
        "Chicken breast", ["Mushrooms", "Asparagus"], "White rice",
        protein_state="Fresh Raw", available_equipment=[],
    )
    schedule = build_kitchen_lane_schedule(value, burner_count=2)
    assert {item.lane for item in schedule if item.lane.startswith("Burner ")} <= {
        "Burner 1", "Burner 2"
    }


def test_low_energy_schedule_keeps_one_human_attention_lane():
    value = candidate(
        "Chicken breast", ["Mushrooms", "Asparagus"], "White rice",
        protein_state="Fresh Raw", available_equipment=["Rice cooker"],
    )
    schedule = build_kitchen_lane_schedule(value, human_attention_lanes=1)
    busy = sorted(
        (item.start_minute, item.start_minute + item.attention_minutes)
        for item in schedule if item.attention_minutes > 0
    )
    assert all(next_start >= prior_end for (_, prior_end), (next_start, _) in zip(busy, busy[1:]))


def test_selected_sauce_has_an_executable_timeline_activity():
    value = candidate(
        "Ground beef", ["Onions", "Carrots"], protein_state="Fresh Raw",
        available_items=["Ground beef", "Onions", "Carrots", "Chicken broth", "Milk", "Cornstarch"],
    )
    graph = build_activity_graph(value)
    sauce = graph["finish sauce:meal"]
    assert sauce.minutes > 0
    assert sauce.equipment in {"burner", "skillet"}
    assert any(word in sauce.instruction.lower() for word in ("simmer", "coat", "thicken"))
    assert "cook skillet:meal" in sauce.depends_on
