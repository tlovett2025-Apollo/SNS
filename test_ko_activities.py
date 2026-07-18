import re

from cooking_planner import build_cooking_activities, summarize_cooking_activities
from recipe_engine import build_recipe_from_candidate, generate_candidates


def sample_candidate():
    return generate_candidates(
        "Chicken breast", "Swiss chard & Black olives", "White rice", "Comfort Food",
        "Low", "Budget", 30, 4, 1,
        vegetable_names=["Swiss chard", "Black olives"],
    )[0]


def test_knowledge_objects_publish_component_activities():
    activities = build_cooking_activities(sample_candidate())
    assert any(a.component == "Chicken breast" and a.activity_type == "rest" and a.source == "ko" for a in activities)
    assert any(a.component == "Swiss chard" and a.activity_type == "cook" and a.source == "ko" for a in activities)
    assert any(a.component == "Black olives" and a.activity_type == "assemble" and a.source == "ko" for a in activities)


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
    assert "slice:Chicken breast" not in graph
    assert "rest:Chicken breast" in graph["finish and serve:meal"].depends_on
    assert all(dep in graph for activity in graph.values() for dep in activity.depends_on)


def test_activity_consolidation_builds_one_real_ingredient_prep_phase():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())
    prep = graph["prep:meal"]

    assert prep.depends_on == ["gather:meal"]
    assert prep.component == "meal"
    assert prep.activity_type == "prep"
    instruction = prep.instruction.lower()
    assert instruction.startswith("ingredient prep:")
    assert "mise en place" not in instruction
    assert instruction.count("\n\n- ") >= 4
    assert "chicken breast" in instruction
    assert "swiss chard" in instruction
    assert "mushrooms" in instruction
    assert "asparagus" in instruction
    assert "white rice" in instruction
    assert "Measure 1/4 cup Soy sauce" in prep.instruction
    assert "Measure 1 tablespoon Cornstarch" in prep.instruction


def test_component_cooking_depends_on_consolidated_prep():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())

    assert graph["cook:Chicken breast"].depends_on == ["prep:meal"]
    assert graph["cook:White rice"].depends_on == ["prep:meal"]
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
        "Chicken breast", "Swiss chard", "White rice", "Comfort Food",
        "Low", "Budget", 45, 4, 1,
        vegetable_names=["Swiss chard"],
        protein_state=state,
        requested_method="skillet",
    )[0]


def test_protein_state_flows_into_candidate():
    candidate = state_candidate("Frozen Raw")
    assert candidate["protein_state"] == "Frozen Raw"


def test_fresh_raw_chicken_publishes_cook_rest_and_slice():
    activities = build_cooking_activities(state_candidate("Fresh Raw"))
    kinds = [a.activity_type for a in activities if a.component == "Chicken breast"]
    assert kinds == ["prep", "cook", "verify", "rest"]


def test_frozen_raw_chicken_publishes_verify_and_longer_path():
    activities = build_cooking_activities(state_candidate("Frozen Raw"))
    chicken = [a for a in activities if a.component == "Chicken breast"]
    kinds = [a.activity_type for a in chicken]
    assert kinds == ["thaw", "prep", "cook", "verify", "rest"]
    assert sum(a.minutes or 0 for a in chicken) > 30
    assert "thaw" in chicken[0].instruction.lower()
    assert "thaw" not in chicken[1].instruction.lower()


def test_cooked_chicken_reheats_without_raw_cooking_cycle():
    activities = build_cooking_activities(state_candidate("Cooked"))
    chicken = [a for a in activities if a.component == "Chicken breast"]
    kinds = [a.activity_type for a in chicken]
    assert kinds == ["prep", "reheat"]
    assert "cook" not in kinds
    assert "rest" not in kinds


def test_generic_canned_protein_and_beans_publish_reheating_not_cooking():
    from ingredient_profiles import get_ingredient_profile

    chicken = get_ingredient_profile("Canned chicken", "protein").publish_activities("skillet", "Canned")
    beans = get_ingredient_profile("Navy beans", "foundation").publish_activities("skillet", "Canned")

    assert [activity.activity_type for activity in chicken] == ["prep", "reheat"]
    assert [activity.activity_type for activity in beans] == ["prep", "reheat"]
    assert "drain" in chicken[0].instruction.lower()
    assert "drain and rinse" in beans[0].instruction.lower()
    assert "mash" in beans[1].instruction.lower()


