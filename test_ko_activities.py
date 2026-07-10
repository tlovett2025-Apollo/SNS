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
    assert any("finish: meal" in line and line.endswith("planner") for line in summaries)


def test_activity_graph_dependencies_resolve():
    from cooking_planner import build_activity_graph
    graph = build_activity_graph(sample_candidate())
    assert "prep:Chicken breast" in graph
    assert graph["slice:Chicken breast"].depends_on == ["rest:Chicken breast"]
    assert all(dep in graph for activity in graph.values() for dep in activity.depends_on)


def test_lane_schedule_respects_single_human_attention_lane():
    from cooking_planner import build_kitchen_lane_schedule
    schedule = build_kitchen_lane_schedule(sample_candidate(), burner_count=2, human_attention_lanes=1)
    busy = sorted(
        [(item.start_minute, item.end_minute) for item in schedule if item.activity.human_busy and item.end_minute > item.start_minute]
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
