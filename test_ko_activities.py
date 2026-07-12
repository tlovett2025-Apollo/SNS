import re

from cooking_planner import build_cooking_activities, summarize_cooking_activities
from recipe_engine import generate_candidates


def sample_candidate():
    return generate_candidates(
        "Chicken breast", "Swiss chard & Black olives", "Rice", "Comfort Food",
        "Low", "Budget", 30, 4, 1,
        vegetable_names=["Swiss chard", "Black olives"],
    )[0]


def test_knowledge_objects_publish_component_activities():
    activities = build_cooking_activities(sample_candidate())
    assert any(a.component == "Chicken breast" and a.activity_type == "rest" and a.source == "ko" for a in activities)
    assert any(a.component == "Swiss chard" and a.activity_type == "serve" and a.source == "ko" for a in activities)
    assert any(a.component == "Black olives" and a.activity_type == "drain" and a.source == "ko" for a in activities)
    assert any(a.component == "Black olives" and a.activity_type == "fold in" and a.source == "ko" for a in activities)


def test_planner_does_not_replace_components_with_roles():
    activities = build_cooking_activities(sample_candidate())
    assert not any(a.component in {"protein", "vegetable", "foundation"} for a in activities)


def test_debug_exposes_activity_ownership():
    summaries = summarize_cooking_activities(sample_candidate())
    assert any("rest: Chicken breast" in line and line.endswith("ko") for line in summaries)
    assert any(": meal" in line and line.endswith("planner") for line in summaries)


def test_activity_graph_dependencies_resolve():
    from cooking_planner import build_activity_graph
    graph = build_activity_graph(sample_candidate())
    assert "prep:meal" in graph
    assert "prep:Chicken breast" not in graph
    assert graph["prep:meal"].source == "consolidator"
    assert graph["slice:Chicken breast"].depends_on == ["rest:Chicken breast"]
    assert all(dep in graph for activity in graph.values() for dep in activity.depends_on)


def test_activity_consolidation_builds_one_real_mise_en_place_phase():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())
    launch = graph["prep:launch"]
    prep = graph["prep:meal"]

    assert launch.depends_on == ["gather:meal"]
    assert prep.depends_on == ["start:Rice"]
    assert prep.component == "meal"
    assert prep.activity_type == "prep"
    instruction = prep.instruction.lower()
    assert "chicken breast" in instruction
    assert "swiss chard" in instruction
    assert "mushrooms" in instruction
    assert "asparagus" in instruction
    assert "rice" in launch.instruction.lower()
    assert "simple stir-fry sauce" in instruction


def test_component_cooking_depends_on_consolidated_prep():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())

    assert graph["cook:Chicken breast"].depends_on == ["prep:meal"]
    assert graph["start:Rice"].depends_on == ["prep:launch"]
    assert all(
        not dependency.startswith("prep:") or dependency in {"prep:meal", "prep:launch"}
        for activity in graph.values()
        for dependency in activity.depends_on
    )


def test_lane_schedule_respects_single_human_attention_lane():
    from cooking_planner import build_kitchen_lane_schedule
    schedule = build_kitchen_lane_schedule(sample_candidate(), burner_count=2, human_attention_lanes=1)
    busy = sorted(
        [
            (item.start_minute, item.start_minute + item.attention_minutes)
            for item in schedule if item.attention_minutes > 0
        ]
    )
    for (_, previous_end), (next_start, _) in zip(busy, busy[1:]):
        assert next_start >= previous_end


def test_lane_schedule_never_uses_more_burners_than_available():
    from cooking_planner import build_kitchen_lane_schedule
    schedule = build_kitchen_lane_schedule(sample_candidate(), burner_count=2)
    burner_lanes = {item.lane for item in schedule if item.lane.startswith("Burner ")}
    assert burner_lanes <= {"Burner 1", "Burner 2"}


def state_candidate(state):
    return generate_candidates(
        "Chicken breast", "Swiss chard", "Rice", "Comfort Food",
        "Low", "Budget", 45, 4, 1,
        vegetable_names=["Swiss chard"],
        protein_state=state,
    )[0]


def test_protein_state_flows_into_candidate():
    candidate = state_candidate("Frozen Raw")
    assert candidate["protein_state"] == "Frozen Raw"


def test_fresh_raw_chicken_publishes_cook_rest_and_slice():
    activities = build_cooking_activities(state_candidate("Fresh Raw"))
    kinds = [a.activity_type for a in activities if a.component == "Chicken breast"]
    assert kinds == ["prep", "cook", "wait", "rest", "slice"]


def test_frozen_raw_chicken_publishes_verify_and_longer_path():
    activities = build_cooking_activities(state_candidate("Frozen Raw"))
    chicken = [a for a in activities if a.component == "Chicken breast"]
    kinds = [a.activity_type for a in chicken]
    assert kinds == ["prep", "cook", "wait", "verify", "rest", "slice"]
    assert sum(a.minutes or 0 for a in chicken) > 30