def test_citrus_finishes_the_meal_instead_of_cooking_as_a_vegetable():
    from ingredient_profiles import get_ingredient_profile

    activities = get_ingredient_profile("Lemons", "vegetable").publish_activities("skillet", "Fresh")

    assert [activity.activity_type for activity in activities] == ["assemble"]
    assert activities[-1].equipment == "counter"
    assert "juice or wedges" in activities[-1].instruction.lower()


def test_integrated_rustic_sauce_softens_aromatics_before_tomatoes_join():
    candidate = generate_candidates(
        "Rotisserie chicken", "", "", "Italian", "Low", "Moderate", 45, 4, 1,
        vegetable_names=["Onions", "Red bell pepper", "Tomatoes"],
        protein_state="Cooked",
        available_items=["Rotisserie chicken", "Onions", "Red bell pepper", "Tomatoes"],
        requested_method="skillet",
        meal_structure="integrated",
    )[0]
    recipe = build_recipe_from_candidate(candidate)
    plan = " ".join(recipe["action_steps"])

    self_soften = plan.index("soften")
    tomato_join = plan.index("Add Tomatoes")
    assert "Onions & Red bell pepper" in plan
    assert self_soften < tomato_join
    assert "Do not continue simmering after it is hot" in plan


def test_integrated_skillet_protects_one_vessel_from_overlapping_operations():
    candidate = generate_candidates(
        "Rotisserie chicken", "", "Navy beans", "Mediterranean", "Low", "Moderate", 45, 4, 1,
        vegetable_names=["Mushrooms", "Zucchini"], protein_state="Cooked",
        component_forms={"Navy beans": "Canned", "Rotisserie chicken": "Ready to Eat"},
        available_items=["Rotisserie chicken", "Navy beans", "Mushrooms", "Zucchini"],
        requested_method="skillet", meal_structure="integrated",
    )[0]
    from cooking_planner import build_kitchen_lane_schedule
    schedule = build_kitchen_lane_schedule(candidate)
    skillet_work = sorted(
        [item for item in schedule if item.activity.equipment == "burner" and item.activity.component != "Navy beans"],
        key=lambda item: item.start_minute,
    )

    assert all(
        current.end_minute <= following.start_minute
        for current, following in zip(skillet_work, skillet_work[1:])
    )


def test_state_changes_lane_schedule_duration():
    from cooking_planner import build_kitchen_lane_schedule
    fresh = build_kitchen_lane_schedule(state_candidate("Fresh Raw"))
    frozen = build_kitchen_lane_schedule(state_candidate("Frozen Raw"))
    cooked = build_kitchen_lane_schedule(state_candidate("Cooked"))
    fresh_end = max(item.end_minute for item in fresh)
    frozen_end = max(item.end_minute for item in frozen)
    cooked_end = max(item.end_minute for item in cooked)
    assert frozen_end > fresh_end > cooked_end


def test_microwave_thaw_launches_first_and_prep_overlaps_it():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = generate_candidates(
        "Chicken breast", "Onions & Carrots", "", "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Onions", "Carrots"],
        protein_state="Frozen Raw",
        available_equipment=["Microwave"],
        requested_method="skillet",
    )[0]
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    thaw = by_id["thaw:Chicken breast"]
    general_prep = by_id["prep:meal"]
    chicken_prep = by_id["prep:Chicken breast"]
    assert thaw.lane == "Sink"
    assert thaw.end_minute - thaw.start_minute == 30
    assert general_prep.start_minute < thaw.end_minute
    assert chicken_prep.start_minute >= thaw.end_minute


def test_skillet_vegetables_share_one_pan_after_chicken_is_verified():
    from cooking_planner import build_activity_graph

    candidate = generate_candidates(
        "Chicken breast", "Onions & Carrots", "", "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Onions", "Carrots"],
        protein_state="Frozen Raw",
        available_equipment=["Microwave"],
        requested_method="skillet",
    )[0]
    graph = build_activity_graph(candidate)

    assert "cook vegetables:meal" in graph
    assert "cook:Onions" not in graph
    assert "cook:Carrots" not in graph
    shared = graph["cook vegetables:meal"]
    assert "verify:Chicken breast" in shared.depends_on
    assert "Carrots" in shared.instruction
    assert "Onions" in shared.instruction


def test_frozen_ground_beef_uses_one_pan_and_a_feasible_doneness_check():
    from cooking_planner import build_activity_graph

    candidate = generate_candidates(
        "Ground beef", "Onions", "", "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Onions"],
        protein_state="Frozen Raw",
        available_equipment=["Microwave"],
    )[0]
    graph = build_activity_graph(candidate)

    assert graph["thaw:Ground beef"].minutes == 7
    assert graph["thaw:Ground beef"].equipment == "microwave"
    assert graph["prep:Ground beef"].depends_on == ["thaw:Ground beef"]
    assert "cook:Ground beef" not in graph
    assert "verify:Ground beef" not in graph
    skillet = graph["cook skillet:meal"]
    assert "prep:Ground beef" in skillet.depends_on
    assert "same skillet" in skillet.instruction
    assert "no pink ground meat remains" in skillet.instruction
    assert "30 seconds after the last pink disappears" in skillet.instruction


def test_ground_beef_skilletting_and_sauce_stay_on_one_burner_lane():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = generate_candidates(
        "Ground beef", "Onions", "", "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Onions"],
        protein_state="Frozen Raw",
        available_equipment=["Microwave"],
    )[0]
    by_id = {
        item.activity.activity_id: item
        for item in build_kitchen_lane_schedule(candidate)
    }

    assert by_id["cook skillet:meal"].lane == by_id["finish sauce:meal"].lane


def parallel_regression_candidate():
    return generate_candidates(
        "Chicken breast",
        "Swiss chard & Mushrooms & Asparagus",
        "White rice",
        "Chinese",
        "Low",
        "Budget",
        45,
        4,
        1,
        vegetable_names=["Swiss chard", "Mushrooms", "Asparagus"],
        protein_state="Fresh Raw",
    )[0]


def test_fresh_chicken_cook_window_is_not_followed_by_duplicate_passive_cooking():
    from cooking_planner import build_kitchen_lane_schedule

    schedule = build_kitchen_lane_schedule(parallel_regression_candidate())
    by_id = {item.activity.activity_id: item for item in schedule}

    assert "wait:Chicken breast" not in by_id
    assert by_id["rest:Chicken breast"].start_minute == by_id["verify:Chicken breast"].end_minute


def test_rice_passive_cooking_overlaps_other_human_work():
    from cooking_planner import build_kitchen_lane_schedule

    schedule = build_kitchen_lane_schedule(parallel_regression_candidate())
    rice = next(item for item in schedule if item.activity.activity_id == "cook:White rice")

    assert any(
        item.activity.human_busy
        and item.start_minute < rice.end_minute
        and item.end_minute > rice.start_minute
        and item.activity.component != "White rice"
        for item in schedule
    )


def test_rice_launches_before_general_mise_en_place():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["user_energy"] = "Normal"
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    assert by_id["cook:White rice"].start_minute >= by_id["prep:meal"].end_minute
    assert by_id["cook:White rice"].attention_minutes < (
        by_id["cook:White rice"].end_minute - by_id["cook:White rice"].start_minute
    )


def test_basmati_rice_uses_rice_long_lead_activity_graph():
    from cooking_planner import build_activity_graph

    candidate = parallel_regression_candidate()
    candidate["foundation"] = "Basmati rice"
    graph = build_activity_graph(candidate)

    assert "cook:Basmati rice" in graph
    assert graph["cook:Basmati rice"].attention_load < 0.5
    assert graph["cook:Basmati rice"].minutes == 18
    assert graph["cook:Basmati rice"].depends_on == ["prep:meal"]


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


def test_user_energy_input_flows_into_candidate_schedule():
    normal = generate_candidates(
        "Chicken breast", "Mushrooms", "White rice", "Chinese",
        "Medium", "Budget", 60, 4, 1,
    )[0]
    low = generate_candidates(
        "Chicken breast", "Mushrooms", "White rice", "Chinese",
        "Very Low", "Budget", 60, 4, 1,
    )[0]

    assert normal["user_energy"] == "Medium"
    assert low["user_energy"] == "Very Low"
    assert low["active_minutes"] > normal["active_minutes"]


def test_effort_comes_from_whole_meal_schedule():
    full = generate_candidates(
        "Chicken breast", "Mushrooms & Swiss chard & Asparagus", "White rice", "Chinese",
        "Medium", "Budget", 60, 4, 1,
        vegetable_names=["Mushrooms", "Swiss chard", "Asparagus"],
    )[0]
    reduced = generate_candidates(
        "Chicken breast", "Mushrooms", "White rice", "Chinese",
        "Medium", "Budget", 60, 4, 1,
        vegetable_names=["Mushrooms"],
    )[0]

    assert full["effort_score"] > reduced["effort_score"]