def test_cooked_chicken_reheats_without_raw_cooking_cycle():
    activities = build_cooking_activities(state_candidate("Cooked"))
    chicken = [a for a in activities if a.component == "Chicken breast"]
    kinds = [a.activity_type for a in chicken]
    assert kinds == ["prep", "reheat"]
    assert "cook" not in kinds
    assert "rest" not in kinds


def test_state_changes_lane_schedule_duration():
    from cooking_planner import build_kitchen_lane_schedule
    fresh = build_kitchen_lane_schedule(state_candidate("Fresh Raw"))
    frozen = build_kitchen_lane_schedule(state_candidate("Frozen Raw"))
    cooked = build_kitchen_lane_schedule(state_candidate("Cooked"))
    fresh_end = max(item.end_minute for item in fresh)
    frozen_end = max(item.end_minute for item in frozen)
    cooked_end = max(item.end_minute for item in cooked)
    assert frozen_end > fresh_end > cooked_end


def parallel_regression_candidate():
    return generate_candidates(
        "Chicken breast",
        "Swiss chard & Mushrooms & Asparagus",
        "Rice",
        "Chinese",
        "Low",
        "Budget",
        45,
        4,
        1,
        vegetable_names=["Swiss chard", "Mushrooms", "Asparagus"],
        protein_state="Fresh Raw",
    )[0]


def test_scheduler_starts_passive_chicken_wait_when_active_cook_ends():
    from cooking_planner import build_kitchen_lane_schedule

    schedule = build_kitchen_lane_schedule(parallel_regression_candidate())
    by_id = {item.activity.activity_id: item for item in schedule}

    assert by_id["wait:Chicken breast"].start_minute == by_id["cook:Chicken breast"].end_minute


def test_rice_passive_cooking_overlaps_other_human_work():
    from cooking_planner import build_kitchen_lane_schedule

    schedule = build_kitchen_lane_schedule(parallel_regression_candidate())
    rice = next(item for item in schedule if item.activity.activity_id == "simmer:Rice")

    assert any(
        item.activity.human_busy
        and item.start_minute < rice.end_minute
        and item.end_minute > rice.start_minute
        and item.activity.component != "Rice"
        for item in schedule
    )


def test_rice_launches_before_general_mise_en_place():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["user_energy"] = "Normal"
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    assert by_id["prep:launch"].end_minute == by_id["start:Rice"].start_minute
    assert by_id["start:Rice"].end_minute == by_id["prep:meal"].start_minute
    assert by_id["prep:meal"].start_minute < by_id["simmer:Rice"].end_minute


def test_basmati_rice_uses_rice_long_lead_activity_graph():
    from cooking_planner import build_activity_graph

    candidate = parallel_regression_candidate()
    candidate["foundation"] = "Basmati rice"
    graph = build_activity_graph(candidate)

    assert "start:Basmati rice" in graph
    assert "simmer:Basmati rice" in graph
    assert graph["simmer:Basmati rice"].human_busy is False
    assert graph["simmer:Basmati rice"].minutes == 18
    assert graph["start:Basmati rice"].depends_on == ["prep:launch"]


def test_time_feasibility_uses_required_lead_time():
    from cooking_planner import assess_time_feasibility

    candidate = parallel_regression_candidate()
    required = assess_time_feasibility(candidate, 999)["required_lead_minutes"]
    too_late = assess_time_feasibility(candidate, required - 1)
    enough_time = assess_time_feasibility(candidate, required)

    assert too_late["time_feasible"] is False
    assert too_late["time_shortfall_minutes"] == 1
    assert enough_time["time_feasible"] is True
    assert enough_time["time_shortfall_minutes"] == 0


def test_energy_scales_human_attention_and_schedule():
    from cooking_planner import build_kitchen_lane_schedule

    normal_candidate = parallel_regression_candidate()
    normal_candidate["user_energy"] = "Normal"
    exhausted_candidate = dict(normal_candidate)
    exhausted_candidate["user_energy"] = "Barely Breathing"

    normal = build_kitchen_lane_schedule(normal_candidate)
    exhausted = build_kitchen_lane_schedule(exhausted_candidate)
    normal_attention = sum(item.attention_minutes for item in normal)
    exhausted_attention = sum(item.attention_minutes for item in exhausted)

    assert exhausted_attention > normal_attention
    assert max(item.end_minute for item in exhausted) >= max(item.end_minute for item in normal)


def test_chicken_uses_fractional_not_exclusive_attention():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["user_energy"] = "Normal"
    schedule = build_kitchen_lane_schedule(candidate)
    chicken = next(item for item in schedule if item.activity.activity_id == "cook:Chicken breast")

    assert chicken.attention_minutes == 3
    assert chicken.end_minute - chicken.start_minute == 12


def test_optional_cuisine_intent_builds_have_need_grocery_gap():
    candidate = generate_candidates(
        "Chicken breast", "Mushrooms & Swiss chard & Asparagus", "Rice", "Chinese",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Mushrooms", "Swiss chard", "Asparagus"],
    )[0]

    assert "Chicken breast" in candidate["inventory_have"]
    assert "Mushrooms" in candidate["inventory_have"]
    assert "Soy sauce" in candidate["inventory_need"]
    assert "Garlic" in candidate["inventory_need"]
    assert "Cornstarch" in candidate["inventory_need"]