def test_chicken_uses_fractional_not_exclusive_attention():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["user_energy"] = "Normal"
    schedule = build_kitchen_lane_schedule(candidate)
    chicken = next(item for item in schedule if item.activity.activity_id == "cook:Chicken breast")

    assert chicken.attention_minutes == 7
    assert chicken.end_minute - chicken.start_minute == 14


def test_optional_cuisine_intent_builds_have_need_grocery_gap():
    candidate = generate_candidates(
        "Chicken breast", "Mushrooms & Swiss chard & Asparagus", "White rice", "Chinese",
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
        "Chicken breast", "Mushrooms", "White rice", "Chinese",
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


def test_rice_cooker_remains_the_low_energy_choice_even_when_time_is_not_shortest():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["foundation"] = "Basmati rice"
    candidate["available_equipment"] = ["Rice cooker"]
    candidate["user_energy"] = "Very Low"

    build_kitchen_lane_schedule(candidate)

    assert candidate["selected_rice_equipment"] == "rice cooker"


def test_slowest_branch_starts_first_and_shorter_branches_converge_at_service():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = generate_candidates(
        "Chicken breast", "Mushrooms & Swiss chard & Asparagus", "Basmati rice", "Chinese",
        "Normal", "Budget", 60, 4, 1,
        vegetable_names=["Mushrooms", "Swiss chard", "Asparagus"],
        protein_state="Frozen Raw",
        available_equipment=["Pressure cooker", "Microwave"],
    )[0]
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    assert min(by_id["prep:launch"].start_minute, by_id["thaw:Chicken breast"].start_minute) == 0
    rice_ready = by_id["pressure cycle:Basmati rice"].end_minute
    service = by_id["finish and serve:meal"]
    chard = by_id["cook vegetables:meal"]
    assert service.start_minute >= rice_ready
    assert service.start_minute - chard.end_minute <= 3


def test_long_post_prep_delay_explains_that_the_wait_is_intentional():
    from cooking_planner import KitchenActivity, ScheduledActivity, _planned_wait_after_prep

    prep = ScheduledActivity(
        KitchenActivity("meal", "prep", "Prep everything.", 4, True),
        "Counter", 0, 4, 4,
    )
    rice = ScheduledActivity(
        KitchenActivity("Basmati rice", "cook", "Cook rice.", 20, False),
        "Rice Cooker", 0, 20, 0,
    )
    vegetables = ScheduledActivity(
        KitchenActivity("vegetables", "cook", "Cook vegetables.", 5, True),
        "Burner 1", 15, 20, 5,
    )

    wait_after, note = _planned_wait_after_prep([prep, rice, vegetables])

    assert wait_after is prep
    assert "about 11 minutes" in note
    assert "Basmati rice is still cooking" in note


def test_small_post_prep_gap_does_not_add_waiting_chatter():
    from cooking_planner import KitchenActivity, ScheduledActivity, _planned_wait_after_prep

    prep = ScheduledActivity(
        KitchenActivity("meal", "prep", "Prep everything.", 4, True),
        "Counter", 0, 4, 4,
    )
    next_step = ScheduledActivity(
        KitchenActivity("vegetables", "cook", "Cook vegetables.", 5, True),
        "Burner 1", 11, 16, 5,
    )

    wait_after, note = _planned_wait_after_prep([prep, next_step])

    assert wait_after is None
    assert note == ""


def test_three_vegetable_meal_uses_five_minute_prep_rule():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())
    assert graph["prep:meal"].minutes == 5


def test_sauce_seasoning_and_service_are_explicit_activities():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(parallel_regression_candidate())
    assert "finish sauce:meal" in graph
    assert "adjust seasoning" in graph["finish sauce:meal"].instruction
    assert "finish and serve:meal" in graph
    assert "plate sides:meal" not in graph
    assert "serve chicken:meal" not in graph


def test_final_service_is_consolidated_after_chicken_rests():
    from cooking_planner import build_kitchen_lane_schedule

    candidate = parallel_regression_candidate()
    candidate["available_equipment"] = ["Rice cooker"]
    candidate["user_energy"] = "Normal"
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    service = by_id["finish and serve:meal"]
    assert service.start_minute >= by_id["rest:Chicken breast"].end_minute
    assert "slice:Chicken breast" not in by_id
    assert service.end_minute - service.start_minute == 2
    # The vegetables and sauce now honor the same physical skillet instead of
    # borrowing an imaginary second pan to preserve the older 31-minute target.
    assert service.end_minute == 42


def test_printed_recipe_uses_detailed_ko_instructions():
    from cooking_planner import generate_human_instructions

    candidate = parallel_regression_candidate()
    candidate["available_equipment"] = ["Rice cooker"]
    instructions = generate_human_instructions(candidate)

    assert "single, uncrowded layer" in instructions
    assert "trim tough ends or strings" in instructions
    assert "Bright color and crisp-tender centers" in instructions
    assert "Do not rinse Chicken breast" in instructions
    assert "165°F" in instructions
    assert "adjust seasoning" in instructions


def test_pressure_cooker_rice_uses_one_silent_equipment_owned_cycle():
    from cooking_planner import build_activity_graph

    candidate = parallel_regression_candidate()
    candidate["foundation"] = "Basmati rice"
    candidate["available_equipment"] = ["Pressure cooker"]
    graph = build_activity_graph(candidate)

    cycle = graph["pressure cycle:Basmati rice"]
    assert cycle.minutes == 35
    assert cycle.equipment == "pressure cooker"
    assert cycle.show_in_plan is False
    assert "pressurize:Basmati rice" not in graph
    assert "pressure cook:Basmati rice" not in graph
    assert "natural release:Basmati rice" not in graph


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

    assert "Measure 1/2 cup Water" in text
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


def soup_candidate(energy="Medium"):
    candidates = generate_candidates(
        "Beef stew meat", "Potatoes & Carrots", "", "Comfort Food",
        energy, "Budget", 120, 4, 10,
        vegetable_names=["Potatoes", "Carrots"],
        protein_state="Fresh Raw",
    )
    return next(candidate for candidate in candidates if candidate["strategy"] == "soup")


def test_soup_uses_one_shared_pot_instead_of_separate_component_cooking():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(soup_candidate())

    assert "optional sear:meal" in graph
    assert "build soup:meal" in graph
    assert "shared simmer:meal" in graph
    assert "finish soup:meal" in graph
    assert "cook:Beef stew meat" not in graph
    assert "cook:Potatoes" not in graph
    assert "cook:Carrots" not in graph
    assert graph["optional sear:meal"].equipment == "burner"
    assert graph["build soup:meal"].equipment == "burner"
    assert graph["shared simmer:meal"].equipment == "burner"


def test_soup_instructions_name_same_pot_and_optional_sear():
    from cooking_planner import generate_human_instructions

    text = generate_human_instructions(soup_candidate()).lower()

    assert "optional but preferred" in text
    assert "soup pot" in text
    assert "same pot" in text
    assert "gently simmer" in text
    assert "gravy or cream sauce" not in text


def test_very_low_energy_soup_skips_optional_sear():
    from cooking_planner import build_activity_graph

    graph = build_activity_graph(soup_candidate("Very Low"))

    assert "optional sear:meal" not in graph
    assert graph["build soup:meal"].depends_on == ["prep:launch"]


def test_pressure_cooker_rice_has_one_launch_instruction_and_no_progress_notes():
    from cooking_planner import generate_human_instructions, generate_human_plan_items

    candidate = generate_candidates(
        "Canned chicken", "Onions", "White rice", "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Onions"], protein_state="Canned",
        available_equipment=["Pressure cooker"],
    )[0]
    text = generate_human_instructions(candidate)
    all_text = " ".join(item["text"] for item in generate_human_plan_items(candidate))

    assert text.count("lock the lid, close the valve, and start high pressure") == 1
    assert "come to pressure" not in all_text
    assert "coming to pressure" not in all_text
    assert "Cook the rice at high pressure" not in all_text
    assert "natural release" not in all_text
    assert "Ingredient Prep:" in text


def test_pressure_cooker_white_rice_uses_25_minutes_to_cooked_plus_ten_release():
    from cooking_planner import build_kitchen_lane_schedule, generate_human_instructions

    candidate = generate_candidates(
        "Ground beef", "Zucchini", "White rice", "Comfort Food",
        "Low", "Budget", 60, 4, 1,
        vegetable_names=["Zucchini"], protein_state="Fresh Raw",
        available_equipment=["Pressure cooker"],
    )[0]
    schedule = build_kitchen_lane_schedule(candidate)
    by_id = {item.activity.activity_id: item for item in schedule}

    start = by_id["start:White rice"]
    cycle = by_id["pressure cycle:White rice"]
    assert cycle.end_minute - start.end_minute == 35
    assert by_id["finish and serve:meal"].start_minute >= cycle.end_minute
    text = generate_human_instructions(candidate)
    assert "Minutes 4–9: Ingredient Prep:" in text
    assert "After prep, you’ll have about 16 minutes before the next cooking step." in text