def test_available_cuisine_items_are_removed_from_grocery_gap():
    candidate = generate_candidates(
        "Chicken breast", "Mushrooms", "Rice", "Chinese",
        "Normal", "Budget", 60, 4, 1,
        available_items=["Soy sauce"],
    )[0]

    assert "Soy sauce" not in candidate["inventory_need"]
    assert "Garlic" in candidate["inventory_need"]


def test_rice_cooker_moves_rice_off_burner_lane():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["foundation"] = "Basmati rice"
    candidate["available_equipment"] = ["Rice cooker"]
    schedule = build_kitchen_lane_schedule(candidate)
    rice = [item for item in schedule if item.activity.component == "Basmati rice"]

    assert any(item.lane == "Rice Cooker" for item in rice)
    assert not any(item.lane.startswith("Burner ") for item in rice)


def test_three_vegetable_meal_uses_five_minute_prep_rule():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())
    assert graph["prep:meal"].minutes == 5


def test_sauce_seasoning_and_service_are_explicit_activities():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())
    assert "finish sauce:meal" in graph
    assert "adjust seasoning" in graph["finish sauce:meal"].instruction
    assert "plate sides:meal" in graph
    assert "serve chicken:meal" in graph


def test_sides_can_be_plated_while_chicken_rests():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["available_equipment"] = ["Rice cooker"]
    candidate["user_energy"] = "Normal"
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    assert by_id["plate sides:meal"].start_minute < by_id["rest:Chicken breast"].end_minute
    assert by_id["serve chicken:meal"].start_minute >= by_id["slice:Chicken breast"].end_minute


def test_printed_recipe_uses_detailed_ko_instructions():
    from cooking_planner import generate_human_instructions

    candidate = parallel_regression_candidate()
    candidate["available_equipment"] = ["Rice cooker"]
    instructions = generate_human_instructions(candidate)

    assert "do not soak" in instructions
    assert "single, uncrowded layer" in instructions
    assert "woody ends" in instructions
    assert "bright green and crisp-tender" in instructions
    assert "edible stems" in instructions
    assert "Do not rinse raw chicken" in instructions
    assert "165°F" in instructions
    assert "adjust seasoning" in instructions


def test_pressure_cooker_rice_has_all_equipment_owned_phases():
    from cooking_planner import build_activity_graph

    candidate = parallel_regression_candidate()
    candidate["foundation"] = "Basmati rice"
    candidate["available_equipment"] = ["Pressure cooker"]
    graph = build_activity_graph(candidate)

    assert graph["pressurize:Basmati rice"].minutes == 10
    assert graph["pressure cook:Basmati rice"].minutes == 15
    assert graph["natural release:Basmati rice"].minutes == 8
    assert graph["natural release:Basmati rice"].equipment == "pressure cooker"


def test_candidate_metrics_come_from_final_schedule():
    candidate = generate_candidates(
        "Chicken breast", "Mushrooms & Swiss chard & Asparagus", "Basmati rice", "Chinese",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Mushrooms", "Swiss chard", "Asparagus"],
        available_equipment=["Rice cooker"],
    )[0]

    assert candidate["active_minutes"] + candidate["passive_minutes"] == candidate["minutes"]
    assert candidate["selected_rice_equipment"] == "rice cooker"


def test_real_sauce_ko_flows_to_recipe_and_inventory():
    from recipe_engine import build_recipe_from_candidate

    candidate = generate_candidates(
        "Chicken breast", "Mushrooms", "Basmati rice", "Chinese",
        "Normal", "Budget", 60, 4, 1,
        available_items=["Soy sauce", "Cornstarch"],
        available_equipment=["Rice cooker"],
    )[0]
    recipe = build_recipe_from_candidate(candidate)
    text = " ".join(recipe["instructions"])

    assert "1/2 cup water or broth" in text
    assert "cornstarch slurry" in text
    statuses = {item["name"]: item["status"] for item in recipe["inventory_requirements"]}
    assert statuses["Soy sauce"] == "Have"
    assert statuses["Garlic"] == "Need"
    assert "Garlic" in recipe["grocery_list"]


def test_printed_recipe_omits_zero_minute_developer_artifacts():
    from cooking_planner import generate_human_instructions

    candidate = parallel_regression_candidate()
    candidate["available_equipment"] = ["Rice cooker"]
    assert not re.search(r"Minutes (\d+)–\1", generate_human_instructions(candidate))


def test_candidate_total_uses_lane_schedule_makespan():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    schedule = build_kitchen_lane_schedule(candidate)
    makespan = max(item.end_minute for item in schedule)

    assert candidate["minutes"] == makespan
    assert candidate["minutes"] == candidate["active_minutes"] + candidate["passive_minutes"]
